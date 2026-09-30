"""Independent finite-basket reconstruction; no model calls, no source mutation."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];FOLDER=HERE.parent/'relative_value';RUN=ROOT/'data/sim/gross-edge-500-20260929T204545Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def eq(a,b):assert np.allclose(a,b,atol=1e-11,rtol=0,equal_nan=True),(a,b)
summary=json.loads((FOLDER/'summary.json').read_text());archive=np.load(FOLDER/'relative_value_family.npz');boot=np.load(FOLDER/'bootstrap_arrays.npz')
source_audit=json.loads((FOLDER/'audit.json').read_text());assert all(sha(ROOT/p)==h for p,h in source_audit['source_sha256'].items())
manifest=json.loads((RUN/'manifest.json').read_text());decisions={r['case']:r['decision'] for r in map(json.loads,(RUN/'accepted_decisions.jsonl').read_text().splitlines())}
cases=pd.DataFrame(manifest['cases']);cases['entry_time']=pd.to_datetime(cases.entry_time)
for col in ['action','confidence','stop_pct']:cases[col]=[decisions[c][col] for c in cases.case]
assets=['SOL-USD','BTC-USD','ETH-USD','DOGE-USD'];blocks=cases[['block','entry_time']].drop_duplicates().sort_values('entry_time');assert len(blocks)==125
assert list(archive['block'])==list(blocks.block) and list(archive['asset'])==assets
pathcache=np.load(RUN/'paths.npz');path_lookup={w:p for w,p in zip(pathcache['window_id'],pathcache['paths'])}
returns=[];scores=[];window_ids=[]
for _,block in blocks.iterrows():
 b=cases[cases.block==block.block].set_index('asset').loc[assets];assert b.entry_time.nunique()==1
 ret=[];score=[[],[],[],[],[],[]];wid=[]
 for asset,c in b.iterrows():
  p=path_lookup[c.window_id];assert p.shape==(361,4) and np.isfinite(p).all() and (p>0).all();eq(p[0,3],c.price_real)
  ret.append(100*(p[240,3]-p[1,0])/p[1,0]);wid.append(c.window_id)
  sign=1 if c.action=='long' else -1
  values=[sign,sign*c.confidence,sign*c.confidence*c.atr14_pct/(100*c.stop_pct),c.ret_vis_pct,100*(100/c.ma20_now-1)/c.atr14_pct,c.atr14_pct]
  for j,v in enumerate(values):score[j].append(v)
 returns.append(ret);scores.append(score);window_ids.append(wid)
returns=np.array(returns);scores=np.array(scores).transpose(1,0,2);eq(returns,archive['asset_return_pct']);eq(scores,archive['scores'])
assert np.array_equal(np.array(window_ids),archive['window_id'])
weights=np.zeros((12,125,4));active=np.zeros((12,125),bool);gross=np.zeros((12,125))
for j,score in enumerate(scores):
 for b,row in enumerate(score):
  lower=min(row);upper=max(row)
  if lower==upper:continue
  buys=[i for i,x in enumerate(row) if x==lower];sells=[i for i,x in enumerate(row) if x==upper]
  for i in buys:weights[j*2,b,i]=.5/len(buys)
  for i in sells:weights[j*2,b,i]=-.5/len(sells)
  weights[j*2+1,b]=-weights[j*2,b];active[j*2:j*2+2,b]=True
for j in range(12):
 for b in range(125):gross[j,b]=sum(weights[j,b,i]*returns[b,i] for i in range(4))
eq(weights,archive['weights']);eq(gross,archive['gross_pct']);assert np.array_equal(active,archive['selected'])
eq(weights.sum(2),0);eq(np.abs(weights).sum(2),active.astype(float));eq(gross[::2],-gross[1::2])
quarter=blocks.entry_time.dt.to_period('Q').astype(str).to_numpy();ql=sorted(set(quarter));q=np.array([ql.index(x) for x in quarter]);G=len(ql)
bw=np.random.default_rng(2026093018).multinomial(125,np.full(125,1/125),size=20000)
qw=np.random.default_rng(2026093019).multinomial(G,np.full(G,1/G),size=20000)
bm=bw@gross.T/125
# Independent observation-weight computation, not group-sum matrices.
qm=np.empty_like(bm)
for start in range(0,20000,200):
 w=qw[start:start+200][:,q];qm[start:start+len(w)]=(w@gross.T)/w.sum(1)[:,None]
eq(bm,boot['block_mean']);eq(qm,boot['quarter_mean'])
policy=list(archive['policy']);folds=np.repeat(np.arange(5),25);passed=[];short_results=[]
for i,name in enumerate(policy):
 s=summary['policies'][name];r=s['summary'];x=gross[i];a=active[i];z=x[a];assert r['active']==a.sum()
 eq(x.mean(),r['mean_per_opportunity_pct']);eq(z.mean(),r['mean_per_active_pct']);eq(np.median(z),r['median_per_active_pct']);eq((z>0).mean(),r['active_win_rate'])
 eq(np.sort(z)[:-3].mean(),r['ex_best3_active_mean_pct'])
 for kind,v in [('block',bm[:,i]),('quarter',qm[:,i])]:
  eq(np.quantile(v,[.025,.975]),[r[kind+'_ci95_low'],r[kind+'_ci95_high']])
 halves=np.array_split(np.arange(125),2);loomean=min(x[q!=j].mean() for j in range(G))
 crit={'at_least40_active':a.sum()>=40,'both_halves_positive':all(x[h].mean()>0 for h in halves),
       'at_least3_later_folds_positive':sum(x[folds==j].mean()>0 for j in range(1,5))>=3,
       'later100_positive':x[25:].mean()>0,'exclude_best3_positive':np.sort(z)[:-3].mean()>0,'leave_one_quarter_out_positive':loomean>0}
 assert {k:bool(v) for k,v in crit.items()}==s['criteria'] and bool(all(crit.values()))==r['discovery_stability_screen_pass']
 if i in [0,2,4] and all(crit.values()):passed.append(name)
 short_results.append({'policy':name,'active':int(a.sum()),'opportunity_mean_pct':float(x.mean()),'block_ci95':np.quantile(bm[:,i],[.025,.975]).tolist(),'quarter_ci95':np.quantile(qm[:,i],[.025,.975]).tolist(),'stability_pass':bool(all(crit.values()))})
assert passed==summary['AI_reverse_stability_passes']
contrasts=pd.read_csv(FOLDER/'paired_price_control_differences.csv');assert len(contrasts)==18
for _,c in contrasts.iterrows():
 i=policy.index(c.AI_policy);j=policy.index(c.control_policy);delta=gross[i]-gross[j]
 eq(delta.mean(),c.difference_per_opportunity_pct);eq(np.quantile(bm[:,i]-bm[:,j],[.025,.975]),[c.block_ci95_low,c.block_ci95_high]);eq(np.quantile(qm[:,i]-qm[:,j],[.025,.975]),[c.quarter_ci95_low,c.quarter_ci95_high])
 masked=delta.copy();masked[~active[i]]=0;eq(masked.mean(),c.matched_skip_difference_per_opportunity_pct);eq(delta[active[i]].mean(),c.AI_active_only_conditional_difference_pct)
 mb=bw@masked/125;mq=np.empty(20000)
 for start in range(0,20000,200):
  w=qw[start:start+200][:,q];mq[start:start+len(w)]=w@masked/w.sum(1)
 eq(np.quantile(mb,[.025,.975]),[c.matched_skip_block_ci95_low,c.matched_skip_block_ci95_high]);eq(np.quantile(mq,[.025,.975]),[c.matched_skip_quarter_ci95_low,c.matched_skip_quarter_ci95_high])
budget=ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json';b=json.loads(budget.read_text());assert len(b['reserved_attempts'])==771
assert all(sha(ROOT/p)==h for p,h in source_audit['source_sha256'].items())
out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'blocks':125,'asset_windows':500,'reconstructed_policies':12,'scalar_basket_values':1500,'all_20000_block_and_quarter_bootstrap_arrays_match':True,'all_18_control_contrasts_reproduced':True,'all_stability_flags_reproduced':True,'reverse_candidate_count':len(passed),'source_hashes_preserved':True,'model_calls_this_audit':0,'physical_calls_still':771,'remaining_preserved':29,'budget_sha256':sha(budget),'results':short_results,'interpretation':'No reversed AI score passes its finite stability screen. Positive follow-confidence is a prespecified comparator, not an independently validated reversal strategy. All outcomes were already inspected; intervals are descriptive and not full historical search correction.'}
(HERE/'relative_value_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='results'},indent=2))
