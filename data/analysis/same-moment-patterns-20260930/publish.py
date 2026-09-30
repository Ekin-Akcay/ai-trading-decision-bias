"""Build the saved findings and trade-by-trade inspection report."""
from pathlib import Path
import json,html,hashlib
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P=Path(__file__).resolve().parent;ROOT=P.parents[2]
def load(name):return json.loads((P/name).read_text())
def pct(x):return f'{x:+.3f}%'
volume=load('volume_reaction/summary.json');vs={r['policy']:r for r in volume}
diag=load('volume_reaction/diagnostics_summary.json');ds={r['policy']:r for r in diag}
joint=pd.read_csv(P/'joint_results.csv')
managed=pd.read_csv(P/'managed_exits/policy_summary.csv').set_index('policy')
lead=vs['quiet_up_extension_short__noAI'];cirow=joint[joint.policy.eq(lead['policy'])].iloc[0]
allrows=pd.read_csv(P/'volume_reaction/trade_ledger.csv')
tr=allrows[allrows.policy.eq(lead['policy'])&allrows.selected].copy().sort_values(['original_entry_time','asset'])
assert len(tr)==56
total=tr.groupby('original_entry_time').gross_pct.sum().sort_values(ascending=False)
top3=set(total.index[:3]);tr['removed_in_best3_check']=tr.original_entry_time.isin(top3)
pf=tr.loc[tr.gross_pct>0,'gross_pct'].sum()/-tr.loc[tr.gross_pct<0,'gross_pct'].sum()
tr.to_csv(P/'quiet_rally_trades.csv',index=False)

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig,(ax,bx)=plt.subplots(1,2,figsize=(12,4.6),gridspec_kw={'width_ratios':[1.3,1]})
labels=['Quiet-rally short','Remove best 3 events','Entry 1 minute later','Entry 5 minutes later','Same rise, any volume','Unconditional short']
means=[lead['gross_mean_pct'],lead['without_best3_blocks_pct'],ds['quiet_up_short_delay1']['gross_mean_pct'],ds['quiet_up_short_delay5']['gross_mean_pct'],ds['up_geometry_only_short']['gross_mean_pct'],ds['unconditional_delayed_short']['gross_mean_pct']]
yy=np.arange(len(labels));ax.barh(yy,means,color=['#247399' if v>=0 else '#b65c5c' for v in means]);ax.set_yticks(yy,labels);ax.invert_yaxis();ax.axvline(0,color='#555',lw=.8);ax.set_xlabel('Mean gross return per executed trade (%)');ax.set_title('Observed return and execution checks')
for i,v in enumerate(means):ax.text(v+0.008 if v>=0 else 0.008,i,pct(v),va='center',ha='left',fontsize=9)
ax.set_xlim(-.085,.52);ax.grid(axis='x',alpha=.15)
b=pd.read_csv(P/'volume_reaction/breakdown.csv');b=b[b.policy.eq(lead['policy'])&b.group.eq('fold')].sort_values('label')
bx.bar(np.arange(1,6),b.gross_mean_pct,color='#247399');bx.axhline(0,color='#555',lw=.8);bx.set_xticks(np.arange(1,6));bx.set_xlabel('Chronological fifth of original market moments');bx.set_ylabel('Mean gross return per trade (%)');bx.set_title('All five chronological groups positive')
for i,r in enumerate(b.itertuples(),1):bx.text(i,r.gross_mean_pct+.015,f'n={r.trades}',ha='center',fontsize=9)
bx.set_ylim(0,.72);bx.grid(axis='y',alpha=.15)
fig.suptitle('Quiet rallies: a coherent exploratory lead, not verified profitability',fontsize=13)
fig.text(.5,.015,'56 trades / 46 entry-time clusters · 34 wins · zero fees · observed outcomes reused · whole-search interval includes zero',ha='center',fontsize=9,color='#555')
fig.tight_layout(rect=[0,.055,1,.94]);fig.savefig(P/'quiet_rally_review.png',dpi=160);plt.close(fig)

rule='Wait 30 minutes after an existing AI snapshot. If price has risen at least half of the original ATR14 and those 30 minutes have at most 75% of the median 30-minute volume from the preceding 50 hours, short at the next minute open. Exit after 120 complete minutes. No AI-direction filter, stop or target.'
readme=f'''# Same-moment pattern tests

This pass found one coherent **exploratory price/volume lead**: shorting a quiet rally. It is based entirely on moments where AI decisions already existed. No new trade-agent calls or new sampled dates were used. The remaining29 snapshot credits are preserved.

The lead is a price-only comparison rule that emerged from the volume study. It does not establish that AI consistently makes the wrong directional call. All outcomes have already been studied, and every favorable result here remains exploratory.

## Exact rule

{rule}

ATR is the pre-entry value already supplied in the original snapshot. Both volume sums use native minute data; the reference is100 consecutive30-minute sums before the snapshot. The feature becomes known at elapsed30 minutes; entry is minute31 open and exit minute150 close. One original window lacked complete volume history and was excluded from all volume policies, leaving1019 eligible windows.

## Observed result

| Measure | Result |
|---|---:|
| Executed positions / original-entry clusters |56 /46|
| Wins |34 /56 (60.7%)|
| Mean gross per trade |+0.3921%|
| Median gross |+0.1209%|
| Average winner / loser |+0.9682% /−0.4982%|
| Gross profit factor |{pf:.2f}|
| Worst / best position |−2.9184% /+9.1835%|
| Mean after removing best entry-time cluster |+0.2323%|
| Mean after removing best3 entry-time clusters |+0.1038%|
| Chronological halves |+0.4976% /+0.2939%|
| Entry delayed1 /5 minutes, still held120 minutes |+0.4070% /+0.3468%|

All five chronological groups and all seven sampled calendar years have positive means. Four of five source cohorts are positive; the above-MA enriched next50 cohort contributes only two trades and averages−1.2479%. All four asset means are nonnegative, but BTC is effectively flat on six trades. Most observations are SOL (36 of56). These splits support further investigation; they are not independent holdouts.

The original ordinary quarter-bootstrap95% interval is+0.0798% to+0.6889%. The14-definition volume-family interval includes zero. Across all44 definitions in this pass, the conservative simultaneous interval is **{cirow.whole_search_simultaneous_low_pct:+.4f}% to{cirow.whole_search_simultaneous_high_pct:+.4f}%**. None of the44 definitions has a positive whole-search lower bound. That correction still does not erase earlier adaptive research history. This is an observed gross result, not verified future profitability.

## What the comparisons say

The same upward half-ATR geometry without the volume filter averages−0.0202% across248 shorts. Unconditional shorting at the same delayed clock averages+0.0123% across1019 positions. These are post-score diagnostic comparisons, clearly separated from the original frozen family. The quiet-rally rule's conditional mean is higher, but its paired opportunity-return improvements remain uncertain: +0.02646 percentage points versus geometry alone and+0.00927 points versus unconditional shorts; both intervals include zero. They do not establish a causal volume effect.

The lead only trades5.5% of eligible snapshots. Its mean per original eligible opportunity, counting skips as zero, is+0.02155%; the+0.3921% figure is per executed trade. Neither is an annualized, compounded or leverage-adjusted account return.

Splitting the same quiet-rally positions by original AI action gives40 trades averaging+0.4614% when the AI had already said SHORT, and16 averaging+0.2190% when it had said LONG. This split was inspected after the original result and is descriptive. The stronger subset **follows a bearish call after waiting for a counter-move**. It suggests an entry-timing hypothesis; it does not prove incremental AI value or justify retrospectively restricting the rule.

For long trades, the quiet-down/AI-LONG partition averages+0.1287% over37 positions, but falls to−0.0297% after removing its three best market events. The declared long candidates lose. There is no comparably coherent long lead from this pass.

## Other ideas tested

- Protecting reversed positions with breakeven, trailing stops or partial profit-taking: means {managed.loc['BE_after_1ATR','mean_gross_pct']:+.4f}%, {managed.loc['TRAIL_1ATR_after_1ATR','mean_gross_pct']:+.4f}% and {managed.loc['HALF_at_1ATR_then_BE','mean_gross_pct']:+.4f}% over1020 positions. The unchanged240-minute hold is+0.0550%. These management rules reduced returns.
- BTC recovering while an AI-bearish asset lags: the two long policies average−0.1173% and−0.1494%. Both mirrored short policies and all direct price-only gates also lose.
- High-volume recovery/rejection and quiet directional extensions with an AI-reversal filter: the long policies lose; the positive short cells become negative after removing their best3 market events.

There were11 initial candidate definitions and26 declared controls/comparators, followed by seven explicitly post-score diagnostics. All44 vectors (43 unique) are retained. No parameter grid, new model opinion or extra market moment was added.

## Files

- [HTML trade inspector](index.html): all56 quiet-rally positions, original AI reasons, prices and interactive paths.
- [All56 trades](quiet_rally_trades.csv): entries, exits, returns, volume/price features and top-event flags.
- [Volume study](volume_reaction/RESULTS.md), [BTC reaction study](market_reaction/RESULTS.md), [managed exits](managed_exits/RESULTS.md).
- [All current results](joint_results.csv), [joint uncertainty calculation](joint_audit.json), and independent audit artifacts in audit/.
- [Post-score diagnostics](volume_reaction/POST_SCORE_DIAGNOSTICS.md) records exactly what was added after seeing results.

Earlier decisions, reports and the771-attempt budget ledger remain unchanged. Numerical audits verify the simulated executions and statistics; they do not convert exploratory findings into a demonstrated market edge.
'''
# Keep the prose readable without altering identifiers or data.
for old,new in [('remaining29','remaining 29'),('reference is100','reference is 100'),('consecutive30','consecutive 30'),('elapsed30','elapsed 30'),('minute31','minute 31'),('minute150','minute 150'),('leaving1019','leaving 1019'),('best3','best 3'),('delayed1 /5','delayed 1 /5'),('held120','held 120'),('only two','only two'),('averages−','averages −'),('36 of56','36 of 56'),('quarter-bootstrap95','quarter-bootstrap 95'),('The14-definition','The 14-definition'),('all44','all 44'),('of the44','of the 44'),('across248','across 248'),('across1019','across 1019'),('and+','and +'),('only trades5.5','only trades 5.5'),('gives40','gives 40'),('and16','and 16'),('over37','over 37'),('over1020','over 1020'),('unchanged240','unchanged 240'),('were11','were 11'),('and26','and 26'),('All44','All 44'),('all56','all 56'),('All56','All 56'),('the771','the 771')]:readme=readme.replace(old,new)
(P/'RESULTS.md').write_text(readme)
(P/'volume_reaction/RESULTS.md').write_text('# Volume reaction study\n\nRead the parent RESULTS.md for the quiet-rally lead, complete uncertainty and all limitations. The original four AI-reversal candidates all fail their declared screen. The price-only quiet-up short comparison produces the most coherent positive point result; it remains exploratory.\n\nOriginal rules and all controls: PLAN.md, summary.json, comparisons.json, trade_ledger.csv, breakdown.csv and vectors.npz. Additional diagnostic rules are explicitly post-score in POST_SCORE_DIAGNOSTICS.md and diagnostics_*.json/npz/csv. No original rule was replaced.\n')
(P/'QUIET_RALLY_IDEA.md').write_text('# Quiet-rally short: retained research hypothesis\n\n'+rule+'\n\nObserved: 56 positions /46 event clusters, +0.3921% mean gross, 60.7% wins; removing the best three event clusters leaves +0.1038%. The rule survives fixed 1/5-minute entry delays descriptively. Whole-search uncertainty includes losses. This needs separate verification before a profitability claim; no additional calls are queued.\n\nThe rule is price-only. An after-the-fact subset with original AI SHORT has a larger mean, suggesting delayed entry in the original direction, but no AI-specific effect is established. Full results, failures and source cohorts are in RESULTS.md.\n')

def table(headers,rows):return '<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'
wn=pd.read_csv(ROOT/'data/analysis/new-angles-20260930/target_exhaustion/windows.csv');paths=np.load(ROOT/'data/analysis/new-angles-20260930/target_exhaustion/paths.npz')['paths'];lookup={x:i for i,x in enumerate(wn.window_id)}
payload=[]
for r in tr.itertuples():
    i=lookup[r.window_id];p=paths[i];o=p[1,0]
    payload.append(dict(window=r.window_id,asset=r.asset,cohort=r.cohort,AI=r.AI_action,reason=r.AI_reason,time=r.original_entry_time,entry=r.entry_time,exit=r.exit_time,entryPrice=r.entry_price,exitPrice=r.exit_price,gross=r.gross_pct,volume=r.volume_ratio,rise=r.early_long_return_pct,best3=bool(r.removed_in_best3_check),curve=np.r_[100,100*p[1:151,3]/o].round(5).tolist(),tradeEntry=100*r.entry_price/o,tradeExit=100*r.exit_price/o))
data=json.dumps(payload,allow_nan=False).replace('<','\\u003c')
comparison_rows=[[labels[i],pct(means[i])] for i in range(len(labels))]
jointrows=[[r.family,r.policy,r.role,r.trades,pct(r.gross_mean_pct),f'[{r.whole_search_simultaneous_low_pct:+.3f}, {r.whole_search_simultaneous_high_pct:+.3f}]%'] for r in joint.itertuples()]
html_doc='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Same-moment trade simulations</title><style>
body{margin:0;padding:32px;background:#101723;color:#e7edf6;font:16px/1.55 system-ui,sans-serif;max-width:1450px}h1,h2{line-height:1.2}p{max-width:1050px}a{color:#93c7ff}.cards{display:flex;gap:12px;flex-wrap:wrap}.card{background:#1c2b3d;padding:18px;min-width:180px}.card strong{display:block;font-size:26px}.note{border-left:4px solid #e2b963;padding:16px;background:#28271f}.wrap{overflow:auto;margin:18px 0}table{border-collapse:collapse;font-size:14px;width:100%}td,th{padding:10px;border-bottom:1px solid #354459;text-align:left;vertical-align:top}th{background:#1c2b3d}#rows tr{cursor:pointer}#rows tr:hover{background:#253449}input,button,select{background:#1c2b3d;color:#e7edf6;border:1px solid #5a6b82;padding:9px;font:inherit}button{cursor:pointer;margin:5px}#chart{width:100%;max-width:1100px;background:#192435}#detail{padding:16px;background:#1c2b3d;margin-top:16px}small{color:#bac6d7}.scroll{max-height:560px;overflow:auto}img{max-width:1250px;width:100%;height:auto}
</style><h1>Same-moment trade simulations</h1><p>Existing AI decisions and their original market windows. Three pattern families, zero new trade-agent calls. <strong>29 snapshot credits remain.</strong></p>
<h2>Exploratory lead: short a quiet rally</h2><div class="cards"><div class="card"><strong>56</strong>positions /46 event clusters</div><div class="card"><strong>+0.392%</strong>mean gross per trade</div><div class="card"><strong>60.7%</strong>win rate</div><div class="card"><strong>+0.104%</strong>after removing best3 events</div></div>
<p>__RULE__</p><div class="note">The same outcomes have been examined before. The conservative interval across all44 tested definitions is −0.174% to+0.935% per trade. This is a research lead, not verified profitability. All results use zero fees and unlevered initial notional.</div>
<p>The stronger original-AI-SHORT subset follows a bearish call after waiting for a rally:40 trades,+0.461% mean. That partition is post-score and descriptive. The declared long candidates lose, and the positive long diagnostic loses after removal of its best3 events.</p>
<p><a href="RESULTS.md">Full findings</a> · <a href="QUIET_RALLY_IDEA.md">Exact research idea</a> · <a href="quiet_rally_trades.csv">All56 positions</a> · <a href="joint_results.csv">All44 results</a></p>
<img src="quiet_rally_review.png" alt="Quiet-rally mean remains positive in timing and concentration checks; all chronological groups positive">
<h2>Price and execution comparisons</h2><p>These checks were added after seeing the original control result and are labelled post-score. Entry delays retain120 complete minutes after the actual fill. Conditional means use different trade counts; paired opportunity-return improvements remain uncertain.</p>__COMPARISONS__
<h2>Inspect every quiet-rally position</h2><p>Prices below are normalized to100 at the original snapshot's first native minute open. The shaded interval is the30-minute observation period; the green marker is the actual short entry and red marker the time exit. Click a row to inspect its original AI reason and path.</p>
<input id="filter" aria-label="Filter trades" placeholder="Filter asset, date, AI side or window…"><button id="median">Median trade</button><button id="best">Best trade</button><button id="worst">Worst trade</button><p id="count"></p><svg id="chart" viewBox="0 0 1000 290" role="img" aria-label="Selected trade price path"></svg><div id="detail"></div>
<div class="scroll"><table><thead><tr><th>Original time</th><th>Asset</th><th>AI</th><th>Volume ratio</th><th>First30m rise</th><th>Gross</th><th>Best3-event flag</th><th>Window</th></tr></thead><tbody id="rows"></tbody></table></div>
<h2>Every candidate and control retained</h2><p>11 original candidates and26 declared comparisons, plus seven post-score diagnostics. The44 columns include one duplicate. No whole-search interval excludes zero on the positive side. All prior experiments are preserved.</p><div class="wrap">__ALL__</div>
<script>
const trades=__DATA__;
const fmt=x=>(x>=0?'+':'')+x.toFixed(3)+'%';
const body=document.getElementById('rows');
function show(t){
const all=[...t.curve,t.tradeEntry,t.tradeExit],lo=Math.min(...all),hi=Math.max(...all),pad=Math.max(.03,(hi-lo)*.1),bottom=lo-pad,top=hi+pad;
const xx=m=>64+m/150*900, yy=v=>245-(v-bottom)/(top-bottom)*210;
const points=t.curve.map((v,i)=>xx(i)+','+yy(v)).join(' ');
let grid='';for(let i=0;i<5;i++){const v=bottom+(top-bottom)*i/4;grid+=`<line x1="64" x2="964" y1="${yy(v)}" y2="${yy(v)}" stroke="#34445b"/><text x="55" y="${yy(v)+4}" text-anchor="end" fill="#c8d3e2" font-size="12">${v.toFixed(2)}</text>`;}
for(const m of[0,30,60,90,120,150])grid+=`<text x="${xx(m)}" y="268" text-anchor="middle" fill="#c8d3e2" font-size="12">${m}m</text>`;
document.getElementById('chart').innerHTML=`<rect x="${xx(0)}" y="26" width="${xx(30)-xx(0)}" height="220" fill="#33404e"/>${grid}<polyline points="${points}" fill="none" stroke="#92c9ff" stroke-width="2"/><line x1="${xx(30)}" x2="${xx(30)}" y1="26" y2="246" stroke="#80d3ac" stroke-dasharray="4 4"/><circle cx="${xx(30)}" cy="${yy(t.tradeEntry)}" r="5" fill="#80d3ac"/><circle cx="${xx(150)}" cy="${yy(t.tradeExit)}" r="5" fill="#ef948d"/><text x="64" y="17" fill="#c8d3e2" font-size="13">Normalized price · elapsed minutes after original AI moment</text>`;
document.getElementById('detail').textContent=t.asset+' | '+t.window+' | AI '+t.AI.toUpperCase()+': '+t.reason+' | Short entry '+t.entry+' @ '+t.entryPrice+'; exit '+t.exit+' @ '+t.exitPrice+'; gross '+fmt(t.gross)+'. Volume ratio '+t.volume.toFixed(3)+'; first30m move '+fmt(t.rise)+'.';
}
function render(){const q=document.getElementById('filter').value.toLowerCase();body.replaceChildren();let n=0;for(const t of trades){if(![t.asset,t.time,t.AI,t.window].join(' ').toLowerCase().includes(q))continue;n++;const r=document.createElement('tr');for(const v of[t.time,t.asset,t.AI,t.volume.toFixed(3),fmt(t.rise),fmt(t.gross),t.best3?'Yes':'',t.window]){const c=document.createElement('td');c.textContent=v;r.append(c);}r.addEventListener('click',()=>show(t));body.append(r);}document.getElementById('count').textContent=n+' of '+trades.length+' trades';}
const sorted=[...trades].sort((a,b)=>a.gross-b.gross);document.getElementById('filter').addEventListener('input',render);document.getElementById('best').onclick=()=>show(sorted.at(-1));document.getElementById('worst').onclick=()=>show(sorted[0]);document.getElementById('median').onclick=()=>show(sorted[Math.floor(sorted.length/2)]);render();show(sorted[Math.floor(sorted.length/2)]);
</script></html>'''
html_doc=html_doc.replace('__RULE__',html.escape(rule)).replace('__COMPARISONS__',table(['Definition','Mean gross/trade'],comparison_rows)).replace('__ALL__',table(['Family','Policy','Role','Trades','Mean gross','Whole-search interval'],jointrows)).replace('__DATA__',data)
(P/'index.html').write_text(html_doc)
print('Published RESULTS.md, index.html, quiet_rally_trades.csv and quiet_rally_review.png')
