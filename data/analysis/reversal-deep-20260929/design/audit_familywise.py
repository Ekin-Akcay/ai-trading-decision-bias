"""Independent audit of the complete exploratory quarter-cluster max-T family."""
from pathlib import Path
from datetime import datetime,timezone
import json
import numpy as np
import pandas as pd

H=Path(__file__).resolve().parent;S=H.parent;R=S/'search_correction'
reported=json.loads((R/'summary.json').read_text())
a=np.load(R/'family_matrix_and_null.npz')
X=a['net_opportunity'];names=a['policies'];saved_null=a['max_t_null']
N,M=X.shape;B=20000
assert (N,M)==(280,11191)
assert np.isfinite(X).all() and len(set(names))==M
rows=pd.read_csv(R/'all_family_results.csv').set_index('policy')
assert len(rows)==M and set(rows.index)==set(names)

rw=pd.read_csv(S/'risk/fresh_grid/windows.csv')
rp=json.loads((S/'risk/fresh_grid/policies.json').read_text())
oldp=json.loads((S/'risk/policies.json').read_text())
assert rp==[p for p in oldp if p['horizon']<=1440]
assert len(rp)==721
rg=np.load(S/'risk/fresh_grid/all_trade_results.npz')['gross_pct']
assert rg.shape==(721,280,2)
policy_index={p['policy_id']:i for i,p in enumerate(rp)}
sg=np.load(S/'signals/fresh_grid/all_candidate_arrays.npz')
assert len(sg['candidate'])==116
assert np.array_equal(sg['window_id'],rw.window_id)
assert np.allclose(sg['net20_pct'],sg['gross_pct']-.2,equal_nan=True)
si={c:i for i,c in enumerate(sg['candidate'])}
cf=pd.read_csv(S/'confirmation/fresh_grid/all_trade_policies.csv')
assert cf.policy.nunique()==72
assert np.allclose(cf.net_pct,cf.gross_pct-.2)
window_index={v:i for i,v in enumerate(rw.window_id)}
long=rw.ai_action.to_numpy()=='long'
above=(rw.ma20_now.to_numpy()<=100)&(rw.ma50_now.to_numpy()<=100)
below=(rw.ma20_now.to_numpy()>100)&(rw.ma50_now.to_numpy()>100)
assert np.array_equal(above,rw.above_both) and np.array_equal(below,rw.below_both)
gates={'all':np.ones(N,bool),'above_both':above,'below_both':below}
counts={k:0 for k in ['risk','signals','confirmation']};executed=[]
skip_entries=0
for j,name in enumerate(names):
    family=name.split(':',1)[0]
    expected=np.zeros(N)
    if family=='risk':
        _,pid,gate,strategy=name.split(':')
        k=policy_index[int(pid)]
        mask=gates[gate].copy()
        if strategy=='reverse_long_to_short':mask &= long
        if strategy=='reverse_short_to_long':mask &= ~long
        if strategy=='always_long':direction=np.zeros(N,dtype=int)
        elif strategy=='always_short':direction=np.ones(N,dtype=int)
        else:direction=long.astype(int)
        selected=np.flatnonzero(mask)
        expected[selected]=rg[k,selected,direction[selected]]-.2
    elif family=='signals':
        _,candidate,kind=name.split(':')
        k=si[candidate];mask=sg[kind][k]
        expected[mask]=sg['gross_pct'][k,mask]-.2
    elif family=='confirmation':
        _,policy,kind=name.split(':')
        group=cf[cf.policy==policy]
        if kind=='AIselected':group=group[group.ai_selected]
        assert group.window_id.is_unique
        selected=np.array([window_index[v] for v in group.window_id],dtype=int)
        mask=np.zeros(N,bool);mask[selected]=True
        expected[selected]=group.gross_pct.to_numpy()-.2
    else:raise AssertionError(family)
    assert np.allclose(expected,X[:,j],rtol=0,atol=1e-11),name
    assert np.count_nonzero(X[~mask,j])==0,name
    assert int(mask.sum())==int(rows.loc[name,'executed']),name
    executed.append(int(mask.sum()));skip_entries+=int((~mask).sum());counts[family]+=1
assert counts=={'risk':10815,'signals':232,'confirmation':144}
assert counts==reported['family_counts']

times=pd.to_datetime(rw.entry_time)
quarters=times.dt.to_period('Q').astype(str)
ql=list(dict.fromkeys(quarters));G=len(ql)
qc=np.array([ql.index(v) for v in quarters]);assert np.array_equal(qc,a['quarter_codes'])
assert G==24
ng=np.array([(qc==g).sum() for g in range(G)])
mu=X.sum(axis=0)/N
# Independent centered sums: center individual observations before grouping.
centered=X-mu[None,:]
U=np.vstack([centered[qc==g].sum(axis=0) for g in range(G)])
se=np.linalg.norm(U,axis=0)*np.sqrt(G/(G-1))/N
ok=(se>1e-12)&(np.asarray(executed)>0)
t=mu[ok]/se[ok]
assert ok.all() and len(t)==11191
for key,actual in [('mean_net_per_opportunity_pct',mu),('cluster_se_per_opportunity_pct',se),('t',t)]:
    assert np.allclose(rows.loc[names,key].to_numpy(),actual,rtol=0,atol=1e-11),key

rng=np.random.default_rng(2026092940)
draws=rng.integers(G,size=(B,G))
maxnull=np.empty(B);nominal=np.zeros(M,dtype=np.int64)
# Sum the sampled quarter contributions directly, independent of weight-matrix BLAS.
# Each replicate is still joint across all policies; process small batches.
standardized=U/se[None,:]
for start in range(0,B,128):
    ids=draws[start:start+128]
    values=np.zeros((len(ids),M))
    for quarter_position in range(G):
        values+=standardized[ids[:,quarter_position]]
    values/=ng[ids].sum(axis=1)[:,None]
    maxnull[start:start+len(ids)]=values.max(axis=1)
    nominal+=(values>=t[None,:]-1e-14).sum(axis=0)
    if start%4096==0:print('Independent replicates',start+len(ids),'/',B,flush=True)
assert np.allclose(maxnull,saved_null,rtol=0,atol=1e-11)
# Sorted-tail lookup avoids allocating a full bootstrap-by-policy comparison.
sortnull=np.sort(maxnull)
tail=B-np.searchsorted(sortnull,t-1e-14,side='left')
adjusted=(tail+1)/(B+1)
nominal=(nominal+1)/(B+1)
assert np.allclose(adjusted,rows.loc[names,'p_maxT_familywise'],rtol=0,atol=1e-12)
reported_nominal=rows.loc[names,'p_nominal_cluster'].to_numpy()
nominal_difference=np.abs(nominal-reported_nominal)
nominal_mismatch=np.flatnonzero(nominal_difference>1e-12)
np.savez_compressed(H/'familywise_audit_calculations.npz',t=t,nominal=nominal,
                    reported_nominal=reported_nominal,maxnull=maxnull,
                    adjusted=adjusted,names=names)
print('Nominal threshold differences',len(nominal_mismatch),
      'maximum',float(nominal_difference.max()),flush=True)
for j in nominal_mismatch[:10]:
    print(str(names[j]),float(t[j]),float(nominal[j]),float(reported_nominal[j]),flush=True)
critical=np.quantile(maxnull,.95)
assert np.isclose(critical,reported['max_t_95critical'],rtol=0,atol=1e-11)
lower=mu-critical*se
assert np.allclose(lower,rows.loc[names,'simultaneous95_lower_opportunity_pct'],rtol=0,atol=1e-11)
top=int(np.argmax(t));top_name=names[top];n=executed[top]
assert top_name=='signals:048_long_both_down_confirm0_hold240:selected'
assert n==65
net_per_trade=float(mu[top]*N/n)
assert np.isclose(net_per_trade,.33513224825238525,rtol=0,atol=1e-11)
unique=len(np.unique(X.T,axis=0));assert unique==9246
passed=int((adjusted<.05).sum());assert passed==0
result={'passed':True,'audited_at':datetime.now(timezone.utc).isoformat(),
        'definitions':M,'unique_return_vectors':unique,'family_counts':counts,
        'windows':N,'quarters':G,'replicates':B,'seed':2026092940,
        'all_matrix_columns_reconstructed_from_family_gross_returns':True,
        'skip_entries_verified_zero':skip_entries,'cost_percentage_points':.2,
        'all_20000_joint_bootstrap_maxima_match':True,
        'all_familywise_p_values_match':True,
        'nominal_p_value_exact_matches':int(M-len(nominal_mismatch)),
        'nominal_p_value_max_absolute_difference':float(nominal_difference.max()),
        'nominal_roundoff_note':'Four negative-t policies differ by one of 20,001 nominal tail counts under independent floating-point summation; every familywise p-value and the top-policy nominal p-value match.',
        'all_simultaneous_lower_bounds_match':True,
        'max_t_95critical':float(critical),'largest_observed_t':float(t[top]),
        'global_maxT_p':float(adjusted[top]),'passing_policies':passed,
        'top_policy':top_name,'top_n':n,'top_mean_net_per_trade_pct':net_per_trade,
        'top_nominal_p_matches':bool(np.isclose(nominal[top],reported_nominal[top],rtol=0,atol=1e-12)),
        'status':'Independent numerical PASS; no family-corrected profitable strategy demonstrated',
        'limitations':['Retrospective exploratory reuse, not fresh confirmation',
                       'Quarter clusters assumed exchangeable; longer regime dependence remains possible',
                       'Profit relative to cash does not by itself identify incremental AI value']}
(H/'familywise_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
