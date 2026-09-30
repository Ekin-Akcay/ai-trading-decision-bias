"""Independent arithmetic checks and visualization; no additional policies."""
from pathlib import Path
import hashlib,json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
a=np.load(HERE/'relative_value_family.npz');s=pd.read_csv(HERE/'all_policies.csv');folds=pd.read_csv(HERE/'chronological_folds.csv')
names=a['policy'].tolist();returns=a['asset_return_pct'];weights=a['weights'];gross=a['gross_pct'];score=a['scores'];active=a['selected']
assert weights.shape==(12,125,4) and gross.shape==(12,125)
checks=0
for pi,name in enumerate(names):
    si=pi//2;sign=1 if pi%2==0 else -1
    scalar=[]
    for b in range(125):
        x=list(score[si,b]);minimum=min(x);maximum=max(x)
        if minimum==maximum:w=np.zeros(4)
        else:
            low=[i for i,v in enumerate(x) if v==minimum];high=[i for i,v in enumerate(x) if v==maximum]
            w=np.zeros(4)
            for i in low:w[i]=sign*.5/len(low)
            for i in high:w[i]=-sign*.5/len(high)
        assert np.allclose(w,weights[pi,b],rtol=0,atol=1e-15)
        scalar.append(sum(w[j]*returns[b,j] for j in range(4)));checks+=5
    assert np.allclose(scalar,gross[pi],rtol=0,atol=1e-12)
    row=s[s.policy.eq(name)].iloc[0]
    assert abs(row.mean_per_opportunity_pct-np.mean(scalar))<1e-12
    assert abs(row.mean_per_active_pct-gross[pi,active[pi]].mean())<1e-12
    for f in range(1,6):
        z=folds[folds.policy.eq(name)&folds.fold.eq(f)].iloc[0]
        assert abs(z.mean_per_opportunity_pct-gross[pi,a['fold']==f].mean())<1e-12
        checks+=1

# These are algebraic mirrors of already-declared reverse-versus-price contrasts.
# No additional strategy, return vector or bootstrap sample is introduced.
c=pd.read_csv(HERE/'paired_price_control_differences.csv');mirror=[]
for row in c.to_dict('records'):
    r=dict(row);r['AI_policy']=row['AI_policy'].replace('__reverse','__follow')
    r['control_policy']=row['control_policy'].replace('__reverse','__MIRROR').replace('__follow','__reverse').replace('__MIRROR','__follow')
    for k in ['difference_per_opportunity_pct','AI_active_only_conditional_difference_pct','matched_skip_difference_per_opportunity_pct']:r[k]=-row[k]
    for base in ['block_ci95','quarter_ci95','matched_skip_block_ci95','matched_skip_quarter_ci95']:
        r[base+'_low']=-row[base+'_high'];r[base+'_high']=-row[base+'_low']
    r['exact_sign_mirror_not_new_test']=True;mirror.append(r)
pd.DataFrame(mirror).to_csv(HERE/'following_mirrored_price_control_differences.csv',index=False)

plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
fig,(ax,heat)=plt.subplots(1,2,figsize=(13.5,6.4),gridspec_kw={'width_ratios':[1.1,1]})
y=np.arange(12);ordered=s.set_index('policy').loc[names]
labels=[x.replace('AI_stop_ATR_conviction','AI stop / ATR conviction').replace('AI_confidence','AI confidence').replace('AI_direction','AI direction').replace('price_momentum','Price momentum').replace('price_MA20_ATR','Price MA20 / ATR').replace('price_ATR','Price ATR').replace('__',' · ') for x in names]
colors=['#BB4B4E' if i<6 and i%2==0 else '#397EA6' if i<6 else '#7E878D' for i in range(12)]
for i,(name,row) in enumerate(ordered.iterrows()):
    mean=row.mean_per_opportunity_pct;lo=row.quarter_ci95_low;hi=row.quarter_ci95_high
    ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',color=colors[i],capsize=3,lw=1.4)
ax.axvline(0,color='#555',lw=.9);ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlabel('Gross % per sampled opportunity');ax.set_title('All 12 policies · whole-quarter 95% intervals');ax.grid(axis='x',alpha=.18)
m=np.array([[folds.loc[folds.policy.eq(name)&folds.fold.eq(f),'mean_per_opportunity_pct'].item() for f in range(1,6)] for name in names])
vmax=max(.4,np.max(np.abs(m)));im=heat.imshow(m,aspect='auto',cmap='RdBu',vmin=-vmax,vmax=vmax)
for i in range(12):
    for j in range(5):heat.text(j,i,f'{m[i,j]:+.2f}',ha='center',va='center',fontsize=9,color='white' if abs(m[i,j])>.6*vmax else '#20242A')
heat.set_xticks(np.arange(5),[f'Fold {f}' for f in range(1,6)]);heat.set_yticks(y,[]);heat.set_title('Chronological transfer · 25 blocks per fold');heat.set_xlabel('Fixed policies; no fitting or sign changes between folds')
fig.suptitle('Relative-value discovery: reversed AI rankings do not show a stable edge',fontsize=14)
fig.text(.5,.022,'125 simultaneous timestamps · four assets per timestamp · zero costs · unit gross notional · known outcomes, not fresh validation',ha='center',fontsize=9,color='#535B60')
fig.tight_layout(rect=[0,.06,1,.94]);fig.savefig(HERE/'relative_value_profile.png',dpi=170,bbox_inches='tight');plt.close(fig)

audit=json.loads((HERE/'audit.json').read_text());audit.update(independent_rank_weight_and_fold_checks=checks,exact_mirror_control_contrasts=18)
for p in [HERE/'run.py',HERE/'finish.py']:audit['source_sha256'][str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in audit['source_sha256'].items())
(HERE/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('PASS: independent rank weights, baskets and all chronological folds;',checks,'checks')
