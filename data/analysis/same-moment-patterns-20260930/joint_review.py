"""Common-calendar descriptive uncertainty for every current policy and control."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
w=pd.read_csv(ROOT/'data/analysis/new-angles-20260930/target_exhaustion/windows.csv')
names=[];families=[];roles=[];ys=[];ns=[]
def add(family,labels,y,n,role):
    assert y.shape==n.shape==(1020,len(labels)) and np.isfinite(y).all()
    for j,label in enumerate(labels):
        names.append(str(label));families.append(family);roles.append(str(role[j]));ys.append(y[:,j]);ns.append(n[:,j])
v=np.load(P/'volume_reaction/vectors.npz');s=json.loads((P/'volume_reaction/summary.json').read_text())
add('volume_reaction',v['policies'],v['returns'],v['selected'],[r['role'] for r in s])
d=np.load(P/'volume_reaction/diagnostics_vectors.npz')
add('volume_post_score',d['policies'],d['returns'],d['selected'],['post_score_diagnostic']*len(d['policies']))
m=np.load(P/'market_reaction/paired_vectors.npz');assert np.array_equal(m['window_id'],w.window_id.to_numpy(str))
add('market_reaction',m['policy'],m['opportunity_gross_pct'].T,m['selected'].T,m['kind'])
e=np.load(P/'managed_exits/policy_vectors.npz');assert np.array_equal(e['window_id'],w.window_id.to_numpy(str))
add('managed_exits',e['policy'],e['gross_pct'].T,np.ones_like(e['gross_pct'].T),['candidate']*3+['control']*2)
y=np.array(ys).T;n=np.array(ns).T.astype(float)
codes,labels=pd.factorize(w.quarter,sort=True);k=len(labels)
a=np.zeros((k,len(names)));b=np.zeros_like(a);np.add.at(a,codes,y);np.add.at(b,codes,n)
weights=np.random.default_rng(2026093047).multinomial(k,np.full(k,1/k),size=20000)
numer=weights@a;den=weights@b;bs=np.divide(numer,den,out=np.full_like(numer,np.nan),where=den>0)
uniques={}
for j in range(len(names)):
    key=hashlib.sha256(np.column_stack([y[:,j],n[:,j]]).tobytes()).hexdigest();uniques.setdefault(key,[]).append(j)
alpha=.025/len(names);rows=[]
for j,name in enumerate(names):
    mask=n[:,j]>0;mean=y[:,j].sum()/n[:,j].sum()
    ci=np.nanquantile(bs[:,j],[.025,.975]);familyci=np.nanquantile(bs[:,j],[alpha,1-alpha])
    rows.append(dict(family=families[j],policy=name,role=roles[j],trades=int(mask.sum()),entry_time_blocks=w.loc[mask,'entry_time'].nunique(),gross_mean_pct=mean,quarter95_low_pct=ci[0],quarter95_high_pct=ci[1],whole_search_simultaneous_low_pct=familyci[0],whole_search_simultaneous_high_pct=familyci[1],positive_whole_search_interval=bool(familyci[0]>0),empty_resamples=int(np.isnan(bs[:,j]).sum())))
pd.DataFrame(rows).to_csv(P/'joint_results.csv',index=False)
np.savez_compressed(P/'joint_vectors.npz',policy=np.array(names),family=np.array(families),returns=y,selected=n.astype(bool),quarter_means=bs,quarter_weights=weights,quarter_labels=np.asarray(labels,dtype=str),window_id=w.window_id.to_numpy(str))
audit=dict(definitions=len(names),unique_payoff_and_selection_vectors=len(uniques),families=pd.Series(families).value_counts().to_dict(),bootstrap_replicates=20000,seed=2026093047,quarters=k,scope='All current policy/control vectors plus seven explicitly post-score diagnostics; duplicate retained conservatively.',past_search_history_not_erased=True,independent_confirmation=False,positive_simultaneous_intervals=[r['policy'] for r in rows if r['positive_whole_search_interval']],duplicates=[[names[j] for j in v] for v in uniques.values() if len(v)>1])
(P/'joint_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit,indent=2));print(pd.DataFrame(rows).sort_values('gross_mean_pct',ascending=False).head(8).to_string(index=False))
