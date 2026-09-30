"""Finite same-moment managed-exit discovery; every original trade retained."""
from pathlib import Path
import hashlib,json
import numpy as np,pandas as pd
from engine import replay,POLICIES,CANDIDATES,CONTROLS

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
SOURCE=ROOT/'data/analysis/new-angles-20260930/target_exhaustion'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
    if isinstance(v,np.integer):return int(v)
    if isinstance(v,np.bool_):return bool(v)
    if isinstance(v,(float,np.floating)):return float(v) if np.isfinite(v) else None
    return v
def save(name,v):(HERE/name).write_text(json.dumps(clean(v),indent=2,allow_nan=False)+'\n')
def stats(x):
    x=np.asarray(x,float);n=len(x)
    if not n:return {'n':0}
    ordered=np.sort(x);pos=x[x>1e-12];neg=x[x< -1e-12]
    return {'n':n,'mean_gross_pct':x.mean(),'median_gross_pct':np.median(x),'wins':len(pos),'losses':len(neg),'breakeven':int((np.abs(x)<=1e-12).sum()),
        'win_rate':len(pos)/n,'loss_rate':len(neg)/n,'breakeven_rate':(np.abs(x)<=1e-12).mean(),'mean_winner_pct':pos.mean() if len(pos) else np.nan,'mean_loser_pct':neg.mean() if len(neg) else np.nan,
        'profit_factor':pos.sum()/-neg.sum() if len(neg) else np.nan,'best_pct':x.max(),'worst_pct':x.min(),'sum_trade_pct_not_portfolio':x.sum(),
        'exclude_best1_mean_pct':ordered[:-1].mean() if n>1 else np.nan,'exclude_best3_mean_pct':ordered[:-3].mean() if n>3 else np.nan,'top3_sum_pct':ordered[-3:].sum()}
def bootstrap(matrix,groups,seed):
    code,labels=pd.factorize(groups,sort=True);counts=np.bincount(code,minlength=len(labels));sums=np.zeros((len(labels),matrix.shape[0]));np.add.at(sums,code,matrix.T)
    weights=np.random.default_rng(seed).multinomial(len(labels),np.full(len(labels),1/len(labels)),size=20000)
    return (weights@sums)/(weights@counts)[:,None],weights,labels
def ci(x):return np.quantile(x,[.025,.975])

def main():
    assert json.loads((HERE/'synthetic_audit.json').read_text())['passed']
    sources=[HERE/'PLAN.md',HERE/'engine.py',Path(__file__),HERE/'test_synthetic.py',SOURCE/'windows.csv',SOURCE/'paths.npz']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sources};save('SCORING_FREEZE.json',{'source_sha256':hashes,'candidate_count':3,'control_count':2,'model_calls':0,'phase':'existing_outcome_exit_extension'})
    w=pd.read_csv(SOURCE/'windows.csv');w.entry_time=pd.to_datetime(w.entry_time);a=np.load(SOURCE/'paths.npz');paths=a['paths']
    assert len(w)==1020 and w.window_id.nunique()==1020 and paths.shape==(1020,361,4) and np.array_equal(a['window_id'],w.window_id)
    assert np.isfinite(paths).all() and (paths>0).all() and np.isfinite(w.atr14_pct).all() and (w.atr14_pct>0).all()
    assert w.action.isin(['long','short']).all()
    signs=np.where(w.action.eq('short'),1,-1);w['position_side']=np.where(signs==1,'long','short')
    w['quarter']=w.entry_time.dt.to_period('Q').astype(str);w['year']=w.entry_time.dt.year
    unique=np.sort(w.entry_time.unique());block={t:i for i,t in enumerate(unique)};bc=np.array([block[t] for t in w.entry_time.to_numpy()]);fold=np.zeros(len(unique),int);half=fold.copy();third=fold.copy()
    for i,ids in enumerate(np.array_split(np.arange(len(unique)),5),1):fold[ids]=i
    for i,ids in enumerate(np.array_split(np.arange(len(unique)),2),1):half[ids]=i
    for i,ids in enumerate(np.array_split(np.arange(len(unique)),3),1):third[ids]=i
    w['calendar_block']=bc;w['calendar_fold']=fold[bc];w['calendar_half']=half[bc];w['calendar_third']=third[bc]
    ledger=[];eventrows=[];gross=np.empty((len(POLICIES),len(w)));fields={}
    for pi,policy in enumerate(POLICIES):
        current=[]
        for i,row in w.iterrows():
            r,events=replay(paths[i],row.atr14_pct,int(signs[i]),policy,events=True)
            gross[pi,i]=r['gross_pct'];r.update(policy=policy,window_id=row.window_id,asset=row.asset,cohort=row.cohort,entry_time=str(row.entry_time),AI_action=row.action,position_side=row.position_side,atr_pct=row.atr14_pct,
                calendar_block=int(row.calendar_block),quarter=row.quarter,year=int(row.year),calendar_fold=int(row.calendar_fold),calendar_half=int(row.calendar_half),calendar_third=int(row.calendar_third))
            ledger.append(r);current.append(r)
            eventrows.extend({'policy':policy,'window_id':row.window_id,**x} for x in events)
        fields[policy]=pd.DataFrame(current)
        print(policy,stats(gross[pi]),flush=True)
    # The no-stop control must exactly reconcile with native first-open /240close.
    raw=signs*(paths[:,240,3]/paths[:,1,0]-1)*100
    assert np.allclose(gross[-1],raw,rtol=0,atol=1e-10)
    # Fixed-stop control independently checks the existing previously proven engine.
    import sys
    sys.path.insert(0,str(ROOT/'data/analysis/reversal-deep-20260929/risk'))
    from validation_engine import bracket_batch
    # Shift only the engine's artificial previous close to first open; native future bars stay exact.
    same=paths.copy();same[:,0,3]=paths[:,1,0]
    fixed=bracket_batch(same,w.atr14_pct.to_numpy(),sign=signs,rr=1e6,horizon=240)['gross_pct']
    assert np.allclose(fixed,gross[POLICIES.index('FIXED_1ATR_stop')],atol=1e-10,rtol=0)
    bm,bw,bl=bootstrap(gross,w.entry_time,2026093041);qm,qw,ql=bootstrap(gross,w.quarter,2026093042)
    summaries={};breakdown=[];contrasts=[];tails=[];rank=[]
    for pi,policy in enumerate(POLICIES):
        r={'pooled':stats(gross[pi]),'calendar_blocks':len(bl),'quarters':len(ql),'block_ci95':ci(bm[:,pi]),'quarter_ci95':ci(qm[:,pi]),
            'halves':[stats(gross[pi,w.calendar_half.eq(k)]) for k in [1,2]],'thirds':[stats(gross[pi,w.calendar_third.eq(k)]) for k in [1,2,3]],
            'cohorts':{x:stats(gross[pi,w.cohort.eq(x)]) for x in sorted(w.cohort.unique())},'position_sides':{x:stats(gross[pi,w.position_side.eq(x)]) for x in ['long','short']},
            'assets':{x:stats(gross[pi,w.asset.eq(x)]) for x in sorted(w.asset.unique())},
            'minimum_leave_one_quarter_out_mean_pct':min(gross[pi,w.quarter.ne(x)].mean() for x in ql)}
        frame=fields[policy]
        r['execution_counts']={x:int(frame[x].sum()) for x in ['protection_armed','partial_executed','ambiguous_partial_target_stop','trigger_and_stop_same_bar','adverse_open_overrun_of_stop','adverse_open_move_from_previous_close']}
        r['outcomes']=frame.outcome.value_counts().to_dict();r['median_final_elapsed_upper_minutes']=frame.exit_elapsed_upper_minutes.median()
        for category in ['cohort','position_side','asset','calendar_fold','calendar_half','calendar_third','year','quarter']:
            for value in sorted(w[category].unique()):
                mask=w[category].eq(value).to_numpy();breakdown.append({'policy':policy,'category':category,'value':str(value),**stats(gross[pi,mask])})
        for idx in np.argsort(gross[pi])[-3:][::-1]:tails.append({'policy':policy,'window_id':w.iloc[idx].window_id,'entry_time':str(w.iloc[idx].entry_time),'asset':w.iloc[idx].asset,'cohort':w.iloc[idx].cohort,'gross_pct':gross[pi,idx]})
        if policy in CANDIDATES:
            control_i=POLICIES.index('FIXED_1ATR_stop');diff=gross[pi]-gross[control_i]
            gates={'pooled_positive':r['pooled']['mean_gross_pct']>0,'both_halves_positive':all(x['mean_gross_pct']>0 for x in r['halves']),
                'at_least4_of5_cohorts_positive':sum(x['mean_gross_pct']>0 for x in r['cohorts'].values())>=4,
                'exclude_best3_positive':r['pooled']['exclude_best3_mean_pct']>0,'fixed_stop_paired_improvement_positive':diff.mean()>0}
            r['discovery_triage']={'criteria':gates,'passed':all(gates.values()),'failed':[k for k,v in gates.items() if not v]}
            for control in CONTROLS:
                j=POLICIES.index(control);dv=gross[pi]-gross[j]
                contrasts.append({'candidate':policy,'control':control,'all':stats(dv),'block_ci95':ci(bm[:,pi]-bm[:,j]),'quarter_ci95':ci(qm[:,pi]-qm[:,j]),
                    'cohorts':{x:stats(dv[w.cohort.eq(x)]) for x in sorted(w.cohort.unique())},'position_sides':{x:stats(dv[w.position_side.eq(x)]) for x in ['long','short']},
                    'halves':[stats(dv[w.calendar_half.eq(k)]) for k in [1,2]],'does_not_establish_incremental_AI_information':True})
        summaries[policy]=r;rank.append({'policy':policy,**r['pooled'],'block_ci95_low':r['block_ci95'][0],'block_ci95_high':r['block_ci95'][1],'quarter_ci95_low':r['quarter_ci95'][0],'quarter_ci95_high':r['quarter_ci95'][1]})
    save('summary.json',{'phase':'reused_outcome_discovery_exit_extension','new_model_calls':0,'windows':len(w),'calendar_blocks':len(unique),'policies':summaries,'candidates':CANDIDATES,'controls':CONTROLS})
    save('matched_control_differences.json',contrasts)
    pd.DataFrame(ledger).to_csv(HERE/'trade_ledger.csv',index=False);pd.DataFrame(eventrows).to_csv(HERE/'execution_events.csv',index=False)
    pd.DataFrame(breakdown).to_csv(HERE/'breakdown.csv',index=False);pd.DataFrame(tails).to_csv(HERE/'largest_winners.csv',index=False);pd.DataFrame(rank).to_csv(HERE/'policy_summary.csv',index=False)
    np.savez_compressed(HERE/'policy_vectors.npz',gross_pct=gross,policy=np.array(POLICIES),window_id=w.window_id.to_numpy(str),entry_time=w.entry_time.astype(str).to_numpy(str),asset=w.asset.to_numpy(str),cohort=w.cohort.to_numpy(str),position_side=w.position_side.to_numpy(str),calendar_block=bc)
    np.savez_compressed(HERE/'bootstrap_arrays.npz',block_means=bm,quarter_means=qm,block_weights=bw,quarter_weights=qw,policy=np.array(POLICIES),quarter=np.asarray(ql,dtype=str))
    assert all(sha(ROOT/p)==h for p,h in hashes.items())
    save('evaluation_audit.json',{'passed':True,'source_sha256':hashes,'source_windows':1020,'evaluated_trades':len(ledger),'candidates':3,'controls':2,'events':len(eventrows),'raw_time_control_matches_native':True,'fixed_stop_matches_previous_proven_engine':True,'max_fixed_stop_error_pct':np.max(np.abs(fixed-gross[3])),'max_raw_hold_error_pct':np.max(np.abs(raw-gross[4])),'no_new_model_calls':True})
    print('Finished; all controls and source hashes verified.',flush=True)

if __name__=='__main__':main()
