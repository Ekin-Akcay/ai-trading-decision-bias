from pathlib import Path
import json
import numpy as np
import pandas as pd
from discover import score,clean
HERE=Path(__file__).resolve().parent
trials=pd.read_csv(HERE/'all_trials.csv');m=pd.read_csv(HERE/'windows.csv');policies=json.loads((HERE/'policies.json').read_text());pp=np.load(HERE/'paths.npz');g=np.load(HERE/'all_trade_results.npz')['gross_pct'];paths=[{k:pp[str(i)+'_'+k] for k in ['o','h','l','c','o_real','h_real','l_real','c_real']} for i in range(len(m))]
# Candidate choices are discovery decisions: highest stable short-horizon AI-stop policy,
# plus the simpler ATR 1:1 policy with all the same stability checks and short horizon.
choices=[764,508]
result=[];candidate_trades=[]
for pid in choices:
 row=trials[(trials.policy_id==pid)&(trials.gate=='all')&(trials.strategy=='reverse_long_to_short')].iloc[0];p=policies[pid];sub=trials[(trials.unit==p['unit'])&(trials.gate=='all')&(trials.strategy=='reverse_long_to_short')]
 # Immediate axial neighbors in the originally declared ordered grids; self excluded.
 vals={k:sorted(sub[k].unique()) for k in ['stop','ratio','horizon']};ns=[]
 for k in vals:
  vi=vals[k].index(p[k])
  for adj in [vi-1,vi+1]:
   if 0<=adj<len(vals[k]):
    q=sub.copy()
    for kk in vals:q=q[q[kk]==(vals[k][adj] if kk==k else p[kk])]
    assert len(q)==1;ns.append(q.iloc[0].to_dict())
 mask=m.ai_action.eq('long').to_numpy();idx=np.flatnonzero(mask);sensitivity=[]
 for delay in [0,1,5]:
  vals=[];outs=[]
  for wi,path in enumerate(paths):
   stop=p['stop']*(m.iloc[wi].agent_stop_pct if p['unit']=='agent' else m.iloc[wi].atr_pct)
   out=score(path,-1,stop,stop*p['ratio'],p['horizon'],delay=delay);vals.append(out[0]);outs.append(out)
   if mask[wi]:candidate_trades.append({'policy_id':pid,'delay_minutes':delay,**m.iloc[wi].to_dict(),'gross_pct':out[0],'net20_pct':out[0]-.2,'net30_pct':out[0]-.3,'holding_minutes_after_entry':out[1],'exit_outcome':out[4]})
  vals=np.array(vals);x=vals[mask];mid=len(idx)//2
  def mean(sel):return float(vals[sel].mean()-.2) if len(sel) else None
  sensitivity.append({'delay_minutes':delay,'n':len(x),'gross_mean_pct':x.mean(),'net20_mean_pct':x.mean()-.2,'net30_mean_pct':x.mean()-.3,'gross_win_rate':(x>0).mean(),'net_win_rate':(x>.2).mean(),'earlier_net20_pct':mean(idx[:mid]),'later_net20_pct':mean(idx[mid:]),'old_net20_pct':mean(np.flatnonzero(mask&m.batch.eq('original100'))),'new_net20_pct':mean(np.flatnonzero(mask&m.batch.eq('latest50'))),'all_eligible_short_control_net20_pct':vals.mean()-.2,'above_both_short_control_net20_pct':vals[m.above_both].mean()-.2})
 result.append({'policy':p,'rule':'If Terra says long, short. No MA gate. Skip Terra shorts.','discovery_summary':row.to_dict(),'immediate_neighbors':ns,'neighbor_positive_net_count':sum(n['mean_net_pct']>0 for n in ns),'neighbor_count':len(ns),'neighbor_median_net_pct':np.median([n['mean_net_pct'] for n in ns]),'neighbor_stable_chronology_count':sum(n['early_net']>0 and n['late_net']>0 for n in ns),'sensitivity':sensitivity,'controls':trials[(trials.policy_id==pid)&trials.strategy.isin(['always_long','always_short'])].to_dict('records')})
(HERE/'candidates.json').write_text(json.dumps(clean(result),indent=2,allow_nan=False)+'\n');pd.DataFrame(candidate_trades).to_csv(HERE/'candidate_trades.csv',index=False)
# Fully retain a diagnostic ranking, even when a candidate fails a criterion.
r=trials[trials.strategy.str.startswith('reverse')&(trials.n>=20)].copy();r['stable_all_available_splits']=(r.early_net>0)&(r.late_net>0)&((r.old_n<5)|(r.old_net>0))&((r.new_n<5)|(r.new_net>0));r.sort_values(['stable_all_available_splits','mean_net_pct'],ascending=False).to_csv(HERE/'ranked_discovery.csv',index=False)
print(json.dumps(clean([{k:r[k] for k in ['policy','neighbor_positive_net_count','neighbor_count','neighbor_median_net_pct','neighbor_stable_chronology_count','sensitivity']} for r in result]),indent=2))
