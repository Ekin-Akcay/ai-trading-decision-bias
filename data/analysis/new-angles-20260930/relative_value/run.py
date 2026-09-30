"""Twelve predeclared cross-sectional policies. Discovery only; no model calls."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
RUN=ROOT/'data/sim/gross-edge-500-20260929T204545Z'
ASSETS=['SOL-USD','BTC-USD','ETH-USD','DOGE-USD']
SCORES=['AI_direction','AI_confidence','AI_stop_ATR_conviction','price_momentum','price_MA20_ATR','price_ATR']

def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
    if isinstance(v,np.integer):return int(v)
    if isinstance(v,np.bool_):return bool(v)
    if isinstance(v,(float,np.floating)):return float(v) if np.isfinite(v) else None
    return v

def save(name,v):(HERE/name).write_text(json.dumps(clean(v),indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def ranked_weights(scores):
    lo=scores==scores.min(axis=1,keepdims=True);hi=scores==scores.max(axis=1,keepdims=True)
    active=~np.all(lo,axis=1)
    w=.5*lo/lo.sum(1,keepdims=True)-.5*hi/hi.sum(1,keepdims=True)
    assert np.allclose(w.sum(1),0) and np.allclose(np.abs(w).sum(1),active.astype(float))
    return w,active

def stats(x,active):
    x=np.asarray(x,float);active=np.asarray(active,bool);z=x[active];n=len(z);N=len(x)
    if n==0:return {'opportunities':N,'active':0,'frequency':0,'mean_per_opportunity_pct':x.mean() if N else np.nan}
    o=np.sort(z);pos=z[z>0];neg=z[z<0]
    return dict(opportunities=N,active=n,frequency=n/N,mean_per_opportunity_pct=x.mean(),mean_per_active_pct=z.mean(),median_per_active_pct=np.median(z),
        active_win_rate=(z>0).mean(),wins=int((z>0).sum()),mean_winner_pct=pos.mean() if len(pos) else np.nan,
        mean_loser_pct=neg.mean() if len(neg) else np.nan,profit_factor=pos.sum()/-neg.sum() if len(neg) else np.nan,
        sum_block_percentages_not_compounded=z.sum(),best_pct=z.max(),worst_pct=z.min(),
        ex_best1_active_mean_pct=o[:-1].mean() if n>1 else np.nan,ex_best3_active_mean_pct=o[:-3].mean() if n>3 else np.nan,
        top1_sum_pct=o[-1],top3_sum_pct=o[-3:].sum(),top3_fraction_positive_gains=o[-3:].sum()/pos.sum() if len(pos) else np.nan)

def main():
    sources=[HERE/'PLAN.md',RUN/'window_results.csv',RUN/'paths.npz']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
    d=pd.read_csv(sources[1]);d.entry_time=pd.to_datetime(d.entry_time)
    assert len(d)==500 and len(d.block.unique())==125 and d.window_id.nunique()==500
    assert d.groupby('block').asset.apply(set).eq(set(ASSETS)).all()
    assert d.groupby('block').entry_time.nunique().eq(1).all()
    cache=np.load(sources[2]);paths=cache['paths'];assert paths.shape==(500,361,4)
    path_by_window={s:i for i,s in enumerate(cache['window_id'])}
    assert set(path_by_window)==set(d.window_id)
    blockmeta=d[['block','entry_time']].drop_duplicates().sort_values('entry_time').reset_index(drop=True)
    index=pd.MultiIndex.from_product([blockmeta.block,ASSETS],names=['block','asset'])
    order=d.set_index(['block','asset']).loc[index].reset_index();assert len(order)==500
    rowids=np.array([path_by_window[x] for x in order.window_id]);p=paths[rowids]
    assert np.isfinite(p).all() and (p>0).all()
    assert np.allclose(p[:,0,3],order.price_real,atol=1e-8,rtol=0)
    ep=p[:,1,0];xp=p[:,240,3];returns=((xp/ep-1)*100).reshape(125,4)
    sign=np.where(order.action.eq('long'),1.,-1.);assert order.action.isin(['long','short']).all()
    conf=order.confidence.to_numpy();atr=order.atr14_pct.to_numpy();stop=order.stop_pct.to_numpy()*100
    assert np.isfinite(np.c_[conf,atr,stop]).all() and (atr>0).all() and (stop>0).all() and ((conf>=0)&(conf<=1)).all()
    scores=np.stack([sign,sign*conf,sign*conf/(stop/atr),order.ret_vis_pct.to_numpy(),(100/order.ma20_now.to_numpy()-1)*100/atr,atr]).reshape(6,125,4)
    assert np.isfinite(scores).all()
    policy=[];weights=[];active=[];families=[]
    for name,score in zip(SCORES,scores):
        rw,act=ranked_weights(score)
        for mode,mult in [('reverse',1),('follow',-1)]:
            policy.append(name+'__'+mode);weights.append(mult*rw);active.append(act.copy());families.append('AI' if name.startswith('AI') else 'price_only')
    weights=np.asarray(weights);active=np.asarray(active);gross=np.einsum('pba,ba->pb',weights,returns)
    assert len(policy)==12 and weights.shape==(12,125,4) and np.allclose(gross[::2],-gross[1::2])
    # Independent scalar basket calculation, including all tied side allocations.
    for pi in range(12):
        for b in range(125):
            v=sum(float(weights[pi,b,a])*float(returns[b,a]) for a in range(4))
            assert abs(v-gross[pi,b])<1e-12
    quarters=blockmeta.entry_time.dt.to_period('Q').astype(str);qc,ql=pd.factorize(quarters,sort=True)
    qn=np.bincount(qc,minlength=len(ql));rng=np.random.default_rng(2026093018);bw=rng.multinomial(125,np.full(125,1/125),size=20000)
    rng=np.random.default_rng(2026093019);qw=rng.multinomial(len(ql),np.full(len(ql),1/len(ql)),size=20000)
    bmeans=bw@gross.T/125;qs=np.zeros((len(ql),12));np.add.at(qs,qc,gross.T);qmeans=(qw@qs)/(qw@qn)[:,None]
    folds=np.repeat(np.arange(1,6),25);halves=np.zeros(125,int);halves[np.array_split(np.arange(125),2)[1]]=1
    results=[];foldrows=[];prefixrows=[];quarterrows=[];contrastrows=[];weightrows=[];rankrows=[];largest=[];candidates=[]
    summaries={}
    for pi,name in enumerate(policy):
        x=gross[pi];act=active[pi];r={'policy':name,'family':families[pi],**stats(x,act)}
        r.update(block_ci95_low=np.quantile(bmeans[:,pi],.025),block_ci95_high=np.quantile(bmeans[:,pi],.975),quarter_ci95_low=np.quantile(qmeans[:,pi],.025),quarter_ci95_high=np.quantile(qmeans[:,pi],.975))
        hs=[stats(x[halves==j],act[halves==j]) for j in range(2)]
        fs=[]
        for k in range(1,6):
            mask=folds==k;z=stats(x[mask],act[mask]);fs.append(z);foldrows.append({'policy':name,'fold':k,'start':str(blockmeta.entry_time[mask].min()),'end':str(blockmeta.entry_time[mask].max()),**z})
            if k>=2:prefixrows.append({'policy':name,'test_fold':k,'past_blocks':int((folds<k).sum()),'past_mean_pct':x[folds<k].mean(),'future25_mean_pct':x[mask].mean(),'past_active':int(act[folds<k].sum()),'future_active':int(act[mask].sum()),'no_policy_fitting_or_selection':True})
        for q in ql:
            m=quarters.eq(q).to_numpy();quarterrows.append({'policy':name,'quarter':q,**stats(x[m],act[m])})
        loo=[x[quarters.ne(q).to_numpy()].mean() for q in ql]
        r['minimum_leave_one_quarter_out_opportunity_mean_pct']=min(loo);r['selected_quarters']=int(quarters[act].nunique())
        r['half1_opportunity_mean_pct']=hs[0]['mean_per_opportunity_pct'];r['half2_opportunity_mean_pct']=hs[1]['mean_per_opportunity_pct']
        r['later100_opportunity_mean_pct']=x[folds>=2].mean();r['positive_later25_folds']=sum(y['mean_per_opportunity_pct']>0 for y in fs[1:])
        market=returns.mean(1);r['correlation_with_equal_weight_market']=np.corrcoef(x,market)[0,1] if np.std(x)>0 else np.nan
        criteria={'at_least40_active':int(act.sum())>=40,'both_halves_positive':all(h['mean_per_opportunity_pct']>0 for h in hs),'at_least3_later_folds_positive':r['positive_later25_folds']>=3,
            'later100_positive':r['later100_opportunity_mean_pct']>0,'exclude_best3_positive':r.get('ex_best3_active_mean_pct',-np.inf)>0,'leave_one_quarter_out_positive':min(loo)>0}
        r['discovery_stability_screen_pass']=all(criteria.values());r['failed_discovery_conditions']=';'.join(k for k,v in criteria.items() if not v)
        results.append(r);summaries[name]={'summary':r,'chronological_halves':hs,'folds':fs,'criteria':criteria}
        if pi in [0,2,4] and all(criteria.values()):candidates.append(name)
        for a,asset in enumerate(ASSETS):weightrows.append({'policy':name,'asset':asset,'mean_signed_weight':weights[pi,:,a].mean(),'mean_abs_weight':np.abs(weights[pi,:,a]).mean(),
            'long_blocks':int((weights[pi,:,a]>0).sum()),'short_blocks':int((weights[pi,:,a]<0).sum()),'mean_opportunity_contribution_pct':(weights[pi,:,a]*returns[:,a]).mean()})
        for b in np.argsort(x)[-3:][::-1]:largest.append({'policy':name,'block':int(blockmeta.block[b]),'entry_time':str(blockmeta.entry_time[b]),'gross_pct':x[b],**{a:weights[pi,b,j] for j,a in enumerate(ASSETS)}})
    # All cross-sectional controls remain in the finite family, even when they look better.
    for pi in [0,2,4]:
        for ci in range(6,12):
            delta=gross[pi]-gross[ci];bd=bmeans[:,pi]-bmeans[:,ci];qd=qmeans[:,pi]-qmeans[:,ci]
            matched_delta=np.where(active[pi],delta,0);mb=bw@matched_delta/125
            mqsum=np.bincount(qc,weights=matched_delta,minlength=len(ql));mq=(qw@mqsum)/(qw@qn)
            contrastrows.append({'AI_policy':policy[pi],'control_policy':policy[ci],'difference_per_opportunity_pct':delta.mean(),'block_ci95_low':np.quantile(bd,.025),'block_ci95_high':np.quantile(bd,.975),
                'quarter_ci95_low':np.quantile(qd,.025),'quarter_ci95_high':np.quantile(qd,.975),'AI_active_blocks':int(active[pi].sum()),
                'AI_active_only_conditional_difference_pct':delta[active[pi]].mean(),'matched_skip_difference_per_opportunity_pct':matched_delta.mean(),
                'matched_skip_block_ci95_low':np.quantile(mb,.025),'matched_skip_block_ci95_high':np.quantile(mb,.975),
                'matched_skip_quarter_ci95_low':np.quantile(mq,.025),'matched_skip_quarter_ci95_high':np.quantile(mq,.975),'conditional_comparison_is_AI_gated':True})
    # Spearman ranks show whether the model points the wrong way within a timestamp.
    rr=pd.DataFrame(returns).rank(axis=1,method='average').to_numpy()
    for si,name in enumerate(SCORES):
        sr=pd.DataFrame(scores[si]).rank(axis=1,method='average').to_numpy()
        for b in range(125):
            valid=np.std(sr[b])>0 and np.std(rr[b])>0
            rankrows.append({'score':name,'block':int(blockmeta.block[b]),'entry_time':str(blockmeta.entry_time[b]),'rank_correlation':np.corrcoef(sr[b],rr[b])[0,1] if valid else np.nan,'defined':bool(valid)})
    # No automatic winner selection: a stability pass is only a necessary screen.
    save('summary.json',{'phase':'known_outcome_discovery_only','policies':summaries,'AI_reverse_stability_passes':candidates,'candidate_recommendations_require_control_review':True,
        'economic_units':125,'model_calls_this_study':0,'horizon_minutes':240,'cost_bps':0,'gross_notional':1,'net_dollars':0,'beta_neutrality_claim':False})
    for filename,rows in [('all_policies',results),('chronological_folds',foldrows),('expanding_prefix_transfers',prefixrows),('quarter_breakdown',quarterrows),('paired_price_control_differences',contrastrows),('asset_weight_contributions',weightrows),('cross_sectional_rank_correlations',rankrows),('largest_blocks',largest)]:pd.DataFrame(rows).to_csv(HERE/(filename+'.csv'),index=False)
    order['entry_open']=ep;order['exit_240_close']=xp;order['gross_asset_return_pct']=returns.reshape(-1);order.to_csv(HERE/'asset_window_vectors.csv',index=False)
    blockmeta['fold']=folds;blockmeta['quarter']=quarters;blockmeta.to_csv(HERE/'calendar_blocks.csv',index=False)
    np.savez_compressed(HERE/'relative_value_family.npz',gross_pct=gross,selected=active,weights=weights,policy=np.asarray(policy,dtype=str),block=blockmeta.block.to_numpy(),entry_time=blockmeta.entry_time.astype(str).to_numpy(str),asset=np.asarray(ASSETS),asset_return_pct=returns,
        window_id=order.window_id.to_numpy(str).reshape(125,4),scores=scores,score_name=np.asarray(SCORES,dtype=str),fold=folds)
    np.savez_compressed(HERE/'bootstrap_arrays.npz',policy=np.asarray(policy),block_mean=bmeans,quarter_mean=qmeans)
    audit={'passed':True,'blocks':125,'asset_windows':500,'finite_policies':12,'independent_scalar_basket_checks':1500,'all_reverse_follow_vectors_exact_negatives':bool(np.array_equal(gross[::2],-gross[1::2])),
        'all_active_baskets_zero_dollars_unit_gross':True,'source_sha256':hashes,'all_sources_preserved':all(sha(ROOT/k)==v for k,v in hashes.items()),'no_new_model_calls':True}
    save('audit.json',audit)
    print(pd.DataFrame(results)[['policy','active','mean_per_opportunity_pct','mean_per_active_pct','half1_opportunity_mean_pct','half2_opportunity_mean_pct','later100_opportunity_mean_pct','positive_later25_folds','ex_best3_active_mean_pct','discovery_stability_screen_pass']].to_string(index=False),flush=True)
    print('AI reverse stability passes:',candidates,flush=True)

if __name__=='__main__':main()
