"""Anonymized random-window trading simulation (docs/05-simulation.md).

Loop: sample a random 15m window (any asset, any time, overlap allowed) →
build an anonymized snapshot (price rebased to 100 at the current bar, volume
as ratio to recent average, no dates, no names) → render a candlestick chart
PNG + an identical stats/prompt text for every model → each model returns one
bracket trade (direction, stop %, target %) → resolve immediately against
historical 1m bars (first passage) recording outcome, holding time, P/L %,
and max favorable/adverse excursion → append everything to one JSONL row per
(window × model).

The chart deliberately mimics a standard trading chart (green/red candles,
MA20/MA50 overlays, volume subpanel) — it is a stimulus, and ecological
validity beats house style.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import SIGN, _scan_bracket
from .config import DATA_SIM, cost_bps_per_side
from .intraday import load_intraday

SIM_PROMPT_VERSION = "sim-v1-15m-window"
CONTEXT_BAR_MIN = 15

UP, DOWN = "#26a69a", "#ef5350"          # conventional trading-chart candle colors
MA_FAST_C, MA_SLOW_C = "#1976d2", "#f39c12"


# ---------------------------------------------------------------- windows ----

def window_id(asset: str, ts) -> str:
    return hashlib.sha256(f"{asset}|{ts}".encode()).hexdigest()[:10]


def sample_windows(prices15: dict[str, pd.DataFrame], n: int, hist_bars: int,
                   seed: int) -> list[tuple[str, pd.Timestamp]]:
    """Uniform random (asset, window-end-bar) pairs; overlaps allowed."""
    rng = np.random.default_rng(seed)
    assets = sorted(prices15)
    out = []
    for _ in range(n):
        asset = assets[int(rng.integers(len(assets)))]
        idx = prices15[asset].index
        i = int(rng.integers(hist_bars + 1, len(idx) - 2))
        out.append((asset, idx[i]))
    return out


# --------------------------------------------------------------- snapshot ----

def build_snapshot(px15: pd.DataFrame, ts, visible_bars: int = 20,
                   hist_bars: int = 200) -> dict:
    """Anonymized view: rebased prices (now = 100), volume ratios, indicators
    computed on a hidden longer history (hist_bars) so MAs are well-defined."""
    end_i = px15.index.get_loc(ts)
    if end_i < hist_bars:
        raise ValueError("not enough history for this window")
    hist = px15.iloc[end_i - hist_bars + 1:end_i + 1]
    vis = hist.iloc[-visible_bars:]
    price_real = float(vis["close"].iloc[-1])
    k = 100.0 / price_real

    close_h = hist["close"]
    vol_avg = float(hist["volume"].mean()) or 1.0
    ma20 = close_h.rolling(20).mean() * k
    ma50 = close_h.rolling(50).mean() * k
    rets_vis = vis["close"].pct_change().dropna()
    rets_2d = close_h.pct_change().iloc[-192:].dropna()      # ~2 days of 15m bars
    tr = np.maximum(
        hist["high"] - hist["low"],
        np.maximum((hist["high"] - close_h.shift()).abs(),
                   (hist["low"] - close_h.shift()).abs()))
    atr14 = float(tr.rolling(14).mean().iloc[-1] / price_real)

    return {
        "ts": pd.Timestamp(ts),
        "visible_bars": visible_bars,
        "price_real": price_real,
        "ohlc": vis[["open", "high", "low", "close"]].to_numpy(float) * k,
        "vol_ratio": (vis["volume"] / vol_avg).to_numpy(float),
        "ma20_vis": ma20.iloc[-visible_bars:].to_numpy(float),
        "ma50_vis": ma50.iloc[-visible_bars:].to_numpy(float),
        "ma20_now": float(ma20.iloc[-1]),
        "ma50_now": float(ma50.iloc[-1]),
        "sigma_vis_pct": float(rets_vis.std() * 100),
        "sigma_2d_pct": float(rets_2d.std() * 100),
        "atr14_pct": atr14 * 100,
        "ret_vis_pct": float((vis["close"].iloc[-1] / vis["close"].iloc[0] - 1) * 100),
        "vol24_ratio": float(hist["volume"].iloc[-96:].mean() / vol_avg),
        "vol_last5_ratio": float(vis["volume"].iloc[-5:].mean() / vol_avg),
    }


# ------------------------------------------------------------------ chart ----

def render_chart(snap: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = snap["visible_bars"]
    x = np.arange(n)
    o, h, l, c = snap["ohlc"].T
    up = c >= o

    fig, (ax, axv) = plt.subplots(
        2, 1, figsize=(max(8.0, n * 0.24), 5.5), dpi=110, sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.06})
    for i in range(n):
        color = UP if up[i] else DOWN
        ax.plot([x[i], x[i]], [l[i], h[i]], color=color, linewidth=1.1, zorder=2)
        body_lo, body_hi = min(o[i], c[i]), max(o[i], c[i])
        ax.add_patch(plt.Rectangle((x[i] - 0.32, body_lo), 0.64,
                                   max(body_hi - body_lo, 1e-4),
                                   facecolor=color, edgecolor=color, zorder=3))
    ax.plot(x, snap["ma20_vis"], color=MA_FAST_C, linewidth=1.4, zorder=4)
    ax.plot(x, snap["ma50_vis"], color=MA_SLOW_C, linewidth=1.4, zorder=4)
    ax.text(x[-1] + 0.4, snap["ma20_vis"][-1], "MA20", color=MA_FAST_C,
            fontsize=8, va="center")
    ax.text(x[-1] + 0.4, snap["ma50_vis"][-1], "MA50", color=MA_SLOW_C,
            fontsize=8, va="center")
    ax.axhline(100.0, color="#888888", linewidth=0.7, linestyle=":", zorder=1)
    ax.set_ylabel("price (now = 100)", fontsize=9)
    ax.grid(alpha=0.22, linewidth=0.5)
    ax.set_xlim(-0.8, n + 1.6)

    axv.bar(x, snap["vol_ratio"], width=0.64,
            color=[UP if u else DOWN for u in up], alpha=0.55)
    axv.axhline(1.0, color="#888888", linewidth=0.7, linestyle=":")
    axv.set_ylabel("vol ÷ avg", fontsize=9)
    axv.grid(alpha=0.22, linewidth=0.5)
    tick_step = 5 if n <= 30 else 10
    ticks = list(range(0, n - 2, tick_step)) + [n - 1]
    axv.set_xticks(ticks)
    axv.set_xticklabels([("now" if t == n - 1 else str(t - (n - 1))) for t in ticks],
                        fontsize=8)
    for a in (ax, axv):
        for side in ("top", "right"):
            a.spines[side].set_visible(False)
        a.tick_params(labelsize=8)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------- prompt ----

def sim_prompt(snap: dict) -> str:
    n = snap["visible_bars"]
    lines = []
    for i in range(n):
        o, h, l, c = snap["ohlc"][i]
        tag = "now" if i == n - 1 else f"{i - (n - 1):+d}"
        lines.append(f"{tag:>4}: O={o:7.2f} H={h:7.2f} L={l:7.2f} C={c:7.2f} "
                     f"vol={snap['vol_ratio'][i]:4.2f}x")
    pos20 = "above" if 100.0 >= snap["ma20_now"] else "below"
    pos50 = "above" if 100.0 >= snap["ma50_now"] else "below"
    return (
        "You are a short-term trader looking at an anonymized chart of a liquid "
        "asset: 15-minute bars, no dates, price rebased so the CURRENT price = "
        "100.00, volume shown as a multiple of recent average volume.\n"
        f"The last {n} bars (oldest first; bar offsets, 'now' = current bar):\n"
        + "\n".join(lines) + "\n"
        f"Indicators (same rebased scale): MA20 = {snap['ma20_now']:.2f}, "
        f"MA50 = {snap['ma50_now']:.2f}; price is {pos20} MA20 and {pos50} MA50.\n"
        f"Volatility: std of 15m returns over these {n} bars = "
        f"{snap['sigma_vis_pct']:.3f}%/bar; over the last 2 days = "
        f"{snap['sigma_2d_pct']:.3f}%/bar; ATR(14) = {snap['atr14_pct']:.3f}% "
        f"of price.\n"
        f"Move over the visible window: {snap['ret_vis_pct']:+.2f}%. "
        f"Volume: last 24h average = {snap['vol24_ratio']:.2f}x normal, "
        f"last 5 bars = {snap['vol_last5_ratio']:.2f}x normal.\n"
        "Entry is at the current price (100.00). Your trade will run untouched "
        "until your stop-loss or take-profit is hit. Place your bracket trade now: "
        "long, short, or flat, with stop_loss_pct and take_profit_pct as percent "
        "of entry."
    )


# -------------------------------------------------------------- resolution ---

class SimResolver:
    """Resolves bracket decisions against historical 1m bars, immediately.

    Precomputes per-asset arrays once; each resolve() is a fast first-passage
    scan returning outcome, timing, P/L and excursion stats."""

    def __init__(self, assets: list[str], eval_interval: str = "1m",
                 time_stop_hours: int = 72):
        self.bar_min = {"1m": 1, "5m": 5}[eval_interval]
        self.max_bars = time_stop_hours * 60 // self.bar_min if time_stop_hours else None
        self._d = {}
        for a in assets:
            px = load_intraday(a, eval_interval)
            self._d[a] = (px.index, px["open"].to_numpy(float),
                          px["high"].to_numpy(float), px["low"].to_numpy(float),
                          px["close"].to_numpy(float))

    def resolve(self, asset: str, ts: pd.Timestamp, action: str,
                stop_pct: float, tp_pct: float) -> dict:
        base = {"outcome": "none", "entry_price": np.nan, "exit_price": np.nan,
                "exit_ts": None, "minutes_held": 0, "pnl_gross_pct": 0.0,
                "pnl_net_pct": 0.0, "mfe_pct": np.nan, "mae_pct": np.nan}
        sign = SIGN.get(action, 0.0)
        if sign == 0.0 or not (stop_pct > 0 and tp_pct > 0):
            return base
        idx, o, h, l, c = self._d[asset]
        moment = pd.Timestamp(ts) + pd.Timedelta(minutes=CONTEXT_BAR_MIN)
        p = int(idx.searchsorted(moment)) - 1
        if p < 0 or p >= len(c) - 1:
            return base
        outcome, exit_px, held, mfe, mae = _scan_bracket(
            o, h, l, c, p, sign, stop_pct, tp_pct, self.max_bars)
        entry = c[p]
        rt = 2 * cost_bps_per_side(asset) / 1e4
        gross = np.nan if outcome == "ambiguous" else sign * (exit_px / entry - 1.0)
        return {
            "outcome": outcome,
            "entry_price": float(entry),
            "exit_price": None if np.isnan(exit_px) else float(exit_px),
            "exit_ts": str(idx[p + held]) if held > 0 else None,
            "minutes_held": int(held * self.bar_min),
            "pnl_gross_pct": None if np.isnan(gross) else float(gross * 100),
            "pnl_net_pct": None if np.isnan(gross) else float((gross - rt) * 100),
            "mfe_pct": float(mfe * 100),
            "mae_pct": float(mae * 100),
        }


# ---------------------------------------------------------------- storage ----

def sim_rows_path(run_id: str) -> Path:
    return DATA_SIM / "decisions" / f"{run_id}.jsonl"


def append_rows(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def read_rows(path: Path) -> pd.DataFrame:
    rows = []
    with open(path) as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def summarize_sim(df: pd.DataFrame) -> pd.DataFrame:
    """Per-model results table for a simulation run."""
    out = []
    for model, g in df.groupby("model"):
        traded = g[g["action"].isin(["long", "short"])]
        hit = traded[traded["outcome"].isin(["tp", "sl"])]
        closed = traded[traded["outcome"].isin(["tp", "sl", "timeout"])]
        tp_base = (traded["stop_pct"] / (traded["stop_pct"] + traded["tp_pct"])).mean()
        out.append({
            "model": model,
            "n": len(g),
            "long%": (g["action"] == "long").mean() * 100,
            "flat%": (g["action"] == "flat").mean() * 100,
            "err%": (g["action"] == "error").mean() * 100,
            "tpHit%": (hit["outcome"] == "tp").mean() * 100 if len(hit) else np.nan,
            "tpBase%": tp_base * 100 if len(traded) else np.nan,
            "gross%/tr": closed["pnl_gross_pct"].mean() if len(closed) else np.nan,
            "afterFees%/tr": closed["pnl_net_pct"].mean() if len(closed) else np.nan,
            "med_min": closed["minutes_held"].median() if len(closed) else np.nan,
            "mfe%": closed["mfe_pct"].mean() if len(closed) else np.nan,
            "mae%": closed["mae_pct"].mean() if len(closed) else np.nan,
            "stopW%": traded["stop_pct"].mean() * 100 if len(traded) else np.nan,
            "tpW%": traded["tp_pct"].mean() * 100 if len(traded) else np.nan,
            "tmo%": (traded["outcome"] == "timeout").mean() * 100 if len(traded) else np.nan,
            "amb%": (traded["outcome"] == "ambiguous").mean() * 100 if len(traded) else np.nan,
        })
    return pd.DataFrame(out).set_index("model").round(2)
