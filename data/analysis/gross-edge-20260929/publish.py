"""Publish the frozen study, including failures, every decision and trade path."""
from pathlib import Path
import html,json,sys,hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
run=Path(json.loads((HERE/'run.json').read_text())['run_dir'])
s=json.loads((run/'summary.json').read_text());m=json.loads((run/'manifest.json').read_text())
d=pd.read_csv(run/'window_results.csv');t=pd.read_csv(run/'strategy_trades.csv');basket=pd.read_csv(run/'sampled_basket.csv')
budget=json.loads((HERE/'snapshot_budget.json').read_text());calls=len(budget['reserved_attempts'])
rules=s['rules'];e=html.escape
fmt=lambda x:f'{x:+.3f}%' if x is not None else 'unavailable'
def ci(x):return f'[{fmt(x[0])}, {fmt(x[1])}]'
verified=[k for k,v in rules.items() if v['profit_verified'] and v['AI_contribution_verified']]
profit=[k for k,v in rules.items() if v['profit_verified']]
if verified:
    verdict='Fresh gross-return and incremental-AI criteria passed: '+', '.join(verified)+'.'
elif profit:
    verdict='Fresh gross-profit criteria passed for '+', '.join(profit)+', but incremental AI value is not verified.'
else:
    verdict='Neither frozen rule passed the fresh gross-profit verification criteria.'

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
colors=['#2a7f94','#b66b36']
for i,(name,r) in enumerate(rules.items()):
    v=r['selected']['mean_gross_pct'];bounds=r['block_inference']['profit']['simultaneous97_5']
    ax[0,0].errorbar(v,i,xerr=np.array([[v-bounds[0]],[bounds[1]-v]]),fmt='o',color=colors[i],capsize=5)
ax[0,0].set(yticks=[0,1],yticklabels=['L048 · long','S508 · short'],xlabel='Mean gross return per trade (%)',title='Frozen rules · simultaneous block intervals')
ax[0,0].axvline(0,color='#888',lw=1)
assets=list(d.asset.unique());x=np.arange(len(assets))
for i,(name,r) in enumerate(rules.items()):
    vals=[r['assets'][a].get('mean_gross_pct',np.nan) for a in assets]
    ax[0,1].bar(x+(i-.5)*.33,vals,.33,label=name,color=colors[i])
ax[0,1].set(xticks=x,xticklabels=[a.split('-')[0] for a in assets],ylabel='Mean gross return (%)',title='Asset transport');ax[0,1].axhline(0,color='#888',lw=1);ax[0,1].legend()
ax[1,0].plot(pd.to_datetime(basket.entry_time),basket.equity,color='#314f67');ax[1,0].axhline(1,color='#888',lw=1)
ax[1,0].set(ylabel='Sampled basket equity (start = 1)',title='Both rules · equal quarter notional per asset')
cross=pd.crosstab(d.ma_regime,d.action).reindex(['below_both','mixed','above_both']).fillna(0)
pct=cross.div(cross.sum(1),axis=0)*100
ax[1,1].bar(np.arange(3),pct.get('long',0),label='AI long',color='#2a7f94');ax[1,1].bar(np.arange(3),pct.get('short',0),bottom=pct.get('long',0),label='AI short',color='#b66b36')
ax[1,1].set(xticks=np.arange(3),xticklabels=['Below both','Mixed','Above both'],ylabel='AI decisions (%)',title='Direction bias by intraday MAs');ax[1,1].legend()
fig.suptitle('AI reversal · fresh targets · zero transaction costs',fontsize=16)
fig.savefig(run/'overview.png',dpi=170);fig.savefig(run/'overview.pdf');plt.close(fig)

md=['# AI reversal: fee-free fresh validation','',verdict,'',f'{len(d)} isolated Terra snapshots across {s["calendar_blocks"]} calendar blocks and four assets. {calls} physical calls used in this phase; {budget["prior_phase_attempts"]+calls} including the previous280. No historical findings were overwritten. All primary returns below are unlevered and exclude costs.','',
    '| Frozen rule | Trades / blocks | Gross per trade | Gross wins | Simultaneous block interval | Price-only mean |','|---|---:|---:|---:|---:|---:|']
for name,r in rules.items():
    a=r['selected'];md.append(f'| {name} | {a["n"]} / {r["selected_blocks"]} | {fmt(a["mean_gross_pct"])} | {a["win_rate"]:.1%} | {ci(r["block_inference"]["profit"]["simultaneous97_5"])} | {fmt(r["eligible_price_only"]["mean_gross_pct"])} |')
md+=['','L048: when AI chooses SHORT and the completed prior-day asset close≤50DMA and BTC close≤200DMA, buy at the next minute open and exit after240minutes. S508: when AI chooses LONG above both intraday MAs, short with stop=target=2×ATR14 and a240-minute timeout.','',
     '## What survives the checks','']
for name,r in rules.items():
    md += [f'**{name}**: profit verified={r["profit_verified"]}; incremental AI contribution verified={r["AI_contribution_verified"]}.',
           f'- Quarter-bootstrap95% profit interval: {ci(r["quarter_inference"]["profit"]["ci95"])}.',
           f'- AI increment after asset/era/MA-stratum standardization: {fmt(r["block_inference"]["AI_increment_mean_pct"])}; simultaneous block interval {ci(r["block_inference"]["AI_increment"]["simultaneous97_5"])}.',
           f'- Entry delayed1/5minutes: {fmt(r["delay_sensitivities"]["1"]["mean_gross_pct"])}, {fmt(r["delay_sensitivities"]["5"]["mean_gross_pct"])}.',
           f'- Chronological halves: '+', '.join(fmt(v.get('mean_gross_pct')) for v in r['chronological_halves'])+'.',
           f'- Removing the largest1/3winners: {fmt(r["selected"]["exclude_best1_mean_pct"])}, {fmt(r["selected"]["exclude_best3_mean_pct"])}.',
           '- Failed profit criteria: '+(', '.join(k for k,v in r['profit_criteria'].items() if not v) or 'none')+'.','']
md+=['## Interpretation','',
     'The500calls contain125distinct market times, so uncertainty resamples whole four-asset blocks and whole quarters. New future paths do not overlap previously examined chart/history/outcome intervals; feature histories may reuse known past data. This is newly held-out historical target data, not live trading or proof against model pretraining exposure.',
     '', 'The price-only controls execute the identical direction and geometry whenever the price gate holds. The standardized comparison asks whether AI selection adds information beyond declared asset, era and intraday-MA groups. It does not establish causality or superiority to every possible price-only model.',
     '',f'The secondary sampled basket returned {fmt(s["combined_sampled_basket"]["final_return_pct"])} with {fmt(s["combined_sampled_basket"]["maximum_drawdown_pct"])} maximum drawdown. It holds one-quarter equity notional per eligible asset and cash for skips. This sparse experimental basket is not an annualized or continuously deployed strategy; it cannot rescue failed primary rules.',
     '', 'Leverage was not used in the test. The zero-cost assumption excludes spread, commissions, funding and liquidation mechanics. A positive gross result would still need executable pricing and position-sizing validation before any live profitability claim.',
     '', 'Secondary fixed-percentage short and15-minute-confirmed long results remain labeled secondary in summary.json. No post-outcome rule was promoted to a winner.',
     '', '## Artifacts','',f'- [Interactive trade report]({run}/index.html)',f'- [Full strategy trade ledger]({run}/strategy_trades.csv)',f'- [Model decisions]({run}/accepted_decisions.jsonl)',f'- [Machine-readable summary]({run}/summary.json)',f'- [Locked protocol]({HERE}/VALIDATION_PROTOCOL.md)',f'- [Sampling audit]({HERE}/design/sampling_design_audit.json)','']
text='\n'.join(md)
(HERE/'RESULTS.md').write_text(text);(run/'FINDINGS.md').write_text(text)

cards=[]
for name,r in rules.items():
    a=r['selected'];cards.append(f'<article><h2>{name} · {"Long" if name=="L048" else "Short"}</h2><strong>{fmt(a["mean_gross_pct"])}</strong><p>gross per trade · {a["n"]} trades · {a["win_rate"]:.1%} wins</p><p>Block interval {ci(r["block_inference"]["profit"]["simultaneous97_5"])}</p><p>Gross profit verified: <b>{r["profit_verified"]}</b><br>Incremental AI verified: <b>{r["AI_contribution_verified"]}</b></p></article>')
checks=[]
for name,r in rules.items():
    checks.append(f'<tr><td>{name}</td><td>{fmt(r["eligible_price_only"]["mean_gross_pct"])}</td><td>{fmt(r["block_inference"]["AI_increment_mean_pct"])}</td><td>{ci(r["block_inference"]["AI_increment"]["simultaneous97_5"])}</td><td>{fmt(r["delay_sensitivities"]["1"]["mean_gross_pct"])}</td><td>{fmt(r["delay_sensitivities"]["5"]["mean_gross_pct"])}</td></tr>')
payload=[]
for _,row in t.iterrows():
    src=d[d.case==row['case']].iloc[0]
    payload.append({'rule':row['rule'],'case':int(row['case']),'block':int(row['block']),'asset':row.asset,'date':row.entry_time,'selected':bool(row.selected),'eligible':bool(row.eligible),
                    'AI':row.AI_action,'gross':float(row.gross_pct),'exit':row.outcome,'held':int(row.held_minutes),'mae':float(row.mae_through_exit_bar_pct),'mfe':float(row.mfe_through_exit_bar_pct),
                    'reason':str(src.reason),'confidence':float(src.confidence),'move15':float(row.scheduled_direction_move_15m_pct),'move60':float(row.scheduled_direction_move_60m_pct),
                    'image':f'stimuli/case{int(row["case"]):03d}/chart.png','input':f'stimuli/case{int(row["case"]):03d}/input.txt'})
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI reversal · fresh gross validation</title>
<style>body{margin:0;background:#f5f5f1;color:#172d3a;font:15px/1.5 system-ui,sans-serif}main{max-width:1260px;margin:auto;padding:34px 24px}h1{font-size:36px;line-height:1.1}h2{font-size:20px}.eyebrow{font-size:12px;letter-spacing:.15em;text-transform:uppercase;color:#526873}.verdict{background:#e6ebec;padding:18px;border-left:4px solid #314f67}.cards{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:24px 0}article{background:white;border:1px solid #d4dddd;padding:24px}article strong{font-size:38px}article h2{margin-top:0}.note{color:#526873;max-width:1040px}img.overview{width:100%;border:1px solid #d4dddd}table{border-collapse:collapse;width:100%;font-size:13px;background:#fff}th,td{padding:9px;border-bottom:1px solid #e1e5e5;text-align:right}th:first-child,td:first-child{text-align:left}th{background:#e7ecec;position:sticky;top:0}.tablewrap{overflow:auto;max-height:640px}select,input{font:inherit;padding:8px;margin:6px 10px 12px 0;border:1px solid #afc0c4;background:#fff}a{color:#1b7189}button{cursor:pointer;font:inherit;background:#eef4f4;border:1px solid #b3c6cb;border-radius:4px}dialog{max-width:1050px;width:90%;border:1px solid #b3c6cb}dialog img{max-width:100%}.negative{color:#a3402a}.positive{color:#1c7276}@media(max-width:700px){.cards{grid-template-columns:1fr}main{padding:20px 12px}h1{font-size:28px}}</style>
<main><div class="eyebrow">NAI Trading / locked historical test / zero fees</div><h1>Does reversing the AI add an edge?</h1>
<p>500 isolated Terra snapshots · 125 calendar blocks · SOL, BTC, ETH, DOGE</p><p class="verdict">VERDICT</p><div class="cards">CARDS</div>
<p class="note">L048 buys against AI shorts in the specified daily downtrend and exits after four hours. S508 shorts against AI longs above both intraday averages with stop and target each two ATRs, capped at four hours. Both rules were fixed before opening these outcomes.</p>
<img class="overview" src="overview.png" alt="Gross returns, asset results, sampled equity, and MA direction bias">
<h2>Controls and timing</h2><div class="tablewrap"><table><thead><tr><th>Rule</th><th>Price-only mean</th><th>Standardized AI increment</th><th>Increment interval</th><th>Entry +1min</th><th>Entry +5min</th></tr></thead><tbody>CHECKS</tbody></table></div>
<p class="note">Returns are unlevered percentages with zero costs. Intervals resample complete four-asset blocks. The full findings include quarter uncertainty, chronological consistency and winner concentration. The sparse basket is descriptive, not an annualized deployed strategy.</p>
<p><a href="FINDINGS.md">Full findings</a> · <a href="summary.json">Summary JSON</a> · <a href="strategy_trades.csv">Trade ledger CSV</a> · <a href="accepted_decisions.jsonl">Raw decisions</a> · <a href="isolation_audit.json">Isolation audit</a> · <a href="../../analysis/gross-edge-20260929/VALIDATION_PROTOCOL.md">Locked protocol</a></p>
<h2>Every position and model opinion</h2><label>Rule <select id="rule"><option value="">Both</option>L048</option><option>S508</option></select></label><label>Asset <select id="asset"><option value="">All</option>SOL-USD</option><option>BTC-USD</option><option>ETH-USD</option><option>DOGE-USD</option></select></label><label>Rows <select id="scope"><option value="selected">Executed trades</option><option value="eligible">Price-eligible, including skips</option><option value="all">All model windows</option></select></label><span id="count"></span>
<div class="tablewrap"><table><thead><tr><th>Case</th><th>Rule</th><th>Asset</th><th>UTC entry</th><th>AI</th><th>Trade?</th><th>Gross</th><th>Exit</th><th>Minutes</th><th>MAE*</th><th>MFE*</th><th>15m move</th><th>60m move</th></tr></thead><tbody id="rows"></tbody></table></div>
<p class="note">For skipped rows, returns show the hypothetical price-only control. Click a case to inspect the exact anonymized input and model reason. *MAE/MFE include the full exit minute because intraminute ordering is unknown; scheduled moves can extend beyond an earlier bracket exit. Actual trade return always stops at its recorded exit.</p><p class="note">CALLS physical attempts in this phase. Earlier reports and ledgers remain unchanged.</p></main>
<dialog id="detail"><button id="close">Close</button><h2 id="detailtitle"></h2><p id="reason"></p><a id="input">Exact model input</a><br><img id="chart" alt="Anonymized model chart"></dialog>
<script>const data=PAYLOAD;const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const pct=x=>(x>=0?'+':'')+x.toFixed(3)+'%';function render(){const z=data.filter(x=>(!rule.value||x.rule===rule.value)&&(!asset.value||x.asset===asset.value)&&(scope.value==='all'||x[scope.value]));count.textContent=z.length+' rows';rows.innerHTML=z.map(x=>`<tr><td><button data-key="${x.rule}:${x.case}">${x.case}</button></td><td>${x.rule}</td><td>${x.asset}</td><td>${esc(x.date)}</td><td>${x.AI}</td><td>${x.selected?'yes':'skip'}</td><td class="${x.gross<0?'negative':'positive'}">${pct(x.gross)}</td><td>${x.exit}</td><td>${x.held}</td><td>${pct(x.mae)}</td><td>${pct(x.mfe)}</td><td>${pct(x.move15)}</td><td>${pct(x.move60)}</td></tr>`).join('')}for(const id of ['rule','asset','scope'])document.getElementById(id).addEventListener('change',render);rows.addEventListener('click',ev=>{const key=ev.target.dataset.key;if(!key)return;const x=data.find(z=>z.rule+':'+z.case===key);detailtitle.textContent=x.rule+' · case '+x.case+' · '+x.asset;reason.textContent='AI '+x.AI+' · confidence '+x.confidence+' · '+x.reason;chart.src=x.image;input.href=x.input;detail.showModal()});document.getElementById('close').onclick=()=>detail.close();render();</script></html>'''
page=page.replace('VERDICT',e(verdict)).replace('CARDS',''.join(cards)).replace('CHECKS',''.join(checks)).replace('CALLS',str(calls)).replace('PAYLOAD',json.dumps(payload).replace('</','<\\/'))
(run/'index.html').write_text(page)
(HERE/'index.html').write_text(f'<!doctype html><meta charset="utf-8"><title>Gross edge research</title><h1>AI reversal: fresh gross validation</h1><p>{e(verdict)}</p><p><a href="../../sim/{run.name}/index.html">Open complete trade report</a></p><p><a href="RESULTS.md">Read findings</a> · <a href="VALIDATION_PROTOCOL.md">Protocol</a></p>')
pointer=ROOT/'data/sim/reports'/f'{run.name}.html'
assert not pointer.exists(), 'Refuse to overwrite an existing shared report'
pointer.write_text(f'<!doctype html><meta charset="utf-8"><title>AI reversal fresh gross validation</title><h1>AI reversal: fresh gross validation</h1><p>{e(verdict)}</p><a href="../{run.name}/index.html">Open full report and all trades</a>')
print(json.dumps({'verdict':verdict,'report':str(run/'index.html'),'findings':str(HERE/'RESULTS.md'),'physical_calls':calls},indent=2))
