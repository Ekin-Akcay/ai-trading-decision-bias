# Information beyond the model's raw direction — frozen discovery plan

This plan is written before computing the signal family below. Every outcome has already been exposed in earlier research. This is reused-outcome discovery, not fresh verification. No trade-agent, model API, or model CLI calls will be made. Fees are zero at the user's request. All earlier failed primary tests remain failed.

## Novelty and data

Earlier `direction-paths-20260929` work already examined confidence thresholds, lexical reason categories, unanimity, and randomly assigned grouped cross-validation. Repeating those associations would not be a new mechanism. The extension here is **forward-calendar prediction of what the AI normally says from the price information it receives**, followed by fixed policies using unexpected choices, unusually high confidence, or unexpected rationale mentions. Price features must predict the AI information using earlier calendar years only. The separate paired-input policies ask whether repeat disagreement or disagreement caused by removing MAs has economic meaning; the earlier paired experiment tested overall arm means and flip frequency.

Use the original 150 SOL windows, later 280 SOL windows, 500 four-asset windows, and primary MA_A decision on each of the 90 paired SOL windows. This is 1,020 distinct asset/window events, not 1,200 independent events. The extra MA_B/NO_MA decisions are used only for the two explicitly paired rules. Save all source hashes. No new sampling or outcome-based exclusions.

## Timing and training

One execution convention for every rule: entry at the first native minute open following the visible 15-minute history, exit at the close of minute 240. No stop, target, macro gate, delay optimization, or alternative horizon. Short returns are the negative underlying percentage change with fixed initial notional; these are per-trade arithmetic returns, not a compounded portfolio claim.

2020–2021 provide the initial training period. Test folds are calendar years 2022, 2023, 2024, 2025, and 2026, with all assets at the same time in the same fold. At each January 1, train only on earlier entries at least seven days before that date. All subsequent years remain out of that fit. Models train only on existing MA-present primary decisions; no outcome enters fitting the AI-action, confidence, or reason models. Refit once annually; no hyperparameter search. If a training fold has fewer than 50 observations, mark it unavailable rather than relaxing this rule.

Five numeric price inputs are fixed: (100−MA20)/ATR%, (100−MA50)/ATR%, visible return/ATR%, log(volume ratio), and log(ATR%). Add fixed BTC/ETH/DOGE asset indicators with SOL as reference. Standardize numeric inputs using training-only means and standard deviations. These are inputs supplied to the model, not latent forward data. Any input missing or nonpositive where logged causes an explicit coverage failure, not silent median imputation.

Fit AI SHORT probability by logistic regression with sum logistic loss plus L2 coefficient penalty 10/2; do not penalize the intercept. Fit confidence by ridge regression with sum squared error plus 10 times squared coefficients. Confidence and each rationale model also receive the actual AI action, since the aim is information beyond the raw direction. Confidence predictions are clipped to [0,1]. Reason models use the same fixed logistic specification. A one-class training target uses Laplace-smoothed training prevalence. Numerical optimization may improve convergence but not change the objective or features.

## Eleven fixed candidate definitions

All thresholds below are semantic defaults (.5 for a binary prediction or zero residual), not optimized values. Rationale definitions are literal, case-insensitive mentions, not claims to recover hidden reasoning or resolve negation. Tags may overlap. Do not add words after scoring.

1. **Unexpected bearish call:** buy when AI chooses SHORT but its price-only predicted SHORT probability is < .5.
2. **Unexpected bullish call:** short when AI chooses LONG but its price-only predicted SHORT probability is > .5.
3. **Confident unexpected bearish call:** rule 1, additionally actual confidence > confidence predicted from price plus actual action.
4. **Confident unexpected bullish call:** rule 2, with the same positive confidence residual.
5. **Unexpected exhaustion rationale:** fade actual AI direction when the reason mentions `exhaust`, `overbought`, `oversold`, `overextend`, `over-extend`, `mean reversion`, `mean-reversion`, or `stretched`, and that tag's predicted probability from price plus actual action is < .5.
6. **Unexpected break rationale:** fade actual AI direction when the reason mentions `breakout`, `breakdown`, `break out`, `break down`, `broke above`, or `broke below`, and predicted tag probability is < .5.
7. **Unexpected rejection rationale:** fade actual AI direction when the reason mentions `reject`, `failed`, `failure`, `stalled`, or `stalling`, and predicted tag probability is < .5.
8. **Unexpected continuation rationale:** fade actual AI direction when the reason mentions `continu`, `persist`, `momentum`, `trend`, `higher lows`, or `lower highs`, and predicted tag probability is < .5.
9. **Unexpected counterevidence wording:** fade actual AI direction when the reason contains a whole-word `despite`, `although`, `however`, `but`, or `yet`, and predicted tag probability is < .5.
10. **Repeat disagreement with independent-view tie break:** on paired90 only, when MA_A and MA_B disagree, follow NO_MA's direction.
11. **MA-removal reversal of a stable call:** on paired90 only, when MA_A=MA_B and NO_MA differs, follow NO_MA's direction.

Rules 10–11 need no fitted auxiliary model and use all 90 paired windows; their separate cohort and limited sample prevent treating them as across-cohort confirmation. The other nine use only forward-fold predictions. Raw AI fade, unconditional long, and short are declared comparators, not extra finalists. Report long and short legs of mixed rules as descriptive decomposition, never select a previously unregistered leg as a new winner.

## Controls and inference

For every selected trade, compute a price-matched baseline using all eligible windows in the same cohort × asset × calendar era (2020–21, 2022–23, 2024–26) × pre-entry MA regime (above both, below both, mixed), retaining its selected trade direction. This baseline ignores AI information. Also compute a raw-direction-conditioned comparator by adding the actual model action to the same groups. For paired rules, the reference action is NO_MA; for the other rules it is the primary action. The latter is deliberately not called AI-free: it measures increment beyond direction. Use each stratum's inclusive mean; report all-selected strata, mixed strata, and the fraction with a genuine selected/nonselected contrast. Do not pretend all-selected strata establish incremental selection information.

Report every rule by old150/new280/fourasset500/paired90 cohort, asset, chronological test year, and quarter. Save full per-window selection, side, return, both control expectations, and residual returns. Report mean, median, win rate, worst/best, removal of best 1/3, chronological halves, and leave-one-calendar-year-out means. Paired policies must keep all three arms of a window together.

Use 20,000 fixed-seed quarter-cluster resamples, keeping all same-time assets and nearby events in the same quarter. Produce 95% intervals for return and both incremental returns, and conservative 11-comparison Bonferroni bootstrap intervals as descriptive family diagnostics. Seeds and every vector must be saved. These are conditional on the historically fitted models and do not estimate every source of training uncertainty. No interval converts reused outcomes into independent verification.

A candidate may be recommended for a later, separately frozen test only if it has at least 40 scored trades, at least 10 trades in three separate cohorts with positive gross means and positive direction-conditioned increments in each of those cohorts, at least three test years with 10 trades and positive means, positive mean after removal of its three best trades, and positive aggregate direction-conditioned increment. Show whether ordinary and family intervals exclude zero; do not waive criteria to return a candidate. At most two recommendations; zero is acceptable. Paired-only policies cannot meet the cohort rule and remain mechanism diagnostics even if their local mean is attractive.

No rewriting old L048/S508, no holding-time or stop grid, and no additional trade-model calls.
