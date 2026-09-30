#!/usr/bin/env python3
"""Pull/refresh daily OHLCV for the whole universe into data/raw/."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nai.data import pull_all  # noqa: E402


def main():
    force = "--force" in sys.argv
    print("Pulling universe (yfinance primary, stooq/binance fallback)…")
    summary = pull_all(force=force)
    print(summary.to_string(index=False))
    failed = summary[summary["rows"] == 0]
    if not failed.empty:
        print(f"\n{len(failed)} asset(s) failed — see messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
