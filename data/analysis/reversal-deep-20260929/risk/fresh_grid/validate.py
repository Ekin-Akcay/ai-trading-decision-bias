from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;R=H.parent;ROOT=R.parents[3]
sys.path.insert(0,str(R));from independent_s_check import scalar_native
A=np.load(H/'all_trade_results.npz');G=A['gross_pct'];P=json.loads((H/'policies.json').read_text());W=pd.read_csv(H/'windows.csv');raw=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index();assert G.shape==(721,280,2)
assert list(A['original_policy_ids'])==[p['policy_id'] for p in P]
rg=np.random.default_rng(2026092991);count=0;maxerror=0
for k in range(700):
 pi=int(rg.integers(len(P)));wi=int(rg.integers(len(W)));di=int(rg.integers(2));p=P[pi];w=W.iloc[wi];sgn=1 if di==0 else -1;t=pd.Timestamp(w.entry_time)
 if p['unit']=='time':
  e=float(raw.loc[t-pd.Timedelta(minutes=1),'close']);x=float(raw.loc[t+pd.Timedelta(minutes=p['horizon']-1),'close']);v=sgn*(x/e-1)*100
 else:
  stop=p['stop']*({'fixed':1,'atr':w.atr_pct,'agent':w.agent_stop_pct}[p['unit']]);r=scalar_native(raw,t,stop,sgn,p['ratio'],0,p['horizon']);v=r['gross_pct'];assert r['held_minutes']==A['held_minutes'][pi,wi,di];assert r['ambiguous']==A['ambiguous'][pi,wi,di];assert r['gap']==A['gap'][pi,wi,di]
 err=abs(v-G[pi,wi,di]);assert err<1e-8,(pi,wi,di,err);maxerror=max(maxerror,err);count+=1
roots=[json.loads(s) for s in (ROOT/'data/sim/reversal-validation280-20260929T194012Z/window_results.jsonl').read_text().splitlines()]
for pid,field in [(764,'S_gross_pct'),(508,'S_ATR2_RR1_gross_pct')]:
 pi=[p['policy_id'] for p in P].index(pid)
 for i,r in enumerate(roots):assert abs(G[pi,i,1]-r[field])<1e-8
summary=pd.read_csv(H/'all_trials.csv');checks=0
for _,s in summary.sample(250,random_state=931).iterrows():
 pi=[p['policy_id'] for p in P].index(s.policy_id);mask=np.ones(280,bool);dirs=W.ai_action.eq('long').astype(int).to_numpy().copy()
 if s.gate!='all':mask &= W[s.gate].to_numpy()
 if s.strategy=='reverse_long_to_short':mask &= W.ai_action.eq('long').to_numpy()
 if s.strategy=='reverse_short_to_long':mask &= W.ai_action.eq('short').to_numpy()
 if s.strategy=='always_long':dirs[:]=0
 if s.strategy=='always_short':dirs[:]=1
 ids=np.flatnonzero(mask);v=G[pi,ids,dirs[ids]]-.2;assert len(v)==s.n
 if len(v):assert abs(v.mean()-s.mean_net_pct)<1e-10
 checks+=1
au=json.loads((H/'audit.json').read_text());assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in au['source_files_unchanged'].items())
out={'passed':True,'scalar_native_checks':count,'maximum_error_pct':maxerror,'original_finalist_diag_perwindow_checks':560,'group_summary_checks':checks,'original_artifacts_unchanged':True,'max_future_minutes':max(p['horizon'] for p in P),'all_finite':bool(np.isfinite(G).all()),'axis_policy_ids_match':True}
(H/'validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
