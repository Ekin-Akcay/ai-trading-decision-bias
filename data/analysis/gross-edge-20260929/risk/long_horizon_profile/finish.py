"""Reconcile cached native vectors and render the fixed diagnostic profile."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
d=pd.read_csv(HERE/'window_vectors.csv');p=pd.read_csv(HERE/'all_profiles.csv')
c=pd.read_csv(HERE/'descriptive_inference.csv').rename(columns={'selected_blocks':'selected_clusters'})
c.to_csv(HERE/'descriptive_inference.csv',index=False)
a=np.load(ROOT/'data/analysis/gross-edge-20260929/signals/all116_zero_fee_vectors.npz')
idx=np.flatnonzero(a['candidate']=='003_long_none_confirm0_hold240').item()
old=d.set_index('window_id').loc[a['window_id']]
errors=[np.max(np.abs(old.gross_240_pct.to_numpy()-a['gross_pct'][idx]))]
t=pd.read_csv(ROOT/'data/sim/gross-edge-500-20260929T204545Z/strategy_trades.csv')
t=t[t.rule.eq('L048')].set_index('window_id')
f=d[d.cohort.eq('fresh500')].set_index('window_id').loc[t.index]
assert np.array_equal(f.selected_L048.to_numpy(),t.selected.to_numpy())
for h in [15,30,60,105,240]:errors.append(np.max(np.abs(f[f'gross_{h}_pct'].to_numpy()-t[f'scheduled_direction_move_{h}m_pct'].to_numpy())))
assert max(errors)<1e-10
audit=json.loads((HERE/'audit.json').read_text());audit.update(per_window_reconciliation_comparisons=2930,per_window_reconciliation_max_abs_error_pct=float(max(errors)),all500_L048_selection_masks_match=True)
for path in [Path(__file__),HERE/'run.py',ROOT/'data/analysis/gross-edge-20260929/signals/all116_zero_fee_vectors.npz',ROOT/'data/sim/gross-edge-500-20260929T204545Z/strategy_trades.csv']:
    audit['source_sha256'][str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
(HERE/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,3,figsize=(14,5.1),sharex=True)
colors={'L048_AI_short':'#1766A5','macro_no_AI':'#6C757D','macro_AI_long_complement':'#D47C24'}
labels={'L048_AI_short':'L048: AI SHORT → LONG','macro_no_AI':'Macro gate, no AI','macro_AI_long_complement':'Macro gate, AI LONG'}
tail=pd.read_csv(HERE/'fixed_240_tail_sensitivity.csv')
for ax,scope,title in zip(axes,['old150','new280','fresh500'],['Original 150 SOL windows · 22 trades','Next 280 SOL windows · 65 trades','Fresh 500 across four assets · 101 trades']):
    for group in colors:
        z=p[p.scope.eq(scope)&p.group.eq(group)].sort_values('horizon')
        ax.plot(z.horizon,z.mean_gross_pct,'o-',color=colors[group],label=labels[group],lw=2)
    z=tail[tail.scope.eq(scope)].sort_values('horizon')
    ax.plot(z.horizon,z.ex_same_top3_at240_mean_pct,'--',color='#BD4161',label='L048 minus top three at 240m',lw=1.8)
    ax.axhline(0,color='#31363A',lw=.8);ax.set_title(title,fontsize=10);ax.set_xlabel('Elapsed minutes after entry')
    ax.set_xticks([15,60,105,240]);ax.grid(alpha=.17)
axes[0].set_ylabel('Mean gross return per trade (%)')
handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.5,.055))
fig.suptitle('Exploratory horizon profile: early reversal does not transfer consistently',fontsize=14)
fig.text(.5,.012,'Zero fees. Equal notional. The same 240m winners are removed at every horizon as a hindsight sensitivity.',ha='center',fontsize=9,color='#52585E')
fig.tight_layout(rect=[0,.20,1,.95]);fig.savefig(HERE/'horizon_profile.png',dpi=170,bbox_inches='tight');plt.close(fig)

fs=d[d.cohort.eq('fresh500')&d.selected_L048].copy()
blocks=fs.groupby(['calendar_block','entry_time']).gross_240_pct.agg(['sum','count']).sort_values('sum',ascending=False)
blocks.to_csv(HERE/'fresh500_selected_block_returns.csv')
print('PASS: 2,930 per-window return comparisons; maximum error',max(errors))
print('Top three 240m winners share of summed trade returns:',fs.gross_240_pct.nlargest(3).sum()/fs.gross_240_pct.sum())
print('Top three 240m blocks share:',blocks['sum'].iloc[:3].sum()/fs.gross_240_pct.sum())
