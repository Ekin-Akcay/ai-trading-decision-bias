# BTC leader / traded-asset lag at existing AI decision moments

Frozen before scoring this family. This is reused-outcome discovery, not fresh verification. No new trade-agent, model API, or model CLI calls. Preserve the 29 unused credits and all prior outputs. Work only in this folder.

## Events and clock

Use exactly the 1,020 primary Terra MA-present asset/window events in `data/analysis/new-angles-20260930/target_exhaustion/windows.csv` and its aligned `paths.npz`. These consist of original100, next50, next280, multi500, and paired90 primary MA_A decisions. Extra paired arms are not additional events. BTC rows are retained as explicitly skipped ledger rows but excluded from leader/lag trading, leaving the already-sampled SOL/ETH/DOGE moments only. Do not create new entry timestamps or substitute another traded asset. Native BTC minute prices at those same times provide context only.

Let t0 be the first minute after visible history. Observe the completed first15 minutes, from the t0 open through the t0+14-minute bar close. Define asset return A =100×(asset close[t0+14]/asset open[t0]−1), and BTC return B identically. Both are raw percentage changes; do not estimate a beta, volatility ratio, ranking, or optimized threshold. At t0+15 minutes all these inputs are known. Enter the existing traded asset at that minute's open, hold120 full minute bars, and exit at the t0+134-minute bar close (t0+135-minute clock). No target/stop and no horizon variants. Fees are zero. Short return is the negative underlying change on fixed initial notional.

The cached path row0 is only the previous visible close; row1 is the t0 OHLC bar. Therefore observation uses rows1..15, entry is row16 open, and exit is row135 close. Validate this convention against native15-minute closes and at least the relevant native minute prices. Missing any BTC observation minute makes the event explicitly unavailable to every member and comparator of this family. Do not fill or shift time.

## Four fixed policies

1. **Long after leader rises, laggard has not risen:** AI action SHORT; B>0; A<=0. Buy at t0+15, exit at t0+135.
2. **Long after lagging recovery:** AI action SHORT; 0<A<B. Same execution.
3. **Symmetric short diagnostic, laggard has not fallen:** AI action LONG; B<0; A>=0. Sell at t0+15, exit at t0+135.
4. **Symmetric short diagnostic, lagging decline:** AI action LONG; B<A<0. Same execution.

No other comparison thresholds. Equality at zero belongs to the non-moving laggard policy; equality of A and B is not selected by recovery/decline. The short policies are symmetric diagnostics, not an invitation to optimize short thresholds. All actual AI decisions precede the15-minute observation.

## Declared controls, same eligible events and execution clock

For each of the four policies, execute the exact same BTC/asset price gate without the AI action requirement. These four price-only controls can reveal a useful market pattern even when the model adds no value; report that conclusion separately.

For each side (long/short), also retain: (a) every opposite-AI call entered after15 minutes without a price gate; (b) the old15-minute asset confirmation gate plus opposite AI, where side×(asset close[t0+14]/previous visible close−1)>0; (c) that exact old confirmation gate without AI; (d) opposite AI and leader moving in the proposed trade direction (side×B>0), without requiring asset lag; and (e) unconditional delayed entry. The old confirmation benchmark uses its original previous-visible-close reference, but its hold is120 minutes to make the clock identical. It is a comparator for the old gate, not a re-score or alteration of the old240-minute strategy.

Save all18 declared strategy/comparator vectors (4 candidates +4 direct price controls +10 side controls), with skipped outcomes zero for opportunity accounting. For each candidate compare its return vector with each relevant comparator at the identical original asset/window. Report paired mean difference per eligible opportunity, as well as conditional mean per executed trade and trade frequency. The direct no-AI gate is a nested control, not an independent sample. Also standardize the direct price-control mean within cohort×asset×calendar-year to the AI-selected composition; recompute its group means within each bootstrap draw. This is an association adjustment, not causal identification.

## Uncertainty, stability and candidate gate

Keep synchronized assets and all same-time controls in the same group. Report unique entry-time blocks, active UTC weeks, and quarters as well as trade counts. Use20,000 quarter-cluster resamples with fixed seed2026093014; preserve shared quarter weights across every vector. Report95% intervals for per-trade return, per-opportunity return, paired opportunity differences, and the composition-standardized AI increment. Use the same denominators inside each resample. Provide four-candidate Bonferroni intervals as descriptive family diagnostics, not fresh-confirmation claims. No threshold or exit changes after reading results.

Break down original100, next50, combined old150, next280, multi500, and paired90, plus asset, calendar year, inherited chronological five-block fold, and common-calendar halves. Half membership comes from sorted unique eligible entry times, not splitting selected rows. Record long/short contribution; do not hide a short-dependent pooled mean. Show removal of the best1 and best3 individual trades and best1/best3 calendar blocks, plus leave-one-year-out means.

A possible research candidate requires at least50 unique selected entry-time blocks, positive gross mean in both common-calendar halves, at least three cohorts with>=10trades and positive means (old150 counts as one), at least three calendar years with>=10trades and positive means, positive mean after removing the three best calendar blocks, and a positive quarter95% lower bound. Report failures without changing the gate. A claim that the AI contributes also needs positive composition-standardized incremental mean and a quarter95% lower bound above zero. A price-only gate may instead be described as a market-pattern candidate if its own gross criteria pass; do not imply that it validates AI-wrongness. Passing this reused-outcome screen authorizes no model calls or live trades. At most two leading findings, including honest rejection if none qualify.

Pre-score audit clarification: because the four direct price-only gates may themselves be reported as market-pattern candidates, also provide simultaneous Bonferroni bootstrap intervals over the combined eight candidate/direct-price rules. The four-rule interval alone does not cover a price-only claim. A nominal95% screening pass remains exploratory if this wider interval includes zero.
