# Managed exits did not rescue the reversed AI trades

None of the three frozen protection rules produced a positive average gross return. All three also underperformed both controls on the exact same entries. No candidate is selected for further testing from this exit family.

We replayed all **1,020 existing primary Terra decisions at their original timestamps**, representing 645 calendar moments and 25 quarters. Each policy reverses the AI direction, enters at the first native minute open, and has a fixed 240-minute cap. Costs are zero. The five original cohorts are retained, including MA_A only for paired90. These are previously examined outcomes: this is an exploratory exit-management extension, with no new model calls, new targets, or claim of fresh validation. The remaining 29 snapshot credits are unchanged.

| Frozen exit rule | Mean gross/trade | Positive trades | Breakeven trades | Mean without best 3 | Difference vs fixed stop |
|---|---:|---:|---:|---:|---:|
| Breakeven after +1 ATR | −0.04981% | 169 / 1,020 | 322 | −0.08380% | −0.05243 pp |
| Trail by 1 ATR after +1 ATR | −0.06986% | 489 / 1,020 | 2 | −0.10813% | −0.07247 pp |
| Half profit at +1 ATR, then breakeven | −0.04846% | 489 / 1,020 | 2 | −0.07071% | −0.05107 pp |
| Fixed 1 ATR stop, no target — control | +0.00262% | 295 / 1,020 | 4 | −0.03196% | — |
| Hold 240 minutes — control | +0.05500% | 548 / 1,020 | 5 | +0.01264% | — |

Each figure is an equal-original-notional trade mean, not a compounded portfolio return. Uneven asset coverage makes this a mixed historical sample: 645 SOL observations and 125 each for BTC, ETH and DOGE. Simultaneous assets remain in the same calendar block in every chronological split and bootstrap.

## What happened inside the trades

Protection armed on 484 of 1,020 trades. Breakeven protection created 322 zero-return exits, but the three managed policies still had 529 losing trades. Their average losing trade was −0.76136%. More apparently successful exits did not create positive expectancy: trailing protection won 47.94% of trades, with an average winner of +0.67793%; half-profit protection had the same positive-trade rate, with an average winner of +0.72256%.

The clearest matched comparison is breakeven versus the fixed stop. Breakeven improved **192 trades by an average +0.55638 percentage points**, worsened **126 by −1.27223 points**, and left 702 unchanged. It helped more individual trades than it hurt, but the lost return on the hurt trades was larger. Its mean paired effect was −0.05243 points. Trailing and partial-profit management also had negative paired effects. This is consistent with stops preventing some losses while also cutting off subsequent recovery or larger winners; retaining a favorable excursion alone was insufficient.

Risk limits did reduce the worst observed single-trade loss from −21.45298% under the raw hold to −7.13280% under each stopped policy. That is a different property from improving expected return. No sizing or capital-allocation conclusion is inferred from this comparison.

## Long trades and stability

| Exit rule | Longs: 655 trades | Shorts: 365 trades | First calendar half | Second calendar half |
|---|---:|---:|---:|---:|
| Breakeven | −0.08638% | +0.01581% | −0.08096% | −0.01915% |
| Trailing | −0.08694% | −0.03919% | −0.08394% | −0.05599% |
| Half profit | −0.08227% | +0.01222% | −0.08728% | −0.01024% |
| Fixed-stop control | −0.00718% | +0.02020% | −0.01520% | +0.02015% |
| Raw-hold control | +0.00374% | +0.14699% | +0.03469% | +0.07499% |

All three managed rules lost on the long side and in both calendar halves. Each was positive in only two of five cohorts: original100 and next280. Each was negative in next50, multi500 and paired90. Removing the best three trades leaves all three negative. Small positive short components are descriptive and are not promoted as new rules.

| Exit rule | Entry-time-block 95% interval | Whole-quarter 95% interval |
|---|---:|---:|
| Breakeven | [−0.14722%, +0.05075%] | [−0.13098%, +0.02919%] |
| Trailing | [−0.15178%, +0.01648%] | [−0.12879%, −0.01155%] |
| Half profit | [−0.12624%, +0.02983%] | [−0.11994%, +0.01689%] |
| Fixed-stop control | [−0.11206%, +0.12208%] | [−0.09414%, +0.10001%] |
| Raw-hold control | [−0.17186%, +0.25002%] | [−0.13607%, +0.22622%] |

These intervals use the frozen 20,000-draw block and quarter resampling procedures. They are descriptive uncertainty measures on reused outcomes, without correction for the broader research search. The raw hold's positive sample mean does not establish profitability. Both controls have intervals spanning zero. None of the managed policies passes the frozen exploratory triage screen.

## Execution and interpretation

Stops updated from a completed minute activate only on the following minute. An adversely crossed stop fills at the actual open, including an activation level beyond that open. Favorable target gaps fill at the target. Intrabar stop/target ambiguity is resolved against the trade; a target already executed at the open precedes a later stop. A half exit always represents half the original notional. No same-bar high is used to retroactively protect against its low.

The synthetic suite passed 18 long cases and their 18 short reflections, plus the native DOGE boundary regression, including partial target at the open followed by the old stop, same-bar target/stop ambiguity, next-minute activation and adverse stop overruns. All 1,020 raw holds reconcile to direct native first-open-to-240-close returns. All 1,020 fixed-stop controls reconcile to the separately established bracket engine, with maximum absolute discrepancy below 3×10⁻¹⁴ percentage points. Source and frozen-code hashes were preserved. The independent review is recorded separately in the parent study's audit folder. Its first pass identified one missed inclusive contact caused by floating-point rounding. The correction reduced one trailing trade from +0.94281% to +0.01546% and moved four other exit timestamps without changing their payoffs; trailing's pooled mean fell by 0.000909 percentage points. All results here include the correction. The original 22 files are archived with hashes; `NUMERICAL_CORRECTION.md` and `.json` document the unchanged rules, sample and bootstrap draws. Inclusive contacts now use only a scale-aware machine-epsilon tolerance, with no tick-sized buffer.

The corrected independent replay **passed**: all 5,100 paths, 112,200 ledger fields, five payoff vectors, both 20,000-draw cluster bootstraps, and all six paired intervals reconcile to the separate percentage-space reference. There are no remaining discrepancies. See `../audit/managed_exits_final_audit.json`.

The paired controls isolate the effect of exit management on these AI-reversed entries. They do not identify an incremental AI signal over price-only entries. Here even the simpler observed-return requirement fails for all three candidates, so no informational claim is needed to reject this family as a current lead.

## Reproducible outputs

- `trade_ledger.csv`: all 5,100 policy trades, entry/exit prices, side, ATR, partial execution, activation, gap and ambiguity fields.
- `execution_events.csv`: 10,835 execution and stop-update events, including when updates become active.
- `summary.json`, `matched_control_differences.json`, `breakdown.csv`, `largest_winners.csv`: all frozen comparisons, cohort/time/asset/side results and concentration diagnostics.
- `CANDIDATE_GATE.json`: all three failed gates, with no selected candidate.
- `joint_family_vectors.npz`: `returns_pct` and `selected` arrays with shape **(1,020 windows, 5 policies)**, plus policy, role, window IDs, UTC quarter, entry time, asset, cohort, side and calendar-block labels. All controls are retained for the root study's joint correction. `joint_family_schema.json` records units, alignment and SHA-256.
- `PLAN.md`, `SCORING_FREEZE.json`, `engine.py`, `run.py`, `test_synthetic.py`, `finish.py`, `evaluation_audit.json`: frozen definitions, implementation and reproducibility checks.
