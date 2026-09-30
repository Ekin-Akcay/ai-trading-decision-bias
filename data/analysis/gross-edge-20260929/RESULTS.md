# Completed research: AI reversal with zero fees

**No tested inverse strategy passed fresh verification, even with costs set to zero.** The work used771 of800 newly authorized physical agent runs:770 valid isolated decisions and one timed-out attempt.29 remain unused. Every opinion, individual position, failed test and independent audit is saved; earlier findings are unchanged.

The useful distinction is between a predictable **decision tendency** and a profitable **wrong-call signal**. Terra's direction strongly tracks the price/MA configuration. In the500-window test it chose SHORT on all175 charts below both intraday averages. Removing explicit MAs did not remove its bearish tendency or create a profitable reversal rule in the controlled follow-up.

| Test | Executed trades | Mean gross/trade | Finding |
|---|---:|---:|---|
| Four-asset long reversal L048 |101|+0.3607%|Uncertain and concentrated in a few episodes |
| Four-asset ATR short reversal S508 |171|−0.0129%|Failed despite57.3%wins |
| Fresh SOL long replication MA_A |71|−0.1297%|Failed; both chronological halves negative |
| Identical-input repeat MA_B |67|−0.0608%|Diagnostic, not a replacement primary |
| Explicit MAs removed NO_MA |72|−0.1167%|No established economic improvement |

All returns are unlevered percentages with zero fees. These are separate frozen tests and diagnostic arms, not alternatives from which to select a winner after seeing results.

## What happened in the first fresh test

500snapshots covered125 fresh calendar times across SOL, BTC, ETH and DOGE. L048 buys against AI SHORT when the completed prior-day asset close≤50DMA and BTC close≤200DMA, then exits after four hours. S508 sells against AI LONG above both intraday MAs, with stop=target=2×ATR and a four-hour timeout. Both were fixed before opening outcomes.

L048's simultaneous block interval was **[−0.3809%,+1.1944%]**. After matching the price-only comparison by asset, era and intraday-MA regime, the AI added only **+0.0206percentage points**, with interval **[−0.0680,+0.1035]**. One episode supplied69.2% of summed profit; removing the best three calendar episodes made the mean **−0.127%**. Shorter horizons and volatility normalization did not resolve this concentration.

S508's average winner was+0.7443%, versus−1.0438% for its average loser. Its57.3%win rate was insufficient even before fees. Independent replay found no accounting or fill bug.

## Controlled MA removal and a further fresh replication

90 further SOL windows satisfied the unchanged daily gate. Each received full-MA primary MA_A, an identical-input repeat MA_B, and NO_MA. Only the explicit MA20/MA50 lines, labels and one text line were removed; candles, volume, scales and all other statistics remained fixed. The full-MA images matched the canonical renderer exactly. Execution order was randomized. There were90 market observations, not270 independent trades.

The prespecified SOL primary averaged **−0.1297%**, with99%window interval **[−0.8255%,+0.6008%]**. Removing its best three winners reduced the mean to−0.4061%. Both chronological halves and both delayed-entry variants were negative. No incremental AI contribution was verified.

- MA removal changed19/90 actions; repeating identical input changed10/90.
- The exact paired test gave **p=.0318**, missing the frozen.01 threshold: suggestive input sensitivity, not a passed mechanism claim.
- SHORT calls were **71/90 with MAs and72/90 without**. Nine SHORT→LONG changes were offset by ten LONG→SHORT changes.
- NO_MA improved returns by only **+0.0090percentage points per opportunity**, counting skips as zero;95%paired interval **[−0.1600,+0.1897]**. No economic improvement was established.

This does not show that MAs never matter or that every future inverse strategy must fail. It shows that the tested MA intervention and frozen reversal policies have not supplied the requested edge. A directional preference in bearish conditions alone is not proof of systematically wrong calls.

## Verification and saved records

The studies contain590 distinct asset windows at215 distinct calendar times. New future targets were excluded from earlier examined history/outcome intervals. Features may reuse known past observations. These are historical held-out targets, not live trading or guaranteed unseen model-training data. Whole-window/calendar-block and quarter inference preserves repeated-opinion and cross-asset dependence.

Independent workers reproduced native minute prices, gates, delays, conservative fills, paired stimuli, bootstrap arrays, exact paired tests and claim flags. Original AI bracket outcomes are separate from reversal positions. Paired ledgers include an arm identifier so repeated opinions are not mistaken for independent market samples.

- [Research dashboard](<./data/analysis/gross-edge-20260929/index.html>)
- [All500 snapshots and positions](<./data/sim/gross-edge-500-20260929T204545Z/index.html>)
- [All90 paired windows and270 opinions](<./data/sim/ma-ablation-sol90-20260929T210853Z/index.html>)
- [Completion and budget record](<./data/analysis/gross-edge-20260929/completion.json>)
- [Shorter-horizon diagnostic](<./data/analysis/gross-edge-20260929/risk/long_horizon_profile/FINDINGS.md>)
- [Risk-normalization diagnostic](<./data/analysis/gross-edge-20260929/signals/risk_normalization/FINDINGS.md>)

The profitable-strategy objective remains unmet.29 calls are retained. No failed candidate was promoted, leverage was not used to change the conclusion, and no actual orders were placed.
