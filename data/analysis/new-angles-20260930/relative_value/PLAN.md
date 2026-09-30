# Relative-value AI ranking study: finite discovery plan

This plan freezes a new mechanism before its computation: within the same timestamp, does the model rank four assets' relative future performance incorrectly? All outcomes have already been examined in previous studies, so this entire exercise is discovery. It cannot supply a fresh validation claim. No new model, API or trade-snapshot calls are permitted. Existing L048 and S508 rules are not modified.

Use all 125 simultaneous SOL/BTC/ETH/DOGE blocks from `gross-edge-500-20260929T204545Z`, with the existing independent Terra opinions and audited native-minute path cache. Entry is each asset's first minute open after its visible chart ends. Exit is its native close at elapsed240 minutes. No alternative horizons, stops, targets, confidence cuts, regimes, asset subsets or risk-scaling variants are searched. Returns are zero-cost and unlevered, per total gross notional.

## Twelve fixed policies

In each four-asset block, rank one of six pre-entry scores below. A **reverse** basket allocates +0.5 divided equally among assets tied for the minimum score, and −0.5 divided equally among assets tied for the maximum. A **follow** basket is its exact negative. All-score-equal blocks skip with zero return. A tie is exact equality of the provided/calculated scores, with no outcome-dependent tolerance or tie breaking. Every active basket has zero net dollars and unit gross notional. This is dollar neutrality, not estimated beta neutrality.

1. `AI_direction`: +1 for model LONG, −1 for model SHORT. Thus the reverse basket buys all AI SHORT assets and shorts all AI LONG assets, equally within sides; it acts only on direction-disagreement blocks.
2. `AI_confidence`: action sign × reported confidence. The reverse basket buys the model's most bearish conviction and shorts its most bullish conviction. This can compare differing confidences even when all action directions agree.
3. `AI_stop_ATR_conviction`: action sign × confidence / (model stop percentage / pre-entry ATR14 percentage). Convert the model's fractional stop to percentage points before dividing. This explicitly tests the hypothesis that tighter proposed risk relative to observed volatility expresses conviction; it does not assume that confidence or stop ratios are calibrated forecasts.
4. `price_momentum`: visible-window price return percentage. This uses the same extreme-rank basket construction without AI.
5. `price_MA20_ATR`: ((100 / normalized MA20 −1) ×100) / ATR14 percentage. This ranks the visible price's pre-entry distance from MA20 in ATR units, without AI.
6. `price_ATR`: pre-entry ATR14 percentage. This ranks relative pre-entry risk alone, without AI.

Each score has reverse and follow directions: **12 policies total**. The final six are the matched price-only controls; their entries, exit, tie handling and unit gross notional are identical. Also report controls restricted to an AI policy's active blocks strictly as conditional diagnostics: that restriction is AI-dependent and must not be called an independent price-only strategy.

## Evaluation fixed before scoring

Chronologically order all 125 blocks and divide into five contiguous25-block folds. Report every fixed policy on every fold. Use the first25 as the initial historical prefix, then report expanding prior prefixes of25/50/75/100 against the next25-block fold. No parameter, sign, basket rule or policy choice is fitted or changed from one fold to the next. These are chronological transfer diagnostics on already-examined data, not untouched out-of-sample validation.

Report active frequency, mean per active block and per sampled opportunity, median, win rate, average wins/losses, profit factor, worst block, exclusion of the best1/3blocks, chronological halves, quarters, leave-one-quarter-out, asset weight/contribution concentration and top1/3blocks. Compare each reverse policy to its following mirror and all six price-only policies. Use20,000 whole-block bootstrap draws with seed2026093018 and whole-quarter draws with seed2026093019 for descriptive95% intervals, including paired control differences. There are no new statistical verification or profitability claims after this search.

For direct ranking diagnostics, report each score's per-block Spearman correlation with four-hour asset returns, handling ties with average ranks. Undefined correlations on equal scores are omitted only from that diagnostic. Report correlation with the equal-weight four-asset return to reveal possible residual common-market exposure; dollar neutrality does not imply beta neutrality. Save the entire policy×125 block return matrix, weights, active masks, asset returns and identifiers for independent or family-level analysis.

At most two AI reverse research candidates may be described, and only if each has at least40 active blocks, positive means in both chronological halves, positive mean in at least3 of the4 later25-block folds, positive mean across all100 later blocks, positive mean after removing the best3blocks and positive minimum leave-one-quarter-out mean. A passing candidate still needs a convincing distinction from matched price-only controls; otherwise report no AI-specific candidate. This finite support screen is a discovery triage rule, not a formal validation criterion. No hindsight winning follow arm or price-only control is promoted to an AI-reversal discovery.
