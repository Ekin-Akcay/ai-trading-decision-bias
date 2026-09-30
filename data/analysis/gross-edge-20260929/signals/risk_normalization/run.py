from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];SIGNALS=HERE.parent
RUN=ROOT/'data/sim/gross-edge-500-20260929T204545Z'
assert (RUN/'ALLOW_EVALUATION').exists()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
    if isinstance(v,(np.integer,)):return int(v)
    if isinstance(v,(np.bool_,)):return bool(v)
    if isinstance(v,(float,np.floating)):return float(v) if np.isfinite(v) else None
    return v
def save(name,v):(HERE/name).write_text(json.dumps(clean(v),indent=2,allow_nan=False)+'\n')
sources=[SIGNALS/'windows.csv',SIGNALS/'all116_zero_fee_vectors.npz',SIGNALS/'fresh_L048_independent_rows.csv',RUN/'window_results.csv',RUN/'bootstrap_arrays.npz',RUN/'summary.json',ROOT/'data/sim/decisions/rules2to1-openai-20260926T072414Z.jsonl',ROOT/'data/sim/decisions/reversal-terra50-20260929T184044Z.jsonl',HERE/'PLAN.md']
hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
existing=pd.read_csv(SIGNALS/'windows.csv');bundle=np.load(SIGNALS/'all116_zero_fee_vectors.npz');pid=list(bundle['candidate']).index('003_long_none_confirm0_hold240')
assert existing.window_id.tolist()==bundle['window_id'].tolist();existing['gross_pct']=bundle['gross_pct'][pid]
meta={}
for p in sources[6:8]:
    for line in p.read_text().splitlines():
        r=json.loads(line)
        if r['model']=='gpt-5.6-terra-agent':meta[r['window_id']]=r
for i,row in existing.iterrows():
    if row.cohort=='old150':
        record=meta[row.window_id];existing.loc[i,'sigma_2d_pct']=record['sigma_2d_pct'];existing.loc[i,'asset']=record['asset']
existing['macro']=existing.both_down
existing['block']=existing.entry_time
fresh=pd.read_csv(RUN/'window_results.csv');own=pd.read_csv(SIGNALS/'fresh_L048_independent_rows.csv')
assert fresh.window_id.tolist()==own.window_id.tolist();fresh['gross_pct']=own.gross_pct
fresh['macro']=own.eligible;fresh['cohort']='fresh500'
cols=['case','block','window_id','asset','entry_time','cohort','action','macro','ma20_now','ma50_now','atr14_pct','sigma_2d_pct','gross_pct']
data=pd.concat([existing[cols],fresh[cols]],ignore_index=True)
assert len(data)==930 and data.window_id.nunique()==930
assert np.isfinite(data[['gross_pct','atr14_pct','sigma_2d_pct']]).all().all()
assert (data[['atr14_pct','sigma_2d_pct']]>0).all().all()
data['entry_time']=pd.to_datetime(data.entry_time)
data['selected']=data.macro & data.action.eq('short')
data['below_ma20_control']=data.macro & data.ma20_now.gt(100)
data['gross_per_ATR']=data.gross_pct/data.atr14_pct
data['gross_per_sigma2d']=data.gross_pct/data.sigma_2d_pct
data.to_csv(HERE/'windows.csv',index=False)
results=[];concentration=[];assetrows=[];increments=[]
root_boot=np.load(RUN/'bootstrap_arrays.npz')

def summarize(values,mask,frame,blocks,bw,quarters,qw):
    values=np.asarray(values,float);mask=np.asarray(mask,bool);x=values[mask];n=len(x)
    if not n:return {'n':0}
    blockn=np.bincount(blocks,weights=mask,minlength=bw.shape[1]);blocksums=np.bincount(blocks,weights=np.where(mask,values,0),minlength=bw.shape[1]);den=bw@blockn;draw=(bw@blocksums)[den>0]/den[den>0]
    qn=np.bincount(quarters,weights=mask,minlength=qw.shape[1]);qs=np.bincount(quarters,weights=np.where(mask,values,0),minlength=qw.shape[1]);qd=qw@qn;quartermeans=(qw@qs)[qd>0]/qd[qd>0]
    rank=np.argsort(blocksums)[::-1]
    remove=lambda k:values[mask & ~np.isin(blocks,rank[:k])].mean() if np.any(mask & ~np.isin(blocks,rank[:k])) else np.nan
    order=frame.loc[mask].sort_values('entry_time').index.to_numpy();temporal=values[order]
    return {'n':n,'selected_blocks':int((blockn>0).sum()),'opportunities':len(frame),'frequency':n/len(frame),'mean':x.mean(),'median':np.median(x),'win_rate':(x>0).mean(),'best':x.max(),'worst':x.min(),'profit_factor_in_these_units':x[x>0].sum()/-x[x<0].sum() if (x<0).any() else None,'block_ci95':np.quantile(draw,[.025,.975]),'block_ci975':np.quantile(draw,[.0125,.9875]),'quarter_ci95':np.quantile(quartermeans,[.025,.975]),'largest_block_share_total_signed_sum':blocksums.max()/x.sum() if x.sum()!=0 else np.nan,'largest3_blocks_share_total_signed_sum':blocksums[rank[:3]].sum()/x.sum() if x.sum()!=0 else np.nan,'exclude_largest_block_mean':remove(1),'exclude_largest3_blocks_mean':remove(3),'exclude_best_trade_mean':np.sort(x)[:-1].mean() if n>1 else np.nan,'exclude_best3_trades_mean':np.sort(x)[:-3].mean() if n>3 else np.nan,'chrono_half_means':[z.mean() for z in [temporal[:n//2],temporal[n//2:]]] if n>=2 else [],'chrono_third_means':[z.mean() for z in np.array_split(temporal,3)] if n>=3 else []}

for cohort in ['old150','new280','fresh500']:
    f=data[data.cohort==cohort].copy().reset_index(drop=True)
    blockcodes,blocklabels=pd.factorize(f.block,sort=True);qcodes,qlabels=pd.factorize(f.entry_time.dt.to_period('Q').astype(str),sort=True)
    if cohort=='fresh500':bw=root_boot['block_weights'];qw=root_boot['quarter_weights']
    else:
        brng=np.random.default_rng(2026093061+(cohort=='new280'));qrng=np.random.default_rng(2026093062+(cohort=='new280'))
        bw=brng.multinomial(len(blocklabels),np.repeat(1/len(blocklabels),len(blocklabels)),size=20000);qw=qrng.multinomial(len(qlabels),np.repeat(1/len(qlabels),len(qlabels)),size=20000)
    assert bw.shape==(20000,len(blocklabels)) and qw.shape==(20000,len(qlabels))
    era=np.where(f.entry_time.dt.year<=2021,'2020-21',np.where(f.entry_time.dt.year<=2023,'2022-23','2024-26'))
    reg=np.where((f.ma20_now<=100)&(f.ma50_now<=100),'above_both',np.where((f.ma20_now>=100)&(f.ma50_now>=100),'below_both','mixed'))
    strata,labels=pd.factorize(f.asset+'|'+era+'|'+reg,sort=True)
    for measure in ['gross_pct','gross_per_ATR','gross_per_sigma2d']:
        values=f[measure].to_numpy()
        for name,mask in [('AI_selected_L048',f.selected.to_numpy()),('macro_no_AI',f.macro.to_numpy(bool)),('macro_below_MA20_no_AI',f.below_ma20_control.to_numpy())]:
            result=summarize(values,mask,f,blockcodes,bw,qcodes,qw);results.append({'cohort':cohort,'measure':measure,'policy':name,**result})
            for code,label in enumerate(blocklabels):
                use=mask&(blockcodes==code)
                if use.any():concentration.append({'cohort':cohort,'measure':measure,'policy':name,'block':str(label),'entry_time':str(f.loc[blockcodes==code,'entry_time'].iloc[0]),'n':int(use.sum()),'sum':values[use].sum(),'mean':values[use].mean()})
            for asset in sorted(f.asset.unique()):
                use=mask&f.asset.eq(asset).to_numpy();opposite=mask&~f.asset.eq(asset).to_numpy()
                assetrows.append({'cohort':cohort,'measure':measure,'policy':name,'asset':asset,'n':int(use.sum()),'mean':values[use].mean() if use.any() else np.nan,'excluding_asset_mean':values[opposite].mean() if opposite.any() else np.nan})
        # Fixed standardized AI increment: selected-stratum weights, all eligible control means.
        chosen=f.selected.to_numpy();eligible=f.macro.to_numpy(bool)
        ns=len(labels);ng=len(blocklabels)
        def group_arrays(groups,ng):
            sa=np.zeros((ng,ns));en=np.zeros_like(sa);ev=np.zeros_like(sa)
            np.add.at(sa,(groups,strata),chosen);np.add.at(en,(groups,strata),eligible);np.add.at(ev,(groups,strata),np.where(eligible,values,0))
            num=np.bincount(groups,weights=np.where(chosen,values,0),minlength=ng)
            return sa,en,ev,num
        s,en,ev,num=group_arrays(blockcodes,ng);stratum_n=s.sum(0);stratum_en=en.sum(0);stratum_sum=ev.sum(0)
        means=np.divide(stratum_sum,stratum_en,out=np.zeros(ns),where=stratum_en>0);baseline=np.sum(stratum_n*means)/stratum_n.sum();observed=values[chosen].mean()-baseline
        def inc_boot(weights,arrays):
            sa,en,ev,num=arrays;counts=weights@sa;en_=weights@en;ev_=weights@ev;den=counts.sum(1)
            baseline_=np.sum(counts*np.divide(ev_,en_,out=np.zeros_like(ev_),where=en_>0),axis=1)
            delta=(weights@num-baseline_)[den>0]/den[den>0]
            return {'ci95':np.quantile(delta,[.025,.975]),'ci975':np.quantile(delta,[.0125,.9875])}
        qb=inc_boot(qw,group_arrays(qcodes,len(qlabels)));bb=inc_boot(bw,(s,en,ev,num))
        increments.append({'cohort':cohort,'measure':measure,'selected_mean':values[chosen].mean(),'standardized_no_AI_mean':baseline,'AI_increment':observed,'block':bb,'quarter':qb,'selected_in_all_selected_strata':int(stratum_n[stratum_n==stratum_en].sum()),'selected_in_mixed_strata':int(stratum_n[(stratum_n>0)&(stratum_n<stratum_en)].sum())})

save('results.json',results);save('AI_increment.json',increments)
pd.DataFrame(results).to_csv(HERE/'results.csv',index=False);pd.DataFrame(concentration).to_csv(HERE/'block_concentration.csv',index=False);pd.DataFrame(assetrows).to_csv(HERE/'asset_results.csv',index=False)
root=json.loads((RUN/'summary.json').read_text())['rules']['L048'];baseline=next(r for r in results if r['cohort']=='fresh500' and r['measure']=='gross_pct' and r['policy']=='AI_selected_L048')
assert baseline['n']==root['selected']['n'] and abs(baseline['mean']-root['selected']['mean_gross_pct'])<1e-10
assert np.allclose(baseline['block_ci975'],root['block_inference']['profit']['simultaneous97_5'],atol=1e-10)
inc=next(r for r in increments if r['cohort']=='fresh500' and r['measure']=='gross_pct');assert abs(inc['AI_increment']-root['block_inference']['AI_increment_mean_pct'])<1e-10
assert np.allclose(inc['block']['ci975'],root['block_inference']['AI_increment']['simultaneous97_5'],atol=1e-10)
audit={'passed':True,'no_new_model_calls':True,'exact_L048_masks_unchanged':True,'all930_inputs_finite_with_positive_preentry_denominators':True,'only_three_fixed_measures':True,'current500_uses_original_frozen_block_quarter_bootstrap_draws':True,'current500_raw_primary_and_AI_increment_reproduced':True,'source_sha256':hashes,'all_sources_unchanged':all(sha(ROOT/p)==h for p,h in hashes.items())}
assert audit['all_sources_unchanged'];save('audit.json',audit)
for r in results:
    if r['policy']=='AI_selected_L048':print(json.dumps(clean(r),indent=2))
print('AIincrements',json.dumps(clean(increments),indent=2))
