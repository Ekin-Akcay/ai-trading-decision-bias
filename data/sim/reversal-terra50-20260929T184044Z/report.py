from pathlib import Path
import json,html
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];IDEAS=ROOT/'data/research/reversal-ideas-20260929'
S=json.loads((HERE/'summary.json').read_text());D=pd.read_json(HERE/'strategy_trades.jsonl',lines=True);E=html.escape
fmt=lambda x:f'{x:+.3f}%'
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+E(str(h))+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+E(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
short=S['hypotheses']['H-SHORT'];long=S['hypotheses']['H-LONG']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(1,2,figsize=(12,5),gridspec_kw={'width_ratios':[1.1,1]})
for i,(name,r,color) in enumerate([('Reverse AI long → SHORT / 105m',short,'#b45309'),('Reverse AI short → LONG / 30m',long,'#157a70')]):
    x=D.loc[D.hypothesis==('H-SHORT' if i==0 else 'H-LONG'),'gross_pct'].to_numpy();y=np.full(len(x),1-i)+(np.arange(len(x))%5-2)*.055
    ax[0].scatter(x,y,s=24,alpha=.65,color=color);lo,hi=r['ci95_mean_gross_pct'];mu=r['mean_gross_pct'];ax[0].errorbar(mu,1-i+.3,xerr=[[mu-lo],[hi-mu]],fmt='D',capsize=5,color=color)
ax[0].axvline(0,color='#555',lw=1);ax[0].axvline(.2,color='#777',lw=1,ls='--');ax[0].set_yticks([1,0],['SHORT · n=42','LONG · n=8']);ax[0].set_ylim(-.4,1.65);ax[0].set_xlabel('Gross return per trade (%)');ax[0].set_title('Many small wins can still lose money\nDots = trades; diamonds = mean + 95% interval')
labels=['SHORT\n105 min','LONG\n30 min'];pos=np.arange(2);width=.24
ax[1].bar(pos-width,[short['mean_gross_pct'],long['mean_gross_pct']],width,label='Reversal gross',color='#157a70');ax[1].bar(pos,[short['mean_net_pct'],long['mean_net_pct']],width,label='Reversal net',color='#b45309');ax[1].bar(pos+width,[short['baseline']['mean_gross_pct'],long['baseline']['mean_gross_pct']],width,label='No-AI gross baseline',color='#89939a');ax[1].axhline(0,color='#555',lw=1);ax[1].set_xticks(pos,labels);ax[1].set_ylabel('Mean return per trade (%)');ax[1].set_title('No demonstrated incremental AI edge\nBoth selection tests: BH q = 0.935');ax[1].legend(loc='lower right',fontsize=8)
fig.suptitle('50 fresh historical SOL setups · Terra · frozen reversal rules',fontsize=15);fig.text(.5,.015,'Net subtracts 0.20 percentage points per trade. Eligible entries are above both intraday MAs. Not portfolio returns.',ha='center',fontsize=8);fig.tight_layout(rect=[0,.04,1,.92]);fig.savefig(HERE/'overview.png',dpi=170);fig.savefig(HERE/'overview.pdf');plt.close(fig)
rows=[]
for name,r in S['hypotheses'].items():rows.append([name,r['n'],f"{r['gross_positive']}/{r['n']} ({r['gross_win_rate']:.1%})",f"{r['net_positive']}/{r['n']}",fmt(r['mean_gross_pct']),fmt(r['mean_net_pct']),fmt(r['median_gross_pct']),' to '.join(fmt(x) for x in r['ci95_mean_gross_pct']),f"{r['selection_test']['q_bh_two_tests']:.3f}"])
primary=table(['Rule','Trades','Gross wins','Net wins','Mean gross','Mean net','Median gross','95% CI: mean gross','AI-selection q'],rows)
base=table(['No-AI policy on all 50','Gross wins','Mean gross','Mean net'],[[k,f"{v['gross_positive']}/50",fmt(v['mean_gross_pct']),fmt(v['mean_net_pct'])] for k,v in S['baselines'].items()])
controls=table(['Rule','Same-AI-side gross','Same-AI-side net','Next-open reversal gross','Next-open reversal net','Earlier half gross','Later half gross'],[[k,fmt(v['same_ai_direction']['mean_gross_pct']),fmt(v['same_ai_direction']['mean_net_pct']),fmt(v['next_open_entry_sensitivity']['mean_gross_pct']),fmt(v['next_open_entry_sensitivity']['mean_net_pct']),fmt(v['chronological_halves']['earlier']['mean_gross_pct']),fmt(v['chronological_halves']['later']['mean_gross_pct'])] for k,v in S['hypotheses'].items()])
winloss={}
for name,g in D.groupby('hypothesis'):
    winloss[name]={'mean_positive_gross_pct':g.loc[g.gross_pct>0,'gross_pct'].mean(),'mean_negative_gross_pct':g.loc[g.gross_pct<0,'gross_pct'].mean(),'max_loss_pct':g.gross_pct.min(),'max_win_pct':g.gross_pct.max()}
(HERE/'descriptive_payoffs.json').write_text(json.dumps(winloss,indent=2)+'\n')
payoff=table(['Rule','Mean winning trade','Mean losing trade','Worst','Best'],[[k,*[fmt(v[j]) for j in ['mean_positive_gross_pct','mean_negative_gross_pct','max_loss_pct','max_win_pct']]] for k,v in winloss.items()])
cards=[]
for r in D.to_dict('records'):
    case=int(r['case']);chart=f'stimuli/case{case:03d}/chart.png';text=f'stimuli/case{case:03d}/input.txt'
    data=table(['AI side → reversal','Hold','Entry → exit','Gross / net','Max favorable / adverse','Positive minute closes','Original AI bracket'],[[f"{r['ai_action']} → {r['strategy_action']}",f"{r['horizon_minutes']} min",f"{r['entry_price']:.6g} → {r['exit_price']:.6g}",f"{fmt(r['gross_pct'])} / {fmt(r['net_pct'])}",f"{fmt(r['mfe_pct'])} / {fmt(r['mae_pct'])}",f"{r['positive_minute_closes']} / {r['horizon_minutes']}",f"{r['original_bracket_outcome']} · {fmt(r['original_bracket_gross_pct'])} gross · {r['original_bracket_minutes']} min"]])
    cards.append(f'<section id="case-{case}"><h2>Case {case:02d} · {E(r["hypothesis"])}</h2><p class="muted">Private research metadata: SOL-USD · Entry {E(str(r["entry_time"]))} UTC · Exit {E(str(r["exit_time"]))} UTC · {E(r["window_id"])}</p>{data}<p><strong>Saved model explanation:</strong> {E(r["reason"])} <span class="muted">Confidence {r["confidence"]:.0%}; original SL {100*r["stop_pct"]:.2f}%, TP {100*r["tp_pct"]:.2f}%.</span></p><details><summary>View exactly supplied chart and text</summary><img loading="lazy" src="{chart}" alt="Exact anonymized model input, case {case}"><p><a href="{text}">Full model input text</a></p></details></section>')
findings=f'''# Fifty-window reversal test: neither rule establishes a profitable edge

Completed all 50 new historical SOL windows with gpt-5.6-terra, medium reasoning.50 independent sessions, full text/image audit, zero tools, no retries. Old files preserved. This is50 total setups, split42 SHORT trades and8 LONG trades by Terra's direction; not50 per strategy.

| Frozen rule | Trades | Gross-positive | Mean gross/trade | Mean net/trade |
|---|---:|---:|---:|---:|
| Terra LONG → SHORT,105 minutes |42|24/42 (57.1%)|−0.205%|−0.405%|
| Terra SHORT → LONG,30 minutes |8|5/8 (62.5%)|+0.049%|−0.151%|
| Combined |50|29/50 (58.0%)|−0.165%|−0.365%|

Net assumes20 bps roundtrip, not funding/borrow/market impact. These are arithmetic means per trade, not portfolio returns. Both rules had50% net-positive trades.

The short idea failed to reproduce its earlier positive gross estimate. Its average winner was{fmt(winloss['H-SHORT']['mean_positive_gross_pct'])}, while its average loser was{fmt(winloss['H-SHORT']['mean_negative_gross_pct'])}. A57% gross win rate therefore still lost money. The long idea had only 8 signals: its 4.9 bps gross mean did not cover20 bps assumed costs.

Against the same side/time baseline across all 50eligible windows, AI selection changed mean returns by −0.048percentage points for shorts and+0.022points for longs. Label-permutation p-values were 0.586 and 0.935; both BH-adjusted q-values 0.935. Neither result demonstrates incremental value from the AI opinion. Gross-mean 95% intervals: SHORT[−0.653%,+0.220%]; LONG[−0.533%,+0.602%]. Broad intervals do not prove zero effect; they fail to establish an edge.

Terra still chose LONG 42/50 (84%) in this above-both-MA sample. That is a directional preference conditional on the selected regime, not proof of systematically bad forecasts. Following its LONG calls for the same 105 minutes produced+0.205% gross and+0.005% net on those42 cases; that estimate also has an interval crossing zero and is not a new validated strategy.

Prespecified next-bar-open sensitivity (at the same entry timestamp) changes the combined mean only to−0.160% gross/−0.360% net. Both chronological halves lose after costs for H-SHORT; H-LONG changes from+0.068% net in the earlier4 cases to−0.370% in the later4. No extra horizons or thresholds were searched.

The original AI 2:1 bracket trades are recorded separately:18 TP,32 SL, mean+0.068% gross/−0.132% net. Those outcomes are not the reversal strategy. Each trade's original explanation, chart, bracket outcome, reversal price/time, minute-path excursions and returns are in the report and ledgers.

These are previously unused, separated windows from the existing historical archive, not live or chronological held-out data. Bootstrap/permutation inference assumes exchangeability; residual regime dependence and prior exploratory model/rule selection limit conclusions. MAs are intraday, not a daily macro filter. Source timestamps are treated as UTC. Primary entry at the visible close ignores inference latency; next-open sensitivity is not a latency simulation.

I would not call either reversal rule successful from this batch. The long hypothesis is still weakly measured because it fired8 times, but this run does not justify changing its horizon or optimizing a filter on these outcomes. Preserve this result as a failed/uncertain validation.

- [Complete HTML report](../../sim/{S['run_id']}/index.html)
- [All 50 strategy trades](../../sim/{S['run_id']}/strategy_trades.csv)
- [Summary with uncertainty and controls](../../sim/{S['run_id']}/summary.json)
- [Original AI decisions and bracket outcomes](../../sim/decisions/{S['run_id']}.jsonl)
- [Frozen protocol](PROTOCOL.md)
- [Idea archive](IDEAS.md)
'''
(IDEAS/'RESULTS.md').write_text(findings)
# Report-local findings need different relative links.
local=findings.replace('../../sim/'+S['run_id']+'/', '').replace('../../sim/decisions/','../decisions/').replace('(PROTOCOL.md)','(../../research/reversal-ideas-20260929/PROTOCOL.md)').replace('(IDEAS.md)','(../../research/reversal-ideas-20260929/IDEAS.md)')
(HERE/'FINDINGS.md').write_text(local)
style='body{margin:0;background:#f5f5f0;color:#22352f;font:15px/1.65 system-ui}main{max-width:1400px;margin:auto;padding:32px}h1{font-size:34px;line-height:1.2}h2{font-size:23px}section{background:white;border:1px solid #dce2dc;padding:22px;margin:24px 0;border-radius:10px}a{color:#126d62}img{max-width:100%;height:auto}.notice{padding:18px;background:#fff0da;border-left:4px solid #b45309}.muted{color:#63726b;font-size:13px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #dce2dc;white-space:nowrap}th{background:#edf2ed}summary{cursor:pointer}'
doc=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Terra reversal validation ·50 fresh windows</title><style>{style}</style></head><body><main><p class="muted">COMPLETED ·50/50 isolated decisions · September 29, 2026</p><h1>Neither reversal rule establishes a profitable edge</h1><p class="notice">Terra chose LONG42 times and SHORT8 times. Reversing those calls produced29/50gross winners but averaged<strong> −0.165% gross and−0.365% net per trade</strong>. The short rule failed to reproduce its discovery result; the long rule had just8 signals and did not cover costs. Neither AI-selection test distinguished the rule from its no-AI baseline.</p><p>50 total new historical SOL setups, chosen randomly from entries above both intraday MA20/MA50. Reverse AI LONG→SHORT and exit105 minutes; reverse AI SHORT→LONG and exit30 minutes. Rules/model/sample frozen before decisions and outcomes. Each entry is at least122 hours from previously used entries and other new entries. This is a fresh-to-experiment historical test, not live or chronological holdout evidence.</p><p><a href="../../research/reversal-ideas-20260929/IDEAS.md">Idea archive</a> · <a href="../../research/reversal-ideas-20260929/PROTOCOL.md">Frozen protocol</a> · <a href="FINDINGS.md">Findings</a> · <a href="strategy_trades.csv">All 50 trade rows</a> · <a href="../decisions/{S['run_id']}.jsonl">Original AI ledger</a> · <a href="summary.json">Full statistics</a> · <a href="validation.json">Verification</a> · <a href="overview.pdf">Export figure</a></p><img src="overview.png" alt="Individual reversal trade returns, bootstrap intervals and no-AI comparisons"><section><h2>Frozen primary results</h2>{primary}<p>Gross/net are arithmetic per-trade returns. Net subtracts0.20 percentage points (20 bps) roundtrip;50% of trades are net-positive in each group. No compounding/leverage claim. Both gross 95% intervals cross zero. The AI-selection test shuffles long/short labels across all 50 windows, preserving counts; q adjusts the two primary tests.</p></section><section><h2>What the AI opinion added</h2>{base}<p>Relative to the matching side/horizon baseline, AI selection changed SHORT mean by −0.048percentage points and LONG mean by +0.022points. Two-sided permutation p=0.586 and 0.935; BH q=0.935 for both. No demonstrated incremental AI contribution.</p>{controls}<p>Earlier/later means split each triggered group chronologically:21/21 short trades and4/4 long trades. Next-open sensitivity uses the next1-minute bar open with the same exit clock. Primary entry ignores inference latency; sensitivity does not simulate latency.</p></section><section><h2>Why a majority of wins did not mean profit</h2>{payoff}<p>Terra's 84% LONG preference is conditional on an already bullish intraday-MA sample. Directional bias does not by itself imply an exploitable error. Large losing reversal trades outweighed the more frequent small wins. The original AI bracket trades separately had 18 TP/32 SL, averaging+0.068% gross/−0.132% net; they are not this reversal policy.</p></section><p class="muted">10,000 whole-window bootstrap draws, seed 2026092902. One bootstrap draw contained no long signals and is excluded from that subgroup's interval. Regime dependence can remain despite nonoverlapping histories/futures. Costs exclude funding, borrow and market impact. Exploratory prior rule/model selection and small groups limit generalization.</p><h2>All 50 trades and saved model explanations</h2><p>{' · '.join(f'<a href="#case-{i}">{i:02d}</a>' for i in range(1,51))}</p>{''.join(cards)}</main></body></html>'''
(HERE/'index.html').write_text(doc)
(HERE/'HANDOFF.md').write_text(f'''# COMPLETE —50 new Terra decisions and50 reversal trades

All 50 fresh isolated decisions collected, audited and scored. No retries/missing cases. H-SHORT 42 trades, H-LONG 8 trades. Report:index.html; findings:FINDINGS.md; strategy ledger:strategy_trades.jsonl; original AI ledger:../decisions/{S['run_id']}.jsonl. Frozen protocol/idea archive:../../research/reversal-ideas-20260929/.

Both strategies negative net. See summary.json for uncertainty/no-AI baselines. Existing24 source/data/report files hash-verified unchanged. Exact stimuli, raw attempts, session audits, manifest and protocol hash retained. evaluate.py and report.py regenerate only this run's artifacts; existing ledger rows must match before appending. Do not rerun model decisions or change frozen rules based on these results.
''')
p=json.loads((HERE/'progress.json').read_text());p.update(status='complete',scored_decisions=50,strategy_trades=50,report=str((HERE/'index.html').relative_to(ROOT)),ledger=f"data/sim/decisions/{S['run_id']}.jsonl");(HERE/'progress.json').write_text(json.dumps(p,indent=2)+'\n')
print('Report, chart, findings and completion metadata saved.')
