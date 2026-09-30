from pathlib import Path
import sys,json,hashlib,time
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'src'))
from nai.intraday import load_intraday
from nai.backtest import _scan_bracket

def clean(x):
 if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
 if isinstance(x,(np.integer,)):return int(x)
 if isinstance(x,(np.bool_,)):return bool(x)
 if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
 return x

def score(path,sign,stop,tp,horizon,delay=0):
 # Normalized percentages from entry; unlike repo resolver adverse ambiguity is scored.
 if delay:
  entry=path['o_real'][delay]
  oo=(path['o_real'][delay:]/entry-1)*100
  hh=(path['h_real'][delay:]/entry-1)*100
  ll=(path['l_real'][delay:]/entry-1)*100
  cc=(path['c_real'][delay:]/entry-1)*100
  horizon-=delay
 else:oo,hh,ll,cc=path['o'],path['h'],path['l'],path['c']
 if horizon<=0 or len(cc)<horizon:return (np.nan,0,0,0,'missing')
 if stop==0:return (float(sign*cc[horizon-1]),horizon,0,0,'timeout')
 favorable=hh[:horizon] if sign>0 else -ll[:horizon]
 adverse=ll[:horizon] if sign>0 else -hh[:horizon]
 hits=np.flatnonzero((favorable>=tp)|(adverse<=-stop))
 if not len(hits):return (float(sign*cc[horizon-1]),horizon,0,0,'timeout')
 j=int(hits[0]); op=sign*oo[j]
 if op<=-stop:return (float(op),j+1,0,1,'sl_gap')
 if op>=tp:return (float(tp),j+1,0,1,'tp_gap_capped')
 hs=adverse[j]<=-stop;ht=favorable[j]>=tp
 if hs:return (-float(stop),j+1,int(ht),0,'sl_ambiguous' if ht else 'sl')
 return (float(tp),j+1,0,0,'tp')

def main():
 t=time.time();sources=[('original100','data/sim/decisions/rules2to1-openai-20260926T072414Z.jsonl'),('latest50','data/sim/decisions/reversal-terra50-20260929T184044Z.jsonl')]
 rows=[];hashes={}
 for batch,file in sources:
  p=ROOT/file;hashes[file]=hashlib.sha256(p.read_bytes()).hexdigest()
  for s in p.read_text().splitlines():
   r=json.loads(s)
   if 'terra' not in r['model']:continue
   r['batch']=batch;rows.append(r)
 rows.sort(key=lambda r:r['window_end_ts']);assert len(rows)==150 and len({r['window_id'] for r in rows})==150
 px=load_intraday('SOL-USD','1m');index=px.index.as_unit('ns');vals=px[['open','high','low','close']].to_numpy(float)
 paths=[];meta=[];maxh=4320
 for r in rows:
  ts=pd.Timestamp(r['window_end_ts'])+pd.Timedelta(minutes=15);p=int(index.searchsorted(ts));entry=vals[p-1,3]
  take=vals[p:p+maxh];tt=index[p:p+maxh].asi8
  good=np.flatnonzero(tt!=ts.value+np.arange(len(tt))*60_000_000_000)
  n=int(good[0]) if len(good) else len(take)
  take=take[:n];ret=(take/entry-1)*100
  paths.append(dict(zip(['o','h','l','c'],ret.T))|dict(zip(['o_real','h_real','l_real','c_real'],take.T)))
  assert abs(entry-r['price_real'])<1e-7
  meta.append({'window_id':r['window_id'],'case':r['case'],'entry_time':str(ts),'batch':r['batch'],'ai_action':r['action'],'reverse_sign':-1 if r['action']=='long' else 1,'above_both':max(r['ma20_now'],r['ma50_now'])<=100,'below_both':min(r['ma20_now'],r['ma50_now'])>100,'atr_pct':r['atr14_pct'],'agent_stop_pct':r['stop_pct']*100,'confidence':r['confidence'],'complete_minutes':n})
 meta=pd.DataFrame(meta);meta.to_csv(HERE/'windows.csv',index=False)
 print('loaded',len(meta),'complete4320',int((meta.complete_minutes>=4320).sum()),flush=True)
 horizons=[15,30,60,105,240,720,1440,4320]
 policies=[]
 for h in horizons:policies.append({'unit':'time','stop':0.,'ratio':0.,'horizon':h})
 for unit,stops in [('fixed',[.35,.5,.75,1,1.5,2]),('atr',[.5,.75,1,1.5,2,3]),('agent',[.5,.75,1,1.5,2])]:
  for s in stops:
   for rr in [.5,.75,1,1.5,2,3]:
    for h in horizons:policies.append({'unit':unit,'stop':s,'ratio':rr,'horizon':h})
 assert len(policies)==824
 P=len(policies);W=len(meta);gross=np.full((P,W,2),np.nan);held=np.zeros((P,W,2),np.int32);amb=np.zeros((P,W,2),np.int8);gap=amb.copy()
 for pi,policy in enumerate(policies):
  policy['policy_id']=pi
  for wi,path in enumerate(paths):
   s=policy['stop']*({'time':0,'fixed':1,'atr':meta.iloc[wi].atr_pct,'agent':meta.iloc[wi].agent_stop_pct}[policy['unit']]);tp=s*policy['ratio']
   for di,sign in enumerate([1,-1]):
    a,b,c,d,_=score(path,sign,s,tp,policy['horizon']);gross[pi,wi,di]=a;held[pi,wi,di]=b;amb[pi,wi,di]=c;gap[pi,wi,di]=d
  if pi%100==0:print('policy',pi,'seconds',round(time.time()-t,1),flush=True)
 np.savez_compressed(HERE/'all_trade_results.npz',gross_pct=gross,held_minutes=held,ambiguous=amb,gap=gap)
 (HERE/'policies.json').write_text(json.dumps(policies,indent=2)+'\n')
 # Consistency audit against original resolver on fixed and ATR policy samples.
 checks=0;differences=0
 for pi in np.random.default_rng(629).choice(P,40,replace=False):
  pol=policies[pi]
  if pol['unit']=='time':continue
  for wi in np.random.default_rng(int(pi)+2026).choice(W,10,replace=False):
   if meta.iloc[wi].complete_minutes<pol['horizon']:continue
   path=paths[wi];s=pol['stop']*({'fixed':1,'atr':meta.iloc[wi].atr_pct,'agent':meta.iloc[wi].agent_stop_pct}[pol['unit']])/100
   e=1.;a=[np.r_[e,path[k]/100+1] for k in ['o','h','l','c']]
   for di,sign in enumerate([1,-1]):
    outcome,ex,*_=_scan_bracket(*a,0,sign,s,s*pol['ratio'],pol['horizon'])
    ours=gross[pi,wi,di];checks+=1
    if outcome=='ambiguous':assert abs(ours+s*100)<1e-8
    elif gap[pi,wi,di] and outcome=='tp':assert ours<=sign*(ex-1)*100+1e-8
    else:assert abs(ours-sign*(ex-1)*100)<1e-8,(pi,wi,sign,outcome,ours,ex)
 masks={'all':np.ones(W,bool),'above_both':meta.above_both.to_numpy(),'below_both':meta.below_both.to_numpy()}
 dirs=(meta.reverse_sign==-1).to_numpy().astype(int)
 output=[]
 def st(x):
  x=x[np.isfinite(x)];n=len(x)
  if not n:return {'n':0}
  net=x-.2;wins=x[x>0];losses=x[x<0]
  return {'n':n,'mean_gross_pct':x.mean(),'mean_net_pct':net.mean(),'median_net_pct':np.median(net),'gross_win_rate':(x>0).mean(),'net_win_rate':(net>0).mean(),'profit_factor_net':net[net>0].sum()/-net[net<0].sum() if (net<0).any() else None,'mean_gross_win_pct':wins.mean() if len(wins) else None,'mean_gross_loss_pct':losses.mean() if len(losses) else None}
 for pi,pol in enumerate(policies):
  for gate,gm in masks.items():
   for strategy in ['reverse_all','reverse_long_to_short','reverse_short_to_long','always_long','always_short']:
    mask=gm.copy();d=dirs.copy()
    if strategy=='reverse_long_to_short':mask &= (meta.ai_action=='long').to_numpy()
    if strategy=='reverse_short_to_long':mask &= (meta.ai_action=='short').to_numpy()
    if strategy=='always_long':d[:]=0
    if strategy=='always_short':d[:]=1
    eligible=np.flatnonzero(mask & np.isfinite(gross[pi,np.arange(W),d]));x=gross[pi,eligible,d[eligible]]
    entry={'policy_id':pi,**pol,'gate':gate,'strategy':strategy,**st(x),'ambiguity_count':int(amb[pi,eligible,d[eligible]].sum()),'gap_count':int(gap[pi,eligible,d[eligible]].sum()),'mean_minutes':float(held[pi,eligible,d[eligible]].mean()) if len(eligible) else None}
    mid=len(eligible)//2
    for label,sub in [('early',eligible[:mid]),('late',eligible[mid:]),('old',eligible[meta.iloc[eligible].batch.to_numpy()=='original100']),('new',eligible[meta.iloc[eligible].batch.to_numpy()=='latest50'])]:
     z=st(gross[pi,sub,d[sub]])
     entry[label+'_n']=z['n'];entry[label+'_net']=z.get('mean_net_pct')
    output.append(entry)
 out=pd.DataFrame(output);out.to_csv(HERE/'all_trials.csv',index=False)
 (HERE/'audit.json').write_text(json.dumps(clean({'passed':True,'source_sha256':hashes,'plan_sha256':hashlib.sha256((HERE/'PLAN.md').read_bytes()).hexdigest(),'windows':W,'policies':P,'summaries':len(out),'elementary_trade_results':P*W*2,'resolver_crosschecks':checks,'complete4320':int((meta.complete_minutes>=4320).sum()),'nan_elementary_results':int(np.isnan(gross).sum()),'seconds':time.time()-t}),indent=2)+'\n')
 print(out[(out.strategy.str.startswith('reverse'))&(out.n>=20)].sort_values('mean_net_pct',ascending=False).head(30).to_string(index=False))
 # Keep a serialized compact metadata/path bundle for independent follow-up, no refetch.
 np.savez_compressed(HERE/'paths.npz',**{str(i)+'_'+k:v for i,path in enumerate(paths) for k,v in path.items()})
 print('DONE',round(time.time()-t,1),flush=True)
if __name__=='__main__':main()
