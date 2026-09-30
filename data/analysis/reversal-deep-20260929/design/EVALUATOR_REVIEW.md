# Evaluator review before fresh outcomes

Reviewed `data/sim/reversal-validation280-20260929T194012Z/evaluate.py`, `risk/validation_engine.py`, and the locked validation protocol by reading code only. Did not run the evaluator, read fresh returns, or inspect agent outputs.

## Matches the frozen statistical design

- 20,000 shared whole-window bootstrap draws, seed 2026092930; subgroup means recomputed within each resampled window set.
- 95% intervals and Bonferroni-compatible 97.5% two-sided intervals for two primary profit claims.
- Whole-calendar-quarter cluster resampling, with variable subgroup denominator retained, and chronological-third summaries.
- 20,000 shared conditional permutations, seed 2026092931, within the nine declared era × MA-regime strata.
- L moves the action label, leaves confirmation and subsequent returns attached to receiver windows, and recomputes the selected-trade mean.
- S jointly moves action and stop/ATR ratio; the donor geometry is scaled by receiver ATR and actual bracket paths are replayed. The payoff matrix diagonal is compared with original S outcomes.
- One-sided conditional permutation p-values use finite-simulation plus-one correction; Holm adjustment of two tests is implemented correctly.
- L confirmation/entry/exit indices are 15-close, 16-open, and 255-close, respectively, giving a 240-minute hold after confirmation. Both delayed-entry sensitivities retain the original exit clock.
- S uses 1.5 times supplied stop percent and a target at twice that strategy stop. Price-only ATR controls and the equal-distance diagnostic match their declared geometry.
- Conservative bracket engine processes open gaps before intraminute level touches, fills adverse stop gaps at open, caps favorable target gaps at target, and assigns ambiguous double touches to stops.

## Changes requested before evaluation

1. The original implementation combined every verification boolean with `all(...)`. This added requirements that all three chronological-third means be positive and that the cluster simultaneous interval also exclude zero. Those are stronger than the locked primary criteria. Separate primary profit verification, AI-contribution verification, and descriptive robustness diagnostics. Any exact interpretation of the protocol's single-period-support limitation should be stated before outcome inspection, rather than silently adding or removing significance requirements afterward.
2. Explicitly handle zero executed trades or zero valid conditional selections. The current `stats()` zero-count return lacks fields accessed later, and S's null can divide by zero if every action is short. Such cases should produce an unverified/no-selection result rather than crashing.
3. In addition to checking 280 accepted outputs, assert that each accepted decision's agent path belongs to the passed isolation-audit set. The collector already filters this way; verifying the relationship again at scoring protects against stale or mismatched checkpoint files.

The bootstrap and permutation machinery was not executed during this review. Conditional permutation inference still assumes exchangeability within broad strata; it cannot establish causal AI value after accounting for every possible price feature.
