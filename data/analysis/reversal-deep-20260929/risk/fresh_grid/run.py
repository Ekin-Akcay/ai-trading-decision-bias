from pathlib import Path
import json,sys,time,hashlib
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;RISK=H.parent;ROOT=RISK.parents[3]
sys.path.insert(0,str(RISK));from validation_engine import bracket_batch
RUN=ROOT/'data/sim/reversal-validation280-20260929T194012Z'
PALL=json.loads((RISK/'policies.json').read_text());POL=[p for p in PALL if p['horizon']<=1440]
assert len(POL)==721
clean=lambda x:float(x) if isinstance(x,np.floating) else (int(x) if isinstance(x,np.integer) else x)

def stats(values):
 x=np.asarray(values);x=x[np.isfinite(x)];n=len(x)
 if not n:return {'n':0}
 net=x-.2;w=x[x>0];l=x[x<0]
 return {'n':n,'mean_gross_pct':x.mean(),'mean_net_pct':net.mean(),'median_net_pct':np.median(net),'gross_win_rate':(x>0).mean(),'net_win_rate':(net>0).mean(),'profit_factor_net':net[net>0].sum()/-net[net<0].sum() if (net<0).any() else None,'mean_gross_win_pct':w.mean() if len(w) else None,'mean_gross_loss_pct':l.mean() if len(l) else None,'net_at30bps':x.mean()-.3,'net_without_best3':np.sort(net)[:-3].mean() if n>3 else None}

def main():
 start=time.time();assert (RUN/'ALLOW_EVALUATION').exists()
 oldfiles=['all_trade_results.npz','all_trials.csv','policies.json','windows.csv','candidates.json','FINDINGS.md']
 sourcehash={str(RISK/f):hashlib.sha256((RISK/f).read_bytes()).hexdigest() for f in oldfiles}
 M=json.loads((RUN/'manifest.json').read_text());rr=[json.loads(s) for s in (RUN/'accepted_decisions.jsonl').read_text().splitlines()];rr.sort(key=lambda r:r['case']);assert len(rr)==280
 native=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index();arr=native[['open','high','low','close']].to_numpy(float);idx=native.index
 paths=[];meta=[]
 for w,r in zip(M['cases'],rr):
  assert w['case']==r['case'];t=pd.Timestamp(w['entry_time']);i=int(idx.searchsorted(t))-1;slab=arr[i:i+1441].copy()
  assert idx[i:i+1441].equals(pd.date_range(t-pd.Timedelta(minutes=1),periods=1441,freq='min'))
  assert abs(slab[0,3]-w['price_real'])<1e-8
  paths.append(slab);meta.append({'case':w['case'],'window_id':w['window_id'],'entry_time':str(t),'ai_action':r['decision']['action'],'reverse_sign':-1 if r['decision']['action']=='long' else 1,'above_both':max(w['ma20_now'],w['ma50_now'])<=100,'below_both':min(w['ma20_now'],w['ma50_now'])>100,'ma20_now':w['ma20_now'],'ma50_now':w['ma50_now'],'atr_pct':w['atr14_pct'],'agent_stop_pct':r['decision']['stop_pct']*100})
 paths=np.array(paths);meta=pd.DataFrame(meta);N=len(meta);K=len(POL);meta.to_csv(H/'windows.csv',index=False)
 gross=np.zeros((K,N,2));held=np.zeros((K,N,2),np.int32);ambiguity=np.zeros((K,N,2),bool);gap=ambiguity.copy()
 for pi,pol in enumerate(POL):
  if pol['unit']=='time':
   v=(paths[:,pol['horizon'],3]/paths[:,0,3]-1)*100;gross[pi,:,0]=v;gross[pi,:,1]=-v;held[pi]=pol['horizon']
  else:
   scale={'fixed':np.ones(N),'atr':meta.atr_pct.to_numpy(),'agent':meta.agent_stop_pct.to_numpy()}[pol['unit']];stop=pol['stop']*scale
   for di,sign in enumerate([1,-1]):
    r=bracket_batch(paths,stop,sign=sign,rr=pol['ratio'],horizon=pol['horizon'])
    gross[pi,:,di]=r['gross_pct'];held[pi,:,di]=r['held_minutes'];ambiguity[pi,:,di]=r['ambiguous'];gap[pi,:,di]=r['gap']
  if pi%100==0:print('completed policy',pi,'of',K,'seconds',round(time.time()-start,1),flush=True)
 np.savez_compressed(H/'all_trade_results.npz',gross_pct=gross,held_minutes=held,ambiguous=ambiguity,gap=gap,original_policy_ids=np.array([p['policy_id'] for p in POL]))
 (H/'policies.json').write_text(json.dumps(POL,indent=2)+'\n')
 groups={'all':np.ones(N,bool),'above_both':meta.above_both.to_numpy(),'below_both':meta.below_both.to_numpy()};dirs=(meta.ai_action=='long').to_numpy().astype(int);summ=[]
 for pi,pol in enumerate(POL):
  for gate,gm in groups.items():
   for strategy in ['reverse_all','reverse_long_to_short','reverse_short_to_long','always_long','always_short']:
    mask=gm.copy();ds=dirs.copy()
    if strategy=='reverse_long_to_short':mask &= meta.ai_action.eq('long').to_numpy()
    if strategy=='reverse_short_to_long':mask &= meta.ai_action.eq('short').to_numpy()
    if strategy=='always_long':ds[:]=0
    if strategy=='always_short':ds[:]=1
    ids=np.flatnonzero(mask);values=gross[pi,ids,ds[ids]];order=ids[np.argsort(meta.iloc[ids].entry_time.to_numpy())];mid=len(order)//2
    r={**pol,'gate':gate,'strategy':strategy,**stats(values),'ambiguity_count':int(ambiguity[pi,ids,ds[ids]].sum()),'gap_count':int(gap[pi,ids,ds[ids]].sum()),'mean_minutes':held[pi,ids,ds[ids]].mean() if len(ids) else None,'net_per_opportunity':float((values-.2).sum()/gm.sum()) if gm.sum() else None}
    for label,sub in [('early',order[:mid]),('late',order[mid:])]:
     r[label+'_n']=len(sub);r[label+'_net']=float(gross[pi,sub,ds[sub]].mean()-.2) if len(sub) else None
    for j,sub in enumerate(np.array_split(order,3)):
     r['third'+str(j+1)+'_n']=len(sub);r['third'+str(j+1)+'_net']=float(gross[pi,sub,ds[sub]].mean()-.2) if len(sub) else None
    summ.append(r)
 fresh=pd.DataFrame(summ);fresh.to_csv(H/'all_trials.csv',index=False)
 old=pd.read_csv(RISK/'all_trials.csv');merged=old.merge(fresh,on=['policy_id','unit','stop','ratio','horizon','gate','strategy'],suffixes=('_old','_fresh'),validate='one_to_one');merged.to_csv(H/'old_fresh_comparison.csv',index=False)
 eligible=merged[(merged.n_old>=20)&(merged.n_fresh>=40)&merged.strategy.str.startswith('reverse')].copy()
 eligible['positive_old_fresh_means']=(eligible.mean_net_pct_old>0)&(eligible.mean_net_pct_fresh>0)
 eligible['positive_four_halves']=(eligible.early_net_old>0)&(eligible.late_net_old>0)&(eligible.early_net_fresh>0)&(eligible.late_net_fresh>0)
 eligible['old_batches_positive']=((eligible.old_n<5)|(eligible.old_net>0))&((eligible.new_n<5)|(eligible.new_net>0))
 eligible['fresh_thirds_positive']=(eligible.third1_net>0)&(eligible.third2_net>0)&(eligible.third3_net>0)
 eligible['minimum_half_net']=eligible[['early_net_old','late_net_old','early_net_fresh','late_net_fresh']].min(axis=1)
 eligible.sort_values(['positive_four_halves','old_batches_positive','fresh_thirds_positive','minimum_half_net','mean_net_pct_fresh'],ascending=False).to_csv(H/'ranked_candidates.csv',index=False)
 stable=eligible[eligible.positive_four_halves&eligible.old_batches_positive];stable.to_csv(H/'stable_candidates.csv',index=False)
 cols=['policy_id','unit','stop','ratio','horizon','gate','strategy','n_old','n_fresh','mean_net_pct_old','mean_net_pct_fresh','early_net_old','late_net_old','early_net_fresh','late_net_fresh','third1_net','third2_net','third3_net']
 print('STABLE',len(stable),flush=True);print(stable.sort_values('minimum_half_net',ascending=False)[cols].head(30).to_string(index=False),flush=True)
 print('TOP FRESH ANY',flush=True);print(eligible.sort_values('mean_net_pct_fresh',ascending=False)[cols].head(15).to_string(index=False),flush=True)
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in sourcehash.items())
 result={'status':'exploratory_after_primary_outcomes','new_model_calls':0,'windows':N,'max_future_minutes':1440,'policies':K,'omitted_4320min_policies':len(PALL)-K,'elementary_payoffs':K*N*2,'summary_rows':len(fresh),'eligible_reversal_cells':len(eligible),'positive_old_fresh_means':int(eligible.positive_old_fresh_means.sum()),'positive_four_halves':int(eligible.positive_four_halves.sum()),'positive_four_halves_and_old_batches':len(stable),'also_positive_fresh_thirds':int(stable.fresh_thirds_positive.sum()),'source_files_unchanged':sourcehash,'plan_sha256':hashlib.sha256((H/'PLAN.md').read_bytes()).hexdigest(),'seconds':time.time()-start}
 (H/'audit.json').write_text(json.dumps(result,indent=2,default=clean)+'\n');print(json.dumps(result,indent=2,default=clean))
if __name__=='__main__':main()
