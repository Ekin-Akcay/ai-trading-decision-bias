#!/usr/bin/env python3
"""Pull Binance USDT-M perp klines (1h context + 5m evaluation bars) and
funding rates for the crypto sleeve. See src/nai/intraday.py."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nai.intraday import pull_funding, pull_intraday  # noqa: E402

DEFAULT_ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", nargs="*", default=DEFAULT_ASSETS)
    ap.add_argument("--intervals", nargs="*", default=["15m", "1m"])
    ap.add_argument("--no-funding", action="store_true")
    args = ap.parse_args()

    print(f"Pulling {args.intervals} perp klines for {args.assets} "
          f"(data.binance.vision bulk + fapi tail)…")
    summary = pull_intraday(args.assets, args.intervals)
    print(summary.to_string(index=False))

    if not args.no_funding:
        print("\nFunding rates:")
        for note in pull_funding(args.assets):
            print(f"  {note}")


if __name__ == "__main__":
    main()
