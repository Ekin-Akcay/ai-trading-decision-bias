# Does hedging BTC exposure rescue the reversal strategy?

**No. Every nonzero hedge tested loses on the 280 fresh windows after charging both legs.** This is an exploratory mechanism study after primary validation outcomes were visible. No primary result changed, no additional model calls were made, and no untouched-validation claim is made.

The finite family contains four signals and four hedges: reverse either AI call immediately; reverse AI longs into shorts; reverse AI shorts into longs; and the exact confirmed-long L entry. Hedges are zero, 0.5, 1.0, and trailing OLS beta. Every trade holds 240 minutes after actual entry. The time-exit short is explicitly a different exploratory policy from the locked bracket short.

OLS beta uses 199 paired simple returns from 200 completed 15-minute closes ending at the original snapshot. It is clipped to [0, 3] and never updated using confirmation or future prices. Mean clipped beta in the fresh sample is 1.4635.

## Fresh results per SOL notional

Each active SOL leg and BTC leg pays 20 bp roundtrip, proportional to its notional.

| Signal | Executed trades | No hedge | 0.5 BTC hedge | 1.0 BTC hedge | OLS hedge |
|---|---:|---:|---:|---:|---:|
| Reverse either AI decision immediately | 280 | +0.0745% | −0.0623% | −0.1991% | −0.3829% |
| AI long → immediate SOL short | 91 | +0.0082% | −0.1056% | −0.2193% | −0.3611% |
| AI short → immediate SOL long | 189 | +0.1064% | −0.0415% | −0.1894% | −0.3934% |
| AI short → confirmed SOL long, fixed L | 85 | +0.0151% | −0.1517% | −0.3185% | −0.5433% |

All values are mean net percent per trade per initial SOL notional. Dividing each trade by total initial gross notional also leaves every nonzero fresh hedge variant negative. Both conventions and all controls are retained for the expanded multiplicity family; variable OLS beta changes mean weights, so the conventions are not treated as interchangeable.

The confirmed-long example makes the tradeoff concrete. Its unhedged gross average is +0.2151%; adding a 1.0 BTC hedge reduces gross to +0.0815%, while roundtrip costs rise from 0.20% to 0.40% per SOL notional. Net therefore becomes −0.3185%.

## Consistency and downside

No AI strategy has positive net averages in all four old/fresh chronological halves, on either notional convention. Some old-sample hedged long variants were positive, but the new sample did not reproduce them. The apparently profitable unhedged fresh variants also have negative later halves, and removing their three largest winners makes every unhedged fresh mean negative.

Hedging sometimes reduces loss severity. For fixed L, the worst net trade improves from −8.9259% without a hedge to −4.4677% with a 1.0 hedge, and the worst-five-percent average improves from −5.3244% to −3.2234%. That risk reduction does not rescue expected net returns. OLS is not a uniformly safer hedge: for immediate long reversals, its worst loss is worse than the unhedged loss.

Matching fresh price-only controls also lose. Always-long 240-minute net averages are −0.0609% unhedged and −0.3166% with a 1.0 BTC hedge. Positive-15-minute-confirmation longs without AI selection average −0.2153% and −0.4833% respectively. AI selection can improve a weak control without creating a verified profitable strategy.

## Coverage and verification

All 280 fresh windows pass native BTC/SOL minute alignment and finite-positive price checks. One old window, `72c5a0798c`, has a gap in the required SOL pre-entry history and is excluded consistently from all old hedge variants and controls. Thus the paired old comparison uses 149 windows, not 150; its zero-hedge averages can differ slightly from earlier full-sample summaries.

Independent verification passed 81,286 checks, including 858 minute paths, 2,574 comparisons with native 15-minute exit closes, 429 OLS slopes using an independent least-squares implementation, economics/selection reconstruction for every cell, and reconciliation of zero-hedge fixed L with the original fresh result. Maximum numeric error was below 6e−14.

## Retained data

- `hedge_family.npz`: 28 × 280 strategy/control arrays named `net_per_SOL_notional_pct`, `net_per_total_notional_pct`, `selected`, `policy`, and `window_id`.
- `hedge_family_all_notional_conventions.npz`: both conventions stacked into 56 × 280 `net_pct`/`selected` arrays, with policy names and matching window IDs.
- `old150_payoffs.npz` and `fresh280_payoffs.npz`: full economics, hedge weights and opportunity returns. The old file contains the 149 usable observations, explicitly recorded in its window axis.
- `all_trials.csv` and `old_fresh_comparison.csv`: all strategy and control summaries, both notional conventions.
- `windows.csv`, `missing.json`, `audit.json`, and `validation.json`: clock prices, beta estimates, missingness and verification.

The finite/positive data hardening did not change sample membership or conclusions. Earlier artifacts and the locked primary results remain preserved.
