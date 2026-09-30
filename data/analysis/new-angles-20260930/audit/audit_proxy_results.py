"""Independent locked proxy economics and all bootstrap distributions; no refitting."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];F=HERE.parent/'proxy_replication'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def eq(a,b):
 def c(v):
  if isinstance(v,(list,tuple,np.ndarray)):return [c(x) for x in v]
  return np.nan if v is None else v
 assert np.allclose(c(a),c(b),atol=1e-11,rtol=0,equal_nan=True),(a,b)
def check_stats(v,s):
 v=np.asarray(v);assert len(v)==s['n'];eq(v.mean(),s['mean_pct']);eq(np.median(v),s['median_pct']);assert int((v>0).sum())==s['wins'];eq((v>0).mean(),s['win_rate'])
 eq(v.sum(),s['sum_percentages_not_compounded']);eq(v.min(),s['worst_pct']);eq(v.max(),s['best_pct']);eq(np.sort(v)[-3:].sum(),s['best3_sum_pct'])
 for n in [1,3]:eq(np.sort(v)[:-n].mean(),s['exclude_best'+str(n)+'_mean_pct'])
 for name,z in [('winner',v[v>0]),('loser',v[v<0])]:eq(z.mean() if len(z) else np.nan,s['mean_'+name+'_pct'])
 eq(v[v>0].sum()/-v[v<0].sum() if (v<0).any() else np.nan,s['profit_factor'])

assert (F/'PREFLIGHT_PASS').exists()
sample=json.loads((F/'frozen_sample.json').read_text());lock=json.loads((F/'SCORING_FREEZE.json').read_text());summary=json.loads((F/'summary.json').read_text())
assert sha(F/'frozen_sample.json')==lock['sample_sha256']
for hashes in [sample['source_sha256'],lock['source_sha256']]:assert all(sha(ROOT/p)==h for p,h in hashes.items())
features=pd.read_csv(F/'frozen_features_predictions.csv');features.entry_time=pd.to_datetime(features.entry_time)
assets=['SOL-USD','BTC-USD','ETH-USD','DOGE-USD'];times=pd.DatetimeIndex(sample['entry_times']);N=len(times);assert N==783
index=pd.MultiIndex.from_product([times,assets],names=['entry_time','asset']);d=features.set_index(['entry_time','asset']).loc[index].reset_index();assert len(d)==3132
savedpaths=np.load(F/'paths.npz');paths=savedpaths['paths'];assert paths.shape==(3132,241,4)
assert np.array_equal(savedpaths['asset'],d.asset) and np.array_equal(pd.to_datetime(savedpaths['entry_time']),d.entry_time)
# Re-read each native interval; no dependence on production return columns.
for asset,g in d.groupby('asset'):
 raw=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_1m.csv.gz',index_col=0,parse_dates=True).sort_index()
 for i,r in g.iterrows():
  part=raw.loc[r.entry_time-pd.Timedelta(minutes=1):r.entry_time+pd.Timedelta(minutes=239)]
  assert part.index.equals(pd.date_range(r.entry_time-pd.Timedelta(minutes=1),periods=241,freq='min'))
  arr=part[['open','high','low','close']].to_numpy();eq(arr,paths[i]);eq(arr[0,3],r.price_real)
  assert np.isfinite(arr).all() and (arr>0).all()
  assert (arr[:,1]>=np.maximum.reduce([arr[:,0],arr[:,2],arr[:,3]])).all() and (arr[:,2]<=np.minimum.reduce([arr[:,0],arr[:,1],arr[:,3]])).all()
raw=np.array([(p[240,3]-p[1,0])/p[1,0]*100 for p in paths]).reshape(N,4)
proxy=np.array([1 if p>=.5 else -1 for p in d.pred_short]).reshape(N,4)
ma=np.array([1 if p>=100 else -1 for p in d.ma20_now]).reshape(N,4)
sides=np.stack([proxy,-proxy,np.ones((N,4)),ma]);trade=np.empty((4,N,4));basket=np.empty((N,4));names=['proxy_fade','proxy_follow','always_long','MA20_fade']
for j in range(4):
 for b in range(N):
  for a in range(4):trade[j,b,a]=sides[j,b,a]*raw[b,a]
  basket[b,j]=sum(.25*trade[j,b,a] for a in range(4))
v=np.load(F/'policy_vectors.npz');eq(trade,v['trade_gross_pct']);eq(basket.T,v['basket_gross_pct']);eq(sides,v['sides']);assert list(v['policy'])==names
eq(basket[:,0],-basket[:,1]);w=pd.read_csv(F/'window_results.csv');baskets=pd.read_csv(F/'basket_results.csv')
eq(raw.ravel(),w.long_gross_pct);eq(paths[:,1,0],w.entry_open);eq(paths[:,240,3],w.exit_240_close)
for j,name in enumerate(names):eq(trade[j].ravel(),w[name+'_gross_pct']);eq(basket[:,j],baskets[name+'_gross_pct'])
boot=np.load(F/'bootstrap_arrays.npz',allow_pickle=True);distributions={};groupcodes={}
for label,groups,seed in [('weekly',times.to_period('W-SUN').astype(str),2026093031),('quarter',times.to_period('Q').astype(str),2026093032)]:
 labels=sorted(set(groups));codes=np.array([labels.index(x) for x in groups]);groupcodes[label]=codes;G=len(labels)
 weights=np.random.default_rng(seed).multinomial(G,np.full(G,1/G),size=20000)
 assert np.array_equal(weights,boot[label+'_weights'])
 assert list(boot['week' if label=='weekly' else 'quarter'])==labels
 # Direct row weights reconstitute every sampled basket without grouped-sum code.
 result=np.empty((20000,4))
 for start in range(0,20000,250):
  rw=weights[start:start+250][:,codes];result[start:start+len(rw)]=(rw@basket)/rw.sum(1)[:,None]
 eq(result,boot[label+'_means']);distributions[label]=result
half=np.array_split(np.arange(N),2);third=np.array_split(np.arange(N),3);quarter=times.to_period('Q').astype(str)
for j,name in enumerate(names):
 s=summary['policies'][name];check_stats(basket[:,j],s['basket']);check_stats(trade[j].ravel(),s['asset_trades']);assert s['weeks']==192 and s['quarters']==19
 for group,distr in distributions.items():
  eq(np.quantile(distr[:,j],[.025,.975]),s[group+'_intervals']['ci95']);eq(np.quantile(distr[:,j],[.005,.995]),s[group+'_intervals']['ci99'])
 for ids,st in zip(half,s['chronological_halves']):check_stats(basket[ids,j],st)
 for ids,st in zip(third,s['chronological_thirds']):check_stats(basket[ids,j],st)
 for a,asset in enumerate(assets):check_stats(trade[j,:,a],s['assets'][asset]);check_stats(np.delete(trade[j],a,axis=1).mean(1),s['leave_one_asset_out'][asset]);eq(trade[j,:,a].mean()/4,s['asset_mean_contribution_pct'][asset])
 assert s['direction_counts']=={'long':int((sides[j]>0).sum()),'short':int((sides[j]<0).sum())}
 eq(min(basket[quarter!=q,j].mean() for q in set(quarter)),s['minimum_leave_one_quarter_out_mean_pct'])
 for q in set(quarter):eq(basket[quarter==q,j].sum(),s['quarter_sum_percentages_not_compounded'][q])
delta=basket[:,0]-basket[:,3];dt=trade[0]-trade[3];di=summary['proxy_minus_MA20'];check_stats(delta,di['basket']);eq(delta,baskets.proxy_minus_MA20_pct)
for group,distr in distributions.items():
 eq(np.quantile(distr[:,0]-distr[:,3],[.025,.975]),di[group+'_intervals']['ci95']);eq(np.quantile(distr[:,0]-distr[:,3],[.005,.995]),di[group+'_intervals']['ci99'])
for ids,s in zip(half,di['chronological_halves']):check_stats(delta[ids],s)
for ids,s in zip(third,di['chronological_thirds']):check_stats(delta[ids],s)
for a,asset in enumerate(assets):check_stats(dt[:,a],di['assets'][asset]);check_stats(np.delete(dt,a,axis=1).mean(1),di['leave_one_asset_out'][asset])
for label,values,trades,interval_col in [('gross_profit_gate',basket[:,0],trade[0],0),('increment_over_MA20_gate',delta,dt,None)]:
 wd=distributions['weekly'][:,0] if interval_col==0 else distributions['weekly'][:,0]-distributions['weekly'][:,3]
 qd=distributions['quarter'][:,0] if interval_col==0 else distributions['quarter'][:,0]-distributions['quarter'][:,3]
 conditions={'at_least250_blocks':N>=250,'at_least12_quarters':len(set(quarter))>=12,'weekly99_lower_positive':np.quantile(wd,.005)>0,'quarter95_lower_positive':np.quantile(qd,.025)>0,
  'both_halves_positive':all(values[ids].mean()>0 for ids in half),'exclude_best3_positive':np.sort(values)[:-3].mean()>0,'all_leave_one_asset_out_positive':all(np.delete(trades,a,axis=1).mean()>0 for a in range(4))}
 actual={k:bool(v) for k,v in conditions.items()};assert actual==summary[label]['conditions'];assert bool(all(conditions.values()))==summary[label]['passed'];assert [k for k,v in actual.items() if not v]==summary[label]['failed']
assert summary['two_claims_passed']==bool(summary['gross_profit_gate']['passed'] and summary['increment_over_MA20_gate']['passed'])
# Long/short decomposition is accounting only, not a new selected policy.
legs=pd.read_csv(F/'directional_contributions.csv');checks=0
for _,r in legs.iterrows():
 j=names.index(r.policy);sign=1 if r.leg=='long' else -1
 if r.scope=='all':x=trade[j];mask=sides[j]==sign;factor=1
 elif r.scope=='year':take=times.year==int(r.scope_value);x=trade[j,take];mask=sides[j,take]==sign;factor=1
 else:a=assets.index(r.scope_value);x=trade[j,:,a];mask=sides[j,:,a]==sign;factor=.25
 assert mask.sum()==r.trades;eq(x[mask].mean() if mask.any() else np.nan,r.mean_per_leg_trade_pct);eq(np.where(mask,x,0).mean()*factor,r.contribution_per_total_basket_opportunity_pct);checks+=1
budget=ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json';b=json.loads(budget.read_text());assert len(b['reserved_attempts'])==771
for hashes in [sample['source_sha256'],lock['source_sha256']]:assert all(sha(ROOT/p)==h for p,h in hashes.items())
out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'native_asset_paths_rechecked':3132,'native_rows_rechecked':3132*241,'calendar_baskets':783,'UTC_week_clusters':192,'quarters':19,'independently_reconstructed_trade_values':3132*4,
 'all_20000_weekly_and_quarter_arrays_match':True,'all_policy_and_increment_summary_stats_match':True,'all_locked_gate_flags_match':True,'descriptive_leg_accounting_checks':checks,
 'profit_mean_pct':float(basket[:,0].mean()),'profit_weekly99':np.quantile(distributions['weekly'][:,0],[.005,.995]).tolist(),'profit_quarter95':np.quantile(distributions['quarter'][:,0],[.025,.975]).tolist(),
 'MA20_increment_pp':float(delta.mean()),'increment_weekly99':np.quantile(distributions['weekly'][:,0]-distributions['weekly'][:,3],[.005,.995]).tolist(),'increment_quarter95':np.quantile(distributions['quarter'][:,0]-distributions['quarter'][:,3],[.025,.975]).tolist(),
 'gross_profit_gate':summary['gross_profit_gate'],'increment_gate':summary['increment_over_MA20_gate'],'all_source_hashes_preserved':True,'physical_model_calls_still':771,'remaining_calls_preserved':29,'new_model_calls':0,
 'interpretation':'Both locked claims fail. Small positive historical gross mean does not establish profitable expectancy or improvement over MA20. This is the fixed historical price-proxy test; neither a selected leg nor alternative control rescues it.'}
(HERE/'proxy_final_statistics_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
