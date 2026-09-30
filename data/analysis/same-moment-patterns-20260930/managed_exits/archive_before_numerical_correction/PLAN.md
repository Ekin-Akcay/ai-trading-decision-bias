# Managed exits on existing AI moments: finite discovery plan

This study asks whether reversing an already-recorded AI trade produces favorable excursions that an executable protection rule can retain. It is an **exit-management extension**, not a new informational signal or a fresh validation sample. Use only the1,020 existing primary Terra MA-present windows and their original timestamps from `new-angles-20260930/target_exhaustion/windows.csv` and `paths.npz`; use MA_A only for paired90. No new model/API/trade-snapshot calls, new timestamps, refits, entry filters or exit grids. Preserve all29 remaining snapshot credits.

## Fixed entry, three candidates and two controls

Every policy reverses the existing AI direction. Enter at the first native minute open immediately after the chart ends. The risk unit A is the original pre-entry ATR14 percentage, applied to this actual entry price. Use a single fixed240-minute cap and zero costs. Position notional is1; no volatility rescaling or extra leverage.

Three candidate policies are frozen before scoring:

1. **BE_after_1ATR:** initial stop at−1A. Once a completed minute reaches+1A favorable excursion, move the stop to entry, effective from the next minute. Keep that stop until exit or the240-minute cap.
2. **TRAIL_1ATR_after_1ATR:** initial stop at−1A. After a completed minute reaches+1A, ratchet the stop to the best completed-bar favorable excursion minus1A, never loosening it. Each new stop is effective only from the next minute. This includes breakeven when the high-water mark first reaches exactly1A.
3. **HALF_at_1ATR_then_BE:** initial stop at−1A. Close exactly half the original position at+1A. Move the remainder's stop to entry from the next minute, with the original240-minute cap for anything left. This tests cash realization of the first favorable move, not another optimized target ladder.

Controls have the identical entry, AI-reversed side, size and240-minute clock: **FIXED_1ATR_stop**, initial−1A stop with no take profit; and **RAW_hold_240**, no stop or take profit. No following-AI, side-only or alternative ATR geometry is promoted as an extra candidate. Matched differences isolate the incremental effect of the exit policy on these same entries; they do not establish that AI contributes information beyond price-only entries.

## Causal minute ordering and conservative fills

Use native OHLC bars, including the entry minute. Maintain favorable/adverse price moves in side-adjusted percentage points relative to actual entry. For a long, favorable uses high and adverse uses low; for a short these reverse. Do not activate a stop using the current minute's high before its low can occur.

At each minute:

1. The only active stop is the initial stop or an update from a previous completed minute. If the open has crossed it adversely, fill remaining size at the actual open. Losses are not capped at the stop after a gap. A gap is strictly beyond the stop; equality fills the stop price.
2. For the partial policy only, if the open is at or beyond its unfilled+1A target, execute the half-target at the target price (favorable gaps are capped). That open execution precedes any later intraminute stop. The remainder still has its old stop during this minute.
3. Check whether the minute's adverse extreme touches the still-active stop. Exit all remaining size at the stop. If an unfilled partial target and stop both touch inside the same minute without a favorable target gap at open, assume stop first and execute no target. Record that genuine target/stop ambiguity. Separately record cases where a protection trigger and stop share a bar; next-minute activation makes those stop executions unambiguous under the fixed policy.
4. If the position survives and the partial target has not filled, execute its half-target if touched at+1A. No current-minute breakeven stop is introduced.
5. Only after all current-minute executions, update completed-bar favorable high-water marks and calculate any breakeven/trailing stop for the next minute. If this is minute240, close remaining size at that minute's close; a newly proposed stop has no opportunity to execute.

A partial target at open followed by an old-stop touch in the same bar yields half at target and half at the old stop. A stop gap can occur below/above a newly activated breakeven/trailing level on the following bar and fills the actual open. Store actual stop levels, target events, remaining fractions, gap flags and within-minute ambiguity. Final minute indices are bar-resolution timestamps, not invented tick-level execution times.

## Fixed analysis and interpretation

Retain every policy's per-window gross return, initial risk unit, entry/exit details, partial realization, time held, protection activation and gap/ambiguity status. Report all three candidates and both controls regardless of performance.

Report pooled equal-notional trade results and original cohorts (original100,next50,next280,multi500,paired90), plus all assets and the AI-reversed long/short decomposition. Show calendar halves/thirds, five contiguous calendar folds, yearly/quarterly means, counts and activity, positive/zero/negative trade rates, payoff sizes, worst trade, largest1/3winner sensitivity, and leave-one-quarter-out. Split chronology on whole original entry-time blocks so simultaneous assets never straddle a split. The sample contains uneven asset and cohort counts; pooled means are not a balanced four-asset strategy portfolio.

For each candidate, report paired per-window differences versus both matched controls. Use20,000 whole-entry-time-block bootstrap draws with seed2026093041 and whole-quarter draws with seed2026093042, recomputing denominators from sampled row counts. Report descriptive95% intervals for observed candidate returns and matched exit improvements. Do not call these fresh validation intervals or require an incremental-AI test to report an observed price-strategy return.

A research shortlist may contain a candidate with positive pooled mean, positive means in both chronological halves, positive means in at least4/5 existing cohorts, positive mean after removal of the largest3winning trades and a positive pooled paired difference versus FIXED_1ATR_stop. Report any failure rather than changing the rules. This is a fixed exploratory triage screen; it does not prove profitability. Long/short or asset components cannot replace a failed pooled rule after inspection.

Before full scoring, run synthetic cases covering next-minute activation, entry-minute handling, adverse stop gaps, favorable target gaps, partial target/stop ambiguity, a target-at-open followed by old-stop touch, trailing ratchets and fixed-clock timeout. Have the independent reviewer check causal ordering and replay the saved ledgers. No fee, leverage or live-execution claim is made from these zero-cost bar-based simulations.
