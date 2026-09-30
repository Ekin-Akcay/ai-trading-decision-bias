# Frozen discovery grid — risk exits

Written before calculating this grid on 2026-09-29. All existing 100 v2 Terra windows and the latest 50 Terra windows are DISCOVERY data, including the latest 50 because their outcomes have already been seen. No claims of independently verified profit will be made from this search. No new model calls are authorized to this worker.

## Data, clocks, costs

Each unique SOL window is one observation. Entry is the last visible 15-minute candle close. Scan subsequent native one-minute bars. Stop/target first passage is path-dependent; do not clip terminal returns to pretend a stop. Gaps beyond a stop fill at the adverse opening price. Favorable gaps are conservatively capped at the target. When both levels are touched within a minute and the opening price has not crossed either, assume stop first. Close any remaining position at the stated fixed clock horizon. A 20 bp roundtrip charge applies to every trade. Funding and latency are not part of this first grid; top candidates get 1/5 minute delayed-open sensitivity and 30 bp cost sensitivity.

## Finite grid

* Time horizons: 15, 30, 60, 105, 240, 720, 1440, 4320 minutes.
* Time exits without brackets at each horizon.
* Fixed stop percentage: 0.35, 0.50, 0.75, 1.0, 1.5, 2.0.
* ATR14 stop multiples: 0.50, 0.75, 1.0, 1.5, 2.0, 3.0 (ATR is the pre-entry 15-minute value).
* Original AI stop multiples: 0.50, 0.75, 1.0, 1.5, 2.0.
* For each stop, target/stop ratios: 0.5, 0.75, 1, 1.5, 2, 3.
* These are 824 exit policies: 8 pure time exits plus 17 × 6 × 8 brackets.
* Gate strata: all windows, above both MA20/MA50, below both MA20/MA50. Mixed-MA windows remain in all only.
* Direction strategies within each gate: reverse either AI decision; only reverse AI long into short; only reverse AI short into long.
* Baselines: always long and always short on every eligible gate window with identical exits. Agent-stop baselines still depend on AI sizing and are explicitly not a no-AI control.

## Reporting and candidate ranking

Save every window-policy-direction result and every group summary. Show pooled and original100/latest50 source-batch statistics, earlier/later chronological halves, net win rate, mean/median, profit factor, ambiguity/gap counts, and both sides independently. Primary candidate minimum support: at least 20 executed windows, each chronological half at least 10. Favor positive net average in both halves and both source batches where each has at least 5 observations, and broad neighboring parameter support. Selection is exploratory even when these conditions hold. At most two fixed policies will be proposed for new data. Provide simpler no-AI comparison and 1/5 minute entry delay sensitivity for those candidates. No p values or confidence-interval claims that ignore this search.
