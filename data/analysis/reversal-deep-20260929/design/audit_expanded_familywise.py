"""Audit 104 new exploratory vectors and the complete expanded max-T family.

Reuses the independently audited first-family maxima only after checking that
the archived matrix and first 11,191 columns are identical. All new bootstrap
scores are independently recomputed with exactly the original shared draws.
"""
from pathlib import Path
from datetime import datetime,timezone
import json
import numpy as np
import pandas as pd
H=Path(__file__).resolve().parent;S=H.parent;R=S/'search_correction'
old=np.load(R/'initial11191/family_matrix_and_null.npz')
new=np.load(R/'family_matrix_and_null.npz')
ownold=np.load(H/'familywise_audit_calculations.npz')
summary=json.loads((R/'summary.json').read_text())
rows=pd.read_csv(R/'all_family_results.csv').set_index('policy')
ai_width_controls=rows[rows.index.str.contains('AI_width_control_not_AI_free',regex=False)]
assert len(ai_width_controls)==16 and ai_width_controls.contains_AI.eq(True).all()
X=new['net_opportunity'];names=new['policies'];N,M=X.shape
assert (N,M)==(280,11295)
assert np.array_equal(X[:,:11191],old['net_opportunity'])
assert np.array_equal(names[:11191],old['policies'])
assert np.array_equal(new['quarter_codes'],old['quarter_codes'])
assert np.array_equal(names[:11191],ownold['names'])
assert np.allclose(old['max_t_null'],ownold['maxnull'],rtol=0,atol=1e-11)
rw=pd.read_csv(S/'risk/fresh_grid/windows.csv');wids=rw.window_id.to_numpy()
ai_long=rw.ai_action.to_numpy()=='long'

hedge=H.parent/'risk/hedge_study'
hw=pd.read_csv(hedge/'windows.csv');hw=hw[hw.dataset=='fresh280'].set_index('window_id').loc[wids]
hv=np.load(hedge/'hedge_family_all_notional_conventions.npz')
hp=np.load(hedge/'fresh280_payoffs.npz')
assert np.array_equal(hv['window_id'],wids) and np.array_equal(hp['window_ids'],wids)
assert len(hv['policy'])==56
assert np.isfinite(hw.beta_ols_clip).all() and hw.beta_ols_clip.between(0,3).all()
hedge_source={}
for label in hv['policy']:
    kind,signal,weight,units=str(label).split('/')
    key=weight.split('=')[1]
    beta={'zero':np.zeros(N),'half':np.full(N,.5),'one':np.ones(N),'ols':hw.beta_ols_clip.to_numpy()}[key]
    confirmed=signal.startswith('confirmed')
    sol=hw['SOL_return15_pct' if confirmed else 'SOL_return0_pct'].to_numpy()
    btc=hw['BTC_return15_pct' if confirmed else 'BTC_return0_pct'].to_numpy()
    direction=np.where(ai_long,-1,1) if signal=='reverse_all' else (-1 if signal in ['reverse_long_to_short','always_short'] else 1)
    if signal=='reverse_long_to_short':mask=ai_long
    elif signal=='reverse_short_to_long':mask=~ai_long
    elif signal=='confirmed_reverse_short_to_long':mask=(~ai_long)&hw.confirmation.to_numpy()
    elif signal=='confirmed_long_no_AI':mask=hw.confirmation.to_numpy()
    else:mask=np.ones(N,bool)
    gross=direction*(sol-beta*btc)
    net=gross-.2*(1+beta)
    if units=='total_gross_notional':net=net/(1+beta)
    else:assert units=='SOL_notional'
    hedge_source[str(label)]=(net,mask)

stop=S/'signals/stopout_fade'
sf=np.load(stop/'family_vectors.npz')
ledger=pd.read_csv(stop/'all_window_paths.csv.gz')
ledger=ledger[ledger.cohort=='new280']
assert np.array_equal(sf['window_id'],wids) and len(sf['policylabels'])==48
stop_source={}
for label in sf['policylabels']:
    policy,group=str(label).split('/')
    width='ATR_width' if group=='ATR_width_price_only_control' else 'AI_width'
    frame=ledger[(ledger.policy==policy)&(ledger.width==width)].set_index('window_id').loc[wids]
    trigger=frame.original_first_outcome.str.startswith('sl').to_numpy()
    if group=='AI_selected_stopout_fade':
        mask=trigger&(frame.ai_action.to_numpy()==frame.strategy_side.to_numpy())
    else:mask=trigger
    signs=np.where(frame.strategy_side.to_numpy()=='long',1,-1)
    net=100*signs*(frame.exit_price.to_numpy()/frame.entry_price.to_numpy()-1)-.2
    assert np.allclose(net[trigger],frame.net20_pct.to_numpy()[trigger],rtol=0,atol=1e-11)
    assert not (frame.original_first_outcome=='sl_ambiguous').any()
    stop_source[str(label)]=(net,mask)

new_counts={'hedges':0,'stopout_fade':0};executed=[]
for j in range(11191,M):
    family,label=str(names[j]).split(':',1)
    net,mask=(hedge_source if family=='hedges' else stop_source)[label]
    expected=np.zeros(N);expected[mask]=net[mask]
    assert np.allclose(expected,X[:,j],rtol=0,atol=1e-11),str(names[j])
    assert int(mask.sum())==int(rows.loc[names[j],'executed'])
    new_counts[family]+=1;executed.append(int(mask.sum()))
assert new_counts=={'hedges':56,'stopout_fade':48}

# Existing source normalizations also reconstruct the aggregate hedge export.
for j,label in enumerate(hv['policy']):
    net,mask=hedge_source[str(label)]
    assert np.allclose(hv['net_pct'][j],net,rtol=0,atol=1e-11)
    assert np.array_equal(hv['selected'][j],mask)
for j,label in enumerate(sf['policylabels']):
    net,mask=stop_source[str(label)]
    assert np.allclose(sf['net_pct'][j][mask],net[mask],rtol=0,atol=1e-11)
    assert np.array_equal(sf['selected'][j],mask)

qc=new['quarter_codes'];G=int(qc.max()+1);assert G==24
ng=np.bincount(qc,minlength=G)
Z=X[:,11191:];mu=Z.mean(axis=0)
U=np.vstack([(Z[qc==g]-mu).sum(axis=0) for g in range(G)])
se=np.linalg.norm(U,axis=0)*np.sqrt(G/(G-1))/N
assert (se>1e-12).all()
new_t=mu/se
assert np.allclose(new_t,rows.loc[names[11191:],'t'],rtol=0,atol=1e-11)
assert np.allclose(mu,rows.loc[names[11191:],'mean_net_per_opportunity_pct'],rtol=0,atol=1e-11)
assert np.allclose(mu*N/np.asarray(executed),rows.loc[names[11191:],'mean_net_per_trade_pct'],rtol=0,atol=1e-11)
B=20000;rng=np.random.default_rng(2026092940);draws=rng.integers(G,size=(B,G))
newmax=np.empty(B);standardized=U/se[None,:]
for start in range(0,B,256):
    ids=draws[start:start+256];v=np.zeros((len(ids),104))
    for j in range(G):v+=standardized[ids[:,j]]
    v/=ng[ids].sum(axis=1)[:,None]
    newmax[start:start+len(ids)]=v.max(axis=1)
maxnull=np.maximum(ownold['maxnull'],newmax)
assert np.allclose(maxnull,new['max_t_null'],rtol=0,atol=1e-11)
assert np.all(new['max_t_null']>=old['max_t_null']-1e-11)
t=np.r_[ownold['t'],new_t]
sortnull=np.sort(maxnull)
adjusted=(1+B-np.searchsorted(sortnull,t-1e-14,side='left'))/(B+1)
assert np.allclose(adjusted,rows.loc[names,'p_maxT_familywise'],rtol=0,atol=1e-12)
crit=float(np.quantile(maxnull,.95))
assert np.isclose(crit,summary['max_t_95critical'],rtol=0,atol=1e-11)
assert int((adjusted<.05).sum())==0
unique=len(np.unique(X.T,axis=0));assert unique==9336
top=int(np.argmax(t));assert str(names[top])==summary['top_policy']['policy']
assert np.isclose(adjusted[top],summary['global_maxT_p'],rtol=0,atol=1e-12)
result={'passed':True,'audited_at':datetime.now(timezone.utc).isoformat(),
        'definitions':M,'unique_return_vectors':unique,'new_vectors':new_counts,
        'old11191_columns_bit_identical':True,
        'all104_new_columns_independently_reconstructed':True,
        'hedge_leg_costs_and_both_notional_conventions_verified':True,
        'stopout_first_exit_masks_and_new_trade_costs_verified':True,
        'ambiguous_original_triggers':0,
        'windows':N,'quarters':G,'bootstrap_replicates':B,'seed':2026092940,
        'all20000_expanded_bootstrap_maxima_match':True,
        'expanded_null_not_smaller_than_original':True,
        'every_familywise_p_value_matches':True,
        'max_t_95critical':crit,'largest_observed_t':float(t[top]),
        'global_maxT_p':float(adjusted[top]),'passing_policies':0,
        'top_policy':str(names[top]),'top_n':int(rows.loc[names[top],'executed']),
        'top_mean_net_pct':float(rows.loc[names[top],'mean_net_per_trade_pct']),
        'conclusion':'No family-corrected profitable strategy demonstrated; added mechanisms do not change the conclusion.',
        'AI_width_control_metadata_corrected':True,
        'metadata_note':'All 16 AI-width stopout controls are correctly marked contains_AI=true.'}
(H/'expanded_familywise_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
