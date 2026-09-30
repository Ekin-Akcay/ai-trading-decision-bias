"""Two previously exposed action partitions only; no new policy or model call."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OLD=ROOT/'data/analysis/same-moment-patterns-20260930/volume_reaction'
w=pd.read_csv(OLD/'features.csv');w.entry_time=pd.to_datetime(w.entry_time)
v=np.load(OLD/'vectors.npz');d=np.load(OLD/'diagnostics_vectors.npz')
names=list(v['policies']);dn=list(d['policies']);weights=v['quarter_weights']
q,labels=pd.factorize(w.quarter,sort=True);q=q.astype(np.int64)
coverage=v['coverage'];assert coverage.sum()==1019
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,np.integer):return int(x)
    if isinstance(x,np.bool_):return bool(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x
def bs(y,m):
    a=np.bincount(q,weights=y,minlength=len(labels));b=np.bincount(q,weights=m,minlength=len(labels));den=weights@b
    return np.divide(weights@a,den,out=np.full(len(weights),np.nan),where=den>0)
def ci(x):return np.nanquantile(x,[.025,.975])
def simple(y,m):
    x=y[m];blocks=pd.DataFrame({'ts':w.entry_time,'y':y,'n':m.astype(int)}).groupby('ts').sum();best=blocks[blocks.n>0].nlargest(3,'y').index
    trimmed=m&~w.entry_time.isin(best).to_numpy()
    return {'trades':int(m.sum()),'blocks':int(w.entry_time[m].nunique()),'mean_pct':x.mean(),'sd_pct':x.std(ddof=1),'win_rate':(x>0).mean(),'ci95_quarter':ci(bs(y,m)),'without_best3_blocks_pct':y[trimmed].mean(),'halves':[{'n':int((m&w.half.eq(h).to_numpy()).sum()),'mean_pct':y[m&w.half.eq(h).to_numpy()].mean()}for h in [1,2]],'cohorts':{str(c):{'n':int((m&w.cohort.eq(c).to_numpy()).sum()),'mean_pct':y[m&w.cohort.eq(c).to_numpy()].mean() if (m&w.cohort.eq(c).to_numpy()).any() else None}for c in w.cohort.unique()},'years':{str(c):{'n':int((m&w.entry_time.dt.year.eq(c).to_numpy()).sum()),'mean_pct':y[m&w.entry_time.dt.year.eq(c).to_numpy()].mean() if (m&w.entry_time.dt.year.eq(c).to_numpy()).any() else None}for c in sorted(w.entry_time.dt.year.unique())}}
out=[]
for ai,base in [('quiet_up_short_AI_SHORT','quiet_up_extension_short__noAI'),('quiet_down_long_AI_LONG','quiet_down_extension_long__noAI')]:
    j=dn.index(ai);k=names.index(base);m=d['selected'][:,j];allmask=v['selected'][:,k];other=allmask&~m
    y=d['returns'][:,j];all_y=v['returns'][:,k];other_y=all_y-y
    assert np.array_equal(m|other,allmask) and not (m&other).any()
    inc=bs(y,m)-bs(all_y,allmask);partition=bs(y,m)-bs(other_y,other)
    opp=bs(y-all_y,allmask)
    # Standardize the complete price-gate outcome to AI-selected cohort/asset/year composition.
    frame=w.copy();frame['year']=frame.entry_time.dt.year
    matched=np.full(len(w),np.nan);boot_expected=np.zeros(len(weights));mixed_count=0
    for key,g in frame[allmask].groupby(['cohort','asset','year']):
        ids=g.index.to_numpy();chosen=ids[m[ids]]
        matched[ids]=all_y[ids].mean()
        cnt=weights@np.bincount(q[ids],minlength=len(labels));total=weights@np.bincount(q[ids],weights=all_y[ids],minlength=len(labels))
        avg=np.divide(total,cnt,out=np.zeros(len(weights)),where=cnt>0)
        boot_expected+=avg*(weights@np.bincount(q[chosen],minlength=len(labels)))
        if len(chosen)<len(ids):mixed_count+=len(chosen)
    ownsum=weights@np.bincount(q,weights=y,minlength=len(labels));den=weights@np.bincount(q,weights=m,minlength=len(labels))
    diff=np.divide(ownsum-boot_expected,den,out=np.full(len(weights),np.nan),where=den>0)
    candidate=simple(y,m);control=simple(all_y,allmask);complement=simple(other_y,other)
    # Normal-approximation planning scale, descriptive; clustering/search increase requirements.
    mu=candidate['mean_pct'];sd=candidate['sd_pct'];rate=m.sum()/allmask.sum()
    n80=((1.96+.8416212336)*sd/mu)**2 if mu>0 else None
    out.append({'AI_policy':ai,'price_only_control':base,'candidate':candidate,'control':control,'opposite_AI_partition_same_trade_direction':complement,'AI_agreement_fraction_on_price_gate':rate,'conditional_increment_vs_price_only_pp':candidate['mean_pct']-control['mean_pct'],'conditional_increment_ci95':ci(inc),'conditional_agree_minus_disagree_pp':candidate['mean_pct']-complement['mean_pct'],'agree_minus_disagree_ci95':ci(partition),'opportunity_increment_per_price_gate_pp':(y-all_y).sum()/allmask.sum(),'opportunity_increment_ci95':ci(opp),'matched_increment_cohort_asset_year_pp':(y[m]-matched[m]).mean(),'matched_increment_ci95':ci(diff),'selected_with_mixed_composition_contrast':int(mixed_count),'approx_selected_n_for80pct_power_at_observed_gross_mean':n80,'approx_price_gated_calls_for80pct_power':n80/rate if n80 else None,'power_calculation_limitations':'normal approximation, independent observations, one observed mean, no shrinkage; not a power guarantee','all_old_outcomes_already_seen':True})
artifact={'new_calls':0,'new_outcomes':0,'two_existing_partitions_only':True,'source_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [OLD/'features.csv',OLD/'vectors.npz',OLD/'diagnostics_vectors.npz']},'results':out}
(HERE/'old_signal_statistics.json').write_text(json.dumps(clean(artifact),indent=2,allow_nan=False)+'\n')
for x in out:print(json.dumps(clean(x),indent=2))
