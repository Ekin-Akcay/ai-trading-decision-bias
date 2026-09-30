from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;ROOT=H.parents[3];F=H.parent/'market_reaction'
def eq(a,b): assert np.allclose(a,b,rtol=0,atol=2e-10,equal_nan=True),(a,b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
w=pd.read_csv(F/'windows.csv');w.entry_time=pd.to_datetime(w.entry_time);N=len(w);assert N==1020
p=np.load(ROOT/'data/analysis/new-angles-20260930/target_exhaustion/paths.npz');assert np.array_equal(p['window_id'],w.window_id);p=p['paths']
v=np.load(F/'paired_vectors.npz');names=v['policy'].tolist()
# Native minute endpoints and complete BTC observation, independent of cached returns.
btc_context={};nativechecks=0
for asset,g in w.groupby('asset'):
 raw=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_1m.csv.gz',usecols=['ts','open','close']);raw.ts=pd.to_datetime(raw.ts);raw=raw.set_index('ts').sort_index();assert raw.index.is_unique
 for offset,col,truth in [(0,'open',p[g.index,1,0]),(14,'close',p[g.index,15,3]),(15,'open',p[g.index,16,0]),(134,'close',p[g.index,135,3])]:
  ids=raw.index.get_indexer(pd.DatetimeIndex(g.entry_time)+pd.Timedelta(minutes=offset));assert (ids>=0).all();eq(raw[col].to_numpy()[ids],truth);nativechecks+=len(g)
 if asset=='BTC-USD':
  for t in sorted(w.entry_time.unique()):
   ids=raw.index.get_indexer(pd.date_range(t,periods=15,freq='min'));assert (ids>=0).all();z=raw.iloc[ids][['open','close']].to_numpy();assert np.isfinite(z).all() and (z>0).all();btc_context[t]=(z[0,0],z[-1,1]);nativechecks+=30
A=100*(p[:,15,3]/p[:,1,0]-1);bc=np.array([btc_context[t] for t in w.entry_time]);B=100*(bc[:,1]/bc[:,0]-1);r=100*(p[:,135,3]/p[:,16,0]-1);old=100*(p[:,15,3]/p[:,0,3]-1)
eq(A,w.asset_15m_pct);eq(B,w.btc_15m_pct);eq(bc[:,0],w.btc_first_open);eq(bc[:,1],w.btc_close_15);eq(r,w.long_gross_pct)
E=w.asset.ne('BTC-USD').to_numpy();assert E.sum()==895 and w.btc_observation_complete.all();short=w.action.eq('short').to_numpy();long=~short
G=[(B>0)&(A<=0),(B>0)&(A>0)&(A<B),(B<0)&(A>=0),(B<0)&(A<0)&(A>B)];acts=[short,short,long,long];s=[1,1,-1,-1];m=[E&G[j]&acts[j] for j in range(4)]+[E&g for g in G];side=s+s
for sign,ai in [(1,short),(-1,long)]:
 confirm=sign*old>0
 for gate in [ai,ai&confirm,confirm,ai&(sign*B>0),np.ones(N,bool)]:m.append(E&gate);side.append(sign)
m=np.array(m);gross=np.array(side)[:,None]*r;y=np.where(m,gross,0);assert np.array_equal(m,v['selected']);eq(gross,v['gross_pct']);eq(y,v['opportunity_gross_pct']);assert np.array_equal(E,v['eligible'])
quarters=sorted(w.quarter.unique());q=np.array([quarters.index(x) for x in w.quarter]);Q=len(quarters);wt=np.random.default_rng(2026093014).multinomial(Q,np.ones(Q)/Q,size=20000);saved=np.load(F/'quarter_bootstrap.npz');assert np.array_equal(wt,saved['weights'])
bs=np.full((20000,18),np.nan);op=np.full_like(bs,np.nan)
for start in range(0,20000,200):
 rw=wt[start:start+200,q];den=rw@m.T;num=rw@y.T
 bs[start:start+len(rw)]=np.divide(num,den,out=np.full_like(num,np.nan),where=den>0);op[start:start+len(rw)]=num/(rw@E)[:,None]
def cis(a):return {key:np.nanquantile(a,lo) for key,lo in [('ci95_quarter',[.025,.975]),('ci95_family4_quarter',[.025/4,1-.025/4]),('ci95_family8_quarter',[.025/8,1-.025/8])]}
def checkcis(a,out):
 for k,z in cis(a).items():eq(z,out[k])
res=json.loads((F/'results.json').read_text());assert len(res)==18
for j,x in enumerate(res):
 z=x['all'];take=m[j];ret=gross[j,take];assert len(ret)==z['n'] and w.entry_time[take].nunique()==z['unique_entry_time_blocks'];eq(ret.mean(),z['mean_gross_pct']);eq(y[j].sum()/E.sum(),z['gross_per_opportunity_pct']);checkcis(bs[:,j],z['trade_mean_intervals']);checkcis(op[:,j],z['opportunity_mean_intervals'])
 blocks=pd.DataFrame({'t':w.entry_time,'p':y[j],'n':take}).groupby('t').sum();rank=blocks[blocks.n>0].sort_values('p',ascending=False)
 for k in [1,3]:keep=take&~w.entry_time.isin(rank.index[:k]).to_numpy();eq(gross[j,keep].mean(),z[f'exclude_best_block{k}_mean_pct'])
 for half in z['common_calendar_halves']:eq(gross[j,take&w.common_half.eq(half['half']).to_numpy()].mean(),half['mean_pct'])
# Conditional means are rebuilt with the SAME resampled quarters inside every stratum.
matched=[]
for j in range(4):
 allowed=E&G[j];groups=list(w[allowed].groupby(['cohort','asset','year']).groups.values());expected=np.full(N,np.nan);null_num=np.zeros(20000)
 for group in groups:
  ids=np.array(group);sel=ids[m[j,ids]];expected[ids]=gross[j,ids].mean();a=np.zeros(Q);b=np.zeros(Q);c=np.zeros(Q)
  for k in ids:a[q[k]]+=gross[j,k];b[q[k]]+=1
  for k in sel:c[q[k]]+=1
  d=wt@b;mean=np.divide(wt@a,d,out=np.zeros(20000),where=d>0);null_num+=mean*(wt@c)
 den=wt@np.bincount(q,weights=m[j],minlength=Q);obs=wt@np.bincount(q,weights=y[j],minlength=Q);delta=np.divide(obs-null_num,den,out=np.full(20000,np.nan),where=den>0)
 eq(gross[j]-expected,v['matched_price_increment_pct'][j]);z=res[j]['AI_increment_vs_composition_matched_price'];eq((gross[j]-expected)[m[j]].mean(),z['mean_pct']);checkcis(delta,z);matched.append(float(z['mean_pct']))
comp=json.loads((F/'comparisons.json').read_text());assert len(comp)==24
for c in comp:
 a=names.index(c['candidate']);b=names.index(c['control']);eq((y[a]-y[b])[E].mean(),c['paired_per_opportunity_difference_pct']);checkcis(op[:,a]-op[:,b],c['paired_per_opportunity_intervals']);eq(gross[a,m[a]].mean()-gross[b,m[b]].mean(),c['trade_mean_difference_pct']);checkcis(bs[:,a]-bs[:,b],c['trade_mean_difference_intervals'])
ledger=pd.read_csv(F/'all_trades_and_skips.csv.gz');assert len(ledger)==N*18
for j,name in enumerate(names):
 z=ledger[ledger.policy==name].reset_index(drop=True);assert np.array_equal(z.window_id,w.window_id) and np.array_equal(z.selected,m[j]);eq(z.hypothetical_gross_pct,gross[j]);eq(z.opportunity_gross_pct,y[j]);eq(z.entry_price,p[:,16,0]);eq(z.exit_price,p[:,135,3]);assert (pd.to_datetime(z.entry_time)==w.entry_time+pd.Timedelta(minutes=15)).all();assert (pd.to_datetime(z.exit_close_time)==w.entry_time+pd.Timedelta(minutes=135)).all()
a=json.loads((F/'audit.json').read_text());assert all(sha(ROOT/k)==h for k,h in a['source_sha256'].items());budget=json.loads((ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json').read_text());assert len(budget['reserved_attempts'])==771
gates=json.loads((F/'CANDIDATE_GATE.json').read_text())['gates'];assert all(not x['passes_gross_research_screen'] for x in gates) and all(res[j]['all']['mean_gross_pct']<0 for j in range(8))
out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'native_minute_endpoint_and_context_values_checked':nativechecks,'all18_masks_payoffs_and_ledger_clocks_match':True,'all20000_quarter_draws_and_intervals_match':True,'all4_reestimated_composition_baselines_match':True,'all24_control_comparisons_match':True,'eligible_opportunities':895,'eligible_time_blocks':int(w.entry_time[E].nunique()),'first8_gross_means_pct':[res[j]['all']['mean_gross_pct'] for j in range(8)],'candidate_matched_AI_increments_pp':matched,'candidate_or_direct_price_screen_passes':0,'source_hashes_preserved':True,'physical_calls':771,'remaining_calls':29,'new_model_calls':0}
(H/'market_reaction_final_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
