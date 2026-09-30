# Risk-management discovery on existing Terra decisions

These findings are **discovery only**. All 150 historical windows were already visible, and 824 exit policies were searched. The two finalists below are fixed candidates to falsify on fresh data; neither is verified profitable.

## Why 57% wins was insufficient

The latest 42 reversed shorts had 24 gross winners averaging **+0.76398%** and 18 losers averaging **−1.49797%**. The break-even win probability for that payout distribution is 66.22% before costs and **75.07% at 20 bp roundtrip costs**. Actual wins were 57.14%. The latest eight reversed longs require 74.14% at those costs versus their observed 62.5%.

Changing a stop changes which trades win. We therefore replayed the complete minute-by-minute path. We did not clip the terminal loss while keeping the same winners.

## What was searched and checked

[PLAN.md](PLAN.md) froze 824 policies before the grid ran: eight time horizons, fixed/ATR/AI-stop distances, and six reward/risk ratios. The search produced 247,200 elementary trade results and 12,360 grouped summaries. All 150 windows have complete contiguous 72-hour minute data. Prices came from existing local files; no new AI calls were made.

Adverse opening gaps fill at the actual opening price. Favorable gaps are capped at target, and simultaneous stop/target touches assume stop first. Every trade pays 20 bp, with 30 bp sensitivity. Trade entry is the final visible candle close, followed by explicitly checked one/five-minute delayed-open sensitivities. The timeout remains the original snapshot clock. Independent tests compare native-engine outcomes and a separately implemented minute loop, including gaps, ambiguity, and delays.

## Two frozen candidate policies

Both rules: **when Terra says LONG, short; when Terra says SHORT, skip. No MA gate.** They each executed 72 of 150 windows (30 original and 42 from the latest sample).

| Policy | Stop | Target | Maximum time | Gross/trade | Net/trade | Net wins | Net profit factor |
|---|---|---|---|---:|---:|---:|---:|
| 764, first candidate | 1.5 × Terra's original stop distance | 2 × our stop | 240 minutes | +0.4445% | **+0.2445%** | 51.39% | 1.435 |
| 508, simpler risk sizing | 2 × pre-entry 15m ATR14 as percent | 1 × our stop | 240 minutes | +0.3537% | **+0.1537%** | 58.33% | 1.281 |

These are different exit policies on the same trades, not two independent replications.

| Sensitivity | Policy 764 net/trade | Policy 508 net/trade |
|---|---:|---:|
| Earlier chronological half | +0.4625% | +0.2951% |
| Later chronological half | +0.0265% | +0.0123% |
| Original batch | +0.4516% | +0.2829% |
| Latest batch | +0.0966% | +0.0615% |
| 30 bp costs, unchanged entry | +0.1445% | +0.0537% |
| One-minute delayed entry | +0.2501% | +0.1779% |
| Five-minute delayed entry | +0.1788% | +0.1156% |
| Remove largest three winning trades | +0.0624% | +0.0107% |

The positive average alone hides fragility. With one-minute delayed entry, later-half returns become **−0.0298% / −0.0315%**. With five minutes they become **−0.1057% / −0.0840%**. The top three winning trades account for 75.55% and 93.33% of summed net gains respectively. These are arithmetic sample contribution measures, not portfolio returns.

Five of six immediate parameter neighbors have a positive pooled net average for each policy. Their median averages are +0.1775% and +0.0383%. But **zero of six / one of six** neighbors remain positive in both chronological halves. Therefore, the broad stable neighborhood criterion is not satisfied. Only four of the eligible reversal rules at horizons <=24 hours passed all available un-delayed split-positivity checks; none becomes an independently validated strategy just by passing those screens.

## Does AI add anything beyond price conditions?

The all-window short controls average +0.0560% for policy 764 and +0.0093% for policy 508. Restricting a simple short control to price above both MAs gives **+0.1688% / +0.0856%**, explaining much of the candidate gain. The AI-selected above-both subset gives +0.1971% / +0.1078%, only about +0.0283 / +0.0222 percentage points more. In the latest batch, shorting all 50 eligible windows actually beats selecting the 42 AI-long windows for both policies.

Policy 764's control uses Terra's stop distance, so it is an AI-sizing control rather than a pure no-AI strategy. Policy 508 uses price-only ATR and is the clean no-AI control. Fresh validation should retain both all-window and MA-matched controls.

## Long trades and unrestricted reversal

No immediate-entry long-only rule with at least 20 observations, <=24-hour horizon, positive chronological halves and positive represented source batches qualified. The highest positive long-only cell had +0.0843% net across 78 trades but a negative later half and negative latest batch. Reversing every AI call also fails these stability checks. This search supports testing a restricted short hypothesis; it does not support “AI is wrong in general.”

## Files

- [candidates.json](candidates.json): exact two policies, statistics, neighbors, sensitivities and controls.
- [candidate_trades.csv](candidate_trades.csv): all candidate path outcomes with all three entry delays.
- [all_trials.csv](all_trials.csv): every group summary, including failed policies.
- [all_trade_results.npz](all_trade_results.npz): every elementary window/policy/direction return, hold time, ambiguity and gap flag. Axes: policies in policies.json, windows in windows.csv, directions long/short.
- [audit.json](audit.json): preserved input hashes and numerical verification.

No fee/latency model establishes executable fills. Funding, impact and model-call costs remain for the fresh validation layer. Old and latest source batches have different sampling conditions; pooled counts must not conceal that.
