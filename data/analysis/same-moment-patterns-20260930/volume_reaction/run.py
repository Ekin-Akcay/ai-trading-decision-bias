"""Four frozen volume/price reaction rules on existing AI decision windows."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
OLD=ROOT/'data/analysis/new-angles-20260930/target_exhaustion'
SEED=2026093041

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()

def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,np.integer):return int(x)
    if isinstance(x,np.bool_):return bool(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x

def save(name,data):(OUT/name).write_text(json.dumps(clean(data),indent=2,allow_nan=False)+'\n')

def bootstrap(y,den,groups,weights=None):
    codes,labels=pd.factorize(groups,sort=True)
    a=np.zeros((len(labels),y.shape[1]));b=np.zeros_like(a)
    np.add.at(a,codes,y);np.add.at(b,codes,den)
    if weights is None:
        weights=np.random.default_rng(SEED).multinomial(len(labels),np.ones(len(labels))/len(labels),size=20000)
    numerator=weights@a;denominator=weights@b
    return np.divide(numerator,denominator,out=np.full_like(numerator,np.nan),where=denominator>0),weights

def main():
    sources={str(p.relative_to(ROOT)):sha(p) for p in [OLD/'windows.csv',OLD/'paths.npz',OUT/'PLAN.md']}
    budget=ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json'
    bh=sha(budget);assert len(json.loads(budget.read_text())['reserved_attempts'])==771
    w=pd.read_csv(OLD/'windows.csv');w['entry_time']=pd.to_datetime(w.entry_time)
    z=np.load(OLD/'paths.npz');paths=z['paths']
    assert len(w)==1020 and paths.shape==(1020,361,4)
    assert np.array_equal(w.window_id.to_numpy(str),z['window_id'])
    w['volume_coverage']=False;w['volume_exclusion']='unchecked';w['volume30']=np.nan;w['pre50h_median_volume30']=np.nan;w['volume_ratio']=np.nan
    for asset,rows in w.groupby('asset',sort=True):
        p=ROOT/f'data/raw/intraday/{asset}_1m.csv.gz';sources[str(p.relative_to(ROOT))]=sha(p)
        raw=pd.read_csv(p,usecols=['ts','volume']);raw['ts']=pd.to_datetime(raw.ts)
        raw=raw.set_index('ts').sort_index();assert raw.index.is_unique
        for i,r in rows.iterrows():
            grid=pd.date_range(r.entry_time-pd.Timedelta(minutes=3000),periods=3030,freq='min')
            v=raw.volume.reindex(grid).to_numpy(float)
            if not np.isfinite(v).all():w.loc[i,'volume_exclusion']='missing_or_nonfinite_volume';continue
            if (v<0).any():w.loc[i,'volume_exclusion']='negative_volume';continue
            prior=v[:3000].reshape(100,30).sum(1);median=np.median(prior)
            if median<=0:w.loc[i,'volume_exclusion']='nonpositive_reference';continue
            w.loc[i,['volume_coverage','volume_exclusion','volume30','pre50h_median_volume30','volume_ratio']]=[True,'none',float(v[3000:].sum()),float(median),float(v[3000:].sum()/median)]
        print(asset,'volume features prepared',flush=True)
    o=paths[:,1,0];h=paths[:,1:31,1].max(1);l=paths[:,1:31,2].min(1);c=paths[:,30,3]
    atr=w.atr14_pct.to_numpy(float)/100;cover=w.volume_coverage.to_numpy(bool)
    assert np.isfinite(paths).all() and (paths>0).all() and np.isfinite(atr).all() and (atr>0).all()
    assert (paths[:,:,1]>=paths[:,:,[0,2,3]].max(2)).all() and (paths[:,:,2]<=paths[:,:,[0,1,3]].min(2)).all()
    w['early_open']=o;w['early_high']=h;w['early_low']=l;w['early_close']=c
    w['early_long_return_pct']=100*(c/o-1);w['early_close_location']=(c-l)/(h-l)
    w['down_excursion_atr']=(o-l)/(o*atr);w['up_excursion_atr']=(h-o)/(o*atr)
    w['known_signal_time']=w.entry_time+pd.Timedelta(minutes=30)
    # Freeze all features and masks before computing a trading payoff in this script.
    cases=[('sell_pressure_recovery_long',1,(o-l>=.5*o*atr)&(c>=(h+l)/2),w.volume_ratio.ge(1.5).to_numpy()),
           ('buy_pressure_rejection_short',-1,(h-o>=.5*o*atr)&(c<=(h+l)/2),w.volume_ratio.ge(1.5).to_numpy()),
           ('quiet_down_extension_long',1,(o-c>=.5*o*atr),w.volume_ratio.le(.75).to_numpy()),
           ('quiet_up_extension_short',-1,(c-o>=.5*o*atr),w.volume_ratio.le(.75).to_numpy())]
    definitions=[];pairs=[]
    for name,side,geometry,volume in cases:
        ai=w.action.eq('short' if side==1 else 'long').to_numpy()
        definitions += [(name,'candidate',side,cover&ai&geometry&volume),
                        (name+'__noAI','price_only_control',side,cover&geometry&volume),
                        (name+'__noVolume','AI_geometry_control',side,cover&ai&geometry)]
        pairs += [(name,name+'__noAI'),(name,name+'__noVolume')]
    definitions += [('AI_SHORT_delayed_long','AI_only_control',1,cover&w.action.eq('short').to_numpy()),
                    ('AI_LONG_delayed_short','AI_only_control',-1,cover&w.action.eq('long').to_numpy())]
    assert len(definitions)==14 and len(pairs)==8
    w.to_csv(OUT/'features.csv',index=False)
    save('SCORING_FREEZE.json',dict(source_sha256=sources,features_sha256=sha(OUT/'features.csv'),definitions=[dict(name=n,role=r,side=s,selected=int(m.sum())) for n,r,s,m in definitions],new_model_calls=0,independent_confirmation=False))
    ep=paths[:,31,0];xp=paths[:,150,3];raw=100*(xp/ep-1)
    highs=paths[:,31:151,1].max(1);lows=paths[:,31:151,2].min(1)
    names=[d[0] for d in definitions];mask=np.column_stack([d[3] for d in definitions]);sides=np.array([d[2] for d in definitions])
    y=np.where(mask,raw[:,None]*sides,0);n=mask.astype(float)
    bs,weights=bootstrap(y,n,w.quarter)
    oppden=np.tile(cover[:,None],(1,len(definitions))).astype(float)
    oppbs,_=bootstrap(y,oppden,w.quarter,weights)
    rows=[];ledger=[];breakdown=[];concentration=[]
    for j,(name,role,side,selected) in enumerate(definitions):
        ret=y[selected,j];t=w.loc[selected,'entry_time']
        sumtab=pd.DataFrame({'time':w.entry_time,'pnl':y[:,j],'n':n[:,j]}).groupby('time')[['pnl','n']].sum()
        best=sumtab[sumtab.n>0].sort_values('pnl',ascending=False)
        ex1=selected&~w.entry_time.isin(best.index[:1]).to_numpy();ex3=selected&~w.entry_time.isin(best.index[:3]).to_numpy()
        halves=[];folds=[]
        for group in ['cohort','asset','half','fold']:
            for label,g in w.groupby(group,sort=True):
                idx=g.index;sel=selected[idx];rr=y[idx,j][sel]
                mean=float(rr.mean()) if len(rr) else None
                breakdown.append(dict(policy=name,group=group,label=str(label),coverage_windows=int(cover[idx].sum()),trades=int(sel.sum()),blocks=int(w.loc[idx[sel],'entry_time'].nunique()),gross_mean_pct=mean,opportunity_mean_pct=float(y[idx,j].sum()/cover[idx].sum()) if cover[idx].sum() else None))
                if group=='half':halves.append(mean)
                if group=='fold':folds.append(mean)
        for yy in sorted(w.entry_time.dt.year.unique()):
            idx=np.where(w.entry_time.dt.year.to_numpy()==yy)[0];rr=y[idx,j][selected[idx]]
            breakdown.append(dict(policy=name,group='year',label=str(yy),coverage_windows=int(cover[idx].sum()),trades=len(rr),blocks=int(w.loc[idx[selected[idx]],'entry_time'].nunique()),gross_mean_pct=float(rr.mean()) if len(rr) else None,opportunity_mean_pct=float(y[idx,j].sum()/cover[idx].sum()) if cover[idx].sum() else None))
        ci=np.nanquantile(bs[:,j],[.025,.975]) if len(ret) else [np.nan,np.nan]
        familyci=np.nanquantile(bs[:,j],[.025/14,1-.025/14]) if len(ret) else [np.nan,np.nan]
        row=dict(policy=name,role=role,side='long' if side==1 else 'short',opportunities=int(cover.sum()),trades=len(ret),blocks=t.nunique(),gross_mean_pct=ret.mean() if len(ret) else np.nan,median_pct=np.median(ret) if len(ret) else np.nan,win_rate=np.mean(ret>0) if len(ret) else np.nan,wins=int((ret>0).sum()),mean_win_pct=ret[ret>0].mean() if (ret>0).any() else np.nan,mean_loss_pct=ret[ret<0].mean() if (ret<0).any() else np.nan,worst_pct=ret.min() if len(ret) else np.nan,best_pct=ret.max() if len(ret) else np.nan,opportunity_mean_pct=y[:,j].sum()/cover.sum(),quarter95_ci_pct=ci,quarter_family95_ci_pct=familyci,without_best1_block_pct=y[ex1,j].mean() if ex1.any() else np.nan,without_best3_blocks_pct=y[ex3,j].mean() if ex3.any() else np.nan,halves=halves,folds=folds)
        row['stronger_discovery_lead']=bool(t.nunique()>=30 and all(v is not None and v>0 for v in halves) and ex3.any() and y[ex3,j].mean()>0 and familyci[0]>0)
        rows.append(row)
        for time,r in best.head(3).iterrows():concentration.append(dict(policy=name,entry_time=str(time),sum_trade_pct=r.pnl,trades=int(r.n)))
        for i,r in w.iterrows():
            sel=bool(selected[i]);mfe=100*((highs[i]/ep[i]-1) if side==1 else (1-lows[i]/ep[i]));mae=100*((lows[i]/ep[i]-1) if side==1 else (1-highs[i]/ep[i]))
            ledger.append(dict(policy=name,role=role,window_id=r.window_id,asset=r.asset,cohort=r.cohort,original_entry_time=str(r.entry_time),quarter=r.quarter,AI_action=r.action,AI_reason=r.reason,coverage=bool(cover[i]),coverage_exclusion=r.volume_exclusion,selected=sel,status=('trade' if sel else 'pattern_not_met') if cover[i] else 'coverage_exclusion',side=side,entry_time=str(r.entry_time+pd.Timedelta(minutes=30)) if sel else None,exit_time=str(r.entry_time+pd.Timedelta(minutes=150)) if sel else None,entry_price=ep[i] if sel else None,exit_price=xp[i] if sel else None,gross_pct=y[i,j] if sel else None,opportunity_gross_pct=y[i,j] if cover[i] else None,mfe_pct=mfe if sel else None,mae_pct=mae if sel else None,volume_ratio=r.volume_ratio,early_long_return_pct=r.early_long_return_pct,early_close_location=r.early_close_location,down_excursion_atr=r.down_excursion_atr,up_excursion_atr=r.up_excursion_atr))
    comparisons=[]
    for a,b in pairs:
        j=names.index(a);k=names.index(b);d=oppbs[:,j]-oppbs[:,k]
        comparisons.append(dict(candidate=a,control=b,opportunity_difference_pp=(y[:,j]-y[:,k]).sum()/cover.sum(),quarter95_ci_pp=np.nanquantile(d,[.025,.975]),quarter_family95_ci_pp=np.nanquantile(d,[.025/8,1-.025/8])))
    save('summary.json',rows);save('comparisons.json',comparisons)
    pd.DataFrame([{k:v for k,v in r.items() if not isinstance(v,(list,np.ndarray))} for r in rows]).to_csv(OUT/'summary.csv',index=False)
    pd.DataFrame(ledger).to_csv(OUT/'trade_ledger.csv',index=False);pd.DataFrame(breakdown).to_csv(OUT/'breakdown.csv',index=False);pd.DataFrame(concentration).to_csv(OUT/'largest_blocks.csv',index=False)
    np.savez_compressed(OUT/'vectors.npz',policies=np.array(names),returns=y,selected=mask,coverage=cover,quarter_bootstrap=bs,opportunity_bootstrap=oppbs,quarter_weights=weights)
    assert all(sha(ROOT/name)==h for name,h in sources.items());assert sha(budget)==bh
    save('audit.json',dict(source_hashes_preserved=True,budget_hash_preserved=True,source_sha256=sources,budget_sha256=bh,original_windows=len(w),coverage_windows=int(cover.sum()),coverage_exclusions=w.loc[~cover,'volume_exclusion'].value_counts().to_dict(),trade_agent_calls=0,remaining_credit_allowance=29,candidates=4,controls=10,bootstrap_replicates=20000,bootstrap_seed=SEED,seen_outcomes=True))
    print(pd.DataFrame(rows)[['policy','trades','blocks','gross_mean_pct','without_best3_blocks_pct','stronger_discovery_lead']].to_string(index=False))

if __name__=='__main__':main()
