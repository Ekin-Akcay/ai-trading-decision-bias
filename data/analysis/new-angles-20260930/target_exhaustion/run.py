from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
BASE=ROOT/'data/analysis/new-angles-20260930'
RUNS=[('original100','rules2to1-openai-20260926T072414Z'),('next50','reversal-terra50-20260929T184044Z'),('next280','reversal-validation280-20260929T194012Z'),('multi500','gross-edge-500-20260929T204545Z'),('paired90','ma-ablation-sol90-20260929T210853Z')]

def inputs():
    rows=[]; source_hashes={}
    for name in ['data/analysis/reversal-deep-20260929/risk/windows.csv','data/analysis/reversal-deep-20260929/risk/paths.npz','data/sim/gross-edge-500-20260929T204545Z/paths.npz','data/sim/ma-ablation-sol90-20260929T210853Z/paths.npz','data/raw/intraday/SOL-USD_1m.csv.gz']:
        source_hashes[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    for cohort,run in RUNS:
        p=ROOT/'data/sim/decisions'/f'{run}.jsonl'
        source_hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        for line in p.read_text().splitlines():
            r=json.loads(line)
            if r['model']!='gpt-5.6-terra-agent' or (cohort=='paired90' and r['arm']!='MA_A'): continue
            r['cohort']=cohort
            r['entry_time']=pd.Timestamp(r['window_end_ts'])+pd.Timedelta(minutes=15)
            rows.append(r)
    df=pd.DataFrame(rows).sort_values(['entry_time','asset','cohort']).reset_index(drop=True)
    assert len(df)==1020 and not df.duplicated(['asset','window_id']).any()
    old=pd.read_csv(ROOT/'data/analysis/reversal-deep-20260929/risk/windows.csv')
    z=np.load(ROOT/'data/analysis/reversal-deep-20260929/risk/paths.npz')
    cache={}
    for i,r in old.iterrows():
        cache[r.window_id]=np.column_stack([z[f'{i}_{x}_real'][:360] for x in 'ohlc'])
    z=np.load(ROOT/'data/sim/gross-edge-500-20260929T204545Z/paths.npz')
    cache.update({str(w):p[1:] for w,p in zip(z['window_id'],z['paths'])})
    z=np.load(ROOT/'data/sim/ma-ablation-sol90-20260929T210853Z/paths.npz')
    for r in df[df.cohort=='paired90'].itertuples(): cache[r.window_id]=z['paths'][int(r.block)-1,1:]
    raw=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',usecols=['ts','open','high','low','close'])
    raw['ts']=pd.to_datetime(raw.ts);raw=raw.set_index('ts').sort_index()
    # Exact grids establish complete minutes and identical cache conventions.
    cache_diffs=[]
    paths=[]
    for r in df.itertuples():
        if r.window_id not in cache:
            grid=pd.date_range(r.entry_time,periods=360,freq='min')
            future=raw.reindex(grid)[['open','high','low','close']].to_numpy(float)
        else: future=cache[r.window_id]
        assert future.shape==(360,4) and np.isfinite(future).all(),r.window_id
        assert (future>0).all() and np.all(future[:,1]>=future[:,[0,2,3]].max(1)) and np.all(future[:,2]<=future[:,[0,1,3]].min(1)),r.window_id
        assert r.stop_pct>0 and r.atr14_pct>0
        if r.asset=='SOL-USD':
            grid=pd.date_range(r.entry_time,periods=360,freq='min')
            truth=raw.reindex(grid)[['open','high','low','close']].to_numpy(float)
            assert np.isfinite(truth).all(),r.window_id
            cache_diffs.append(float(np.max(np.abs(future-truth))))
            assert np.allclose(future,truth,rtol=0,atol=1e-8),r.window_id
        paths.append(np.vstack([np.full(4,float(r.price_real)),future]))
    df['donor_stop_pct']=np.nan;df['donor_window_id']=''
    for _,g in df.groupby(['cohort','asset'],sort=False):
        for prev,curr in zip(g.index[:-1],g.index[1:]):
            assert df.loc[prev,'entry_time']<df.loc[curr,'entry_time']
            df.loc[curr,'donor_stop_pct']=df.loc[prev,'stop_pct']/df.loc[prev,'atr14_pct']*df.loc[curr,'atr14_pct']
            df.loc[curr,'donor_window_id']=df.loc[prev,'window_id']
    times=np.sort(df.entry_time.unique());fold={t:min(4,int(i*5/len(times)))+1 for i,t in enumerate(times)}
    half={t:int(i>=len(times)/2)+1 for i,t in enumerate(times)}
    df['fold']=[fold[t] for t in df.entry_time];df['half']=[half[t] for t in df.entry_time]
    df['quarter']=df.entry_time.dt.to_period('Q').astype(str)
    keep=['cohort','window_id','asset','entry_time','price_real','action','confidence','reason','stop_pct','atr14_pct','donor_stop_pct','donor_window_id','fold','half','quarter']
    df[keep].to_csv(OUT/'windows.csv',index=False)
    np.savez_compressed(OUT/'paths.npz',paths=np.array(paths),window_id=df.window_id.to_numpy(str))
    return df,np.array(paths),source_hashes,cache_diffs

def replay(p,original_sign,stop):
    if not np.isfinite(stop):return dict(status='missing_donor')
    origin=p[0,3];target=origin*(1+original_sign*2*stop);sl=origin*(1-original_sign*stop)
    hit=None
    for j in range(1,241):
        o,h,l,c=p[j]
        # The open is observed before the intraminute extremes.
        if original_sign*(o-sl)<=0:return dict(status='stop_first',first_event_minute=j)
        if original_sign*(o-target)>=0:hit=j;break
        sl_touch=l<=sl if original_sign==1 else h>=sl
        tp_touch=h>=target if original_sign==1 else l<=target
        if sl_touch:return dict(status='ambiguous_stop_first' if tp_touch else 'stop_first',first_event_minute=j)
        if tp_touch:hit=j;break
    if hit is None:return dict(status='no_target_240')
    reclaim=None
    for k in range(hit+1,hit+16):
        if original_sign*(p[k,3]-target)<0:reclaim=k;break
    if reclaim is None:return dict(status='no_confirmation_15',target_minute=hit)
    entry=p[reclaim+1,0];exit=p[reclaim+60,3];side=-original_sign
    highs=p[reclaim+1:reclaim+61,1];lows=p[reclaim+1:reclaim+61,2]
    mfe=100*((highs.max()/entry-1) if side==1 else (1-lows.min()/entry))
    mae=100*((lows.min()/entry-1) if side==1 else (1-highs.max()/entry))
    delays={f'delay{d}_gross_pct':100*side*(p[reclaim+60+d,3]/p[reclaim+1+d,0]-1) for d in [1,5]}
    return dict(status='trade',target_minute=hit,confirmation_minute=reclaim,entry_minute=reclaim+1,exit_minute=reclaim+60,entry_price=entry,exit_price=exit,position='long' if side==1 else 'short',gross_pct=100*side*(exit/entry-1),mfe_pct=mfe,mae_pct=mae,**delays)

def bs(numer,denom,groups,rng,reps=12000):
    codes,labels=pd.factorize(groups,sort=True);m=len(labels)
    a=np.zeros((m,numer.shape[1]));b=np.zeros_like(a)
    np.add.at(a,codes,numer);np.add.at(b,codes,denom)
    out=[]
    for j in range(0,reps,500):
        ix=rng.integers(0,m,(min(500,reps-j),m))
        num=a[ix].sum(1);den=b[ix].sum(1)
        out.append(np.divide(num,den,out=np.full_like(num,np.nan),where=den>0))
    return np.concatenate(out)

def main():
    budget=ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json'
    budget_hash=hashlib.sha256(budget.read_bytes()).hexdigest()
    df,paths,hashes,cache_diffs=inputs()
    ledger=[]
    for i,r in df.iterrows():
        ai_sign=1 if r.action=='long' else -1
        for geometry,sign,stop in [('ai',ai_sign,r.stop_pct),('donor',ai_sign,r.donor_stop_pct),('atr_same_ai',ai_sign,r.atr14_pct/100),('price_short',-1,r.atr14_pct/100),('price_long',1,r.atr14_pct/100)]:
            result=replay(paths[i],sign,stop)
            if result['status']=='trade':
                result['position_entry_time']=str(r.entry_time+pd.Timedelta(minutes=result['entry_minute']-1))
                result['position_exit_time']=str(r.entry_time+pd.Timedelta(minutes=result['exit_minute']))
            ledger.append(dict(window_index=i,window_id=r.window_id,cohort=r.cohort,asset=r.asset,entry_time=str(r.entry_time),geometry=geometry,original_sign=sign,stop_pct=stop,target_price=r.price_real*(1+sign*2*stop),**result))
    led=pd.DataFrame(ledger);led.to_csv(OUT/'event_ledger.csv',index=False)
    policies=[];numer=[];denom=[]
    for geom in ['ai','donor','atr_same_ai','price_short','price_long']:
        rows=led[led.geometry==geom].set_index('window_index').reindex(df.index)
        for side in (['all','long','short'] if geom in ['ai','donor','atr_same_ai'] else ['all']):
            eligible=(rows.status=='trade') & ((rows.position==side) if side!='all' else True)
            policies.append(geom+'_'+side);denom.append(eligible.to_numpy(float));numer.append(np.where(eligible,rows.gross_pct.fillna(0),0))
    y=np.array(numer).T;n=np.array(denom).T
    rng=np.random.default_rng(2026093001)
    block_bs=bs(y,n,df.entry_time,rng);quarter_bs=bs(y,n,df.quarter,rng)
    opp_bs=bs(y,np.ones_like(n),df.entry_time,rng)
    quarter_opp_bs=bs(y,np.ones_like(n),df.quarter,rng)
    alpha=.05/len(policies)
    summaries=[];breakdown=[]
    for j,name in enumerate(policies):
        active=n[:,j]>0;ret=y[active,j];means={}
        for grouping in ['cohort','fold','half','quarter']:
            means[grouping]=[]
            for label,g in df.groupby(grouping):
                ix=g.index;sel=n[ix,j]>0;rr=y[ix,j][sel]
                mean=float(rr.mean()) if len(rr) else None
                breakdown.append(dict(policy=name,grouping=grouping,label=str(label),trades=len(rr),mean_gross_pct=mean,opportunity_mean_pct=float(y[ix,j].mean())))
                means[grouping].append(mean)
        sums=pd.DataFrame({'time':df.entry_time,'y':y[:,j],'n':n[:,j]}).groupby('time')[['y','n']].sum()
        best=sums[sums.n>0].sort_values('y',ascending=False).head(3).index
        mask=active & ~df.entry_time.isin(best).to_numpy()
        removed=float(y[mask,j].mean()) if mask.sum() else None
        ci=np.nanquantile(block_bs[:,j],[alpha/2,1-alpha/2]);qci=np.nanquantile(quarter_bs[:,j],[.025,.975])
        screen=bool(len(ret)>=30 and (sums.n>0).sum()>=20 and all(v is not None and v>0 for v in means['half']) and sum(v is not None and v>0 for v in means['fold'])>=4 and removed is not None and removed>0 and ci[0]>0)
        summaries.append(dict(policy=name,trades=len(ret),blocks=int((sums.n>0).sum()),wins=int((ret>0).sum()),mean_gross_pct=float(ret.mean()) if len(ret) else None,opportunity_mean_pct=float(y[:,j].mean()),sum_trade_returns_pct=float(ret.sum()),simultaneous_block_ci_pct=ci.tolist(),quarter95_ci_pct=qci.tolist(),without_best3_blocks_pct=removed,halves=means['half'],positive_folds=sum(v is not None and v>0 for v in means['fold']),discovery_screen=screen))
        geom=name.rsplit('_',1)[0]
        ar=led[led.geometry==geom].set_index('window_index').reindex(df.index).loc[active]
        best1=sums[sums.n>0].sort_values('y',ascending=False).head(1).index
        mask1=active & ~df.entry_time.isin(best1).to_numpy()
        summaries[-1].update(median_pct=float(np.median(ret)),worst_pct=float(ret.min()),best_pct=float(ret.max()),mean_win_pct=float(ret[ret>0].mean()),mean_loss_pct=float(ret[ret<0].mean()),mean_mfe_pct=float(ar.mfe_pct.mean()),mean_mae_pct=float(ar.mae_pct.mean()),without_best1_block_pct=float(y[mask1,j].mean()),delay1_mean_pct=float(ar.delay1_gross_pct.mean()),delay5_mean_pct=float(ar.delay5_gross_pct.mean()),median_confirmation_minute=float(ar.confirmation_minute.median()),leave_one_quarter_out_min_mean_pct=min(float(y[active & (df.quarter!=q).to_numpy(),j].mean()) for q in df.quarter.unique()))
    comparisons=[]
    pairs=[('ai_all','donor_all'),('ai_all','atr_same_ai_all'),('ai_long','donor_long'),('ai_long','atr_same_ai_long'),('ai_long','price_short_all'),('ai_short','donor_short'),('ai_short','atr_same_ai_short'),('ai_short','price_long_all')]
    for a,b in pairs:
        ia=policies.index(a);ib=policies.index(b);arr=opp_bs[:,ia]-opp_bs[:,ib]
        ci=np.nanquantile(arr,[.05/(2*len(pairs)),1-.05/(2*len(pairs))])
        qci=np.nanquantile(quarter_opp_bs[:,ia]-quarter_opp_bs[:,ib],[.025,.975])
        comparisons.append(dict(policy=a,control=b,opportunity_difference_pp=float((y[:,ia]-y[:,ib]).mean()),simultaneous_block_ci_pp=ci.tolist(),quarter95_ci_pp=qci.tolist()))
    np.savez_compressed(OUT/'family_arrays.npz',returns=y,active=n,policies=np.array(policies),block_bootstrap=block_bs,quarter_bootstrap=quarter_bs,opportunity_bootstrap=opp_bs,quarter_opportunity_bootstrap=quarter_opp_bs)
    pd.DataFrame(breakdown).to_csv(OUT/'breakdown.csv',index=False)
    pd.DataFrame(summaries).to_json(OUT/'summary.json',orient='records',indent=2)
    (OUT/'comparisons.json').write_text(json.dumps(comparisons,indent=2))
    b=json.loads(budget.read_text());assert hashlib.sha256(budget.read_bytes()).hexdigest()==budget_hash
    audit=dict(windows=len(df),unique_asset_windows=int(df[['asset','window_id']].drop_duplicates().shape[0]),unique_entry_times=int(df.entry_time.nunique()),cohorts=df.cohort.value_counts().to_dict(),path_shape=list(paths.shape),SOL_cache_max_absolute_error=max(cache_diffs),input_hashes=hashes,plan_sha256=hashlib.sha256((OUT/'PLAN.md').read_bytes()).hexdigest(),budget_sha256=budget_hash,attempts_before_and_after=len(b['reserved_attempts']),remaining=800-len(b['reserved_attempts']),additional_model_calls=0,discovery_only=True)
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2))
    print(pd.DataFrame(summaries)[['policy','trades','mean_gross_pct','without_best3_blocks_pct','positive_folds','discovery_screen']].to_string(index=False))

if __name__=='__main__':main()
