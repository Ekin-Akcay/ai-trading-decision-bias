from pathlib import Path
import json
import numpy as np
from engine import replay

HERE=Path(__file__).resolve().parent
def path(*rows):return np.array([[100,100,100,100],*rows],float)
checks=[]
def check(name,p,policy,expected,**fields):
    r=replay(p,1.,1,policy,horizon=len(p)-1)
    assert abs(r['gross_pct']-expected)<1e-10,(name,r)
    for k,v in fields.items():assert r[k]==v,(name,k,r[k],v)
    checks.append({'case':name,'passed':True,'gross_pct':r['gross_pct']})
    # Independent reflection around entry must preserve all strategy payoffs.
    q=p.copy();q[:,0]=200-p[:,0];q[:,1]=200-p[:,2];q[:,2]=200-p[:,1];q[:,3]=200-p[:,3]
    short=replay(q,1.,-1,policy,horizon=len(p)-1)
    assert abs(short['gross_pct']-expected)<1e-10,(name,'short mirror',short)

check('BE update cannot stop same bar',path([100,101.5,99.5,100.2],[100.2,100.8,100.05,100.5]),'BE_after_1ATR',.5,protection_armed=True,outcome='timeout')
check('BE activation adverse open actual fill',path([100,101.5,99.5,100.2],[98.5,99,98,98.8]),'BE_after_1ATR',-1.5,adverse_open_overrun_of_stop=True,final_exit_price=98.5)
check('Trail beyond completed close fills next open',path([100,102,99.5,100.5],[100.5,101,100,100.8]),'TRAIL_1ATR_after_1ATR',.5,adverse_open_overrun_of_stop=True,adverse_open_move_from_previous_close=False)
check('Partial intrabar both levels stop first',path([100,102,98,100]),'HALF_at_1ATR_then_BE',-1,partial_executed=False,ambiguous_partial_target_stop=True)
check('Partial target at open then old stop',path([100,100.5,99.5,100],[102,103,98.5,100]),'HALF_at_1ATR_then_BE',0,partial_executed=True,partial_at_open=True,ambiguous_partial_target_stop=False)
check('Partial favor gap caps half at limit',path([100,100.5,99.5,100],[103,104,100.5,102]),'HALF_at_1ATR_then_BE',1.5,partial_price=101.)
check('Partial BE effective only subsequent minute',path([100,101.5,99.5,100.4],[100.4,100.8,99.5,100.2]),'HALF_at_1ATR_then_BE',.5,final_exit_price=100.)
check('Trailing ratchet advances after completed bars',path([100,101.2,99.5,101],[101,103,100.8,102.5],[102.5,102.8,101.5,102]),'TRAIL_1ATR_after_1ATR',2,final_exit_price=102.)
check('Fixed stop does not become BE',path([100,102,99.5,100.4],[100.4,100.8,99.5,100.2]),'FIXED_1ATR_stop',.2,outcome='timeout',protection_armed=False)
check('Stop gap losses not capped',path([100,100.5,99.5,100],[97,98,96,97.5]),'FIXED_1ATR_stop',-3,final_exit_price=97.,adverse_open_overrun_of_stop=True)
check('Exact stop open is not beyond stop',path([100,100.5,99.5,100],[99,100,98,99.5]),'FIXED_1ATR_stop',-1,adverse_open_overrun_of_stop=False,exit_at_open=True)
check('Raw hold ignores stop and target',path([100,105,95,103]),'RAW_hold_240',3,outcome='timeout')
p=path([100,100,100,100],[100,101,100,100.5]);p[0]=[99,99,99,99]
check('Entry is first open not previous close',p,'RAW_hold_240',.5,entry_price=100.)
(HERE/'synthetic_audit.json').write_text(json.dumps({'passed':True,'long_cases':len(checks),'short_reflections':len(checks),'cases':checks},indent=2)+'\n')
print('PASS:',len(checks),'synthetic cases and',len(checks),'short-side reflections')
