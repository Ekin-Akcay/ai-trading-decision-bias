# Bounded retrospective search diagnostic

The two frozen primary rules have now been evaluated and failed confirmation. The root has authorized replaying the previously declared finite policy families on these same 280 windows as **exploratory research**. The procedure below accounts for searching that recorded family, but it does not turn these reused outcomes into a new untouched confirmation sample.

## Freeze the search universe first

Include all declared risk/exit policies crossed with every searched direction/regime group, all entry/confirmation filters, and all invalidation families. Keep losers, no-signal rules, and duplicated policy definitions in the inventory. Exact duplicate return vectors can be deduplicated computationally, with a mapping back to all definitions. Do not run the family correction only on profitable policies or on the top results of each family. Record the number of definitions, unique vectors, and executed-trade counts.

No new horizon, stop ratio, confidence threshold, model, macro cutoff, or winning time zone is introduced during this replay. Any genuinely new family later added must be included in a recomputed full search correction and remain exploratory.

## Joint quarter-cluster maximum-t calculation

Construct an `N × M` matrix `X`, one row per fresh window and one column per strategy. Each executed trade contributes its percentage return minus 0.20 percentage points; a skipped opportunity contributes exactly zero. Use opportunity returns for the joint statistical test so selection frequency remains in the estimand. Report executed-trade means and trigger counts alongside it. For a strategy with nonzero trigger rate, positive opportunity expectancy and positive trade expectancy have the same sign.

Let `G` be the number of calendar quarters, `n_g` their window counts, and:

```
mu_j = mean_i X_ij
s_gj = sum of X_ij for windows in quarter g
u_gj = s_gj - n_g * mu_j
se_j = sqrt( G/(G-1) * sum_g u_gj^2 ) / N
t_j  = mu_j / se_j
```

The score is one-sided positive net profitability relative to cash. For each of 20,000 replicates, draw `G` quarters with replacement using one shared draw for every policy. Let `w_bg` be the number of times quarter `g` is drawn. Then:

```
N_b = sum_g w_bg * n_g
centered_mean_bj = sum_g w_bg * u_gj / N_b
t_bj = centered_mean_bj / se_j
max_t_b = max_j t_bj
```

Use a new recorded seed, fixed before producing the expanded results. Each policy's single-step familywise adjusted diagnostic is:

```
p_adjusted_j = (1 + count_b(max_t_b >= t_j)) / 20001
```

The global family test uses the largest observed `t_j`. An approximate simultaneous lower bound for the opportunity mean is `mu_j - quantile(max_t_b, .95) * se_j`. Centering every column imposes the least-favorable zero-mean null; many weak policies can make this conservative. Call this a **centered quarter-cluster max-T diagnostic**, not an exact Hansen SPA implementation or a distribution-free proof.

Compute the bootstrap maxima in row chunks to avoid materializing a 20,000 × thousands-of-policies matrix. The much smaller quarter-by-policy centered-sum matrix is sufficient. Keep all columns in each replicate's maximum.

Strategies with zero triggers or numerically zero cluster standard error are not testable and must not be labeled verified. Report them separately. Retain low-trigger strategies in the search inventory; require adequate count, preferably at least 50 executed trades, before treating one as a usable candidate. Do not change that count after looking at winners.

Calendar-quarter resampling retains dependence among windows within a quarter and cross-policy correlation. It assumes quarters are approximately exchangeable. Report a prespecified sensitivity using consecutive multi-quarter blocks if needed to assess longer regime dependence; do not choose whichever block length yields a favorable p-value. No bootstrap fixes nonstationarity automatically.

## Separate profitability from AI contribution

A profitable member may simply exploit a price pattern or market drift. The cash-relative family test above does not establish that reversing AI adds information.

For each candidate, provide the same execution policy with a price-only eligibility rule and without AI selection, using identical costs, entry timing, and stop geometry whenever possible. An own-AI-stop control is not AI-free. A control that changes geometry cannot identify direction selection alone.

A separate familywise test can be applied to prespecified paired opportunity-return differences against an explicitly defined price-only benchmark, using the same cluster procedure. Report what that benchmark tests. Better per-opportunity results from skipping trades can reflect avoiding transaction costs rather than improved direction prediction.

The stronger selection diagnostic is the already used conditional AI-label/geometry permutation, extended jointly across the entire declared family. Preserve paired action and risk information, the nine era × MA-regime strata, and shared permutations. For every policy, compare its observed selected mean against its conditional null; take maxima across all policies after centering/scaling their null distributions. Fixed-geometric policies can reuse receiver-path returns; AI-geometric policies require donor-geometry replay. Do not claim an AI edge from the best unadjusted permutation p-value after searching hundreds of variants.

## What a positive diagnostic means

If a rule survives full-family correction, reasonable fees, latency sensitivity, and concentration checks, describe it as a retrospectively selected historical candidate that survived this diagnostic. Show both its discovery and reused-validation performance. Preserve the original failed primary tests in the report. Fresh confirmation still requires an untouched sample.

Only 20 of the total 300 permitted physical calls remain. Most rare strategies would yield very few trades from those calls, so their existence alone does not justify spending them. A new registered 20-call phase could assess feasibility or stability but is unlikely to verify modest profitability. Do not keep searching, relabeling validation, or adjusting the family until a green p-value appears.
