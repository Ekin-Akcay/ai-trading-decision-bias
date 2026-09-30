# BTC leader / asset-lag reaction: no qualifying pattern

The two long hypotheses and their two symmetric short diagnostics all lost on average. Their four direct price-only controls also lost. None met the fixed research screen, and no additional model calls are justified by this family. All outcomes were already exposed in earlier work; these are discovery simulations, not fresh verification.

The experiment uses only the 1,020 existing primary Terra decision events. It explicitly skips the 125 BTC-self rows, leaving **895 SOL/ETH/DOGE opportunities at 645 existing entry times**. Every eligible event has a complete BTC observation window; none was removed for missing BTC context. There are no new sampled trade moments or substitute traded assets.

At each original decision time t0, observe the first15 minutes of BTC and the original asset. Enter that same asset at the t0+15-minute open and exit at the t0+135-minute clock, a120-minute hold. All comparisons use these identical entry/exit prices. Fees are zero. Returns are fixed-notional arithmetic returns per trade, not a compounded portfolio claim.

## The four fixed hypotheses

Here A is the asset's first15-minute return and B is BTC's contemporaneous first15-minute return, both measured from first open to completed15th-minute close. Comparing raw percentages does not estimate beta-adjusted relative strength or establish information transmission.

| Rule | Trades | Unique entry blocks | Gross mean/trade | Quarter95% interval | Same price gate without AI |
| --- | ---: | ---: | ---: | --- | ---: |
| AI SHORT, B>0 and A<=0 → long | 63 | 61 | -0.1173% | [-0.5376%, +0.2522%] | 97 trades, -0.0842% |
| AI SHORT, 0<A<B → long | 40 | 34 | -0.1494% | [-1.2508%, +0.6422%] | 72 trades, -0.1173% |
| AI LONG, B<0 and A>=0 → short | 37 | 32 | -0.1304% | [-0.5588%, +0.3335%] | 90 trades, -0.0744% |
| AI LONG, B<A<0 → short | 39 | 36 | -0.0570% | [-0.4474%, +0.2980%] | 109 trades, -0.1408% |

All four direct price controls' quarter intervals span zero. All four candidate and four direct-price rules fail the screen. Four-rule and combined eight-rule Bonferroni bootstrap intervals are retained, so a price-only control cannot be presented as an uncorrected selected winner.

## What the long results imply

The non-rising laggard long averages -0.3004% in old150, +0.0124% in next280, -0.1867% in multi500, and -0.2201% in paired90. Its common-calendar halves are -0.3496% and +0.1077%; removing the three best calendar blocks leaves -0.2270%. The second long averages +0.57898% in only3 old150 trades, +0.1206% in next280, -0.4260% in multi500, and -0.2944% in only3 paired90 trades. Its halves are -0.6530% and +0.2626%; removing the three best blocks leaves -0.5428%. Neither has consistent cohort or chronological support.

The exact same-clock delayed-long comparator on every AI SHORT has582 trades and +0.0335% gross, with interval [-0.1202%, +0.1848%]. The legacy asset-only15-minute confirmation gate, with its original previous-visible-close reference but the same120-minute hold, has265 trades and -0.1020%. Requiring only BTC to rise after an AI SHORT has271 trades and -0.1099%. Adding BTC-relative lag did not reveal a robust improvement over those existing confirmations.

Skips are zero in the paired opportunity comparisons. Across the same895 eligible opportunities, the first long contributes -0.008258% per opportunity and the second -0.006678%, versus +0.021758% for the AI-SHORT-only delayed-long comparator. Their paired differences versus that comparator are -0.030016 and -0.028435 percentage points per opportunity; both intervals include zero. Comparisons with the negative legacy gate may look positive simply because the new rules skip more losing positions. They do not make either new rule profitable.

After standardizing each direct no-AI price gate within cohort×asset×year to the AI-selected composition, the two long AI increments are -0.0457 points (95% interval[-0.1339,+0.0976]) and -0.0022 points ([-0.3446,+0.3163]). The first has37 of63 selected observations in strata with an actual selected/nonselected contrast; the second29 of40. This gives no evidence that the AI filter contributes useful information. These standardized benchmarks are association controls, not causal estimates.

The short diagnostics also fail. Their negative averages are not silently reversed into new successful policies; such a sign change would be an additional hypothesis requiring separate registration.

## Reproducibility and scope

`all_trades_and_skips.csv.gz` retains all18,360 policy/window rows, including BTC-self exclusions, price/AI-gate skips, original AI actions, observed A/B returns, exact execution times/prices, and both hypothetical and skips-zero returns. `comparisons.json` retains24 paired comparisons. `breakdown.csv` includes individual cohorts, old150 aggregate, assets, years, chronological folds, and quarters.

`paired_vectors.npz` contains all18 candidates and controls aligned to the original1,020 window IDs. `gross_pct` and `selected` are18×1,020; `opportunity_gross_pct` is exactly `where(selected,gross_pct,0)`. Every BTC-self selection is false. `eligible` identifies the895-window common universe; using all1,020 rows as an opportunity denominator would be a different reported frequency/return convention. Conditional per-trade means are unchanged. The extra four matched-increment arrays require group means to be recomputed under resampling and must not be mistaken for fixed extra trading rules.

The implementation reconciles4,080 cached observation/entry/exit prices against native15-minute prices and validates every BTC observation minute. It uses20,000 shared quarter resamples, recomputes matched baseline means in each draw, and keeps synchronized assets together in chronological halves. All source hashes remain unchanged. Additional external verification, when completed, is recorded by the shared audit worker rather than changing the policy definitions.

**Decision:** no long, short, or direct price-only member qualifies for promotion. The 29 model credits remain unused by this work. The useful exclusion is narrow: first15-minute BTC leadership plus raw-percentage asset lag did not create a reliable two-hour catch-up trade at these existing AI decision moments.
