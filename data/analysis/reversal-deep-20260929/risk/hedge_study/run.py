from pathlib import Path
import json,hashlib,time
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;RISK=H.parent;ROOT=RISK.parents[3];FRESH=ROOT/'data/sim/reversal-validation280-20260929T194012Z'
SOURCES=[('original100',ROOT/'data/sim/decisions/rules2to1-openai-20260926T072414Z.jsonl'),('latest50',ROOT/'data/sim/decisions/reversal-terra50-20260929T184044Z.jsonl'),('fresh280',ROOT/'data/sim/decisions/reversal-validation280-20260929T194012Z.jsonl')]

def clean(x):
 if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
 if isinstance(x,(np.integer,)):return int(x)
 if isinstance(x,(np.bool_,)):return bool(x)
 if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
 return x

def stats(gross,net,mask,times):
 ids=np.flatnonzero(mask);order=ids[np.argsort(times[ids])];x=gross[ids];y=net[ids];n=len(ids)
 if not n:return {'n':0}
 res={'n':n,'mean_gross_pct':x.mean(),'mean_net_pct':y.mean(),'median_net_pct':np.median(y),'gross_win_rate':(x>0).mean(),'net_win_rate':(y>0).mean(),'profit_factor_net':y[y>0].sum()/-y[y<0].sum() if (y<0).any() else None,'worst_net_pct':y.min(),'best_net_pct':y.max(),'net_p05_pct':np.quantile(y,.05),'net_expected_shortfall_p05_pct':np.sort(y)[:max(1,int(np.ceil(.05*n)))].mean(),'net_without_best3_pct':np.sort(y)[:-3].mean() if n>3 else None,'mean_net_per_opportunity_pct':y.sum()/len(mask)}
 for k,part in enumerate(np.array_split(order,2)):
  res[('early' if k==0 else 'late')+'_n']=len(part);res[('early' if k==0 else 'late')+'_net_pct']=net[part].mean() if len(part) else None
 for k,part in enumerate(np.array_split(order,3)):
  res[f'third{k+1}_n']=len(part);res[f'third{k+1}_net_pct']=net[part].mean() if len(part) else None
 return res

def main():
 started=time.time();rows=[];hashes={};assert (FRESH/'ALLOW_EVALUATION').exists()
 for cohort,file in SOURCES:
  hashes[str(file.relative_to(ROOT))]=hashlib.sha256(file.read_bytes()).hexdigest()
  for line in file.read_text().splitlines():
   r=json.loads(line)
   if 'terra' not in r['model']:continue
   r['cohort']=cohort;r['dataset']='fresh280' if cohort=='fresh280' else 'old150';rows.append(r)
 assert len(rows)==430 and len({r['window_id'] for r in rows})==430
 bars={}
 for asset in ['SOL','BTC']:
  for interval in ['1m','15m']:
   p=ROOT/f'data/raw/intraday/{asset}-USD_{interval}.csv.gz';d=pd.read_csv(p,index_col=0,parse_dates=True).sort_index();assert d.index.is_unique;bars[(asset,interval)]=d
 records=[];missing=[]
 for r in rows:
  t=pd.Timestamp(r['window_end_ts'])+pd.Timedelta(minutes=15);ts=t-pd.Timedelta(minutes=15)
  labels=pd.date_range(t-pd.Timedelta(minutes=1),periods=256,freq='min') # previous minute through the minute closing at original+255
  histidx=pd.date_range(ts-pd.Timedelta(minutes=15*199),periods=200,freq='15min')
  reason=[]
  for a in ['SOL','BTC']:
   if np.any(bars[(a,'1m')].index.get_indexer(labels)<0):reason.append(a+'_minute_gap')
   if np.any(bars[(a,'15m')].index.get_indexer(histidx)<0):reason.append(a+'_history_gap')
  if reason:missing.append({'window_id':r['window_id'],'dataset':r['dataset'],'reasons':reason});continue
  for a in ['SOL','BTC']:
   minute_prices=bars[(a,'1m')].loc[labels,['open','high','low','close']].to_numpy(float)
   history_prices=bars[(a,'15m')].loc[histidx,['open','high','low','close']].to_numpy(float)
   if not np.isfinite(minute_prices).all() or np.any(minute_prices<=0):reason.append(a+'_invalid_minute_OHLC')
   if not np.isfinite(history_prices).all() or np.any(history_prices<=0):reason.append(a+'_invalid_history_OHLC')
  if reason:missing.append({'window_id':r['window_id'],'dataset':r['dataset'],'reasons':reason});continue
  sr=bars[('SOL','15m')].loc[histidx,'close'].to_numpy();br=bars[('BTC','15m')].loc[histidx,'close'].to_numpy();rs=sr[1:]/sr[:-1]-1;rb=br[1:]/br[:-1]-1
  var=float(np.mean((rb-rb.mean())**2))
  if not var>0:missing.append({'window_id':r['window_id'],'dataset':r['dataset'],'reasons':['zero_BTC_return_variance']});continue
  beta=float(np.mean((rs-rs.mean())*(rb-rb.mean()))/var);clip=float(np.clip(beta,0,3));vals={}
  for a in ['SOL','BTC']:
   px=bars[(a,'1m')];entry=float(px.loc[t-pd.Timedelta(minutes=1),'close']);exit0=float(px.loc[t+pd.Timedelta(minutes=239),'close']);entry15=float(px.loc[t+pd.Timedelta(minutes=15),'open']);exit15=float(px.loc[t+pd.Timedelta(minutes=254),'close']);confirmclose=float(px.loc[t+pd.Timedelta(minutes=14),'close'])
   vals.update({a+'_entry0':entry,a+'_exit0':exit0,a+'_entry15':entry15,a+'_exit15':exit15,a+'_confirm_close':confirmclose,a+'_return0_pct':(exit0/entry-1)*100,a+'_return15_pct':(exit15/entry15-1)*100})
  assert abs(vals['SOL_entry0']-r['price_real'])<1e-8
  records.append({'window_id':r['window_id'],'case':r['case'],'dataset':r['dataset'],'cohort':r['cohort'],'entry_time':str(t),'ai_action':r['action'],'beta_ols_raw':beta,'beta_ols_clip':clip,'beta_observations':len(rs),'confirmation':vals['SOL_confirm_close']>vals['SOL_entry0'],**vals})
 W=pd.DataFrame(records);W.to_csv(H/'windows.csv',index=False);(H/'missing.json').write_text(json.dumps(missing,indent=2)+'\n')
 hedge=['zero','half','one','ols'];signals=['reverse_all','reverse_long_to_short','reverse_short_to_long','confirmed_reverse_short_to_long'];controls=['always_long','always_short','confirmed_long_no_AI'];spec=[{'policy_id':i,'signal':s,'hedge':b,'kind':'strategy'} for i,(s,b) in enumerate((s,b) for s in signals for b in hedge)];spec +=[{'policy_id':16+i,'signal':s,'hedge':b,'kind':'control'} for i,(s,b) in enumerate((s,b) for s in controls for b in hedge)]
 (H/'policies.json').write_text(json.dumps(spec,indent=2)+'\n');summ=[];output={}
 for dataset in ['old150','fresh280']:
  d=W[W.dataset==dataset].reset_index(drop=True);n=len(d);gsol=np.empty((len(spec),n));nsol=np.empty_like(gsol);gtotal=np.empty_like(gsol);ntotal=np.empty_like(gsol);masks=np.empty((len(spec),n),bool);weights=np.empty_like(gsol);allmask=np.ones(n,bool);longAI=d.ai_action.eq('long').to_numpy();confirmed=d.confirmation.to_numpy();times=d.entry_time.to_numpy()
  for p in spec:
   signal=p['signal'];key=p['hedge'];ratio=np.zeros(n) if key=='zero' else (np.full(n,.5) if key=='half' else (np.ones(n) if key=='one' else d.beta_ols_clip.to_numpy()));immediate=not signal.startswith('confirmed');rs=d.SOL_return0_pct.to_numpy() if immediate else d.SOL_return15_pct.to_numpy();rb=d.BTC_return0_pct.to_numpy() if immediate else d.BTC_return15_pct.to_numpy()
   sign=np.where(longAI,-1,1) if signal=='reverse_all' else (-1 if signal in ['reverse_long_to_short','always_short'] else 1)
   mask={'reverse_all':allmask,'reverse_long_to_short':longAI,'reverse_short_to_long':~longAI,'confirmed_reverse_short_to_long':(~longAI)&confirmed,'always_long':allmask,'always_short':allmask,'confirmed_long_no_AI':confirmed}[signal]
   gross=sign*(rs-ratio*rb);net=gross-.2*(1+ratio);i=p['policy_id'];gsol[i]=gross;nsol[i]=net;gtotal[i]=gross/(1+ratio);ntotal[i]=net/(1+ratio);masks[i]=mask;weights[i]=ratio
   for units,x,y in [('SOL_notional',gross,net),('total_gross_notional',gross/(1+ratio),net/(1+ratio))]:
    q={**p,'dataset':dataset,'units':units,**stats(x,y,mask,times),'mean_hedge_weight':ratio[mask].mean() if mask.any() else None,'fee20_pct_mean':(.2*(1+ratio[mask])).mean()/(1 if units=='SOL_notional' else 1) if mask.any() else None}
    if units=='total_gross_notional':q['fee20_pct_mean']=.2
    q['net30_mean_pct']=float((gross[mask]-.3*(1+ratio[mask])).mean()) if units=='SOL_notional' else float(((gross[mask]-.3*(1+ratio[mask]))/(1+ratio[mask])).mean())
    # Break-even one-leg roundtrip fee holding hedge weights fixed.
    q['break_even_leg_roundtrip_bps']=float(gross[mask].sum()/(1+ratio[mask]).sum()*100) if mask.any() and units=='SOL_notional' else (float((gross[mask]/(1+ratio[mask])).mean()*100) if mask.any() else None)
    summ.append(q)
  np.savez_compressed(H/f'{dataset}_payoffs.npz',gross_SOL_notional_pct=gsol,net_SOL_notional_pct=nsol,gross_total_notional_pct=gtotal,net_total_notional_pct=ntotal,active=masks,hedge_weights=weights,net_opportunity_SOL_notional_pct=np.where(masks,nsol,0),net_opportunity_total_notional_pct=np.where(masks,ntotal,0),window_ids=d.window_id.to_numpy(str),entry_times=d.entry_time.to_numpy(str),policy_ids=np.arange(len(spec)))
  output[dataset]=n
  if dataset=='fresh280':
   fullnet=np.zeros((len(spec),280));fullnorm=np.zeros_like(fullnet);fullactive=np.zeros_like(fullnet,dtype=bool)
   positions=d['case'].to_numpy(int)-1;fullnet[:,positions]=nsol;fullnorm[:,positions]=ntotal;fullactive[:,positions]=masks
   canonical=sorted([r for r in rows if r['dataset']=='fresh280'],key=lambda r:r['case'])
   assert [r['case'] for r in canonical]==list(range(1,281))
   ids=np.array([r['window_id'] for r in canonical]);labels=np.array([p['kind']+'/'+p['signal']+'/hedge='+p['hedge'] for p in spec])
   np.savez_compressed(H/'hedge_family.npz',net_per_SOL_notional_pct=fullnet,net_per_total_notional_pct=fullnorm,selected=fullactive,policy=labels,window_id=ids)
   np.savez_compressed(H/'hedge_family_all_notional_conventions.npz',net_pct=np.concatenate([fullnet,fullnorm]),selected=np.concatenate([fullactive,fullactive]),policy=np.concatenate([np.char.add(labels,'/SOL_notional'),np.char.add(labels,'/total_gross_notional')]),window_id=ids)
 out=pd.DataFrame(summ);out.to_csv(H/'all_trials.csv',index=False);old=out[out.dataset=='old150'].drop(columns='dataset');fresh=out[out.dataset=='fresh280'].drop(columns='dataset');merged=old.merge(fresh,on=['policy_id','signal','hedge','kind','units'],suffixes=('_old','_fresh'),validate='one_to_one');merged['positive_four_halves']=(merged.early_net_pct_old>0)&(merged.late_net_pct_old>0)&(merged.early_net_pct_fresh>0)&(merged.late_net_pct_fresh>0);merged.to_csv(H/'old_fresh_comparison.csv',index=False)
 print(merged[(merged.kind=='strategy')&(merged.units=='SOL_notional')][['signal','hedge','n_old','n_fresh','mean_net_pct_old','mean_net_pct_fresh','early_net_pct_old','late_net_pct_old','early_net_pct_fresh','late_net_pct_fresh','positive_four_halves']].to_string(index=False),flush=True)
 assert all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==v for f,v in hashes.items())
 audit={'stage':'explicitly_exploratory_after_primary_validation','input_windows':430,'usable_windows':output,'missing_windows':len(missing),'strategy_cells':16,'control_cells':12,'notional_conventions':2,'beta_completed_closes':200,'beta_return_pairs':199,'maximum_future_close_minutes':255,'beta_range_clipped':[0,3],'new_model_calls':0,'source_hashes_unchanged':hashes,'plan_sha256':hashlib.sha256((H/'PLAN.md').read_bytes()).hexdigest(),'positive_four_halves_strategy_SOLnotional':int(merged[(merged.kind=='strategy')&(merged.units=='SOL_notional')].positive_four_halves.sum()),'positive_four_halves_strategy_totalnotional':int(merged[(merged.kind=='strategy')&(merged.units=='total_gross_notional')].positive_four_halves.sum()),'seconds':time.time()-started}
 (H/'audit.json').write_text(json.dumps(clean(audit),indent=2)+'\n');print(json.dumps(clean(audit),indent=2))
if __name__=='__main__':main()
