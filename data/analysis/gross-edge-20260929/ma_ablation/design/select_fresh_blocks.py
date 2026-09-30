"""Frozen SOL MA-ablation sample; timestamp, coverage and pre-entry gates only."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[4]
SEED=2026092995; TARGET=90; HOUR=3600*10**9
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'fresh_blocks.json').exists(), 'Sample already frozen'
previous=HERE.parents[1]/'design/fresh_blocks.json'
plan=json.loads(previous.read_text()); hashes={str(previous.relative_to(ROOT)):sha(previous)}
prior={pd.Timestamp(r['entry_time']).value:int(r['outcome_hours']) for r in plan['prior_exposure_intervals']}
assert len(prior)==466
for b in plan['blocks']:
    t=pd.Timestamp(b['entry_time']).value
    prior[t]=max(prior.get(t,0),6)
assert len(prior)==591
paths=[ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',ROOT/'data/raw/SOL-USD.csv',ROOT/'data/raw/BTC-USD.csv']
for p in paths:hashes[str(p.relative_to(ROOT))]=sha(p)
bars=pd.read_csv(paths[0],index_col=0,parse_dates=True).sort_index()
minute=pd.read_csv(paths[1],index_col=0,parse_dates=True).sort_index()
assert bars.index.is_unique and minute.index.is_unique
bns=bars.index.as_unit('ns').asi8;mns=minute.index.as_unit('ns').asi8
ns=bns+15*60*10**9;grid=pd.DatetimeIndex(ns);N=len(ns)
calendar=np.ones(N,bool)
for t,h in sorted(prior.items()):
    delta=ns-t
    calendar &= (delta<=-56*HOUR)|(delta>=h*HOUR)

def bad_ohlc(v,volume=False):
    o,h,l,c=v[:,:4].T
    bad=(~np.isfinite(v)).any(axis=1)|(v[:,:4]<=0).any(axis=1)
    bad |= (h<np.maximum.reduce([o,l,c]))|(l>np.minimum.reduce([o,h,c]))
    if volume:bad |= v[:,4]<0
    return bad
# Last model-visible bar is each native15m row; root build_snapshot requires index>=200.
bp=np.arange(N);first=np.maximum(bp-199,0)
bbad=bad_ohlc(bars[['open','high','low','close','volume']].to_numpy(float),True)
bprefix=np.r_[0,np.cumsum(bbad)];bgaps=np.r_[0,np.cumsum(np.r_[False,np.diff(bns)!=15*60*10**9])]
history=(bp>=200)&(bprefix[bp+1]-bprefix[first]==0)&(bgaps[bp+1]-bgaps[first+1]==0)
mp=np.searchsorted(mns,ns);end=mp+360
bounded=(mp>0)&(mp<len(minute))&(end<=len(minute))
msafe=np.clip(mp,1,len(minute)-1);esafe=np.minimum(end,len(minute))
forward=bounded&(mns[msafe]==ns)&(mns[msafe-1]==ns-60*10**9)
mbad=bad_ohlc(minute[['open','high','low','close']].to_numpy(float))
mprefix=np.r_[0,np.cumsum(mbad)];mgaps=np.r_[0,np.cumsum(np.r_[False,np.diff(mns)!=60*10**9])]
forward &= (mprefix[esafe]-mprefix[msafe-1]==0)&(mgaps[esafe]-mgaps[msafe]==0)
close_match=np.isclose(minute.close.to_numpy()[msafe-1],bars.close.to_numpy(),rtol=0,atol=1e-8)
previous_day=grid.normalize()-pd.Timedelta(days=1)
daily_ok=np.ones(N,bool);gates={};daily_metadata={}
for asset,period,path in [('SOL-USD',50,paths[2]),('BTC-USD',200,paths[3])]:
    d=pd.read_csv(path,index_col=0,parse_dates=True).sort_index();assert d.index.is_unique
    values=d.close.where(np.isfinite(d.close)&(d.close>0));ma=values.rolling(period,min_periods=period).mean()
    valid=ma.notna().to_numpy(copy=True);dns=d.index.as_unit('ns').asi8
    gaps=np.r_[0,np.cumsum(np.r_[False,np.diff(dns)!=24*HOUR])]
    di=np.arange(len(d));first=np.maximum(di-period+1,0)
    valid &= (di>=period-1)&(gaps[di+1]-gaps[first+1]==0)
    dp=d.index.get_indexer(previous_day);dsafe=np.maximum(dp,0)
    available=(dp>=0)&valid[dsafe]
    daily_ok &= available
    gates[asset]=available&(values.to_numpy()[dsafe]<=ma.to_numpy()[dsafe])
    daily_metadata[asset]={'required_completed_bars':period,'available_grid_rows':int(available.sum())}
coverage=history&forward&close_match&daily_ok
macro=gates['SOL-USD']&gates['BTC-USD'];eligible=calendar&coverage&macro

def greedy(values):
    selected=[]
    for t in values:
        if not selected or np.min(np.abs(np.array(selected,dtype=np.int64)-t))>=56*HOUR:
            selected.append(int(t))
    return np.array(selected,dtype=np.int64)
random_greedy=greedy(np.random.default_rng(SEED).permutation(ns[eligible]));assert len(random_greedy)>=TARGET
selected=random_greedy[:TARGET];indices=np.searchsorted(ns,selected)
assert eligible[indices].all() and len(np.unique(selected))==90
assert np.diff(np.sort(selected)).min()>=56*HOUR
# Direct interval comparisons provide an independent exclusion check.
for entry in selected:
    for old,h in prior.items():
        assert entry+6*HOUR<=old-50*HOUR or entry>=old+h*HOUR
# Native ranges rechecked separately for each chosen block, with no return computation.
for j in indices:
    hist=bars.iloc[j-199:j+1];p=mp[j];f=minute.iloc[p-1:p+360]
    assert len(hist)==200 and len(f)==361
    assert (np.diff(hist.index.as_unit('ns').asi8)==15*60*10**9).all()
    assert (np.diff(f.index.as_unit('ns').asi8)==60*10**9).all()
    assert f.index[-1].value==ns[j]+359*60*10**9
    assert not bad_ohlc(hist[['open','high','low','close','volume']].to_numpy(float),True).any()
    assert not bad_ohlc(f[['open','high','low','close']].to_numpy(float)).any()

dt=pd.DatetimeIndex(selected)
def distribution(period):
    v=dt.year.astype(str) if period=='year' else dt.to_period('Q').astype(str)
    return {str(k):int(v) for k,v in pd.Series(v).value_counts().sort_index().items()}
iso=lambda t:pd.Timestamp(t,tz='UTC').isoformat().replace('+00:00','Z')
result={'assets':['SOL-USD'],'blocks':[{'entry_time':iso(t),'coverage':{'history15m_bars':200,'future_minutes':360,'minute_timestamps_including_prior_close':361,'SOL_completed_daily50_BTC_completed_daily200':True},'macro_gate':{'SOL_at_or_below_50DMA':True,'BTC_at_or_below_200DMA':True}} for t in selected],
    'seed':SEED,'timezone':'UTC','created_at':datetime.now(timezone.utc).isoformat(),
    'description':'First90 eligible blocks from a fixed-seed random permutation followed by a56-hour-spacing greedy filter. Eligibility: SOL previous completed daily close at/below its50-day close average and BTC previous completed daily close at/below its200-day close average; native SOL input/forward coverage. Every new six-hour forward target avoids all591 previously exposed global intervals (466 older and125 first fee-free blocks). Known past input history may be reused. Only timestamps, validity and pre-entry macro indicators informed selection; forward returns were not calculated or inspected. Three isolated input arms per block share the same market outcome and count as90 calendar observations.',
    'calendar_blocks':90,'planned_valid_model_snapshots':270,'arms_per_block':3,
    'minimum_new_block_gap_hours':56,'actual_minimum_new_block_gap_hours':float(np.diff(np.sort(selected)).min()/HOUR),
    'prior_unique_calendar_entries':591,'older_calendar_entries':466,'first_fee_free_calendar_entries':125,
    'prior_horizon_counts':{str(k):int(v) for k,v in pd.Series(list(prior.values())).value_counts().sort_index().items()},
    'prior_exposure_intervals':[{'entry_time':iso(t),'history_hours':50,'outcome_hours':h} for t,h in sorted(prior.items())],
    'coverage_counts':{'grid':N,'calendar_eligible':int(calendar.sum()),'SOL_history_valid':int(history.sum()),'SOL_forward_valid':int(forward.sum()),'all_required_coverage':int(coverage.sum()),'macro_and_coverage_and_exclusions':int(eligible.sum()),'chronological_greedy_maximum':len(greedy(ns[eligible])),'full_random_greedy_capacity':len(random_greedy)},
    'daily_coverage':daily_metadata,'selected_blocks_by_year':distribution('year'),'selected_blocks_by_quarter':distribution('quarter'),
    'forward_returns_examined':False,'source_sha256':hashes,
    'limitations':['Known past feature histories may repeat earlier exposed history/outcomes; new labels are disjoint.', 'A historical archive is not live validation or guaranteed unknown to model pretraining.', 'SOL macro-bear population only; findings do not establish all-market or cross-asset performance.', 'Three model outputs per block do not triple independent market observations.', 'Serial and macro-regime dependence remain; quarter and block inference required.']}
assert all(sha(ROOT/p)==h for p,h in hashes.items())
(HERE/'fresh_blocks.json').write_text(json.dumps(result,indent=2)+'\n')
np.savez_compressed(HERE/'coverage_and_candidate_masks.npz',entry_time_ns=ns,calendar_exclusions_pass=calendar,coverage_pass=coverage,macro_bear_gate=macro,eligible=eligible,selected_entry_time_ns=selected)
audit={'status':'PASS','selected_blocks':90,'selection_seed':SEED,'independent_interval_comparisons':90*591,'selected_native_history_and_minute_ranges_rechecked':90,'selected_macro_gate_passes':90,'source_hashes_unchanged':True,'forward_returns_examined':False,'model_calls':0,'sample_sha256':sha(HERE/'fresh_blocks.json'),'minimum_gap_hours':result['actual_minimum_new_block_gap_hours'],'capacity':result['coverage_counts'],'quarters':result['selected_blocks_by_quarter']}
(HERE/'sampling_design_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit,indent=2))
