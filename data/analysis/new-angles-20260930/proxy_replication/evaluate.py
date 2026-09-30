"""Score one frozen behavior-proxy policy and three fixed controls; no fitting."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import numpy as np,pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
ASSETS=['SOL-USD','BTC-USD','ETH-USD','DOGE-USD']
POLICIES=['proxy_fade','proxy_follow','always_long','MA20_fade']

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
    sx=np.sort(x);pos=x[x>0];neg=x[x<0]
    return {'n':n,'mean_pct':x.mean(),'median_pct':np.median(x),'wins':int((x>0).sum()),'win_rate':(x>0).mean(),
        'mean_winner_pct':pos.mean() if len(pos) else np.nan,'mean_loser_pct':neg.mean() if len(neg) else np.nan,
        'profit_factor':pos.sum()/-neg.sum() if len(neg) else np.nan,'worst_pct':x.min(),'best_pct':x.max(),
        'sum_percentages_not_compounded':x.sum(),'exclude_best1_mean_pct':sx[:-1].mean() if n>1 else np.nan,
        'exclude_best3_mean_pct':sx[:-3].mean() if n>3 else np.nan,'best3_sum_pct':sx[-3:].sum()}

def grouped_boot(values,groups,seed):
    codes,labels=pd.factorize(groups,sort=True);counts=np.bincount(codes,minlength=len(labels));sums=np.zeros((len(labels),values.shape[1]));np.add.at(sums,codes,values)
    rng=np.random.default_rng(seed);weights=rng.multinomial(len(labels),np.full(len(labels),1/len(labels)),size=20000)
    return (weights@sums)/(weights@counts)[:,None],weights,labels

def intervals(x):return {'ci95':np.quantile(x,[.025,.975]),'ci99':np.quantile(x,[.005,.995])}

def main():
    assert (HERE/'PREFLIGHT_PASS').exists(),'Independent sample/prediction preflight required before score'
    assert not (HERE/'summary.json').exists(),'Complete frozen scoring already exists; do not replace'
    sample=json.loads((HERE/'frozen_sample.json').read_text());assert not sample['new_forward_returns_computed']
    assert all(sha(ROOT/p)==h for p,h in sample['source_sha256'].items())
    assert sha(HERE/'frozen_features_predictions.csv')==sample['features_predictions_sha256']
    freeze={'frozen_utc':datetime.now(timezone.utc).isoformat(),'no_new_returns_opened_at_freeze':True,
        'sample_sha256':sha(HERE/'frozen_sample.json'),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [HERE/'PLAN.md',HERE/'BEFORE_SCORING_ADDENDUM.md',Path(__file__),HERE/'frozen_features_predictions.csv']}}
    save('SCORING_FREEZE.json',freeze)
    d=pd.read_csv(HERE/'frozen_features_predictions.csv');d.entry_time=pd.to_datetime(d.entry_time)
    times=pd.DatetimeIndex(sample['entry_times']);N=len(times);assert N==sample['calendar_blocks'] and len(d)==4*N
    ix=pd.MultiIndex.from_product([times,ASSETS],names=['entry_time','asset']);d=d.set_index(['entry_time','asset']).loc[ix].reset_index()
    paths=np.empty((len(d),241,4));checks=0
    for asset in ASSETS:
        px=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_1m.csv.gz',index_col=0,parse_dates=True).sort_index();assert px.index.is_unique
        for i,r in d[d.asset.eq(asset)].iterrows():
            q=px.index.get_loc(r.entry_time);part=px.iloc[q-1:q+240]
            assert part.index.equals(pd.date_range(r.entry_time-pd.Timedelta(minutes=1),periods=241,freq='min'))
            v=part[['open','high','low','close']].to_numpy(float);assert np.isfinite(v).all() and (v>0).all()
            assert (v[:,1]>=np.maximum.reduce([v[:,0],v[:,2],v[:,3]])).all() and (v[:,2]<=np.minimum.reduce([v[:,0],v[:,1],v[:,3]])).all()
            assert abs(v[0,3]-r.price_real)<1e-8
            paths[i]=v;checks+=1
        print('Native frozen target paths loaded:',asset,flush=True)
    ep=paths[:,1,0];xp=paths[:,240,3];raw=((xp/ep-1)*100).reshape(N,4)
    fade=d.proxy_fade_side.to_numpy().reshape(N,4);ma=d.MA20_fade_side.to_numpy().reshape(N,4)
    assert np.array_equal(fade,np.where(d.pred_short.to_numpy().reshape(N,4)>=.5,1,-1))
    assert np.array_equal(ma,np.where(d.ma20_now.to_numpy().reshape(N,4)>=100,1,-1))
    side=np.stack([fade,-fade,np.ones_like(fade),ma]);trade=side*raw[None,:,:];basket=trade.mean(2).T
    assert np.array_equal(basket[:,0],-basket[:,1])
    # Reconstruct every payoff with scalar native entry and exit values.
    maxerr=0.
    for i in range(len(d)):
        b=i//4;a=i%4
        for pi in range(4):maxerr=max(maxerr,abs(float(side[pi,b,a])*(float(xp[i])/float(ep[i])-1)*100-trade[pi,b,a]))
    assert maxerr<1e-12
    weeks=times.to_period('W-SUN').astype(str);quarters=times.to_period('Q').astype(str);years=times.year
    wb,ww,wl=grouped_boot(basket,weeks,2026093031);qb,qw,ql=grouped_boot(basket,quarters,2026093032)
    halves=np.array_split(np.arange(N),2);thirds=np.array_split(np.arange(N),3)
    summaries={};breakdown=[];legs=[];concentration=[]
    for pi,policy in enumerate(POLICIES):
        x=basket[:,pi];ts=trade[pi]
        h=[stats(x[ids]) for ids in halves];th=[stats(x[ids]) for ids in thirds]
        byasset={a:stats(ts[:,j]) for j,a in enumerate(ASSETS)}
        leaveasset={a:stats(np.delete(ts,j,axis=1).mean(1)) for j,a in enumerate(ASSETS)}
        looq=[x[quarters!=q].mean() for q in ql]
        sums={str(q):float(x[quarters==q].sum()) for q in ql}
        summaries[policy]={'basket':stats(x),'asset_trades':stats(ts.ravel()),'weeks':len(wl),'quarters':len(ql),
            'weekly_intervals':intervals(wb[:,pi]),'quarter_intervals':intervals(qb[:,pi]),'chronological_halves':h,'chronological_thirds':th,
            'assets':byasset,'leave_one_asset_out':leaveasset,'minimum_leave_one_quarter_out_mean_pct':min(looq),
            'quarter_sum_percentages_not_compounded':sums,'direction_counts':{'long':int((side[pi]>0).sum()),'short':int((side[pi]<0).sum())},
            'asset_mean_contribution_pct':{a:float(ts[:,j].mean()/4) for j,a in enumerate(ASSETS)}}
        for field,labels in [('year',years),('quarter',quarters)]:
            for value in sorted(set(labels)):
                m=labels==value;breakdown.append({'policy':policy,'breakdown':field,'value':str(value),**stats(x[m])})
        for b in np.argsort(x)[-3:][::-1]:concentration.append({'policy':policy,'entry_time':str(times[b]),'basket_pct':x[b],**{a:ts[b,j]/4 for j,a in enumerate(ASSETS)}})
        for direction,sgn in [('long',1),('short',-1)]:
            m=side[pi]==sgn
            legs.append({'policy':policy,'scope':'all','scope_value':'all','leg':direction,'trades':int(m.sum()),'mean_per_leg_trade_pct':ts[m].mean() if m.any() else np.nan,
                'contribution_per_total_basket_opportunity_pct':np.where(m,ts,0).mean(),'diagnostic_only':True})
            for yy in sorted(set(years)):
                yy_mask=years==yy;mm=m[yy_mask];vv=ts[yy_mask]
                legs.append({'policy':policy,'scope':'year','scope_value':str(yy),'leg':direction,'trades':int(mm.sum()),'mean_per_leg_trade_pct':vv[mm].mean() if mm.any() else np.nan,
                    'contribution_per_total_basket_opportunity_pct':np.where(mm,vv,0).mean(),'diagnostic_only':True})
            for j,a in enumerate(ASSETS):
                mm=m[:,j];vv=ts[:,j]
                legs.append({'policy':policy,'scope':'asset','scope_value':a,'leg':direction,'trades':int(mm.sum()),'mean_per_leg_trade_pct':vv[mm].mean() if mm.any() else np.nan,
                    'contribution_per_total_basket_opportunity_pct':np.where(mm,vv,0).mean()/4,'diagnostic_only':True})
    delta=basket[:,0]-basket[:,3];dtrade=trade[0]-trade[3]
    di={'basket':stats(delta),'weekly_intervals':intervals(wb[:,0]-wb[:,3]),'quarter_intervals':intervals(qb[:,0]-qb[:,3]),
        'chronological_halves':[stats(delta[ids]) for ids in halves],'chronological_thirds':[stats(delta[ids]) for ids in thirds],
        'assets':{a:stats(dtrade[:,j]) for j,a in enumerate(ASSETS)},'leave_one_asset_out':{a:stats(np.delete(dtrade,j,axis=1).mean(1)) for j,a in enumerate(ASSETS)}}
    def gate(r):
        conditions={'at_least250_blocks':N>=250,'at_least12_quarters':len(ql)>=12,'weekly99_lower_positive':r['weekly_intervals']['ci99'][0]>0,
            'quarter95_lower_positive':r['quarter_intervals']['ci95'][0]>0,'both_halves_positive':all(x['mean_pct']>0 for x in r['chronological_halves']),
            'exclude_best3_positive':r['basket']['exclude_best3_mean_pct']>0,'all_leave_one_asset_out_positive':all(x['mean_pct']>0 for x in r['leave_one_asset_out'].values())}
        return {'conditions':conditions,'passed':all(conditions.values()),'failed':[k for k,v in conditions.items() if not v]}
    primarygate=gate(summaries['proxy_fade']);incrementgate=gate(di)
    d['entry_open']=ep;d['exit_240_close']=xp;d['long_gross_pct']=raw.ravel()
    for pi,policy in enumerate(POLICIES):d[policy+'_gross_pct']=trade[pi].ravel()
    d.to_csv(HERE/'window_results.csv',index=False)
    bb=pd.DataFrame({'entry_time':times.astype(str),'week':weeks,'quarter':quarters,'year':years})
    for pi,policy in enumerate(POLICIES):bb[policy+'_gross_pct']=basket[:,pi]
    bb['proxy_minus_MA20_pct']=delta;bb.to_csv(HERE/'basket_results.csv',index=False)
    pd.DataFrame(breakdown).to_csv(HERE/'calendar_breakdown.csv',index=False);pd.DataFrame(legs).to_csv(HERE/'directional_contributions.csv',index=False);pd.DataFrame(concentration).to_csv(HERE/'largest_blocks.csv',index=False)
    np.savez_compressed(HERE/'paths.npz',paths=paths,asset=d.asset.to_numpy(str),entry_time=d.entry_time.astype(str).to_numpy(str))
    np.savez_compressed(HERE/'policy_vectors.npz',policy=np.array(POLICIES),basket_gross_pct=basket.T,trade_gross_pct=trade,sides=side,asset=np.array(ASSETS),entry_time=times.astype(str).to_numpy(str))
    np.savez_compressed(HERE/'bootstrap_arrays.npz',policy=np.array(POLICIES),weekly_means=wb,quarter_means=qb,weekly_weights=ww,quarter_weights=qw,week=np.asarray(wl),quarter=np.asarray(ql))
    save('summary.json',{'phase':'frozen_proxy_fresh_target_historical_replication','sample_blocks':N,'asset_trades':len(d),'model_calls':0,'refits':0,'cost_bps':0,'policies':summaries,
        'proxy_minus_MA20':di,'gross_profit_gate':primarygate,'increment_over_MA20_gate':incrementgate,'two_claims_passed':primarygate['passed'] and incrementgate['passed'],'long_short_legs_descriptive_only':True})
    assert all(sha(ROOT/p)==h for p,h in sample['source_sha256'].items())
    save('evaluation_audit.json',{'passed':True,'native_windows':checks,'native_minutes_per_window':241,'scalar_trade_checks':len(d)*4,'max_scalar_abs_error_pct':maxerr,'frozen_source_hashes_preserved':True,'following_is_exact_negative':True,
        'source_sha256':freeze['source_sha256'],'frozen_sample_sha256':freeze['sample_sha256'],'no_new_models_no_refits':True})
    print(json.dumps(clean({'proxy_fade':summaries['proxy_fade'],'proxy_minus_MA20':di,'gross_profit_gate':primarygate,'increment_gate':incrementgate}),indent=2),flush=True)

if __name__=='__main__':main()
