# Exit-policy results — exploratory, 2026-09-29

## What changed when we exited earlier or shrank the brackets?

Neither change produced a credible net improvement on these existing windows. Smaller percentage returns partly reflect mechanically smaller risk width; they do not alone establish weaker directional expectancy. The risk-normalized appendix below separates gross expectancy from fee burden. The clearest pattern is mechanical: shrinking both levels makes trades resolve much faster while their small gross movement increasingly struggles to cover the same 20-basis-point cost. This is evidence about this sample, not proof that every short-duration strategy is unprofitable.

All results below average decisions within each market window, then average the 100 windows. The same ten decisions share each market path; they are not 1,000 independent observations. The main grid includes both v1 and v2 and all five models. Original flat decisions remain zero-return and zero-cost. Figures are percentage points of entry, without leverage or position sizing.

| Policy | Gross mean | Net mean | Median holding time |
|---|---:|---:|---:|
| Original brackets | +0.114% | −0.081% | 96 min |
| Exit after 15 min / 1 candle | +0.047% | −0.148% | 15 min |
| Exit after 30 min / 2 candles | +0.043% | −0.152% | 30 min |
| Exit after 105 min / 7 candles | +0.015% | −0.180% | 105 min |
| Both brackets at 75% width | +0.054% | −0.141% | 50 min |
| Both brackets at 50% width | +0.039% | −0.156% | 20 min |
| Both brackets at 25% width | +0.017% | approximately −0.177% | 6 min |

The 25%-width row excludes two ambiguous outcomes from its displayed gross mean; assigning each ambiguous trade to its stop or target puts the mean net result across all 1,000 rows between −0.1776% and −0.1764%. The precise exclusion-only mean is −0.1777%; because exclusions change within-window weights, it need not lie between those all-row bounds.

The six primary paired changes have negative observed mean differences versus original brackets, but their 95% difference intervals all include zero. Each has BH-adjusted q = 0.543 in the six-test primary family. Thus we have not established that modifying the policy helps, or a statistically decisive ranking between them. Negative net point estimates are not the same claim as statistically established negative expected returns.

## Costs are larger than the movement captured

For active trades, the gross mean at 15 minutes supports only about **4.85 bps** of break-even round-trip cost; at 30 minutes, **4.45 bps**; at 105 minutes, **1.54 bps**. The assumed cost is **20 bps**. These are descriptive break-even calculations, not revised fee assumptions or validated edges at lower fees. Original brackets support about **11.70 bps** in this sample. Fee realism matters, but lowering a backtest's fee assumption after seeing results does not establish a strategy.

Original target-hit frequency is 390/975 = 40.0% of active trades. It becomes 38.7%, 40.2% and 39.3% at 75%, 50% and 25% width respectively (25% excludes two ambiguous trades from the denominator). Smaller geometry changes speed far more clearly than success frequency. These pooled hit rates combine v1's variable reward/risk and v2's fixed 2:1, so use the per-model/protocol table for geometry-specific interpretation.

## What about combining time exits with narrow brackets, or reversing direction?

All twelve frozen scale-by-time combinations (four scales × 15/30/105 minutes) remain negative after the same costs. None has a significant paired improvement over the original. All six reversed-direction time policies also have negative pooled net means. Reversing direction does not remove the cost burden.

An always-short benchmark at 105 minutes has a positive point estimate, +0.063% net, but a wide 95% interval [−0.191%, +0.329%]. Its improvement over the AI time exit is +0.243 percentage points, with interval [−0.051%, +0.556%] and adjusted q = 0.967 across the 24 benchmark contrasts. This is a warning to control for the underlying sample's downward drift, not a confirmed always-short strategy. MA20 and visible-momentum benchmarks, reversal, every horizon and every combined policy remain visible in the full tables.

## Stability and sessions

Original brackets averaged +0.042% net in the chronologically earlier 50 windows and −0.204% in the later 50. The primary 15/30/105-minute exits and 50%/25% brackets were negative in both halves. The earlier/later split is a sensitivity summary, not a held-out test: these windows were already studied.

Entry times are also grouped into four fixed six-hour UTC sessions. Those small groups are descriptive and unadjusted; the report lists every session/policy cell. They do not define a time-of-day trading rule. No best-session filter has been selected.

## How this relates to the v3 MA-removal experiment

Do not change the v3 prompt or choose an exit using these outcomes while v3 is collecting. V3 keeps only the raw 40-candle OHLCV chart and data: it removes MA lines/values, ATR/sigma, derived movement and aggregate volume summaries. This is a broader indicator-removal experiment, not an MA-only causal test. The v2 controls are historical, not concurrent. Apply the same frozen 15/30/105-minute evaluation to both versions once outputs exist. Compare paired direction changes, confidence and uncensored paths; keep bracket variants secondary. Any chosen duration or reversal rule requires future windows untouched by this exploration.

## Verification and limits

* Reused the unmodified `nai.backtest._scan_bracket` engine: realistic gap-open fills and ambiguous simultaneous touches.
* **All 1,000 original outcomes, holding times, gross returns and net returns reproduced exactly** to numerical tolerance (4,000 checks).
* **All 100 windows have complete native one-minute OHLC through 72 hours** after entry, without missing-minute shifts.
* Evaluated **46 policies × 1,000 decisions = 46,000 policy rows**; 25 flats remain flat in all paired policies. Momentum abstains on one additional zero-input window; its paired contrast excludes that window from both sides. Original scale-1 results contain zero ambiguities. Two distinct decisions become ambiguous at 25% width; they recur in that width's capped variants.
* Window bootstrap: 10,000 resamples. Primary and secondary tests use separate prespecified BH families. Temporal-cluster sensitivity combines neighboring events at most 72 hours apart into 92 groups; its intervals also include zero for every primary difference.
* The five models and two protocols are correlated evaluations of the same 100 SOL windows. Their repetitions do not broaden market coverage. Most resumed v2 OpenAI calls changed collection harness, which limits clean protocol attribution.
* Minute OHLC cannot order two touches in the same minute. Paired tests exclude ambiguous pairs; full stop-first/target-first bounds are provided, without claiming either order.
* Results are per-decision means, not portfolio returns. No capital constraints, funding, extra slippage, market impact or sizing optimization are modeled. No result is an independent confirmation or out-of-sample strategy validation.
* Input and source hashes were checked after analysis; original files remain unchanged.

## Files

- `index.html`: standalone local report and complete grouped tables.
- `per_trade_policies.csv`: all 46,000 individual policy outcomes, original comparison and ambiguity bounds.
- `policy_summary.csv`: all pooled and model/protocol policy cells with window-bootstrap intervals.
- `paired_vs_original.csv`: every primary/secondary paired test, ambiguity bounds and temporal-group sensitivity.
- `benchmark_contrasts.csv`: all baseline/reversal comparisons.
- `half_summary.csv`, `utc_session_summary.csv`, `break_even_costs.csv`: descriptive diagnostics.
- `PLAN.md`, `run.py`, `build_report.py`, `audit.json`, `engine_audit.json`: frozen plan, reproducible computation and audit.

## Post-hoc appendix: regime and original direction

This appendix was requested after the pooled results were available. All pre-entry MA regimes × original action cells are reported, for all seven primary/reference policies; no significance tests or selected filter are claimed. Flat rows are kept visible. Means first average the available decisions within each window and then average windows. Long and short strata can cover different overlapping sets of windows, so their difference is not a paired causal comparison.

The 456 original **short decisions below both MAs** cover all 50 below-both windows. Their equal-window gross/net averages are **+0.201%/+0.001% at 15 minutes**, **+0.197%/−0.003% at 30 minutes**, and **+0.258%/+0.058% at 105 minutes**. Because every one of those 50 windows has a short decision, the pure-time result is exactly what simply shorting every below-both window would produce. It does not establish an AI contribution.

The earlier **68%** first-candle directional accuracy refers to **34 of 50 v2 majority decisions/windows**, not every model row. In this appendix, 314/456 below-both short model decisions have positive gross 15-minute movement (68.9%); 220/456 do at 105 minutes (48.2%). Those counts weight windows according to how many models shorted, so they are different estimands. Accuracy can fall while mean return rises because movement sizes also differ.

The 243 **long decisions above both MAs** cover 29 windows. Equal-window gross averages are **−0.128%, −0.086% and −0.386%** at 15, 30 and 105 minutes; net averages are **−0.328%, −0.286% and −0.586%**. This is a descriptive continuation-failure pattern worth retaining for fresh-window evaluation, not a validated filter or a reason to select a reversal policy now.

See `posthoc_regime_direction.csv` for every pooled/v1/v2 cell and its decision/window counts and ambiguity bounds. Small countertrend and mixed-regime cells are included rather than hidden.

## Post-hoc risk normalization: smaller width is not automatically weaker direction

This descriptive diagnostic was added after inspecting the percentage-return results. One R is the trade's **scaled stop distance**: gross R = gross return percent / (original stop fraction × scale × 100), with net R defined the same way. The table averages active, unambiguous decision rows; flats and ambiguous rows are excluded. It is not an executable position-sizing or leverage recommendation. No new significance tests are performed.

| Protocol | Width scale | Known / active | Ambiguous | Target hits | Gross R | Fee R | Net R |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | 1.00 | 475 / 475 | 0 | 42.74% | +0.082 | 0.234 | −0.152 |
| v1 | 0.75 | 475 / 475 | 0 | 42.74% | +0.097 | 0.312 | −0.216 |
| v1 | 0.50 | 475 / 475 | 0 | 42.95% | +0.099 | 0.469 | −0.370 |
| v1 | 0.25 | 474 / 475 | 1 | 42.83% | +0.105 | 0.937 | −0.832 |
| v2 | 1.00 | 500 / 500 | 0 | 37.40% | +0.122 | 0.246 | −0.124 |
| v2 | 0.75 | 500 / 500 | 0 | 34.80% | +0.044 | 0.327 | −0.283 |
| v2 | 0.50 | 500 / 500 | 0 | 37.60% | +0.128 | 0.491 | −0.363 |
| v2 | 0.25 | 499 / 500 | 1 | 35.87% | +0.076 | 0.982 | −0.906 |

**The half-width v2 gross expectancy is essentially unchanged in the observed sample: +0.128 R versus +0.122 R originally.** The quarter-width value is +0.076 R; the pattern across widths is not monotonic. Meanwhile fees rise from 0.246 R to 0.491 R at half width and 0.982 R at quarter width. V1 gross expectancy also stays in a narrow +0.082 to +0.105 R range. Therefore falling percentage returns should not be presented as proof of weaker directional expectancy; shrinking risk distance mechanically reduces the percentage scale while magnifying fixed fees in R.

V1 has variable target/stop ratios, so its hit rate cannot be interpreted using v2's fixed 2:1 payoff assumption. Exact gap-open fills can produce small differences from idealized +2 R/−1 R payoffs in v2. Counts are correlated decisions on the same windows, not independent samples. `posthoc_risk_normalization.csv` and `.json` include all four scales, ambiguity counts and supplementary equal-window means.


## First-candle count correction

Correction: the earlier 70% / 35-of-50 statement counted one exactly unchanged first-candle close as a decline. The correct result is 34/50 (68%), with 15 adverse and one unchanged; 34/49 (69.4%) if the tie is excluded. Seven-candle correctness remains 24/50 (48%). Return values and existing return-based tests are unchanged.


## Follow-up: typical path versus a few large moves

Rechecking all 50 below-both-MA windows: 34 (68%) move in the short direction at 15 minutes, 15 move against it, and one is unchanged. At 105 minutes only 24 (48%) remain favorable. Fifteen of the 34 initially correct calls are wrong by minute 105. The median signed move falls from +0.158% to −0.010%, despite the mean increasing from +0.201% to +0.258%.

That difference is concentrated in the upper tail: the three largest favorable 105-minute moves account for 82.8% of the total signed movement across all 50 windows. Excluding those three as a sensitivity reduces the gross mean from +0.258% to +0.047%. This is not an executable exclusion rule; it shows why a declining hit rate and a rising average can coexist. The average favorable 105-minute move is +1.225%, versus −0.634% for unfavorable moves. These are simple below-both short paths, not evidence of incremental AI information.

The four fixed UTC entry-session summaries also differ descriptively: at 105 minutes, pooled direction-signed gross movement averages +0.318%, +0.014%, −0.259%, and −0.003% for 00–06, 06–12, 12–18, and 18–24 UTC respectively, on 26,23,27,24 windows. These are entry-time strata, not a rule for exiting at a clock time. No regime/year adjustment or held-out session test establishes an independent time-of-day effect.
