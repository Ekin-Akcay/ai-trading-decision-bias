# L048 five-horizon diagnostic

The early-reversal explanation does not reproduce consistently. The newer 280 SOL windows showed progressively positive moves, but the fresh 500-window test was approximately flat after 15–30 minutes and negative after 60 minutes. Its positive four-hour mean largely arrives later and depends on a few correlated market episodes. Shortening the exit does not resolve that problem. I would not use the remaining calls to validate a shorter version of the same rule based on this profile.

This is an **exploratory diagnostic after the primary outcome inspection**, not untouched validation. The frozen 240-minute L048 rule and its failed verification remain unchanged. No model calls, sizing changes, thresholds or horizon searches beyond the five requested times were made.

## Identical entries, five fixed exits

L048 buys at the first native minute open after the model's visible chart ends when the model says SHORT and both original completed-daily macro conditions are bearish. Each row below uses the same selected trades at every horizon. Returns are percentages per trade with equal position notional and zero fees. The fresh 500 windows contain four assets at 125 calendar timestamps; the 101 selected trades occupy only 38 timestamps.

| Sample | Trades | 15m | 30m | 60m | 105m | 240m |
|---|---:|---:|---:|---:|---:|---:|
| Original 150 SOL | 22 | −0.062 | −0.010 | +0.177 | +0.147 | +0.212 |
| Next 280 SOL | 65 | +0.044 | +0.093 | +0.231 | +0.445 | +0.535 |
| Fresh 500, four assets | 101 | +0.001 | +0.029 | −0.046 | +0.161 | +0.361 |
| Fresh SOL subset | 24 | −0.011 | +0.077 | +0.277 | +0.677 | +0.890 |

The fresh pooled median is −0.013%, −0.016%, −0.059%, +0.003% and +0.007% respectively. Every horizon's fresh whole-calendar-block 95% bootstrap interval for the mean includes zero. The same is true with whole-quarter resampling. These intervals are descriptive and do not correct for the entire historical research search.

## Tail and episode dependence

The fresh sample contributes −0.046 percentage points by minute 60, then +0.207 points from minutes 60–105 and +0.200 points from minutes 105–240. It is not a consistent immediate bounce against the AI's bearish opinion.

The three largest individual four-hour gains supply **80.1% of the summed four-hour trade returns**. Removing those same three trades at all horizons leaves fresh means of −0.018%, −0.005%, −0.151%, +0.021% and +0.074%. This is a hindsight sensitivity, not an executable filter.

At the relevant dependence level, the three largest calendar blocks supply **131.0% of the summed four-hour trade returns**. Removing all selected assets in those three episodes leaves **−0.127% per trade at 240 minutes**. The episodes are 2024-08-07 22:30 UTC, 2022-12-29 21:45 UTC and 2022-06-13 16:45 UTC, four selected assets each. Trade-percentage sums here measure contribution and are not compounded portfolio returns.

Fresh SOL's +0.890% four-hour mean becomes −0.239% after removing its three biggest gains. Removing the three biggest gains separately within BTC, ETH or DOGE also leaves each asset's four-hour mean negative. Consequently, the large SOL point estimate does not establish an independent, broadly distributed SOL edge.

The original 150 windows' four-hour +0.212% similarly becomes −0.224% after their three largest gains. The next 280 windows are the exception: their +0.535% remains +0.246% without their three biggest gains, and their earlier 60–105-minute movement is stronger. That favorable sample-specific pattern does not reproduce in the subsequent test.

## Price-only controls and chronology

| Fresh500 policy | Trades | 15m | 30m | 60m | 105m | 240m |
|---|---:|---:|---:|---:|---:|---:|
| L048, AI SHORT selected | 101 | +0.001 | +0.029 | −0.046 | +0.161 | +0.361 |
| Same macro gate, no AI | 149 | +0.038 | +0.040 | +0.009 | +0.148 | +0.297 |
| Same macro gate, AI LONG complement | 48 | +0.116 | +0.064 | +0.124 | +0.122 | +0.164 |
| Existing macro + below-MA20 control | 68 | +0.014 | +0.141 | +0.050 | +0.275 | +0.725 |

The selection advantage is much smaller after standardizing the no-AI control to the selected asset × era × MA-regime composition. At 15/30/60/105/240 minutes, fresh AI increments are **−0.012/−0.022/−0.009/+0.020/+0.021 percentage points**. Every corresponding whole-block 95% interval includes zero. At 240 minutes, the standardized price baseline is +0.340%, versus L048's +0.361%. The stronger below-MA20 control is reported because it was already prescribed; this result does not promote it to a new validated strategy.

The standardized AI increment is negative at all five horizons in old150, positive at all five in new280, and mixed in fresh500. Identifying variation is limited: only 2, 4 and 11 macro-eligible asset/era/MA strata respectively contain both AI-selected and complementary observations.

The fresh chronological halves are both positive only at 105 and 240 minutes. At 60 minutes both halves are negative. The latest chronological third is −0.055%, +0.005%, −0.271%, −0.119% and −0.171% across the five horizons. Thus neither the earliest exits nor the later positive pooled means are stable across the fixed calendar partitions. All partitions are computed on the full sample's calendar blocks, preserving simultaneous assets; old discovery reports that split only selected trade counts may show different partition values.

## Verification and files

All 930 original windows were replayed directly from native minute opens/closes, with 241 contiguous positive finite observations per window and the last visible close verified. A horizon h exits at the close of the minute opened at t0+h−1. All original four-hour means and selected counts reconcile. A further 2,930 per-window comparisons against the original 430 discovery returns and all five fresh500 diagnostic horizons agree within 4.45×10⁻¹⁶ percentage points. No MA20-equality case changes the old/new below-MA20 control predicate.

Reproduce with `run.py`, then `finish.py`. `PLAN.md` records the finite diagnostic before computation; `audit.json` records checks and source hashes. Complete returns and masks are in `window_vectors.csv` and `window_vectors.npz`. `all_profiles.csv`, `chronological_splits.csv`, `descriptive_inference.csv`, `fixed_240_tail_sensitivity.csv`, `time_segment_contributions.csv`, `largest_240_trades.csv` and `fresh500_selected_block_returns.csv` retain the full analysis. `horizon_profile.png` visualizes the five fixed horizons and the same-three-winner sensitivity.
