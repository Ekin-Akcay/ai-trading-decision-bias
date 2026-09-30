"""Read only timestamps, prior coverage masks, frozen fits and pre-entry features."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];F=HERE.parent/'proxy_replication';G=ROOT/'data/analysis/gross-edge-20260929';H=3600*10**9
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((F/'frozen_sample.json').read_text());assert not m['new_forward_returns_computed']
assert all(sha(ROOT/p)==h for p,h in m['source_sha256'].items())
assert sha(F/m['features_predictions_file'])==m['features_predictions_sha256']
fits=json.loads((HERE.parent/'information/model_fits.json').read_text());fit={x['test_year']:x for x in fits['folds'] if 'action' in x}
priorplan=json.loads((G/'ma_ablation/design/fresh_blocks.json').read_text());prior={pd.Timestamp(x['entry_time']).value:x['outcome_hours'] for x in priorplan['prior_exposure_intervals']}
prior.update({pd.Timestamp(x['entry_time']).value:6 for x in priorplan['blocks']});assert len(prior)==681
assert {(pd.Timestamp(x['entry_time']).value,x['outcome_hours']) for x in m['prior_exposure_intervals']}==set(prior.items())
cov=np.load(G/'design/coverage_and_candidate_masks.npz');ns=cov['entry_time_ns'];dt=pd.DatetimeIndex(ns)
valid=cov['all_asset_coverage'].copy()&np.isin(dt.year,list(fit))&(dt.minute==0)&np.isin(dt.hour,[0,6,12,18])
for t,h in prior.items():valid&=((ns+4*H<=t-50*H)|(ns>=t+h*H))
for year,f in fit.items():valid&=(dt.year!=year)|(ns>=pd.Timestamp(f['training_end']).value+168*H)
selected=np.array([pd.Timestamp(t).value for t in m['entry_times']],dtype=np.int64)
assert np.array_equal(ns[valid],selected) and len(selected)==783 and np.diff(selected).min()==6*H
for new in selected:
 for old,h in prior.items():assert new+4*H<=old-50*H or new>=old+h*H
rows=pd.read_csv(F/'frozen_features_predictions.csv');rows.entry_time=pd.to_datetime(rows.entry_time)
assert len(rows)==3132 and not rows.duplicated(['entry_time','asset']).any()
assets=['SOL-USD','BTC-USD','ETH-USD','DOGE-USD'];assert rows.groupby('entry_time').asset.apply(set).eq(set(assets)).all()
maxerr=0;checked=0
for asset,g in rows.groupby('asset'):
 raw=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_15m.csv.gz',index_col=0,parse_dates=True).sort_index()
 for _,r in g.iterrows():
  cutoff=r.entry_time-pd.Timedelta(minutes=15);i=raw.index.get_loc(cutoff);assert i>=200
  hist=raw.iloc[i-199:i+1];assert len(hist)==200 and hist.index[-1]==cutoff
  assert (np.diff(hist.index.as_unit('ns').asi8)==15*60*10**9).all()
  x=hist[['open','high','low','close','volume']].to_numpy(float);assert np.isfinite(x).all() and (x[:,:4]>0).all() and (x[:,4]>=0).all()
  close=x[:,3];price=close[-1];k=100/price
  hi=x[-14:,1];lo=x[-14:,2];prev=close[-15:-1]
  true_range=np.maximum.reduce([hi-lo,np.abs(hi-prev),np.abs(lo-prev)])
  atr=true_range.mean()*100/price
  fvalues={'price_real':price,'ma20_now':close[-20:].mean()*k,'ma50_now':close[-50:].mean()*k,'ret_vis_pct':100*(price/close[-40]-1),'vol24_ratio':x[-96:,4].mean()/x[:,4].mean(),'atr14_pct':atr}
  assert atr>0 and fvalues['vol24_ratio']>0
  for key,v in fvalues.items():assert np.isclose(v,r[key],atol=1e-11,rtol=1e-13),(asset,r.entry_time,key,v,r[key])
  f=fit[r.entry_time.year];assert int(r.model_year)==r.entry_time.year and pd.Timestamp(f['training_end'])+pd.Timedelta(days=7)<=r.entry_time
  v=np.array([(100-fvalues['ma20_now'])/atr,(100-fvalues['ma50_now'])/atr,fvalues['ret_vis_pct']/atr,np.log(fvalues['vol24_ratio']),np.log(atr)])
  standard=(v-np.array(f['mu']))/np.array(f['sd']);beta=np.array(f['action']['coefficients']);z=beta[0]+np.dot(beta[1:6],standard)+sum(beta[6+j]*(asset==name) for j,name in enumerate(['BTC-USD','ETH-USD','DOGE-USD']))
  probability=1/(1+np.exp(-np.clip(z,-700,700)));maxerr=max(maxerr,abs(probability-r.pred_short));assert abs(probability-r.pred_short)<1e-11
  assert r.proxy_fade_side==(1 if probability>=.5 else -1) and r.MA20_fade_side==(1 if fvalues['ma20_now']>=100 else -1)
  checked+=1
weeks=pd.DatetimeIndex(selected).to_period('W-SUN').astype(str);quarters=pd.DatetimeIndex(selected).to_period('Q').astype(str)
budget=G/'snapshot_budget.json';b=json.loads(budget.read_text());assert len(b['reserved_attempts'])==771
assert all(sha(ROOT/p)==h for p,h in m['source_sha256'].items())
out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'calendar_blocks':783,'asset_predictions_independently_reconstructed':checked,'unique_UTC_Monday_weeks':len(set(weeks)),'unique_quarters':len(set(quarters)),
 'prior_global_exposure_intervals':681,'direct_interval_comparisons':783*681,'complete_eligible_grid_reproduced':True,'six_hour_spacing_four_hour_nonoverlapping_outcomes':True,'all_inputs_past_only_and_yearly_fit_embargo_pass':True,'max_probability_absolute_error':maxerr,
 'all_source_and_feature_hashes_preserved':True,'sample_sha256':sha(F/'frozen_sample.json'),'budget_physical_calls':771,'remaining_calls_preserved':29,'new_model_calls':0,'new_target_returns_or_minute_prices_opened':False,
 'interpretation':'Frozen price-only model trained on earlier AI labels; historical fresh-target transport test, not a causal AI-value test or removal of prior adaptive discovery. Weekly/quarter dependence remains.'}
(HERE/'proxy_preflight_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
