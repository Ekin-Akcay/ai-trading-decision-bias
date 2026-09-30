# Static review of two additional exploratory mechanisms

Reviewed both registered plans and implementations without optimizing or selecting their outcomes. Both mechanisms reuse already inspected historical windows and remain exploratory. The failed primary tests stay unchanged.

## BTC hedge

The accounting is consistent with fixed initial notionals: SOL sign times `(SOL return − beta × BTC return)`, less 20 basis points on each unit of active initial leg notional. Dividing the resulting gross and net amounts by `1 + abs(beta)` correctly expresses performance per total initial gross notional. A zero hedge weight incurs only the SOL leg cost.

The OLS slope uses 199 paired returns from 200 completed 15-minute closes ending at the original snapshot cutoff; neither confirmation prices nor later prices enter beta estimation. The slope is frozen and clipped as registered. Matching BTC/SOL close or open conventions correctly align the legs for immediate and confirmed entries.

Both reporting normalizations must be retained in the expanded search family. Fixed beta merely rescales returns, but variable OLS beta changes the relative weighting of trades under the two denominators. Selecting whichever normalization looks better without recording both would be additional search.

Requested coverage hardening: check finite, positive historical and required minute OHLC in addition to timestamp presence. The owner has confirmed the checks and correction of the one unnecessary extra future-minute coverage request. Counts remain 149 old and 280 fresh usable windows. The omitted old window `72c5a0798c` has a SOL history gap, and is omitted consistently across all hedge variants. All fresh windows pass the hardened coverage checks.

Funding, borrow, market impact, and inference latency remain unmodeled as declared. These omissions do not affect the algebra but limit a live-profitability interpretation.

## Stop-out fade

The first-exit function checks adverse/favorable opening gaps before within-minute extrema. Original TP-first cases do not trigger. An original SL-first case enters at the following minute's open after the entire trigger candle has completed. A trigger on original minute index zero therefore enters one minute after the original snapshot; a trigger on the final 240-minute waiting bar enters at minute 240.

The new trade follows the original AI direction and therefore opposes the hypothetical closing flow. Its 60/240-minute holding period includes the new entry minute; the longest case exits at elapsed minute 480. The ATR bracket uses pre-original-entry ATR and is recentered on the actual new entry. Only the new trade's return and cost are booked, which is correct for a strategy observing a hypothetical earlier trade rather than having held it.

The AI-width control retains model-supplied geometry and is correctly labeled as not AI-free. The ATR-width control changes triggering geometry and sometimes entry timing, so it cannot by itself isolate direction selection.

Two cautions were sent to root and the owner:

- Assert finite/positive source OHLC before scoring.
- Treating an original candle that touches both SL and TP as SL-first is adverse for the hypothetical original trade, but it can create additional profitable entries for a later fade. It is not automatically conservative for the new strategy. Preserve the registered primary convention, count these cases, and show their influence transparently; an exclusion sensitivity is descriptive, not a replacement winner.

The simulation measures a hypothetical stop-timing signal. No actual model trade was placed, so it does not establish that real retail liquidation flow caused subsequent prices.
