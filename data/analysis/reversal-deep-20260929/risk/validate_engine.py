"""Validate reusable engine using synthetic paths and already-seen 150 windows only."""
from pathlib import Path
import json,time,hashlib
import numpy as np
import pandas as pd
from validation_engine import bracket_batch, donor_matrix
from discover import score
H=Path(__file__).resolve().parent
m=pd.read_csv(H/'windows.csv');old=np.load(H/'paths.npz')
paths=[];reference=[]
for i in range(len(m)):
 d={k:old[str(i)+'_'+k] for k in ['o','h','l','c','o_real','h_real','l_real','c_real']}
 e=d['o_real'][0]/(1+d['o'][0]/100)
 p=np.vstack([np.full((1,4),e),np.column_stack([d[k] for k in ['o_real','h_real','l_real','c_real']])])
 paths.append(p[:1441]);reference.append(d)
paths=np.array(paths);assert paths.shape==(150,1441,4)
checks=0;maxerr=0.
for delay in [0,1,5]:
 for rr in [1,2]:
  for sgn in [-1,1]:
   stops=1.5*m.agent_stop_pct.to_numpy();out=bracket_batch(paths,stops,sign=sgn,rr=rr,delay=delay)
   for i,ref in enumerate(reference):
    a=score(ref,sgn,stops[i],stops[i]*rr,240,delay)
    err=abs(a[0]-out['gross_pct'][i]);maxerr=max(maxerr,err)
    assert err<1e-8,(i,sgn,rr,delay,a,out['gross_pct'][i])
    assert a[1]==out['held_minutes'][i]
    assert bool(a[2])==out['ambiguous'][i]
    assert bool(a[3])==out['gap'][i]
    assert a[4]==out['outcome'][i]
    checks+=1
atr=m.atr_pct.to_numpy();rat=m.agent_stop_pct.to_numpy()/atr
start=time.perf_counter();mat=donor_matrix(paths,atr,rat);seconds=time.perf_counter()-start
obs=bracket_batch(paths,1.5*m.agent_stop_pct.to_numpy())
assert np.max(abs(np.diag(mat)-obs['gross_pct']))<1e-8
rng=np.random.default_rng(629994);donor_checks=0
for _ in range(500):
 i,j=rng.integers(0,len(m),size=2);sl=1.5*atr[i]*rat[j]
 expected=score(reference[i],-1,sl,2*sl,240)[0]
 assert abs(expected-mat[i,j])<1e-8,(i,j,expected,mat[i,j]);donor_checks+=1
# Long/short symmetry, stop-first ambiguity, actual adverse gap, capped target gap,
# timeout at exact clock, and delay includes actual entry minute while skipping earlier bars.
synthetic=0
for sign in [-1,1]:
 for label,first,expected,code in [
  ('both',[100,103,97,100],-1,'sl_ambiguous'),
  ('gap_loss',[98 if sign>0 else 102,103,97,100],-2,'sl_gap'),
  ('gap_profit',[103 if sign>0 else 97,103,97,100],2,'tp_gap_capped')]:
  x=np.ones((1,8,4))*100;x[0,1]=first
  out=bracket_batch(x,1,sign=sign,rr=2,horizon=7)
  assert abs(out['gross_pct'][0]-expected)<1e-8,(sign,label,out)
  assert out['outcome'][0]==code
  assert out['exit_index'][0]==1 and out['held_minutes'][0]==1
  synthetic+=1
x=np.ones((1,8,4))*100;x[0,1]=[100,110,90,100];x[0,2]=[101,101.5,100.5,101];x[0,7]=[101,102,100,101.3]
o=bracket_batch(x,10,sign=1,rr=2,horizon=7,delay=1)
assert abs(o['gross_pct'][0]-(101.3/101-1)*100)<1e-8
assert o['entry_price'][0]==101 and o['exit_price'][0]==101.3 and o['held_minutes'][0]==6 and o['outcome'][0]=='timeout';synthetic+=1
x=np.ones((1,8,4))*100;x[0,1]=[100,101,80,100];x[0,2]=[101,101.5,98,99]
o=bracket_batch(x,1,sign=1,rr=2,horizon=7,delay=1)
assert o['outcome'][0]=='sl' and o['exit_index'][0]==2 and o['held_minutes'][0]==1;synthetic+=1
before=paths.copy();bracket_batch(paths,1);assert np.array_equal(paths,before)
result={'passed':True,'fresh_data_read':False,'old_windows':len(m),'old_scalar_replay_checks':checks,'maximum_gross_error_pct':maxerr,'donor_matrix_shape':list(mat.shape),'donor_matrix_seconds':seconds,'donor_diagonal_checks':len(m),'donor_random_scalar_checks':donor_checks,'synthetic_checks':synthetic,'inputs_not_mutated':True,'engine_sha256':hashlib.sha256((H/'validation_engine.py').read_bytes()).hexdigest()}
(H/'validation_engine_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
