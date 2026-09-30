# Information beyond raw AI direction: no candidate promoted

The eleven fixed definitions produced no candidate that met the discovery recommendation criteria. No model calls were made. All results below reuse previously exposed outcomes and remain discovery results, including those computed with strict forward-calendar fitting.

The useful behavioral finding is **686 of 803 AI directions predicted correctly (85.43%)** by a small model trained on earlier price inputs and earlier AI labels. Its annual action accuracy ranged from 81.67% to 89.47%. This predicts **what the AI will choose**, not where the market will move. The five inputs include MA distances, visible return, volume ratio, and ATR, so this does not isolate a causal effect of MAs. It shows that most of the direction choice is reproducible from a small price-feature set.

The study has 1,020 unique asset/window events at 645 unique entry times. The first nine policies use 803 forward-scored events at 515 entry times; 217 earlier events supply warmup data. Annual fits use only earlier entries with a seven-day embargo. The last two policies use the paired90 experiment directly. Three decisions on one paired window do not count as three market events.

## All eleven definitions, retained

All trades enter at the first minute open after the visible history and exit at the close 240 minutes later. Fees are zero. Percentages below are mean arithmetic returns per selected trade, not compounded portfolio performance. “Extra beyond direction” is the difference against the fixed price-and-raw-action matched association benchmark; it is not a causal estimate.

| Fixed definition | Trades | Entry-time blocks | Gross mean | Extra beyond direction |
| --- | ---: | ---: | ---: | ---: |
| Unexpected SHORT → buy | 57 | 51 | -0.2846% | -0.1405 points |
| Unexpected LONG → sell | 60 | 53 | +0.2943% | -0.0499 points |
| Confident unexpected SHORT → buy | 21 | 20 | -0.3100% | -0.1660 points |
| Confident unexpected LONG → sell | 4 | 4 | +2.9692% | +2.0109 points |
| Unexpected exhaustion mention → fade | 32 | 29 | -0.3733% | -0.5566 points |
| Unexpected breakout/breakdown mention → fade | 282 | 196 | +0.1449% | -0.0080 points |
| Unexpected rejection mention → fade | 204 | 161 | +0.0192% | -0.1079 points |
| Unexpected continuation mention → fade | 6 | 6 | -1.1609% | -0.8913 points |
| Unexpected counterevidence wording → fade | 92 | 80 | -0.1457% | -0.3799 points |
| Identical-input repeats disagree → follow NO_MA | 10 | 10 | +1.0709% | +0.5856 points |
| Identical-input repeats agree, NO_MA flips → follow NO_MA | 14 | 14 | -0.2566% | -0.3566 points |

All eleven family-adjusted intervals for the increment beyond matched raw direction include zero. None passes the fixed combination of sample size, cohort consistency, chronological consistency, positive increment, and removing the three best trades. Full cohort, asset, year, quarter, and directional-leg decompositions are retained in `results.json`; all 11×1,020 policy/window vectors are retained in `all_information_vectors.npz`.

## Why the visible positives do not qualify

The unexpected-LONG short policy has 60 trades and +0.2943% gross, but its 95% quarter interval is [-0.1487%, +0.6736%]. Removing its three best trades changes the mean to -0.0432%. The new280 cohort is +0.8508%, whereas the four-asset cohort is -0.1751%; its incremental return beyond raw direction is negative overall. It does not establish a useful surprise effect.

The breakout/breakdown rationale policy has enough observations to assess: 282 trades, +0.1449% gross, 95% quarter interval [-0.0821%, +0.3805%]. Its apparent edge is already explained by the matched raw-direction comparator, leaving -0.0080 percentage points. Cohort means are -0.0011% old150, +0.0330% new280, +0.2810% fourasset500, and -0.2318% paired90. Its final calendar year, 2026, is -0.2583%. This is not stable incremental rationale information.

Two tiny positives remain visible. The confident-unexpected-LONG policy earns +2.9692% on **four** events; it has no qualifying four-asset cohort trades and cannot support the claim. The repeat-disagreement tie-break earns +1.0709% on **ten** events, with a quarter interval [-0.0728%, +2.7407%]. Removing its best three leaves -0.1564%. Eight of the ten positions are shorts, and it exists in only one cohort. Neither warrants spending reserved calls on its present evidence.

The unusual exhaustion, continuation, and counterevidence fades do not support “the model is especially wrong here.” Their negative results should not be silently sign-flipped into new successful candidates. Those opposite policies were not the registered family.

## What the price-only comparator adds

An independent reviewer identified that matching by cohort, asset, era, and MA regime is coarser than the five continuous fitted features. Therefore the matched baseline cannot establish value beyond the entire price model. Selected-side standardization also is not itself a deployable AI-free strategy.

As a clearly labelled **post-score diagnostic control**, the existing fitted price model's predicted AI direction was followed and faded without a new fit, parameter, or candidate selection. Fading that predicted direction earns +0.16120% across the 803 forward-scored events, compared with +0.16478% for fading the actual AI. The difference is only **+0.00358 percentage points**, with 95% quarter interval **[-0.09201, +0.11254]**. The positive pooled generic reversal is almost completely reproducible from price inputs in this dataset.

This does not verify a price strategy. The control was added after scoring, all outcomes were already exposed, and 2026 is negative for both the price-model fade (-0.10445%) and actual-AI fade (-0.16815%). The appropriate implication is that another inference call currently offers no demonstrated incremental value over that price-based approximation. The controls cannot be promoted as newly registered finalists.

## Audit and decision

Independent verification passed 1,020 source-price entry/four-hour-exit checks, all five annual training boundaries, 5,621 auxiliary prediction reconstructions, 14,814 control-row comparisons, and 110 bootstrap interval endpoints. Control means and selected-side weights were reestimated within each of 20,000 quarter resamples; simultaneous assets stay together in chronological halves. Inference remains conditional on the historically fitted auxiliary models, and coarse matching remains an association analysis.

`CANDIDATE_GATE.json` records **zero recommended candidates and zero authorized additional calls**. This family provides useful evidence about redundant AI information, but it does not supply a verified profitable strategy. Earlier failed primary tests and all original source files remain unchanged.
