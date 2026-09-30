# Exploratory L048 horizon diagnostic

This bounded diagnostic is specified after the 500-window primary results were unsealed. It cannot change the frozen 240-minute L048 rule or its failed primary verification. No model calls, ATR sizing changes, filters, confirmation delays or stop/target searches are permitted here.

Replay native one-minute opens/closes at exactly 15, 30, 60, 105 and 240 elapsed minutes. Entry is the first minute open after the visible chart ends; a horizon h exits at the close of the minute whose open is t0+h-1 minutes. Returns are gross percentages with zero costs, on equal position notional. The original completed-daily macro gate and AI SHORT condition remain unchanged.

Analyze old150 SOL, new280 SOL, the new500 four-asset sample, and its SOL/BTC/ETH/DOGE subsets. Compare the L048 subset against macro-gated longs without AI, its AI-LONG complement, and the already-used macro+below-MA20 price control. Preserve the original below-MA20 predicate (>100 for old430; >=100 for fresh500) and report any equality cases. Do not choose a winner among horizons.

For all five horizons report count/frequency, mean, median, wins, gross gain/loss ratio, chronological halves/thirds split on all sample calendar blocks, per-asset results, leave-one-quarter-out, removal of largest 1/3 trades and largest 1/3 calendar blocks. Calendar block bootstrap and quarter bootstrap intervals are descriptive, not new validation tests; use 20,000 whole-group resamples with fixed seeds 2026093011/2026093012. Standardize no-AI controls to selected asset × era × MA regime strata using the frozen definitions.

Inspect the five-point trajectory of selected trades, the contribution of each time segment, and early behavior with the same top three 240-minute trades removed. Label that last removal explicitly as hindsight sensitivity, not a tradable filter. Save complete per-window vectors, summaries, source hashes and numerical reconciliation with old discovery and fresh primary 240-minute results. Explain whether the early-movement mechanism is consistent across samples or whether the mean is primarily a late/outlier contribution. All outputs stay in this folder.
