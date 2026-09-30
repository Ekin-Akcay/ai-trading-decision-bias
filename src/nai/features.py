"""Trailing features and regime tags used for context building and conditional metrics.

Note: vol terciles and ret20 deciles are computed on the FULL sample per asset —
fine for diagnostics/conditioning tables, but a live trading rule must use
expanding or fixed thresholds instead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def daily_returns(close: pd.Series) -> pd.Series:
    return close.pct_change()


def trailing_frame(prices: pd.DataFrame) -> pd.DataFrame:
    """Per-date trailing stats for one asset. Everything uses data up to and
    including that date (safe to condition decisions on)."""
    close = prices["close"]
    ret = close.pct_change()
    out = pd.DataFrame(index=prices.index)
    out["ret_1"] = ret
    out["ret_5"] = close.pct_change(5)
    out["ret_20"] = close.pct_change(20)
    out["vol_20"] = ret.rolling(20).std()
    out["trend_20"] = np.where(out["ret_20"] > 0, "up", "down")
    # full-sample buckets (diagnostics only — see module docstring)
    try:
        out["vol_bucket"] = pd.qcut(out["vol_20"], 3, labels=["low", "mid", "high"])
    except (ValueError, IndexError):  # too little data / degenerate distribution
        out["vol_bucket"] = None
    dec = out["ret_20"].rank(pct=True)
    out["ret20_extreme"] = np.select(
        [dec >= 0.9, dec <= 0.1], ["ext_up", "ext_down"], default="normal"
    )
    return out


def forward_return(close: pd.Series, horizon: int) -> pd.Series:
    return close.shift(-horizon) / close - 1.0
