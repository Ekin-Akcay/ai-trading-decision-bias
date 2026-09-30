"""Price data: yfinance primary, Stooq (US listings) and Binance (crypto) fallbacks.

All series are daily bars saved to data/raw/<asset>.csv with columns
date,open,high,low,close,volume — close is adjusted where the source supports it.
"""
from __future__ import annotations

import io
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from .config import DATA_RAW, load_assets

STD_COLS = ["open", "high", "low", "close", "volume"]

BINANCE_MAP = {  # asset name -> Binance spot symbol
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "SOL-USD": "SOLUSDT",
    "DOGE-USD": "DOGEUSDT",
}


def _standardize(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    df = df.rename(columns={"adj close": "close"}) if "adj close" in df.columns else df
    df = df[[c for c in STD_COLS if c in df.columns]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df.index.name = "date"
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df.dropna(subset=["close"])


def fetch_yfinance(asset: str, start: str) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(asset, start=start, auto_adjust=True, progress=False)
    if df is None or df.empty:
        raise RuntimeError(f"yfinance returned no data for {asset}")
    return _standardize(df)


def fetch_stooq(asset: str, start: str) -> pd.DataFrame:
    sym = asset.lower() + ".us"  # US-listed equities/ETFs only
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if "Close" not in df.columns or df.empty:
        raise RuntimeError(f"stooq returned no data for {asset}")
    df = df.set_index("Date")
    df = _standardize(df)
    return df[df.index >= pd.Timestamp(start)]


def fetch_binance(asset: str, start: str) -> pd.DataFrame:
    symbol = BINANCE_MAP[asset]
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    rows: list[list] = []
    while True:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": "1d", "startTime": start_ms, "limit": 1000},
            timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        start_ms = batch[-1][6] + 1  # next after last close time
        if len(batch) < 1000:
            break
        time.sleep(0.2)
    if not rows:
        raise RuntimeError(f"binance returned no data for {asset}")
    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "qv", "n", "tbb", "tbq", "ignore",
    ])
    df["date"] = pd.to_datetime(df["open_time"], unit="ms").dt.normalize()
    df = df.set_index("date")[STD_COLS].astype(float)
    today = pd.Timestamp(datetime.now(timezone.utc).date())
    return df[df.index < today]  # drop the still-open UTC bar


def _trim_open_crypto_bar(asset: str, df: pd.DataFrame) -> pd.DataFrame:
    """Crypto trades 24/7: the current UTC day's bar is partial until midnight.
    A decision must never read a partial close, so drop bars >= today (UTC)."""
    if asset in BINANCE_MAP:
        today = pd.Timestamp(datetime.now(timezone.utc).date())
        return df[df.index < today]
    return df


def pull_asset(asset: str, start: str) -> tuple[pd.DataFrame, str]:
    """Try yfinance, then the appropriate fallback. Returns (df, source)."""
    try:
        return _trim_open_crypto_bar(asset, fetch_yfinance(asset, start)), "yfinance"
    except Exception as primary_err:
        try:
            if asset in BINANCE_MAP:
                return fetch_binance(asset, start), "binance"
            return fetch_stooq(asset, start), "stooq"
        except Exception as fallback_err:
            raise RuntimeError(
                f"{asset}: yfinance failed ({primary_err}); fallback failed ({fallback_err})"
            ) from fallback_err


def pull_all(force: bool = False) -> pd.DataFrame:
    """Pull/refresh every asset in the universe. Returns a summary DataFrame."""
    cfg = load_assets()
    start = cfg["start_date"]
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    summary = []
    for group, assets in cfg["universe"].items():
        for asset in assets:
            path = DATA_RAW / f"{asset}.csv"
            try:
                df, source = pull_asset(asset, start)
                df.to_csv(path)
                summary.append({
                    "asset": asset, "group": group, "source": source, "rows": len(df),
                    "first": df.index[0].date(), "last": df.index[-1].date(),
                })
            except Exception as e:
                cached = "cached" if path.exists() else "MISSING"
                summary.append({
                    "asset": asset, "group": group, "source": f"FAILED ({cached})",
                    "rows": 0, "first": None, "last": None,
                })
                print(f"  ! {asset}: {e}")
    return pd.DataFrame(summary)


def load_prices(asset: str) -> pd.DataFrame:
    path = DATA_RAW / f"{asset}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No data for {asset}; run scripts/pull_data.py first")
    df = pd.read_csv(path, index_col="date", parse_dates=True)
    return df.sort_index()


def load_all_prices() -> dict[str, pd.DataFrame]:
    out = {}
    for asset in [a for g in load_assets()["universe"].values() for a in g]:
        try:
            out[asset] = load_prices(asset)
        except FileNotFoundError:
            pass
    return out
