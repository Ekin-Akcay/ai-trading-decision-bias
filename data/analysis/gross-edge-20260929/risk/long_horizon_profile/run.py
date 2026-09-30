"""Fixed five-horizon exploratory diagnostic; no trade-model calls."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
RUN=ROOT/'data/sim/gross-edge-500-20260929T204545Z'
H=np.array([15,30,60,105,240])

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
    if isinstance(v,(np.integer,)):return int(v)
    if isinstance(v,(np.bool_,)):return bool(v)
    if isinstance(v,(np.floating,float)):return float(v) if np.isfinite(v) else None
    return v

def save(name,v):(HERE/name).write_text(json.dumps(clean(v),indent=2,allow_nan=False)+'\n')

def stats(x):
    x=np.asarray(x,float);n=len(x)
    if not n:return {'n':0}
    s=np.sort(x)
    return dict(n=n,mean_gross_pct=x.mean(),median_gross_pct=np.median(x),win_rate=(x>0).mean(),sum_gross_pct=x.sum(),
        best_pct=x.max(),worst_pct=x.min(),mean_winner_pct=x[x>0].mean() if (x>0).any() else np.nan,
        mean_loser_pct=x[x<0].mean() if (x<0).any() else np.nan,
        profit_factor=x[x>0].sum()/-x[x<0].sum() if (x<0).any() else np.nan,
        ex_best1_mean_pct=s[:-1].mean() if n>1 else np.nan,ex_best3_mean_pct=s[:-3].mean() if n>3 else np.nan,
        top3_sum_pct=s[-3:].sum(),top3_share_of_total=s[-3:].sum()/x.sum() if x.sum()!=0 else np.nan)

def infer(d,values,sel,elig,groups,seed):
    code,labels=pd.factorize(groups,sort=True);ng=len(labels)
    sc,sl=pd.factorize(d.stratum,sort=True);ns=len(sl)
    a=np.zeros((ng,ns));b=np.zeros_like(a);c=np.zeros((ng,ns,len(H)))
    np.add.at(a,(code,sc),sel.astype(float));np.add.at(b,(code,sc),elig.astype(float))
    np.add.at(c,(code,sc),np.where(elig[:,None],values,0))
    num=np.zeros((ng,len(H)));np.add.at(num,code,np.where(sel[:,None],values,0))
    rng=np.random.default_rng(seed);w=rng.multinomial(ng,np.full(ng,1/ng),size=20000)
    den=w@a.sum(1);valid=den>0
    sm=(w@num)[valid]/den[valid,None]
    sa=w@a;eb=w@b
    ebmean=np.divide(np.einsum('bg,gsh->bsh',w,c),eb[:,:,None],out=np.zeros((len(w),ns,len(H))),where=eb[:,:,None]>0)
    baseline=(sa[:,:,None]*ebmean).sum(1)[valid]/den[valid,None]
    pooled=np.divide(c.sum(0),b.sum(0)[:,None],out=np.zeros((ns,len(H))),where=b.sum(0)[:,None]>0)
    base=(a.sum(0)[:,None]*pooled).sum(0)/sel.sum()
    return dict(mean_ci95=np.quantile(sm,[.025,.975],axis=0),AI_increment_ci95=np.quantile(sm-baseline,[.025,.975],axis=0),
        standardized_baseline=base,AI_increment=values[sel].mean(0)-base,groups=ng,selected_groups=len(np.unique(code[sel])),
        strata_with_both_groups=int(((a.sum(0)>0)&(b.sum(0)>a.sum(0))).sum()))

def main():
    assert (RUN/'ALLOW_EVALUATION').exists()
    sources=[HERE/'PLAN.md',ROOT/'data/analysis/gross-edge-20260929/signals/windows.csv',RUN/'window_results.csv',RUN/'summary.json',ROOT/'data/analysis/gross-edge-20260929/signals/focus_results.json']
    old=pd.read_csv(sources[1]);old['asset']='SOL-USD';old['macro_gate']=old.both_down
    old['source_block']=old.window_id
    fresh=pd.read_csv(sources[2]);fresh['cohort']='fresh500';fresh['macro_gate']=fresh.macro_both_down;fresh['source_block']=fresh.block.astype(str)
    cols=['cohort','case','window_id','asset','entry_time','price_real','action','ma20_now','ma50_now','macro_gate','source_block']
    d=pd.concat([old[cols],fresh[cols]],ignore_index=True)
    d.entry_time=pd.to_datetime(d.entry_time);d['quarter']=d.entry_time.dt.to_period('Q').astype(str)
    d['calendar_block']=d.cohort+'|'+d.source_block
    d['era']=np.where(d.entry_time.dt.year<=2021,'2020-21',np.where(d.entry_time.dt.year<=2023,'2022-23','2024-26'))
    d['ma_regime']=np.where((d.ma20_now<=100)&(d.ma50_now<=100),'above_both',np.where((d.ma20_now>=100)&(d.ma50_now>=100),'below_both','mixed'))
    d['stratum']=d.asset+'|'+d.era+'|'+d.ma_regime
    assert len(d)==930 and d.window_id.nunique()==930 and set(d.action)=={'long','short'}
    entry=np.full(len(d),np.nan);exits=np.full((len(d),len(H)),np.nan);checks=0
    for asset in d.asset.unique():
        path=ROOT/f'data/raw/intraday/{asset}_1m.csv.gz';sources.append(path)
        px=pd.read_csv(path,index_col=0,parse_dates=True,usecols=[0,1,4]).sort_index()
        assert px.index.is_unique and list(px.columns)==['open','close']
        for i,row in d[d.asset==asset].iterrows():
            q=px.index.get_loc(row.entry_time);part=px.iloc[q-1:q+240]
            assert part.index.equals(pd.date_range(row.entry_time-pd.Timedelta(minutes=1),periods=241,freq='min'))
            a=part.to_numpy(float);assert np.isfinite(a).all() and (a>0).all()
            assert abs(a[0,1]-row.price_real)<1e-8
            entry[i]=a[1,0];exits[i]=a[H,1];checks+=1
        print('native replay complete:',asset,flush=True)
    values=(exits/entry[:,None]-1)*100
    for j,h in enumerate(H):d[f'gross_{h}_pct']=values[:,j];d[f'exit_{h}']=exits[:,j]
    d['entry_open']=entry
    d['selected_L048']=d.macro_gate & d.action.eq('short')
    d['complement_AI_long']=d.macro_gate & d.action.eq('long')
    d['control_belowMA20']=d.macro_gate & np.where(d.cohort.eq('fresh500'),d.ma20_now>=100,d.ma20_now>100)
    d.to_csv(HERE/'window_vectors.csv',index=False)
    np.savez_compressed(HERE/'window_vectors.npz',gross_pct=values,horizons=H,selected=d.selected_L048.to_numpy(),eligible=d.macro_gate.to_numpy(),window_id=d.window_id.to_numpy(str),cohort=d.cohort.to_numpy(str),asset=d.asset.to_numpy(str),calendar_block=d.calendar_block.to_numpy(str))
    # Exact original four-hour reconciliation before any profile conclusions.
    oldfocus=json.loads(sources[4].read_text())[0]
    reconciliation=[]
    for cohort in ['old150','new280','fresh500']:
        mask=d.cohort.eq(cohort)&d.selected_L048
        ref=(json.loads(sources[3].read_text())['rules']['L048']['selected'] if cohort=='fresh500' else oldfocus[cohort])
        err=abs(values[mask,-1].mean()-ref['mean_gross_pct']);assert err<1e-10 and mask.sum()==ref['n']
        reconciliation.append(dict(cohort=cohort,n=int(mask.sum()),mean_gross_pct=values[mask,-1].mean(),absolute_error=err))
    out=[];profiles=[];periods=[];inferences=[];tails=[];segments=[]
    scopes={x:d.cohort.eq(x).to_numpy() for x in ['old150','new280','fresh500']}
    scopes.update({f'fresh500_{a.split("-")[0]}':(d.cohort.eq('fresh500')&d.asset.eq(a)).to_numpy() for a in fresh.asset.unique()})
    for scope,m in scopes.items():
        sd=d.loc[m].reset_index(drop=True);v=values[m];sel=sd.selected_L048.to_numpy(bool);elig=sd.macro_gate.to_numpy(bool)
        groups={'L048_AI_short':sel,'macro_no_AI':elig,'macro_AI_long_complement':sd.complement_AI_long.to_numpy(bool),'macro_belowMA20_no_AI':sd.control_belowMA20.to_numpy(bool)}
        chronological=sd[['calendar_block','entry_time']].drop_duplicates().sort_values('entry_time').calendar_block.to_numpy()
        for name,s in groups.items():
            for j,h in enumerate(H):
                x=v[s,j];r=dict(scope=scope,group=name,horizon=int(h),opportunities=len(sd),frequency=s.mean(),per_opportunity_gross_pct=np.where(s,v[:,j],0).mean(),**stats(x))
                r['selected_blocks']=int(sd.loc[s,'calendar_block'].nunique())
                quarter_means=[v[s&(sd.quarter!=q).to_numpy(),j].mean() for q in sd.loc[s,'quarter'].unique() if (s&(sd.quarter!=q).to_numpy()).any()]
                r['leave_one_quarter_out_min_mean_pct']=min(quarter_means) if quarter_means else np.nan
                bsum=sd.loc[s,['calendar_block']].copy();bsum['v']=x
                bsum=bsum.groupby('calendar_block').v.sum().sort_values(ascending=False)
                for k in [1,3]:
                    keep=s&~sd.calendar_block.isin(bsum.index[:k]).to_numpy()
                    r[f'ex_best{k}_blocks_mean_pct']=v[keep,j].mean() if keep.any() else np.nan
                out.append(r)
                for div in [2,3]:
                    for k,part in enumerate(np.array_split(chronological,div),1):
                        mm=s&sd.calendar_block.isin(part).to_numpy()
                        periods.append(dict(scope=scope,group=name,horizon=int(h),splits=div,part=k,**stats(v[mm,j])))
        inf={kind:infer(sd,v,sel,elig,sd[col],seed) for kind,col,seed in [('block','calendar_block',2026093011),('quarter','quarter',2026093012)]}
        for kind,x in inf.items():
            for j,h in enumerate(H):inferences.append(dict(scope=scope,groups=kind,horizon=int(h),mean_ci95_low=x['mean_ci95'][0,j],mean_ci95_high=x['mean_ci95'][1,j],AI_increment_ci95_low=x['AI_increment_ci95'][0,j],AI_increment_ci95_high=x['AI_increment_ci95'][1,j],standardized_price_baseline_pct=x['standardized_baseline'][j],AI_increment_pct=x['AI_increment'][j],selected_clusters=x['selected_groups'],strata_with_both_groups=x['strata_with_both_groups']))
        ids=np.flatnonzero(sel);top=ids[np.argsort(v[sel,-1])[-3:]];keep=sel.copy();keep[top]=False
        for j,h in enumerate(H):
            profiles.append(dict(scope=scope,horizon=int(h),selected_mean_pct=v[sel,j].mean(),selected_median_pct=np.median(v[sel,j]),ex_same_top3_at240_mean_pct=v[keep,j].mean(),same_top3_at240_sum_pct=v[top,j].sum(),n=int(sel.sum())))
            prev=np.zeros(len(sd)) if j==0 else v[:,j-1]
            segments.append(dict(scope=scope,from_minute=0 if j==0 else int(H[j-1]),to_minute=int(h),mean_increment_pct=(v[:,j]-prev)[sel].mean(),ex_same_top3_at240_mean_increment_pct=(v[:,j]-prev)[keep].mean()))
        for i in top:
            tails.append(dict(scope=scope,case=int(sd.loc[i,'case']),window_id=sd.loc[i,'window_id'],asset=sd.loc[i,'asset'],entry_time=str(sd.loc[i,'entry_time']),**{f'gross_{h}_pct':v[i,j] for j,h in enumerate(H)}))
        print(scope,'selected',int(sel.sum()),'means',np.round(v[sel].mean(0),6).tolist(),'ex240top3',np.round(v[keep].mean(0),6).tolist(),flush=True)
    for name,rows in [('all_profiles',out),('chronological_splits',periods),('descriptive_inference',inferences),('fixed_240_tail_sensitivity',profiles),('time_segment_contributions',segments),('largest_240_trades',tails)]:pd.DataFrame(rows).to_csv(HERE/f'{name}.csv',index=False)
    save('audit.json',dict(passed=True,independent_native_windows=checks,minute_open_close_observations=checks*241,original240_reconciliation=reconciliation,ma20_equal100_cases=int((d.ma20_now==100).sum()),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},exploratory_after_primary_inspection=True,no_model_calls=True))
    print('ALL CHECKS PASSED',flush=True)

if __name__=='__main__':main()
