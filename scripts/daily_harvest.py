#!/usr/bin/env python3
"""E7 — daily decision harvest (the forward, leakage-proof dataset).

For every asset × arm × enabled model: build the context from the latest data
and log ONE bracket trade (direction + stop + target). The trade then resolves
on its own over the following days; report.py evaluates matured trades.
Run daily (cron/launchd/scheduled task); see docs/03-workflows.md for timing.

  .venv/bin/python scripts/daily_harvest.py            # refresh data + harvest
  .venv/bin/python scripts/daily_harvest.py --dry-run  # no data refresh, no write
"""
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nai.config import DATA_DECISIONS                       # noqa: E402
from nai.data import load_all_prices, pull_all              # noqa: E402
from nai.decisions import DecisionRecord, append_records, prompt_hash  # noqa: E402
from nai.models.registry import build_adapters              # noqa: E402
from nai.prompts import (                                   # noqa: E402
    INFORMED_PROMPT_VERSION, MASKED_PROMPT_VERSION,
    build_masked_context, informed_prompt, masked_prompt,
)

ARMS = ("masked", "informed")  # informed = asset name + date ONLY; no news (scope decision)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--no-refresh", action="store_true")
    args = ap.parse_args()

    if not args.dry_run and not args.no_refresh:
        print("Refreshing price data…")
        pull_all()

    adapters, warnings = build_adapters(only=args.models)
    for w in warnings:
        print(f"warning: {w}")
    if not adapters:
        print("No models available/enabled — check configs/models.yaml and API keys.")
        sys.exit(1)
    print(f"Harvesting with: {[a.name for a in adapters]}")

    prices = load_all_prices()
    now = datetime.now(timezone.utc)
    out_path = DATA_DECISIONS / "live" / f"{now.strftime('%Y-%m')}.jsonl"

    records, t0 = [], time.time()
    for asset, px in prices.items():
        try:
            ctx_data = build_masked_context(px, px.index[-1])
        except ValueError:
            continue
        for arm in ARMS:
            prompt = (masked_prompt(ctx_data) if arm == "masked"
                      else informed_prompt(asset, ctx_data))
            pv = MASKED_PROMPT_VERSION if arm == "masked" else INFORMED_PROMPT_VERSION
            for model in adapters:
                whitelist = getattr(model, "asset_whitelist", None)
                if whitelist and asset not in whitelist:
                    continue
                ctx = {"arm": arm, "asset": asset,
                       "date": ctx_data["context_end_date"],
                       "returns": ctx_data["returns"], "prompt": prompt}
                d = model.decide(ctx)
                records.append(DecisionRecord(
                    model=model.name, arm=arm, asset=asset,
                    action=d["action"], stop_pct=d["stop_pct"], tp_pct=d["tp_pct"],
                    confidence=d["confidence"], reason=d["reason"],
                    context_end_date=ctx_data["context_end_date"],
                    price_at_decision=ctx_data["price_at_decision"],
                    prompt_version=pv, prompt_hash=prompt_hash(prompt),
                    model_version=model.model_version, run_id="live",
                ))

    n_err = sum(1 for r in records if r.action == "error")
    print(f"{len(records)} decisions ({n_err} errors) in {time.time() - t0:.1f}s")
    if args.dry_run:
        for r in records[:6]:
            print(f"  {r.model:12s} {r.arm:8s} {r.asset:9s} -> {r.action:5s} "
                  f"sl={r.stop_pct * 100:.2f}% tp={r.tp_pct * 100:.2f}% "
                  f"conf={r.confidence:.2f} ({r.reason[:32]})")
        print("dry run — nothing written")
    else:
        append_records(records, out_path)
        print(f"appended -> {out_path}")


if __name__ == "__main__":
    main()
