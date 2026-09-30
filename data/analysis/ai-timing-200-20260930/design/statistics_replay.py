"""Independent stage statistics check; explicit root release is mandatory.
Reads only released ledger/statistics artifacts, never raw market data or unused reserve outcomes.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,math
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
def eq(a,b):assert np.allclose(a,b,rtol=0,atol=2e-10,equal_nan=True),(a,b)
def bound(x,p):
 z=np.sort(np.where(np.isfinite(x),x,-np.inf));return z[max(0,math.ceil(len(z)*p)-1)]
def decode(x):return -np.inf if x=='-Infinity' else np.inf if x=='Infinity' else x

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--released-by-root',action='store_true',required=True);parser.add_argument('--stage',choices=['screen','confirmation'],required=True);parser.add_argument('--run-dir',required=True);parser.add_argument('--evidence-dir');a=parser.parse_args()
 R=Path(a.run_dir);E=Path(a.evidence_dir) if a.evidence_dir else R;release=json.loads((E/'score_release.json').read_text());assert release['stage']==a.stage
 out=R/a.stage;w=pd.read_csv(out/'trade_ledger.csv');w.t0=pd.to_datetime(w.t0);summary=json.loads((out/'summary.json').read_text());z=np.load(out/'bootstrap_arrays.npz');assert sorted(w.case.tolist())==sorted(release['case_ids']);assert len(w.case.unique())==len(w);assert w.t0.dt.normalize().is_unique
 quarters=sorted(w.quarter.unique());q=np.array([quarters.index(t) for t in w.quarter]);weights=np.random.default_rng(2026093051).multinomial(len(quarters),np.ones(len(quarters))/len(quarters),size=40000);assert np.array_equal(weights,z['quarter_weights']) and quarters==z['quarters'].tolist();checks={}
 for direction in ['up','down']:
  rows=w[w.direction.eq(direction)].sort_values(['t0','case']);g=rows[rows.valid_coverage];s=summary['directions'].get(direction)
  if not len(rows):assert s is None;continue
  r=g.gate_gross_pct.to_numpy();AI=g.AI_aligned.to_numpy(bool);qg=np.array([quarters.index(t) for t in g.quarter]);rw=weights[:,qg];aligned_w=rw*AI[None,:];n=aligned_w.sum(1);mu=np.divide(aligned_w@r,n,out=np.full(40000,np.nan),where=n>0);oppw=rw*(~AI)[None,:];on=oppw.sum(1);omu=np.divide(oppw@r,on,out=np.full(40000,np.nan),where=on>0)
  # Direct weighted residualization of the aligned indicator within each group.
  numer=np.zeros(40000);den=np.zeros(40000);pointnum=0.;pointden=0.;mixeda=0;mixedo=0
  for _,group in g.groupby(['asset','above_equal_MA20']):
   ids=g.index.get_indexer(group.index);aa=AI[ids].astype(float);rr=r[ids];ww=rw[:,ids];nn=ww.sum(1);av=np.divide(ww@aa,nn,out=np.zeros(40000),where=nn>0);resid=aa[None,:]-av[:,None];numer+=(ww*resid)@rr;den+=(ww*resid*resid).sum(1)
   center=aa-aa.mean();pointnum+=center@rr;pointden+=center@center
   if 0<aa.sum()<len(aa):mixeda+=int(aa.sum());mixedo+=int(len(aa)-aa.sum())
  beta=np.divide(numer,den,out=np.full(40000,np.nan),where=den>1e-12);point=pointnum/pointden if pointden>1e-12 else None;assert mixeda==s['fixed_effects']['mixed_aligned_n'] and mixedo==s['fixed_effects']['mixed_opposed_n']
  for vector,key in [(mu,'aligned_mean'),(omu,'opposed_mean'),(mu-omu,'raw_aligned_minus_opposed'),(beta,'adjusted_AI_spread')]:eq(vector,z[direction+'__'+key])
  pointmean=float(r[AI].mean()) if AI.any() else None;opposedmean=float(r[~AI].mean()) if (~AI).any() else None
  if pointmean is not None:eq(pointmean,s['aligned']['mean_gross_pct'])
  if point is not None:eq(point,s['fixed_effects']['adjusted_aligned_minus_opposed_pct'])
  for values,key in [(mu,'primary_aligned_mean_interval'),(beta,'primary_adjusted_spread_interval')]:
   b=s[key];assert int((~np.isfinite(values)).sum())==b['undefined_draws'];eq(bound(values,.0125),decode(b['simultaneous98_75_one_sided_lower']));eq(bound(values,.025),decode(b['ordinary95_lower_with_undefined_as_minus_infinity']))
  screen=AI.sum()>=5 and (~AI).sum()>=5 and pointmean is not None and pointmean>0 and pointmean>opposedmean;assert bool(screen)==s['screen_pass']
  halves=[]
  for block in np.array_split(rows.case.to_numpy(),2):
   keep=g.case.isin(block).to_numpy()&AI;halves.append(float(r[keep].mean()) if keep.any() else None)
  for h,saved in zip(halves,s['chronological_halves']):
   if h is None:assert saved['mean_gross_pct'] is None
   else:eq(h,saved['mean_gross_pct'])
  wins=g[AI& (r>0)].sort_values(['gate_gross_pct','case'],ascending=[False,True]);keep=AI&~g.case.isin(wins.case.iloc[:3]).to_numpy();ex3=float(r[keep].mean()) if keep.any() else None
  if ex3 is not None:eq(ex3,s['remove_largest_winning_events']['3']['mean_gross_pct'])
  confirmed=a.stage=='confirmation' and bound(mu,.0125)>0 and bound(beta,.0125)>0 and mixeda>=10 and mixedo>=10 and all(h is not None and h>0 for h in halves) and ex3 is not None and ex3>0;assert bool(confirmed)==s['confirmed']
  checks[direction]={'gates':len(g),'aligned':int(AI.sum()),'opposed':int((~AI).sum()),'aligned_mean_pct':pointmean,'adjusted_spread_pct':point,'mixed_aligned':mixeda,'mixed_opposed':mixedo,'screen_pass':bool(screen),'confirmed':bool(confirmed)}
 if a.stage=='screen':
  cont=json.loads((out/'continuation.json').read_text());passed=[d for d in ['up','down'] if checks[d]['screen_pass']];assert cont['passing_directions']==passed;size=60 if len(passed)==2 else 120 if len(passed)==1 else 0;assert cont['cases_per_passing_direction']==size
  manifest=json.loads((R/'manifest.json').read_text());ids=[]
  for d in passed:ids.extend(c['case'] for c in manifest['cases'] if c['stage']=='confirmation' and c['direction']==d and c['confirmation_rank']<=size)
  assert sorted(ids)==cont['selected_confirmation_case_ids']
 audit={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'stage':a.stage,'released_cases':len(w),'all40000_quarter_draws_reproduced':True,'all_primary_bootstrap_vectors_reproduced_by_direct_row_weighting':True,'fixed_effects_reestimated_from_row_residuals_each_draw':True,'undefined_samples_and_order_statistic_bounds_reproduced':True,'support_concentration_halves_and_stage_gates_match':True,'directions':checks,'new_model_calls':0,'unused_reserve_outcomes_read':False};(H/(a.stage+'_statistics_audit.json')).write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
