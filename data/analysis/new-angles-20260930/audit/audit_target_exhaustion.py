"""Independent vector-first-event and bootstrap audit; no model calls."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];F=HERE.parent/'target_exhaustion'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def eq(a,b):assert np.allclose(a,b,atol=1e-10,rtol=0,equal_nan=True),(a,b)
d=pd.read_csv(F/'windows.csv');d.entry_time=pd.to_datetime(d.entry_time);cache=np.load(F/'paths.npz');p=cache['paths'];N=len(d)
assert N==1020 and p.shape==(1020,361,4) and np.array_equal(cache['window_id'],d.window_id)
assert d.window_id.nunique()==N and np.isfinite(p).all() and (p>0).all()
assert (p[:,:,1]>=np.maximum.reduce([p[:,:,0],p[:,:,2],p[:,:,3]])).all() and (p[:,:,2]<=np.minimum.reduce([p[:,:,0],p[:,:,1],p[:,:,3]])).all()
assert (d.stop_pct>0).all() and (d.atr14_pct>0).all()
for _,g in d.groupby(['cohort','asset']):
 g=g.sort_values('entry_time');assert np.isnan(g.donor_stop_pct.iloc[0])
 for k in range(1,len(g)):
  old=g.iloc[k-1];new=g.iloc[k];assert old.entry_time<new.entry_time and old.window_id==new.donor_window_id
  eq(new.donor_stop_pct,old.stop_pct*new.atr14_pct/old.atr14_pct)
# Cross-check every cached future row against native asset clocks.
for asset,g in d.groupby('asset'):
 raw=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_1m.csv.gz',index_col=0,parse_dates=True).sort_index()
 for i,r in g.iterrows():
  actual=raw.loc[r.entry_time:r.entry_time+pd.Timedelta(minutes=359)]
  assert actual.index.equals(pd.date_range(r.entry_time,periods=360,freq='min'))
  eq(actual[['open','high','low','close']].to_numpy(),p[i,1:])
  eq(raw.loc[r.entry_time-pd.Timedelta(minutes=1),'close'],r.price_real)

# Detect all possible first events as arrays, then choose the earliest.
def independent(path,sign,width):
 if pd.isna(width):return {'status':'missing_donor'}
 origin=path[0,3];sl=origin*(1-sign*width);tp=origin*(1+sign*2*width)
 o,h,l,c=path[1:241].T
 if sign==1:
  os=o<=sl;ot=o>=tp;ss=l<=sl;tt=h>=tp
 else:
  os=o>=sl;ot=o<=tp;ss=h>=sl;tt=l<=tp
 event=np.select([os,ot,ss,tt],[1,2,1,2],default=0)
 hits=np.flatnonzero(event)
 if len(hits)==0:return {'status':'no_target_240'}
 t=hits[0];j=int(t+1)
 if event[t]==1:return {'status':'ambiguous_stop_first' if (not os[t] and not ot[t] and ss[t] and tt[t]) else 'stop_first','first_event_minute':j}
 closes=path[j+1:j+16,3]
 inside=closes<tp if sign==1 else closes>tp
 choices=np.flatnonzero(inside)
 if not len(choices):return {'status':'no_confirmation_15','target_minute':j}
 k=int(j+1+choices[0]);entry_idx=k+1;exit_idx=entry_idx+59;entry=path[entry_idx,0];exit=path[exit_idx,3]
 assert 1<=j<=240 and j<k<=j+15 and exit_idx<=315
 return {'status':'trade','target_minute':j,'confirmation_minute':k,'entry_minute':entry_idx,'exit_minute':exit_idx,'entry_price':entry,'exit_price':exit,'position':'short' if sign==1 else 'long','gross_pct':100*(-sign)*(exit-entry)/entry}
ledger=pd.read_csv(F/'event_ledger.csv');assert len(ledger)==5100
by_event=ledger.set_index(['window_index','geometry']);reconstructed={};replay_count=0
for i,r in d.iterrows():
 sign=1 if r.action=='long' else -1
 for geom,orientation,width in [('ai',sign,r.stop_pct),('donor',sign,r.donor_stop_pct),('atr_same_ai',sign,r.atr14_pct/100),('price_short',-1,r.atr14_pct/100),('price_long',1,r.atr14_pct/100)]:
  got=independent(p[i],orientation,width);saved=by_event.loc[(i,geom)]
  assert got['status']==saved.status,(i,geom,got,saved.to_dict())
  for key,value in got.items():
   if key in ['status','position']:assert value==saved[key]
   else:eq(value,saved[key])
  reconstructed[i,geom]=got;replay_count+=1
family=np.load(F/'family_arrays.npz');names=list(family['policies']);assert len(names)==11
y=np.zeros((N,11));n=np.zeros((N,11))
for j,name in enumerate(names):
 geom,side=name.rsplit('_',1)
 for i in range(N):
  e=reconstructed[i,geom]
  if e['status']=='trade' and (side=='all' or e['position']==side):y[i,j]=e['gross_pct'];n[i,j]=1
assert np.array_equal(n,family['active']);eq(y,family['returns'])
# Resample group frequencies, then dot grouped totals instead of gathering totals.
def bootstrap(numerator,denominator,groups,rng,B=12000):
 labels=sorted(set(groups));codes=np.array([labels.index(x) for x in groups]);m=len(labels)
 a=np.array([numerator[codes==j].sum(axis=0) for j in range(m)]);b=np.array([denominator[codes==j].sum(axis=0) for j in range(m)])
 result=[]
 for start in range(0,B,500):
  size=min(500,B-start);draw=rng.integers(0,m,(size,m));counts=np.zeros((size,m))
  np.add.at(counts,(np.repeat(np.arange(size),m),draw.ravel()),1)
  den=counts@b;num=counts@a
  result.append(np.divide(num,den,out=np.full_like(num,np.nan),where=den>0))
 return np.concatenate(result)
rng=np.random.default_rng(2026093001)
bm=bootstrap(y,n,list(d.entry_time),rng);qm=bootstrap(y,n,list(d.quarter),rng);om=bootstrap(y,np.ones_like(n),list(d.entry_time),rng)
eq(bm,family['block_bootstrap']);eq(qm,family['quarter_bootstrap']);eq(om,family['opportunity_bootstrap'])
if 'quarter_opportunity_bootstrap' in family.files:
 qom=bootstrap(y,np.ones_like(n),list(d.quarter),rng);eq(qom,family['quarter_opportunity_bootstrap'])
summary=json.loads((F/'summary.json').read_text());assert len(summary)==11
for s in summary:
 j=names.index(s['policy']);active=n[:,j]>0;ret=y[active,j];assert len(ret)==s['trades'];eq(ret.mean(),s['mean_gross_pct']);eq(y[:,j].mean(),s['opportunity_mean_pct'])
 eq(np.nanquantile(bm[:,j],[.05/22,1-.05/22]),s['simultaneous_block_ci_pct']);eq(np.nanquantile(qm[:,j],[.025,.975]),s['quarter95_ci_pct'])
 blocks=pd.DataFrame({'time':d.entry_time,'y':y[:,j],'active':active}).groupby('time').agg(y=('y','sum'),n=('active','sum'))
 assert (blocks.n>0).sum()==s['blocks'];best=blocks[blocks.n>0].sort_values('y',ascending=False).head(3).index
 remaining=active&~d.entry_time.isin(best).to_numpy();eq(y[remaining,j].mean(),s['without_best3_blocks_pct'])
 halves=[y[(d.half==h)&active,j].mean() for h in sorted(d.half.unique())];eq(halves,s['halves'])
 positive_folds=sum(y[(d.fold==f)&active,j].mean()>0 for f in sorted(d.fold.unique()));assert positive_folds==s['positive_folds']
 passed=len(ret)>=30 and (blocks.n>0).sum()>=20 and all(h>0 for h in halves) and positive_folds>=4 and y[remaining,j].mean()>0 and s['simultaneous_block_ci_pct'][0]>0
 assert bool(passed)==s['discovery_screen']
comparisons=json.loads((F/'comparisons.json').read_text());assert len(comparisons)==8
for c in comparisons:
 i=names.index(c['policy']);j=names.index(c['control']);eq((y[:,i]-y[:,j]).mean(),c['opportunity_difference_pp']);eq(np.nanquantile(om[:,i]-om[:,j],[.05/16,1-.05/16]),c['simultaneous_block_ci_pp'])
budget=ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json';b=json.loads(budget.read_text());assert len(b['reserved_attempts'])==771
out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'native_asset_windows_rechecked':N,'native_minutes_rechecked':N*360,'unique_calendar_entries':int(d.entry_time.nunique()),'independent_first_event_replays':replay_count,'policies_reconstructed':11,'all_12000_bootstrap_arrays_reproduced':True,'all_8_opportunity_contrasts_reproduced':True,'discovery_screen_passes':[s['policy'] for s in summary if s['discovery_screen']],'budget_physical_calls':771,'remaining_calls_preserved':29,'budget_sha256':sha(budget),'new_model_calls':0,'limitations':['1020asset opportunities at645entry times; arithmetic averages are per asset opportunity/trade, not equal-capital calendar portfolio returns.','All outcomes were already inspected. No result is untouched validation.','Original hypothetical AI brackets are not market orders, so this does not establish liquidity causation.']}
(HERE/'target_exhaustion_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
