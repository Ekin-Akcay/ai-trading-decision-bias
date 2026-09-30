"""Independent source-price, time-boundary, fitted-objective, and bootstrap audit."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
w=pd.read_csv(HERE/'forward_predictions.csv');w.entry_time=pd.to_datetime(w.entry_time)
results=json.loads((HERE/'results.json').read_text())
fits=json.loads((HERE/'model_fits.json').read_text())
a=np.load(HERE/'all_information_vectors.npz');boot=np.load(HERE/'quarter_bootstrap_draws.npz')
audit=json.loads((HERE/'audit.json').read_text())
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in audit['source_sha256'].items())
assert len(w)==1020 and w.window_id.nunique()==1020 and w.window_id.tolist()==a['window_id'].tolist()

native_checks=0;native_hashes={}
for asset,group in w.groupby('asset'):
    source=ROOT/f'data/raw/intraday/{asset}_15m.csv.gz'
    px=pd.read_csv(source,index_col=0,parse_dates=True,usecols=[0,1,4]).sort_index()
    assert px.index.is_unique
    pos=px.index.get_indexer(group.entry_time);assert (pos>=0).all()
    ep=px.open.to_numpy()[pos];xp=px.close.to_numpy()[pos+15]
    assert np.isfinite(ep).all() and np.isfinite(xp).all() and (ep>0).all() and (xp>0).all()
    assert (px.index[pos+15]+pd.Timedelta(minutes=15)==pd.DatetimeIndex(group.entry_time)+pd.Timedelta(minutes=240)).all()
    calculated=(xp/ep-1)*100
    np.testing.assert_allclose(calculated,group.gross_240_pct,atol=1e-9,rtol=0)
    native_checks+=len(group);native_hashes[str(source.relative_to(ROOT))]=hashlib.sha256(source.read_bytes()).hexdigest()

numeric=np.column_stack([(100-w.ma20_now)/w.atr14_pct,(100-w.ma50_now)/w.atr14_pct,w.ret_vis_pct/w.atr14_pct,np.log(w.vol24_ratio),np.log(w.atr14_pct)])
dummies=np.column_stack([w.asset.eq(s).to_numpy(float) for s in ['BTC-USD','ETH-USD','DOGE-USD']])
max_gradient=0.;predchecks=0;boundarychecks=0
for fit in fits['folds']:
    y=fit['test_year'];boundary=pd.Timestamp(f'{y}-01-01')
    train=(w.entry_time<boundary-pd.Timedelta(days=7)).to_numpy();test=w.year.eq(y).to_numpy()
    assert train.sum()==fit['training_n'] and test.sum()==fit['test_n']
    assert str(w.entry_time[train].max())==fit['training_end']
    assert (pd.to_datetime(w.loc[test,'training_max_time'])+pd.Timedelta(days=7)<boundary).all()
    np.testing.assert_allclose(numeric[train].mean(0),fit['mu'],rtol=0,atol=1e-12)
    mu=np.array(fit['mu']);sd=np.array(fit['sd'])
    X=np.column_stack([(numeric-mu)/sd,dummies]);Xa=np.column_stack([X,w.AI_short.to_numpy(float)])
    for key,info,xx,truth,col in [('action',fit['action'],X,w.AI_short.to_numpy(float),'pred_short'),*[(tag,info,Xa,w['tag_'+tag].to_numpy(float),'pred_tag_'+tag) for tag,info in fit['reasons'].items()]]:
        if 'constant_laplace' in info:
            expected=(truth[train].sum()+1)/(train.sum()+2)
            assert abs(expected-info['constant_laplace'])<1e-12
            pred=np.full(test.sum(),expected)
        else:
            beta=np.array(info['coefficients']);A=np.column_stack([np.ones(len(w)),xx])
            probabilities=1/(1+np.exp(-np.clip(A@beta,-700,700)))
            gradient=A[train].T@(probabilities[train]-truth[train])+np.r_[0,10*beta[1:]]
            max_gradient=max(max_gradient,float(np.abs(gradient).max()))
            assert np.abs(gradient).max()<1e-7
            pred=probabilities[test]
        np.testing.assert_allclose(pred,w.loc[test,col],rtol=0,atol=1e-12);predchecks+=test.sum()
    beta=np.array(fit['confidence']['coefficients']);A=np.column_stack([np.ones(len(w)),Xa])
    residual=A[train].T@(A[train]@beta-w.confidence.to_numpy()[train])+np.r_[0,10*beta[1:]]
    assert np.abs(residual).max()<1e-8
    pred=np.clip(A[test]@beta,0,1)
    np.testing.assert_allclose(pred,w.loc[test,'pred_confidence'],rtol=0,atol=1e-12);predchecks+=test.sum();boundarychecks+=1

# Rebuild bootstrap via explicit per-row multiplicities, without flattened quarter/stratum bins.
quarter_lookup={q:i for i,q in enumerate(boot['quarter'])}
quarter_index=np.array([quarter_lookup[q] for q in w.quarter])
row_weight=boot['weights'][:,quarter_index].astype(float)
base_return=w.gross_240_pct.to_numpy()
ci_checks=0;control_checks=0
for policy_index,result in enumerate(results):
    assert result['candidate']==a['candidate'][policy_index]
    selected=a['selected'][policy_index];side=a['direction'][policy_index]
    allowed=w.scored_forward_fold.to_numpy(bool) if policy_index<9 else w.cohort.eq('paired90').to_numpy()
    ids=np.flatnonzero(selected);den=row_weight[:,ids].sum(1)
    pnl=side*base_return;own_sum=row_weight[:,ids]@pnl[ids];valid=den>0
    q95=np.quantile(own_sum[valid]/den[valid],[.025,.975])
    np.testing.assert_allclose(q95,result['all']['ci95_quarter'],rtol=0,atol=1e-10);ci_checks+=2
    ref='primary_action' if policy_index<9 else 'action_NO_MA'
    for is_ai,field,vector_name in [(False,'price_matched_increment','price_increment_pct'),(True,'direction_matched_increment','direction_increment_pct')]:
        keys=['cohort','asset','era','ma_regime']+([ref] if is_ai else [])
        expected=np.full(len(w),np.nan);control_sum=np.zeros(len(row_weight))
        for _,group in w.loc[allowed].groupby(keys):
            g=group.index.to_numpy();s=g[selected[g]]
            expected[g]=side[g]*base_return[g].mean()
            if len(s):
                count=row_weight[:,g].sum(1)
                total=row_weight[:,g]@base_return[g]
                means=np.divide(total,count,out=np.zeros(len(count)),where=count>0)
                selected_sign=row_weight[:,s]@side[s]
                control_sum+=selected_sign*means
        residual=pnl-expected
        np.testing.assert_allclose(residual[allowed],a[vector_name][policy_index,allowed],rtol=0,atol=1e-10)
        assert abs(residual[selected].mean()-result[field]['mean_pct'])<1e-10
        v=(own_sum-control_sum)[valid]/den[valid]
        for label,quantile in [('ci95_quarter',[.025,.975]),('ci95_family11_bonferroni_quarter',[.025/11,1-.025/11])]:
            np.testing.assert_allclose(np.quantile(v,quantile),result[field][label],rtol=0,atol=1e-10);ci_checks+=2
        control_checks+=int(allowed.sum())
    # A selected simultaneous event may not be split between chronological halves.
    selected_times=sorted(w.entry_time[selected].unique());mid=len(selected_times)//2
    sets=[set(selected_times[:mid]),set(selected_times[mid:])];assert not sets[0]&sets[1]
    for t,h in zip(sets,result['all']['halves']):
        m=selected&w.entry_time.isin(t).to_numpy();assert m.sum()==h['n']
        if m.any():assert abs(pnl[m].mean()-h['mean_pct'])<1e-10

valid=w.scored_forward_fold.to_numpy(bool)
correct=int(((w.pred_short.to_numpy()[valid]>=.5)==w.AI_short.to_numpy()[valid]).sum())
out={'passed':True,'source_hashes_unchanged':True,'native_15m_entry_and_four_hour_exit_checks':native_checks,'forward_training_boundaries_checked':boundarychecks,'independent_auxiliary_prediction_checks':int(predchecks),'maximum_logistic_objective_gradient':max_gradient,'control_row_checks':control_checks,'independent_bootstrap_interval_endpoints_checked':ci_checks,'bootstrap_group_means_reestimated_each_draw':True,'simultaneous_assets_not_split_in_halves':True,'action_prediction_correct':correct,'action_prediction_n':int(valid.sum()),'action_prediction_accuracy':correct/valid.sum(),'this_is_not_market_prediction_accuracy':True,'not_causal_MA_attribution':True,'no_model_calls':True,'native_price_source_sha256':native_hashes}
(HERE/'independent_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
