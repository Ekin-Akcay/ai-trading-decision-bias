from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;P=H.parent;ROOT=H.parents[3]
def eq(a,b):assert np.allclose(a,b,rtol=0,atol=2e-10,equal_nan=True),(a,b)
w=pd.read_csv(ROOT/'data/analysis/new-angles-20260930/target_exhaustion/windows.csv');names=[];ys=[];ms=[];families=[]
for folder,file,namekey,ykey,mkey,transpose in [('volume_reaction','vectors.npz','policies','returns','selected',False),('volume_reaction','diagnostics_vectors.npz','policies','returns','selected',False),('market_reaction','paired_vectors.npz','policy','opportunity_gross_pct','selected',True),('managed_exits','policy_vectors.npz','policy','gross_pct',None,True)]:
 z=np.load(P/folder/file);y=z[ykey].T if transpose else z[ykey];m=(z[mkey].T if transpose else z[mkey]) if mkey else np.ones_like(y,bool);assert y.shape==m.shape==(1020,len(z[namekey]));names+=z[namekey].tolist();ys.append(y);ms.append(m);families.extend([folder if file!='diagnostics_vectors.npz' else 'volume_post_score']*y.shape[1])
y=np.column_stack(ys);m=np.column_stack(ms).astype(bool);assert len(names)==44
j=np.load(P/'joint_vectors.npz');assert j['policy'].tolist()==names and np.array_equal(j['window_id'],w.window_id);eq(y,j['returns']);assert np.array_equal(m,j['selected']);assert not np.any(y[~m])
qlabel=sorted(w.quarter.unique());q=np.array([qlabel.index(x) for x in w.quarter]);Q=len(qlabel);wt=np.random.default_rng(2026093047).multinomial(Q,np.ones(Q)/Q,size=20000);assert np.array_equal(wt,j['quarter_weights']);bs=np.full((20000,44),np.nan)
for st in range(0,20000,200):rw=wt[st:st+200,q];num=rw@y;den=rw@m;bs[st:st+len(rw)]=np.divide(num,den,out=np.full_like(num,np.nan),where=den>0)
eq(bs,j['quarter_means']);result=pd.read_csv(P/'joint_results.csv');assert result.policy.tolist()==names
for k,row in result.iterrows():
 eq(y[:,k].sum()/m[:,k].sum(),row.gross_mean_pct);eq(np.nanquantile(bs[:,k],[.025,.975]),[row.quarter95_low_pct,row.quarter95_high_pct]);eq(np.nanquantile(bs[:,k],[.025/44,1-.025/44]),[row.whole_search_simultaneous_low_pct,row.whole_search_simultaneous_high_pct]);assert bool(row.positive_whole_search_interval)==bool(row.whole_search_simultaneous_low_pct>0)
keys=[hashlib.sha256(np.column_stack([y[:,k],m[:,k]]).tobytes()).hexdigest() for k in range(44)];assert len(set(keys))==43;assert not result.positive_whole_search_interval.any();budget=json.loads((ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json').read_text());assert len(budget['reserved_attempts'])==771
quiet=result[result.policy=='quiet_up_extension_short__noAI'].iloc[0]
out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'current_definitions':44,'unique_vectors':43,'family_counts':pd.Series(families).value_counts().to_dict(),'all_original_selected_and_zero_skip_vectors_match':True,'all20000_shared_quarter_resamples_match':True,'all44_means_and_family_intervals_match':True,'positive_family_adjusted_lower_bounds':0,'quiet_up_price_only_gross_mean_pct':quiet.gross_mean_pct,'quiet_up_current_family_ci_pct':[quiet.whole_search_simultaneous_low_pct,quiet.whole_search_simultaneous_high_pct],'scope_limit':'Exploratory uncertainty across these 44 current vectors only; earlier adaptive search is not erased, and no independent replication is claimed. Extreme-tail bootstrap quantiles are approximate.','physical_calls':771,'remaining_calls':29,'new_model_calls':0}
(H/'joint_final_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
