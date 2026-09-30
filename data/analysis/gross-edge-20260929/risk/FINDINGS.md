# Gross-return risk study: candidate for new validation

**The proposed candidate is S508, selected for a new untouched test—not a verified edge.** Both existing samples are discovery in this fee-free phase. The previous cost-inclusive experiments and failed primary tests remain unchanged.

If original price is at or above both MA20 and MA50 and Terra chooses LONG, short. Set the stop and target each to exactly **2 × pre-entry ATR14 percent of actual entry price**. Close after 240 minutes from the original snapshot if neither level has triggered. Skip all other windows. The model's proposed stop is unused. Adverse gaps fill at the actual opening price; favorable target gaps are capped; simultaneous touches count as stop.

Root selected the volatility-normalized rule for cross-asset validation. A fixed-percentage discovery rule had stronger chronological consistency, but is retained only as a secondary diagnostic rather than substituted after future results.

## Existing gross results

| Metric | Old 150 windows | Newer 280 windows |
|---|---:|---:|
| Executed S508 trades | 67 | 82 |
| Frequency across all sampled windows | 44.67% | 29.29% |
| Frequency within above-both MA windows | 83.75% | 76.64% |
| Mean gross per trade | **+0.30779%** | **+0.28087%** |
| Gross win rate | 64.18% | 56.10% |
| Gross profit factor | 1.619 | 1.560 |
| Earlier/later chronological halves | +0.45376% / +0.16612% | +0.36871% / +0.19302% |
| Mean after removing three largest winners | +0.15143% | +0.13850% |
| Worst individual gross return | −3.57737% | −3.55897% |
| Largest three winners' share of total gross gains | 53.00% | 52.49% |

The old sample contains 100 general windows and 50 windows deliberately sampled above both MAs, so its frequency is not an unbiased estimate of general market opportunity frequency. Within those source batches, selected gross means are +0.38555% (25 trades) and +0.26151% (42 trades).

The old chronological thirds are **+0.41388%, +0.57839%, −0.07371%**. Newer thirds are +0.48585%, +0.06145%, +0.28770%. The negative old third remains a limitation; positive halves do not erase it.

## Does the AI improve a matching price-only strategy?

Shorting every above-both MA window with exactly the same ATR stop/target and timeout averages +0.28558% old and +0.07394% newer. AI selection therefore adds only **+0.02221 percentage points old**, versus **+0.20692 points newer**, per executed trade.

This is a clean price-only comparison because both directions and risk distances are otherwise fixed from pre-entry market data. The larger newer difference is a discovery observation, not independent evidence after inspecting the whole grid. Opportunity-frequency effects, temporal dependence and selection uncertainty belong in the new validation.

Five of six immediate parameter neighbors have positive old and newer gross averages. The exception, a 3×ATR stop/target, loses −0.00879% in the newer sample. Neighbor checks support a nearby positive region in pooled averages, not universal stability.

## Entry-delay audit

The entry shifts to the one-minute open at the stated delay; stop/target distances re-center on that fill, and timeout stays at original +240 minutes.

| Entry delay | Old mean gross | Newer mean gross | Old AI increment over matching control | Newer AI increment |
|---|---:|---:|---:|---:|
| Original close | +0.30779% | +0.28087% | +0.02221 pp | +0.20692 pp |
| 1 minute | +0.33160% | +0.27047% | +0.02239 pp | +0.17984 pp |
| 5 minutes | +0.26192% | +0.11365% | +0.00746 pp | +0.15328 pp |

All delayed old/new half means stay positive. However, old final thirds remain negative, the newer one-minute middle third is approximately flat at −0.00141%, and the newer five-minute mean falls to just +0.00620% after removing three best trades. Execution timing materially reduces the margin.

Independent replay passed 1,290 native-minute scalar comparisons covering all 430 existing windows and all three timing conventions, with 10,320 field checks and zero numerical discrepancy. These are calculation checks, not profitability verification.

## Full family and hedge results

All 721 common risk policies were recomputed directly from saved gross returns, including every original gate and direction/control. Among 5,047 cells meeting old >=20 and newer >=40 trades, 412 have positive all four half means; 32 have positive all six third means; eight additionally remain positive after dropping the three largest winners in each sample. Returns within 1e−10 percentage points of zero are treated as zero for these screens. No cell becomes a validated strategy because it survives a discovery screen.

The simpler fixed stop 1%, target 1.5%, timeout 105-minute reversal has +0.15468% old and +0.13330% newer gross, with all thirds positive. But matching broad price-only shorts already earn +0.13823% and +0.07125%; the newer above-both price-only control earns +0.14870%. This is why AI value must be tested separately from profitable gross averages. It remains a secondary diagnostic only.

BTC hedges were also recomputed without costs. The OLS-hedged immediate short reversal has +0.16778% old and +0.13203% newer per SOL notional, but a negative old last third and newer middle third. Removing its three largest newer winners makes the mean −0.01895%; normalizing by total gross notional reduces average returns to +0.03867% and +0.03251% and leaves additional unstable periods. It does not justify adding a hedge to S508. All hedge variants and both notional conventions are retained.

## Files

- `CANDIDATE508.json`: exact rule, both samples, controls, entry delays and neighbors.
- `candidate508_summary.csv` / `candidate508_window_replays.csv`: every candidate and control result.
- `candidate508_audit.json`: independent clock/path verification.
- `risk_gross_all_trials.csv`, `risk_gross_old_new.csv`, `risk_gross_ranked.csv`: complete risk-family exploration.
- `hedge_gross_all_trials.csv`: complete fee-free hedge-family results.
- `analysis_summary.json`: family sizes and stability screen counts.

This phase assumes zero fees as requested. It does not establish fills without slippage, account returns, or a profitable after-cost strategy. No new model calls were made by this worker.
