# Identical-coverage AI versus MA20 direction

This diagnostic was specified after viewing the completed confirmation results. It is retrospective, has no new model calls or outcomes, and does not change the frozen failed confirmation verdict. Both policies trade every quiet-UP gate with the same 30-minute delayed entry and 120-minute hold. Returns are gross and unleveraged, with zero costs.

The AI policy follows the original AI direction, including long calls that the frozen short-only rule skipped. The MA20 policy shorts when the original snapshot price is below MA20 and buys when above/equal. Both use the original snapshot, not later indicators.

| Stage | Gates | Always follow AI | Always follow MA20 | Paired AI − MA20 |
|---|---:|---:|---:|---:|
| screen | 30 | +0.644% | -0.197% | +0.841 pp |
| confirmation | 120 | +0.109% | +0.157% | -0.048 pp |

Intervals below reuse the original 40,000 complete-quarter resamples and include quarters without UP trades. They are ordinary, unadjusted descriptive intervals; this post-score comparison is not an additional successful validation. Screen and confirmation are never pooled.

## Screen

AI directions: 22 short, 8 long. MA20 directions: 18 short, 12 long. They agree on 22/30 gates.

| Vector | Mean | Ordinary quarter 95% interval | First / second half | Remove best one | Remove best three |
|---|---:|---:|---:|---:|---:|
| follow_AI_pct | +0.644% | [+0.257, +1.169]% | +0.916 / +0.372% | +0.472% | +0.222% |
| follow_MA20_pct | -0.197% | [-0.828, +0.306]% | -0.584 / +0.190% | -0.310% | -0.439% |
| AI_minus_MA20_pp | +0.841 pp | [+0.089, +1.926] pp | +1.500 / +0.182 pp | +0.481 pp | +0.102 pp |

Concentration diagnostics remove the largest positive contributions separately for each vector; the removed case sets can differ. Full masks, removed case IDs and undefined bootstrap fractions are retained in `identical_coverage.json`.

## Confirmation

AI directions: 91 short, 29 long. MA20 directions: 77 short, 43 long. They agree on 96/120 gates.

| Vector | Mean | Ordinary quarter 95% interval | First / second half | Remove best one | Remove best three |
|---|---:|---:|---:|---:|---:|
| follow_AI_pct | +0.109% | [-0.137, +0.381]% | +0.273 / -0.055% | +0.065% | -0.012% |
| follow_MA20_pct | +0.157% | [-0.108, +0.474]% | +0.438 / -0.124% | +0.113% | +0.037% |
| AI_minus_MA20_pp | -0.048 pp | [-0.170, +0.060] pp | -0.165 / +0.070 pp | -0.077 pp | -0.116 pp |

Concentration diagnostics remove the largest positive contributions separately for each vector; the removed case sets can differ. Full masks, removed case IDs and undefined bootstrap fractions are retained in `identical_coverage.json`.

## Interpretation

In confirmation, always following the AI returned +0.109% per gate, while always following MA20 returned +0.157%. The paired AI increment was -0.048 percentage points, with ordinary 95% interval [-0.170, +0.060].
The sign and uncertainty of this paired difference describe whether AI improved on this specific simple direction comparator in the observed sample. A positive mean for either post-score policy is not independently verified profitability. This comparison does not establish AI dependence, causal use of moving averages, or value beyond all price features.
