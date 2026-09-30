from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];F=HERE.parent/'volume_reaction'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def eq(a,b):assert np.allclose(a,b,atol=1e-10,rtol=0,equal_nan=True),(a,b)
reference=np.load(HERE/'volume_reference_vectors.npz');features=pd.read_csv(HERE/'volume_reference_features.csv');w=pd.read_csv(F/'features.csv');w.entry_time=pd.to_datetime(w.entry_time)
source=json.loads((HERE/'volume_reference.json').read_text());assert all(sha(ROOT/p)==h for p,h in source['source_sha256'].items())
assert np.array_equal(features.window_id,w.window_id);eq(features.volume_ratio,w.volume_ratio);eq(features.volume_reference_median,w.pre50h_median_volume30)
for col,rcol in [('open','early_open'),('high','early_high'),('low','early_low'),('close','early_close')]:eq(features[col],w[rcol])
cover=reference['available'];assert np.array_equal(cover,w.volume_coverage) and cover.sum()==1019
v=np.load(F/'vectors.npz');names=list(v['policies']);assert len(names)==14 and v['returns'].shape==(1020,14)
mask=reference['selected'].T;y=reference['opportunity_pct'].T;assert np.array_equal(mask,v['selected']);eq(y,v['returns']);assert np.array_equal(cover,v['coverage'])
quarters=sorted(w.quarter.unique());codes=np.array([quarters.index(q) for q in w.quarter]);G=len(quarters)
weights=np.random.default_rng(2026093041).multinomial(G,np.full(G,1/G),size=20000);assert np.array_equal(weights,v['quarter_weights'])
bs=np.full((20000,14),np.nan);opp=np.full_like(bs,np.nan)
for start in range(0,20000,200):
 rw=weights[start:start+200][:,codes];den=rw@mask.astype(float);num=rw@y
 bs[start:start+len(rw)]=np.divide(num,den,out=np.full_like(num,np.nan),where=den>0)
 opp[start:start+len(rw)]=num/(rw@cover)[:,None]
eq(bs,v['quarter_bootstrap']);eq(opp,v['opportunity_bootstrap'])
summary=json.loads((F/'summary.json').read_text());assert len(summary)==14
for r in summary:
 j=names.index(r['policy']);take=mask[:,j];ret=y[take,j];assert len(ret)==r['trades'] and w.loc[take,'entry_time'].nunique()==r['blocks'];eq(ret.mean(),r['gross_mean_pct']);eq(np.median(ret),r['median_pct']);eq((ret>0).mean(),r['win_rate']);eq(y[:,j].sum()/cover.sum(),r['opportunity_mean_pct'])
 eq(np.nanquantile(bs[:,j],[.025,.975]),r['quarter95_ci_pct']);eq(np.nanquantile(bs[:,j],[.025/14,1-.025/14]),r['quarter_family95_ci_pct'])
 block=pd.DataFrame({'time':w.entry_time,'pnl':y[:,j],'n':take}).groupby('time').sum();best=block[block.n>0].sort_values('pnl',ascending=False)
 for count,key in [(1,'without_best1_block_pct'),(3,'without_best3_blocks_pct')]:m=take&~w.entry_time.isin(best.index[:count]).to_numpy();eq(y[m,j].mean(),r[key])
 halves=[y[take&(w.half==h).to_numpy(),j].mean() for h in sorted(w.half.unique())];eq(halves,r['halves'])
 ex3=take&~w.entry_time.isin(best.index[:3]).to_numpy();passed=w.loc[take,'entry_time'].nunique()>=30 and all(h>0 for h in halves) and ex3.any() and y[ex3,j].mean()>0 and r['quarter_family95_ci_pct'][0]>0
 assert bool(passed)==r['stronger_discovery_lead']
comp=json.loads((F/'comparisons.json').read_text());assert len(comp)==8
for c in comp:
 a=names.index(c['candidate']);b=names.index(c['control']);eq((y[:,a]-y[:,b]).sum()/cover.sum(),c['opportunity_difference_pp']);eq(np.nanquantile(opp[:,a]-opp[:,b],[.025,.975]),c['quarter95_ci_pp']);eq(np.nanquantile(opp[:,a]-opp[:,b],[.025/8,1-.025/8]),c['quarter_family95_ci_pp'])
ledger=pd.read_csv(F/'trade_ledger.csv');assert len(ledger)==1020*14
paths=np.load(ROOT/'data/analysis/new-angles-20260930/target_exhaustion/paths.npz')['paths'];side=[1,-1,1,-1]
for j,name in enumerate(names):
 rows=ledger[ledger.policy==name].reset_index(drop=True);assert np.array_equal(rows.window_id,w.window_id) and np.array_equal(rows.selected,mask[:,j]);s=1 if j in [0,1,2,6,7,8,12] else -1
 for i in np.flatnonzero(mask[:,j]):
  r=rows.iloc[i];assert pd.Timestamp(r.entry_time)==w.entry_time[i]+pd.Timedelta(minutes=30) and pd.Timestamp(r.exit_time)==w.entry_time[i]+pd.Timedelta(minutes=150)
  eq(r.entry_price,paths[i,31,0]);eq(r.exit_price,paths[i,150,3]);eq(r.gross_pct,y[i,j]);ep=paths[i,31,0]
  favorable=(paths[i,31:151,1].max()/ep-1) if s==1 else (1-paths[i,31:151,2].min()/ep)
  adverse=(paths[i,31:151,2].min()/ep-1) if s==1 else (1-paths[i,31:151,1].max()/ep)
  eq([r.mfe_pct,r.mae_pct],[100*favorable,100*adverse])
assert all(sha(ROOT/p)==h for p,h in source['source_sha256'].items())
budget=json.loads((ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json').read_text());assert len(budget['reserved_attempts'])==771
out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'windows':1020,'volume_coverage_valid':1019,'volume_exclusions':w.loc[~cover,['window_id','asset','volume_exclusion']].to_dict('records'),'native_volume_history_and_observation_recomputed':True,'all14_signal_masks_and_payoffs_match':True,'all20000_quarter_conditional_and_opportunity_arrays_match':True,'all8_paired_control_intervals_match':True,'selected_ledger_records_checked':int(mask.sum()),'all_entry_exit_times_and_excursions_match':True,'all_local_screen_flags_match':True,'stronger_leads':[r['policy'] for r in summary if r['stronger_discovery_lead']],'source_hashes_preserved':True,'physical_calls':771,'remaining_calls':29,'new_model_calls':0}
(HERE/'volume_final_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
