#!/usr/bin/env python3
"""E1/E2 runner — intraday (15m) masked bracket backtest for the crypto sleeve.

Decisions on 15m context bars, first-passage evaluation on 1m bars, optional
time-stop. Examples:
  .venv/bin/python scripts/intraday_backtest.py --model momentum-20 --start 2024-01-01
  .venv/bin/python scripts/intraday_backtest.py --model llama8b --every-bars 32 --rescale-vol
  .venv/bin/python scripts/intraday_backtest.py --model claude-haiku --respect-cutoff --every-bars 96
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
from nai.decisions import DecisionRecord, append_records, prompt_hash, read_records  # noqa: E402
from nai.intraday import load_intraday                              # noqa: E402
from nai.metrics import summarize_brackets                          # noqa: E402
from nai.models.registry import build_adapters, model_spec          # noqa: E402
from nai.prompts import (                                           # noqa: E402
    MASKED_15M_VERSION, STYLE_SHORT, context_from_window, masked_prompt,
)

ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"]
BAR_MIN = 15
TARGET_VOL_15M = 0.002   # rescale target per 15m bar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--every-bars", type=int, default=16,
                    help="decision every N 15m bars (16 = every 4h)")
    ap.add_argument("--context-bars", type=int, default=288,
                    help="15m bars shown to the model (288 = 3 days)")
    ap.add_argument("--assets", nargs="*", default=ASSETS)
    ap.add_argument("--max-calls", type=int, default=None)
    ap.add_argument("--rescale-vol", action="store_true")
    ap.add_argument("--time-stop-hours", type=int, default=72,
                    help="exit at market if unresolved after this (0 disables)")
    ap.add_argument("--eval-interval", default="1m", choices=["1m", "5m"])
    ap.add_argument("--respect-cutoff", action="store_true")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    adapters, warnings = build_adapters(only=[args.model])
    for w in warnings:
        print(f"warning: {w}")
    if not adapters:
        sys.exit(f"Model '{args.model}' unavailable.")
    model = adapters[0]

    start = pd.Timestamp(args.start)
    spec = model_spec(args.model) or {}
    if args.respect_cutoff and spec.get("cutoff"):
        start = max(start, pd.Timestamp(spec["cutoff"])
                    + timedelta(days=load_models().get("buffer_days", 30)))
        print(f"Respecting cutoff: start = {start}")
    end = pd.Timestamp(args.end) if args.end else None

    ctx_prices = {a: load_intraday(a, "15m") for a in args.assets}
    eval_prices = {a: load_intraday(a, args.eval_interval) for a in args.assets}
    epm = {"1m": 1, "5m": 5}[args.eval_interval]
    max_bars = (args.time_stop_hours * 60 // epm) if args.time_stop_hours else None

    run_id = args.run_id or (
        f"{args.model}-15m-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}")
    out_path = DATA_DECISIONS / "backtests" / f"{run_id}.jsonl"

    calls, t0 = 0, time.time()
    records: list[DecisionRecord] = []
    for asset, px in ctx_prices.items():
        dates = px.index
        close_np = px["close"].to_numpy(float)
        rets_np = px["close"].pct_change().to_numpy(float)
        start_i = max(args.context_bars + 1, int(dates.searchsorted(start)))
        end_i = int(dates.searchsorted(end)) if end is not None else len(dates)
        for i in range(start_i, end_i, args.every_bars):
            if args.max_calls and calls >= args.max_calls:
                break
            ctx_data = context_from_window(
                rets_np[i - args.context_bars + 1:i + 1], close_np[i], dates[i],
                rescale_vol=args.rescale_vol, target_vol=TARGET_VOL_15M,
                ts_format="%Y-%m-%dT%H:%M")
            prompt = masked_prompt(ctx_data, bar_label="15-minute", style=STYLE_SHORT)
            ctx = {"arm": "masked", "asset": asset, "date": ctx_data["context_end_date"],
                   "returns": ctx_data["returns"], "prompt": prompt}
            d = model.decide(ctx)
            k = ctx_data["scale"]
            records.append(DecisionRecord(
                model=model.name, arm="masked", asset=asset, action=d["action"],
                stop_pct=d["stop_pct"] / k, tp_pct=d["tp_pct"] / k,
                confidence=d["confidence"], reason=d["reason"],
                context_end_date=ctx_data["context_end_date"],
                price_at_decision=ctx_data["price_at_decision"],
                prompt_version=MASKED_15M_VERSION + ("+rescale" if args.rescale_vol else ""),
                prompt_hash=prompt_hash(prompt),
                model_version=model.model_version, timeframe="15m", run_id=run_id,
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
    t0 = time.time()
    trades = evaluate_brackets(decisions, ctx_prices, eval_prices=eval_prices,
                               context_bar_minutes=BAR_MIN, max_bars=max_bars)
    bpd = 1440 / epm
    print(f"evaluated in {time.time() - t0:.1f}s\n")
    print("=== Overall (first passage on "
          f"{args.eval_interval} bars, time-stop {args.time_stop_hours}h) ===")
    print(summarize_brackets(trades, by=["model"], bars_per_day=bpd).to_string())
    print("\n=== By asset ===")
    print(summarize_brackets(trades, by=["model", "asset"], bars_per_day=bpd).to_string())
    print("\n=== After extreme trailing moves (H3; buckets on 15m features) ===")
    print(summarize_brackets(trades, by=["model", "ret20_extreme"],
                             bars_per_day=bpd).to_string())
    if model.is_llm:
        conf = trades[trades["sign"] != 0].copy()
        conf["conf_bucket"] = pd.cut(conf["confidence"], (0.0, 0.5, 0.7, 1.01),
                                     right=False, labels=["<0.5", "0.5-0.7", ">=0.7"])
        print("\n=== Calibration (H4) ===")
        print(summarize_brackets(conf, by=["model", "conf_bucket"],
                                 bars_per_day=bpd).to_string())


if __name__ == "__main__":
    main()
