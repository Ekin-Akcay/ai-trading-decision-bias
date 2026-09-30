#!/usr/bin/env python3
"""E0 — engine validation + noise floor, bracket trade model.

Runs the four control models daily over the whole universe (each places a
2σ-stop / 4σ-target bracket; only direction differs), evaluates by first
passage, prints the metric battery, and demonstrates why raw 'hit rate' is
meaningless without the geometry-implied base rate.
Results saved to data/results/e0_baselines.csv.
"""
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nai.backtest import evaluate, evaluate_brackets     # noqa: E402
from nai.config import DATA_RESULTS                      # noqa: E402
from nai.data import load_all_prices                     # noqa: E402
from nai.metrics import summarize, summarize_brackets    # noqa: E402
from nai.models.baselines import BASELINES               # noqa: E402

START = "2019-01-01"
MIN_CONTEXT = 60


def run_baselines(prices: dict) -> pd.DataFrame:
    rows = []
    for name, factory in BASELINES.items():
        model = factory()
        for asset, px in prices.items():
            close = px["close"]
            rets = close.pct_change().to_numpy()
            dates = close.index
            start_i = max(MIN_CONTEXT + 1, dates.searchsorted(pd.Timestamp(START)))
            for i in range(start_i, len(dates)):
                ctx = {
                    "asset": asset, "date": dates[i].strftime("%Y-%m-%d"),
                    "returns": rets[i - MIN_CONTEXT:i + 1],
                }
                d = model.decide(ctx)
                rows.append({
                    "model": model.name, "arm": "masked", "asset": asset,
                    "action": d["action"], "stop_pct": d["stop_pct"],
                    "tp_pct": d["tp_pct"], "confidence": d["confidence"],
                    "context_end_date": ctx["date"],
                })
    return pd.DataFrame(rows)


def main():
    prices = load_all_prices()
    if not prices:
        print("No price data. Run scripts/pull_data.py first.")
        sys.exit(1)
    print(f"Universe loaded: {len(prices)} assets. Generating baseline bracket decisions…")
    t0 = time.time()
    decisions = run_baselines(prices)
    print(f"{len(decisions):,} decisions in {time.time() - t0:.1f}s. First-passage evaluation…")
    t0 = time.time()
    trades = evaluate_brackets(decisions, prices)
    print(f"evaluated in {time.time() - t0:.1f}s")

    overall = summarize_brackets(trades, by=["model"])
    print("\n=== E0 noise floor — bracket trades, net of costs ===")
    print(overall.to_string())
    print("\nHow to read: with 2σ stop / 4σ target, a RANDOM-WALK trader hits TP at "
          "tpBase% (≈ stop/(stop+tp) ≈ 33%).\nSkill = tpHit% vs tpBase%, not vs 50%. "
          "Net bps/trade for the random model ≈ pure cost drag — the bar to clear.")

    print("\n=== By asset group (momentum-20 and reversal-5) ===")
    sub = trades[trades["model"].isin(["momentum-20", "reversal-5"])]
    print(summarize_brackets(sub, by=["model", "group"]).to_string())

    print("\n=== Conditional split: after extreme 20d moves (H3 template) ===")
    print(summarize_brackets(trades[trades["model"] == "momentum-20"],
                             by=["model", "ret20_extreme"]).to_string())

    print("\n=== Direction diagnostic (secondary, fixed h=1, ignores brackets) ===")
    diag = evaluate(decisions, prices, horizon=1)
    print(summarize(diag, by=["model"])[["traded", "hit%", "bps/trade"]].to_string())

    DATA_RESULTS.mkdir(parents=True, exist_ok=True)
    overall.to_csv(DATA_RESULTS / "e0_baselines.csv")
    print(f"\nSaved: {DATA_RESULTS / 'e0_baselines.csv'}")


if __name__ == "__main__":
    main()
