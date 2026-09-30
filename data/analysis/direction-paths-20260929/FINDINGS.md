# Direction and path study — 29 September 2026

**The clearest pattern is in how the models choose and express confidence: they mostly follow the visible trend and moving averages. The evidence for an additional, reliably tradable AI signal is much weaker.** There is an interesting early-continuation / later-fade pattern, but it is also present in the underlying price regimes without asking an AI.

This analysis reconstructs every recorded AI decision: **1,052 decisions, 120 market windows**. The comparable experiment is **1,000 decisions on the same 100 SOL windows**: Haiku, Sonnet, Luna, Terra and Astra under both original rules (v1) and forced-direction, fixed 2:1 rules (v2). The other 52 decisions—20 Opus decisions on SOL plus 32 decisions on other assets—are included in the explorer as supplements. Ten model/rule decisions on a window still represent only **one market realization**, not ten independent observations.

[Open the complete interactive trade explorer](index.html). [Download every enriched decision](decisions_enriched.csv). [Read the registered exploratory plan](ANALYSIS_PLAN.md).

## 1. A simple price model can reproduce about 86% of AI direction choices

A fixed, regularized logistic model using six pre-entry price/volume features predicted the models' long/short choices in grouped cross-validation:

| Rules | Direction choices | Price-feature accuracy | Training-set majority baseline | Simple price-versus-MA20 rule |
|---|---:|---:|---:|---:|
| Original | 475 | 85.7% | 62.1% | 82.3% |
| Forced 2:1 | 500 | 86.2% | 67.4% | 77.8% |

These are predictions of **AI choices**, not future market direction. All decisions from the same window are held out together. Windows separated by no more than 72 hours are kept in the same fold; the 100 windows form 92 temporal groups. The six features are visible move / ATR, distances to MA20 and MA50 / ATR, last-bar return, last-five-bar return and relative recent volume. Scaling is learned on training folds only. This is internal, exploratory cross-validation, not a later-period live test.

In the forced-rule experiment, individual models follow the sign of the visible trend in **75–82%** of windows, and price-versus-MA20 in **65–88%**. They select short in **63–71%** of windows. However, 60% of these inputs already lie below MA20 and 59% show a negative visible move: part of the short bias belongs to the supplied sample.

The strongest collective regularity is more specific: **when price is below both MA20 and MA50, the v2 majority chooses short in all 50 of 50 windows**. Above both averages, it chooses long in 25 of 30. There are only 20 mixed windows. All five models agree in 55 of the 100 v2 windows. Changing the rules leaves the same action in 77–89 of 100 cases per model.

**Interpretation:** these agents behave like related trend/indicator followers. This supports a behavioral-bias hypothesis. It does not establish that they simulate typical retail traders, nor that reversing their choices will profit.

## 2. Confidence measures agreement with the setup more clearly than future accuracy

For Astra under forced rules, confidence correlates with following MA20 at **r = +0.562**, with a multiple-test-adjusted **q = 0.002**. Mean confidence is 59.3% when aligned with MA20 and 55.4% when opposing it. Sonnet, Haiku and Terra show the same association with adjusted q below 0.05.

Astra's confidence correlation with seven-candle directional correctness is **r = −0.173**, but **q = 0.271**: insufficient evidence of a stable inverse-confidence effect. Across the 40 confidence tests, none of the future-direction / future-return relationships survives adjustment at q < 0.05. The smallest such q is about 0.096, for Terra's first-candle accuracy.

Thus, higher confidence appears to describe a more familiar or internally consistent chart narrative. It is not demonstrated to identify a better forecast here. The original confidence field was not specifically defined as a probability of being right at 105 minutes, so this is not a formal probability-calibration test.

## 3. The first candle and the seventh candle tell different stories

The most interesting timing lead is the **below-both-averages regime**:

- All 50 v2 majority decisions are short.
- The market falls during the first 15 minutes in **34/50 cases (68%; one additional case unchanged)**.
- At 105 minutes—seven 15-minute candles—it remains below entry in only **24/50 cases (48%)**.

This suggests early continuation that often fades. Crucially, the signal in this cell is exactly a price-regime rule: every AI majority chose the same direction. The AI is not adding identification within that group.

Across all 100 v2 windows, majority-direction accuracy is **54% at 15 minutes, 52% at 90 minutes and 46% at 105 minutes**. The paths break down as follows:

| First candle → seventh candle | Windows |
|---|---:|
| Direction right at both endpoints | 33 |
| Right initially, wrong later | 21 |
| Wrong initially, right later | 13 |
| Wrong at both endpoints | 32 |
| At least one endpoint exactly at entry | 1 |

These are endpoint categories, not claims that price stayed on one side throughout. The minute-by-minute explorer makes the intervening fluctuations visible. Typical paths cross entry several times.

The below-both first-candle cells are the strongest findings in the 110-cell context/horizon scan, but their adjusted **q is 0.088**, above 0.05. These tests concern mean signed ATR movement; the 68% → 48% paired accuracy decline is descriptive and has not received a separate confirmatory test. Seeing the same result in v1 and v2 is not independent replication: both use the same future candles. A large opposite move after extreme visible trends at 24 hours is another exploratory lead, but its adjusted q is roughly 0.53. Neither should be promoted to a validated rule.

## 4. Long calls are weaker, but price-regime exposure is a competing explanation

| Model, forced rules | Long correct at 105m | Short correct at 105m |
|---|---:|---:|
| Haiku | 10/33 — 30.3% | 32/67 — 47.8% |
| Sonnet | 14/37 — 37.8% | 32/63 — 50.8% |
| Luna | 13/34 — 38.2% | 34/66 — 51.5% |
| Terra | 10/30 — 33.3% | 35/70 — 50.0% |
| Astra | 12/29 — 41.4% | 38/71 — 53.5% |

That asymmetry deserves further study. But in the 30 windows already above both averages, the asset itself rises over seven candles in only **10/30 cases (33.3%)**, averaging −0.408%. Since models frequently buy those setups, their poor long accuracy could be inherited from those price patterns. The models' errors are also highly dependent because they trade the same events.

The clean next question is: **within comparable price regimes and trend strength, does an AI long call identify additional downside beyond a simple price rule?** The current evidence does not establish that.

## 5. What their explanations say on right and wrong decisions

We can inspect the recorded explanations, not the models' hidden internal thought process. A dictionary fixed before this path analysis tags trend, moving averages, breakouts, failed moves, support/resistance, weak/strong volume and reversal/exhaustion language. Tags may overlap and keyword matching misses nuance.

For v2 at seven candles, moving-average language appears in **83.3% of wrong-direction decisions versus 76.1% of right-direction decisions**. Trend language appears in **76.7% versus 70.4%**. These are descriptive decision-level counts across shared windows, not independent statistical evidence that those words predict failure. They fit the broader tendency to justify continuation using familiar indicators, including when continuation subsequently fails. No distinct, validated “losing-trade vocabulary” has been established.

The explorer shows the exact saved reason beside the uncensored future path and the anonymized chart supplied to the model. This permits direct comparisons between models seeing the same input and between v1/v2 decisions. Every case is available; the display does not select only dramatic mistakes.

Three concrete examples make the distinction visible. These are **retrospectively selected illustrations**, not extra statistical tests:

| Case | All five v2 decisions | Direction-signed first candle | Direction-signed seventh candle | Saved reasoning theme |
|---|---|---:|---:|---|
| 4 | Short | +0.352% | −0.779% | Below declining averages; breakdown / lower highs |
| 29 | Long | −0.632% | −3.130% | High-volume breakout above rising averages |
| 81 | Short | +0.151% | +5.039% | Below averages; lower highs / continuation |

In case 4, the continuation story works briefly then reverses. In case 29, all five models favor the same breakout that subsequently fails. Case 81 is a counterexample: similar continuation language precedes a strong favorable move. The language alone does not distinguish these paths.

## 6. Why stop/target labels hide useful behavior

A stop loss does not uniquely describe the later path. Under v2, **4 Haiku, 4 Sonnet, 3 Luna, 5 Terra and 7 Astra decisions actually stop out within the first 105 minutes yet have a favorable signed return at minute 105**. These are decision counts on overlapping sets of market windows. Conversely, a temporary favorable excursion need not survive to the seventh candle.

For each directional decision the dataset adds:

- Direction-signed returns at 15 horizons from 1 minute through 24 hours, including every one of the first seven 15-minute closes.
- Maximum favorable and adverse excursions over fixed horizons, independent of bracket exit.
- Fraction of minute closes on the favorable side, first favorable minute, sign changes and first ±0.5 / ±1 ATR barrier touches. If both barriers are touched in the same one-minute candle, touch order is recorded as ambiguous.
- Initial-to-later directional transition, MA regime, trend/volume features, confidence and explanation tags.

The signed path is positive when price moves in the chosen direction. It is an analytical hypothetical held through the chosen horizon, not the original realized trade P&L. Fees, leverage and actual exit execution are not part of these path returns. Flat decisions have no directional return.

## 7. What did not hold up

For the v2 majority, mean signed seven-candle movement is **+0.051%**, with a window-bootstrap 95% interval of approximately **−0.215% to +0.326%**. A base-rate-preserving permutation gives p = 0.652; restricting permutations within MA regimes gives p = 0.727. The multi-horizon adjusted tests do not demonstrate directional value.

Adding AI votes and confidence to the fixed price-feature model changes seven-candle out-of-fold market-direction accuracy from **54% to 52%**. Its Brier-score improvement is essentially zero, with an interval spanning both benefit and harm. At each tested prediction horizon, the interval for incremental AI Brier performance contains zero. With only 100 market events and a small fixed model this is a failure to demonstrate improvement, not proof that no useful nonlinear relationship exists.

The v2 signed mean also changes from **+0.425 ATR in the earlier chronological half to −0.199 ATR in the later half**. That instability argues against turning a selected historical pattern straight into a strategy.

## Scope, validation and limits

Entry is the close of the last visible 15-minute bar. Its stored timestamp is the bar's OPEN, so future paths begin 15 minutes after that timestamp. Every saved entry is checked against raw one-minute and native 15-minute closes; the first seven future closes are independently checked against native 15-minute data. All 120 windows have complete 24-hour one-minute coverage. Source-file hashes are retained and rechecked; see `validation.json`. The figure was visually inspected and report JavaScript syntax checked. The browser URL policy blocked the local-file preview, so interactive rendering has not been verified in-browser.

Bootstrap samples use windows rather than model rows. The 100 SOL windows occupy 98 entry dates; three pairs overlap within 24 hours, including one pair within 105 minutes. Date-cluster and chronological-half sensitivities are provided; a window bootstrap is still an approximation to dependence. Cross-validation uses 92 groups with a 72-hour separation rule, but is not a walk-forward deployment simulation. The intervals for out-of-fold forecast comparisons do not refit the entire model inside each bootstrap sample.

The 30 primary horizon/protocol tests use a shared permutation across horizons, false-discovery adjustment and maximum-statistic familywise correction. The separate 40-confidence-test and 110-context-cell families use false-discovery adjustment. The implemented context scan uses 11 cells per protocol: three MA regimes, unanimous/nonunanimous, extreme/nonextreme visible move, high/low ensemble confidence, and majority long/short. This refines the exploratory plan: confidence is split at the median ensemble confidence rather than each model’s median, and direction cells replace a separate visible-trend-sign split. Neither variant was treated as confirmatory. The context sign-flip test assumes symmetry under its null; it is exploratory, not causal adjustment. Tag comparisons and pairwise model contrasts are descriptive. The same data has been inspected in previous research, so this is not an untouched confirmation sample even though the present analysis plan was recorded before computing these paths.

The last 214 OpenAI v2 decisions were resumed with a fresh Codex CLI harness; the first 86 used desktop subagents. This is a collection-harness change, not new independent market data. Claude/OpenAI differences cannot be attributed solely to model quality. The supplementary asset/model cells are too small for generalization.

## Freeze these questions for fresh windows

1. **Behavior:** reproduce the high choice-prediction rate and confidence–indicator association on new, temporally separated windows, using the same definitions.
2. **Early continuation / later fade:** pre-register the below-both-MA regime and 15-minute and 105-minute endpoints. Compare an AI vote with the direct regime rule. Test the paired change in directional correctness, not selected win/loss subsets.
3. **Contrarian long calls:** compare AI longs against matched above-both and trend-strength controls. Require incremental value, with frozen thresholds and untouched out-of-time windows, before testing economic returns.

Collect enough new independent windows for a power calculation tied to a minimum meaningful effect; do not count additional model opinions on an old window as new market observations. Freeze model versions, prompts and harness, and do not tune the above rules using this sample again.


## First-candle count correction

Correction: the earlier 70% / 35-of-50 statement counted one exactly unchanged first-candle close as a decline. The correct result is 34/50 (68%), with 15 adverse and one unchanged; 34/49 (69.4%) if the tie is excluded. Seven-candle correctness remains 24/50 (48%). Return values and existing return-based tests are unchanged.
