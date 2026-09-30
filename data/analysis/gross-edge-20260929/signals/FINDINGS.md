# One gross-return long candidate for a fresh test

**Recommend candidate048 as the single long primary to freeze next.** It is the most defensible simple long hypothesis in these existing results when fees are set to zero. All430 windows are now discovery, so the statistics below support further testing, not a new validation claim.

Exact rule: at the decision time, use only the previous completed UTC day's asset close and its trailing50-day SMA, and BTC's previous completed close and trailing200-day SMA. When both closes are at or below their respective averages and Terra predicts SHORT, enter LONG at the first1-minute open after the visible15-minute candle closes. Hold240minutes, exiting at the elapsed240-minute close. No stop, target, confidence threshold, intraday-MA gate, confirmation wait or reasoning-text filter. Otherwise skip. Current evidence is SOL only. Applying asset50DMA/BTC200DMA to other assets is an explicit new transport hypothesis; for BTC itself this means BTC is below both its50DMA and200DMA.

## Existing evidence, zero fees

| Sample | Executed / opportunities | Mean gross/trade | Ordinary95% interval | Calendar-quarter95% interval |
|---|---:|---:|---:|---:|
| Original discovery |22/150(14.7%)|+0.2116%|−0.5464% to+0.9780%|−0.3862% to+0.8937%|
| Later reused sample |65/280(23.2%)|+0.5351%|+0.0651% to+1.0420%|+0.2208% to+0.9518%|
| Combined discovery |87/430(20.2%)|+0.4533%|+0.0517% to+0.8783%|+0.1932% to+0.7731%|

Combined gross win rate is46/87=52.9%, median trade+0.1981%, and gross profit factor1.953. The later sample has34/65gross winners(52.3%) and profit factor2.244. The attraction is the payoff distribution, not an unusually high hit rate. These are simple unlevered per-trade percentages, not compounded portfolio returns.

The later65-trade chronological thirds are **+1.0435%,+0.3867%,+0.1581%**. Removing its largest1/3/5winners leaves+0.4187%/+0.2461%/+0.1015% per trade. Dropping any one of its calendar quarters leaves a mean of at least+0.4434%. Combined trades span14quarters,11 with positive means. This is broader than one isolated profitable episode.

However, the original22 observations are weak: one chronological half is negative, the middle third is negative, its ordinary and quarter intervals include zero, and removing its top3 winners produces−0.2242%. The combined2023 slice is negative(6trades,−0.1781%), and2024 is barely positive(8trades,+0.0597%). Macro regimes cluster in time; counting87trades as87 fully independent regimes would overstate the evidence. The strategy was also selected after a broad historical search.

## Does the AI add information beyond the macro gate?

| Rule, same immediate entry/240m hold | Original mean gross | Later mean gross | Combined mean gross |
|---|---:|---:|---:|
| Daily macro gate + AI SHORT → LONG |+0.2116%|+0.5351%|+0.4533%|
| Same daily gate, LONG regardless of AI |+0.0908%|+0.1853%|+0.1540%|
| Same daily gate, LONG only when AI LONG |−0.0198%|−0.6269%|−0.3467%|
| Same daily gate + price below intradayMA20, no AI |−0.0709%|+0.3515%|+0.2425%|

The later selected mean exceeds the daily-only baseline by+0.3498percentagepoints; its ordinary paired-window bootstrap interval is+0.0165to+0.7311. The advantage over the additional simple intraday-MA20 price filter is only+0.1836points, with an interval spanning zero(−0.3249to+0.8308). Thus the AI may provide some useful selection, but its incremental value over known price patterns remains uncertain.

An exploratory action-label permutation within nine fixed era×intraday-MA strata gives one-sided p≈0.0276 for the later cohort and0.0346 pooled. These values are **not corrected for the earlier search and are not independent confirmation**. They justify measuring AI contribution carefully in the fresh protocol, not claiming it is already established.

## Why this candidate rather than the other long rules?

Ungated AI-SHORT→LONG240m averages+0.30796% gross in the later189trades, but its ordinary and quarter intervals include zero. The previous confirmed-L rule(wait15m positive confirmation, thenLONG240m) averages+0.21507% gross in85later trades, with a wide interval crossing zero and a negative mean after removing its best3winners. The registered stop-out-fade leaders remain negative in the original sample even at zero fees. Earlier delayed-invalidation alternatives also provide no clearer simple long candidate with matching stability. Their complete gross re-expressions are retained beside this note.

Do not add another long finalist or tune these thresholds on the forthcoming sample. Freeze the exact rule, compare it with both daily-only and daily+intraday-MA20 price controls, and test on fresh calendar blocks across the selected assets. Group uncertainty by calendar block because simultaneous crypto observations are correlated. Original-close availability and actual model latency are different assumptions; preserve the declared entry convention and fixed delayed-entry sensitivities in the fresh protocol. All prior fee-adjusted failures remain valid under their original assumptions and have not been overwritten.
