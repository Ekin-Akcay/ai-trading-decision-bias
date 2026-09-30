# Frozen behavior proxy: fresh replication failed

The earlier price-only proxy edge did not transfer clearly to new calendar targets. Fading its predicted AI direction averaged **+0.00883% per four-asset basket (0.883 basis points)** across 783 new timestamps. Neither the gross-profit claim nor the increment over the fixed MA20 comparator passed. No side, asset or alternative control is promoted.

This test used **zero new AI/API/snapshot calls and zero refits**. The existing annual models predicted AI choice from pre-entry price/volume features; they were not trained to predict market returns. The old post-score comparator averaged +0.1612% on 803 previously studied asset windows. That old number and this new result come from different sampling populations, so their difference is evidence of weak historical transfer, not a paired estimate of performance decay.

## Frozen new sample and economics

The complete eligible UTC 00/06/12/18 grid yielded 783 simultaneous SOL/BTC/ETH/DOGE blocks, 3,132 asset trades, 192 calendar weeks and 19 quarters during 2022–2026. Every four-hour target avoids the full known 50-hour input history plus 6/24/72-hour outcome interval of all 681 prior exposed calendar events. Pre-entry histories may reuse known prices; targets do not overlap one another. No count target, refit, threshold, regime gate or outcome-based extension was used.

Each year's frozen model buys when predicted P(AI SHORT) ≥ 0.5 and sells otherwise. Four assets receive equal quarter notional; entry is the first native minute open, exit the close at 240 minutes, costs zero. The fixed MA20 comparator buys when normalized MA20 ≥ 100 and sells otherwise.

| Fixed policy | Mean basket gross return | Basket win rate | Mean after removing best 3 blocks |
|---|---:|---:|---:|
| Proxy fade, sole primary | +0.00883% | 52.23% | −0.01377% |
| Proxy-follow mirror | −0.00883% | 47.77% | −0.03398% |
| Always long | +0.01760% | 54.15% | −0.01256% |
| MA20 fade, primary competitor | −0.00185% | 49.81% | −0.02514% |

The proxy's 99% whole-week interval is **[−0.09351%, +0.10856%]**; its 95% whole-quarter interval is **[−0.04316%, +0.05755%]**. Its paired increment over MA20 is **+0.01069 percentage points**, with weekly 99% interval [−0.08886, +0.10952] and quarter 95% interval [−0.07409, +0.09807]. Neither establishes a positive effect. These intervals preserve simultaneous asset dependence and resample entire weeks or quarters with their observed block counts.

The profit gate passes support only and fails both interval requirements, positive halves, best 3 removal and positive leave-one-asset-out means. The MA20-increment gate additionally passes halves and leave-one-asset-out stability, but fails both intervals and best 3 removal. `CANDIDATE_GATE.json` records every condition.

## Stability and the user's long preference

Primary basket means by year are 2022: +0.07582%, 2023: −0.01456%, 2024: −0.02651%, 2025: +0.06371%, 2026: −0.02933%. Chronological halves are −0.00600% and +0.02370%. Removing the single best block already makes the pooled mean −0.00276%; removing the best three makes it −0.01377%. The worst basket is −9.22548%, versus the best +9.07360%. Arithmetic return sums are contribution diagnostics, not compounded portfolio returns.

Per-asset means are SOL −0.00231%, BTC −0.00047%, ETH −0.04045%, and DOGE +0.07855%. Removing DOGE leaves a three-asset mean of −0.01441%. This does not justify selecting DOGE after seeing outcomes; the prespecified pooled result fails.

The descriptive **long leg** has 2,022 trades averaging **+0.02047%**, with 52.72% wins. It contributes +0.01322 percentage points per complete four-asset opportunity. The **short leg** has 1,110 trades averaging **−0.01237%**, with 51.62% wins; its contribution is −0.00439 points. These sum to the primary +0.00883%. The leg split was pinned before returns, but it is not a separate tested strategy or a significance claim. The more attractive long point estimate does not replace the failed two-sided primary.

## Verification and conclusion

Before scoring, an independent audit reconstructed all 3,132 features/probabilities, reproduced the exact 783-point grid and checked 533,223 prior-interval exclusions, annual training embargoes and unchanged hashes. The frozen classifier also reproduced all 803 previous forward probabilities within 5.42×10⁻¹⁴. Scoring checked 3,132 native 241-minute paths and 12,528 scalar trade calculations. The independent final audit passed: it reproduced every native path and trade payoff, all 20,000 weekly/quarter bootstrap arrays, the fixed gates and all 80 leg-accounting rows. Its record is `../audit/proxy_final_statistics_audit.json`.

`PLAN.md` and `BEFORE_SCORING_ADDENDUM.md` precede scoring. `frozen_sample.json` and `frozen_features_predictions.csv` preserve the sample and decisions; `SCORING_FREEZE.json` records the locked scorer. `window_results.csv`, `basket_results.csv`, `directional_contributions.csv`, `calendar_breakdown.csv`, `policy_vectors.npz`, `paths.npz`, `bootstrap_arrays.npz`, `summary.json` and `evaluation_audit.json` retain the complete calculation. `proxy_replication.png` is the overview.

This is a failed fresh-target historical replication of a frozen price-only behavior proxy. It is useful evidence against assuming that the earlier AI-fade result represented a stable general mean-reversion effect. It does not prove that all future expectancy is zero, and it supplies no verified profit or incremental-AI claim. No further model calls were used or recommended by this test.
