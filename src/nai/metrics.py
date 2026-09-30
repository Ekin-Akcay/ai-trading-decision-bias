"""Metric battery: hit rates with Wilson intervals, mean bps with t-stats,
annualized Sharpe, calibration, regime splits, consensus/dispersion utilities.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .config import periods_per_year


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (center - half, center + half)


def _summarize_group(g: pd.DataFrame) -> pd.Series:
    traded = g[g["sign"] != 0]
    n, nt = len(g), len(traded)
    hit = traded["correct"].mean() if nt else np.nan
    lo, hi = wilson_ci(int(traded["correct"].sum()), nt) if nt else (np.nan, np.nan)
    mean_pnl = traded["pnl"].mean() if nt else np.nan
    std_pnl = traded["pnl"].std() if nt > 1 else np.nan
    tstat = mean_pnl / (std_pnl / math.sqrt(nt)) if nt > 1 and std_pnl > 0 else np.nan
    ppy = int(g["asset"].map(periods_per_year).mean()) if "asset" in g else 252
    h = g["horizon_days"].mode().iat[0] if len(g) else 1
    sharpe = (mean_pnl / std_pnl * math.sqrt(ppy / h)
              if nt > 1 and std_pnl and std_pnl > 0 else np.nan)
    return pd.Series({
        "n": n,
        "traded": nt,
        "long%": (g["action"] == "long").mean() * 100,
        "short%": (g["action"] == "short").mean() * 100,
        "flat%": (g["action"] == "flat").mean() * 100,
        "err%": (g["action"] == "error").mean() * 100,
        "hit%": hit * 100 if nt else np.nan,
        "hit_lo%": lo * 100,
        "hit_hi%": hi * 100,
        "bps/trade": mean_pnl * 1e4 if nt else np.nan,
        "t": tstat,
        "annSharpe": sharpe,
    })


def summarize(trades: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """Direction-diagnostic metric table (fixed-horizon trades from `evaluate`)."""
    if trades.empty:
        return pd.DataFrame()
    by = by or ["model"]
    return trades.groupby(by, observed=True, dropna=False).apply(
        _summarize_group, include_groups=False).round(2)


def _summarize_brackets_group(g: pd.DataFrame, bars_per_day: float = 1.0) -> pd.Series:
    traded = g[g["sign"] != 0]
    hit_lvl = traded[traded["outcome"].isin(["tp", "sl"])]
    closed = traded[traded["outcome"].isin(["tp", "sl", "timeout"])]
    n, nt, nr, nc = len(g), len(traded), len(hit_lvl), len(closed)
    tp_hits = int((hit_lvl["outcome"] == "tp").sum())
    tp_rate = tp_hits / nr if nr else np.nan
    lo, hi = wilson_ci(tp_hits, nr) if nr else (np.nan, np.nan)
    # random-walk-implied TP probability for the chosen geometry: stop/(stop+tp)
    tp_base = (traded["stop_pct"] / (traded["stop_pct"] + traded["tp_pct"])).mean() \
        if nt else np.nan
    mean_pnl = closed["pnl"].mean() if nc else np.nan
    std_pnl = closed["pnl"].std() if nc > 1 else np.nan
    tstat = mean_pnl / (std_pnl / math.sqrt(nc)) if nc > 1 and std_pnl > 0 else np.nan
    mdays = closed["bars_held"].mean() / bars_per_day if nc else np.nan
    ppy = int(g["asset"].map(periods_per_year).mean()) if "asset" in g else 252
    sharpe = (mean_pnl / std_pnl * math.sqrt(ppy / max(mdays, 1.0 / bars_per_day))
              if nc > 1 and std_pnl and std_pnl > 0 else np.nan)
    rr = (traded["tp_pct"] / traded["stop_pct"]).replace([np.inf, -np.inf], np.nan).mean() \
        if nt else np.nan
    stop_sigma = (traded["stop_pct"] / traded["vol_20"]).replace(
        [np.inf, -np.inf], np.nan).mean() if nt and "vol_20" in traded else np.nan
    return pd.Series({
        "n": n,
        "traded": nt,
        "closed": nc,
        "long%": (g["action"] == "long").mean() * 100,
        "flat%": (g["action"] == "flat").mean() * 100,
        "err%": (g["action"] == "error").mean() * 100,
        "tpHit%": tp_rate * 100,        # among tp/sl resolutions only
        "tpHit_lo%": lo * 100,
        "tpHit_hi%": hi * 100,
        "tpBase%": tp_base * 100,       # tpHit% vs tpBase% is the skill read
        "bps/trade": mean_pnl * 1e4,    # over closed trades (tp/sl/timeout)
        "t": tstat,
        "annSharpe~": sharpe,           # ~: varying holding times, approximation
        "days": mdays,
        "stopW%": traded["stop_pct"].mean() * 100 if nt else np.nan,
        "tpW%": traded["tp_pct"].mean() * 100 if nt else np.nan,
        "RR": rr,
        "stop/σbar": stop_sigma,        # stop width in units of context-bar vol (20-bar)
        "tmo%": (traded["outcome"] == "timeout").mean() * 100 if nt else np.nan,
        "amb%": (traded["outcome"] == "ambiguous").mean() * 100 if nt else np.nan,
        "open%": (traded["outcome"] == "open").mean() * 100 if nt else np.nan,
    })


def summarize_brackets(trades: pd.DataFrame, by: list[str] | None = None,
                       bars_per_day: float = 1.0) -> pd.DataFrame:
    """Bracket-trade metric table (first-passage trades from `evaluate_brackets`).

    bars_per_day: evaluation-bar frequency (1 for daily bars, 1440 for 1m bars)
    so `days` and annualization are in calendar terms.
    Key reads: tpHit% vs tpBase% (skill beyond geometry), bps/trade net,
    stop/σbar (stops inside the per-bar noise band get churned, H12),
    RR asymmetry (H13), tmo%/amb%/open% (time-stop and data-resolution health)."""
    if trades.empty:
        return pd.DataFrame()
    by = by or ["model"]
    return trades.groupby(by, observed=True, dropna=False).apply(
        _summarize_brackets_group, include_groups=False,
        bars_per_day=bars_per_day).round(2)


def calibration(trades: pd.DataFrame, bins=(0.0, 0.5, 0.7, 1.01)) -> pd.DataFrame:
    t = trades[trades["sign"] != 0].copy()
    if t.empty:
        return pd.DataFrame()
    t["conf_bucket"] = pd.cut(t["confidence"], bins, right=False,
                              labels=["<0.5", "0.5-0.7", ">=0.7"])
    return summarize(t, by=["model", "conf_bucket"])


def regime_table(trades: pd.DataFrame) -> pd.DataFrame:
    return summarize(trades, by=["model", "trend_20", "vol_bucket"])


def extreme_move_table(trades: pd.DataFrame) -> pd.DataFrame:
    return summarize(trades, by=["model", "ret20_extreme"])


def consensus_frame(decisions: pd.DataFrame) -> pd.DataFrame:
    """Per (asset, date): mean signed action across models (confidence-weighted)
    and dispersion. Input: raw decisions with >=2 models per asset-date."""
    d = decisions.copy()
    sign = d["action"].map({"long": 1.0, "short": -1.0, "flat": 0.0})
    d["signed"] = sign * d["confidence"].clip(0, 1)
    g = d.groupby(["asset", "context_end_date"])
    out = g.agg(consensus=("signed", "mean"),
                dispersion=("signed", "std"),
                n_models=("model", "nunique"))
    return out[out["n_models"] >= 2].reset_index()


def agreement_with(trades: pd.DataFrame, other: pd.DataFrame) -> float:
    """Share of asset-dates where two models chose the same non-flat action (H8)."""
    key = ["asset", "context_end_date"]
    a = trades[trades["sign"] != 0][key + ["action"]]
    b = other[other["sign"] != 0][key + ["action"]]
    m = a.merge(b, on=key, suffixes=("_a", "_b"))
    return float((m["action_a"] == m["action_b"]).mean()) if len(m) else float("nan")
