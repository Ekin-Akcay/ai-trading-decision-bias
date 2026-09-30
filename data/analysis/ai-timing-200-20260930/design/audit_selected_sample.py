"""Pre-call audit. No post-entry return, excursion, or price is emitted."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;ROOT=H.parents[3];MIN=60*10**9
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def eq(a,b):assert np.allclose(a,b,rtol=1e-11,atol=1e-11,equal_nan=True),(a,b)
f=json.loads((H/'fresh_windows.json').read_text());w=pd.DataFrame(f['cases']);assert len(w)==300 and w.case_id.tolist()==list(range(1,301))
assert sha(H/'fresh_windows.json')=='c75250262c5596c0b68307a6fd47f1b599521d527be82132e67a035084d6a8a6'
assert all(sha(ROOT/p)==h for p,h in f['source_sha256'].items())
for key,name in [('candidate_metadata_sha256','candidate_metadata.csv'),('selected_sample_sha256','selected_sample.csv'),('exclusion_intervals_sha256','exclusion_intervals.json')]:assert sha(H/name)==f[key]
# Reconstruct earlier exposures directly from the canonical prior manifests.
ma=json.loads((ROOT/'data/analysis/gross-edge-20260929/ma_ablation/design/fresh_blocks.json').read_text());proxy=json.loads((ROOT/'data/analysis/new-angles-20260930/proxy_replication/frozen_sample.json').read_text())
prior={pd.Timestamp(z['entry_time']).value:(z['history_hours'],z['outcome_hours']) for z in ma['prior_exposure_intervals']};assert len(prior)==591
for z in ma['blocks']:prior[pd.Timestamp(z['entry_time']).value]=(50,6)
assert len(prior)==681
intervals=[(int(t-h*60*MIN),int(t+n*60*MIN)) for t,(h,n) in prior.items()]+[(pd.Timestamp(t).value,pd.Timestamp(t).value+240*MIN) for t in proxy['entry_times']];assert len(intervals)==1464
saved=json.loads((H/'exclusion_intervals.json').read_text());assert sorted(intervals)==sorted((x['start_ns'],x['end_ns']) for x in saved['intervals'])
assert not any(int(t) in prior for t in w.t0_ns);assert w.window_id.nunique()==300 and w.utc_day.nunique()==300
sorted_ns=np.sort(w.t0_ns.to_numpy(np.int64));assert np.diff(sorted_ns).min()>=120*MIN
boundary=0
for _,r in w.iterrows():
 t=int(r.t0_ns);assert t%(30*MIN)==0;assert pd.Timestamp(r.t0).value==t and pd.Timestamp(r.window_end_ts).value==t-15*MIN;assert pd.Timestamp(r.entry_time).value==t+30*MIN and pd.Timestamp(r.horizon_end).value==t+150*MIN
 for a,b in intervals:assert t+150*MIN<=a or t+30*MIN>=b;boundary+=int(t+150*MIN==a or t+30*MIN==b)
assert (w.iloc[:60].stage=='screen').all() and (w.iloc[60:].stage=='confirmation').all();assert w[w.stage.eq('screen')].direction.value_counts().to_dict()=={'down':30,'up':30} or w[w.stage.eq('screen')].direction.value_counts().to_dict()=={'up':30,'down':30}
for direction in ['up','down']:
 z=w[w.stage.eq('confirmation')&w.direction.eq(direction)];assert z.confirmation_rank.tolist()==list(range(1,121));assert set(z[z.confirmation_rank<=60].asset.value_counts())=={15};assert set(z.asset.value_counts())=={30}
# Recompute every gate from native past/observation data. Future values used ONLY for validity.
gate_checks=0
for asset,g in w.groupby('asset'):
 b=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_15m.csv.gz',index_col=0,parse_dates=True).sort_index();m=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_1m.csv.gz',index_col=0,parse_dates=True).sort_index();assert b.index.is_unique and m.index.is_unique
 for _,r in g.iterrows():
  t=pd.Timestamp(int(r.t0_ns));bi=b.index.get_loc(t-pd.Timedelta(minutes=15));mi=m.index.get_loc(t);assert bi>=200 and mi>=3000
  hist=b.iloc[bi-199:bi+1];assert len(hist)==200;assert np.array_equal(hist.index,pd.date_range(t-pd.Timedelta(hours=50),periods=200,freq='15min'));bv=hist[['open','high','low','close','volume']].to_numpy();assert np.isfinite(bv).all() and (bv[:,:4]>0).all() and (bv[:,4]>=0).all()
  history=m.iloc[mi-3000:mi];obs=m.iloc[mi:mi+30];coverage=m.iloc[mi:mi+150]
  assert len(history)==3000 and np.array_equal(history.index,pd.date_range(t-pd.Timedelta(minutes=3000),periods=3000,freq='min'))
  assert np.array_equal(coverage.index,pd.date_range(t,periods=150,freq='min'))
  # Only boolean validity is computed on target OHLC, without deriving price changes.
  cv=coverage[['open','high','low','close']].to_numpy();assert np.isfinite(cv).all() and (cv>0).all() and (cv[:,1]>=cv[:,[0,2,3]].max(axis=1)).all() and (cv[:,2]<=cv[:,[0,1,3]].min(axis=1)).all()
  hv=history.volume.to_numpy();ov=obs.volume.to_numpy();assert np.isfinite(hv).all() and np.isfinite(ov).all() and (hv>=0).all() and (ov>=0).all()
  baseline=np.median(hv.reshape(100,30).sum(axis=1));assert baseline>0;ratio=ov.sum()/baseline;move=100*(obs.close.iloc[-1]/obs.open.iloc[0]-1)
  c=hist.close.to_numpy();h=hist.high.to_numpy();l=hist.low.to_numpy();tr=np.maximum.reduce([h[1:]-l[1:],abs(h[1:]-c[:-1]),abs(l[1:]-c[:-1])]);atr=tr[-14:].mean()/c[-1]*100
  eq([ratio,move,atr,baseline,ov.sum()],[r.gate_volume_ratio,r.gate_move_pct,r.atr14_pct,r.baseline_volume_median,r.gate_volume]);assert abs(move)>=.5*atr and ratio<=.75 and ('up' if move>0 else 'down')==r.direction
  eq(m.close.iloc[mi-1],c[-1]);gate_checks+=1
 del b,m
# Reconstruct the deterministic selection from frozen pre-entry candidate metadata.
pool=pd.read_csv(H/'candidate_metadata.csv').sort_values(['t0','asset']).reset_index(drop=True);random=np.random.default_rng(2026093017).random(len(pool));eq(random,pool.random_priority)
assets=['SOL-USD','BTC-USD','ETH-USD','DOGE-USD'];blocked=np.zeros(len(pool),bool);selected=[]
for tier,up,down in [('screen',[8,8,7,7],[7,7,8,8]),('confirmation_core',[15]*4,[15]*4),('confirmation_extension',[15]*4,[15]*4)]:
 need={(d,a):n for d,quota in [('up',up),('down',down)] for a,n in zip(assets,quota)};yearcount={int(v):0 for v in pool.year.unique()};picked=[]
 while sum(need.values()):
  choices=[]
  for (d,a),count in need.items():
   if count:
    ids=np.flatnonzero(~blocked&pool.direction.eq(d).to_numpy()&pool.asset.eq(a).to_numpy());assert len(ids);choices.append((pool.iloc[ids].utc_day.nunique()/count,d,a,ids))
  _,d,a,ids=min(choices,key=lambda z:z[:3]);k=min(ids,key=lambda k:(yearcount[int(pool.year[k])],random[k],pool.t0[k],pool.asset[k]));picked.append(k);yearcount[int(pool.year[k])]+=1;need[d,a]-=1;blocked|=pool.utc_day.eq(pool.utc_day[k]).to_numpy()|(abs(pool.t0_ns.to_numpy()-int(pool.t0_ns[k]))<120*MIN)
 selected+=sorted(picked,key=lambda k:random[k])
assert pool.iloc[selected].window_id.tolist()==w.window_id.tolist()
assert all(sha(ROOT/p)==h for p,h in f['source_sha256'].items());budget=json.loads((H.parent/'snapshot_budget.json').read_text());assert not budget['reserved_attempts'];assert sha(Path(budget['old_budget_file_absolute']))==budget['old_budget_sha256']
out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'frozen_sample_sha256':sha(H/'fresh_windows.json'),'potential_cases':300,'unique_UTC_days':300,'maximum_valid_calls':180,'screen_cases':60,'confirmation_core_per_direction':60,'confirmation_extended_per_direction':120,'all300_native_preentry_gates_and_indicator_values_reproduced':True,'all300_history_and_future_validity_coverage_checks_pass':True,'post_entry_returns_computed':False,'post_entry_prices_exported':False,'direct_global_exclusion_comparisons':len(intervals)*len(w),'half_open_boundary_adjacencies':boundary,'all_native_target_intervals_disjoint':True,'deterministic_case_order_and_balancing_reproduced':True,'all_frozen_hashes_preserved':True,'model_calls':0,'new_physical_budget_used':0,'old_physical_calls_preserved':771,'old_remaining_preserved':29}
(H/'precollection_selection_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
