#!/usr/bin/env python3
"""The simulation loop (docs/05-simulation.md): random anonymized 15m windows →
same chart + same prompt to every model → bracket decision → immediate
resolution on historical 1m bars → one JSONL row per (window × model).

Stub test (no AI, baseline controls):
  .venv/bin/python scripts/run_simulation.py --windows 16
Live (once API keys are in .env and models enabled/flagged in configs/models.yaml):
  .venv/bin/python scripts/run_simulation.py --windows 200 --models claude-haiku gpt-mini deepseek gemini-flash --seed 42
"""
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from nai.decisions import prompt_hash                       # noqa: E402
from nai.intraday import load_intraday                      # noqa: E402
from nai.models.registry import build_adapters              # noqa: E402
from nai.sim import (                                       # noqa: E402
    DATA_SIM, SIM_PROMPT_VERSION, SimResolver, append_rows, build_snapshot,
    read_rows, render_chart, sample_windows, sim_prompt, sim_rows_path,
    summarize_sim, window_id,
)

ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", type=int, default=16)
    ap.add_argument("--assets", nargs="*", default=ASSETS,
                    help="restrict window sampling to these assets (scope decision "
                         "2026-09-25: SOL-USD only for the current test phase)")
    ap.add_argument("--models", nargs="*", default=None,
                    help="adapter names; default = all enabled in configs/models.yaml")
    ap.add_argument("--visible-bars", type=int, default=40)
    ap.add_argument("--hist-bars", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--time-stop-hours", type=int, default=72)
    ap.add_argument("--no-charts", action="store_true",
                    help="skip PNG rendering (text-only stimulus)")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    adapters, warnings = build_adapters(only=args.models)
    for w in warnings:
        print(f"warning: {w}")
    if not adapters:
        sys.exit("No models available — check configs/models.yaml / API keys.")
    print(f"Models: {[a.name for a in adapters]} "
          f"(vision: {[a.name for a in adapters if getattr(a, 'vision', False)]})")

    print("Loading data…")
    prices15 = {a: load_intraday(a, "15m") for a in args.assets}
    resolver = SimResolver(args.assets, time_stop_hours=args.time_stop_hours)
    windows = sample_windows(prices15, args.windows, args.hist_bars, args.seed)

    run_id = args.run_id or f"sim-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    out_path = sim_rows_path(run_id)
    charts_dir = DATA_SIM / "charts" / run_id
    print(f"{len(windows)} windows → {out_path}")

    t0 = time.time()
    for wi, (asset, ts) in enumerate(windows, 1):
        try:
            snap = build_snapshot(prices15[asset], ts,
                                  visible_bars=args.visible_bars,
                                  hist_bars=args.hist_bars)
        except (ValueError, KeyError):
            continue
        wid = window_id(asset, ts)
        img_path = None
        if not args.no_charts:
            img_path = charts_dir / f"{wid}.png"
            render_chart(snap, img_path)
        prompt = sim_prompt(snap)

        closes = snap["ohlc"][:, 3]
        vis_returns = np.diff(closes) / closes[:-1]
        rows = []
        for model in adapters:
            ctx = {
                "arm": "sim", "asset": asset, "date": str(ts), "prompt": prompt,
                "image_path": str(img_path) if img_path else None,
                # baselines read these (per-bar returns of the visible window);
                # LLM adapters ignore them
                "returns": vis_returns,
            }
            d = model.decide(ctx)
            res = resolver.resolve(asset, ts, d["action"], d["stop_pct"], d["tp_pct"])
            got_image = bool(img_path) and getattr(model, "vision", False)
            rows.append({
                "run_id": run_id,
                "window_id": wid,
                "asset": asset,
                "window_end_ts": str(ts),
                "visible_bars": args.visible_bars,
                "stimulus": "text+image" if got_image else "text",
                "price_real": snap["price_real"],
                "model": model.name,
                "model_version": model.model_version,
                "action": d["action"],
                "stop_pct": d["stop_pct"],
                "tp_pct": d["tp_pct"],
                "confidence": d["confidence"],
                "reason": d["reason"],
                "prompt_version": SIM_PROMPT_VERSION,
                "prompt_hash": prompt_hash(prompt),
                "image": str(img_path.relative_to(ROOT)) if img_path else None,
                "sigma_vis_pct": snap["sigma_vis_pct"],
                "sigma_2d_pct": snap["sigma_2d_pct"],
                "atr14_pct": snap["atr14_pct"],
                "ret_vis_pct": snap["ret_vis_pct"],
                "ma20_now": snap["ma20_now"],
                "ma50_now": snap["ma50_now"],
                "vol24_ratio": snap["vol24_ratio"],
                "ts_decided": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                **res,
            })
        append_rows(rows, out_path)
        if wi % 5 == 0 or wi == len(windows):
            print(f"  window {wi}/{len(windows)} ({time.time() - t0:.0f}s)")

    df = read_rows(out_path)
    df = df[df["run_id"] == run_id]
    print(f"\n{len(df)} decisions recorded. Summary:")
    print(summarize_sim(df).to_string())
    print(f"\nrows:   {out_path}\ncharts: {charts_dir if not args.no_charts else '(skipped)'}")


if __name__ == "__main__":
    main()
