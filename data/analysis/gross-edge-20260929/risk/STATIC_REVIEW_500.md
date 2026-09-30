# Static S508 review for the new 500-snapshot run

Run: `gross-edge-500-20260929T204545Z`. This review and synthetic checks do not inspect new forward prices. Await explicit root unseal and `ALLOW_EVALUATION` before native replay.

The new evaluator matches the frozen S508 contract: original-close entry; above-both MA gate and Terra LONG selection; stop=target=2×pre-entry ATR14%; minute first passage; timeout at index240; delayed opens at indices2/6 with brackets re-centered and the same original timeout. The mirrored long control replays its own bracket. Eligible price-only controls reuse identical execution without the AI filter.

Calendar blocks are resampled as whole four-asset groups. The observed standardized price-only baseline weights each eligible asset/era/MA stratum by its selected count. A separate design worker handles statistical-inference review; the prepared risk audit independently reproduces the observed baseline and difference.

A diagnostic issue was caught and fixed before evaluation: MFE/MAE now include entry, keeping MFE>=0 and MAE<=0 when a gap places the entire exit bar on one side of the original close. This never changed returns. Root explicitly retains the inclusive below-both regime convention, with above-both classification evaluated first; the audit matches that declared convention.

## Prepared independent audit

`independent_s508_audit.py` requires all of:

1. Root explicitly supplies `--release gross-edge-500-20260929T204545Z`.
2. The matching run has `ALLOW_EVALUATION`.
3. Exactly500 unique accepted decisions pass the isolation audit.

Only then does it read new prices. It independently checks all500 windows, primary short plus1/5-minute delays and mirrored long (2,000 native scalar replays), the pre-entry ATR/MA features, native minute clocks, all root trade outcomes, scheduled moves, extrema, controls, chronological/asset summaries, and observed standardized AI increments. Results will be written only under this risk folder.

Nine synthetic tests already passed, covering long/short simultaneous touches, both gap directions, target caps, ignored pre-entry extremes, delayed re-centering, entry-minute stops and fixed timeout clocks. These tests used invented OHLC only. The native checker has not been released or run against the new sample.
