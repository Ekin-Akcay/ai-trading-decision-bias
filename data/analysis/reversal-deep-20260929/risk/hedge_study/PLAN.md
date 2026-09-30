# New exploratory mechanism: hedge common BTC exposure

Written before computing any hedge-family returns. Both old150 and fresh280 SOL/Terra windows have been inspected in earlier research; this is **new exploratory work, never untouched validation**. Preserve both locked primary results. No new model calls or additional regime/feature filters.

## Fixed family: 16 AI strategy cells

Four signal groups, each tested with hedge weights 0, 0.5, 1.0, and trailing OLS beta:

1. Immediate reverse-all: opposite to either Terra decision, entered at the last visible SOL close.
2. Immediate short reversal: Terra LONG -> short SOL; skip Terra SHORT.
3. Immediate long reversal: Terra SHORT -> long SOL; skip Terra LONG.
4. Confirmed long reversal: exactly the fixed L rule. Terra SHORT, next complete15m SOL close strictly above the original visible close, buy SOL at original+15m one-minute open.

Every executed position holds240minutes after actual entry. Immediate entry is at the original visible close; exit is original+240m close. Confirmed entry is original+15m open; exit is original+255m close. The short time exit is a new diagnostic replacement for its bracket, not a change to the primary S result.

BTC position is opposite SOL with initial BTC notional equal to hedge_weight×SOL notional, entered/exited at matching BTC minute clocks and the same close/open convention. Hedge weights are nonnegative. Weight0 is the unhedged reference.

OLS beta uses200 completed trailing15m closes ending at the ORIGINAL snapshot cutoff, yielding199 paired simple returns. Regress SOL returns on BTC returns with an intercept; slope=covariance/variance, then clip to[0,3]. No confirmation-window prices enter beta estimation. Fixed/OLS hedges remain unchanged throughout each trade. If pre-entry history or either forward minute series is incomplete, preserve missingness and omit that window from all hedge variants and controls for the affected cohort (no gap filling or synthetic prices).

Gross percent per SOL notional = SOL_position_sign×(SOL_return_pct - beta×BTC_return_pct).
Net percent per SOL notional = gross -0.20×(1+abs(beta)).
Gross/net per total initial gross notional divide the respective SOL-notional values by(1+abs(beta)). Every active leg pays20bp roundtrip. No leverage, funding, borrow, rebalancing or portfolio compounding assumptions.

## Controls and reporting

For each hedge weight: always-long and always-short immediate time positions; positive15m-confirmed long without AI selection. Same clocks, hedge, costs and beta estimator as the matching AI rule.

Old150 and fresh280 are reported separately, including counts, chronological halves/thirds, net/gross means, win rates, cost break-even, loss/tail concentration, largest-three-winner exclusion and positive-half consistency. Primary comparisons are mean net per executed trade on BOTH notional conventions; opportunity vectors contain0for skips. Save all16cells' per-window payoff/mask vectors and all12controls for root's multiplicity analysis. Do not single out an optimized hedge as verified or omit failed variants.
