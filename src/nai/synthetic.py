"""Synthetic decoy series for the masked arm (E9, H11).

A model cannot have memorized a bootstrap path. Interleaving statistically
matched synthetic series with real ones in a masked run turns "is there
leakage?" from an argument into a measurement:

    accuracy(real) - accuracy(synthetic)  on PRE-cutoff dates  ≈ memorization
    accuracy(real) - accuracy(synthetic)  on POST-cutoff dates ≈ 0 expected

Decoys are moving-block bootstraps of each real asset's own returns (block=10
preserves short-range autocorrelation and volatility clustering), so summary
stats fed to the model are distribution-matched. Deterministic per (asset, k).
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

SYN_PREFIX = "SYN-"


def block_bootstrap_prices(prices: pd.DataFrame, source: str, clone: int,
                           block: int = 10) -> pd.DataFrame:
    """Bootstrap whole OHLC bars (as ratios to the previous close) so intrabar
    wick structure survives — bracket (stop/target) evaluation on decoys must
    face the same touch dynamics as real bars."""
    c = prices["close"].to_numpy(float)
    ratios = np.column_stack([
        prices["open"].to_numpy(float)[1:] / c[:-1],
        prices["high"].to_numpy(float)[1:] / c[:-1],
        prices["low"].to_numpy(float)[1:] / c[:-1],
        c[1:] / c[:-1],
    ])
    n = len(ratios)
    if n < 3 * block:
        raise ValueError("series too short to bootstrap")
    seed = int(hashlib.sha256(f"syn|{source}|{clone}".encode()).hexdigest()[:12], 16)
    rng = np.random.default_rng(seed)
    picks = np.empty((n, 4))
    i = 0
    while i < n:
        start = int(rng.integers(0, n - block))
        take = min(block, n - i)
        picks[i:i + take] = ratios[start:start + take]
        i += take
    prev_close = 100.0 * np.concatenate([[1.0], np.cumprod(picks[:-1, 3])])
    df = pd.DataFrame(
        {
            "open": prev_close * picks[:, 0],
            "high": prev_close * picks[:, 1],
            "low": prev_close * picks[:, 2],
            "close": prev_close * picks[:, 3],
            "volume": 0.0,
        },
        index=prices.index[1:],
    )
    df.index.name = "date"
    return df


def add_decoys(prices: dict[str, pd.DataFrame], per_asset: int) -> dict[str, pd.DataFrame]:
    out = dict(prices)
    for asset, px in prices.items():
        for k in range(1, per_asset + 1):
            out[f"{SYN_PREFIX}{asset}-{k}"] = block_bootstrap_prices(px, asset, k)
    return out


def is_synthetic(asset: str) -> bool:
    return asset.startswith(SYN_PREFIX)
