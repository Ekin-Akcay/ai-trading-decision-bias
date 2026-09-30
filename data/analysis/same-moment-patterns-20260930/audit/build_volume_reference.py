"""Independent replay of the frozen14-policy early-volume family."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];SOURCE=ROOT/'data/analysis/new-angles-20260930/target_exhaustion';STUDY=HERE.parent/'volume_reaction'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=pd.read_csv(SOURCE/'windows.csv');d.entry_time=pd.to_datetime(d.entry_time);cache=np.load(SOURCE/'paths.npz');paths=cache['paths'];assert len(d)==1020 and np.array_equal(cache['window_id'],d.window_id)
source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [STUDY/'PLAN.md',SOURCE/'windows.csv',SOURCE/'paths.npz']}
N=len(d);volume=np.full(N,np.nan);reference=np.full(N,np.nan);available=np.zeros(N,bool);reasons=np.repeat('',N).astype(object)
for asset,g in d.groupby('asset'):
 p=ROOT/f'data/raw/intraday/{asset}_1m.csv.gz';source_hashes[str(p.relative_to(ROOT))]=sha(p)
 raw=pd.read_csv(p,index_col=0,parse_dates=True).sort_index();assert raw.index.is_unique
 for i,r in g.iterrows():
  history=raw.loc[r.entry_time-pd.Timedelta(minutes=3000):r.entry_time-pd.Timedelta(minutes=1)]
  observation=raw.loc[r.entry_time:r.entry_time+pd.Timedelta(minutes=29)]
  if not history.index.equals(pd.date_range(r.entry_time-pd.Timedelta(minutes=3000),periods=3000,freq='min')):reasons[i]='history_grid';continue
  if not observation.index.equals(pd.date_range(r.entry_time,periods=30,freq='min')):reasons[i]='observation_grid';continue
  h=history.volume.to_numpy(float);v=observation.volume.to_numpy(float)
  if not(np.isfinite(h).all() and np.isfinite(v).all() and (h>=0).all() and (v>=0).all()):reasons[i]='invalid_volume';continue
  m=np.median(h.reshape(100,30).sum(1))
  if m<=0:reasons[i]='nonpositive_median';continue
  ohlc=observation[['open','high','low','close']].to_numpy(float)
  if not(np.isfinite(ohlc).all() and (ohlc>0).all() and (ohlc[:,1]>=np.maximum.reduce([ohlc[:,0],ohlc[:,2],ohlc[:,3]])).all() and (ohlc[:,2]<=np.minimum.reduce([ohlc[:,0],ohlc[:,1],ohlc[:,3]])).all()):reasons[i]='invalid_observation_ohlc';continue
  assert np.allclose(ohlc,paths[i,1:31],atol=1e-8,rtol=0)
  volume[i]=v.sum()/m;reference[i]=m;available[i]=True
O=paths[:,1,0];H=paths[:,1:31,1].max(1);L=paths[:,1:31,2].min(1);C=paths[:,30,3];risk=O*d.atr14_pct.to_numpy()/100
geometries=np.stack([(O-L>=.5*risk)&(C>=(H+L)/2),(H-O>=.5*risk)&(C<=(H+L)/2),(O-C>=.5*risk),(C-O>=.5*risk)])
volgates=np.stack([volume>=1.5,volume>=1.5,volume<=.75,volume<=.75]);sides=[1,-1,1,-1];ai=np.stack([d.action.eq('short'),d.action.eq('long'),d.action.eq('short'),d.action.eq('long')])
long_return=100*(paths[:,150,3]-paths[:,31,0])/paths[:,31,0]
names=[];masks=[];raw=[]
for j in range(4):
 for label,mask in [('candidate',ai[j]&geometries[j]&volgates[j]),('price_only',geometries[j]&volgates[j]),('no_volume',ai[j]&geometries[j])]:
  names.append(f'{j+1}_{label}');masks.append(available&mask);raw.append(sides[j]*long_return)
for sign,label,mask in [(1,'long',d.action.eq('short').to_numpy()),(-1,'short',d.action.eq('long').to_numpy())]:names.append('AI_only_'+label);masks.append(available&mask);raw.append(sign*long_return)
masks=np.array(masks);raw=np.array(raw);opportunity=np.where(masks,raw,0)
features=pd.DataFrame({'window_id':d.window_id,'entry_time':d.entry_time,'asset':d.asset,'available':available,'exclusion_reason':reasons,'volume_ratio':volume,'volume_reference_median':reference,'open':O,'high':H,'low':L,'close':C,'risk_distance':risk,'entry_price':paths[:,31,0],'exit_price':paths[:,150,3],'long_gross_pct':long_return})
features.to_csv(HERE/'volume_reference_features.csv',index=False)
np.savez_compressed(HERE/'volume_reference_vectors.npz',name=np.array(names),selected=masks,gross_pct=raw,opportunity_pct=opportunity,window_id=d.window_id.to_numpy(str),available=available)
assert all(sha(ROOT/p)==h for p,h in source_hashes.items())
budget=json.loads((ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json').read_text());assert len(budget['reserved_attempts'])==771
result={'status':'independent_reference_ready','created_at':datetime.now(timezone.utc).isoformat(),'valid_windows':int(available.sum()),'excluded_windows':int((~available).sum()),'source_sha256':source_hashes,'policies':[{'reference_name':name,'selected':int(mask.sum()),'mean_gross_pct':float(value[mask].mean()) if mask.any() else None} for name,mask,value in zip(names,masks,raw)],'physical_calls':771,'new_model_calls':0}
(HERE/'volume_reference.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
