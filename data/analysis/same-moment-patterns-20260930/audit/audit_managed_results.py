from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;ROOT=H.parents[3];F=H.parent/'managed_exits';S=ROOT/'data/analysis/new-angles-20260930/target_exhaustion'
def eq(a,b):assert np.allclose(a,b,rtol=0,atol=2e-10,equal_nan=True),(a,b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
w=pd.read_csv(S/'windows.csv');w.entry_time=pd.to_datetime(w.entry_time);p=np.load(S/'paths.npz')['paths'];v=np.load(F/'policy_vectors.npz');names=v['policy'].tolist();s=np.where(w.action.eq('short'),1,-1);N=len(w);assert N==1020
# Independent event accounting in signed percentage returns, with explicit fill list.
def reference(bars,atr,side,policy):
 entry=bars[1,0];path=side*(bars[1:241]/entry-1)*100;active=-atr;highwater=0.;unfilled=1.;fills=[];half=False;armed=False;armedbar=0;updates=0;partialbar=0;partialopen=False;amb=False;trigsame=False;overrun=False;adversemove=False
 for ix,bar in enumerate(path):
  k=ix+1;op=bar[0];fav=max(bar[1:3]);adv=min(bar[1:3]);close=bar[3];exitop=False
  if policy!='RAW_hold_240' and op<=active+1e-12:
   fills.append((unfilled,op));unfilled=0.;exitop=True;kind='stop_open';final=bars[k,0];overrun=op<active-1e-12;adversemove=side*(bars[k,0]-bars[k-1,3])<0;break
  if policy=='HALF_at_1ATR_then_BE' and not half and op>=atr-1e-12:
   fills.append((.5,atr));unfilled=.5;half=True;partialbar=k;partialopen=True
  if policy!='RAW_hold_240' and adv<=active+1e-12:
   amb=policy=='HALF_at_1ATR_then_BE' and not half and fav>=atr-1e-12;trigsame=policy in names[:3] and not armed and fav>=atr-1e-12
   fills.append((unfilled,active));unfilled=0.;kind='stop_touch';final=entry*(1+side*active/100);break
  if policy=='HALF_at_1ATR_then_BE' and not half and fav>=atr-1e-12:
   fills.append((.5,atr));unfilled=.5;half=True;partialbar=k
  highwater=max(highwater,fav)
  if k==240:
   fills.append((unfilled,close));unfilled=0.;kind='timeout';final=bars[k,3];break
  trigger=(half if policy=='HALF_at_1ATR_then_BE' else highwater>=atr-1e-12)
  if policy in names[:3] and trigger:
   if not armed:armed=True;armedbar=k
   candidate=highwater-atr if policy=='TRAIL_1ATR_after_1ATR' else 0.
   if candidate>active:active=candidate;updates+=1
 assert unfilled==0 and abs(sum(f[0] for f in fills)-1)<1e-12
 gross=sum(f*ret for f,ret in fills)
 return dict(gross_pct=gross,entry_price=entry,final_exit_price=final,weighted_equivalent_exit_price=entry*(1+side*gross/100),outcome=kind,exit_minute_index=k,exit_elapsed_upper_minutes=k-int(exitop),exit_at_open=exitop,final_active_stop_price=entry*(1+side*active/100) if policy!='RAW_hold_240' else np.nan,protection_armed=armed,armed_after_minute=armedbar,stop_updates=updates,partial_executed=half,partial_minute_index=partialbar,partial_at_open=partialopen,partial_price=entry*(1+side*atr/100) if half else np.nan,partial_elapsed_upper_minutes=partialbar-int(partialopen),partial_fraction=.5 if half else 0.,ambiguous_partial_target_stop=amb,trigger_and_stop_same_bar=trigsame,adverse_open_overrun_of_stop=overrun,adverse_open_move_from_previous_close=adversemove)
ledger=pd.read_csv(F/'trade_ledger.csv');y=np.zeros((5,N));matches=0;boundary_differences=[]
for j,name in enumerate(names):
 rows=ledger[ledger.policy==name].reset_index(drop=True);assert np.array_equal(rows.window_id,w.window_id)
 for i in range(N):
  z=reference(p[i],float(w.atr14_pct[i]),int(s[i]),name);y[j,i]=z['gross_pct'];row=rows.iloc[i]
  for key,val in z.items():
   if isinstance(val,(str,bool,np.bool_)):
    if val!=row[key]:boundary_differences.append({'row':i,'window_id':w.window_id[i],'policy':name,'field':key,'reference':str(val),'published':str(row[key])})
   else:
    try:eq(val,row[key])
    except AssertionError:boundary_differences.append({'row':i,'window_id':w.window_id[i],'policy':name,'field':key,'reference':float(val),'published':float(row[key])})
   matches+=1
 pass
(H/'managed_boundary_after_correction.json').write_text(json.dumps({'differences':boundary_differences,'max_payoff_difference_pct':float(abs(y-v['gross_pct']).max()),'differing_payoffs':np.argwhere(abs(y-v['gross_pct'])>1e-10).tolist()},indent=2)+'\n')
assert not boundary_differences,boundary_differences
eq(y,v['gross_pct'])
# Same frozen cluster draws, independent direct row-weight arithmetic.
b=np.load(F/'bootstrap_arrays.npz');ref={}
for name,groups,seed in [('block',w.entry_time,2026093041),('quarter',w.entry_time.dt.to_period('Q').astype(str),2026093042)]:
 labels=sorted(groups.unique());code=np.array([labels.index(t) for t in groups]);G=len(labels);wt=np.random.default_rng(seed).multinomial(G,np.ones(G)/G,size=20000);assert np.array_equal(wt,b[name+'_weights']);a=np.empty((20000,5))
 for start in range(0,20000,100):rw=wt[start:start+100,code];a[start:start+len(rw)]=(rw@y.T)/rw.sum(axis=1)[:,None]
 eq(a,b[name+'_means']);ref[name]=a
res=json.loads((F/'summary.json').read_text());comparisons=json.loads((F/'matched_control_differences.json').read_text());assert len(comparisons)==6
for j,name in enumerate(names):
 z=res['policies'][name];ret=y[j];po=z['pooled'];eq(ret.mean(),po['mean_gross_pct']);eq(np.sort(ret)[:-3].mean(),po['exclude_best3_mean_pct']);eq((ret>1e-12).mean(),po['win_rate']);eq(ret[ret>1e-12].sum()/-ret[ret< -1e-12].sum(),po['profit_factor'])
 for key in ['block','quarter']:eq(np.quantile(ref[key][:,j],[.025,.975]),z[key+'_ci95'])
 for side in ['long','short']:eq(ret[(s==1) if side=='long' else (s==-1)].mean(),z['position_sides'][side]['mean_gross_pct'])
 if j<3:assert not z['discovery_triage']['passed']
for c in comparisons:
 j=names.index(c['candidate']);k=names.index(c['control']);eq((y[j]-y[k]).mean(),c['all']['mean_gross_pct'])
 for key in ['block','quarter']:eq(np.quantile(ref[key][:,j]-ref[key][:,k],[.025,.975]),c[key+'_ci95'])
a=json.loads((F/'evaluation_audit.json').read_text());assert all(sha(ROOT/k)==h for k,h in a['source_sha256'].items());budget=json.loads((ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json').read_text());assert len(budget['reserved_attempts'])==771
out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'independent_percentage_space_fill_engine':True,'inclusive_contact_roundoff_tolerance_pct':1e-12,'numerical_boundary_correction_audited':True,'paths_replayed':5100,'ledger_fields_checked':matches,'all5_payoff_vectors_match':True,'all40000_block_and_quarter_draws_match':True,'all6_paired_exit_control_intervals_match':True,'means_pct':dict(zip(names,y.mean(axis=1).tolist())),'all3_candidates_lose':bool((y[:3].mean(axis=1)<0).all()),'source_hashes_preserved':True,'physical_calls':771,'remaining_calls':29,'new_model_calls':0}
(H/'managed_exits_final_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
