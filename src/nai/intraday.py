"""Intraday crypto data: Binance USDT-M perpetual futures klines + funding.

Why perps: it's the venue the strategy would trade (native shorting, ~5 bps
taker), bars carry real wick structure for stop/target touch evaluation, and
funding rates (the incumbent crowding signal, H10) live here.

Sources:
  * bulk history: data.binance.vision monthly + current-month daily zip files
    (public CDN, no key);
  * tail (last day) and funding: fapi.binance.com public API — geo-restricted
    in some regions; failures degrade gracefully (bulk zips reach ~yesterday).

Storage: data/raw/intraday/<ASSET>_<interval>.csv.gz, index = bar OPEN time
(UTC, tz-naive). The current, still-open bar is always dropped.
"""
from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from .config import DATA_RAW
from .data import BINANCE_MAP

DATA_INTRADAY = DATA_RAW / "intraday"
DATA_FUNDING = DATA_RAW / "funding"

VISION = "https://data.binance.vision/data/futures/um"
FAPI = "https://fapi.binance.com"
PERP_DATA_START = "2019-09"          # earliest UM futures bulk data
INTERVAL_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240}


def _epoch_to_dt(series: pd.Series) -> pd.DatetimeIndex:
    v = pd.to_numeric(series, errors="coerce").astype("int64")
    first = int(v.iloc[0])
    unit = "us" if first > 1e14 else ("ms" if first > 1e11 else "s")
    return pd.to_datetime(v, unit=unit)


def _read_kline_zip(content: bytes) -> pd.DataFrame | None:
    try:
        z = zipfile.ZipFile(io.BytesIO(content))
        df = pd.read_csv(z.open(z.namelist()[0]), header=None)
    except Exception:
        return None
    if df.empty:
        return None
    if not str(df.iloc[0, 0]).lstrip("-").isdigit():   # header row present in some files
        df = df.iloc[1:].reset_index(drop=True)
    df = df.iloc[:, :6].copy()
    df.columns = ["ts", "open", "high", "low", "close", "volume"]
    df.index = _epoch_to_dt(df["ts"])
    df.index.name = "ts"
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def _fetch_zip(url: str) -> pd.DataFrame | None:
    try:
        r = requests.get(url, timeout=60)
        if r.status_code != 200:
            return None
        return _read_kline_zip(r.content)
    except requests.RequestException:
        return None


def _month_list(start: str) -> list[str]:
    months = []
    cur = pd.Timestamp(start + "-01")
    now = pd.Timestamp(datetime.now(timezone.utc).date().replace(day=1))
    while cur <= now:
        months.append(cur.strftime("%Y-%m"))
        cur += pd.offsets.MonthBegin(1)
    return months


def _fapi_tail(symbol: str, interval: str, start: pd.Timestamp) -> pd.DataFrame | None:
    rows = []
    start_ms = int(start.tz_localize("UTC").timestamp() * 1000)
    try:
        while True:
            r = requests.get(f"{FAPI}/fapi/v1/klines", timeout=30, params={
                "symbol": symbol, "interval": interval,
                "startTime": start_ms, "limit": 1500})
            if r.status_code != 200:
                break
            batch = r.json()
            if not batch:
                break
            rows.extend(batch)
            start_ms = batch[-1][0] + 1
            if len(batch) < 1500:
                break
    except requests.RequestException:
        pass
    if not rows:
        return None
    df = pd.DataFrame(rows).iloc[:, :6]
    df.columns = ["ts", "open", "high", "low", "close", "volume"]
    df.index = _epoch_to_dt(df["ts"])
    df.index.name = "ts"
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def fetch_um_klines(symbol: str, interval: str, start_month: str = PERP_DATA_START,
                    workers: int = 8) -> pd.DataFrame:
    months = _month_list(start_month)
    urls = [f"{VISION}/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{m}.zip"
            for m in months]
    # current month arrives as daily files
    now = datetime.now(timezone.utc).date()
    day = now.replace(day=1)
    while day < now:
        urls.append(f"{VISION}/daily/klines/{symbol}/{interval}/"
                    f"{symbol}-{interval}-{day.isoformat()}.zip")
        day += timedelta(days=1)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        parts = [p for p in ex.map(_fetch_zip, urls) if p is not None and not p.empty]
    if not parts:
        raise RuntimeError(f"no bulk data for {symbol} {interval}")
    df = pd.concat(parts).sort_index()
    tail = _fapi_tail(symbol, interval, df.index[-1] + pd.Timedelta(minutes=1))
    if tail is not None:
        df = pd.concat([df, tail]).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    # drop the still-open bar
    cutoff = pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None) \
        - pd.Timedelta(minutes=INTERVAL_MINUTES[interval])
    return df[df.index <= cutoff]


def pull_intraday(assets: list[str], intervals: list[str]) -> pd.DataFrame:
    DATA_INTRADAY.mkdir(parents=True, exist_ok=True)
    summary = []
    for asset in assets:
        symbol = BINANCE_MAP[asset]
        for interval in intervals:
            try:
                df = fetch_um_klines(symbol, interval)
                path = DATA_INTRADAY / f"{asset}_{interval}.csv.gz"
                df.to_csv(path)
                summary.append({"asset": asset, "interval": interval, "rows": len(df),
                                "first": df.index[0], "last": df.index[-1]})
            except Exception as e:
                summary.append({"asset": asset, "interval": interval, "rows": 0,
                                "first": None, "last": f"FAILED: {e}"})
    return pd.DataFrame(summary)


def load_intraday(asset: str, interval: str) -> pd.DataFrame:
    path = DATA_INTRADAY / f"{asset}_{interval}.csv.gz"
    if not path.exists():
        raise FileNotFoundError(f"no {interval} data for {asset}; run scripts/pull_intraday.py")
    df = pd.read_csv(path, index_col="ts", parse_dates=True)
    return df.sort_index()


def _read_funding_zip(content: bytes) -> pd.DataFrame | None:
    try:
        z = zipfile.ZipFile(io.BytesIO(content))
        df = pd.read_csv(z.open(z.namelist()[0]), header=None)
    except Exception:
        return None
    if df.empty:
        return None
    if not str(df.iloc[0, 0]).lstrip("-").isdigit():   # header row variant
        df = df.iloc[1:].reset_index(drop=True)
    # columns: calc_time, funding_interval_hours, last_funding_rate
    df = df.iloc[:, [0, -1]].copy()
    df.columns = ["ts", "fundingRate"]
    df.index = _epoch_to_dt(df["ts"])
    df.index.name = "ts"
    return df[["fundingRate"]].astype(float)


def fetch_funding(symbol: str) -> pd.DataFrame | None:
    """fapi first; on failure (geo-blocked), data.binance.vision monthly zips."""
    rows = []
    start_ms = int(pd.Timestamp(PERP_DATA_START + "-01", tz="UTC").timestamp() * 1000)
    try:
        while True:
            r = requests.get(f"{FAPI}/fapi/v1/fundingRate", timeout=30, params={
                "symbol": symbol, "startTime": start_ms, "limit": 1000})
            if r.status_code != 200:
                rows = []
                break
            batch = r.json()
            if not batch:
                break
            rows.extend(batch)
            start_ms = batch[-1]["fundingTime"] + 1
            if len(batch) < 1000:
                break
    except requests.RequestException:
        rows = []
    if rows:
        df = pd.DataFrame(rows)
        df.index = pd.to_datetime(df["fundingTime"].astype("int64"), unit="ms")
        df.index.name = "ts"
        return df[["fundingRate"]].astype(float)

    urls = [f"{VISION}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{m}.zip"
            for m in _month_list(PERP_DATA_START)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        raw = []
        for url in urls:
            raw.append(url)
        parts = []
        for content in ex.map(lambda u: _get_bytes(u), raw):
            if content is not None:
                p = _read_funding_zip(content)
                if p is not None and not p.empty:
                    parts.append(p)
    if not parts:
        return None
    df = pd.concat(parts).sort_index()
    return df[~df.index.duplicated(keep="last")]


def _get_bytes(url: str) -> bytes | None:
    try:
        r = requests.get(url, timeout=60)
        return r.content if r.status_code == 200 else None
    except requests.RequestException:
        return None


def pull_funding(assets: list[str]) -> list[str]:
    DATA_FUNDING.mkdir(parents=True, exist_ok=True)
    notes = []
    for asset in assets:
        df = fetch_funding(BINANCE_MAP[asset])
        if df is None or df.empty:
            notes.append(f"{asset}: funding unavailable (fapi blocked?) — H10 deferred")
            continue
        df.to_csv(DATA_FUNDING / f"{asset}.csv.gz")
        notes.append(f"{asset}: {len(df)} funding points "
                     f"({df.index[0].date()} → {df.index[-1].date()})")
    return notes
