#!/usr/bin/env python3
"""Weekly evaluation: resolve all live harvested bracket trades by first
passage and print the metric battery, per timeframe sleeve. Open (unresolved)
trades are counted, not scored. See docs/03-workflows.md cadence."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd                                     # noqa: E402

from nai.backtest import evaluate_brackets              # noqa: E402
from nai.config import DATA_DECISIONS                   # noqa: E402
from nai.data import load_all_prices                    # noqa: E402
from nai.decisions import read_records                  # noqa: E402
from nai.intraday import load_intraday                  # noqa: E402
from nai.metrics import consensus_frame, summarize_brackets  # noqa: E402

CRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"]
TIME_STOP_H = 72


def battery(trades: pd.DataFrame, bpd: float, label: str):
    n_open = int((trades["outcome"] == "open").sum())
    print(f"--- {label}: {len(trades)} evaluable, {n_open} still open ---")
    for title, by in [("by model × arm", ["model", "arm"]),
                      ("by asset", ["model", "asset"]),
                      ("extreme trailing moves (H3)", ["model", "ret20_extreme"])]:
        t = summarize_brackets(trades, by=by, bars_per_day=bpd)
        if not t.empty:
            print(f"=== {label} — {title} ===")
            print(t.to_string(), "\n")
    conf = trades[trades["sign"] != 0].copy()
    if not conf.empty:
        conf["conf_bucket"] = pd.cut(conf["confidence"], (0.0, 0.5, 0.7, 1.01),
                                     right=False, labels=["<0.5", "0.5-0.7", ">=0.7"])
        print(f"=== {label} — calibration (H4) ===")
        print(summarize_brackets(conf, by=["model", "conf_bucket"],
                                 bars_per_day=bpd).to_string(), "\n")


def main():
    decisions = read_records(sorted((DATA_DECISIONS / "live").glob("*.jsonl")))
    if decisions.empty:
        print("No live decisions harvested yet — run the harvest scripts daily.")
        return
    if "timeframe" not in decisions:
        decisions["timeframe"] = "1d"
    decisions["timeframe"] = decisions["timeframe"].fillna("1d")
    print(f"{len(decisions)} decisions logged "
          f"({decisions['timeframe'].value_counts().to_dict()})\n")

    d15 = decisions[decisions["timeframe"] == "15m"]
    if not d15.empty:
        ctx = {a: load_intraday(a, "15m") for a in CRYPTO}
        ev = {a: load_intraday(a, "1m") for a in CRYPTO}
        trades = evaluate_brackets(d15, ctx, eval_prices=ev, context_bar_minutes=15,
                                   max_bars=TIME_STOP_H * 60)
        if not trades.empty:
            battery(trades, bpd=1440, label="15m crypto sleeve")

    d1 = decisions[decisions["timeframe"] == "1d"]
    if not d1.empty:
        trades = evaluate_brackets(d1, load_all_prices())
        if not trades.empty:
            battery(trades, bpd=1, label="daily control sleeve")

    cons = consensus_frame(decisions)
    if not cons.empty:
        print("=== Consensus/dispersion coverage (E4/E8 feedstock) ===")
        print(cons.describe().round(3).to_string())


if __name__ == "__main__":
    main()
