# Shared correction interface

File: `paired_vectors.npz`. All18 vectors must remain available to the joint family correction, including declared controls. There are no locally selected winners.

| Key | Shape | Meaning |
| --- | --- | --- |
| `policy` | (18,) | Unique strategy/comparator label |
| `kind` | (18,) | AI_candidate, direct_price_control, or comparator |
| `selected` | (18,1020) | Actual trade mask; every BTC-self column is false |
| `gross_pct` | (18,1020) | Finite hypothetical trade return in percent, signed by policy side |
| `opportunity_gross_pct` | (18,1020) | Exactly `where(selected,gross_pct,0)` |
| `direction` | (18,) | +1 long or -1 short |
| `eligible` | (1020,) | Common non-BTC complete-context universe:895 true |
| `window_id`, `asset`, `cohort`, `entry_time`, `quarter` | (1020,) | Window-axis identifiers and grouping |
| `matched_price_increment_pct` | (4,1020) | Descriptive composition-adjusted residuals; NaN outside each direct price gate |

Window order is exactly `new-angles-20260930/target_exhaustion/windows.csv`. Align by `window_id` if another family changes row order. All same-time assets must share bootstrap weights. Per-trade estimates use selected counts as denominator; this study's opportunity estimates use eligible895 counts as denominator and skipped returns zero. A1020-opportunity convention can be computed for joint reporting, but label the changed denominator.

The four matched increment arrays are not extra fixed-return trading strategies. Their composition baseline is estimated within cohort×asset×year among the corresponding no-AI price gate. Its group means and selected-side weights must be reestimated inside a resample; resampling cached residuals alone misses nuisance uncertainty. The main18gross vectors require no such reestimation.

`quarter_bootstrap.npz` supplies the local20,000 multinomial quarter weights and quarter labels, using seed2026093014. A joint correction may replace those draws with a common shared draw matrix across families. All quantities use zero costs and first-open at t0+15 to the close at t0+135.
