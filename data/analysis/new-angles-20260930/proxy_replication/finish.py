"""Render frozen proxy results without selecting any new policy."""
from pathlib import Path
import hashlib,json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
s=json.loads((HERE/'summary.json').read_text());sample=json.loads((HERE/'frozen_sample.json').read_text())
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in sample['source_sha256'].items())
p=s['policies']['proxy_fade'];inc=s['proxy_minus_MA20']
gate={'study':'frozen_behavior_proxy_new_calendar_replication','phase':'fresh_target_historical_test_after_prior_discovery','model_calls':0,'refits':0,
    'sample_blocks':s['sample_blocks'],'asset_trades':s['asset_trades'],'primary_policy':'proxy_fade','primary_competitor':'MA20_fade','primary_research_candidates':[],
    'gross_profit_gate':s['gross_profit_gate'],'increment_over_MA20_gate':s['increment_over_MA20_gate'],'decision':'NO_VERIFIED_PROXY_EDGE',
    'two_claims_passed':s['two_claims_passed'],'side_or_asset_promotion':False,'sample_sha256':hashlib.sha256((HERE/'frozen_sample.json').read_bytes()).hexdigest(),
    'mean_gross_pct':p['basket']['mean_pct'],'mean_increment_pct':inc['basket']['mean_pct'],
    'interpretation':'Gross mean is near zero; neither frozen claim passes. Descriptive longs/shorts or DOGE may not replace the pooled primary. This is a price-only proxy of AI behavior, not evidence of incremental live AI information.'}
assert not s['two_claims_passed']
(HERE/'CANDIDATE_GATE.json').write_text(json.dumps(gate,indent=2)+'\n')

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,(ax,byyear)=plt.subplots(1,2,figsize=(12.8,4.9),gridspec_kw={'width_ratios':[1.25,1]})
names=['proxy_fade','proxy_follow','always_long','MA20_fade'];labels=['Frozen proxy fade','Proxy-follow mirror','Always long','MA20 fade control']
for i,name in enumerate(names):
    x=s['policies'][name];mean=x['basket']['mean_pct'];lo,hi=x['weekly_intervals']['ci99'];color='#236EA0' if i==0 else '#78838B'
    ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',color=color,capsize=4,lw=1.6)
    ax.text(.143,i,f'{mean:+.4f}%',va='center',fontsize=9,color=color)
ax.axvline(0,color='#333',lw=.9);ax.set_yticks(range(4),labels);ax.invert_yaxis();ax.set_xlim(-.125,.195)
ax.set_xlabel('Mean four-asset basket gross return (%)');ax.set_title('783 fresh calendar targets · 99% whole-week intervals');ax.grid(axis='x',alpha=.18)
d=pd.read_csv(HERE/'calendar_breakdown.csv');d=d[d.policy.eq('proxy_fade')&d.breakdown.eq('year')]
byyear.bar(d.value.astype(str),d.mean_pct,color=['#397EA6' if v>0 else '#BD5757' for v in d.mean_pct])
byyear.axhline(0,color='#333',lw=.9);byyear.set_ylabel('Mean basket gross return (%)');byyear.set_title('Frozen annual models · no refits')
for i,row in enumerate(d.itertuples(index=False)):byyear.annotate(f'{row.mean_pct:+.3f}%\nn={row.n}',(i,row.mean_pct),xytext=(0,5 if row.mean_pct>=0 else -5),textcoords='offset points',ha='center',va='bottom' if row.mean_pct>=0 else 'top',fontsize=9)
byyear.set_ylim(-.065,.115);byyear.grid(axis='y',alpha=.18)
fig.suptitle('Behavior-proxy replication: the earlier gross edge does not transfer clearly',fontsize=14)
fig.text(.5,.025,'3,132 asset trades · 783 four-asset blocks · 192 weeks · 19 quarters · zero costs · fixed 240-minute exit · no new AI calls',ha='center',fontsize=9,color='#545D64')
fig.tight_layout(rect=[0,.07,1,.93]);fig.savefig(HERE/'proxy_replication.png',dpi=170,bbox_inches='tight');plt.close(fig)
print('Final gate and figure written; frozen sources preserved.')
