"""Fixed forward-calendar information study; existing decisions only, no model calls."""
from pathlib import Path
import hashlib,json,re
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
GROSS=ROOT/'data/analysis/gross-edge-20260929/signals'
B=20_000;SEED=2026093007;L2=10.
SOURCES={}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source(p):
    p=Path(p);SOURCES[str(p.relative_to(ROOT))]=sha(p);return p
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.bool_,)):return bool(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x
def save(name,x):(HERE/name).write_text(json.dumps(clean(x),indent=2,allow_nan=False)+'\n')
def records(p):return [json.loads(s) for s in source(p).read_text().splitlines() if s.strip()]

source(HERE/'PLAN.md')
old=pd.read_csv(source(GROSS/'windows.csv'))
arrays=np.load(source(GROSS/'all116_zero_fee_vectors.npz'))
assert list(arrays['window_id'])==old.window_id.tolist()
k=list(arrays['candidate']).index('003_long_none_confirm0_hold240')
old['gross_240_pct']=arrays['gross_pct'][k]
old['asset']=old.asset.fillna('SOL-USD');old['primary_action']=old.action
keep=['cohort','window_id','asset','entry_time','primary_action','confidence','reason','atr14_pct','ma20_now','ma50_now','vol24_ratio','ret_vis_pct','gross_240_pct']
frames=[old[keep].copy()]

for folder,cohort in [('gross-edge-500-20260929T204545Z','fourasset500'),('ma-ablation-sol90-20260929T210853Z','paired90')]:
    run=ROOT/'data/sim'/folder
    assert (run/'ALLOW_EVALUATION').is_file()
    manifest=json.loads(source(run/'manifest.json').read_text())
    cases=pd.DataFrame(manifest['cases'])
    dec=records(run/'accepted_decisions.jsonl')
    decisions=pd.DataFrame([{'case':r['case'],**r['decision']} for r in dec])
    joined=cases.merge(decisions,on='case',validate='one_to_one')
    joined['cohort']=cohort;joined['primary_action']=joined.action
    if cohort=='fourasset500':
        ret=pd.read_csv(source(GROSS/'fresh_L048_independent_rows.csv'))[['window_id','gross_pct']]
        joined=joined.merge(ret,on='window_id',validate='one_to_one').rename(columns={'gross_pct':'gross_240_pct'})
    else:
        paired=joined.copy()
        ret=pd.read_csv(source(GROSS/'paired90_independent_windows.csv'))[['window_id','gross_pct']]
        joined=joined[joined.arm=='MA_A'].merge(ret,on='window_id',validate='one_to_one').rename(columns={'gross_pct':'gross_240_pct'})
    frames.append(joined[keep].copy())

w=pd.concat(frames,ignore_index=True)
w['entry_time']=pd.to_datetime(w.entry_time)
w=w.sort_values(['entry_time','asset','cohort','window_id']).reset_index(drop=True)
assert len(w)==1020 and w.window_id.nunique()==1020
assert w.primary_action.isin(['short','long']).all()
assert np.isfinite(w[['atr14_pct','ma20_now','ma50_now','vol24_ratio','ret_vis_pct','gross_240_pct','confidence']].to_numpy()).all()
assert w.atr14_pct.gt(0).all() and w.vol24_ratio.gt(0).all() and w.confidence.between(0,1).all()
w['year']=w.entry_time.dt.year
w['quarter']=w.entry_time.dt.to_period('Q').astype(str)
w['era']=np.where(w.year<=2021,'2020-21',np.where(w.year<=2023,'2022-23','2024-26'))
w['ma_regime']=np.where((w.ma20_now<=100)&(w.ma50_now<=100),'above_both',np.where((w.ma20_now>=100)&(w.ma50_now>=100),'below_both','mixed'))
w['AI_short']=w.primary_action.eq('short')
w['AI_sign']=np.where(w.AI_short,-1,1)
for arm in ['MA_A','MA_B','NO_MA']:
    byid=paired[paired.arm==arm].set_index('window_id')
    w['action_'+arm]=w.window_id.map(byid.action)
    w['confidence_'+arm]=w.window_id.map(byid.confidence)

TAGS={
 'exhaustion':r'exhaust|overbought|oversold|over[- ]?extend|mean[- ]reversion|stretched',
 'break':r'breakout|breakdown|break out|break down|broke above|broke below',
 'rejection':r'reject|failed|failure|stalled|stalling',
 'continuation':r'continu|persist|momentum|trend|higher lows|lower highs',
 'counterevidence':r'\b(?:despite|although|however|but|yet)\b',
}
for name,pattern in TAGS.items():w['tag_'+name]=w.reason.str.contains(pattern,case=False,regex=True)
numeric=np.column_stack([(100-w.ma20_now)/w.atr14_pct,(100-w.ma50_now)/w.atr14_pct,w.ret_vis_pct/w.atr14_pct,np.log(w.vol24_ratio),np.log(w.atr14_pct)])
feature_names=['ma20_distance_atr','ma50_distance_atr','visible_move_atr','log_vol24_ratio','log_atr14_pct','BTC','ETH','DOGE']
dummy=np.column_stack([w.asset.eq(s).to_numpy(float) for s in ['BTC-USD','ETH-USD','DOGE-USD']])
assert np.isfinite(numeric).all()

def logistic(X,y,T):
    """Newton method for sum logistic loss + L2/2 penalty; intercept unpenalized."""
    y=np.asarray(y,float);A=np.column_stack([np.ones(len(X)),X]);At=np.column_stack([np.ones(len(T)),T])
    if len(np.unique(y))==1:
        p=(y.sum()+1)/(len(y)+2)
        return np.full(len(T),p),{'constant_laplace':p,'n':len(y)}
    penalty=np.eye(A.shape[1])*L2;penalty[0,0]=0
    beta=np.zeros(A.shape[1]);beta[0]=np.log((y.sum()+.5)/(len(y)-y.sum()+.5))
    def loss(b):return (np.logaddexp(0,A@b)-y*(A@b)).sum()+.5*b@penalty@b
    converged=False
    for iteration in range(100):
        z=A@beta;p=1/(1+np.exp(-np.clip(z,-700,700)))
        grad=A.T@(p-y)+penalty@beta
        hess=A.T@((p*(1-p))[:,None]*A)+penalty
        step=np.linalg.solve(hess,grad)
        fraction=1.;before=loss(beta)
        while loss(beta-fraction*step)>before+1e-12:
            fraction*=.5
            assert fraction>1e-12
        beta-=fraction*step
        if np.max(np.abs(fraction*step))<1e-9:
            converged=True;break
    assert converged, 'The fixed logistic objective did not converge.'
    pred=1/(1+np.exp(-np.clip(At@beta,-700,700)))
    return pred,{'coefficients':beta.tolist(),'iterations':iteration+1,'max_abs_gradient':float(np.abs(grad).max()),'objective':float(loss(beta))}

def ridge(X,y,T):
    A=np.column_stack([np.ones(len(X)),X]);At=np.column_stack([np.ones(len(T)),T])
    penalty=np.eye(A.shape[1])*L2;penalty[0,0]=0
    beta=np.linalg.solve(A.T@A+penalty,A.T@y)
    return np.clip(At@beta,0,1),{'coefficients':beta.tolist()}

prediction_names=['pred_short','pred_confidence',*['pred_tag_'+x for x in TAGS]]
for col in prediction_names:w[col]=np.nan
w['training_n']=0;w['training_max_time']='';w['scored_forward_fold']=False
fits=[];calibration=[]
for year in [2022,2023,2024,2025,2026]:
    boundary=pd.Timestamp(f'{year}-01-01')
    tr=(w.entry_time<boundary-pd.Timedelta(days=7)).to_numpy();te=w.year.eq(year).to_numpy()
    if tr.sum()<50:fits.append({'test_year':year,'unavailable_training_n':int(tr.sum())});continue
    assert (w.entry_time[tr]+pd.Timedelta(days=7)<boundary).all()
    mu=numeric[tr].mean(0);sd=numeric[tr].std(0);sd[sd<1e-12]=1
    X=np.column_stack([(numeric-mu)/sd,dummy]);Xa=np.column_stack([X,w.AI_short.to_numpy(float)])
    p,fit_action=logistic(X[tr],w.AI_short.to_numpy(float)[tr],X[te])
    c,fit_conf=ridge(Xa[tr],w.confidence.to_numpy()[tr],Xa[te])
    w.loc[te,'pred_short']=p;w.loc[te,'pred_confidence']=c
    tagfits={}
    for tag in TAGS:
        q,info=logistic(Xa[tr],w['tag_'+tag].to_numpy(float)[tr],Xa[te])
        w.loc[te,'pred_tag_'+tag]=q;tagfits[tag]=info
    w.loc[te,'training_n']=int(tr.sum());w.loc[te,'training_max_time']=str(w.entry_time[tr].max());w.loc[te,'scored_forward_fold']=True
    fits.append({'test_year':year,'training_n':int(tr.sum()),'test_n':int(te.sum()),'training_end':str(w.entry_time[tr].max()),'test_start':str(w.entry_time[te].min()),'mu':mu.tolist(),'sd':sd.tolist(),'action':fit_action,'confidence':fit_conf,'reasons':tagfits})
    true=w.AI_short.to_numpy(float)[te];actual=w.confidence.to_numpy()[te]
    calibration.append({'test_year':year,'n':int(te.sum()),'actual_short_rate':true.mean(),'short_accuracy':np.mean((p>=.5)==true),'short_Brier':np.mean((p-true)**2),'training_majority_accuracy':np.mean((w.AI_short[tr].mean()>=.5)==true),'training_prevalence_Brier':np.mean((w.AI_short[tr].mean()-true)**2),'confidence_MAE':np.abs(actual-c).mean(),'confidence_training_mean_MAE':np.abs(actual-w.confidence[tr].mean()).mean()})

w['confidence_residual']=w.confidence-w.pred_confidence
eligible=w.scored_forward_fold.to_numpy(bool);pairedmask=w.cohort.eq('paired90').to_numpy()
short=w.AI_short.to_numpy(bool);unexpected_short=short&w.pred_short.lt(.5).to_numpy()&eligible
unexpected_long=~short&w.pred_short.gt(.5).to_numpy()&eligible
fade=-w.AI_sign.to_numpy();one=np.ones(len(w),int)
definitions=[
 ('01_unexpected_SHORT_buy',unexpected_short,one,eligible,'primary_action'),
 ('02_unexpected_LONG_sell',unexpected_long,-one,eligible,'primary_action'),
 ('03_confident_unexpected_SHORT_buy',unexpected_short&w.confidence_residual.gt(0).to_numpy(),one,eligible,'primary_action'),
 ('04_confident_unexpected_LONG_sell',unexpected_long&w.confidence_residual.gt(0).to_numpy(),-one,eligible,'primary_action'),
]
for i,tag in enumerate(TAGS,5):
    mask=eligible&w['tag_'+tag].to_numpy(bool)&w['pred_tag_'+tag].lt(.5).to_numpy()
    definitions.append((f'{i:02d}_unexpected_{tag}_fade',mask,fade,eligible,'primary_action'))
nomadir=np.where(w.action_NO_MA.eq('long'),1,-1)
repeat_disagree=pairedmask&w.action_MA_A.ne(w.action_MA_B).to_numpy()
ma_flip=pairedmask&w.action_MA_A.eq(w.action_MA_B).to_numpy()&w.action_NO_MA.ne(w.action_MA_A).to_numpy()
definitions.extend([('10_repeat_disagree_follow_NO_MA',repeat_disagree,nomadir,pairedmask,'action_NO_MA'),('11_stable_MA_call_flip_follow_NO_MA',ma_flip,nomadir,pairedmask,'action_NO_MA')])
assert len(definitions)==11

quarters=sorted(w.quarter.unique());qcodes=pd.Categorical(w.quarter,categories=quarters).codes.astype(np.int64);qn=len(quarters)
rng=np.random.default_rng(SEED)
draws=rng.multinomial(qn,np.full(qn,1/qn),size=B).astype(np.int16)
r=w.gross_240_pct.to_numpy()

def control(allowed,reference):
    keys=['cohort','asset','era','ma_regime'];data=w.loc[allowed].copy()
    means=data.groupby(keys).gross_240_pct.transform('mean')
    with_ai=data.groupby(keys+[reference]).gross_240_pct.transform('mean')
    out=np.full(len(w),np.nan);aiout=out.copy()
    out[data.index]=means;aiout[data.index]=with_ai
    return out,aiout

def interval(values,mask):
    sums=np.bincount(qcodes,weights=np.where(mask,values,0),minlength=qn)
    counts=np.bincount(qcodes,weights=mask,minlength=qn)
    denom=draws@counts;valid=denom>0
    result=(draws@sums)[valid]/denom[valid]
    return {'ci95_quarter':np.quantile(result,[.025,.975]),'ci95_family11_bonferroni_quarter':np.quantile(result,[.025/11,1-.025/11])} if len(result) else {}

def resampled_increment(mask,side,allowed,reference=None):
    """Reestimate matched means and selected-side weights in every quarter draw."""
    keys=['cohort','asset','era','ma_regime']+([reference] if reference else [])
    ids=np.flatnonzero(allowed)
    labels=w.loc[allowed,keys].astype(str).agg('|'.join,axis=1)
    gcodes,glabels=pd.factorize(labels);gn=len(glabels)
    flat=qcodes[ids]*gn+gcodes
    totals=np.bincount(flat,weights=r[ids],minlength=qn*gn).reshape(qn,gn)
    counts=np.bincount(flat,minlength=qn*gn).reshape(qn,gn)
    selected_side=np.bincount(flat,weights=mask[ids]*side[ids],minlength=qn*gn).reshape(qn,gn)
    group_count=draws@counts
    mean=np.divide(draws@totals,group_count,out=np.zeros((B,gn)),where=group_count>0)
    control_total=np.sum((draws@selected_side)*mean,axis=1)
    own_total=draws@np.bincount(qcodes,weights=np.where(mask,side*r,0),minlength=qn)
    denominator=draws@np.bincount(qcodes,weights=mask,minlength=qn)
    valid=denominator>0;v=(own_total-control_total)[valid]/denominator[valid]
    return {'ci95_quarter':np.quantile(v,[.025,.975]),'ci95_family11_bonferroni_quarter':np.quantile(v,[.025/11,1-.025/11]),'matched_baselines_reestimated_each_draw':True} if len(v) else {}

def summary(values,mask,with_ci=False):
    ids=np.flatnonzero(mask);x=values[mask];n=len(x)
    if not n:return {'n':0}
    quarters_here=sorted(w.quarter[mask].unique());years_here=sorted(w.year[mask].unique())
    times=sorted(w.entry_time[mask].unique());mid=len(times)//2
    half_masks=[mask&w.entry_time.isin(t).to_numpy() for t in [times[:mid],times[mid:]]]
    z={'n':n,'unique_entry_time_blocks':len(times),'active_UTC_weeks':int(w.entry_time[mask].dt.to_period('W').nunique()),'quarters':len(quarters_here),'mean_pct':x.mean(),'median_pct':np.median(x),'sum_trade_pct_not_portfolio':x.sum(),'wins':int((x>0).sum()),'win_rate':(x>0).mean(),'best_pct':x.max(),'worst_pct':x.min(),'exclude_best1_mean_pct':np.sort(x)[:-1].mean() if n>1 else None,'exclude_best3_mean_pct':np.sort(x)[:-3].mean() if n>3 else None,'halves':[{'n':int(m.sum()),'unique_entry_time_blocks':int(w.entry_time[m].nunique()),'mean_pct':values[m].mean() if m.any() else None} for m in half_masks],'leave_year_out':[{'omitted':int(y),'remaining_n':int(np.sum(mask&w.year.ne(y).to_numpy())),'mean_pct':values[mask&w.year.ne(y).to_numpy()].mean() if np.any(mask&w.year.ne(y).to_numpy()) else None} for y in years_here]}
    if with_ci:z.update(interval(values,mask))
    return z

def contrast_coverage(selected,allowed,reference):
    data=w.loc[allowed].copy();data['selected']=selected[allowed]
    table=data.groupby(['cohort','asset','era','ma_regime',reference]).selected.agg(['sum','count'])
    table['mixed']=(table['sum']>0)&(table['sum']<table['count'])
    return {'selected_in_mixed_strata':int(table.loc[table.mixed,'sum'].sum()),'selected_in_all_selected_strata':int(table.loc[(table['sum']>0)&~table.mixed,'sum'].sum()),'mixed_strata':int(table.mixed.sum()),'selected_strata':int((table['sum']>0).sum()),'table':table.reset_index().to_dict('records')}

results=[];ledger=[];quick=[];pnl_matrix=[];mask_matrix=[];direction_matrix=[];price_matrix=[];rawdir_matrix=[]
for name,mask,side,allowed,reference in definitions:
    assert np.all(mask<=allowed)
    cp,ca=control(allowed,reference)
    pnl=side*r;price=side*cp;rawdir=side*ca
    price_increment=pnl-price;direction_increment=pnl-rawdir
    assert np.isfinite(pnl[mask]).all() and np.isfinite(price_increment[mask]).all() and np.isfinite(direction_increment[mask]).all()
    result={'candidate':name,'reference_action':reference,'available_windows':int(allowed.sum()),'eligible_cohorts':sorted(w.cohort[allowed].unique()),'all':summary(pnl,mask,True),'price_matched_increment':summary(price_increment,mask),'direction_matched_increment':summary(direction_increment,mask),'price_matched_control_mean_pct':price[mask].mean() if mask.any() else None,'direction_matched_control_mean_pct':rawdir[mask].mean() if mask.any() else None,'contrast_coverage':contrast_coverage(mask,allowed,reference),'cohorts':{},'years':{},'assets':{},'legs':{},'quarters':{}}
    result['price_matched_increment'].update(resampled_increment(mask,side,allowed))
    result['direction_matched_increment'].update(resampled_increment(mask,side,allowed,reference))
    for grouping,col in [('cohorts','cohort'),('years','year'),('assets','asset'),('quarters','quarter')]:
        for label in sorted(w[col][allowed].unique()):
            m=mask&w[col].eq(label).to_numpy()
            result[grouping][str(label)]={'return':summary(pnl,m),'price_matched_increment':summary(price_increment,m),'direction_matched_increment':summary(direction_increment,m)}
    for leg,s in [('long',1),('short',-1)]:
        m=mask&(side==s);result['legs'][leg]={'return':summary(pnl,m),'price_matched_increment':summary(price_increment,m),'direction_matched_increment':summary(direction_increment,m),'descriptive_not_new_finalist':True}
    coherent_cohorts=[k for k,v in result['cohorts'].items() if v['return']['n']>=10 and v['return']['mean_pct']>0 and v['direction_matched_increment']['mean_pct']>0]
    coherent_years=[k for k,v in result['years'].items() if v['return']['n']>=10 and v['return']['mean_pct']>0]
    criteria={'at_least40':int(mask.sum())>=40,'three_positive_cohorts_n10_with_increment':len(coherent_cohorts)>=3,'three_positive_years_n10':len(coherent_years)>=3,'exclude_best3_positive':result['all'].get('exclude_best3_mean_pct',-999) is not None and result['all'].get('exclude_best3_mean_pct',-999)>0,'positive_direction_increment':result['direction_matched_increment'].get('mean_pct',-999)>0}
    result['recommendation_screen']=criteria;result['passes_recommendation_screen']=all(criteria.values());result['positive_cohorts_n10']=coherent_cohorts;result['positive_years_n10']=coherent_years
    results.append(result)
    quick.append({'candidate':name,'n':int(mask.sum()),'gross_mean_pct':result['all'].get('mean_pct'),'price_increment_pct':result['price_matched_increment'].get('mean_pct'),'direction_increment_pct':result['direction_matched_increment'].get('mean_pct'),'gross_ci95_low':result['all'].get('ci95_quarter',[None,None])[0],'gross_ci95_high':result['all'].get('ci95_quarter',[None,None])[1],'direction_increment_ci95_low':result['direction_matched_increment'].get('ci95_quarter',[None,None])[0],'direction_increment_ci95_high':result['direction_matched_increment'].get('ci95_quarter',[None,None])[1],'mixed_contrast_n':result['contrast_coverage']['selected_in_mixed_strata'],'passes_screen':result['passes_recommendation_screen']})
    for i in np.flatnonzero(allowed):
        ledger.append({'candidate':name,'window_id':w.window_id[i],'cohort':w.cohort[i],'asset':w.asset[i],'entry_time':str(w.entry_time[i]),'year':int(w.year[i]),'quarter':w.quarter[i],'selected':bool(mask[i]),'direction':int(side[i]),'gross_pct':pnl[i],'price_matched_pct':price[i],'direction_matched_pct':rawdir[i],'price_increment_pct':price_increment[i],'direction_increment_pct':direction_increment[i],'reference_action':w[reference][i]})
    pnl_matrix.append(pnl);mask_matrix.append(mask);direction_matrix.append(side);price_matrix.append(price_increment);rawdir_matrix.append(direction_increment)

comparators=[]
for name,side in [('always_long',one),('always_short',-one),('raw_AI_fade',fade)]:
    value=side*r
    comparators.append({'name':name,'all_forward_folds':summary(value,eligible,True),'cohorts':{c:summary(value,eligible&w.cohort.eq(c).to_numpy()) for c in sorted(w.cohort.unique())},'years':{str(y):summary(value,eligible&w.year.eq(y).to_numpy()) for y in sorted(w.year[eligible].unique())}})

np.savez_compressed(HERE/'all_information_vectors.npz',gross_pct=np.array(pnl_matrix),selected=np.array(mask_matrix),direction=np.array(direction_matrix),price_increment_pct=np.array(price_matrix),direction_increment_pct=np.array(rawdir_matrix),candidate=np.array([x[0] for x in definitions]),window_id=w.window_id.to_numpy(str),cohort=w.cohort.to_numpy(str),asset=w.asset.to_numpy(str),entry_time=w.entry_time.astype(str).to_numpy(str),quarter=w.quarter.to_numpy(str))
np.savez_compressed(HERE/'quarter_bootstrap_draws.npz',weights=draws,quarter=np.array(quarters))
w.to_csv(HERE/'forward_predictions.csv',index=False)
pd.DataFrame(ledger).to_csv(HERE/'all_candidate_windows.csv.gz',index=False,compression='gzip')
pd.DataFrame(quick).to_csv(HERE/'candidate_summary.csv',index=False)
save('results.json',results);save('model_fits.json',{'numeric_and_asset_feature_names':feature_names,'action_added_to_confidence_and_reason':True,'L2':L2,'folds':fits});save('model_calibration.json',calibration);save('comparators.json',comparators)
audit={'passed':True,'no_model_calls':True,'fees_bps':0,'unique_asset_windows':len(w),'unique_entry_time_blocks':int(w.entry_time.nunique()),'paired_extra_decisions_not_counted_as_events':180,'source_sha256':SOURCES,'source_hashes_unchanged':all(sha(ROOT/p)==h for p,h in SOURCES.items()),'forward_calendar_test_years':[2022,2023,2024,2025,2026],'embargo_days':7,'scored_auxiliary_windows':int(eligible.sum()),'warmup_windows':int((~eligible).sum()),'fixed_candidates':len(definitions),'new_thresholds_after_scoring':False,'bootstrap_draws':B,'bootstrap_seed':SEED,'matched_control_means_reestimated_each_draw':True,'chronological_halves_keep_simultaneous_assets_together':True,'all_outcomes_previously_inspected':True,'independent_validation':False,'price_controls_coarse_matching_not_causal_identification':True}
assert audit['source_hashes_unchanged'];save('audit.json',audit)
print(pd.DataFrame(quick).to_string(index=False));print('CALIBRATION',json.dumps(clean(calibration)));print('AUDIT',json.dumps(clean(audit)))
