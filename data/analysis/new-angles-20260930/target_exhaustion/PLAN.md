# Confirmed failure after an AI target

Frozen before calculating this family's returns on 2026-09-30. This is discovery on previously studied outcomes, not an untouched holdout or preregistered independent confirmation. No additional model decisions may be requested.

Hypothesis: an AI's projected continuation level can mark exhaustion. A completed favorable move followed by rejection/reclaim might provide a better contrarian entry than reversing the opinion immediately. These hypothetical levels are not actual orders or evidence of liquidity hunting.

Use one Terra MA-present opinion per distinct asset window from the original100, next50, next280, four-asset500, and paired90 MA_A cohorts (1020 windows). MA_B/NO_MA do not add independent windows. Preserve cohort and calendar grouping. Existing cohorts have different sampling rules.

Execution: original entry is the last visible close. Original stop is the model stop and target exactly twice that distance. Within240 complete future minutes, require target before stop. A gap open determines the first known event; otherwise a minute touching both levels is SL-first and excluded. After the TP minute j, require a subsequent minute j+1 through j+15 inclusive to close back inside the target. For an original SHORT, close must be above target; buy the next minute open. For an original LONG, close must be below target; short the next minute open. Hold exactly60 complete minutes, then close. No further bracket. Costs zero, returns on unlevered notional. TP-minute close cannot confirm. No exit or threshold search.

Fixed comparison family (11 policies):

- Model levels: all signals, buy-only (AI SHORT), sell-only (AI LONG).
- Donor levels on the same AI direction: all/buy/sell. Donor stop/ATR is the immediately preceding window by time within the same cohort and asset; scale by current ATR. First observation has no donor and skips. Donors are AI-derived, not price-only.
- One-ATR stop/two-ATR target on the same AI direction: all/buy/sell. This isolates model geometry but still uses AI direction.
- Fully price-only brackets: hypothetical SHORT with one-ATR stop/two-ATR target then buy reclaim; hypothetical LONG with the same distances then short rejection.

Save every opportunity including skips, geometry, both event indices, entry/exit and returns. Compare both per-trade means and per-original-window opportunity returns (skips zero); equal opportunity arithmetic does not imply equal risk. Do not add long and short control means as one deployment portfolio. Report cohort means, five chronological folds, two chronological halves, calendar-quarter and original-entry-block bootstrap intervals, largest contributors and removal of best3 blocks. Preserve simultaneous confidence bounds for all11 policies, not only any favorable one. Minimum discovery screen:30 trades/20 original-entry blocks, positive two halves, positive at least4/5 folds, positive after removing best3 blocks, and positive simultaneous lower bound. Incremental AI information additionally needs positive same-opportunity control differences with simultaneous lower bound. Passing this screen still requires new-data verification before a profit claim.
