"""Exploratory reuse: apply all116 unchanged discovery entry definitions to280."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from validate_fresh_long import resolve_run,HERE,ROOT

OUT=HERE/'fresh_grid';OUT.mkdir(exist_ok=True)
run=resolve_run();manifest=json.loads((run/'manifest.json').read_text())
candidates=json.loads((HERE/'candidate_definitions.json').read_text())
old_results=json.loads((HERE/'candidate_results.json').read_text())
records=sorted([json.loads(s) for s in (run/'accepted_decisions.jsonl').read_text().splitlines() if s.strip()],key=lambda x:x['case'])
cases=sorted(manifest['cases'],key=lambda x:x['case'])
assert len(records)==len(cases)==280 and len(candidates)==len(old_results)==116
assert [x['case'] for x in records]==list(range(1,281))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
    if isinstance(v,(np.integer,)):return int(v)
    if isinstance(v,(np.bool_,)):return bool(v)
    if isinstance(v,(float,np.floating)):return float(v) if np.isfinite(v) else None
    return v
def save(name,v):(OUT/name).write_text(json.dumps(clean(v),indent=2,allow_nan=False)+'\n')

sources=[HERE/'candidate_definitions.json',HERE/'candidate_results.json',run/'manifest.json',run/'accepted_decisions.jsonl',ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',ROOT/'data/raw/SOL-USD.csv',ROOT/'data/raw/BTC-USD.csv',OUT/'PLAN.md']
hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
d=pd.DataFrame([{**w,**r['decision']} for w,r in zip(cases,records)]).sort_values('case').reset_index(drop=True)
d['entry_time']=pd.to_datetime(d.entry_time)
daily={}
for asset,length in [('SOL-USD',50),('BTC-USD',200)]:
    x=pd.read_csv(ROOT/f'data/raw/{asset}.csv',index_col=0,parse_dates=True).sort_index()
    x['sma']=x.close.rolling(length,min_periods=length).mean();daily[asset]=x
    dates=d.entry_time.dt.normalize()-pd.Timedelta(days=1)
    ii=x.index.get_indexer(dates);assert (ii>=0).all()
    vals=x.iloc[ii];assert np.isfinite(vals.sma).all()
    d[f'{asset}_daily_up']=vals.close.to_numpy()>vals.sma.to_numpy()
    d[f'{asset}_daily_close']=vals.close.to_numpy();d[f'{asset}_daily_sma']=vals.sma.to_numpy()
d['above_both']=(d.ma20_now<=100)&(d.ma50_now<=100)
d['below_both']=(d.ma20_now>=100)&(d.ma50_now>=100)
d['sol_up']=d['SOL-USD_daily_up'];d['both_up']=d.sol_up & d['BTC-USD_daily_up'];d['both_down']=~d.sol_up & ~d['BTC-USD_daily_up']
d['low_conf']=d.confidence<.65;d['high_conf']=~d.low_conf
d['stop_below_atr']=d.stop_pct*100<d.atr14_pct;d['stop_at_least_atr']=~d.stop_below_atr
px=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True,usecols=[0,1,4]);assert list(px.columns)==['open','close']
bars=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',index_col=0,parse_dates=True,usecols=[0,1,4])
idx=px.index;opens=px.open.to_numpy();closes=px.close.to_numpy();positions=idx.get_indexer(d.entry_time)
assert (positions>0).all() and np.allclose(closes[positions-1],d.price_real,atol=1e-8,rtol=0)
for t,q in zip(d.entry_time,positions):
    sub=idx[q-1:q+270];assert len(sub)==271 and np.all(np.diff(sub.as_unit('ns').asi8)==60_000_000_000)
for wait in [0,15,30]:
    d[f'entry_{wait}']=opens[positions+wait]
    d[f'close_confirm_{wait}']=closes[positions+wait-1]
    bentry=bars.index.get_indexer(d.entry_time+pd.Timedelta(minutes=wait));assert (bentry>=0).all()
    assert np.allclose(bars.open.to_numpy()[bentry],d[f'entry_{wait}'],atol=1e-8,rtol=0)
    for hold in [30,105,240]:
        d[f'exit_{wait}_{hold}']=closes[positions+wait+hold-1]
        bexit=bars.index.get_indexer(d.entry_time+pd.Timedelta(minutes=wait+hold-15));assert (bexit>=0).all()
        assert np.allclose(bars.close.to_numpy()[bexit],d[f'exit_{wait}_{hold}'],atol=1e-8,rtol=0)
        d[f'long_gross_{wait}_{hold}']=(d[f'exit_{wait}_{hold}']/d[f'entry_{wait}']-1)*100
d.to_csv(OUT/'windows.csv',index=False)
rng=np.random.default_rng(2026092961)
def stats(v,ci=False):
    v=np.asarray(v,float);n=len(v)
    if n==0:return {'n':0}
    net=v-.2
    result={'n':n,'gross_mean':v.mean(),'net_mean':net.mean(),'net30_mean':v.mean()-.3,'gross_median':np.median(v),'net_median':np.median(net),'gross_wins':int((v>0).sum()),'net_wins':int((net>0).sum()),'gross_winrate':(v>0).mean(),'net_winrate':(net>0).mean(),'gross_sum':v.sum(),'net_sum':net.sum(),'mean_excluding_best1_net':np.sort(net)[:-1].mean() if n>1 else None,'mean_excluding_best3_net':np.sort(net)[:-3].mean() if n>3 else None,'best_gross':v.max(),'worst_gross':v.min(),'profit_factor_net':net[net>0].sum()/-net[net<0].sum() if (net<0).any() else None,'same_AI_direction_net_mean':-v.mean()-.2}
    if ci and n>=2:
        boot=v[rng.integers(n,size=(10000,n))].mean(1)-.2
        result['net_mean_ci95']=np.quantile(boot,[.025,.975]).tolist()
    return result

results=[];allrows=[];gross_matrix=[];mask_matrix=[];eligible_matrix=[]
for num,(cand,old) in enumerate(zip(candidates,old_results),1):
    side,gate,wait,hold,family=[cand[k] for k in ['side','gate','wait','hold','family']]
    cid=f'{num:03d}_{side}_{gate}_confirm{wait}_hold{hold}'
    assert cid==old['candidate']
    sign=1 if side=='long' else -1
    market=d[gate].to_numpy(bool) if gate!='none' and family=='market' else np.ones(280,bool)
    confirm=np.ones(280,bool) if wait==0 else sign*(d[f'close_confirm_{wait}'].to_numpy()/d.price_real.to_numpy()-1)>0
    eligible=market & confirm
    aimeta=d[gate].to_numpy(bool) if family=='AI_metadata' else np.ones(280,bool)
    selected=eligible & aimeta & (d.action.to_numpy()!=side)
    values=d[f'long_gross_{wait}_{hold}'].to_numpy()*sign
    ids=d.loc[selected].sort_values('entry_time').index.to_numpy();mid=len(ids)//2
    thirds=[stats(values[i]) for i in np.array_split(ids,3)]
    result={'candidate':cid,**cand,**stats(values[selected],True),'no_AI_control':stats(values[eligible]),'nonselected_control':stats(values[eligible & ~selected]),'earlier_half':stats(values[ids[:mid]]),'later_half':stats(values[ids[mid:]]),'thirds':thirds,'original150':old}
    result['incremental_gross_vs_no_AI']=values[selected].mean()-values[eligible].mean() if selected.any() else None
    result['net_mean_per_opportunity']=float(np.where(selected,values-.2,0).mean())
    checks={'fresh_n_atleast40':result['n']>=40,'old_n_atleast20':old['n']>=20,'old_net_positive':old.get('net_mean',-999)>0,'fresh_net_positive':result.get('net_mean',-999)>0,'fresh30bps_positive':result.get('net30_mean',-999)>0,'all_halves_positive':all(result[k].get('net_mean',-999)>0 for k in ['earlier_half','later_half']),'all_thirds_positive':all(v.get('net_mean',-999)>0 for v in thirds),'remove_best3_positive':result.get('mean_excluding_best3_net',-999)>0 if result['n']>3 else False,'AI_increment_positive':result.get('incremental_gross_vs_no_AI',-999)>0}
    result['screen']=checks;result['passes_screen']=all(checks.values());results.append(result)
    gross_matrix.append(values);mask_matrix.append(selected);eligible_matrix.append(eligible)
    for i in range(280):
        allrows.append({'candidate':cid,'case':int(d.loc[i,'case']),'window_id':d.loc[i,'window_id'],'ai_action':d.loc[i,'action'],'side':side,'signal_time':str(d.loc[i,'entry_time']),'entry_time':str(d.loc[i,'entry_time']+pd.Timedelta(minutes=wait)),'exit_time':str(d.loc[i,'entry_time']+pd.Timedelta(minutes=wait+hold)),'entry_px':d.loc[i,f'entry_{wait}'],'exit_px':d.loc[i,f'exit_{wait}_{hold}'],'hypothetical_gross_pct':values[i],'hypothetical_net20_pct':values[i]-.2,'hypothetical_net30_pct':values[i]-.3,'market_gate':bool(market[i]),'confirmation':bool(confirm[i]),'no_AI_eligible':bool(eligible[i]),'AI_metadata_gate':bool(aimeta[i]),'selected':bool(selected[i]),'policy_net20_pct':values[i]-.2 if selected[i] else 0.0})
save('candidate_results.json',results)
flat=[]
for r in results:
    row={k:v for k,v in r.items() if not isinstance(v,(dict,list))}
    for sub in ['no_AI_control','nonselected_control','earlier_half','later_half','original150']:
        row.update({sub+'_'+k:r[sub].get(k) for k in ['n','net_mean','gross_winrate']})
    row.update({f'third{i+1}_net':v.get('net_mean') for i,v in enumerate(r['thirds'])})
    row.update({'check_'+k:v for k,v in r['screen'].items()})
    row['ci_low_net']=r.get('net_mean_ci95',[None,None])[0];row['ci_high_net']=r.get('net_mean_ci95',[None,None])[1]
    flat.append(row)
sf=pd.DataFrame(flat);sf.to_csv(OUT/'candidate_results.csv',index=False)
pd.DataFrame(allrows).to_csv(OUT/'all_candidate_windows.csv.gz',index=False)
np.savez_compressed(OUT/'all_candidate_arrays.npz',gross_pct=np.array(gross_matrix),net20_pct=np.array(gross_matrix)-.2,selected=np.array(mask_matrix),no_AI_eligible=np.array(eligible_matrix),case=d.case.to_numpy(),window_id=d.window_id.to_numpy(dtype=str),candidate=np.array([r['candidate'] for r in results]),entry_time=d.entry_time.astype(str).to_numpy(dtype=str))
audit={'status':'passed','exploratory_after_primary_inspection':True,'independent_confirmation':False,'new_model_calls':0,'unchanged_candidate_count':116,'fresh_windows':280,'all_candidate_window_rows':len(allrows),'native15m_entry_checks':840,'native15m_exit_checks':2520,'original_source_hashes':hashes,'all_hashes_still_match':all(sha(ROOT/p)==h for p,h in hashes.items()),'screen_pass_count':int(sf.passes_screen.sum())}
assert audit['all_hashes_still_match'];save('audit.json',audit)
show=['candidate','n','net_mean','net30_mean','original150_n','original150_net_mean','no_AI_control_net_mean','incremental_gross_vs_no_AI','earlier_half_net_mean','later_half_net_mean','third1_net','third2_net','third3_net','mean_excluding_best3_net','ci_low_net','passes_screen']
print('Passing screen:',len(sf[sf.passes_screen]));print(sf[sf.passes_screen][show].to_string(index=False))
print('\nFresh>=40, original>=20 ranked:');print(sf[(sf.n>=40)&(sf.original150_n>=20)].sort_values('net_mean',ascending=False).head(20)[show].to_string(index=False))
