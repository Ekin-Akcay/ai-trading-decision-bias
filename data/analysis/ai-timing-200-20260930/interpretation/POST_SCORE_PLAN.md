# Identical-coverage direction comparator: retrospective diagnostic

This plan is written after the completed frozen confirmation results were inspected. It is an explicitly post-score diagnostic, not another preregistered confirmation claim. It changes none of the prior results or passing criteria and uses zero model calls, new windows, horizons, thresholds, or native-price reads.

Use every valid quiet-UP gate separately in the screen and confirmation stages. Both comparators enter at the already-fixed t0+30 native open and exit at t0+150 using the close of minute t0+149, with zero costs. Both take a position at every included gate; there are no confidence, asset, or additional market filters.

- **Always follow original AI direction:** existing short-side gross return multiplied by +1 for AI SHORT or −1 for AI LONG.
- **Always follow original MA20 direction:** existing short-side gross return multiplied by +1 when original t0 price is below MA20, or −1 when above/equal. This uses the original snapshot MA20 side, not any later moving average.
- **Paired incremental return:** AI-direction return minus MA20-direction return on the exact same gate.

Report each stage independently: counts, mean gross returns, the paired mean difference in percentage points, and ordinary 95% quarter bootstrap intervals. Reuse each stage's already-frozen 40,000 quarter weights and its complete released-stage quarter universe from `bootstrap_arrays.npz`, including quarters with no UP cases. Recompute weighted sums and denominators under each draw. Use empirical `inverted_cdf` quantiles. Report undefined draw fraction and retain undefined draws as negative infinity for the diagnostic lower bound; no significance-based candidate promotion will follow these intervals.

Also report chronological halves, split at the midpoint of all chronological UP cases. For each of the three reported vectors independently, show its mean after removing its one and three largest positive event contributions (case-ID tie-break). The trimmed populations can therefore differ between vectors; these are concentration diagnostics, not additional deployable strategies. One event per UTC day was frozen in the original sample.

Keep screen and confirmation separate. This diagnostic was requested after inspecting these outcomes, so its intervals are unadjusted descriptive uncertainty and do not constitute independent replication, rescue the failed confirmation, or establish that AI is necessary for a profitable strategy.
