"""BTC reaction at existing Terra moments: fixed four-rule discovery, zero calls."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
SOURCE=ROOT/'data/analysis/new-angles-20260930/target_exhaustion'
B=20_000;SEED=2026093014
HASHES={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source(p):
    p=Path(p);HASHES[str(p.relative_to(ROOT))]=sha(p);return p
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,np.integer):return int(x)
    if isinstance(x,np.bool_):return bool(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x
def save(name,x):(HERE/name).write_text(json.dumps(clean(x),indent=2,allow_nan=False)+'\n')
source(HERE/'PLAN.md');source(HERE/'run.py')
w=pd.read_csv(source(SOURCE/'windows.csv'));w.entry_time=pd.to_datetime(w.entry_time)
z=np.load(source(SOURCE/'paths.npz'));path=z['paths'];N=len(w)
assert N==1020 and w.window_id.nunique()==N and w.window_id.tolist()==z['window_id'].tolist()
assert path.shape==(N,361,4) and np.isfinite(path[:,:136]).all() and (path[:,:136]>0).all()
np.testing.assert_allclose(path[:,0,3],w.price_real,rtol=0,atol=1e-8)
w['analysis_cohort']=w.cohort.replace({'original100':'old150','next50':'old150'})
w['year']=w.entry_time.dt.year;w['quarter']=w.entry_time.dt.to_period('Q').astype(str)
w['first_asset_open']=path[:,1,0];w['asset_close_15']=path[:,15,3]
w['asset_15m_pct']=(path[:,15,3]/path[:,1,0]-1)*100
w['old_asset_confirmation_pct']=(path[:,15,3]/path[:,0,3]-1)*100
w['trade_entry_time']=w.entry_time+pd.Timedelta(minutes=15)
w['trade_exit_close_time']=w.entry_time+pd.Timedelta(minutes=135)
w['trade_entry_price']=path[:,16,0];w['trade_exit_price']=path[:,135,3]
w['long_gross_pct']=(path[:,135,3]/path[:,16,0]-1)*100
w['btc_first_open']=np.nan;w['btc_close_15']=np.nan;w['btc_15m_pct']=np.nan;w['btc_observation_complete']=False

# BTC supplies context, never a substitute traded asset.
btcfile=source(ROOT/'data/raw/intraday/BTC-USD_1m.csv.gz')
btc=pd.read_csv(btcfile,usecols=['ts','open','close']);btc.ts=pd.to_datetime(btc.ts);btc=btc.set_index('ts').sort_index()
assert btc.index.is_unique
for ts,g in w.groupby('entry_time',sort=True):
    grid=pd.date_range(ts,periods=15,freq='min');positions=btc.index.get_indexer(grid)
    if (positions<0).any():continue
    values=btc.iloc[positions][['open','close']].to_numpy()
    if not np.isfinite(values).all() or not (values>0).all():continue
    opening=float(values[0,0]);close=float(values[-1,1]);ret=(close/opening-1)*100
    w.loc[g.index,['btc_first_open','btc_close_15','btc_15m_pct']]=[opening,close,ret]
    w.loc[g.index,'btc_observation_complete']=True

# Independent timeframe reconciliation of cached observed/entry/exit prices.
native_price_checks=0
for asset,g in w.groupby('asset'):
    raw=pd.read_csv(source(ROOT/f'data/raw/intraday/{asset}_15m.csv.gz'),index_col=0,parse_dates=True,usecols=[0,1,4]).sort_index()
    assert raw.index.is_unique
    q=raw.index.get_indexer(g.entry_time);assert (q>=0).all()
    assert (raw.index[q+1]==pd.DatetimeIndex(g.entry_time)+pd.Timedelta(minutes=15)).all()
    assert (raw.index[q+8]+pd.Timedelta(minutes=15)==pd.DatetimeIndex(g.entry_time)+pd.Timedelta(minutes=135)).all()
    for truth,col in [(raw.open.to_numpy()[q],'first_asset_open'),(raw.close.to_numpy()[q],'asset_close_15'),(raw.open.to_numpy()[q+1],'trade_entry_price'),(raw.close.to_numpy()[q+8],'trade_exit_price')]:
        np.testing.assert_allclose(truth,g[col],atol=1e-8,rtol=0);native_price_checks+=len(g)
    if asset=='BTC-USD':
        nonmissing=g.btc_observation_complete.to_numpy()
        np.testing.assert_allclose(raw.open.to_numpy()[q][nonmissing],g.btc_first_open.to_numpy()[nonmissing],atol=1e-8,rtol=0)
        np.testing.assert_allclose(raw.close.to_numpy()[q][nonmissing],g.btc_close_15.to_numpy()[nonmissing],atol=1e-8,rtol=0)

eligible=w.asset.ne('BTC-USD').to_numpy()&w.btc_observation_complete.to_numpy(bool)
w['eligible']=eligible
w['eligibility_status']=np.where(w.asset.eq('BTC-USD'),'BTC_self_excluded',np.where(w.btc_observation_complete,'eligible','BTC_observation_missing'))
times=sorted(w.entry_time[eligible].unique());mid=len(times)//2
w['common_half']=np.where(w.entry_time.isin(times[:mid]),1,2)
A=w.asset_15m_pct.to_numpy();C=w.btc_15m_pct.to_numpy();r=w.long_gross_pct.to_numpy()
AIshort=w.action.eq('short').to_numpy();AIlong=w.action.eq('long').to_numpy()
spec=[('L1_BTC_up_asset_not_up',1,(C>0)&(A<=0),AIshort),('L2_BTC_up_asset_lagging_up',1,(C>0)&(A>0)&(A<C),AIshort),('S1_BTC_down_asset_not_down',-1,(C<0)&(A>=0),AIlong),('S2_BTC_down_asset_lagging_down',-1,(C<0)&(A<0)&(A>C),AIlong)]
policies=[]
for name,side,gate,AI in spec:policies.append({'name':name,'kind':'AI_candidate','side':side,'selected':eligible&gate&AI,'price_gate':eligible&gate,'AI_gate':AI})
for name,side,gate,AI in spec:policies.append({'name':name+'_price_only','kind':'direct_price_control','side':side,'selected':eligible&gate,'price_gate':eligible&gate,'AI_gate':np.ones(N,bool)})
for label,side,AI in [('long',1,AIshort),('short',-1,AIlong)]:
    confirm=side*w.old_asset_confirmation_pct.to_numpy()>0
    masks={'AI_only':AI,'legacy_confirm_AI':AI&confirm,'legacy_confirm_price':confirm,'BTC_direction_AI':AI&(side*C>0),'unconditional':np.ones(N,bool)}
    for suffix,mask in masks.items():policies.append({'name':'C_'+label+'_'+suffix,'kind':'comparator','side':side,'selected':eligible&mask,'price_gate':eligible,'AI_gate':AI})
assert len(policies)==18
names=[p['name'] for p in policies];lookup={n:i for i,n in enumerate(names)}
mask=np.array([p['selected'] for p in policies]);side=np.array([p['side'] for p in policies]);gross=side[:,None]*r
payoff=np.where(mask,gross,0.)
quarters=sorted(w.quarter.unique());qn=len(quarters);q=pd.Categorical(w.quarter,categories=quarters).codes.astype(np.int64)
draws=np.random.default_rng(SEED).multinomial(qn,np.full(qn,1/qn),size=B).astype(np.int16)

def ci(samples):
    samples=samples[np.isfinite(samples)]
    if not len(samples):return {}
    return {'ci95_quarter':np.quantile(samples,[.025,.975]),'ci95_family4_quarter':np.quantile(samples,[.025/4,1-.025/4]),'ci95_family8_quarter':np.quantile(samples,[.025/8,1-.025/8])}
def boot_mean(values,selected):
    nums=np.bincount(q,weights=np.where(selected,values,0),minlength=qn)
    dens=np.bincount(q,weights=selected,minlength=qn)
    den=draws@dens
    return np.divide(draws@nums,den,out=np.full(B,np.nan),where=den>0)
def opportunity_boot(values,opportunities):
    nums=np.bincount(q,weights=np.where(opportunities,values,0),minlength=qn)
    den=draws@np.bincount(q,weights=opportunities,minlength=qn)
    return np.divide(draws@nums,den,out=np.full(B,np.nan),where=den>0)
def stats(values,selected,opportunities,bootstrap=False):
    n=int(selected.sum());ids=np.flatnonzero(selected);x=values[selected]
    out={'n':n,'opportunities':int(opportunities.sum()),'unique_entry_time_blocks':int(w.entry_time[selected].nunique()),'active_weeks':int(w.entry_time[selected].dt.to_period('W').nunique()),'quarters':int(w.quarter[selected].nunique()),'trade_frequency':n/opportunities.sum() if opportunities.any() else None,'gross_per_opportunity_pct':float(np.sum(x)/opportunities.sum()) if opportunities.any() else None}
    if not n:return out
    out.update(mean_gross_pct=x.mean(),median_gross_pct=np.median(x),win_rate=(x>0).mean(),wins=int((x>0).sum()),sum_trade_pct_not_portfolio=x.sum(),best_pct=x.max(),worst_pct=x.min(),exclude_best_trade1_mean_pct=np.sort(x)[:-1].mean() if n>1 else None,exclude_best_trade3_mean_pct=np.sort(x)[:-3].mean() if n>3 else None)
    sums=pd.DataFrame({'time':w.entry_time[selected].to_numpy(),'ret':x}).groupby('time').ret.sum().sort_values(ascending=False)
    for k in [1,3]:
        remaining=selected&~w.entry_time.isin(sums.index[:k]).to_numpy()
        out[f'exclude_best_block{k}_remaining_trades']=int(remaining.sum());out[f'exclude_best_block{k}_mean_pct']=values[remaining].mean() if remaining.any() else None
    out['best_block_sum_trade_pct']=sums.iloc[0];out['best_block_share_of_signed_sum']=sums.iloc[0]/x.sum() if abs(x.sum())>1e-12 else None
    out['common_calendar_halves']=[{'half':h,'n':int((selected&w.common_half.eq(h).to_numpy()).sum()),'mean_pct':values[selected&w.common_half.eq(h).to_numpy()].mean() if (selected&w.common_half.eq(h).to_numpy()).any() else None} for h in [1,2]]
    out['leave_one_year_out']=[{'omitted':int(y),'n':int((selected&w.year.ne(y).to_numpy()).sum()),'mean_pct':values[selected&w.year.ne(y).to_numpy()].mean() if (selected&w.year.ne(y).to_numpy()).any() else None}for y in sorted(w.year[selected].unique())]
    if bootstrap:
        out['trade_mean_intervals']=ci(boot_mean(values,selected))
        out['opportunity_mean_intervals']=ci(opportunity_boot(np.where(selected,values,0),opportunities))
    return out

results=[];breakdown=[]
for i,p in enumerate(policies):
    result={'policy':p['name'],'kind':p['kind'],'side':'long' if p['side']==1 else 'short','all':stats(gross[i],mask[i],eligible,True),'cohorts':{},'cohort_components':{},'years':{},'assets':{},'folds':{},'quarters':{}}
    for output,col in [('cohorts','analysis_cohort'),('cohort_components','cohort'),('years','year'),('assets','asset'),('folds','fold'),('quarters','quarter')]:
        for v in sorted(w.loc[eligible,col].unique()):
            scope=w[col].eq(v).to_numpy();zstat=stats(gross[i],mask[i]&scope,eligible&scope)
            result[output][str(v)]=zstat
            breakdown.append({'policy':p['name'],'grouping':output,'group':v,**{k:x for k,x in zstat.items() if not isinstance(x,(dict,list))}})
    results.append(result)

# Matched no-AI price gate; reestimate mean outcome within every resample.
comparisons=[];matched_vectors=np.full((4,N),np.nan)
for j,(name,s,gate,AI) in enumerate(spec):
    selected=mask[j];allowed=eligible&gate
    keys=['cohort','asset','year'];data=w.loc[allowed].copy();data['selected']=selected[allowed]
    expected=np.full(N,np.nan);control_total=np.zeros(B)
    strata=[]
    for label,g in data.groupby(keys):
        ids=g.index.to_numpy();sel=ids[selected[ids]]
        expected[ids]=s*r[ids].mean()
        qcount=np.bincount(q[ids],minlength=qn);qsum=np.bincount(q[ids],weights=r[ids],minlength=qn)
        qsel=np.bincount(q[sel],minlength=qn)
        count=draws@qcount;mean=np.divide(draws@qsum,count,out=np.zeros(B),where=count>0)
        control_total+=s*mean*(draws@qsel)
        strata.append({'cohort':label[0],'asset':label[1],'year':int(label[2]),'price_gate_n':len(ids),'AI_selected_n':len(sel),'mixed':0<len(sel)<len(ids)})
    residual=gross[j]-expected;matched_vectors[j]=residual
    den=draws@np.bincount(q,weights=selected,minlength=qn)
    own=draws@np.bincount(q,weights=payoff[j],minlength=qn)
    samples=np.divide(own-control_total,den,out=np.full(B,np.nan),where=den>0)
    results[j]['AI_increment_vs_composition_matched_price']={'mean_pct':residual[selected].mean() if selected.any() else None,**ci(samples),'selected_with_mixed_contrast':sum(x['AI_selected_n'] for x in strata if x['mixed']),'selected_in_all_selected_strata':sum(x['AI_selected_n'] for x in strata if not x['mixed']),'strata':strata,'baselines_reestimated_each_draw':True,'association_not_causal':True}
    label='long' if s==1 else 'short'
    compare_names=[name+'_price_only',*[f'C_{label}_{suffix}'for suffix in ['AI_only','legacy_confirm_AI','legacy_confirm_price','BTC_direction_AI','unconditional']]]
    for other in compare_names:
        k=lookup[other];diff=payoff[j]-payoff[k]
        candidate_sample=boot_mean(gross[j],mask[j]);control_sample=boot_mean(gross[k],mask[k])
        comparisons.append({'candidate':name,'control':other,'same_common_asset_opportunities':int(eligible.sum()),'candidate_n':int(mask[j].sum()),'control_n':int(mask[k].sum()),'candidate_trade_mean_pct':gross[j,mask[j]].mean() if mask[j].any() else None,'control_trade_mean_pct':gross[k,mask[k]].mean() if mask[k].any() else None,'paired_per_opportunity_difference_pct':diff[eligible].mean(), 'paired_per_opportunity_intervals':ci(opportunity_boot(diff,eligible)),'trade_mean_difference_pct':gross[j,mask[j]].mean()-gross[k,mask[k]].mean() if mask[j].any() and mask[k].any() else None,'trade_mean_difference_intervals':ci(candidate_sample-control_sample),'skips_zero':True,'same_clock':True})

gate=[]
for j in range(8):
    zstat=results[j]['all'];half=zstat.get('common_calendar_halves',[])
    cohorts=[c for c,v in results[j]['cohorts'].items() if v['n']>=10 and v.get('mean_gross_pct',-999)>0]
    years=[y for y,v in results[j]['years'].items() if v['n']>=10 and v.get('mean_gross_pct',-999)>0]
    criteria={'at_least50_selected_time_blocks':zstat['unique_entry_time_blocks']>=50,'both_common_halves_positive':len(half)==2 and all(x['mean_pct'] is not None and x['mean_pct']>0 for x in half),'three_positive_cohorts_n10':len(cohorts)>=3,'three_positive_years_n10':len(years)>=3,'remove_best3_blocks_positive':zstat.get('exclude_best_block3_mean_pct') is not None and zstat['exclude_best_block3_mean_pct']>0,'quarter95_lower_positive':zstat.get('trade_mean_intervals',{}).get('ci95_quarter',[-999])[0]>0}
    ai=results[j].get('AI_increment_vs_composition_matched_price')
    evidence=bool(ai and ai['mean_pct'] is not None and ai['mean_pct']>0 and ai.get('ci95_quarter',[-999])[0]>0)
    gate.append({'policy':results[j]['policy'],'kind':results[j]['kind'],'criteria':criteria,'passes_gross_research_screen':all(criteria.values()),'positive_cohorts_n10':cohorts,'positive_years_n10':years,'family8_gross_lower_positive':zstat.get('trade_mean_intervals',{}).get('ci95_family8_quarter',[-999])[0]>0,'AI_increment_evidence':evidence,'new_calls_authorized':False,'fresh_verification':False})

ledger=[]
for j,p in enumerate(policies):
    for i,row in w.iterrows():
        status=row.eligibility_status if not eligible[i] else ('trade' if mask[j,i] else 'gate_not_met')
        if eligible[i] and j<4 and not mask[j,i]:status='AI_action_not_selected' if p['price_gate'][i] else 'price_gate_not_met'
        ledger.append({'policy':p['name'],'kind':p['kind'],'window_id':row.window_id,'cohort':row.cohort,'asset':row.asset,'original_entry_time':str(row.entry_time),'AI_action':row.action,'asset_15m_pct':A[i],'btc_15m_pct':C[i],'status':status,'eligible':bool(eligible[i]),'selected':bool(mask[j,i]),'direction':int(p['side']),'entry_time':str(row.trade_entry_time),'exit_close_time':str(row.trade_exit_close_time),'entry_price':row.trade_entry_price,'exit_price':row.trade_exit_price,'hypothetical_gross_pct':gross[j,i],'opportunity_gross_pct':payoff[j,i]})

w.to_csv(HERE/'windows.csv',index=False)
pd.DataFrame(ledger).to_csv(HERE/'all_trades_and_skips.csv.gz',index=False,compression='gzip')
pd.DataFrame(breakdown).to_csv(HERE/'breakdown.csv',index=False)
save('results.json',results);save('comparisons.json',comparisons);save('CANDIDATE_GATE.json',{'candidate_count':4,'direct_price_gates':4,'additional_comparators':10,'model_calls':0,'new_calls_authorized':False,'fresh_verification':False,'gates':gate})
np.savez_compressed(HERE/'paired_vectors.npz',policy=np.array(names),kind=np.array([p['kind']for p in policies]),selected=mask,gross_pct=gross,opportunity_gross_pct=payoff,eligible=eligible,direction=side,window_id=w.window_id.to_numpy(str),asset=w.asset.to_numpy(str),cohort=w.cohort.to_numpy(str),entry_time=w.entry_time.astype(str).to_numpy(str),quarter=w.quarter.to_numpy(str),matched_price_increment_pct=matched_vectors)
np.savez_compressed(HERE/'quarter_bootstrap.npz',weights=draws,quarters=np.array(quarters))
audit={'passed':True,'source_sha256':HASHES,'source_hashes_unchanged':all(sha(ROOT/p)==h for p,h in HASHES.items()),'model_calls':0,'all_existing_windows':N,'existing_unique_time_blocks':int(w.entry_time.nunique()),'eligible_nonBTC_windows':int(eligible.sum()),'eligible_nonBTC_time_blocks':int(w.entry_time[eligible].nunique()),'BTC_self_excluded':int(w.asset.eq('BTC-USD').sum()),'nonBTC_missing_context_excluded':int((w.asset.ne('BTC-USD')&~w.btc_observation_complete).sum()),'native15m_cached_price_checks':native_price_checks,'observation_minutes':15,'entry_delay_minutes':15,'hold_minutes':120,'exit_elapsed_minutes':135,'fees_bps':0,'policies_and_controls':18,'zero_skips_in_opportunity_vectors':True,'matched_means_reestimated_each_quarter_draw':True,'bootstrap_draws':B,'bootstrap_seed':SEED,'common_halves_keep_synchronized_assets_together':True,'reused_outcome_discovery':True}
assert audit['source_hashes_unchanged'];save('audit.json',audit)
table=[{'policy':x['policy'],'n':x['all']['n'],'blocks':x['all']['unique_entry_time_blocks'],'mean':x['all'].get('mean_gross_pct'),'ci95':x['all'].get('trade_mean_intervals',{}).get('ci95_quarter'),'per_opportunity':x['all']['gross_per_opportunity_pct'],'remove3blocks':x['all'].get('exclude_best_block3_mean_pct')}for x in results]
print(json.dumps(clean(table),indent=2));print('GATE',json.dumps(clean(gate)));print('AUDIT',json.dumps(clean(audit)))
