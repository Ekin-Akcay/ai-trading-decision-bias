#!/usr/bin/env python3
"""E1/E2 runner — masked-arm historical bracket backtest for any adapter.

Examples:
  .venv/bin/python scripts/run_masked_backtest.py --model momentum-20
  .venv/bin/python scripts/run_masked_backtest.py --model llama8b --every 2 --rescale-vol --decoys 1
  .venv/bin/python scripts/run_masked_backtest.py --model claude-haiku --respect-cutoff --every 3

Each decision is a bracket trade (direction + stop + target) evaluated by first
passage. Decisions are appended to data/decisions/backtests/<run_id>.jsonl,
then the metric battery is printed.
"""
import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nai.backtest import evaluate_brackets                          # noqa: E402
from nai.config import DATA_DECISIONS, load_models                  # noqa: E402
from nai.data import load_all_prices                                # noqa: E402
from nai.decisions import DecisionRecord, append_records, prompt_hash, read_records  # noqa: E402
from nai.metrics import summarize_brackets                          # noqa: E402
from nai.models.registry import build_adapters, model_spec          # noqa: E402
from nai.prompts import MASKED_PROMPT_VERSION, build_masked_context, masked_prompt  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="adapter name from configs/models.yaml")
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--every", type=int, default=1, help="sample every Nth trading day")
    ap.add_argument("--assets", nargs="*", default=None)
    ap.add_argument("--max-calls", type=int, default=None, help="hard cap (cost guard)")
    ap.add_argument("--rescale-vol", action="store_true",
                    help="normalize context returns to 1%% daily vol (leakage mitigation); "
                         "bracket distances are converted back to real space for evaluation")
    ap.add_argument("--decoys", type=int, default=0,
                    help="E9: add N block-bootstrap synthetic decoys per real asset; "
                         "real-vs-synthetic gap estimates memorization leakage")
    ap.add_argument("--respect-cutoff", action="store_true",
                    help="start only after the model's training cutoff + buffer")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    adapters, warnings = build_adapters(only=[args.model])
    for w in warnings:
        print(f"warning: {w}")
    if not adapters:
        print(f"Model '{args.model}' unavailable.")
        sys.exit(1)
    model = adapters[0]

    start = pd.Timestamp(args.start)
    spec = model_spec(args.model) or {}
    if args.respect_cutoff:
        cutoff = spec.get("cutoff")
        if cutoff:
            buffer_days = load_models().get("buffer_days", 30)
            start = max(start, pd.Timestamp(cutoff) + timedelta(days=buffer_days))
            print(f"Respecting cutoff: start = {start.date()}")
        else:
            print("note: no cutoff on record for this model; using --start as-is")
    end = pd.Timestamp(args.end) if args.end else None

    prices = load_all_prices()
    if args.assets:
        prices = {a: p for a, p in prices.items() if a in args.assets}
    if args.decoys:
        from nai.synthetic import add_decoys
        prices = add_decoys(prices, args.decoys)
        print(f"E9 mode: {args.decoys} synthetic decoy(s) per asset interleaved "
              f"({len(prices)} series total)")

    run_id = args.run_id or (
        f"{args.model}-masked-bracket-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    )
    out_path = DATA_DECISIONS / "backtests" / f"{run_id}.jsonl"

    calls, t0 = 0, time.time()
    records: list[DecisionRecord] = []
    for asset, px in prices.items():
        dates = px.index
        start_i = max(61, int(dates.searchsorted(start)))
        end_i = int(dates.searchsorted(end)) if end is not None else len(dates)
        for i in range(start_i, end_i, args.every):
            if args.max_calls and calls >= args.max_calls:
                break
            date = dates[i]
            ctx_data = build_masked_context(px, date, rescale_vol=args.rescale_vol)
            prompt = masked_prompt(ctx_data)
            ctx = {
                "arm": "masked", "asset": asset,
                "date": ctx_data["context_end_date"],
                "returns": ctx_data["returns"], "prompt": prompt,
            }
            d = model.decide(ctx)
            # model chose distances in shown-space; convert to real space
            k = ctx_data["scale"]
            records.append(DecisionRecord(
                model=model.name, arm="masked", asset=asset,
                action=d["action"],
                stop_pct=d["stop_pct"] / k, tp_pct=d["tp_pct"] / k,
                confidence=d["confidence"], reason=d["reason"],
                context_end_date=ctx_data["context_end_date"],
                price_at_decision=ctx_data["price_at_decision"],
                prompt_version=MASKED_PROMPT_VERSION + ("+rescale" if args.rescale_vol else ""),
                prompt_hash=prompt_hash(prompt),
                model_version=model.model_version, run_id=run_id,
            ))
            calls += 1
            if model.is_llm and calls % 25 == 0:
                append_records(records, out_path)
                records = []
                print(f"  {calls} calls… ({time.time() - t0:.0f}s)")
    append_records(records, out_path)
    print(f"\n{calls} decisions → {out_path} ({time.time() - t0:.1f}s)")

    decisions = read_records(out_path)
    decisions = decisions[decisions["run_id"] == run_id]
    trades = evaluate_brackets(decisions, prices)
    if trades.empty:
        print("No evaluable trades.")
        return
    print("\n=== Overall (bracket, first passage) ===")
    print(summarize_brackets(trades, by=["model"]).to_string())
    if args.decoys:
        from nai.synthetic import is_synthetic
        trades["series"] = ["synthetic" if is_synthetic(a) else "real"
                            for a in trades["asset"]]
        print("\n=== E9 leakage gauge: real vs synthetic (gap ≈ memorization + "
              "identity effects; expect ~0 for baselines and post-cutoff LLMs) ===")
        print(summarize_brackets(trades, by=["model", "series"]).to_string())
    real = trades[~trades["asset"].str.startswith("SYN-")]
    print("\n=== By group ===")
    print(summarize_brackets(real, by=["model", "group"]).to_string())
    print("\n=== After extreme 20d moves (H3) ===")
    print(summarize_brackets(real, by=["model", "ret20_extreme"]).to_string())
    if model.is_llm:
        conf = real[real["sign"] != 0].copy()
        conf["conf_bucket"] = pd.cut(conf["confidence"], (0.0, 0.5, 0.7, 1.01),
                                     right=False, labels=["<0.5", "0.5-0.7", ">=0.7"])
        print("\n=== Calibration (H4) ===")
        print(summarize_brackets(conf, by=["model", "conf_bucket"]).to_string())


if __name__ == "__main__":
    main()
