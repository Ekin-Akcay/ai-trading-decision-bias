# Released MA-ablation economic audit

The SOL long replication failed economically. Removing explicit MA information did not establish a profitable strategy or a reliable improvement over the original input. There is suggestive evidence that MA removal changes decisions more than an identical repeat, but it did not meet the frozen mechanism threshold. These are separate conclusions.

All 270 accepted isolated calls cover the same 90 market windows. This audit was run only after the explicit root release and `ALLOW_EVALUATION` marker. It passed **3,023 numerical/claim checks**, with maximum discrepancy **3.56×10⁻¹⁵ percentage points**. No payoff, skip-denominator, support, concentration or frozen-criterion error was found. Native minute prices and independent statistical mathematics are assigned to the other reviewers; this audit does not claim to duplicate them.

## Economic result

Each SHORT call selects the fixed contrarian long trade; a LONG call skips. All values are gross percentages at zero fees.

| Arm | Executed longs | Mean per trade | Mean per opportunity, including skips | Trade win rate | Profit factor | Mean excluding best 3 |
|---|---:|---:|---:|---:|---:|---:|
| MA_A, sole profit replication | 71 | −0.1297% | −0.1023% | 46.48% | 0.850 | −0.4061% |
| MA_B, identical-input repeat | 67 | −0.0608% | −0.0452% | 44.78% | 0.924 | −0.3512% |
| NO_MA, input intervention | 72 | −0.1167% | −0.0934% | 47.22% | 0.869 | −0.3885% |

MA_A's average winner was +1.5783% and its average loser −1.6130%. With those realized payout sizes, the descriptive break-even win rate is 50.54%, versus the observed 46.48%. The gross expectancy is already negative before costs. This arithmetic neither establishes a profitable strategy in the AI's original direction nor licenses reversing the rule again after seeing the answer.

The primary 99% window interval is [−0.8255%, +0.6008%]; its 95% whole-quarter interval is [−0.4913%, +0.2169%]. The intervals do not establish positive expectancy, and they also do not prove that every possible future expectancy must be negative.

MA_A passes only the minimum-support requirement. It fails the other five frozen conditions: the window lower bound, quarter lower bound, positive chronological halves, positive delayed-entry means, and positive mean without the best three trades. Its halves are −0.2107% and −0.0416%; its thirds are −0.3256%, +0.1506% and −0.1348%. The 1- and 5-minute delay means are −0.1215% and −0.1233%. Only 6 of 15 represented quarters have positive selected-trade means. Both halves are also negative in MA_B and NO_MA.

The three largest MA_A winners supply 35.3% of the sum of winning-trade gains, yet all gains together still fail to offset losses. Removing the largest winner reduces the mean to −0.2253%; removing the largest three reduces it to −0.4061%. Because total return is negative, a signed top-three-to-total ratio is not a useful headline measure of profit concentration; the complete JSON retains that arithmetic only for reproducibility. Sums of trade percentages are not compounded portfolio returns.

## AI contribution and the MA intervention

The all-window price-only long control averages −0.1746% across 90 windows. The existing macro-plus-below-MA20 control averages −0.2134% across 55. MA_A appears less negative than these raw controls, but after the frozen era × MA-regime standardization its baseline is −0.0932% and its AI increment is **−0.0364 percentage points**. Its 99% window increment interval [−0.2258, +0.1050] and 95% quarter interval [−0.1408, +0.0615] do not establish incremental AI value. Only three eligible strata contain both selected and complementary observations.

On paired opportunities, NO_MA−MA_A is just **+0.00895 percentage points**. Its 95% window interval is [−0.1600, +0.1897] and its quarter interval [−0.1777, +0.1932]. The identical-repeat MA_B−MA_A difference is larger at +0.0571 points, and also uncertain. Conditional per-trade means alone must not be used to claim that MA removal improved performance: the arms select different trade subsets. Neither secondary arm can replace the designated MA_A replication.

MA removal flips 19/90 actions (21.11%), versus 10/90 (11.11%) for an identical repeat. The treatment-only versus repeat-only discordants are 14 versus 5; the frozen one-sided exact test gives **p=0.03178**, above the required 0.01. The 95% excess-flip interval excludes zero, but that weaker diagnostic does not supersede the frozen threshold. The correct interpretation is suggestive input sensitivity, **not verified MA dependence under this protocol** and not evidence that this sensitivity causes an exploitable market error.

Removing MAs does not remove the overall bearish choice frequency: MA_A calls SHORT 71 times, MA_B 67, and NO_MA 72. Relative to MA_A, NO_MA changes 10 LONG calls to SHORT and 9 SHORT calls to LONG: one net additional SHORT, not fewer. The model can still infer trend and averages from price history. This controlled intervention addresses explicit supplied MA information; it cannot establish that the model no longer uses MA-like reasoning.

## Artifacts and interpretation boundaries

`economic_audit.json` preserves all arm statistics, quarters, halves/thirds, largest windows, failed criteria, paired opportunity intervals and source hashes. `economic_window_vectors.csv` contains the 270 audited economic rows. `audit.log` records the completed run. Reproduce only with the explicit release argument documented in `audit.py`.

The 90 fresh market outcomes are the economic units; the 270 independent model sessions are not 270 independent price paths. The prior failed 500-window test and this failed replication remain separate. None of the favorable secondary observations supplies a new verified profit claim.
