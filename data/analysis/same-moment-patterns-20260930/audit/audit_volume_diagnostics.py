from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;ROOT=H.parents[3];F=H.parent/'volume_reaction'
def eq(a,b):assert np.allclose(a,b,rtol=0,atol=1e-10,equal_nan=True),(a,b)
w=pd.read_csv(F/'features.csv');w.entry_time=pd.to_datetime(w.entry_time);a=np.load(H/'volume_reference_vectors.npz');f=pd.read_csv(H/'volume_reference_features.csv');p=np.load(ROOT/'data/analysis/new-angles-20260930/target_exhaustion/paths.npz')['paths'];v=np.load(F/'vectors.npz');d=np.load(F/'diagnostics_vectors.npz');C=a['available'];up=a['selected'][10];down=a['selected'][7];assert list(v['policies'])[10]=='quiet_up_extension_short__noAI';assert list(v['policies'])[7]=='quiet_down_extension_long__noAI'
geometry=C&((f.close-f.open).to_numpy()>=.5*f.open.to_numpy()*w.atr14_pct.to_numpy()/100);short=w.action.eq('short').to_numpy();long=~short
m=np.column_stack([geometry,C,up,up,up&short,up&long,down&long]);entries=[31,31,32,36,31,31,31];exits=[150,150,151,155,150,150,150];sides=[-1,-1,-1,-1,-1,-1,1];gross=np.column_stack([s*100*(p[:,x,3]/p[:,e,0]-1) for s,e,x in zip(sides,entries,exits)]);y=np.where(m,gross,0);assert np.array_equal(m,d['selected']);eq(y,d['returns']);assert np.array_equal(C,d['coverage'])
quarters=sorted(w.quarter.unique());q=np.array([quarters.index(x) for x in w.quarter]);wt=v['quarter_weights'];bs=np.full((20000,7),np.nan);op=np.full_like(bs,np.nan)
for st in range(0,20000,200):rw=wt[st:st+200,q];num=rw@y;den=rw@m;bs[st:st+len(rw)]=np.divide(num,den,out=np.full_like(num,np.nan),where=den>0);op[st:st+len(rw)]=num/(rw@C)[:,None]
eq(bs,d['quarter_bootstrap']);eq(op,d['opportunity_bootstrap']);summary=json.loads((F/'diagnostics_summary.json').read_text());names=d['policies'].tolist();assert len(summary)==7
for j,r in enumerate(summary):
 assert r['post_score'] and r['trades']==int(m[:,j].sum());eq(gross[m[:,j],j].mean(),r['gross_mean_pct']);eq(np.nanquantile(bs[:,j],[.025,.975]),r['quarter95_ci_pct']);eq(y[:,j].sum()/C.sum(),r['opportunity_mean_pct'])
 b=pd.DataFrame({'time':w.entry_time,'p':y[:,j],'n':m[:,j]}).groupby('time').sum();top=b[b.n>0].nlargest(3,'p').index;keep=m[:,j]&~w.entry_time.isin(top).to_numpy();eq(gross[keep,j].mean(),r['without_best3_blocks_pct']);eq([gross[m[:,j]&w.half.eq(h).to_numpy(),j].mean() for h in [1,2]],r['halves'])
for c in json.loads((F/'diagnostics_comparisons.json').read_text()):
 j=names.index(c['control']);assert c['post_score'];delta=v['opportunity_bootstrap'][:,10]-op[:,j];eq((v['returns'][:,10]-y[:,j]).sum()/C.sum(),c['opportunity_difference_pp']);eq(np.nanquantile(delta,[.025,.975]),c['quarter95_ci_pp']);eq(np.nanquantile(delta,[.0125,.9875]),c['two_comparison_simultaneous_ci_pp'])
ledger=pd.read_csv(F/'diagnostics_trade_ledger.csv')
for j,name in enumerate(names):
 z=ledger[ledger.policy==name].reset_index(drop=True);assert np.array_equal(z.selected,m[:,j]) and np.array_equal(z.window_id,w.window_id);take=m[:,j];eq(z.loc[take,'gross_pct'],gross[take,j]);eq(z.loc[take,'entry_price'],p[take,entries[j],0]);eq(z.loc[take,'exit_price'],p[take,exits[j],3]);assert (pd.to_datetime(z.loc[take,'entry_time'])==w.entry_time[take]+pd.Timedelta(minutes=entries[j]-1)).all();assert (pd.to_datetime(z.loc[take,'exit_time'])==w.entry_time[take]+pd.Timedelta(minutes=exits[j])).all();assert exits[j]-(entries[j]-1)==120
budget=json.loads((ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json').read_text());assert len(budget['reserved_attempts'])==771
out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'post_score_exploration':True,'all7_masks_and_native_cached_payoffs_match':True,'all20000_conditional_and_opportunity_arrays_match':True,'all2_paired_comparisons_match':True,'all_ledger_clocks_match':'Fixed 120-minute holds from each delayed entry','trades_and_means':[{'name':r['policy'],'trades':r['trades'],'mean_gross_pct':r['gross_mean_pct'],'without_best3_blocks_pct':r['without_best3_blocks_pct']} for r in summary],'AI_SHORT_cell_is_follow_AI_after_upward_reaction':True,'promoted_as_verified':False,'physical_calls':771,'remaining_calls':29,'new_model_calls':0}
(H/'volume_diagnostics_final_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
