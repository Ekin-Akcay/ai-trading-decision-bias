"""Select fresh forward targets using coverage/timestamps only; no returns scored."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,gc
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
ASSETS=['SOL-USD','BTC-USD','ETH-USD','DOGE-USD']
SEED=2026092990;HOURS=6;GAP=56;TARGET=125
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'fresh_blocks.json').exists(),'Frozen block sample already exists'
prior={};asset_entries={a:set() for a in ASSETS};source_hashes={}
for p in sorted((ROOT/'data/sim/decisions').glob('*.jsonl')):
    source_hashes[str(p.relative_to(ROOT))]=sha(p)
    horizon=24 if p.stem=='reversal-validation280-20260929T194012Z' else 72
    for line in p.read_text().splitlines():
        if not line.strip():continue
        r=json.loads(line)
        if r.get('asset') not in ASSETS or not r.get('window_end_ts'):continue
        t=pd.Timestamp(r['window_end_ts'])+pd.Timedelta(minutes=15)
        asset_entries[r['asset']].add(t)
        prior[t]=max(prior.get(t,0),horizon)
assert {a:len(v) for a,v in asset_entries.items()}=={'SOL-USD':436,'BTC-USD':11,'ETH-USD':12,'DOGE-USD':7}
prior=sorted(prior.items())

# Calendar candidates start on the common SOL 15-minute grid. Other assets may
# have longer archives; they are not used to overweight the earliest period.
base=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',index_col=0,parse_dates=True).sort_index()
grid=(base.index+pd.Timedelta(minutes=15)).as_unit('ns')
ns=grid.asi8;N=len(grid);del base
old_ns=np.array([t.value for t,h in prior],dtype=np.int64)
old_h=np.array([h for t,h in prior],dtype=np.int64)
fresh=np.ones(N,bool);strict=np.ones(N,bool)
for t,h in zip(old_ns,old_h):
    delta=ns-t
    fresh &= (delta<=-56*3600e9)|(delta>=h*3600e9)
    strict &= (delta<=-56*3600e9)|(delta>=(50+h)*3600e9)
candidate_calendar_fresh=int(fresh.sum());candidate_calendar_strict=int(strict.sum())
coverage=np.ones(N,bool);asset_coverage={};previous_day=grid.normalize()-pd.Timedelta(days=1)

def integrity_bad(values,with_volume=False):
    o,h,l,c=values[:,:4].T
    bad=(~np.isfinite(values)).any(axis=1)|(values[:,:4]<=0).any(axis=1)
    bad |= (h<np.maximum.reduce([o,l,c]))|(l>np.minimum.reduce([o,h,c]))
    if with_volume:bad |= values[:,4]<0
    return bad

for asset in ASSETS:
    p15=ROOT/f'data/raw/intraday/{asset}_15m.csv.gz'
    p1=ROOT/f'data/raw/intraday/{asset}_1m.csv.gz'
    pdaily=ROOT/f'data/raw/{asset}.csv'
    for p in [p15,p1,pdaily]:source_hashes[str(p.relative_to(ROOT))]=sha(p)
    bars=pd.read_csv(p15,index_col=0,parse_dates=True).sort_index()
    minute=pd.read_csv(p1,index_col=0,parse_dates=True).sort_index()
    daily=pd.read_csv(pdaily,index_col=0,parse_dates=True).sort_index()
    assert bars.index.is_unique and minute.index.is_unique and daily.index.is_unique
    bns=bars.index.as_unit('ns').asi8;mns=minute.index.as_unit('ns').asi8
    bp=np.searchsorted(bns,ns-900e9);bsafe=np.minimum(bp,len(bars)-1)
    history_ok=(bp>=200)&(bp<len(bars))&(bns[bsafe]==ns-900e9)
    bbad=integrity_bad(bars[['open','high','low','close','volume']].to_numpy(float),True)
    bprefix=np.r_[0,np.cumsum(bbad)]
    bgaps=np.r_[0,np.cumsum(np.r_[False,np.diff(bns)!=900e9])]
    first=np.maximum(bsafe-199,0)
    history_ok &= (bprefix[bsafe+1]-bprefix[first]==0)&(bgaps[bsafe+1]-bgaps[first+1]==0)
    mp=np.searchsorted(mns,ns);end=mp+360
    bounded=(mp>0)&(mp<len(minute))&(end<=len(minute))
    msafe=np.clip(mp,1,len(minute)-1);esafe=np.minimum(end,len(minute))
    forward_ok=bounded&(mns[msafe]==ns)&(mns[msafe-1]==ns-60e9)
    mbad=integrity_bad(minute[['open','high','low','close']].to_numpy(float))
    mprefix=np.r_[0,np.cumsum(mbad)];mgaps=np.r_[0,np.cumsum(np.r_[False,np.diff(mns)!=60e9])]
    forward_ok &= (mprefix[esafe]-mprefix[msafe-1]==0)&(mgaps[esafe]-mgaps[msafe]==0)
    # Entry-close consistency uses only the last already-completed minute.
    close_match=np.isclose(minute.close.to_numpy()[msafe-1],bars.close.to_numpy()[bsafe],rtol=0,atol=1e-8)
    period=200 if asset=='BTC-USD' else 50
    dvalues=daily.close.where(np.isfinite(daily.close)&(daily.close>0))
    enough=dvalues.rolling(period,min_periods=period).mean().notna().to_numpy(copy=True)
    dns=daily.index.as_unit('ns').asi8
    dgap=np.r_[0,np.cumsum(np.r_[False,np.diff(dns)!=86400e9])]
    di=np.arange(len(daily));dstart=np.maximum(di-period+1,0)
    enough &= (di>=period-1)&(dgap[di+1]-dgap[dstart+1]==0)
    dp=daily.index.get_indexer(previous_day)
    dsafe=np.maximum(dp,0);daily_ok=(dp>=0)&enough[dsafe]
    okay=history_ok&forward_ok&daily_ok&close_match
    coverage &= okay
    asset_coverage[asset]={'native15m_bars':len(bars),'native1m_bars':len(minute),
        'archive15m_start':str(bars.index[0]),'archive15m_end':str(bars.index[-1]),
        'grid_valid_history200':int(history_ok.sum()),'grid_valid_forward361_minutes':int(forward_ok.sum()),
        'grid_valid_previous_completed_daily_history':int(daily_ok.sum()),
        'required_completed_daily_bars':period,'all_checks_valid':int(okay.sum())}
    print('Coverage checked',asset,'valid',int(okay.sum()),flush=True)
    del bars,minute,daily,bbad,bprefix,bgaps,mbad,mprefix,mgaps,bns,mns,dns
    gc.collect()

fresh &= coverage;strict &= coverage
def greedy(values):
    picked=[]
    for t in values:
        if not picked or np.min(np.abs(np.asarray(picked,dtype=np.int64)-t))>=GAP*3600e9:
            picked.append(int(t))
    return picked
fresh_candidates=ns[fresh];strict_candidates=ns[strict]
random_full=greedy(np.random.default_rng(SEED).permutation(fresh_candidates))
strict_random=greedy(np.random.default_rng(SEED).permutation(strict_candidates))
fresh_max=len(greedy(fresh_candidates));strict_max=len(greedy(strict_candidates))
assert len(random_full)>=TARGET
selected=np.array(random_full[:TARGET],dtype=np.int64)
assert np.diff(np.sort(selected)).min()>=GAP*3600e9
for t,h in zip(old_ns,old_h):
    delta=selected-t
    assert np.all((delta<=-56*3600e9)|(delta>=h*3600e9))
dt=pd.DatetimeIndex(selected)
blocks=[{'entry_time':t.tz_localize('UTC').isoformat().replace('+00:00','Z'),
         'coverage':{'all_four_assets':True,'history15m_bars':200,'future_minutes':360,
                     'minute_timestamps_including_prior_close':361,
                     'previous_completed_asset_daily50_and_BTC_daily200':True}}
        for t in dt]
def distribution(index,kind):
    labels=index.year.astype(str) if kind=='year' else index.to_period('Q').astype(str)
    return {str(k):int(v) for k,v in pd.Series(labels).value_counts().sort_index().items()}
out={'assets':ASSETS,'blocks':blocks,'seed':SEED,'timezone':'UTC',
     'created_at':datetime.now(timezone.utc).isoformat(),
     'description':'125 random calendar blocks, all four assets per block. Each six-hour forward target interval is disjoint from every previously exposed 50-hour snapshot history plus its known 24/72-hour outcome interval across all assets. New 50-hour feature histories may overlap already-known past observations. New blocks are at least56 hours apart, making their complete history-plus-target intervals mutually disjoint. Selection uses timestamps and validity only; no outcome, return, MA regime, or macro regime conditioning. Assets within a block are correlated replications, not independent sample units.',
     'planned_snapshots':500,'calendar_blocks':125,'minimum_new_block_gap_hours':56,
     'actual_minimum_new_block_gap_hours':float(np.diff(np.sort(selected)).min()/3600e9),
     'prior_unique_calendar_entries':len(prior),
     'prior_unique_asset_entries':{a:len(v) for a,v in asset_entries.items()},
     'prior_horizon_counts':{str(k):int(v) for k,v in pd.Series(old_h).value_counts().items()},
     'prior_exposure_intervals':[{'entry_time':t.tz_localize('UTC').isoformat().replace('+00:00','Z'),'history_hours':50,'outcome_hours':int(h)} for t,h in prior],
     'fresh_target_design':{'candidate_grid_bars_before_coverage':candidate_calendar_fresh,
                            'coverage_valid_candidate_bars':len(fresh_candidates),
                            'maximum_chronological_greedy_blocks':fresh_max,
                            'complete_random_greedy_capacity':len(random_full)},
     'strict_all_information_nonoverlap_alternative':{'candidate_grid_bars_before_coverage':candidate_calendar_strict,
                            'coverage_valid_candidate_bars':len(strict_candidates),
                            'maximum_chronological_greedy_blocks':strict_max,
                            'complete_random_greedy_capacity':len(strict_random),
                            'used_for_model_calls':False},
     'asset_coverage':asset_coverage,'selected_blocks_by_year':distribution(dt,'year'),
     'selected_blocks_by_quarter':distribution(dt,'quarter'),
     'forward_returns_examined':False,'source_sha256':source_hashes,
     'limitations':['Historical archive; not live or guaranteed unknown to model training',
                    '500 snapshots are125 calendar blocks, not500 independent market observations',
                    'Known past feature reuse is allowed; fresh targets do not overlap earlier exposed snapshot paths',
                    'Serial and macro-regime dependence remains; infer using calendar/quarter clusters',
                    'Exposure intervals cover previously used snapshot histories and outcome paths; public historical knowledge and prior aggregate daily indicators cannot be made unseen']}
assert all(sha(ROOT/p)==h for p,h in source_hashes.items())
(HERE/'fresh_blocks.json').write_text(json.dumps(out,indent=2)+'\n')
np.savez_compressed(HERE/'coverage_and_candidate_masks.npz',entry_time_ns=ns,all_asset_coverage=coverage,
                    fresh_target_candidate=fresh,strict_candidate=strict,selected_entry_time_ns=selected)
print(json.dumps({k:out[k] for k in ['calendar_blocks','planned_snapshots','actual_minimum_new_block_gap_hours','fresh_target_design','strict_all_information_nonoverlap_alternative','selected_blocks_by_year']},indent=2))
