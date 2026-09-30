# Exploratory reuse of280 windows: unchanged116 entry/filter policies

**No candidate passes the declared robustness screen. None of the116 nominal95% net-mean bootstrap intervals has a lower bound above zero, even before correcting for the search.** This stage reuses the280-window data after the two primary results were inspected; it is not independent confirmation. The failed primary findings remain unchanged.

All116 original candidate definitions were applied without new gates, thresholds, horizons or model calls.45 candidates have a positive net point estimate;19 of those have at least40 fresh and20 original trades. Their uncertainty, period instability or dependence on large winners prevents a verified-profit claim.

## Strongest long lead, still unverified

Candidate `048_long_both_down_confirm0_hold240`: Terra predicts SHORT, the previous completed UTC daily SOL close is below its50-day average, and BTC close is below its200-day average. Buy at the next1-minute open immediately after the original visible close; exit240minutes later. No confidence filter, confirmation wait, stop or target.

| Measure | Result |
|---|---:|
| Original discovery trades |22|
| Original mean net,20bps |+0.0116%|
| Fresh reused trades |65|
| Fresh mean gross |+0.5351%|
| Fresh mean net,20bps |+0.3351%|
| Fresh mean net,30bps |+0.2351%|
| Fresh gross / net winners |34/65 /32/65|
| Fresh profit factor after costs |1.637|
| Fresh nominal95% net-mean interval |−0.1318% to+0.8311%|
| No-AI same daily gate/time LONG baseline |93 trades,−0.0147% net|
| Selected mean minus no-AI baseline |+0.3498 percentagepoints|
| Fresh net after removing best3 trades |+0.0461%|

Its chronological halves are positive(+0.5240%,+0.1519%), but thirds are+0.8435%,+0.1867%,**−0.0419%**. The original22-trade result is near break-even and becomes−0.1424% after removing its largest winner. The latest period and uncertainty therefore fail to support a robust strategy. Selecting this policy now is further discovery, not retroactive success in the locked test.

## Other adequate-size examples

| Unchanged candidate | Fresh trades | Fresh net | Original net | Main failures |
|---|---:|---:|---:|---|
| AI LONG reversed SHORT, both daily trends up, immediate105m |43|+0.2560%|−0.2406%|Original losses; last third negative; interval crosses zero|
| AI LONG reversed SHORT after30m negative confirmation,105m hold |44|+0.1082%|+0.1217%|Later half negative; best3 removal negative; interval crosses zero|
| Locked L: AI SHORT reversed LONG after15m positive confirmation,240m hold |85|+0.0151%|+0.2640%|30bps negative; later half negative; tail sensitivity; interval crosses zero|

These examples illustrate why positive net averages are not sufficient after a large search. The dataset offers research leads, but no entry-only candidate here warrants calling the strategy profitable or using the remaining20 model calls as if they could provide strong standalone confirmation.

## Reproducibility

- `candidate_results.csv` and JSON retain all116 outcomes, original150 comparisons, no-AI controls, halves/thirds, fees and tail sensitivities.
- `all_candidate_arrays.npz` contains116×280 matrices of `gross_pct`, `net20_pct`, `selected` and `no_AI_eligible`, with candidate/case/window/time coordinates for root's common-window search correction.
- `all_candidate_windows.csv.gz` contains every one of32,480 candidate/window rows, including skipped opportunities and explicit masks. Hypothetical returns on skipped rows are not executed profits.
- `audit.json` records frozen-definition/source hashes, zero new model calls,840 independent native15m entry checks and2,520 exit checks. All passed.

Intervals are descriptive and unadjusted. Historical archive data, shared market regimes, unequal original sampling and already-inspected validation data constrain interpretation. No live trading or portfolio-return claim is made.
