from pathlib import Path
import sys,json,hashlib
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT/'src'))
from nai.backtest import _scan_bracket
B=10000;SEED=20260929;H=[5,15,30,60,105,240];S=[1,.75,.5,.25];COST=.2
rng=np.random.default_rng(SEED)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,x):
    if isinstance(x,pd.DataFrame):x.to_csv(HERE/(name+'.csv'),index=False);x=json.loads(x.to_json(orient='records'))
    (HERE/(name+'.json')).write_text(json.dumps(x,indent=2,allow_nan=False))
def ci(a):
    a=np.asarray(a,float);a=a[np.isfinite(a)]
    if not len(a):return [None,None]
    v=a[rng.integers(0,len(a),(B,len(a)))].mean(axis=1)
    return np.quantile(v,[.025,.975]).tolist()
def pval(a):
    a=np.asarray(a,float);a=a[np.isfinite(a)]
    v=(a*rng.choice([-1,1],(B,len(a)))).mean(axis=1)
    return float((1+(np.abs(v)>=abs(a.mean())-1e-14).sum())/(B+1))
def bh(p):
    p=np.array(p);o=np.argsort(p);s=p[o];q=np.minimum.accumulate((s*len(s)/np.arange(1,len(s)+1))[::-1])[::-1];out=np.empty(len(p));out[o]=np.minimum(q,1);return out
src=ROOT/'data/analysis/direction-paths-20260929/decisions_enriched.csv';d=pd.read_csv(src);d=d[d.main].copy();assert len(d)==1000 and d.decision_id.is_unique
raw=ROOT/'data/raw/intraday/SOLUSDT_1m.csv.gz'
# Asset names are read from canonical data rather than assumed.
raw=ROOT/f'data/raw/intraday/{d.asset.iloc[0]}_1m.csv.gz'
source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [src,raw,ROOT/'src/nai/backtest.py',ROOT/'src/nai/sim.py']}
for p in d.source_file.unique():source_hashes[p]=sha(ROOT/p)
print('Loading raw data',flush=True)
px=pd.read_csv(raw,index_col=0,parse_dates=True).sort_index();assert px.index.is_unique
arr={k:px[k].to_numpy(float) for k in ['open','high','low','close']};cached={};coverage=[]
for wid,g in d.groupby('window_id'):
    r=g.iloc[0];start=pd.Timestamp(r.window_end_ts)+pd.Timedelta(minutes=15);p=int(px.index.searchsorted(start))-1
    assert px.index[p]==start-pd.Timedelta(minutes=1)
    future=px.index[p+1:p+4321];assert len(future)==4320 and future.equals(pd.date_range(start,periods=4320,freq='min'))
    assert np.isfinite(px.iloc[p:p+4321][['open','high','low','close']].to_numpy()).all()
    assert abs(arr['close'][p]-r.price_real)<1e-8
    cached[wid]=p;coverage.append(dict(window_id=wid,complete_72h=True))
rows=[];audit=[]
for r in d.itertuples():
    p=cached[r.window_id];entry=arr['close'][p];sign=r.sign
    base={k:getattr(r,k) for k in ['decision_id','case','window_id','protocol','model','action','sign','entry_time','ma_regime','confidence','stop_pct','tp_pct']}
    def add(policy,family,kind,h,scale,direction,oc,ex,held,sl=0,tp=0):
        gross=0. if direction==0 else float(direction*(ex/entry-1)*100) if np.isfinite(ex) else np.nan
        lo=-sl*100 if oc=='ambiguous' else gross;hi=tp*100 if oc=='ambiguous' else gross;cost=COST if direction else 0
        rows.append(dict(base,policy=policy,family=family,kind=kind,horizon_minutes=h,scale=scale,effective_sign=direction,outcome=oc,minutes_held=held,gross_pct=gross,net_pct=gross-cost,gross_lower_pct=lo,gross_upper_pct=hi,net_lower_pct=lo-cost,net_upper_pct=hi-cost))
        return gross
    for scale in S:
        sl=r.stop_pct*scale;tp=r.tp_pct*scale
        for cap in [4320,15,30,105]:
            if sign:oc,ex,held,_,_=_scan_bracket(arr['open'],arr['high'],arr['low'],arr['close'],p,sign,sl,tp,cap)
            else:oc,ex,held='none',entry,0
            pol=f'bracket_{scale:g}' if cap==4320 else f'combined_{scale:g}_{cap}m';family='reference' if cap==4320 and scale==1 else 'primary' if cap==4320 else 'secondary'
            gross=add(pol,family,'bracket' if cap==4320 else 'combined',cap,scale,sign,oc,ex,held,sl,tp)
            if cap==4320 and scale==1:
                checks=dict(outcome=oc==r.outcome,minutes=int(held)==int(r.minutes_held),gross=(np.isnan(gross) and pd.isna(r.pnl_gross_pct)) or abs(gross-r.pnl_gross_pct)<1e-7,net=(np.isnan(gross) and pd.isna(r.pnl_net_pct)) or abs(gross-(COST if sign else 0)-r.pnl_net_pct)<1e-7)
                audit.append(dict(decision_id=r.decision_id,**checks));assert all(checks.values()),(r.decision_id,checks,oc,r.outcome,held,r.minutes_held,gross,r.pnl_gross_pct)
    for h in H:
        ex=arr['close'][p+h]
        for kind,s in [('time',sign),('reverse',-sign),('always_short',-1 if sign else 0),('ma20',(1 if r.above20 else -1) if sign else 0),('momentum',int(np.sign(r.ret_vis_pct)) if sign else 0)]:
            add(f'{kind}_{h}m','primary' if kind=='time' and h in [15,30,105] else 'secondary' if kind=='time' else 'benchmark',kind,h,np.nan,s,'time' if s else 'none',ex,h if s else 0)
x=pd.DataFrame(rows);x.to_csv(HERE/'per_trade_policies.csv',index=False)
print('Policies calculated',len(x),'all originals match',flush=True)
write('engine_audit',audit)
# Keep original paired values and bound cases regardless of ambiguity.
b=x[x.policy=='bracket_1'].set_index('decision_id')
x['original_net_pct']=x.decision_id.map(b.net_pct)
x['delta_net_pct']=x.net_pct-x.original_net_pct
x['delta_lower_pct']=x.net_lower_pct-x.decision_id.map(b.net_upper_pct)
x['delta_upper_pct']=x.net_upper_pct-x.decision_id.map(b.net_lower_pct)
x.to_csv(HERE/'per_trade_policies.csv',index=False)
windows=d[['window_id','entry_time']].drop_duplicates().sort_values('entry_time');windows['time_cluster']=(pd.to_datetime(windows.entry_time).diff().dt.total_seconds().fillna(999999)>72*3600).cumsum();cluster=windows.set_index('window_id').time_cluster.to_dict();half={w:'early_50' if i<50 else 'late_50' for i,w in enumerate(windows.window_id)}
x['half']=x.window_id.map(half);x['utc_session']=pd.to_datetime(x.entry_time).dt.hour.floordiv(6).map({0:'00-06 UTC',1:'06-12 UTC',2:'12-18 UTC',3:'18-24 UTC'})
summary=[]
for group,frame in [('pooled',x)]+[(str(a)+' / '+str(b),g) for (a,b),g in x.groupby(['protocol','model'])]:
    for pol,g in frame.groupby('policy',sort=False):
        # Unambiguous rows are averaged within each window; bounds retain every row.
        a=g.groupby('window_id').net_pct.mean().dropna();gross=g.groupby('window_id').gross_pct.mean().dropna()
        low,high=ci(a)
        summary.append(dict(group=group,policy=pol,family=g.family.iloc[0],kind=g.kind.iloc[0],horizon_minutes=int(g.horizon_minutes.iloc[0]),scale=g.scale.iloc[0],decisions=len(g),active=int((g.effective_sign!=0).sum()),ambiguous=int((g.outcome=='ambiguous').sum()),windows=len(a),gross_mean_pct=gross.mean(),net_mean_pct=a.mean(),net_ci_low=low,net_ci_high=high,net_all_lower_pct=g.groupby('window_id').net_lower_pct.mean().mean(),net_all_upper_pct=g.groupby('window_id').net_upper_pct.mean().mean(),median_minutes=g.loc[g.effective_sign!=0,'minutes_held'].median(),tp_count=int((g.outcome=='tp').sum()),sl_count=int((g.outcome=='sl').sum()),timeout_count=int((g.outcome=='timeout').sum())))
summary=pd.DataFrame(summary);write('policy_summary',summary)
print('Summaries computed',flush=True)
contrasts=[]
for pol,g in x[x.family.isin(['primary','secondary'])].groupby('policy'):
    z=g[g.delta_net_pct.notna()];a=z.groupby('window_id').delta_net_pct.mean();lo,hi=ci(a)
    # Temporal-cluster resample retains per-window weights within sampled blocks.
    vals=pd.DataFrame({'value':a,'cluster':[cluster[w] for w in a.index]}).groupby('cluster').value.agg(['sum','count']);ix=rng.integers(0,len(vals),(B,len(vals)));boots=vals['sum'].to_numpy()[ix].sum(axis=1)/vals['count'].to_numpy()[ix].sum(axis=1);clo,chi=np.quantile(boots,[.025,.975])
    contrasts.append(dict(policy=pol,family=g.family.iloc[0],paired_decisions=len(z),excluded_pairs=len(g)-len(z),windows=len(a),delta_net_pct=a.mean(),ci_low=lo,ci_high=hi,p=pval(a),delta_all_lower_pct=g.groupby('window_id').delta_lower_pct.mean().mean(),delta_all_upper_pct=g.groupby('window_id').delta_upper_pct.mean().mean(),cluster_ci_low=clo,cluster_ci_high=chi,clusters=len(vals)))
c=pd.DataFrame(contrasts)
for fam,ix in c.groupby('family').groups.items():c.loc[ix,'q_bh']=bh(c.loc[ix,'p'])
write('paired_vs_original',c)
bench=[]
for h in H:
    ref=x[x.policy==f'time_{h}m'].set_index('decision_id').net_pct
    for kind in ['reverse','always_short','ma20','momentum']:
        g=x[x.policy==f'{kind}_{h}m'].copy()
        if kind=='momentum':g=g[(g.effective_sign!=0) | (g.sign==0)]
        g['delta']=g.net_pct-g.decision_id.map(ref);a=g.groupby('window_id').delta.mean();lo,hi=ci(a)
        bench.append(dict(horizon_minutes=h,policy=f'{kind}_{h}m',comparison='benchmark minus AI time exit',paired_decisions=len(g),windows=len(a),delta_net_pct=a.mean(),ci_low=lo,ci_high=hi,p=pval(a)))
bt=pd.DataFrame(bench);bt['q_bh']=bh(bt.p);write('benchmark_contrasts',bt)
for key in ['half','utc_session']:
    out=[]
    for (label,pol),g in x.groupby([key,'policy']):
        a=g.groupby('window_id').net_pct.mean();out.append({key:label,'policy':pol,'windows':g.window_id.nunique(),'decisions':len(g),'ambiguous':int((g.outcome=='ambiguous').sum()),'net_mean_pct':a.mean(),'gross_mean_pct':g.groupby('window_id').gross_pct.mean().mean()})
    write(key+'_summary',pd.DataFrame(out))
# Per-protocol distributions of normalized fees and width.
width=d.assign(fee_fraction_of_stop=COST/(d.stop_pct*100)).groupby(['protocol','model']).agg(median_stop_pct=('stop_pct','median'),median_tp_pct=('tp_pct','median'),median_fee_fraction_of_stop=('fee_fraction_of_stop','median')).reset_index();write('widths',width)
assert all(sha(ROOT/p)==h for p,h in source_hashes.items())
write('audit',dict(decisions=len(d),windows=d.window_id.nunique(),policies=x.policy.nunique(),policy_rows=len(x),source_sha256=source_hashes,engine_originals_all_match=True,checks_per_original=4,coverage=coverage,round_trip_cost_pct=COST,bootstrap_resamples=B,seed=SEED,temporal_clusters=windows.time_cluster.nunique(),ambiguity_by_policy=x.groupby('policy').apply(lambda g:int((g.outcome=='ambiguous').sum()),include_groups=False).to_dict(),source_files_unchanged=True,notes=['Bootstrap unit is window; temporal-group sensitivity included.','Originals verified with exact unmodified engine.','All numeric returns are percentage points of entry, not leveraged or risk-scaled.','Ambiguous headline means exclude individual unknown outcomes; all-row SL/TP bounds shown.']))
print(c[c.family=='primary'].to_string(index=False));print(summary[(summary.group=='pooled') & summary.kind.isin(['time','bracket'])].to_string(index=False));print('DONE',flush=True)
