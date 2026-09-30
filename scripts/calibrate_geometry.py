#!/usr/bin/env python3
"""Geometry ↔ duration ↔ resolvability calibration on intraday perp bars.

Answers: which stop sizes produce trades that typically close in the target
window, and is the chosen evaluation granularity sufficient (ambiguous-bar
rate), per asset? Also shows what daily bars would throw away.

Entries at fixed hour marks, alternating long/short, RR fixed at 2.

  .venv/bin/python scripts/calibrate_geometry.py                    # 1m eval
  .venv/bin/python scripts/calibrate_geometry.py --eval-interval 5m --stops 0.5 1 2
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nai.data import load_prices        # noqa: E402
from nai.intraday import load_intraday  # noqa: E402

ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"]
RR = 2.0
CAP_DAYS = 30


def first_passage(o, h, l, c, entries, stop, tp, cap_bars):
    """(outcome_code, bars_held): 1=tp, -1=sl, 0=ambiguous, 2=beyond cap.
    Alternating long/short per entry; timing only (gap price irrelevant here)."""
    out, held = [], []
    n = len(c)
    for k, p in enumerate(entries):
        sign = 1.0 if k % 2 == 0 else -1.0
        entry = c[p]
        if sign > 0:
            sl_px, tp_px = entry * (1 - stop), entry * (1 + tp)
        else:
            sl_px, tp_px = entry * (1 + stop), entry * (1 - tp)
        end = min(n, p + 1 + cap_bars)
        code, bars = 2, end - 1 - p
        for j in range(p + 1, end):
            if sign > 0:
                hit_sl, hit_tp = l[j] <= sl_px, h[j] >= tp_px
            else:
                hit_sl, hit_tp = h[j] >= sl_px, l[j] <= tp_px
            if hit_sl and hit_tp:
                code, bars = 0, j - p
                break
            if hit_sl:
                code, bars = -1, j - p
                break
            if hit_tp:
                code, bars = 1, j - p
                break
        out.append(code)
        held.append(bars)
    return np.array(out), np.array(held)


def daily_amb(asset, stop, tp):
    """Share of daily bars whose range covers BOTH levels — trades daily data
    could never resolve."""
    try:
        px = load_prices(asset)
    except FileNotFoundError:
        return np.nan
    entry = px["close"].shift(1)
    covers = (px["low"] <= entry * (1 - stop)) & (px["high"] >= entry * (1 + tp))
    return float(covers.mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-interval", default="1m", choices=["1m", "5m"])
    ap.add_argument("--stops", nargs="*", type=float, default=[0.1, 0.2, 0.3, 0.5, 1.0],
                    help="stop sizes in PERCENT")
    ap.add_argument("--every-h", type=int, default=8)
    ap.add_argument("--assets", nargs="*", default=ASSETS)
    args = ap.parse_args()

    bar_min = {"1m": 1, "5m": 5}[args.eval_interval]
    cap_bars = CAP_DAYS * 24 * 60 // bar_min
    rows = []
    for asset in args.assets:
        px = load_intraday(asset, args.eval_interval)
        o, h, l, c = (px[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        idx = px.index
        mask = (idx.minute == 0) & (idx.hour % args.every_h == 0)
        entries = np.nonzero(mask)[0]
        entries = entries[entries > 0]
        for stop_pc in args.stops:
            stop, tp = stop_pc / 100, RR * stop_pc / 100
            code, bars = first_passage(o, h, l, c, entries, stop, tp, cap_bars)
            resolved = code != 2
            hrs = bars * bar_min / 60
            rows.append({
                "asset": asset, "stop%": stop_pc, "tp%": RR * stop_pc,
                "median_h": float(np.median(hrs[resolved])) if resolved.any() else np.nan,
                "p90_h": float(np.percentile(hrs[resolved], 90)) if resolved.any() else np.nan,
                "<24h%": float((hrs[resolved] <= 24).mean() * 100),
                "<72h%": float((hrs[resolved] <= 72).mean() * 100),
                f"amb_{args.eval_interval}%": float((code == 0).mean() * 100),
                f">{CAP_DAYS}d%": float((code == 2).mean() * 100),
                "amb_daily%": daily_amb(asset, stop, tp) * 100,
            })
    df = pd.DataFrame(rows).round(2)
    print(df.to_string(index=False))
    print(f"\namb_{args.eval_interval}%: trades the {args.eval_interval} evaluator "
          "can't order (both levels in one bar) — excluded.\namb_daily%: share of "
          "DAILY bars covering both levels — what daily-bar evaluation would discard.")


if __name__ == "__main__":
    main()
