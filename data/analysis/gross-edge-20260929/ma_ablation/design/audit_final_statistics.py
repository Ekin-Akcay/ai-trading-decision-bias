"""Independent paired-study reproduction. Requires explicit parent outcome release."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,math,importlib.util
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;STUDY=HERE.parent;ROOT=HERE.parents[4]
spec=importlib.util.spec_from_file_location('independent_prior_audit',HERE.parents[1]/'design/audit_final_statistics.py')
independent=importlib.util.module_from_spec(spec);spec.loader.exec_module(independent)
eq=independent.eq;row_estimator=independent.row_weight_estimator
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def intervals(v):
    a=np.asarray(v);a=a[np.isfinite(a)]
    return {k:np.quantile(a,q) if len(a) else [np.nan,np.nan] for k,q in [('ci95',[.025,.975]),('ci99',[.005,.995])]}

def check_stats(v,s):
    v=np.asarray(v,float);assert len(v)==s['n']
    if not len(v):return
    eq(v.mean(),s['mean_gross_pct']);eq(np.median(v),s['median_gross_pct']);eq(v.sum(),s['gross_sum_pct'])
    assert int((v>0).sum())==s['wins'];eq((v>0).mean(),s['win_rate'])
    for n in [1,3]:eq(np.sort(v)[:-n].mean() if len(v)>n else np.nan,s['exclude_best'+str(n)+'_mean_pct'])

def main():
    assert '--released-by-root' in sys.argv,'Explicit parent release is required'
    run=Path(json.loads((STUDY/'run.json').read_text())['run_dir']);assert (run/'ALLOW_EVALUATION').exists()
    m=json.loads((run/'manifest.json').read_text());summary=json.loads((run/'summary.json').read_text())
    lock=json.loads((STUDY/'analysis_lock.json').read_text());assert all(sha(ROOT/p)==h for p,h in lock['files'].items())
    audit=json.loads((run/'isolation_audit.json').read_text());passed={x['agent_path'] for x in audit['audits'] if x['passed']}
    rows=[json.loads(s) for s in (run/'accepted_decisions.jsonl').read_text().splitlines()]
    assert len(rows)==270 and len({r['case'] for r in rows})==270 and len({r['thread_id'] for r in rows})==270
    assert sorted(r['case'] for r in rows)==list(range(1,271))
    assert all(r['agent_path'] in passed and not r['tool_calls'] and r['model']=='gpt-5.6-terra' for r in rows)
    assert all(r['decision']['action'] in ['long','short'] for r in rows)
    assert all(sha(ROOT/p)==h for p,h in m['original_sha256'].items())
    decisions={r['case']:r['decision'] for r in rows};cases=pd.DataFrame(m['cases'])
    assert len(cases)==270 and len(cases[['block','arm']].drop_duplicates())==270
    for c in m['cases']:
        folder=Path(c['stimulus_dir'])
        for name,key in [('stats.txt','prompt_sha256'),('input.txt','input_sha256'),('chart.png','image_sha256')]:assert sha(folder/name)==c[key]
    d=cases[cases.arm=='MA_A'].sort_values('block').reset_index(drop=True);assert list(d.block)==list(range(1,91))
    actions={a:np.array([decisions[c]['action'] for c in cases[cases.arm==a].sort_values('block').case]) for a in ['MA_A','MA_B','NO_MA']}
    dates=pd.DatetimeIndex(d.entry_time);quarters=dates.to_period('Q').astype(str);qlabels=sorted(set(quarters));q=np.array([qlabels.index(x) for x in quarters]);G=len(qlabels)
    era=np.where(dates.year<=2021,'2020-21',np.where(dates.year<=2023,'2022-23','2024-26'))
    regime=np.where((d.ma20_now<=100)&(d.ma50_now<=100),'above_both',np.where((d.ma20_now>=100)&(d.ma50_now>=100),'below_both','mixed'))
    names=np.array([a+'|'+b for a,b in zip(era,regime)]);labels=sorted(set(names));strata=np.array([labels.index(x) for x in names])
    native=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index()
    paths=[]
    for date,price in zip(dates,d.price_real):
        frame=native.loc[date-pd.Timedelta(minutes=1):date+pd.Timedelta(minutes=359)]
        assert frame.index.equals(pd.date_range(date-pd.Timedelta(minutes=1),periods=361,freq='min'))
        v=frame[['open','high','low','close']].to_numpy(float);assert np.isfinite(v).all() and (v>0).all()
        assert (v[:,1]>=np.maximum.reduce([v[:,0],v[:,2],v[:,3]])).all() and (v[:,2]<=np.minimum.reduce([v[:,0],v[:,1],v[:,3]])).all()
        eq(v[0,3],price);paths.append(v)
    paths=np.array(paths);eq(paths,np.load(run/'paths.npz')['paths'])
    values=np.array([(p[240,3]-p[1,0])/p[1,0]*100 for p in paths])
    delays={k:np.array([(p[240,3]-p[k+1,0])/p[k+1,0]*100 for p in paths]) for k in [1,5]}
    for asset,period in [('SOL-USD',50),('BTC-USD',200)]:
        daily=pd.read_csv(ROOT/f'data/raw/{asset}.csv',index_col=0,parse_dates=True).sort_index()
        daily['average']=daily.close.rolling(period,min_periods=period).mean()
        previous=daily.reindex(dates.normalize()-pd.Timedelta(days=1));assert previous.close.notna().all() and (previous.close<=previous.average).all()
    bw=np.random.default_rng(2026092997).multinomial(90,np.full(90,1/90),size=20000)
    qw=np.random.default_rng(2026092998).multinomial(G,np.full(G,1/G),size=20000)
    saved=np.load(run/'bootstrap_arrays.npz');assert np.array_equal(bw,saved['weights']) and np.array_equal(qw,saved['quarter_weights'])
    ledger=pd.read_csv(run/'strategy_trades.csv');assert len(ledger)==270
    arm_details={};opp={};eligible=np.ones(90,bool);chronological=np.argsort(dates.to_numpy())
    for arm in actions:
        take=actions[arm]=='short';n=int(take.sum());s=summary['arms'][arm];assert s['short_calls']==n and s['long_calls']==90-n
        check_stats(values[take],s['selected']);opp[arm]=np.where(take,values,0);check_stats(opp[arm],s['opportunity']);eq(opp[arm],saved[arm+'_opportunity'])
        l=ledger[ledger.arm==arm].sort_values('block');assert np.array_equal(l.selected,take)
        eq(l.gross_pct,values);eq(l.opportunity_gross_pct,opp[arm]);eq(l.entry_price,paths[:,1,0]);eq(l.exit_price,paths[:,240,3])
        for k in [1,5]:eq(l['delay'+str(k)+'_gross_pct'],delays[k]);check_stats(delays[k][take],s['delays'][str(k)])
        eq(l.mae_pct,np.minimum(0,100*(paths[:,1:241,2].min(axis=1)/paths[:,1,0]-1)))
        eq(l.mfe_pct,np.maximum(0,100*(paths[:,1:241,1].max(axis=1)/paths[:,1,0]-1)))
        for h in [15,30,60,105,240]:eq(l['long_move_'+str(h)+'m_pct'],100*(paths[:,h,3]/paths[:,1,0]-1))
        original_mean,original_inc=row_estimator(values,take,eligible,strata,np.zeros(90,int),np.ones((1,1)))
        eq(original_inc[0],s['AI_increment_mean_pct']);eq(original_mean[0]-original_inc[0],s['standardized_price_baseline_mean_pct'])
        all_intervals={}
        for kind,groups,weights,prefix in [('window',np.arange(90),bw,''),('quarter',q,qw,'q')]:
            mean,inc=row_estimator(values,take,eligible,strata,groups,weights)
            eq(mean,saved[arm+'_'+prefix+'mean']);eq(inc,saved[arm+'_'+prefix+'increment'])
            for key,arr in [('profit',mean),('increment',inc)]:
                actual=intervals(arr);all_intervals[kind+'_'+key]=actual
                for level,bounds in actual.items():eq(bounds,s[kind+'_'+key+'_intervals'][level])
            opportunity_draws=weights[:,groups]@opp[arm]/weights[:,groups].sum(1)
            claim='opportunity_intervals' if kind=='window' else 'quarter_opportunity_intervals'
            for level,bounds in intervals(opportunity_draws).items():eq(bounds,s[claim][level])
        halves=[values[ids[take[ids]]] for ids in np.array_split(chronological,2)]
        for values_part,st in zip(halves,s['chronological_halves']):check_stats(values_part,st)
        for j,label in enumerate(qlabels):check_stats(values[take&(q==j)],s['quarters'][label])
        for ids,st in zip(np.array_split(chronological,3),s['chronological_thirds']):check_stats(values[ids[take[ids]]],st)
        criteria={'at_least50trades':n>=50,'window99_lower_positive':all_intervals['window_profit']['ci99'][0]>0,
                  'quarter95_lower_positive':all_intervals['quarter_profit']['ci95'][0]>0,
                  'both_halves_positive':all(len(v) and v.mean()>0 for v in halves),
                  'both_delays_positive':all(n and v[take].mean()>0 for v in delays.values()),
                  'remove_best3_positive':n>3 and np.sort(values[take])[:-3].mean()>0}
        assert criteria==s['profit_criteria'] and bool(arm=='MA_A' and all(criteria.values()))==s['profit_verified']
        icriteria={'window99_increment_lower_positive':all_intervals['window_increment']['ci99'][0]>0,'quarter95_increment_lower_positive':all_intervals['quarter_increment']['ci95'][0]>0}
        assert icriteria==s['AI_increment_criteria'] and bool(arm=='MA_A' and all(icriteria.values()))==s['AI_increment_verified']
        arm_details[arm]={'n':n,'mean_gross_pct':float(values[take].mean()) if n else None,'AI_increment_pct':float(original_inc[0]) if n else None,'profit_criteria':{k:bool(v) for k,v in criteria.items()},'profit_verified':s['profit_verified'],'AI_increment_verified':s['AI_increment_verified']}
    treatment=actions['NO_MA']!=actions['MA_A'];repeat=actions['MA_B']!=actions['MA_A'];delta=treatment.astype(int)-repeat.astype(int)
    b=int((delta==1).sum());c=int((delta==-1).sum());nd=b+c
    # Independent recurrence for binomial tail instead of summing combinations.
    mass=2.**(-nd);p=0.
    for k in range(nd+1):
        if k>=b:p+=mass
        if k<nd:mass*=float(nd-k)/(k+1)
    if not nd:p=1.
    s=summary['mechanism'];assert s['discordant_treatment_only']==b and s['discordant_repeat_only']==c
    eq(p,s['exact_one_sided_p']);eq(delta.mean(),s['excess_flip_rate']);eq(treatment.mean(),s['treatment_flip_rate']);eq(repeat.mean(),s['ordinary_flip_rate'])
    db=bw@delta/90;eq(db,saved['mechanism_delta_boot'])
    for level,v in intervals(db).items():eq(v,s['excess_flip_rate_intervals'][level])
    assert s['MA_information_dependence_verified']==bool(p<.01 and delta.mean()>0)
    signed=(actions['MA_A']=='short').astype(int)-(actions['NO_MA']=='short').astype(int)
    eq(signed.mean(),s['short_frequency_reduction_NO_MA_vs_A'])
    for level,v in intervals(bw@signed/90).items():eq(v,s['short_reduction_intervals'][level])
    for arm in ['MA_B','NO_MA']:
        s=summary['secondary_per_opportunity_comparisons'][arm+'_minus_MA_A'];diff=opp[arm]-opp['MA_A'];eq(diff.mean(),s['mean_per_opportunity_difference_pct'])
        for kind,w,g in [('window',bw,np.arange(90)),('quarter',qw,q)]:
            draws=w[:,g]@diff/w[:,g].sum(1)
            for level,v in intervals(draws).items():eq(v,s[kind+'_intervals'][level])
    budget=json.loads((STUDY.parent/'snapshot_budget.json').read_text());assert len(budget['reserved_attempts'])<=800
    out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'run_id':m['run_id'],'unique_windows':90,'accepted_isolated_calls':270,'physical_calls_in_current800_budget':len(budget['reserved_attempts']),
         'native_paths_and_daily_gates_rechecked':90,'arms_reconstructed':arm_details,'all_20000_window_and_quarter_arrays_match':True,'all_intervals_and_verification_flags_match':True,
         'exact_p_independently_reproduced':p,'mechanism_verified':summary['mechanism']['MA_information_dependence_verified'],'all_source_and_stimulus_hashes_match':True,'model_calls':0}
    (HERE/'final_statistics_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
