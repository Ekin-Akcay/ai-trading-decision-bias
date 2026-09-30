# V3 first 20: price and volume only

The requested pilot is complete: **20 exact canonical cases × Luna, Terra and Astra = 60 saved, scored decisions**. All 100 canonical stimuli are ready; cases 21–100 have not been run. Every decision used a fresh single-turn context, the exact new text/chart, medium reasoning and no tool calls. There were60 attempts,60 valid responses, zero exclusions or retries. Existing decisions and reports were preserved.

## Behavior survives removal of the supplied indicators

Only **12 of 60 directions changed** relative to the same model's historical v2 decision: Luna 4, Terra 6, Astra 2. Overall agreement with the original, now-hidden MA20 remains **75%**, versus 78.3% in v2. The models can infer trend from candles; explicit MA displays are not necessary for most of these choices. This is consistent with trend-following from raw price, but does not establish that input removal caused the changes: old v2 calls were not repeated concurrently, some used a different harness, and model sampling can also change choices.

| Model | Direction changes | MA20 alignment v2→v3 | Mean confidence v2→v3 | Median stop distance v2→v3 |
|---|---:|---:|---:|---:|
| Luna | 4/20 | 85%→75% | 63.85%→62.55% | 0.85%→0.80% |
| Terra | 6/20 | 80%→80% | 61.15%→61.40% | 0.95%→0.725% |
| Astra | 2/20 | 70%→70% | 57.50%→58.05% | 0.90%→0.875% |

None of the 60 saved explanations explicitly refers to MA20, MA50, moving averages or ATR. This does not reveal hidden reasoning; it only describes the recorded explanation text.

## A model-specific early-horizon lead, without confirmation

| Model | 15m direction accuracy v2→v3 | 30m v2→v3 | 105m v2→v3 |
|---|---:|---:|---:|
| Luna | 60%→60% | 45%→55% | 45%→45% |
| Terra | 45%→65% | 40%→70% | 40%→40% |
| Astra | 55%→55% | 50%→50% | 50%→40% |

Terra is the interesting case: its 30-minute signed movement improves from **−0.093% to +0.215%**, a paired change of +0.308 percentage points. With 20 bps round-trip costs, its hypothetical 30-minute time exit averages **+0.015% net** in this pilot. However, the paired return sign-flip test has raw p≈0.032 and **q≈0.289 after the nine model×horizon comparisons**. That does not establish a repeatable advantage. The unadjusted bootstrap interval for the paired change is [+0.064,+0.636] percentage points; the small number of changed decisions and discrete permutation test explain why this interval and test need not give identical thresholds. No tested v3-v2 horizon comparison survives correction.

The 70% Terra accuracy here is 14 of 20 model decisions at 30 minutes. It is a different statistic from the corrected 68% first-candle majority-short accuracy in 50 below-both-MA windows. Do not conflate them.

At 105 minutes Terra's direction accuracy is unchanged; Luna is unchanged; Astra falls. This reinforces the need to specify a horizon before interpreting a directional call. These are hypothetical fixed-horizon paths ignoring the model's bracket exit, without leverage or extra slippage.

## Original v3 bracket outcomes

| Model | v3 TP / SL | Mean gross / trade | Mean net / trade (20bps) |
|---|---:|---:|---:|
| Luna | 5 /15 | −0.155% | −0.355% |
| Terra | 5 /15 | −0.168% | −0.368% |
| Astra | 3 /17 | −0.473% | −0.673% |

The forced 2:1 brackets did not become profitable in this 20-case pilot. Terra's short-horizon descriptive improvement therefore should not be conflated with an improvement to the complete bracket strategy.

## Precisely what v3 changed

The user requested only price/volume chart and data. All 40 normalized OHLC/relative-volume rows are byte-identical to v2. V3 removes MA overlays/labels/numeric values, ATR/sigma volatility summaries, and derived move/aggregate-volume summaries. Rebased current price 100 and volume normalization against the prior 200 bars are unchanged. Removing overlays can change automatic chart y-limits. This is **a price/volume-only treatment**, broader than pure MA removal, and cannot identify an MA-only causal effect.

The models never received actual asset/date, earlier decisions, outcomes, or the policy-study findings. Private historical indicators retained in the evaluation ledger are explicitly labeled not-supplied. Outcomes use the unchanged one-minute resolver, exact 2×SL targets, 72h timeout, and original gap/ambiguity rules. All 60 targets obey the fixed ratio and all entry prices match canonical prices.

The comparable sample contains 20 market outcomes, reused by three models and two versions, not 60 independent events. The first 20are a pilot and not a representative replacement for all 100. There are no new unseen market windows or repeated identical-prompt controls, so stochastic variability and harness changes remain competing explanations.

## Artifacts and continuation

- `../reports/pricevolume-v3-openai-20260929T173255Z.html`: every paired decision, reason, fixed-horizon move and chart.
- `../decisions/pricevolume-v3-openai-20260929T173255Z.jsonl`: the 60 new canonical rows.
- `paired_v2_v3.csv`, `summary.json`, `paired_tests.json`: complete comparison and uncertainty.
- `isolation_audit.json`, `preservation_check.json`, `cli_attempts/`: provenance and raw outputs.
- `../pricevolume-v3/INSTRUCTIONS.md`, `../pricevolume-v3/window_list.json`: shared protocol and all 100windows, ready for a separate Claude run or later authorized continuation.

Keep the prompt, model settings and horizon definitions fixed if extending to cases 21–100. Do not rewrite the protocol around Terra's best pilot cell. The simultaneous existing-data policy study lives at `../../analysis/exit-policies-20260929/` and reports the entire grid, including unsuccessful variants.
