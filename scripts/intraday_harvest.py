#!/usr/bin/env python3
"""E7 — intraday forward harvest for the crypto sleeve (run once daily).

The Binance live API is geo-blocked here, so freshest data = data.binance.vision
daily zips (~1 day lag). Each run: refresh bars, then place decisions at every
4h mark not yet logged (lookback --backfill-hours). Retro-marks are leakage-
clean: each context ends at its mark; the model has no channel to later bars.

  .venv/bin/python scripts/intraday_harvest.py            # refresh + harvest
  .venv/bin/python scripts/intraday_harvest.py --dry-run
"""
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from nai.config import DATA_DECISIONS                       # noqa: E402
from nai.decisions import DecisionRecord, append_records, prompt_hash, read_records  # noqa: E402
from nai.intraday import load_intraday, pull_intraday       # noqa: E402
from nai.models.registry import build_adapters              # noqa: E402
from nai.prompts import (                                   # noqa: E402
    INFORMED_15M_VERSION, MASKED_15M_VERSION, STYLE_SHORT,
    build_masked_context, informed_prompt, masked_prompt,
)

ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"]
ARMS = ("masked", "informed")
CONTEXT_BARS = 288
MARK_EVERY_H = 4


def marks_for(px: pd.DataFrame, backfill_hours: int) -> pd.DatetimeIndex:
    """15m bars (open-time labels) whose CLOSE falls on a 4h boundary within
    the backfill window: label minute == 45 and (hour+1) % MARK_EVERY_H == 0."""
    idx = px.index
    lo = idx[-1] - pd.Timedelta(hours=backfill_hours)
    m = idx[(idx >= lo) & (idx.minute == 45) & ((idx.hour + 1) % MARK_EVERY_H == 0)]
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--no-refresh", action="store_true")
    ap.add_argument("--backfill-hours", type=int, default=36)
    args = ap.parse_args()

    if not args.dry_run and not args.no_refresh:
        print("Refreshing intraday bars (bulk CDN)…")
        pull_intraday(ASSETS, ["15m", "1m"])

    adapters, warnings = build_adapters(only=args.models)
    for w in warnings:
        print(f"warning: {w}")
    if not adapters:
        sys.exit("No models available/enabled — check configs/models.yaml and API keys.")
    print(f"Harvesting with: {[a.name for a in adapters]}")

    now = datetime.now(timezone.utc)
    out_path = DATA_DECISIONS / "live" / f"{now.strftime('%Y-%m')}-15m.jsonl"
    existing = read_records(out_path)
    seen = set()
    if not existing.empty:
        seen = set(zip(existing["model"], existing["arm"], existing["asset"],
                       existing["context_end_date"].dt.strftime("%Y-%m-%dT%H:%M")))

    records, t0 = [], time.time()
    for asset in ASSETS:
        px = load_intraday(asset, "15m")
        for ts in marks_for(px, args.backfill_hours):
            try:
                ctx_data = build_masked_context(px, ts, n=CONTEXT_BARS,
                                                ts_format="%Y-%m-%dT%H:%M")
            except ValueError:
                continue
            for arm in ARMS:
                prompt = (masked_prompt(ctx_data, "15-minute", STYLE_SHORT)
                          if arm == "masked"
                          else informed_prompt(asset, ctx_data, "15-minute", STYLE_SHORT))
                pv = MASKED_15M_VERSION if arm == "masked" else INFORMED_15M_VERSION
                for model in adapters:
                    key = (model.name, arm, asset, ctx_data["context_end_date"])
                    if key in seen:
                        continue
                    ctx = {"arm": arm, "asset": asset,
                           "date": ctx_data["context_end_date"],
                           "returns": ctx_data["returns"], "prompt": prompt}
                    d = model.decide(ctx)
                    records.append(DecisionRecord(
                        model=model.name, arm=arm, asset=asset, action=d["action"],
                        stop_pct=d["stop_pct"], tp_pct=d["tp_pct"],
                        confidence=d["confidence"], reason=d["reason"],
                        context_end_date=ctx_data["context_end_date"],
                        price_at_decision=ctx_data["price_at_decision"],
                        prompt_version=pv, prompt_hash=prompt_hash(prompt),
                        model_version=model.model_version,
                        timeframe="15m", run_id="live",
                    ))

    n_err = sum(1 for r in records if r.action == "error")
    print(f"{len(records)} new decisions ({n_err} errors) in {time.time() - t0:.1f}s")
    if args.dry_run:
        for r in records[:8]:
            print(f"  {r.context_end_date} {r.model:12s} {r.arm:8s} {r.asset:9s} "
                  f"-> {r.action:5s} sl={r.stop_pct * 100:.2f}% tp={r.tp_pct * 100:.2f}%")
        print("dry run — nothing written")
    else:
        append_records(records, out_path)
        print(f"appended -> {out_path}")


if __name__ == "__main__":
    main()
