"""Publish the combined completed studies without changing their frozen results."""
from pathlib import Path
import json,re
HERE=Path(__file__).resolve().parent
r1=json.loads((HERE/'run.json').read_text())['run_id']
r2=json.loads((HERE/'ma_ablation/run.json').read_text())['run_id']
root=HERE.parents[2]
c=json.loads((HERE/'completion.json').read_text())
assert c['physical_attempts']==771 and c['valid_decisions']==770 and c['independent_audits_passed']
md=f'''# Completed research: AI reversal with zero fees

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

- [Research dashboard]({HERE}/index.html)
- [All500 snapshots and positions]({root}/data/sim/{r1}/index.html)
- [All90 paired windows and270 opinions]({root}/data/sim/{r2}/index.html)
- [Completion and budget record]({HERE}/completion.json)
- [Shorter-horizon diagnostic]({HERE}/risk/long_horizon_profile/FINDINGS.md)
- [Risk-normalization diagnostic]({HERE}/signals/risk_normalization/FINDINGS.md)

The profitable-strategy objective remains unmet.29 calls are retained. No failed candidate was promoted, leverage was not used to change the conclusion, and no actual orders were placed.
'''
(HERE/'RESULTS.md').write_text(re.sub(r'\]\((/[^)\n]+)\)',r'](<\1>)',md))
(HERE/'STATUS.md').write_text('''# Complete — 771 of800 new physical calls used

Both frozen studies are fully collected, scored, published and independently audited.770 valid decisions; one failed timeout replaced;29 calls unused.590 distinct asset windows at215 market times. Earlier sources, ledgers and reports preserved. No actual orders placed.

The500-window test failed both profit and incremental-AI verification. The90-window/270-call paired follow-up failed the fixed SOL profit replication and its frozen MA-mechanism criterion. Neither study was enlarged after outcomes.

Read RESULTS.md and index.html for combined findings, or completion.json for the durable completion/budget record. All current work is saved. The profitable-strategy objective remains unmet.
''')
page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI reversal research — completed</title>
<style>body{{margin:0;background:#f5f5f0;color:#193442;font:16px/1.55 system-ui}}main{{max-width:1160px;margin:auto;padding:40px 24px}}.tag{{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#5c747e}}h1{{font-size:40px;line-height:1.15}}h2{{font-size:23px}}.verdict{{background:#e3ebec;border-left:4px solid #315e71;padding:20px}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:28px 0}}.metric{{padding:20px;background:white;border:1px solid #d1dddf}}.metric strong{{display:block;font-size:30px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}article{{background:white;border:1px solid #d1dddf;padding:24px}}article h2{{margin-top:0}}.link{{display:inline-block;padding:10px 14px;background:#255d73;color:white;text-decoration:none;margin-top:8px}}a{{color:#176b84}}table{{width:100%;border-collapse:collapse;background:white;font-size:14px}}th,td{{padding:12px;border-bottom:1px solid #d9e2e3;text-align:right}}th:first-child,td:first-child{{text-align:left}}.wrap{{overflow:auto}}.note{{color:#536e79}}img{{max-width:100%;margin:16px 0;border:1px solid #d1dddf}}@media(max-width:720px){{h1{{font-size:30px}}.grid{{grid-template-columns:1fr}}.metrics{{grid-template-columns:1fr 1fr}}main{{padding:24px 14px}}}}</style>
<main><div class="tag">NAI Trading · completed research · zero-cost gross returns</div><h1>A directional tendency is visible.<br>A profitable inverse edge is not verified.</h1><p class="verdict">Two frozen fresh-target tests are complete. Neither tested reversal strategy passed verification. Removing explicit MAs did not remove the model’s bearish tendency or establish a return improvement.</p>
<div class="metrics"><div class="metric"><strong>771 /800</strong>physical calls used</div><div class="metric"><strong>770</strong>valid decisions</div><div class="metric"><strong>215</strong>market times</div><div class="metric"><strong>29</strong>calls unused</div></div>
<div class="grid"><article><h2>1 · Four-asset reversal test</h2><p>500snapshots at125 fresh calendar times. Long and short rules fixed before outcomes; price controls, delayed entries and block/quarter uncertainty included.</p><p><b>Long:</b>+0.361%gross/trade, but concentrated and uncertain.<br><b>Short:</b>−0.013%, despite57.3%wins.</p><a class="link" href="../../sim/{r1}/index.html">Open all500 snapshots and trades</a></article><article><h2>2 · Paired MA intervention</h2><p>90 further fresh SOL windows. Three isolated opinions each: original MAs, identical repeat, and explicit MAs removed. Other inputs held fixed.</p><p><b>Original long rule:</b>−0.130%gross/trade.<br><b>MAs removed:</b>−0.117%. SHORT calls71→72.</p><a class="link" href="../../sim/{r2}/index.html">Open90 paired windows and270 opinions</a></article></div>
<h2>The findings that matter</h2><p>Terra chose SHORT on all175 charts below both intraday averages in the500-window study. That decision pattern did not become a reliable inverse return. The initially positive long result drew69.2% of summed gain from one calendar episode and turned negative after removing its top three episodes.</p><p>In the controlled follow-up, MA removal changed19/90 actions versus10/90 from identical-input repetition. The exact paired p-value was.0318, missing the frozen.01 threshold. Changes went both ways: nine SHORT→LONG and ten LONG→SHORT. The bearish tendency persisted.</p>
<img src="../../sim/{r2}/overview.png" alt="Paired study: negative mean returns, persistent short calls and action changes">
<div class="wrap"><table><thead><tr><th>Policy or arm</th><th>Trades</th><th>Gross/trade</th><th>Status</th></tr></thead><tbody><tr><td>Four-asset long reversal</td><td>101</td><td>+0.3607%</td><td>Not verified</td></tr><tr><td>Four-asset ATR short</td><td>171</td><td>−0.0129%</td><td>Failed</td></tr><tr><td>Fresh SOL primary MA_A</td><td>71</td><td>−0.1297%</td><td>Failed</td></tr><tr><td>Identical repeat MA_B</td><td>67</td><td>−0.0608%</td><td>Diagnostic</td></tr><tr><td>Explicit MAs removed</td><td>72</td><td>−0.1167%</td><td>No established improvement</td></tr></tbody></table></div>
<p class="note">Unlevered returns, costs set to zero. Simultaneous assets and repeated opinions are not independent market observations. Earlier studies and failed candidates are preserved. These historical results are not a live profitability claim; no actual orders were placed.</p>
<h2>Reproducible records</h2><p><a href="RESULTS.md">Full findings</a> · <a href="completion.json">Completion and preservation audit</a> · <a href="snapshot_budget.json">Every physical call reservation</a></p><p><a href="VALIDATION_PROTOCOL.md">Four-asset locked protocol</a> · <a href="ma_ablation/PROTOCOL.md">Paired-study locked protocol</a> · <a href="design/final_statistics_audit.json">Four-asset independent audit</a> · <a href="ma_ablation/design/final_statistics_audit.json">Paired independent audit</a></p><p><a href="risk/long_horizon_profile/FINDINGS.md">Shorter-horizon diagnostic</a> · <a href="signals/risk_normalization/FINDINGS.md">Risk-normalization diagnostic</a></p></main></html>'''
(HERE/'index.html').write_text(page)
print(json.dumps({'dashboard':str(HERE/'index.html'),'findings':str(HERE/'RESULTS.md'),'complete':True}))
