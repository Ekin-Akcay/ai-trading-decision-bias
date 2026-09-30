# Retrospective exit-policy study — frozen before policy results

Created 2026-09-29. This is exploratory reuse of the same 100 SOL windows, not an independent confirmation sample. All 1,000 comparable decisions (five models, v1 and v2) are included. Flat decisions remain zero-return, zero-cost decisions.

## Fixed grid

Primary pure time exits: 15, 30 and 105 minutes (1, 2 and 7 context candles). Secondary: 5, 60 and 240 minutes. Ignore original brackets for these policies.

Primary bracket comparisons: scale both original stop and target distances by 0.75, 0.50 and 0.25; baseline scale 1.00. Preserve original direction, entry and 72-hour timeout. No geometry re-optimization; v2 stays 2:1.

Secondary combinations: all four scales with time caps 15, 30 and 105 minutes. Secondary direction reversal for all six pure time horizons. Simple always-short, MA20 and visible-momentum baselines for each pure time horizon, using each original decision's active/flat mask for paired fairness.

UTC entry-session summaries (00–06, 06–12, 12–18, 18–24) are descriptive, not tuned filters.

## Engine and costs

Use existing nai.backtest._scan_bracket on native 1-minute OHLC, with entry at the last visible 15-minute candle's close. Gap fills use open; two levels touched within the same 1-minute bar without decisive open are ambiguous. Never assume target-first. Scale 1 must reproduce every original recorded decision before proceeding. Check complete 72-hour future minute coverage for every window.

Gross and net returns are percent of entry not risk-normalized; fixed 20-basis-point round-trip cost for every active trade. No leverage, sizing, funding or market-impact assumptions are introduced. Shrinking brackets increases the fee burden relative to distance. Original flat decisions pay no cost. These are separate trades, not a portfolio equity curve.

## Statistics and uncertainty

Primary unit is market window: average the ten decisions within each of 100 windows, then average windows. Ten AI decisions on the same path are not ten independent samples. Bootstrap whole windows (10,000 resamples, fixed seed 20260929), report 95% intervals. Paired policy-minus-original comparisons include only decision pairs with unambiguous known outcomes for BOTH policies; report count and lower/upper bounds retaining all decisions by assigning ambiguous outcomes to SL/TP respectively.

Primary significance family: six pooled paired contrasts (three time exits and three bracket reductions). Secondary pooled family: other time exits and all combined policies. Each family uses two-sided window sign-flip permutation p-values and Benjamini–Hochberg adjustment. Benchmark/reversal time-policy contrasts are a separate exploratory family; none establishes independent confirmation. Per-model/protocol tables and chronological-half summaries are descriptive with bootstrap intervals. Report all grid cells; do not select and test a winner after inspection.

Window independence is imperfect: overlapping events exist. Include a sensitivity bootstrap using groups whose consecutive entry times are at most 72 hours apart; keep the chronological halves descriptive. Costs and ambiguous outcomes are explicit.

## Deliverables

Per-decision policy rows, complete grouped policy tables, paired tests, benchmark and session summaries, reproducible script, audit, scientific charts, FINDINGS.md and a standalone local HTML report. No changes to original source files or decision ledgers.

## Implementation clarification and requested appendix

The rounded visible-momentum input equals zero on one canonical window. The momentum benchmark abstains there; its paired comparison excludes that window from BOTH sides, retaining 99 common windows. Other baselines retain the full active/flat mask. This handles an undefined direction without assigning a post-outcome tie-break.

After pooled results were inspected, the user-facing coordinator requested a **post-hoc descriptive appendix**: primary 15/30/105-minute exits and original/75%/50%/25% brackets by pre-entry MA regime and original long/short direction. Report all cells, counts, gross and net; no significance claims or selected filter. These strata do not constitute a new independent test.

A final requested **post-hoc risk-normalization diagnostic** reports gross R, fee R and net R for every bracket scale, separately for v1/v2, using scaled stop distance as the denominator. Active unambiguous rows only; counts, protocol-specific target-hit rates and supplemental equal-window means are shown. It is descriptive unit normalization, not a sizing/leverage policy or a new significance test. Lower percentage returns alone do not imply weaker directional expectancy when risk width also shrinks.
