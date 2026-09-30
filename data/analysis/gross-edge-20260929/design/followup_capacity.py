"""Coverage and pre-entry gate counts only. Does not freeze a follow-up sample."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
plan=json.loads((H/'fresh_blocks.json').read_text())
a=np.load(H/'coverage_and_candidate_masks.npz')
ns=a['entry_time_ns'];grid=pd.DatetimeIndex(ns);valid=a['fresh_target_candidate'].copy()
new_times=np.array([pd.Timestamp(b['entry_time']).value for b in plan['blocks']],dtype=np.int64)
# All new500 windows exposed the same125 calendar history/future intervals.
# New target [entry,entry+6h] must avoid old [entry_old-50h,entry_old+6h].
for t in new_times:
    delta=ns-t
    valid &= (delta<=-56*3600e9)|(delta>=6*3600e9)
assets=plan['assets'];gates={};previous_day=grid.normalize()-pd.Timedelta(days=1)
daily={}
for asset in assets:
    d=pd.read_csv(ROOT/f'data/raw/{asset}.csv',index_col=0,parse_dates=True).sort_index()
    d['sma50']=d.close.rolling(50,min_periods=50).mean()
    d['sma200']=d.close.rolling(200,min_periods=200).mean()
    daily[asset]=d.reindex(previous_day)
btc_bear=(daily['BTC-USD'].close<=daily['BTC-USD'].sma200).to_numpy()
for asset in assets:
    gates[asset]=btc_bear&(daily[asset].close<=daily[asset].sma50).to_numpy()

def greedy(values,limit=None):
    accepted=[]
    for t in values:
        if not accepted or np.min(abs(np.asarray(accepted)-t))>=56*3600e9:
            accepted.append(int(t))
            if limit is not None and len(accepted)>=limit:break
    return np.asarray(accepted,dtype=np.int64)

def count(mask):
    ts=ns[mask];chrono=greedy(ts)
    random_counts=[]
    for seed in [2026092992,2026092993,2026092994]:
        random_counts.append(len(greedy(np.random.default_rng(seed).permutation(ts))))
    periods=pd.DatetimeIndex(chrono).to_period('Q').astype(str)
    return {'candidate_grid_bars':len(ts),'maximum_chronological_greedy_blocks':len(chrono),
            'random_greedy_capacities':random_counts,
            'max_sample_quarter_coverage':{str(k):int(v) for k,v in pd.Series(periods).value_counts().sort_index().items()},
            'min_entry':str(pd.Timestamp(ts.min())) if len(ts) else None,
            'max_entry':str(pd.Timestamp(ts.max())) if len(ts) else None}

result={'future_hours':6,'new_history_hours':50,'new_new_spacing_hours':56,
        'prior466_calendar_exposures_excluded':True,'new125_calendar_exposures_excluded':True,
        'no_forward_returns_examined':True,'no_sample_frozen':True,'new_model_calls':0,
        'unrestricted_remaining':count(valid),'assets':{asset:count(valid&gates[asset]) for asset in assets}}
three=['SOL-USD','ETH-USD','DOGE-USD']
result['all_three_nonBTC_gates']=count(valid&np.logical_and.reduce([gates[a] for a in three]))
result['all_four_gates']=count(valid&np.logical_and.reduce([gates[a] for a in assets]))
# If blocks are sampled using SOL eligibility, these are the additional known
# asset-gate counts available at those same times; no model opinions involved.
candidate=greedy(np.random.default_rng(2026092992).permutation(ns[valid&gates['SOL-USD']]))
indices=np.searchsorted(ns,candidate)
result['SOL_gated_block_capacity_asset_coverage']={
    'illustrative_seed':2026092992,'calendar_blocks':len(candidate),
    'eligible_snapshots_by_asset':{a:int(gates[a][indices].sum()) for a in assets},
    'eligible_nonBTC_snapshots':sum(int(gates[a][indices].sum()) for a in three),
    'note':'Coverage illustration only; no times exported as a selected sample'}
(H/'followup_capacity.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
