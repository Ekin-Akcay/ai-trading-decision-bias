from pathlib import Path
from datetime import datetime,timezone
import json,html,hashlib,re,shutil
import pandas as pd
H=Path(__file__).resolve().parent;ROOT=H.parents[2];R=Path(json.loads((H/'run.json').read_text())['run_dir']);S=json.loads((R/'summary.json').read_text());F=json.loads((H/'search_correction/summary.json').read_text());B=json.loads((H/'snapshot_budget.json').read_text());E=html.escape
# Keep primary-only findings separate from the complete investigation.
if (H/'RESULTS.md').exists() and not (H/'PRIMARY_RESULTS.md').exists():shutil.copy2(H/'RESULTS.md',H/'PRIMARY_RESULTS.md')
rp=R/'report.py';rp.write_text(rp.read_text().replace("(STUDY/'RESULTS.md')","(STUDY/'PRIMARY_RESULTS.md')"))
report=f'''# Positive backtests found; no reliably profitable AI-reversal strategy verified

The investigation collected **280 additional isolated Terra snapshots** and tested the two chosen rules on all280 before any outcome-driven revision. Both had small positive net averages, but neither passed the locked verification criteria. Continued exploratory work retained **{F['definitions']:,} strategy/control definitions** ({F['unique_return_vectors']:,} unique return vectors). None passed the complete-family, calendar-quarter search correction. The user-authorized limit is300physical calls;280were used, with no retries. No actual financial trades were placed.

## What the win rate means

The earlier short strategy won57.1% of trades, averaging+0.764% on winners and−1.498% on losers. Its payoff distribution required75.1% wins to break even after20bps. A stop changes which trades win; it cannot merely clip final losses while preserving all winners.

The new capped-short rule improved the payout distribution, but its48.4% win rate was only slightly above its48.1% estimated break-even rate. The confirmed-long rule won56.5% versus a56.0% break-even rate. This is why both newer backtests were barely positive after costs despite better trade construction.

![Win rate, payoff and cost relationship](payoff_geometry.png)

## Frozen test on280new windows

| Rule | Executions | Gross-positive | Mean gross/trade | Mean net at20bps | Simultaneous net interval |
|---|---:|---:|---:|---:|---|
| L: AI SHORT → positive15m confirmation → LONG240m |85|48/85(56.5%)|+0.2151%|**+0.0151%**|−0.5485% to+0.5718%|
| S: AI LONG → SHORT,1.5×AI stop,2×risk target,240m cap |91|44/91(48.4%)|+0.2082%|**+0.0082%**|−0.4018% to+0.4363%|

L net at30bps is−0.0849%; S is−0.0918%. Five-minute entry delay leaves L+0.0478% net but turns S to−0.1287%. Removing the largest winner turns either rule's net mean negative. No compounded or leveraged portfolio return is claimed.

AI contribution was tested separately by permuting decisions within pre-entry MA regimes and broad calendar eras. S moved action and stop/ATR ratio jointly while retaining the receiving window's volatility. Adjusted p-values: **L0.2911; S0.0627**. S's rawp0.0313 is an interesting exploratory lead, but it did not pass the two-test correction. Positive historical averages are not the same as evidence of positive expected profits.

## How far the search went

- Initial discovery:824risk/exit geometries,116entry/filter candidates,108invalidation policies, all retained on the existing150Terra windows.
- Expanded replay:721within24h risk geometries across15direction/regime/benchmark configurations, plus the declared signal and invalidation families and controls.
- BTC hedging: fixed0.5/1.0 and trailing-beta hedges, both notional conventions. Every nonzero hedge lost in the fresh sample. L's net moved from+0.0151% unhedged to−0.1517% with half-notionalBTC and−0.5433% with the estimated beta hedge.
- Stop-out fades: wait for the original AI bracket to stop first, then enter its original direction at the following minute open. All16policies lost in the old sample. Two had positive newer means, but were unstable; the best+0.4839% newer result became negative after removing three winners and had−0.3374% in the old sample.

The complete retrospective family includes11295definitions, not11295independent experiments. Shared outcomes and calendar dependence are preserved in20,000joint quarter resamples. Largest observedt=1.8765;95%family criticalt=3.8466; global adjustedp=0.97745. **Zero policies pass.** The original failed primary tests stay unchanged; expanded results are not relabeled as untouched validation.

## Strongest remaining long lead — unverified

When Terra predicts SHORT and the previous completed daily SOL close is below its50-day average and BTC below its200-day average, immediately buy and hold240minutes. This post-selection lead had65fresh trades averaging **+0.5351% gross /+0.3351% net**, versus only+0.0116% net on22old trades. Its newest chronological third averaged−0.0419%; its unadjusted95% interval already includes losses. The full-search adjustedp is0.97745. It is a research hypothesis, not a verified strategy.

## What has been verified

All280decisions used fresh sessions, the exact anonymized inputs, the chosen model and no tools. Every input/source hash was checked. Independent implementations replayed primary entries/exits,78,400donor brackets,40,000conditional permutation results, and both bootstrap families. Additional independent checks covered the full search matrix, hedges and stop-out logic. Every old ledger/report/source file in the preservation manifest remains unchanged.

The archive is historical SOL data, withBTC only as a macro variable or hedge. New windows are unused in these experiments and have disjoint prescribed histories/evaluation intervals; they are not a live or chronological future holdout, and anonymization cannot guarantee absence from model training. Fixed20bps costs omit funding, borrow and market impact. Original-close S entry ignores model latency; delay sensitivities are shown.

## Budget and conclusion

The remaining20calls were not spent merely to fill the limit. At the strongest long lead's23%trigger rate,20random calls would produce roughly five trades—too few to establish a modest edge. Pooling an extra batch until a p-value turns favorable would not be valid confirmation.

There are positive calculated returns here, and the central data/implementation checks passed. **There is no verified reliable profit opportunity from the tested AI-reversal idea yet.** More parameter search on these same outcomes cannot be treated as new evidence. The strategy objective remains unmet; this report records the completed bounded investigation rather than claiming a profitable system was found.

- [Complete primary trade-by-trade report](../../sim/{R.name}/index.html)
- [All280windows, including skips and controls](../../sim/{R.name}/window_results.csv)
- [Every executed primary trade](../../sim/{R.name}/strategy_trades.csv)
- [All11295search results](search_correction/all_family_results.csv)
- [Frozen primary protocol](VALIDATION_PROTOCOL.md)
- [Primary statistical audit](design/validation_final_statistics_audit.json)
- [Full-family statistical audit](design/expanded_familywise_audit.json)
- [Risk discovery and replay](risk/fresh_grid/FINDINGS.md)
- [Signal discovery and replay](signals/fresh_grid/FINDINGS.md)
- [Hedge study](risk/hedge_study/FINDINGS.md)
- [Stop-out fade study](signals/stopout_fade/FINDINGS.md)

Search-history and untouched-validation separation follow the concern described in [Bailey et al., The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf). The reported returns and tests are calculated from this project's files, not that paper.
'''
# Improve text spacing without altering any immutable protocol or source data.
for a,b in {'all280':'all 280','280new':'280 new','300physical':'300 physical','280were':'280 were','won57.1%':'won 57.1%','required75.1%':'required 75.1%','after20bps':'after 20 bps','its48.4%':'its 48.4%','its48.1%':'its 48.1%','won56.5%':'won 56.5%','a56.0%':'a 56.0%','at20bps':'at 20 bps','at30bps':'at 30 bps','positive15m':'positive 15m','LONG240m':'LONG 240m','SHORT,1.5×AI':'SHORT, 1.5× AI','stop,2×risk':'stop, 2× risk','target,240m':'target, 240m','(56.5%)':' (56.5%)','(48.4%)':' (48.4%)','L0.2911':'L 0.2911','S0.0627':'S 0.0627','rawp0.0313':'raw p=0.0313','824risk':'824 risk','116entry':'116 entry','108invalidation':'108 invalidation','existing150Terra':'existing 150 Terra','721within24h':'721 within-24h','across15direction':'across 15 direction','fixed0.5/1.0':'fixed 0.5/1.0','half-notionalBTC':'half-notional BTC','All16policies':'All 16 policies','on22old':'on 22 old','on22':'on 22','65fresh':'65 fresh','its50-day':'its 50-day','its200-day':'its 200-day','hold240minutes':'hold 240 minutes','unadjusted95%':'unadjusted 95%','11295definitions':'11,295 definitions','not11295independent':'not 11,295 independent','in20,000joint':'in 20,000 joint','observedt':'observed t',';95%family':' ; 95% family','criticalt':'critical t','adjustedp':'adjusted p','All280decisions':'All 280 decisions','replayed primary entries/exits,78,400donor':'replayed primary entries/exits, 78,400 donor','brackets,40,000conditional':'brackets, 40,000 conditional','withBTC':'with BTC','Fixed20bps':'Fixed 20 bps','remaining20calls':'remaining 20 calls',"lead's23%trigger":"lead's 23% trigger",'rate,20random':'rate, 20 random','roughly five':'roughly five','All280windows':'All 280 windows','All11295search':'All 11,295 search','All280':'All 280'}.items():report=report.replace(a,b)
(H/'RESULTS.md').write_text(report)
# A compact native HTML overview links to the complete evidence, without external dependencies.
primary=''.join(f"<tr><td>{k}</td><td>{v['n']}</td><td>{v['gross_win_rate']:.1%}</td><td>{v['mean_gross_pct']:+.3f}%</td><td>{v['mean_net_pct']:+.3f}%</td><td>{v['AI_selection']['p_holm_two_tests']:.3f}</td></tr>" for k,v in S['strategies'].items())
links=[('Written findings','RESULTS.md'),('Every primary trade',f'../../sim/{R.name}/index.html'),('All 11,295 search definitions','search_correction/all_family_results.csv'),('Frozen protocol','VALIDATION_PROTOCOL.md'),('Statistical audit','design/validation_final_statistics_audit.json'),('Expanded search audit','design/expanded_familywise_audit.json'),('Hedge results','risk/hedge_study/FINDINGS.md'),('Stop-out results','signals/stopout_fade/FINDINGS.md')]
style='body{background:#f5f5ef;color:#263a31;font:16px/1.7 system-ui;margin:0}main{max-width:1200px;margin:auto;padding:38px}h1{font-size:36px;line-height:1.2}a{color:#13786d}section{background:white;padding:24px;margin:24px 0;border:1px solid #dae2db;border-radius:10px}table{width:100%;border-collapse:collapse;font-size:15px}td,th{text-align:left;padding:12px;border-bottom:1px solid #dae2db}img{width:100%;height:auto}.notice{padding:20px;background:#fff0d9;border-left:4px solid #b75a20}.muted{color:#69756e;font-size:13px}'
doc=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Deep AI reversal investigation</title><style>{style}</style></head><body><main><p class="muted">280 fresh isolated Terra calls · 11,295 recorded strategy/control definitions · 29 September 2026</p><h1>Positive backtests found; no reliable profit edge verified</h1><p class="notice">Two locked rules had small positive net returns on fresh historical windows. Neither passed the prespecified verification tests. The complete expanded search also produced zero passes after accounting for the number of alternatives tested. The profit objective remains unmet.</p><p>{' · '.join(f'<a href="{u}">{t}</a>' for t,u in links)}</p><section><h2>Fresh test of the two frozen rules</h2><table><tr><th>Rule</th><th>Trades</th><th>Gross win rate</th><th>Mean gross</th><th>Mean net</th><th>AI-value adjusted p</th></tr>{primary}</table><p><strong>L:</strong> AI SHORT, positive first-15-minute confirmation, then long for four hours. <strong>S:</strong> AI LONG, short with stop 1.5× AI stop, target 2× strategy risk, four-hour cap.</p><p>Net assumes 20 bps roundtrip. Both uncertainty intervals include losses; both means turn negative at 30 bps. Removing one largest winner makes each mean negative. Short entry assumes immediate inference; prescribed delays are reported.</p><img src="../../sim/{R.name}/overview.png" alt="Discovery versus fresh results and uncertainty"></section><section><h2>Why win rate was not enough</h2><img src="payoff_geometry.png" alt="Win rate compared with payoff-specific break-even rates"><p>Risk reshaping improved the backtest payoff distribution, but did not create a comfortable margin over fees. New long/short break-even costs were only 21.5/20.8 bps against the assumed 20 bps. These lines describe observed payoff sizes; changing a stop also changes the winning-trade rate.</p></section><section><h2>The wider search did not produce verification</h2><p>11,295 definitions, 9,336 unique return vectors, 24 calendar quarters and 20,000 shared cluster resamples. Global adjusted p={F['global_maxT_p']:.3f}; zero passes. This follow-up reused the validation data and is explicitly exploratory.</p><p>The strongest long lead averaged +0.335% net over 65 newer trades, but only +0.012% in 22 older trades and had a negative latest-period average. Hedging BTC made returns worse. Stop-out fades failed to reproduce between old and new samples. No favorable subset was promoted as verified.</p></section><section><h2>Recorded, checked and preserved</h2><p>Exact anonymized inputs, raw model responses, session isolation audits, all trades, skips, controls and failed search cells are saved. Independent calculations reproduced execution, fees, 78,400 donor brackets, conditional permutations and complete-family corrections. Previous data and results remain unchanged.</p><p>280 of the permitted 300 physical snapshot calls were used, with zero retries. The remaining 20 would be too small to establish the modest effects seen here and were not used for optional stopping. This is historical SOL research, not live or chronological future proof. Funding, borrow and market impact are not modeled.</p></section></main></body></html>'''
(H/'index.html').write_text(doc)
(H/'STATUS.md').write_text('''# Completed bounded investigation; strategy objective unmet

280/300 additional physical calls used, zero retries. Two frozen finalists completed all independent audits and both failed verification despite tiny positive point estimates. Broader search completed11,295definitions; no full-family statistical passes. Hedging andstopouttiming studies also failed robustness. Fullreport:index.html; findings:RESULTS.md; everyattemptandfailedtrialretained. No actualtrades. Remaining20callsunused, notneeded for a meaningful confirmation test at observed effect sizes.
''')
status={'investigation_status':'completed_bounded_investigation','profitable_strategy_verified':False,'physical_snapshot_calls':len(B['reserved_attempts']),'authorized_max':300,'remaining_calls':300-len(B['reserved_attempts']),'fresh_windows':280,'strategy_control_definitions':F['definitions'],'unique_return_vectors':F['unique_return_vectors'],'familywise_passes':F['any_passing_5pct'],'global_family_p':F['global_maxT_p'],'completed_at':datetime.now(timezone.utc).isoformat()}
(H/'completion.json').write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(status))
if __name__=='__main__':pass
