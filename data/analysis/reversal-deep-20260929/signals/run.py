from pathlib import Path
import hashlib,json,itertools
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OLD=ROOT/'data/sim/decisions/rules2to1-openai-20260926T072414Z.jsonl'
NEW=ROOT/'data/sim/decisions/reversal-terra50-20260929T184044Z.jsonl'
RAW=ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz'

def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
    if isinstance(v,(np.integer,)):return int(v)
    if isinstance(v,(np.bool_,)):return bool(v)
    if isinstance(v,(float,np.floating)):return float(v) if np.isfinite(v) else None
    return v
def save(name,v):(HERE/name).write_text(json.dumps(clean(v),indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

files=[OLD,NEW,RAW,ROOT/'data/raw/SOL-USD.csv',ROOT/'data/raw/BTC-USD.csv',HERE/'PLAN.md']
audit={'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files}}
frames=[]
for label,path in [('old100',OLD),('new50',NEW)]:
    z=pd.read_json(path,lines=True);z=z[z.model=='gpt-5.6-terra-agent'].copy();z['cohort']=label;frames.append(z)
d=pd.concat(frames,ignore_index=True).sort_values('window_end_ts').reset_index(drop=True)
assert len(d)==150 and d.window_id.nunique()==150 and set(d.action)=={'long','short'}
d['entry_time']=pd.to_datetime(d.window_end_ts)+pd.Timedelta(minutes=15)
daily={}
for asset,length in [('SOL-USD',50),('BTC-USD',200)]:
    x=pd.read_csv(ROOT/f'data/raw/{asset}.csv',index_col=0,parse_dates=True).sort_index()
    x['sma']=x.close.rolling(length,min_periods=length).mean();daily[asset]=x
for asset,x in daily.items():
    dates=d.entry_time.dt.normalize()-pd.Timedelta(days=1)
    ii=x.index.get_indexer(dates);assert (ii>=0).all()
    vals=x.iloc[ii];assert np.isfinite(vals.sma).all()
    d[f'{asset}_daily_up']=(vals.close.to_numpy()>vals.sma.to_numpy())
    d[f'{asset}_daily_close']=vals.close.to_numpy();d[f'{asset}_daily_sma']=vals.sma.to_numpy()
d['above_both']=(d.ma20_now<=100)&(d.ma50_now<=100)
d['below_both']=(d.ma20_now>=100)&(d.ma50_now>=100)
d['sol_up']=d['SOL-USD_daily_up'];d['both_up']=d.sol_up & d['BTC-USD_daily_up'];d['both_down']=~d.sol_up & ~d['BTC-USD_daily_up']
d['low_conf']=d.confidence<.65;d['high_conf']=~d.low_conf
d['stop_below_atr']=d.stop_pct*100<d.atr14_pct;d['stop_at_least_atr']=~d.stop_below_atr
px=pd.read_csv(RAW,index_col=0,parse_dates=True,usecols=[0,1,4]);assert list(px.columns)==['open','close']
idx=px.index;opens=px.open.to_numpy();closes=px.close.to_numpy();positions=idx.get_indexer(d.entry_time)
assert (positions>0).all()
assert np.allclose(closes[positions-1],d.price_real,atol=1e-8,rtol=0)
for t,q in zip(d.entry_time,positions):
    sub=idx[q-1:q+270];assert len(sub)==271
    assert np.all(np.diff(sub.as_unit('ns').asi8)==60_000_000_000)
for wait,hold in itertools.product([0,15,30],[30,105,240]):
    d[f'entry_{wait}']=opens[positions+wait]
    d[f'close_confirm_{wait}']=closes[positions+wait-1]
    d[f'exit_{wait}_{hold}']=closes[positions+wait+hold-1]
    d[f'long_gross_{wait}_{hold}']=(d[f'exit_{wait}_{hold}']/d[f'entry_{wait}']-1)*100
cols=['cohort','case','window_id','entry_time','price_real','action','confidence','reason','stop_pct','atr14_pct','ma20_now','ma50_now','vol24_ratio','ret_vis_pct','SOL-USD_daily_close','SOL-USD_daily_sma','BTC-USD_daily_close','BTC-USD_daily_sma','above_both','below_both','sol_up','both_up','both_down','low_conf','high_conf','stop_below_atr','stop_at_least_atr']
d[cols].to_csv(HERE/'windows.csv',index=False)

candidates=[]
for side,gate,wait,hold in itertools.product(['long','short'],['none','above_both','below_both','sol_up','both_up','both_down'],[0,15,30],[30,105,240]):
    candidates.append({'side':side,'gate':gate,'wait':wait,'hold':hold,'family':'market'})
for side,gate in itertools.product(['long','short'],['low_conf','high_conf','stop_below_atr','stop_at_least_atr']):
    candidates.append({'side':side,'gate':gate,'wait':0,'hold':105,'family':'AI_metadata'})
assert len(candidates)==116
save('candidate_definitions.json',candidates)
rng=np.random.default_rng(2026092911)
def stats(v,ci=False):
    v=np.asarray(v,float);n=len(v)
    if n==0:return {'n':0}
    result={'n':n,'gross_mean':v.mean(),'net_mean':v.mean()-.2,'gross_median':np.median(v),'gross_wins':int((v>0).sum()),'net_wins':int((v>.2).sum()),'gross_winrate':(v>0).mean(),'net_winrate':(v>.2).mean(),'gross_sum':v.sum(),'net_sum':(v-.2).sum(),'mean_excluding_best_net':(np.delete(v,np.argmax(v)).mean()-.2) if n>1 else None,'best_gross':v.max(),'worst_gross':v.min(),'same_AI_direction_net_mean':-v.mean()-.2}
    if ci and n>=2:
        boot=v[rng.integers(n,size=(10000,n))].mean(1)-.2
        result['net_mean_ci95']=np.quantile(boot,[.025,.975]).tolist()
    return result

results=[];trades=[];eligible_ledgers=[]
for num,cand in enumerate(candidates,1):
    side,gate,wait,hold,family=[cand[k] for k in ['side','gate','wait','hold','family']]
    cid=f'{num:03d}_{side}_{gate}_confirm{wait}_hold{hold}'
    sign=1 if side=='long' else -1
    market=d[gate].to_numpy(bool) if gate!='none' and family=='market' else np.ones(150,bool)
    confirm=np.ones(150,bool) if wait==0 else sign*(d[f'close_confirm_{wait}'].to_numpy()/d.price_real.to_numpy()-1)>0
    eligible=market & confirm
    aimeta=d[gate].to_numpy(bool) if family=='AI_metadata' else np.ones(150,bool)
    selected=eligible & aimeta & (d.action.to_numpy()!=side)
    values=d[f'long_gross_{wait}_{hold}'].to_numpy()*sign
    ids=np.flatnonzero(selected);mid=len(ids)//2
    result={'candidate':cid,**cand,**stats(values[selected],True),'no_AI_control':stats(values[eligible]),'nonselected_control':stats(values[eligible & ~selected]),'earlier_half':stats(values[ids[:mid]]),'later_half':stats(values[ids[mid:]]),'old100':stats(values[selected & (d.cohort=='old100')]),'new50':stats(values[selected & (d.cohort=='new50')])}
    result['incremental_gross_vs_no_AI']=values[selected].mean()-values[eligible].mean() if selected.any() else None
    result['source_both_positive']=all(result[k].get('n',0)>=3 and result[k].get('net_mean',-999)>0 for k in ['old100','new50'])
    result['halves_both_positive']=all(result[k].get('n',0)>=5 and result[k].get('net_mean',-999)>0 for k in ['earlier_half','later_half'])
    result['preferred_criteria']=result.get('n',0)>=15 and result['source_both_positive'] and result['halves_both_positive'] and result.get('incremental_gross_vs_no_AI',-999)>0
    results.append(result)
    for i in np.flatnonzero(eligible):
        row={'candidate':cid,'cohort':d.loc[i,'cohort'],'case':int(d.loc[i,'case']),'window_id':d.loc[i,'window_id'],'ai_action':d.loc[i,'action'],'side':side,'signal_time':str(d.loc[i,'entry_time']),'entry_time':str(d.loc[i,'entry_time']+pd.Timedelta(minutes=wait)),'exit_time':str(d.loc[i,'entry_time']+pd.Timedelta(minutes=wait+hold)),'entry_px':d.loc[i,f'entry_{wait}'],'exit_px':d.loc[i,f'exit_{wait}_{hold}'],'gross_pct':values[i],'net_pct':values[i]-.2,'selected':bool(selected[i])}
        eligible_ledgers.append(row)
        if selected[i]:trades.append(row)
save('candidate_results.json',results)
flat=[]
for r in results:
    row={k:v for k,v in r.items() if not isinstance(v,(dict,list))}
    for sub in ['no_AI_control','nonselected_control','earlier_half','later_half','old100','new50']:
        row.update({sub+'_'+k:r[sub].get(k) for k in ['n','net_mean','gross_winrate']})
    row['ci_low_net']=r.get('net_mean_ci95',[None,None])[0];row['ci_high_net']=r.get('net_mean_ci95',[None,None])[1]
    flat.append(row)
sf=pd.DataFrame(flat);sf.to_csv(HERE/'candidate_results.csv',index=False)
pd.DataFrame(trades).to_csv(HERE/'selected_trades.csv',index=False)
pd.DataFrame(eligible_ledgers).to_csv(HERE/'control_trades.csv',index=False)
audit.update(windows=150,old=100,new=50,unique_windows=int(d.window_id.nunique()),finite_candidates=116,all_same_Terra=True,prior_completed_daily_only=True,native_minute_entry_exit_checks=len(eligible_ledgers),all_minute_paths_contiguous=True,no_model_calls=True,all_source_hashes_still_match=all(sha(ROOT/p)==h for p,h in audit['source_sha256'].items()))
assert audit['all_source_hashes_still_match'];save('validation.json',audit)
pref=sf[sf.preferred_criteria];print('Preferred candidates:',len(pref));print(pref.sort_values('net_mean',ascending=False).to_string(index=False))
print('\nTOP n>=15:');print(sf[sf.n>=15].sort_values('net_mean',ascending=False).head(20)[['candidate','n','net_mean','gross_winrate','incremental_gross_vs_no_AI','earlier_half_net_mean','later_half_net_mean','old100_n','old100_net_mean','new50_n','new50_net_mean','ci_low_net']].to_string(index=False))
