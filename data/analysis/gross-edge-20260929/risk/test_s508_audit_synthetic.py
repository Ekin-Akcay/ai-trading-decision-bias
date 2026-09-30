from pathlib import Path
import json
import numpy as np,pandas as pd
from independent_s508_audit import native_scalar,bracket_batch
H=Path(__file__).resolve().parent;t=pd.Timestamp('2000-01-01 00:01:00');idx=pd.date_range(t-pd.Timedelta(minutes=1),periods=9,freq='min');checks=0
for sign in [-1,1]:
 for label,first,gross,code in [('both',[100,102,98,100],-1,'sl_ambiguous'),('gap_sl',[98 if sign>0 else 102,103,97,100],-2,'sl_gap'),('gap_tp',[102 if sign>0 else 98,103,97,100],1,'tp_gap_capped')]:
  arr=np.ones((9,4))*100;arr[0]=[100,500,1,100];arr[1]=first;px=pd.DataFrame(arr,index=idx,columns=['open','high','low','close'])
  ref=native_scalar(px,t,1,sign=sign,horizon=7);engine=bracket_batch(arr[None,:,:],1,sign=sign,rr=1,horizon=7)
  assert abs(ref['gross_pct']-gross)<1e-9 and ref['outcome']==code and ref['exit_index']==1
  for k,v in ref.items():
   if isinstance(v,(float,int)) and not isinstance(v,bool):assert abs(v-engine[k][0])<1e-9
   else:assert v==engine[k][0]
  checks+=1
# Delay skips the original entry-minute spike, enters at its actual open,
# re-centers the bracket and includes that very entry minute in scanning.
arr=np.ones((9,4))*100;arr[1]=[100,140,50,100];arr[2]=[101,101.4,98,101];px=pd.DataFrame(arr,index=idx,columns=['open','high','low','close'])
r=native_scalar(px,t,1,sign=1,delay=1,horizon=7);assert r['outcome']=='sl' and r['entry_price']==101 and r['exit_index']==2 and r['held_minutes']==1;checks+=1
arr=np.ones((9,4))*100;arr[1]=[100,140,50,100];arr[2:]=[101,101.5,100.5,101];arr[7]=[101,101.5,100.5,101.3];px=pd.DataFrame(arr,index=idx,columns=['open','high','low','close'])
r=native_scalar(px,t,10,sign=1,delay=1,horizon=7);assert r['outcome']=='timeout' and r['exit_index']==7 and r['held_minutes']==6 and abs(r['gross_pct']-(101.3/101-1)*100)<1e-9;checks+=1
# Five-minute delay and subsequent adverse gap, with unchanged deadline.
arr=np.ones((9,4))*100;arr[1:6]=[100,160,50,100];arr[6]=[102,102.2,101.8,102];arr[7]=[99,99.2,98.8,99];px=pd.DataFrame(arr,index=idx,columns=['open','high','low','close'])
r=native_scalar(px,t,1,sign=1,delay=5,horizon=7);assert r['outcome']=='sl_gap' and r['entry_price']==102 and r['exit_price']==99 and r['exit_index']==7 and r['held_minutes']==2;checks+=1
result={'passed':True,'synthetic_cases':checks,'fresh_prices_read':False,'release_not_invoked':True,'cases':['long/short both-level touches','adverse gaps','favorable gaps capped','pre-entry extremes ignored','one-minute delayed recenter and entry-minute hit','fixed-clock timeout after delay','five-minute delay followed by adverse gap']}
(H/'s508_audit_synthetic_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
