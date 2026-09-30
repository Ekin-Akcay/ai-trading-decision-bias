"""Exploratory, window-clustered direction/path diagnostics; no bracket-based selection."""
from pathlib import Path
import json,math
import numpy as np
import pandas as pd
from build_dataset import HORIZONS,MAIN
HERE=Path(__file__).resolve().parent
rng=np.random.default_rng(20260929);B=10000

def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,(np.bool_,)):return bool(x)
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x

def save(name,data):
    (HERE/name).write_text(json.dumps(clean(data),indent=2,allow_nan=False))

def bh(p):
    p=np.array(p,float);order=np.argsort(p);q=np.minimum.accumulate((p[order]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1];out=np.empty_like(q);out[order]=np.minimum(q,1);return out

def bootstrap(x):
    x=np.array(x,float);x=x[np.isfinite(x)];n=len(x)
    if n<2:return [None,None]
    means=x[rng.integers(n,size=(B,n))].mean(1)
    return np.quantile(means,[.025,.975]).tolist()

def corr(x,y):
    x=np.array(x,float);y=np.array(y,float);ok=np.isfinite(x)&np.isfinite(y)
    return float(np.corrcoef(x[ok],y[ok])[0,1]) if ok.sum()>2 and x[ok].std()>0 and y[ok].std()>0 else np.nan

def permcorr(x,y):
    x=np.array(x,float);y=np.array(y,float);ok=np.isfinite(x)&np.isfinite(y);x=x[ok];y=y[ok];n=len(x)
    if n<5 or x.std()==0 or y.std()==0:return np.nan,np.nan
    x=(x-x.mean())/x.std();y=(y-y.mean())/y.std();obs=(x*y).mean()
    ix=np.argsort(rng.random((B,n)),axis=1);pv=(x[ix]*y).mean(1)
    return obs,(1+np.sum(np.abs(pv)>=abs(obs)))/(B+1)

def logistic_fit_predict(X,y,Xtest,penalty=1):
    mu=X.mean(0);sd=X.std(0);sd[sd<1e-8]=1
    X=np.c_[np.ones(len(X)),(X-mu)/sd];T=np.c_[np.ones(len(Xtest)),(Xtest-mu)/sd]
    beta=np.zeros(X.shape[1]);pen=np.eye(X.shape[1])*penalty;pen[0,0]=1e-8
    for _ in range(40):
        p=1/(1+np.exp(-np.clip(X@beta,-30,30)));ww=np.maximum(p*(1-p),1e-6)
        step=np.linalg.solve((X.T*ww)@X+pen,X.T@(p-y)+pen@beta);beta-=step
        if np.max(np.abs(step))<1e-7:break
    return 1/(1+np.exp(-np.clip(T@beta,-30,30)))

def main():
    d=pd.read_csv(HERE/'decisions_enriched.csv');w=pd.read_csv(HERE/'windows.csv')
    for c in ['agrees_ma20','agrees_ma50','agrees_visible_trend']+[f'correct_{h}m' for h in HORIZONS]:
        d[c]=d[c].map({True:1,False:0,'True':1,'False':0})
    main=d[d.main].copy();ww=w[w['case'].notna()].sort_values('case').reset_index(drop=True)
    ids=ww.window_id.tolist();N=len(ids);assert N==100
    index={x:i for i,x in enumerate(ids)}
    regimes=[];beh=[];path=[];stability=[];conf=[];models_horizons=[]
    for (protocol,model),g in main.groupby(['protocol','model']):
        tr=g[g.sign!=0]
        beh.append({'protocol':protocol,'model':model,'decisions':len(g),'long':int((g.sign==1).sum()),'short':int((g.sign==-1).sum()),'flat':int((g.sign==0).sum()),'ma20_agreement':tr.agrees_ma20.mean(),'ma50_agreement':tr.agrees_ma50.mean(),'visible_trend_agreement':tr.agrees_visible_trend.mean(),'confidence_mean':tr.confidence.mean(),'confidence_sd':tr.confidence.std(),'stop_atr_median':tr.stop_atr.median(),'stop_atr_IQR':tr.stop_atr.quantile(.75)-tr.stop_atr.quantile(.25)})
        for regime,s in g.groupby('ma_regime'):
            regimes.append({'protocol':protocol,'model':model,'regime':regime,'n':len(s),'long_fraction':(s.sign==1).mean(),'short_fraction':(s.sign==-1).mean(),'flat_fraction':(s.sign==0).mean(),'directional_accuracy_105m':s.correct_105m.mean(),'mean_signed_105m_atr':s.signed_105m_atr.mean()})
        for h in HORIZONS:
            models_horizons.append({'protocol':protocol,'model':model,'horizon_minutes':h,'n_trades':len(tr),'accuracy':tr[f'correct_{h}m'].mean(),'mean_pct':tr[f'signed_{h}m_pct'].mean(),'mean_atr':tr[f'signed_{h}m_atr'].mean(),'median_pct':tr[f'signed_{h}m_pct'].median(),'fraction_time_favorable':tr[f'fraction_favorable_{h}m'].mean()})
        path.append({'protocol':protocol,'model':model,'n':len(tr),'classes':tr.path_15_to_105.value_counts().to_dict(),'first_05atr':tr.favorable_first_05atr.value_counts().to_dict(),'median_favorable_time_fraction':tr.fraction_favorable_105m.median(),'median_mfe_atr':(tr.mfe_105m_pct/tr.atr14_pct).median(),'median_adverse_atr':(-tr.mae_105m_pct/tr.atr14_pct).median(),'median_crossings':tr.crossings_105m.median(),'stopouts_favorable_at105':int(((tr.outcome=='sl')&(tr.signed_105m_pct>0)).sum()),'stopouts_before105_favorable_at105':int(((tr.outcome=='sl')&(tr.minutes_held<=105)&(tr.signed_105m_pct>0)).sum()),'stopouts':int((tr.outcome=='sl').sum())})
        for metric in ['correct_15m','correct_105m','signed_105m_atr','agrees_ma20']:
            rho,p=permcorr(tr.confidence,tr[metric]);conf.append({'protocol':protocol,'model':model,'metric':metric,'n':len(tr),'pearson_r':rho,'p':p})
    good=[i for i,r in enumerate(conf) if np.isfinite(r['p'])]
    for i,q in zip(good,bh([conf[i]['p'] for i in good])):conf[i]['q']=q
    a=main[main.protocol=='v1'];b=main[main.protocol=='v2'];paired=a.merge(b,on=['model','window_id'],suffixes=('_v1','_v2'),validate='one_to_one')
    for model,g in paired.groupby('model'):
        both=g[g.sign_v1!=0]
        stability.append({'model':model,'n':len(g),'same_action':int((g.action_v1==g.action_v2).sum()),'directional_pairs':len(both),'direction_flips':int((both.sign_v1!=both.sign_v2).sum()),'flat_to_position':int((g.sign_v1==0).sum()),'median_stop_v2_over_v1':float((both.stop_pct_v2/both.stop_pct_v1).median()),'confidence_correlation':corr(g.confidence_v1,g.confidence_v2)})
    # All main model rows are reindexed to the same 100 independent market windows.
    signals={};agreement=[]
    for protocol,g in main.groupby('protocol'):
        piv=g.pivot(index='window_id',columns='model',values='sign').reindex(ids)[MAIN]
        vote=piv.mean(axis=1).to_numpy();signals[protocol]={'vote':vote,'majority':np.sign(vote),'unanimous':(np.abs(piv.sum(axis=1))==5).to_numpy(),'confidence':g.groupby('window_id').confidence.mean().reindex(ids).to_numpy()}
        for i,m1 in enumerate(MAIN):
            for m2 in MAIN[i+1:]:
                ok=(piv[m1]!=0)&(piv[m2]!=0)
                agreement.append({'protocol':protocol,'model1':m1,'model2':m2,'paired_trades':int(ok.sum()),'same_direction_fraction':float((piv.loc[ok,m1]==piv.loc[ok,m2]).mean())})
    # One shared permutation per window for every protocol and horizon, retaining inter-horizon dependence.
    perms=np.argsort(rng.random((B,N)),axis=1)
    perm_within=np.tile(np.arange(N),(B,1))
    for regime in ww.ma_regime.unique():
        ix=np.flatnonzero(ww.ma_regime.to_numpy()==regime);perm_within[:,ix]=ix[np.argsort(rng.random((B,len(ix))),axis=1)]
    horizon=[];nullzs=[];observedzs=[]
    baselines={'always_long':np.ones(N),'always_short':-np.ones(N),'ma20':np.where(ww.above20,1.,-1.),'visible_momentum':np.sign(ww.ret_vis_pct.to_numpy())}
    baseline_rows=[];paired_baseline=[]
    for h in HORIZONS:
        ret=ww[f'return_{h}m_pct'].to_numpy();unit=ret/ww.atr14_pct.to_numpy()
        for base,s in baselines.items():baseline_rows.append({'baseline':base,'horizon_minutes':h,'accuracy':float((s*ret>0).mean()),'mean_pct':float((s*ret).mean()),'mean_atr':float((s*unit).mean())})
        for protocol,z in signals.items():
            s=z['majority'];ok=s!=0;val=s*unit;raw=s*ret
            null=(s[perms]*unit).mean(1);nullw=(s[perm_within]*unit).mean(1)
            obs=val.mean();center=null.mean();sd=null.std();observedz=abs((obs-center)/sd);nullz=np.abs((null-center)/sd)
            nullzs.append(nullz);observedzs.append(observedz)
            hit=(s[ok]*ret[ok]>0).mean();hitnull=((s[perms]*ret)>0).sum(1)/ok.sum()
            row={'protocol':protocol,'horizon_minutes':h,'directional_cases':int(ok.sum()),'accuracy':hit,'mean_pct_all_cases':raw.mean(),'mean_atr_all_cases':obs,'median_signed_pct':np.median(raw[ok]),'ci_pct':bootstrap(raw),'ci_atr':bootstrap(val),'null_base_rate_mean_atr':center,'p_permutation':(1+(np.abs(null-center)>=abs(obs-center)).sum())/(B+1),'p_conditional_ma_regime':(1+(np.abs(nullw-nullw.mean())>=abs(obs-nullw.mean())).sum())/(B+1),'p_accuracy':(1+(np.abs(hitnull-hitnull.mean())>=abs(hit-hitnull.mean())).sum())/(B+1),'accuracy_null_mean':hitnull.mean()}
            horizon.append(row)
            for base,bs in baselines.items():
                diff=(s-bs)*unit
                paired_baseline.append({'protocol':protocol,'horizon_minutes':h,'baseline':base,'mean_difference_atr':diff.mean(),'ci_atr':bootstrap(diff)})
    maxnull=np.max(np.column_stack(nullzs),axis=1)
    q=bh([r['p_permutation'] for r in horizon]);qw=bh([r['p_conditional_ma_regime'] for r in horizon]);qa=bh([r['p_accuracy'] for r in horizon])
    for i,r in enumerate(horizon):r.update(q=q[i],q_conditional_ma_regime=qw[i],q_accuracy=qa[i],p_familywise=(1+(maxnull>=observedzs[i]).sum())/(B+1))
    # Candidate context cells, all retained; significance across the entire scan is adjusted.
    cells=[];extreme=np.abs(ww.past_move_atr)>=np.quantile(np.abs(ww.past_move_atr),.75)
    for protocol,z in signals.items():
        s=z['majority'];confhigh=z['confidence']>=np.median(z['confidence'])
        masks={**{x:(ww.ma_regime.to_numpy()==x) for x in ['above_both','below_both','mixed']},'unanimous':z['unanimous'],'not_unanimous':~z['unanimous'],'extreme_visible_move':extreme.to_numpy(),'nonextreme_visible_move':~extreme.to_numpy(),'high_confidence':confhigh,'low_confidence':~confhigh,'majority_long':s==1,'majority_short':s==-1}
        for name,mask in masks.items():
            ix=np.flatnonzero(mask&(s!=0));n=len(ix)
            for h in [15,90,105,240,1440]:
                ret=ww[f'return_{h}m_pct'].to_numpy();v=s[ix]*ret[ix]/ww.atr14_pct.to_numpy()[ix]
                ci=bootstrap(v);p=None
                if n>=15:
                    # Sign-flip mean test is exploratory and assumes symmetry of signed outcomes under its null.
                    null=(rng.choice([-1.,1.],size=(B,n))*v).mean(1);p=(1+(np.abs(null)>=abs(v.mean())).sum())/(B+1)
                cells.append({'protocol':protocol,'cell':name,'horizon_minutes':h,'n':n,'mean_pct':np.mean(s[ix]*ret[ix]),'mean_atr':v.mean(),'accuracy':np.mean(s[ix]*ret[ix]>0),'ci_atr':ci,'p_signflip':p})
    test=[r for r in cells if r['p_signflip'] is not None]
    for r,q in zip(test,bh([r['p_signflip'] for r in test])):r['q']=q
    # Confidence: pool only after centering confidence within model/protocol; aggregate by event.
    main['confidence_centered']=main.confidence-main.groupby(['protocol','model']).confidence.transform('mean')
    # Reasons are descriptive: tag-level return first averaged within window.
    reasons=[]
    for tag in [c for c in main if c.startswith('reason_')]:
        for protocol,g in main.groupby('protocol'):
            for present in [True,False]:
                sub=g[(g[tag]==present)&(g.sign!=0)]
                v=sub.groupby('window_id').signed_105m_atr.mean()
                reasons.append({'protocol':protocol,'tag':tag,'present':present,'decisions':len(sub),'unique_windows':len(v),'mean_direction':sub.sign.mean(),'mean_signed_105m_atr_case_weighted':v.mean(),'ci_atr':bootstrap(v),'mean_confidence':sub.confidence.mean()})
    # Fixed five-fold grouped CV: explain model choices; then try future direction from price alone vs price+AI.
    # Keep neighboring events within 72h in one CV fold, covering overlapping past/future information.
    timeorder=np.argsort(pd.to_datetime(ww.entry_time).to_numpy());blocks=np.empty(N,int);block=-1;last=None
    for idx in timeorder:
        ts=pd.Timestamp(ww.iloc[idx].entry_time)
        if last is None or (ts-last).total_seconds()>72*3600:block+=1
        blocks[idx]=block;last=ts
    unique=np.unique(blocks);assignment={int(b):int(i%5) for i,b in enumerate(rng.permutation(unique))}
    fold=np.array([assignment[int(b)] for b in blocks])
    folds={wid:int(f) for wid,f in zip(ids,fold)};features=['past_move_atr','ma20dist_atr','ma50dist_atr','last_bar_pct','last5_pct','last5_volume_ratio']
    cvchoice=[]
    for protocol,g in main[main.sign!=0].groupby('protocol'):
        X=g[features].to_numpy(float);y=(g.sign.to_numpy()==1).astype(float);F=np.array([folds[v] for v in g.window_id]);pred=np.empty(len(g));base=np.empty(len(g))
        for f in range(5):
            test=F==f;train=~test;pred[test]=logistic_fit_predict(X[train],y[train],X[test]);base[test]=y[train].mean()
        cvchoice.append({'protocol':protocol,'n_directional_decisions':len(g),'groups':100,'price_features_accuracy':np.mean((pred>=.5)==y),'training_majority_accuracy':np.mean((base>=.5)==y),'ma20_rule_accuracy':g.agrees_ma20.mean(),'price_features_brier':np.mean((pred-y)**2)})
    forecast=[];predrows=[]
    Xbase=ww[features].to_numpy(float);Xai=np.c_[Xbase,signals['v1']['vote'],signals['v2']['vote'],signals['v2']['confidence']]
    for h in [15,90,105,240,1440]:
        y=(ww[f'return_{h}m_pct'].to_numpy()>0).astype(float);preds={}
        for name,X in [('price_only',Xbase),('price_plus_AI',Xai)]:
            pred=np.empty(N)
            for f in range(5):
                te=fold==f;pred[te]=logistic_fit_predict(X[~te],y[~te],X[te])
            preds[name]=pred
            forecast.append({'horizon_minutes':h,'features':name,'accuracy':np.mean((pred>=.5)==y),'brier':np.mean((pred-y)**2)})
        delta=(preds['price_plus_AI']-y)**2-(preds['price_only']-y)**2
        forecast.append({'horizon_minutes':h,'features':'incremental_Brier_AI_minus_price_lower_better','mean_difference':delta.mean(),'ci':bootstrap(delta)})
        for i,wid in enumerate(ids):predrows.append({'window_id':wid,'fold':int(fold[i]),'horizon_minutes':h,'actual_up':y[i],'price_probability_up':preds['price_only'][i],'price_plus_ai_probability_up':preds['price_plus_AI'][i]})
    # Sensitivities at the primary seven-candle horizon: halves, leave-one-out, event-date clustering.
    sensitivities=[];order=np.argsort(pd.to_datetime(ww.entry_time).to_numpy());half1=np.zeros(N,bool);half1[order[:50]]=True
    for protocol,z in signals.items():
        v=z['majority']*ww.return_105m_pct.to_numpy()/ww.atr14_pct.to_numpy()
        dates=ww.entry_date
        daily=pd.DataFrame({'date':dates,'v':v}).groupby('date').v.mean()
        loo=(v.sum()-v)/(N-1)
        sensitivities.append({'protocol':protocol,'mean_atr':v.mean(),'early_half_mean_atr':v[half1].mean(),'late_half_mean_atr':v[~half1].mean(),'leave_one_out_range':[loo.min(),loo.max()],'trimmed_10pct_mean_atr':np.sort(v)[10:-10].mean(),'event_days':len(daily),'day_mean_atr':daily.mean(),'day_ci':bootstrap(daily)})
    # Paired within-window direction contrasts, available only on disagreement windows.
    pair_tests=[]
    for proto,g in main.groupby('protocol'):
        for i,m1 in enumerate(MAIN):
            for m2 in MAIN[i+1:]:
                x=g[g.model==m1].merge(g[g.model==m2],on='window_id',suffixes=('_a','_b'))
                x=x[(x.sign_a!=0)&(x.sign_b!=0)&(x.sign_a!=x.sign_b)]
                v=x.signed_105m_atr_a-x.signed_105m_atr_b
                pair_tests.append({'protocol':proto,'model1':m1,'model2':m2,'disagreement_windows':len(x),'mean_difference_atr':v.mean(),'ci_atr':bootstrap(v)})
    tables={'behavior':beh,'regimes':regimes,'per_model_horizons':models_horizons,'paths':path,'stability':stability,'confidence_tests':conf,'model_agreement':agreement,'ensemble_horizons':horizon,'baselines':baseline_rows,'paired_baselines':paired_baseline,'candidate_cells':cells,'reason_tags':reasons,'choice_prediction_cv':cvchoice,'future_prediction_cv':forecast,'sensitivities':sensitivities,'disagreement_contrasts':pair_tests}
    for name,rows in tables.items():save(name+'.json',rows);pd.DataFrame(rows).to_csv(HERE/(name+'.csv'),index=False)
    pd.DataFrame(predrows).to_csv(HERE/'oof_predictions.csv',index=False)
    ensemble=ww.copy()
    for proto,z in signals.items():
        for key,v in z.items():ensemble[f'{proto}_{key}']=v
    ensemble.to_csv(HERE/'ensemble_windows.csv',index=False)
    save('analysis_metadata.json',{'seed':20260929,'resamples':B,'horizons_minutes':HORIZONS,'primary_horizons_minutes':[15,90,105],'main_windows':100,'main_decisions':1000,'folds_by_window':folds,'temporal_CV_blocks':len(unique),'CV_embargo_grouping_hours':72,'CV_features':features,'statistical_caveat':'All exploratory. Window resampling; three overlapping 24h pairs, including one overlapping 105m pair. Shared v1/v2 outcomes are not independent replications. Confidence is not necessarily a fixed-horizon probability. Sign-flip context scan assumes symmetry and is not causally adjusted.'})
    print('Behavior');print(pd.DataFrame(beh).round(3).to_string(index=False))
    print('Primary horizons');print(pd.DataFrame(horizon).query('horizon_minutes in [15,90,105]').round(4).to_string(index=False))
    print('Smallest adjusted candidate q');print(pd.DataFrame(cells).sort_values('q').head(8).to_string(index=False))
    print('Choice CV',cvchoice);print('Confidence smallest q',sorted(conf,key=lambda r:r.get('q',1))[:5]);print('Sensitivity',sensitivities)
if __name__=='__main__':main()
