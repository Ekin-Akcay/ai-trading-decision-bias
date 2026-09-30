# Relative-value ranking discovery

The model did **not** systematically rank relative winners and losers backwards in this sample. All three predeclared reversed-AI baskets lost on average; none passed the fixed stability screen. There is no AI-reversal relative-value research candidate from this exercise.

The confidence-following mirror is a useful opposite-hypothesis observation: it has a positive mean and better chronological stability, but wide intervals, substantial asset/period contribution concentration, and no established advantage over matched price-only controls. It is not promoted to a validated strategy or a reversal candidate.

This is a new question about simultaneous **relative performance**, distinct from the previous directional rules and the SOL/BTC hedge study. It uses all 125 existing four-asset timestamps. Every outcome was previously examined, so the entire result is discovery. **No model/API/snapshot calls were made.**

## Fixed experiment

The plan in `PLAN.md` froze 12 policies: direction, signed confidence, and signed confidence divided by stop/ATR, each reversed and followed; plus momentum, MA20-distance/ATR and ATR-only rankings in both directions. No stop/target, exit, threshold or asset-subset grid was run.

At each timestamp, each active basket buys the minimum-score assets with total long weight0.5 and shorts the maximum-score assets with total short weight0.5; following flips those weights. Ties split equally. All-equal scores skip. Each active basket therefore has zero net dollars and total gross notional1. Entry is each asset's first minute open after the visible chart; exit is the minute close at elapsed240 minutes. Gross returns assume zero costs and no additional leverage.

Dollar neutrality does not guarantee beta neutrality. This study deliberately tests within-time ranking, not another estimated BTC hedge. All comparisons use the same four assets, entry, horizon, weight construction and gross notional. Controls with an AI policy's skip mask are explicitly conditional AI-gated diagnostics, not independent price-only strategies.

## Reversed ranking results

| Reversed AI score | Active blocks | Mean per active basket | Mean per all125 opportunities | First/second half, per opportunity | Positive later25-block folds | Mean after best3 active blocks removed |
|---|---:|---:|---:|---:|---:|---:|
| Direction only | 48 | −0.1571% | −0.0603% | −0.0887% / −0.0315% | 2/4 | −0.2535% |
| Signed confidence | 123 | −0.1330% | −0.1309% | −0.1825% / −0.0784% | 1/4 | −0.2424% |
| Confidence ÷ stop/ATR | 125 | −0.0384% | −0.0384% | −0.0842% / +0.0082% | 2/4 | −0.1378% |

Only 48 timestamps contain differing action directions across the four assets. That is the support for the direction-disagreement basket; it is not 192 independent observations. Confidence distinguishes nearly all remaining timestamps, but reversing that ranking performs worse.

The direct per-block Spearman correlations with future asset returns also point away from the inverted-ranking hypothesis: direction **+0.116** on48 defined blocks, confidence **+0.100** on123, and stop/ATR conviction **+0.059** on125. The price-only MA20-distance rank has **+0.107**, so a modest positive AI rank correlation alone does not establish unique AI information. These are descriptive mean rank correlations, not statistically validated effects.

## Following mirror: observation, not promotion

Following signed confidence averages **+0.1330% per active basket** on123 blocks, or **+0.1309% per sampled opportunity** including two skips. Its win rate is57.72%, profit factor1.634, median+0.0681%, and mean after removing its largest three gains+0.0661% per remaining active basket.

Its five chronological25-block means per opportunity are +0.0600%, +0.4102%, −0.1401%, +0.2844% and +0.0397%. Both chronological halves are positive, and its later100-block mean is+0.1486%. No rule was fitted or changed between folds; `expanding_prefix_transfers.csv` reports every expanding historical prefix and subsequent fixed25-block fold. Because the outcomes were already examined, these are transfer diagnostics rather than untouched out-of-sample validation.

However, its 95% whole-block interval is **[−0.0716%, +0.3013%]** and its whole-quarter interval **[−0.0259%, +0.3034%]**. Every policy in the entire12-policy family has intervals including zero. No multiplicity-adjusted verification is claimed.

Three further limits matter:

- **Controls:** the standalone momentum-reversal price control averages+0.0735% per opportunity; MA20-follow averages+0.0472%; low-ATR-long/high-ATR-short averages+0.0365%. Confidence-follow's skip-matched advantage over momentum reversal is only+0.0589 percentage points per opportunity, with block95% interval[−0.3604, +0.4185] and quarter interval[−0.2954, +0.4283]. AI's incremental value is unresolved. Those following contrasts are exact sign mirrors of the predeclared reverse-versus-price comparisons, not additional policy tests.
- **Concentration:** ETH positions contribute+0.1008 points of the basket's+0.1309-point mean, approximately77%. BTC contributes−0.0351, SOL+0.0365 and DOGE+0.0285. The three best calendar quarters supply76.7% of the summed basket returns. Sixteen of25 quarters are positive; removing any single quarter still leaves a positive mean, with minimum+0.0771%. The largest three blocks supply51.5% of the summed return. These sums describe contribution and are not compounded portfolio returns.
- **Risk/exposure:** the worst single basket is−8.3586%, versus the best+3.2040%. Correlation with the equal-weight four-asset return is−0.276 despite zero net dollars. A positive confidence-follow mean is therefore not evidence of a riskless or fully market-independent spread.

Following confidence would need its own clearly stated hypothesis and untouched test if pursued later. Selecting it now because the reversal failed would not validate the user's AI-is-wrong mechanism. This exercise recommends **zero primary AI-reversal candidates**, while preserving the opposite observation for honest future research.

## Artifacts and verification

`relative_value_family.npz` contains the complete12×125 gross-return matrix, active masks,12×125×4 weights,500 asset returns, score arrays, identifiers and chronological folds. The block axis is chronological; original block IDs remain stored. `all_policies.csv`, `chronological_folds.csv`, `expanding_prefix_transfers.csv`, `quarter_breakdown.csv`, the two control-comparison CSVs, `asset_weight_contributions.csv`, `cross_sectional_rank_correlations.csv` and `largest_blocks.csv` preserve every declared result.

`relative_value_profile.png` displays all policies and chronological folds. `summary.json` retains the finite stability criteria and no passing reversed-AI candidate. `audit.json` records source hashes, all1,500 scalar basket payoff checks, and another7,560 independent rank-weight/fold checks. All zero-net/unit-gross constraints, paired following/reversal identities, source alignment and unchanged-input hashes passed. The native price cache was previously audited against the original minute files; this study reuses that proven cache rather than claiming a second native-price audit.
