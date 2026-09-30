from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'data/analysis/reversal-deep-20260929/risk'
sys.path.insert(0,str(R));from validation_engine import bracket_batch
from independent_s_check import scalar_native
from analyze import metrics
P=json.loads((R/'fresh_grid/policies.json').read_text());PID=508;POL=next(p for p in P if p['policy_id']==PID);PI=[p['policy_id'] for p in P].index(PID)
W={'old150':pd.read_csv(R/'windows.csv'),'newer280':pd.read_csv(R/'fresh_grid/windows.csv')};G={'old150':np.load(R/'all_trade_results.npz')['gross_pct'][PID],'newer280':np.load(R/'fresh_grid/all_trade_results.npz')['gross_pct'][PI]}
raw=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index();idx=raw.index;price=raw[['open','high','low','close']].to_numpy(float)
rows=[];summ=[];audit_count=0;maxerror=0.;details={}
for ds,w in W.items():
 N=len(w);times=pd.to_datetime(w.entry_time);paths=[]
 for t in times:
  p=int(idx.searchsorted(t))-1;assert idx[p:p+241].equals(pd.date_range(t-pd.Timedelta(minutes=1),periods=241,freq='min'));paths.append(price[p:p+241].copy())
 paths=np.array(paths);stop=2*w.atr_pct.to_numpy();mask=(w.above_both&w.ai_action.eq('long')).to_numpy();controls={'same_MA_gate_no_AI_short':w.above_both.to_numpy(),'all_windows_no_AI_short':np.ones(N,bool),'AI_selected':mask}
 for delay in [0,1,5]:
  out=bracket_batch(paths,stop,sign=-1,rr=1,horizon=240,delay=delay)
  for i,t in enumerate(times):
   ref=scalar_native(raw,t,stop[i],sign=-1,rr=1,delay=delay,horizon=240)
   for f in ['gross_pct','entry_price','exit_price','held_minutes','exit_index']:
    err=abs(out[f][i]-ref[f]);maxerror=max(maxerror,err);assert err<1e-8,(ds,i,delay,f,err);audit_count+=1
   for f in ['outcome','ambiguous','gap']:assert out[f][i]==ref[f];audit_count+=1
   rows.append({'dataset':ds,'delay_minutes':delay,'case':int(w.iloc[i]['case']),'window_id':w.iloc[i].window_id,'entry_time':str(t),'ai_action':w.iloc[i].ai_action,'above_both':bool(w.iloc[i].above_both),'selected':bool(mask[i]),'stop_pct_percent':stop[i],'tp_pct_percent':stop[i],'entry_price':out['entry_price'][i],'exit_price':out['exit_price'][i],'gross_pct':out['gross_pct'][i],'outcome':str(out['outcome'][i]),'held_minutes':int(out['held_minutes'][i]),'exit_index':int(out['exit_index'][i])})
  if delay==0:assert np.max(abs(out['gross_pct']-G[ds][:,1]))<1e-8
  for label,cm in controls.items():
   ids=np.flatnonzero(cm);x=out['gross_pct'][ids];result={'dataset':ds,'delay_minutes':delay,'label':label,**metrics(x,ids,w),'sample_windows':N,'frequency_all_windows':len(ids)/N,'mean_gross_per_all_opportunity_pct':x.sum()/N}
   if ds=='old150':
    for batch in ['original100','latest50']:
     bm=w.iloc[ids].batch.eq(batch).to_numpy();result[batch+'_n']=int(bm.sum());result[batch+'_gross_pct']=x[bm].mean() if bm.any() else None
   summ.append(result)
  chosen=out['gross_pct'][mask];control=out['gross_pct'][w.above_both.to_numpy()]
  print(ds,'delay',delay,'n',len(chosen),'gross',chosen.mean(),'control',control.mean(),'increment',chosen.mean()-control.mean(),flush=True)
 follow=bracket_batch(paths,stop,sign=1,rr=1,horizon=240,delay=0)
 ids=np.flatnonzero(mask);summ.append({'dataset':ds,'delay_minutes':0,'label':'follow_AI_long_same_selected_entries',**metrics(follow['gross_pct'][ids],ids,w),'sample_windows':N,'frequency_all_windows':len(ids)/N,'mean_gross_per_all_opportunity_pct':follow['gross_pct'][ids].sum()/N})
 details[ds]={'n_selected':int(mask.sum()),'sample_n':N,'MA_eligible_n':int(w.above_both.sum()),'selection_frequency_all':float(mask.mean()),'selection_frequency_within_MA_gate':float(mask.sum()/w.above_both.sum())}
S=pd.DataFrame(summ);S.to_csv(H/'candidate508_summary.csv',index=False);pd.DataFrame(rows).to_csv(H/'candidate508_window_replays.csv',index=False)
# Neighbors are unchanged immediate axial choices in the prior finite grid.
D=pd.read_csv(H/'risk_gross_old_new.csv');group=D[D.gate.eq('above_both')&D.strategy.eq('reverse_long_to_short')&D.unit.eq('atr')];neighbors=[]
for key in ['stop','ratio','horizon']:
 vals=sorted(group[key].unique());j=vals.index(POL[key])
 for jj in [j-1,j+1]:
  if not 0<=jj<len(vals):continue
  q=group.copy()
  for kk in ['stop','ratio','horizon']:q=q[q[kk]==(vals[jj] if kk==key else POL[kk])]
  assert len(q)==1;neighbors.append(q.iloc[0].to_dict())
for ds in details:
 z=S[S.dataset.eq(ds)];selected=z[z.label.eq('AI_selected')].sort_values('delay_minutes');control=z[z.label.eq('same_MA_gate_no_AI_short')].sort_values('delay_minutes');details[ds]['selected_by_delay']=selected.to_dict('records');details[ds]['matched_price_control_by_delay']=control.to_dict('records');details[ds]['AI_increment_by_delay_pp']={str(int(a.delay_minutes)):float(a.mean_gross_pct-b.mean_gross_pct) for a,b in zip(selected.itertuples(),control.itertuples())}
def clean(x):
 if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
 if isinstance(x,(np.bool_,)):return bool(x)
 if isinstance(x,(np.integer,)):return int(x)
 if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
 return x
result={'candidate_id':'S508','status':'selected_for_future_test_not_verified','fees_bps':0,'rule':'If original price is at/above both MA20 and MA50 and Terra says LONG, short. Stop and target each exactly2×pre-entry ATR14% of actual entry. Timeout240minutes after original entry. Skip other windows.','model_stop_unused':True,'geometry':POL,'datasets':details,'immediate_grid_neighbors':neighbors,'neighbors_positive_means_both_samples':sum(v['mean_gross_pct_old']>0 and v['mean_gross_pct_new']>0 for v in neighbors),'neighbor_count':len(neighbors),'new_model_calls':0,'limitations':['Existing150+280 windows are now discovery; entire gross grid was inspected','Old latest chronological third is negative; old/new halves positive do not erase that fact','AI increment versus same-MA price-only control is small in old data','No fees, funding, slippage or executable-fill claim; future validation is gross only','Root selected volatility-normalized geometry for cross-asset testing; fixed policy179 remains a secondary diagnostic only']}
(H/'CANDIDATE508.json').write_text(json.dumps(clean(result),indent=2,allow_nan=False)+'\n')
audit={'passed':True,'candidate':'S508','old_windows':150,'newer_windows':280,'native_minute_scalar_replays':430*3,'field_comparisons':audit_count,'max_numeric_error':maxerror,'primary_matches_saved_grid':True,'stop_target_recenter_on_delayed_open':True,'timeout_stays_original_plus240':True,'model_calls':0}
(H/'candidate508_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
