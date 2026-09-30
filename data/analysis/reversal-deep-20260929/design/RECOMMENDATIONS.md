# Frozen validation design recommendations

This is a design review, using only previously reported discovery results, existing entry timestamps, input features, and data-coverage checks. No fresh future returns or fresh model decisions were inspected.

## Why a 57% win rate still loses

Expected gross return is `p × average winner − (1 − p) × average loser`. Using 24/42 winning shorts, average winner 0.764%, and average loser 1.498%, this is approximately −0.205% per trade. The gross break-even win rate is 66.2%; with 0.20 percentage points roundtrip costs it is 75.1%. At the observed win rate and unchanged winners, average loss would need to fall to about 0.552% merely to break even after costs.

A stop cannot be evaluated by truncating the final losing returns. Trades that eventually win can touch the stop first, stop orders can fill through their level on gaps, and intraminute order can be unknown. Recompute every trade from minute OHLC, penalize ambiguous same-bar target/stop hits conservatively, and include a same-rule control. Path-dependent stops must be frozen before fresh validation.

## Use the new calls for confirmation

1. Treat all existing 100 original windows and 50 recent random windows as discovery data. Model opinions on the same window are not independent observations. The 20 no-MA windows overlap old windows and cannot count as additional independent outcomes.
2. Search execution choices freely on discovery, record all searched families/counts, and select one primary candidate before generating fresh outputs. If two candidates remain, freeze both and use familywise correction on their primary confirmation tests. Do not select the winner after validation and report its unadjusted interval.
3. If there is no credible discovery candidate (adequate coverage and positive net returns across meaningful chronological folds), do not spend fresh calls merely to produce activity. If there is a candidate, freeze a single fresh sample. Target 280 valid snapshots, reserve 20 physical calls for failures, and enforce at most 300 total launches including retries. A smaller fixed sample is justified by archive capacity or an explicit power calculation.
4. Freeze sampling seed, all window IDs, model version, input treatment, eligibility filter, entry latency, execution rules, costs, statistical tests, and success thresholds before fresh output collection. No new filter, stop size, holding period, or confidence cutoff may be selected using fresh validation outcomes.
5. Collect all decisions without displaying outcome summaries. A progress dashboard can report counts and auditing errors only. Evaluate once after the fixed sample completes. Results from incomplete batches must not trigger changing the model or strategy.

## Non-overlap and feasible capacity

The original inputs use 200 × 15-minute bars, or 50 hours of indicator history. Older bracket labels extend 72 hours. For a new candidate with at most 24 hours of forward evaluation, disjoint complete information intervals require:

- New later than old: new entry at least 122 hours after old entry.
- New earlier than old: new entry at least 74 hours before old entry.
- Two new entries: at least 74 hours apart.

If retaining 72-hour new outcomes, use 122 hours between new entries and symmetrically around old entries. With 156 old SOL entry times excluded, that stricter design has at most 210 eligible nonoverlapping slots before minute coverage checks, and ordinary random-permutation greedy sampling yields about 164–170. It cannot support 300 fresh independent windows. `capacity.json` records the shorter-horizon design's actual minute-coverage checks and sampling capacities.

A 24-hour cap permits many reasonable stop/target policies while preserving enough fresh independent windows. If it changes the chosen candidate, that change must be made using discovery first. Do not relax separation after looking at validation outcomes. Disjoint intervals reduce shared-data dependence but do not remove market-regime dependence.

## Primary estimands and controls

- Report arithmetic mean gross and net return per executed trade, total eligible opportunities, number of executions, gross and net positive-return rates, median, average winner/loss, realized payoff ratio, largest loss, exit causes, duration, and stop-before-eventual-winner frequency on discovery.
- Also report net return per eligible opportunity, assigning zero to skipped trades. This makes selection strategies comparable without ignoring their frequency.
- Use next-minute open after the decision candle as the primary executable entry convention, or a frozen one-minute-later sensitivity if preserving close entry. Do not imply either simulates actual model inference latency. All variants use the same costs and execution engine.
- Compare reversal with following the same AI, always-long, and always-short using the identical entry, bracket, horizon, and price/regime eligibility. For selected directions, compare selected windows with all eligible windows under the same side and policy.
- Test positive net expectancy and incremental AI value separately. Positive profit does not show AI is useful if the matched price-only policy performs as well. A strategy can have an exploratory positive point estimate without passing confirmation.
- Preserve calendar regimes in the AI-selection null: permute AI labels within prespecified broad year/regime strata, preserving counts. Avoid strata so fine that no label variation remains. A propensity-matched or residualized price-only comparison can be descriptive, but fitting it on validation outcomes contaminates confirmation.

## Suggested confirmation criteria

For one frozen primary rule, require the lower bound of a two-sided 95% mean-net-return confidence interval to exceed zero, sufficient trigger count (at least 50 independent executed trades preferred), and a positive incremental AI-selection effect with its prespecified test passing 5%. If confirming two rules, use Holm correction for their profit tests and separately their AI-lift tests; simultaneous confidence intervals are clearer. State the requirement as two co-primary claims rather than multiplying claims opportunistically.

Show prespecified calendar-year or chronological-third results, a block-bootstrap/regime sensitivity, a 30-bps cost sensitivity, and conservative same-minute ambiguity handling. These are robustness diagnostics; do not require every tiny year subgroup to be significant. A win driven by one outlier or one period needs qualified language even if a naive bootstrap passes.

Rare rules are a power constraint. A 16% trigger rate produces only about 45 executions in 280 calls; adding a macro filter may leave much less. Sampling can deliberately restrict to a price-based eligibility condition chosen on discovery, but cannot target particular future AI decisions or continue until a desired number of favorable outcomes occurs. Insufficient precision is a valid inconclusive result, not permission to repeatedly change the rule and call the next result validation.

## What may be claimed

Passing these tests supports a historical, previously unused-window validation result for the frozen strategy and data source. It does not establish unknown-to-training data, live execution profitability, general asset applicability, or an enduring edge. If the primary test fails, preserve the failure and report any additional analysis as discovery requiring a new untouched sample. The user request to keep searching cannot make a losing strategy profitable or justify hiding unsuccessful trials.
