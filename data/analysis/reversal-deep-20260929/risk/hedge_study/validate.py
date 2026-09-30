from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;ROOT=H.parent.parents[3];RUN=ROOT/'data/sim/reversal-validation280-20260929T194012Z'
W=pd.read_csv(H/'windows.csv');P=json.loads((H/'policies.json').read_text());bars={};checks=0;max_beta_error=0.;max_return_error=0.
for a in ['SOL','BTC']:
 for interval in ['1m','15m']:
  df=pd.read_csv(ROOT/f'data/raw/intraday/{a}-USD_{interval}.csv.gz',index_col=0,parse_dates=True).sort_index();bars[(a,interval)]=(df.index,df[['open','high','low','close']].to_numpy(float))
for _,w in W.iterrows():
 t=pd.Timestamp(w.entry_time);closes=[]
 for a in ['SOL','BTC']:
  idx,x=bars[(a,'1m')];p=int(idx.searchsorted(t));expected=pd.date_range(t-pd.Timedelta(minutes=1),periods=256,freq='min');assert idx[p-1:p+255].equals(expected)
  z=x[p-1:p+255];assert np.isfinite(z).all() and (z>0).all()
  e0=x[p-1,3];ex0=x[p+239,3];e15=x[p+15,0];ex15=x[p+254,3];confirm=x[p+14,3]
  for name,value in [('entry0',e0),('exit0',ex0),('entry15',e15),('exit15',ex15),('confirm_close',confirm),('return0_pct',(ex0-e0)/e0*100),('return15_pct',(ex15-e15)/e15*100)]:
   error=abs(value-w[a+'_'+name]);assert error<1e-8,(w.window_id,a,name,error);max_return_error=max(max_return_error,error);checks+=1
  idx15,x15=bars[(a,'15m')];j=int(idx15.searchsorted(t))-1;expect15=pd.date_range(t-pd.Timedelta(minutes=15*200),periods=200,freq='15min');assert idx15[j-199:j+1].equals(expect15)
  hist=x15[j-199:j+1];assert np.isfinite(hist).all() and (hist>0).all();closes.append(hist[:,3]);assert abs(hist[-1,3]-e0)<1e-8
  # Independent native15m exit-price alignment checks, both horizons.
  for clock,price in [(t+pd.Timedelta(minutes=225),ex0),(t+pd.Timedelta(minutes=240),ex15),(t,confirm)]:
   k=int(idx15.searchsorted(clock));assert idx15[k]==clock and abs(x15[k,3]-price)<1e-8;checks+=1
 sol=np.diff(closes[0])/closes[0][:-1];btc=np.diff(closes[1])/closes[1][:-1];coef=np.linalg.lstsq(np.column_stack([np.ones(len(btc)),btc]),sol,rcond=None)[0][1];error=abs(coef-w.beta_ols_raw);assert error<1e-9;max_beta_error=max(max_beta_error,error);assert abs(np.clip(coef,0,3)-w.beta_ols_clip)<1e-9;checks+=2
 assert bool(w.confirmation)==(w.SOL_confirm_close>w.SOL_entry0)
F=np.load(H/'hedge_family.npz');C=np.load(H/'hedge_family_all_notional_conventions.npz');assert F['net_per_SOL_notional_pct'].shape==(28,280) and C['net_pct'].shape==(56,280)
fresh=W[W.dataset=='fresh280'].sort_values('case');assert np.array_equal(F['window_id'],fresh.window_id.to_numpy(str))
for di,dataset in enumerate(['old150','fresh280']):
 d=W[W.dataset==dataset].reset_index(drop=True);a=np.load(H/f'{dataset}_payoffs.npz')
 for pol in P:
  pi=pol['policy_id'];hedge=pol['hedge'];signal=pol['signal'];ratio=np.zeros(len(d)) if hedge=='zero' else (np.full(len(d),.5) if hedge=='half' else (np.ones(len(d)) if hedge=='one' else d.beta_ols_clip.to_numpy()))
  for i,w in d.iterrows():
   immediate=not signal.startswith('confirmed');sgn=(-1 if w.ai_action=='long' else 1) if signal=='reverse_all' else (-1 if signal in ['reverse_long_to_short','always_short'] else 1)
   active={'reverse_all':True,'reverse_long_to_short':w.ai_action=='long','reverse_short_to_long':w.ai_action=='short','confirmed_reverse_short_to_long':w.ai_action=='short' and w.confirmation,'always_long':True,'always_short':True,'confirmed_long_no_AI':w.confirmation}[signal]
   sol=w.SOL_return0_pct if immediate else w.SOL_return15_pct;btc=w.BTC_return0_pct if immediate else w.BTC_return15_pct;gross=sgn*sol-sgn*ratio[i]*btc;net=gross-.2-.2*ratio[i]
   assert abs(gross-a['gross_SOL_notional_pct'][pi,i])<1e-10;assert abs(net-a['net_SOL_notional_pct'][pi,i])<1e-10;assert abs(net/(1+ratio[i])-a['net_total_notional_pct'][pi,i])<1e-10;assert active==a['active'][pi,i];checks+=4
   if dataset=='fresh280':
    assert abs(net-F['net_per_SOL_notional_pct'][pi,i])<1e-10;assert abs(net/(1+ratio[i])-F['net_per_total_notional_pct'][pi,i])<1e-10;assert active==F['selected'][pi,i];checks+=3
assert np.array_equal(C['selected'],np.vstack([F['selected'],F['selected']]))
assert np.allclose(C['net_pct'],np.vstack([F['net_per_SOL_notional_pct'],F['net_per_total_notional_pct']]))
root=[json.loads(s) for s in (RUN/'window_results.jsonl').read_text().splitlines()]
lid=[p['policy_id'] for p in P if p['signal']=='confirmed_reverse_short_to_long' and p['hedge']=='zero'][0]
for i,r in enumerate(root):assert abs(F['net_per_SOL_notional_pct'][lid,i]-r['L_net_pct'])<1e-10 and F['selected'][lid,i]==r['L_selected'];checks+=1
old=json.loads((H/'initial_audit.json').read_text());audit=json.loads((H/'audit.json').read_text());assert old['usable_windows']==audit['usable_windows'] and old['missing_windows']==audit['missing_windows']
assert all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in audit['source_hashes_unchanged'].items())
result={'passed':True,'usable_old_windows':149,'usable_fresh_windows':280,'missing_old_windows':1,'missing_reason':'SOL_history_gap for window72c5a0798c','checks':checks,'maximum_return_or_price_error':max_return_error,'maximum_OLS_slope_error':max_beta_error,'native15m_exit_checks':len(W)*2*3,'one_minute_clock_paths_verified':len(W)*2,'OLS_independent_lstsq_checks':len(W),'finite_positive_OHLC_verified':True,'hardening_did_not_change_sample':True,'root_fixedL_zerohedge_reconciles':True,'family_axis_cases_match':True,'family_all_conventions_shape':[56,280],'inputs_preserved':True}
(H/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
