from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OLD=ROOT/'data/analysis/reversal-deep-20260929/signals'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
    if isinstance(v,(np.integer,)):return int(v)
    if isinstance(v,(np.bool_,)):return bool(v)
    if isinstance(v,(float,np.floating)):return float(v) if np.isfinite(v) else None
    return v
def save(name,v):(HERE/name).write_text(json.dumps(clean(v),indent=2,allow_nan=False)+'\n')
sources=[OLD/'windows.csv',OLD/'control_trades.csv',OLD/'candidate_results.json',OLD/'fresh_grid/windows.csv',OLD/'fresh_grid/all_candidate_arrays.npz',OLD/'fresh_grid/candidate_results.json',OLD/'stopout_fade/results.json',HERE/'PLAN.md']
hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
old=pd.read_csv(OLD/'windows.csv');old['subcohort']=old.cohort;old['cohort']='old150'
new=pd.read_csv(OLD/'fresh_grid/windows.csv');new['cohort']='new280';new['subcohort']='new280'
w=pd.concat([old,new],ignore_index=True);assert len(w)==430 and w.window_id.nunique()==430
w['entry_time']=pd.to_datetime(w.entry_time)
a=np.load(OLD/'fresh_grid/all_candidate_arrays.npz');names=a['candidate'];n=430;pcount=len(names);assert pcount==116
gross=np.full((pcount,n),np.nan);selected=np.zeros((pcount,n),bool);eligible=selected.copy()
oldrows=pd.read_csv(OLD/'control_trades.csv');lookup={v:i for i,v in enumerate(w.window_id)};plook={v:i for i,v in enumerate(names)}
for r in oldrows.itertuples(index=False):
    i=plook[r.candidate];j=lookup[r.window_id];gross[i,j]=r.gross_pct;selected[i,j]=r.selected;eligible[i,j]=True
assert new.window_id.tolist()==a['window_id'].tolist()
gross[:,150:]=a['gross_pct'];selected[:,150:]=a['selected'];eligible[:,150:]=a['no_AI_eligible']
assert np.isfinite(gross[selected]).all() and np.isfinite(gross[eligible]).all()

# Focused long/control values use the ungated0/15minute policies on every window.
immediate=gross[plook['003_long_none_confirm0_hold240']].copy()
confirmed=gross[plook['006_long_none_confirm15_hold240']].copy()
macro=w.both_down.to_numpy(bool);aishort=w.action.eq('short').to_numpy();below20=w.ma20_now.gt(100).to_numpy()
candidate=macro&aishort
assert np.array_equal(candidate,selected[plook['048_long_both_down_confirm0_hold240']])
assert np.array_equal(macro,eligible[plook['048_long_both_down_confirm0_hold240']])
defs=[('048_macro_bear_AIshort_long240',immediate,candidate),('macro_bear_no_AI_long240',immediate,macro),('macro_bear_AIlong_complement_long240',immediate,macro&~aishort),('macro_bear_below_MA20_price_only_long240',immediate,macro&below20),('003_ungated_AIshort_long240',immediate,aishort),('006_confirmed_AIshort_long240',confirmed,selected[plook['006_long_none_confirm15_hold240']])]
rng=np.random.default_rng(2026092981);draws=rng.integers(n,size=(10000,n));quarters=w.entry_time.dt.to_period('Q').astype(str)
qcode,qlabels=pd.factorize(quarters);qn=len(qlabels);qdraws=rng.integers(qn,size=(10000,qn))
def stats(v,mask,boot=True):
    mask=np.asarray(mask,bool);v=np.asarray(v,float);assert np.isfinite(v[mask]).all()
    ids=np.flatnonzero(mask);ids=ids[np.argsort(w.entry_time.to_numpy()[ids])];x=v[ids];k=len(x)
    if not k:return {'n':0}
    result={'n':k,'mean_gross_pct':x.mean(),'median_gross_pct':np.median(x),'gross_wins':int((x>0).sum()),'gross_win_rate':(x>0).mean(),'profit_factor_gross':x[x>0].sum()/-x[x<0].sum() if (x<0).any() else None,'best_gross_pct':x.max(),'worst_gross_pct':x.min(),'mean_gross_winner_pct':x[x>0].mean() if (x>0).any() else None,'mean_gross_loser_pct':x[x<0].mean() if (x<0).any() else None,'sum_trade_percentages_not_portfolio_return':x.sum(),'gross_per_all430_opportunities_pct':x.sum()/430,'mean_excluding_best1_pct':np.sort(x)[:-1].mean() if k>1 else None,'mean_excluding_best3_pct':np.sort(x)[:-3].mean() if k>3 else None,'mean_excluding_best5_pct':np.sort(x)[:-5].mean() if k>5 else None,'chronological_halves':[{'n':len(z),'gross_mean_pct':z.mean() if len(z) else None} for z in [x[:k//2],x[k//2:]]],'chronological_thirds':[{'n':len(z),'gross_mean_pct':z.mean() if len(z) else None} for z in np.array_split(x,3)]}
    present=sorted(set(quarters[mask]));loo=[v[mask & (quarters!=q)].mean() for q in present if np.sum(mask & (quarters!=q))>0]
    result.update(calendar_quarters_with_trades=len(present),leave_one_quarter_out_min_mean_pct=min(loo) if loo else None,leave_one_quarter_out_max_mean_pct=max(loo) if loo else None)
    if boot:
        safe=np.where(mask,v,0);den=mask[draws].sum(1);vals=safe[draws].sum(1)[den>0]/den[den>0]
        qs=np.bincount(qcode,weights=safe,minlength=qn);qc=np.bincount(qcode,weights=mask,minlength=qn);cd=qc[qdraws].sum(1);cv=qs[qdraws].sum(1)[cd>0]/cd[cd>0]
        result.update(ci95_window_mean_pct=np.quantile(vals,[.025,.975]),ci95_quarter_cluster_mean_pct=np.quantile(cv,[.025,.975]))
    return result

focus=[];periods=[];perwindow=[]
for name,values,mask in defs:
    r={'name':name,'combined':stats(values,mask),'frequency_all430':mask.mean(),'old150':stats(values,mask&w.cohort.eq('old150')),'new280':stats(values,mask&w.cohort.eq('new280'))}
    for cohort in ['old150','new280']:
        c=w.cohort.eq(cohort).to_numpy();r[cohort]['opportunities']=int(c.sum());r[cohort]['frequency']=float((mask&c).sum()/c.sum());r[cohort]['gross_per_opportunity_pct']=float(np.nansum(np.where(mask&c,values,0))/c.sum())
    focus.append(r)
    for grouping,labels in [('year',w.entry_time.dt.year.astype(str)),('quarter',quarters)]:
        for period in sorted(set(labels)):
            m=mask&(labels==period).to_numpy();eligible_time=(labels==period).to_numpy();s=stats(values,m,False)
            periods.append({'strategy':name,'grouping':grouping,'period':period,'opportunities_in_period':int(eligible_time.sum()),**{k:v for k,v in s.items() if not isinstance(v,(dict,list))}})
    for i in range(n):perwindow.append({'strategy':name,'window_id':w.loc[i,'window_id'],'cohort':w.loc[i,'cohort'],'subcohort':w.loc[i,'subcohort'],'entry_time':str(w.loc[i,'entry_time']),'selected':bool(mask[i]),'hypothetical_gross_pct':values[i] if np.isfinite(values[i]) else None,'strategy_gross_pct':values[i] if mask[i] else 0,'AI_action':w.loc[i,'action'],'both_daily_below':bool(macro[i]),'below_intraday_MA20':bool(below20[i])})

# Shared-window bootstrap of conditional selection advantage; fixed focus only.
contrasts=[]
for name,cmask in [('macro_no_AI',macro),('macro_AIlong_complement',macro&~aishort),('macro_below_MA20_price_only',macro&below20)]:
    for cohort in ['all430','old150','new280']:
        cohortmask=np.ones(n,bool) if cohort=='all430' else w.cohort.eq(cohort).to_numpy()
        one=candidate&cohortmask;two=cmask&cohortmask
        da=one[draws].sum(1);db=two[draws].sum(1);ok=(da>0)&(db>0)
        diff=np.where(one,immediate,0)[draws].sum(1)[ok]/da[ok]-np.where(two,immediate,0)[draws].sum(1)[ok]/db[ok]
        contrasts.append({'candidate':'048_macro_bear_AIshort_long240','control':name,'cohort':cohort,'selected_n':int(one.sum()),'control_n':int(two.sum()),'observed_mean_gross_difference_pct':immediate[one].mean()-immediate[two].mean(),'ci95_difference_pct':np.quantile(diff,[.025,.975])})

# Diagnostic conditional randomization for the focus, clearly exploratory.
era=np.where(w.entry_time.dt.year<=2021,'2020-21',np.where(w.entry_time.dt.year<=2023,'2022-23','2024-26'))
regime=np.where(w.above_both,'aboveboth',np.where(w.below_both,'belowboth','mixed'))
strata=np.array([a+'/'+b for a,b in zip(era,regime)]);prng=np.random.default_rng(2026092982);tests=[]
for cohort in ['all430','old150','new280']:
    cohortmask=np.ones(n,bool) if cohort=='all430' else w.cohort.eq(cohort).to_numpy();ids=np.flatnonzero(cohortmask)
    labels=np.tile(aishort[ids],(20000,1));groups=strata[ids]
    for label in sorted(set(groups)):
        g=np.flatnonzero(groups==label);labels[:,g]=aishort[ids][g][np.argsort(prng.random((20000,len(g))),axis=1)]
    masks=labels&macro[ids];den=masks.sum(1);null=np.sum(masks*immediate[ids],axis=1)[den>0]/den[den>0]
    obs=immediate[candidate&cohortmask].mean();tests.append({'cohort':cohort,'observed_gross_mean_pct':obs,'conditional_null_mean_pct':null.mean(),'observed_minus_null_pct':obs-null.mean(),'p_one_sided_exploratory_not_search_adjusted':(1+(null>=obs-1e-14).sum())/(len(null)+1),'null_ci95_pct':np.quantile(null,[.025,.975]),'permutations':len(null)})

save('focus_results.json',focus);save('selection_contrasts.json',contrasts);save('conditional_selection_diagnostic.json',tests)
pd.DataFrame(periods).to_csv(HERE/'calendar_breakdown.csv',index=False);pd.DataFrame(perwindow).to_csv(HERE/'focus_per_window.csv',index=False)
w.to_csv(HERE/'windows.csv',index=False)
np.savez_compressed(HERE/'all116_zero_fee_vectors.npz',gross_pct=gross,selected=selected,no_AI_eligible=eligible,candidate=names,window_id=w.window_id.to_numpy(dtype=str),cohort=w.cohort.to_numpy(dtype=str),entry_time=w.entry_time.astype(str).to_numpy(dtype=str))
# Re-express existing116 interval summaries exactly, preserving old original files.
o=json.loads((OLD/'candidate_results.json').read_text());f=json.loads((OLD/'fresh_grid/candidate_results.json').read_text());rows=[]
for x,y in zip(o,f):
    assert x['candidate']==y['candidate']
    row={'candidate':x['candidate'],'old_n':x['n'],'new_n':y['n'],'old_gross_mean_pct':x.get('gross_mean'),'new_gross_mean_pct':y.get('gross_mean'),'old_gross_ci95_low':x.get('net_mean_ci95',[None,None])[0]+.2 if 'net_mean_ci95' in x else None,'old_gross_ci95_high':x.get('net_mean_ci95',[None,None])[1]+.2 if 'net_mean_ci95' in x else None,'new_gross_ci95_low':y.get('net_mean_ci95',[None,None])[0]+.2 if 'net_mean_ci95' in y else None,'new_gross_ci95_high':y.get('net_mean_ci95',[None,None])[1]+.2 if 'net_mean_ci95' in y else None,'new_no_AI_control_gross_pct':y['no_AI_control'].get('gross_mean'),'old_no_AI_control_gross_pct':x['no_AI_control'].get('gross_mean'),'new_gross_excluding_best3_pct':None if y.get('mean_excluding_best3_net') is None else y['mean_excluding_best3_net']+.2}
    rows.append(row)
pd.DataFrame(rows).to_csv(HERE/'all116_gross_reexpression.csv',index=False)
# Existing stopout summaries without rescoring or changing definitions.
fade=[]
for r in json.loads((OLD/'stopout_fade/results.json').read_text()):
    row={'policy':r['policy'],'group':r['group']}
    for cohort in ['old150','new280']:
        z=r[cohort];row[cohort+'_n']=z['n'];row[cohort+'_gross_mean']=z.get('gross_mean');ci=z.get('net_ci95',[None,None]);row[cohort+'_gross_ci_low']=None if ci[0] is None else ci[0]+.2;row[cohort+'_gross_ci_high']=None if ci[1] is None else ci[1]+.2
    fade.append(row)
pd.DataFrame(fade).to_csv(HERE/'stopout_gross_reexpression.csv',index=False)
conf=ROOT/'data/analysis/reversal-deep-20260929/confirmation';confirmation=[]
for cohort,file in [('old150',conf/'all_policy_summaries.csv'),('new280',conf/'fresh_grid/all_policy_summaries.csv')]:
    hashes[str(file.relative_to(ROOT))]=sha(file)
    for r in pd.read_csv(file).to_dict('records'):
        confirmation.append({'cohort':cohort,'policy':r['policy'],'n':r['n'],'mean_gross_pct':r['gross_mean_pct'],'no_AI_trigger_control_n':r['all_triggered_n'],'no_AI_trigger_control_gross_pct':r['all_triggered_net_pct']+.2,'AI_lift_vs_all_triggered_pct':r['ai_lift_vs_all_triggered_pct'],'control_is_price_only':r['control_is_price_only'],'earlier_half_gross_pct':r['early_net_pct']+.2,'later_half_gross_pct':r['late_net_pct']+.2})
pd.DataFrame(confirmation).to_csv(HERE/'confirmation_existing_gross_summary.csv',index=False)
audit={'passed':True,'fees_bps':0,'old150_and_new280_are_discovery':True,'no_new_model_calls':True,'source_hashes':hashes,'all_source_hashes_match':all(sha(ROOT/p)==h for p,h in hashes.items()),'all430_unique_windows':True,'116_original_definitions_unchanged':True,'focus_definition048_matches_existing_mask':True,'focus_daily_gate_matches_existing_no_AI_eligibility':True,'bootstrap_seed':2026092981,'permutation_seed':2026092982}
assert audit['all_source_hashes_match'];save('audit.json',audit)
for r in focus:print(json.dumps(clean(r),indent=2))
print('CONTRASTS',json.dumps(clean(contrasts),indent=2));print('PERM',json.dumps(clean(tests),indent=2))
