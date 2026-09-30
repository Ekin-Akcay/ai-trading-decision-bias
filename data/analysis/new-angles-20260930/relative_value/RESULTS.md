# Relative-value result: no reversed-AI candidate

Twelve fixed policies tested whether AI ranks four assets' relative performance backwards at125 simultaneous timestamps. Each active basket is dollar-neutral, with0.5 long/0.5 short gross notional, first-minute-open entry and a fixed240-minute close. All data were already examined: this is discovery only. **Zero model calls were used.**

| Reversed AI ranking | Active timestamps | Mean per active basket | Mean per opportunity | Passes fixed stability screen? |
|---|---:|---:|---:|---|
| Direction disagreement | 48 | −0.1571% | −0.0603% | No |
| Signed confidence | 123 | −0.1330% | −0.1309% | No |
| Confidence ÷ stop/ATR | 125 | −0.0384% | −0.0384% | No |

All three fail the predeclared chronological/concentration screen. Mean within-timestamp rank correlations are positive, not inverted: +0.116,+0.100,+0.059 respectively. No primary AI-reversal candidate is recommended.

The exact **confidence-following comparator** averages+0.1330% per active basket and+0.0661% after removing its best3blocks. It is an **opposite hypothesis**, not a promoted winner. Its95% whole-block interval[−0.0716%,+0.3013%] and whole-quarter interval[−0.0259%,+0.3034%] cross zero. Its skip-matched advantage over price-momentum reversal is+0.0589percentage points, also uncertain. ETH contributes77% of its mean, three quarters supply76.7% of summed returns, and its worst basket is−8.3586%. Dollar neutrality does not imply beta neutrality.

All12 policies, all five25-block chronological folds, expanding-prefix transfer summaries, price-only controls and matched-skip comparisons are retained. No policy was retuned between folds. Every policy's block/quarter95% interval includes zero. Independent weight/payoff/fold checks and source hashes passed; the separate auditor reproduced the study.

`CANDIDATE_GATE.json` records the final gate. `FINDINGS.md` gives full interpretation. `relative_value_family.npz` contains the12×125 return matrix, masks, asset weights, scores and identifiers. No additional calls are recommended for this reversal hypothesis on the basis of these results.
