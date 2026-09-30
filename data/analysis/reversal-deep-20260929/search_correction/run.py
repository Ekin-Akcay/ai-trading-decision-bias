from pathlib import Path
import json
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;S=H.parent;N=280;B=20000
r=S/'risk/fresh_grid';rw=pd.read_csv(r/'windows.csv');pol=json.loads((r/'policies.json').read_text());ra=np.load(r/'all_trade_results.npz')['gross_pct'];rs=pd.read_csv(r/'all_trials.csv').set_index(['policy_id','gate','strategy']);cols=[];meta=[]
assert np.array_equal(rw.case,np.arange(1,N+1));times=pd.to_datetime(rw.entry_time);revdir=np.where(rw.ai_action=='long',1,0)
for j,p in enumerate(pol):
 for gate,gm in [('all',np.ones(N,bool)),('above_both',rw.above_both.to_numpy(bool)),('below_both',rw.below_both.to_numpy(bool))]:
  for strat in ['reverse_all','reverse_long_to_short','reverse_short_to_long','always_long','always_short']:
   mask=gm.copy();di=revdir.copy()
   if strat=='reverse_long_to_short':mask&=rw.ai_action.to_numpy()=='long'
   if strat=='reverse_short_to_long':mask&=rw.ai_action.to_numpy()=='short'
   if strat=='always_long':di[:]=0
   if strat=='always_short':di[:]=1
   vals=ra[j,np.arange(N),di]-.2;x=np.where(mask,vals,0.);saved=rs.loc[(p['policy_id'],gate,strat)];assert mask.sum()==saved.n
   if mask.any():assert abs(vals[mask].mean()-saved.mean_net_pct)<1e-9
   cols.append(x);meta.append({'family':'risk','policy':f"risk:{p['policy_id']}:{gate}:{strat}",'executed':int(mask.sum()),'contains_AI':strat.startswith('reverse') or p['unit']=='agent'})
sg=S/'signals/fresh_grid';sa=np.load(sg/'all_candidate_arrays.npz');assert np.array_equal(sa['window_id'],rw.window_id)
for j,c in enumerate(sa['candidate']):
 for key in ['selected','no_AI_eligible']:
  mask=sa[key][j];x=np.where(mask,sa['net20_pct'][j],0.);assert np.isfinite(x).all();cols.append(x);meta.append({'family':'signals','policy':f'signals:{c}:{key}','executed':int(mask.sum()),'contains_AI':key=='selected' or any(k in str(c) for k in ['low_conf','high_conf','stop_below_atr','stop_at_least_atr'])})
cf=pd.read_csv(S/'confirmation/fresh_grid/all_trade_policies.csv');ix={w:i for i,w in enumerate(rw.window_id)}
for p,g in cf.groupby('policy',sort=False):
 for selected in [True,False]:
  gg=g[g.ai_selected] if selected else g;x=np.zeros(N);x[[ix[v] for v in gg.window_id]]=gg.net_pct.to_numpy();cols.append(x);meta.append({'family':'confirmation','policy':f'confirmation:{p}:{"AIselected" if selected else "alltriggered"}','executed':len(gg),'contains_AI':selected or p.startswith('ai_stop')})
for family,file,labelkey in [('hedges',S/'risk/hedge_study/hedge_family_all_notional_conventions.npz','policy'),('stopout_fade',S/'signals/stopout_fade/family_vectors.npz','policylabels')]:
 a=np.load(file);assert np.array_equal(a['window_id'],rw.window_id)
 for j,label in enumerate(a[labelkey]):
  mask=a['selected'][j];vals=a['net_pct'][j];x=np.where(mask,vals,0.);assert np.isfinite(x).all();cols.append(x);meta.append({'family':family,'policy':family+':'+str(label),'executed':int(mask.sum()),'contains_AI':'control' not in str(label) or 'AI_width_control_not_AI_free' in str(label)})
X=np.column_stack(cols);assert X.shape==(N,11295),X.shape
assert np.isfinite(X).all();mu=X.mean(0);qc,ql=pd.factorize(times.dt.to_period('Q').astype(str));G=len(ql);ng=np.bincount(qc,minlength=G);sums=np.stack([X[qc==g].sum(0) for g in range(G)]);U=sums-ng[:,None]*mu
se=np.sqrt(G/(G-1)*np.sum(U*U,axis=0))/N;ok=(se>1e-12)&np.array([m['executed']>0 for m in meta]);t=np.full(len(meta),np.nan);t[ok]=mu[ok]/se[ok];V=U[:,ok]/se[ok];rng=np.random.default_rng(2026092940);draws=rng.integers(G,size=(B,G));weights=np.stack([np.bincount(d,minlength=G) for d in draws]);den=weights@ng;maxnull=np.empty(B);pointcount=np.zeros(ok.sum(),int)
for start in range(0,B,256):
 end=min(start+256,B);bt=(weights[start:end]@V)/den[start:end,None];maxnull[start:end]=bt.max(1);pointcount+=np.sum(bt>=t[ok]-1e-14,axis=0)
 if start%2048==0:print('Replicates',end,'/',B,flush=True)
padj=np.full(len(meta),np.nan);pnom=padj.copy();crit=float(np.quantile(maxnull,.95));padj[ok]=(1+np.sum(maxnull[:,None]>=t[ok][None,:]-1e-14,axis=0))/(B+1);pnom[ok]=(1+pointcount)/(B+1);lower=mu-crit*se
oldnull=np.load(H/'initial11191/family_matrix_and_null.npz')['max_t_null'];assert np.all(maxnull>=oldnull-1e-10),'Expanded-family null must include all original policies'
for i,m in enumerate(meta):
 n=m['executed'];m.update(mean_net_per_opportunity_pct=mu[i],mean_net_per_trade_pct=mu[i]*N/n if n else None,cluster_se_per_opportunity_pct=se[i],t=t[i],p_nominal_cluster=pnom[i],p_maxT_familywise=padj[i],simultaneous95_lower_opportunity_pct=lower[i] if ok[i] else None,testable=bool(ok[i]),adequate_n50=n>=50)
out=pd.DataFrame(meta);out.to_csv(H/'all_family_results.csv',index=False);np.savez_compressed(H/'family_matrix_and_null.npz',net_opportunity=X,max_t_null=maxnull,quarter_codes=qc,policies=np.array([m['policy'] for m in meta]));unique=len(np.unique(X.T,axis=0));top=out[out.testable].sort_values('t',ascending=False);top.head(50).to_csv(H/'top50.csv',index=False)
summary={'definitions':len(meta),'unique_return_vectors':unique,'windows':N,'quarters':G,'replicates':B,'seed':2026092940,'testable':int(ok.sum()),'family_counts':out.family.value_counts().to_dict(),'max_t_95critical':crit,'largest_observed_t':float(top.iloc[0].t),'global_maxT_p':float(top.iloc[0].p_maxT_familywise),'any_passing_5pct':int((out.p_maxT_familywise<.05).sum()),'any_passing_adequate_count':int(((out.p_maxT_familywise<.05)&out.adequate_n50).sum()),'top_policy':top.iloc[0].to_dict(),'stage':'retrospective exploratory reuse after primaryvalidation, not fresh confirmation'}
(H/'summary.json').write_text(json.dumps(summary,indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x),allow_nan=False)+'\n');print(json.dumps(summary,indent=2,default=str))
