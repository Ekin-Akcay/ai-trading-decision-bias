# Conditional reversal entry discovery

This study searched116 prewritten candidates on150 historical Terra decisions already available to the project. It found two policies that met the deliberately simple discovery screen, **not a verified profitable strategy**. All candidates, including failures, remain in `candidate_results.csv` and JSON. No new model calls were made.

## Best long candidate to validate

Terra predicts SHORT at t0. Wait for the first completed15-minute candle. If its close is strictly above the t0 price, enter LONG at the next1-minute open (t0+15minutes). Exit at the close exactly240minutes after actual entry. Otherwise skip. Use no MA, daily regime, confidence, stop or reason filter. Charge20bps roundtrip. This is candidate `006_long_none_confirm15_hold240`.

The32 discovery trades averaged **+0.4640% gross and+0.2640% net**, with17 gross winners (53.1%) and15 net winners (46.9%). The mean net95% bootstrap interval is **−0.5245% to+1.1000%**. This wide interval includes substantial losses.

| Slice | Trades | Mean net/trade |
|---|---:|---:|
| Earlier chronological half |16|+0.4117%|
| Later chronological half |16|+0.1164%|
| Original100 windows |27|+0.2073%|
| New above-both-MA50 windows |5|+0.5703%|
| Same price confirmation and240m LONG, ignoring AI |62|+0.1260%|
| Confirmation control when AI predicted LONG |30|−0.0212%|

The AI-selected mean exceeds the all-confirmation baseline by0.1380percentagepoints per trade. The unchanged AI SHORT on precisely these selected holding intervals instead averages−0.6640% net. Neither comparison proves incremental predictive skill because this policy was selected from116 alternatives on the same observations.

**Tail concentration is a serious limitation.** Removing the largest winner leaves+0.0211% net; removing the largest two yields−0.0904%. The new50 subgroup has five trades but just one net winner: a+7.7943% net move on2021-01-12. Without that trade the subgroup averages−1.2356% net. Positive source and chronological means therefore provide only a weak screening signal. Year slices also vary:2023 and2026 are negative.

## Second candidate, weaker AI contribution

Terra predicts LONG while price is at/above both MA20/MA50 at t0. If the completed first15-minute candle closes strictly below t0 price, enter SHORT at the next1-minute open. Exit105minutes after actual entry. Charge20bps. Candidate `068_short_above_both_confirm15_hold105`.

The39 trades average+0.3054% gross, **+0.1054% net**, with22 gross winners(56.4%) and19 net winners(48.7%). Net95% interval is−0.3766% to+0.5922%. Earlier/later chronological means are+0.2087%/+0.0073%; original100/new50 means+0.2157%/+0.0287%.

Its44-trade no-AI market/confirmation baseline already returns+0.0801% net. The AI selection contribution is only+0.0253percentagepoints. Removing the two best trades yields−0.0576% net. This is less compelling as an AI-dependent strategy than the long candidate.

## Implication and validation requirements

The mechanism worth testing is **reverse only after price contradicts the initial AI direction**, rather than instantly reversing every prediction. The candidate did not achieve profitability by a high net win rate: its net hit rate is below50%, and the observed positive expectation comes from the size of winners. Conversely, the user's previous57% gross win rate could lose money when losses are larger and costs consume the margin.

Freeze the exact long candidate before fresh model decisions. On new random eligible archive windows, report all triggered trades,20bps costs, confidence intervals, the identical no-AI confirmation baseline, and the opposite-direction control. Preserve the holdout even if it loses; do not repeatedly alter policies until a historical winner appears. This discovery study is not a future live test, has small selected groups and unequal source sampling, and ignores funding, borrow and additional slippage.

The source hashes and coverage checks are in `validation.json`; independent raw15-minute replay, MA recomputation, prior-day daily-data checks and candidate count/mean checks are in `independent_validation.json`. Raw per-policy selected trades are in `selected_trades.csv`, with all eligible no-AI control trades in `control_trades.csv`.
