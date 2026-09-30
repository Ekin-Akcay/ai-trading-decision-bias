from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from discover import score
H=Path(__file__).resolve().parent;R=H.parents[3]
M=pd.read_csv(H/'windows.csv');P=json.loads((H/'policies.json').read_text());D=np.load(H/'paths.npz');G=np.load(H/'all_trade_results.npz')['gross_pct']
def reference(path,sign,sl,tp,horizon,delay):
 entry=path['o_real'][delay] if delay else path['o_real'][0]/(1+path['o'][0]/100)
 start=delay
 for j in range(start,horizon):
  op,hi,lo,cl=[path[k+'_real'][j] for k in ['o','h','l','c']]
  if not sl:continue
  sp=entry*(1-sign*sl/100);tpv=entry*(1+sign*tp/100)
  if (sign>0 and op<=sp) or (sign<0 and op>=sp):return sign*(op/entry-1)*100
  if (sign>0 and op>=tpv) or (sign<0 and op<=tpv):return tp
  hs=(lo<=sp) if sign>0 else (hi>=sp)
  ht=(hi>=tpv) if sign>0 else (lo<=tpv)
  if hs:return -sl
  if ht:return tp
 return sign*(path['c_real'][horizon-1]/entry-1)*100
rng=np.random.default_rng(62999);checks=0
for _ in range(1500):
 pi=int(rng.integers(len(P)));wi=int(rng.integers(len(M)));sgn=int(rng.choice([-1,1]));delay=int(rng.choice([0,1,5]));p=P[pi];path={k:D[str(wi)+'_'+k] for k in ['o','h','l','c','o_real','h_real','l_real','c_real']};scale={'time':0,'fixed':1,'atr':M.iloc[wi].atr_pct,'agent':M.iloc[wi].agent_stop_pct}[p['unit']];sl=scale*p['stop'];tp=sl*p['ratio']
 a=score(path,sgn,sl,tp,p['horizon'],delay)[0];b=reference(path,sgn,sl,tp,p['horizon'],delay)
 assert abs(a-b)<1e-8,(pi,wi,sgn,delay,a,b);checks+=1
 if not delay:assert abs(a-G[pi,wi,0 if sgn>0 else 1])<1e-8
# Cover adverse gaps, simultaneous touches and conservative favorable gaps explicitly.
for sgn in [1,-1]:
 for case,op,hi,lo,expected in [('both',100,102,98,-1),('gap_loss',98 if sgn>0 else 102,102,98,-2),('gap_profit',102 if sgn>0 else 98,102,98,1)]:
  p={k:np.array([v],float) for k,v in zip(['o','h','l','c'],[op-100,hi-100,lo-100,0])}
  got=score(p,sgn,1,1,1)[0];assert abs(got-expected)<1e-8,(sgn,case,got)
a=json.loads((H/'audit.json').read_text());assert all(hashlib.sha256((R/f).read_bytes()).hexdigest()==h for f,h in a['source_sha256'].items())
a.update(independent_reference_checks=checks,synthetic_gap_ambiguity_checks=6,source_files_still_unchanged=True,finite_grid_verified=True)
(H/'audit.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps(a,indent=2))
