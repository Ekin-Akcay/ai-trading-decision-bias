# Confirmed target exhaustion: rejected for further calls

This tests a new ordered event: the original AI bracket reaches its target before its stop; a later completed minute closes back inside that target; take the opposite direction at the next minute open and hold 60 minutes. It is distinct from previous immediate reversals and stopout fades. All outcomes were previously available, so this is discovery only.

The source set contains 1020 distinct asset windows grouped into 645 original entry-time clusters. One Terra MA-present decision per window is used. Cohorts have different selection rules; pooled means weight asset opportunities, not calendar baskets or a constructed portfolio. Costs are zero; returns use unlevered initial notional.

| Policy | Trades | Mean gross per trade | Without best 3 entry-time clusters | Positive chronological folds |
|---|---:|---:|---:|---:|
| ai_all | 241 | -0.047% | -0.134% | 4/5 |
| ai_long | 175 | -0.083% | -0.207% | 2/5 |
| ai_short | 66 | +0.050% | -0.046% | 4/5 |
| donor_all | 234 | -0.109% | -0.165% | 2/5 |
| donor_long | 161 | -0.112% | -0.186% | 4/5 |
| donor_short | 73 | -0.102% | -0.233% | 1/5 |
| atr_same_ai_all | 273 | -0.019% | -0.111% | 4/5 |
| atr_same_ai_long | 202 | -0.042% | -0.169% | 4/5 |
| atr_same_ai_short | 71 | +0.047% | -0.055% | 4/5 |
| price_short_all | 301 | -0.087% | -0.184% | 2/5 |
| price_long_all | 200 | -0.085% | -0.139% | 2/5 |

The main long policy loses 0.0834% on 175 positions. Its two chronological halves average −0.3414% and +0.2160%; after the best 3 contributing market events are removed, it loses 0.2068%. The short policy makes 0.0499% on 66 positions, but its first half and its result after removing the best 3 events are negative. Neither is a credible candidate.

No policy passes the pre-calculation discovery screen. All eight AI-minus-control opportunity-return intervals include zero. The exact AI target offers no demonstrated advantage over the same state machine using ATR levels. Donor widths are AI-derived; only the two fixed-direction ATR policies are fully price-only controls.

The 11-policy simultaneous block intervals, whole-quarter intervals, cohort/fold results, excursions, 1/5-minute execution-latency sensitivities and every skipped/traded event are saved. Latency sensitivities do not replace the original execution. The positive +0.0034% pooled 5-minute-latency mean is descriptive, not a newly selected rule.

Files: PLAN.md freezes the family; event_ledger.csv stores 5100 window/geometry replays including 241 primary AI trades; summary.json and comparisons.json preserve all definitions; breakdown.csv contains cohort/time detail; family_arrays.npz preserves common resamples. Earlier reports and model decisions are unchanged.
