# Independent audit of the paired 90-window SOL study

Run: `ma-ablation-sol90-20260929T210853Z`. The root explicitly released outcomes after all 270 decisions were accepted and audited. The independent scorer then read native source prices; it imports no root strategy return functions.

The audit passed: 90 complete minute paths, 90 native daily regime gates, 180 pre-entry MA values, 450 native 15-minute horizon checks, and 270 arm rows across 22 fields (5,940 ledger comparisons). All 90 MA_A/MA_B inputs and images are byte-identical. All 90 NO_MA text inputs remove exactly the declared indicators line, and paired chart dimensions agree. The independently computed action disagreements, exact mechanism p-value, and secondary per-opportunity contrasts agree with the root report. This validates computation and the audited stimulus invariants, not the economic hypothesis.

## Locked profit replication

Each arm selects a long position only when its model chooses SHORT. Entry is the first minute open after the visible history; exit is the close 240 minutes later. Fees are zero. These are per-trade arithmetic returns, not a compounded portfolio result.

| Arm | Selected trades | Mean gross return | Win rate |
| --- | ---: | ---: | ---: |
| MA_A, frozen primary | 71 | -0.129687% | 46.48% |
| MA_B, identical-input repeat | 67 | -0.060779% | 44.78% |
| NO_MA | 72 | -0.116699% | 47.22% |

The primary MA_A result fails the frozen profit criteria. Its 99% window interval is [-0.825481%, +0.600780%], and its 95% quarter interval is [-0.491313%, +0.216921%]. Both chronological halves, both fixed-exit entry delays, and the result excluding the best three trades are negative. Selecting the best-looking arm after these results would not repair this failed replication.

The all-window price-only control averages -0.174646%; the below-MA20 price-only control averages -0.213383%. The era/intraday-regime standardized baseline averages -0.093247%, leaving the primary AI increment at -0.036440 percentage points. Its uncertainty intervals include zero. Only 3 of 9 strata contain selected and unselected observations, so the AI increment has limited independent selection contrast. No arm verifies a profit or AI increment.

## Moving-average information mechanism

Removing MAs changes 19/90 decisions relative to MA_A, versus 10/90 changes between identical MA_A and MA_B inputs. The paired discordant counts are 14 treatment-only and 5 repeat-only, giving the registered exact one-sided p-value 0.031784. This is suggestive evidence of some decision sensitivity, but it fails the prespecified 0.01 threshold. It is neither proof of no MA influence nor a verified mechanism under this protocol.

Crucially, removal does not reduce the directional preference for SHORT: MA_A makes 71 short calls, MA_B 67, and NO_MA 72. Relative to MA_A, NO_MA changes 9 short calls to long and 10 long calls to short. The short-frequency reduction is therefore -1.11 percentage points, with a 99% interval spanning zero. The NO_MA return improvement is only +0.008950 percentage points per opportunity, and its 99% interval [-0.216084, +0.255618] includes zero. Ordinary repeat variation produces a larger observed improvement (+0.057062 points), also uncertain.

All 90 windows were deliberately sampled inside the bearish daily SOL/BTC gate. A high SHORT frequency within that conditioned population is not by itself an error or evidence of an unconditional model bias. The test does not identify MAs as the cause of the SHORT preference, and that preference does not create a verified four-hour reversal opportunity here.

No new rules, horizons, gates, or arm selection were introduced after seeing these outcomes. This study strengthens the conclusion that the tested L048 profit hypothesis has not survived independent replication. A further claim of profitability requires a new hypothesis and untouched verification rather than reclassifying the current negative result.
