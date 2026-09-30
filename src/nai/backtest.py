"""Backtest engines.

PRIMARY — bracket (first-passage) evaluation, matching the trade model: enter
at the close of context_end_date; the trade runs untouched until stop or target
is hit. Rules (documented in docs/04-data-and-leakage.md):
  * scanning starts on the NEXT bar; entry bar itself can't exit the trade;
  * a gap through a level exits at the OPEN (realistic gap fill), not the level;
  * a bar that touches BOTH levels intrabar is 'ambiguous' (daily OHLC can't
    order them) -> pnl NaN, excluded from headline stats, count reported;
  * a trade whose levels are never hit by the end of data is 'open' ->
    marked to market at the last close for info, excluded from hit-rate stats;
  * round-trip cost charged once per trade.

SECONDARY — fixed-horizon direction diagnostic (`evaluate`): ignores brackets
and scores direction over a fixed h. Not a trade model; used only to decompose
"direction skill" from "bracket-geometry skill" on the same logged decisions.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import asset_group, cost_bps_per_side
from .features import trailing_frame

SIGN = {"long": 1.0, "short": -1.0, "flat": 0.0, "error": 0.0}


def _scan_bracket(o, h, lo, cl, p, sign, stop, tpd, max_bars):
    """First-passage scan for one trade entered at bar p's close.

    Returns (outcome, exit_px, bars_held, mfe, mae). mfe >= 0 is the max
    favorable excursion and mae <= 0 the max adverse excursion, as signed
    fractional returns from entry, measured through the exit bar (the exit
    bar's full extremes are included). Exit/ambiguity rules per docs/04 §6."""
    n = len(cl)
    entry = cl[p]
    if sign > 0:
        sl_px, tp_px = entry * (1 - stop), entry * (1 + tpd)
    else:
        sl_px, tp_px = entry * (1 + stop), entry * (1 - tpd)
    end_scan = n if max_bars is None else min(n, p + 1 + max_bars)
    run_hi, run_lo = entry, entry
    outcome, exit_px, held = None, None, None
    for j in range(p + 1, end_scan):
        run_hi = max(run_hi, h[j])
        run_lo = min(run_lo, lo[j])
        op = o[j]
        if sign > 0:
            if op <= sl_px:
                outcome, exit_px, held = "sl", op, j - p; break
            if op >= tp_px:
                outcome, exit_px, held = "tp", op, j - p; break
            hit_sl, hit_tp = lo[j] <= sl_px, h[j] >= tp_px
        else:
            if op >= sl_px:
                outcome, exit_px, held = "sl", op, j - p; break
            if op <= tp_px:
                outcome, exit_px, held = "tp", op, j - p; break
            hit_sl, hit_tp = h[j] >= sl_px, lo[j] <= tp_px
        if hit_sl and hit_tp:
            outcome, exit_px, held = "ambiguous", np.nan, j - p; break
        if hit_sl:
            outcome, exit_px, held = "sl", sl_px, j - p; break
        if hit_tp:
            outcome, exit_px, held = "tp", tp_px, j - p; break
    if outcome is None:
        if max_bars is not None and p + max_bars < n:
            outcome, exit_px, held = "timeout", cl[p + max_bars], max_bars
        else:
            outcome, exit_px, held = "open", cl[-1], n - 1 - p
    if sign > 0:
        mfe, mae = run_hi / entry - 1.0, run_lo / entry - 1.0
    else:
        mfe, mae = 1.0 - run_lo / entry, 1.0 - run_hi / entry
    return outcome, exit_px, held, mfe, mae

_FEAT_COLS = ("trend_20", "vol_bucket", "ret20_extreme", "vol_20")


def _attach_features(d: pd.DataFrame, feats: pd.DataFrame) -> pd.DataFrame:
    fidx = feats.index.get_indexer(d["context_end_date"])
    for col in _FEAT_COLS:
        vals = feats[col].to_numpy(dtype=object)
        d[col] = [vals[i] if i >= 0 else None for i in fidx]
    d["vol_20"] = pd.to_numeric(d["vol_20"], errors="coerce")
    return d


def evaluate_brackets(decisions: pd.DataFrame, prices: dict[str, pd.DataFrame],
                      eval_prices: dict[str, pd.DataFrame] | None = None,
                      context_bar_minutes: int = 1440,
                      max_bars: int | None = None) -> pd.DataFrame:
    """One row per decision with: outcome (tp|sl|timeout|ambiguous|open|none),
    exit_price, bars_held (in EVALUATION bars), pnl (net of round-trip cost),
    sign, plus regime features from the CONTEXT series.

    Same-series mode (eval_prices=None): decision label must exist in `prices`
    index; entry at that bar's close, scan from the next bar.
    Cross-series mode: decisions were made on `prices` bars (context, e.g. 15m,
    label = bar OPEN time) and are evaluated on finer `eval_prices` bars (e.g.
    1m). Entry moment = label + context_bar_minutes (the context bar's close);
    entry price = close of the last eval bar before that moment.
    max_bars: optional time-stop — if unresolved after this many eval bars,
    exit at market ('timeout', scored as a real trade).
    """
    frames = []
    for asset, dgroup in decisions.groupby("asset"):
        if asset not in prices:
            continue
        ctx_px = prices[asset]
        epx = ctx_px if eval_prices is None else eval_prices.get(asset)
        if epx is None:
            continue
        o = epx["open"].to_numpy(float)
        h = epx["high"].to_numpy(float)
        lo = epx["low"].to_numpy(float)
        cl = epx["close"].to_numpy(float)
        n = len(cl)
        feats = trailing_frame(ctx_px)
        d = dgroup.copy()
        d["context_end_date"] = pd.to_datetime(d["context_end_date"])
        if eval_prices is None:
            entry_pos = ctx_px.index.get_indexer(d["context_end_date"])
        else:
            moments = d["context_end_date"] + pd.Timedelta(minutes=context_bar_minutes)
            entry_pos = epx.index.searchsorted(moments.to_numpy()) - 1
        ok = (entry_pos >= 0) & (entry_pos < n)
        d = d[ok].reset_index(drop=True)
        entry_pos = np.asarray(entry_pos)[ok]
        if d.empty:
            continue
        rt = 2 * cost_bps_per_side(asset) / 1e4

        outcomes, exits, bars, pnls, signs, mfes, maes = [], [], [], [], [], [], []
        for row, p in zip(d.itertuples(index=False), entry_pos):
            sign = SIGN.get(row.action, 0.0)
            stop, tpd = float(row.stop_pct), float(row.tp_pct)
            if sign == 0.0 or not (stop > 0 and tpd > 0):
                outcomes.append("none"); exits.append(np.nan); bars.append(0)
                pnls.append(0.0); signs.append(0.0); mfes.append(np.nan); maes.append(np.nan)
                continue
            outcome, exit_px, held, mfe, mae = _scan_bracket(
                o, h, lo, cl, p, sign, stop, tpd, max_bars)
            entry = cl[p]
            pnl = np.nan if outcome == "ambiguous" else sign * (exit_px / entry - 1.0) - rt
            outcomes.append(outcome); exits.append(exit_px); bars.append(held)
            pnls.append(pnl); signs.append(sign); mfes.append(mfe); maes.append(mae)

        d["outcome"] = outcomes
        d["exit_price"] = exits
        d["bars_held"] = bars
        d["pnl"] = pnls
        d["sign"] = signs
        d["mfe"] = mfes
        d["mae"] = maes
        d["cost"] = np.where(d["sign"] != 0, rt, 0.0)
        d["group"] = asset_group(asset)
        frames.append(_attach_features(d, feats))

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def evaluate(decisions: pd.DataFrame, prices: dict[str, pd.DataFrame],
             horizon: int = 1) -> pd.DataFrame:
    """Direction-only diagnostic at a fixed horizon (close -> close+h), ignoring
    brackets. Same cost model as a round trip. NOT the trade model."""
    frames = []
    for asset, dgroup in decisions.groupby("asset"):
        if asset not in prices:
            continue
        px = prices[asset]
        close = px["close"]
        feats = trailing_frame(px)
        d = dgroup.copy()
        d["context_end_date"] = pd.to_datetime(d["context_end_date"])
        pos = close.index.get_indexer(d["context_end_date"])
        d = d[pos >= 0].reset_index(drop=True)
        pos = pos[pos >= 0]
        if d.empty:
            continue
        cl = close.to_numpy()
        valid = pos + horizon < len(cl)
        fwd = np.full(len(d), np.nan)
        fwd[valid] = cl[pos[valid] + horizon] / cl[pos[valid]] - 1.0
        d["fwd_ret"] = fwd
        d = d.dropna(subset=["fwd_ret"])
        if d.empty:
            continue
        d["sign"] = d["action"].map(SIGN).fillna(0.0)
        rt = 2 * cost_bps_per_side(asset) / 1e4
        d["cost"] = np.where(d["sign"] != 0, rt, 0.0)
        d["pnl"] = d["sign"] * d["fwd_ret"] - d["cost"]
        d["correct"] = np.where(d["sign"] != 0, d["sign"] * d["fwd_ret"] > 0, np.nan)
        d["horizon_days"] = horizon
        d["group"] = asset_group(asset)
        frames.append(_attach_features(d, feats))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def invert(trades: pd.DataFrame) -> pd.DataFrame:
    """Direction-diagnostic counterfactual only. Identity: for traded rows,
    pnl_inverse = -pnl - 2*round_trip_cost — inversion flips the gross return
    but pays costs AGAIN, the structural drag any fade must overcome.
    (A bracket-trade fade additionally swaps the stop/target geometry and is
    defined in the analysis layer, not here.)"""
    inv = trades.copy()
    inv["sign"] = -inv["sign"]
    inv["pnl"] = inv["sign"] * inv["fwd_ret"] - inv["cost"]
    inv["correct"] = np.where(inv["sign"] != 0, inv["sign"] * inv["fwd_ret"] > 0, np.nan)
    act_map = {"long": "short", "short": "long"}
    inv["action"] = inv["action"].map(lambda a: act_map.get(a, a))
    return inv
