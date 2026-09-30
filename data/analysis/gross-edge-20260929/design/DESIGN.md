# Fresh-target sample design

The frozen sample contains **125 calendar blocks × four assets = 500 snapshots**, ordered by one fixed random permutation with seed 2026092990. Every block includes SOL, BTC, ETH, and DOGE at the same UTC timestamp. No forward return, MA regime, or macro condition influenced sampling.

Existing canonical ledgers contain 436 unique SOL, 11 BTC, 12 ETH, and 7 DOGE entry times. These are 466 distinct calendar events. For old events, the exclusion audit conservatively retains 50 hours of chart/indicator history and 72 hours of outcomes. The recently completed 280-event study used a 24-hour maximum outcome interval. Applying every interval globally also excludes the BTC hedge paths evaluated at SOL event times.

A wholly disjoint old/new history-plus-outcome design can accommodate only 81 common four-asset blocks, or at most 324 snapshots. It cannot support 125 four-asset blocks. This count is retained as an alternative-design audit; no alternate sample is used for outcomes.

The agreed design instead requires that each new **six-hour forward target** avoid every old exposed history/outcome interval. Its 50-hour feature history may reuse already-known past observations, as in normal forecasting validation. This preserves new targets while acknowledging that not all input prices are unseen. New blocks remain at least 56 hours apart, so their own complete history-plus-target intervals are mutually disjoint.

Exact native data checks leave 42,567 candidate timestamps. A complete random-greedy pass could fit 360 blocks; the first 125 are frozen. Actual minimum separation is 86.75 hours. Selected blocks by year are 5, 24, 19, 19, 16, 24, and 18 for 2020–2026. All 58,250 new-target/old-interval comparisons are disjoint.

Every selected asset window has 200 contiguous 15-minute bars, 361 contiguous minute timestamps including the previous-minute entry close and six forward hours, finite positive well-formed OHLC, and valid prior-completed-UTC-day asset 50-day and BTC 200-day averages. Only data integrity and availability were checked in forward data; no future return was computed or scored. Source hashes and per-asset coverage counts are recorded in `fresh_blocks.json`.

The first selector attempt stopped before producing any sample because a pandas boolean array was read-only. The array was copied and the identical algorithm rerun. `selection_initial.log` preserves that failure; no outcomes or alternative seeds were examined.

## Inference implications

500 snapshots represent **125 calendar clusters**, not 500 independent market episodes. Assets share market exposure; use whole-block resampling and a whole-quarter regime sensitivity. Prior aggregate daily indicators and public/model-training knowledge cannot be made unseen by calendar exclusions. The sample is historical fresh-target validation rather than prospective live validation.

The new protocol's separate tests for gross profitability and AI selection are coherent. For the AI increment, recompute the price-only stratum means and selected-count weights in every block resample, and report sparse/all-selected strata. Split chronological halves/thirds by ordered calendar blocks so simultaneous assets cannot be separated across periods. The two primary strategies and their thresholds must stay fixed after outcomes are released.

The sample JSON uses explicit ISO UTC timestamps ending in `Z`. Native archive indices are timezone-naive UTC, so preparation must convert the timestamp to UTC and remove its timezone before indexing those files. Preserve the explicit timezone in external metadata.
