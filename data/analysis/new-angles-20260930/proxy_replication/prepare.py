"""Freeze a complete six-hour-grid proxy sample without calculating future returns."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib
import numpy as np,pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'src'))
from nai.sim import build_snapshot
ASSETS=['SOL-USD','BTC-USD','ETH-USD','DOGE-USD'];HOUR=3600*10**9
FIT=HERE.parent/'information/model_fits.json'
PRIOR=ROOT/'data/analysis/gross-edge-20260929/ma_ablation/design/fresh_blocks.json'
COVER=ROOT/'data/analysis/gross-edge-20260929/design/coverage_and_candidate_masks.npz'
COVMETA=COVER.with_name('fresh_blocks.json')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,np.integer):return int(x)
    if isinstance(x,np.bool_):return bool(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x
def save(name,x):(HERE/name).write_text(json.dumps(clean(x),indent=2,allow_nan=False)+'\n')

def main():
    assert not (HERE/'frozen_sample.json').exists(),'Sample already frozen; do not replace'
    sources=[HERE/'PLAN.md',Path(__file__),FIT,PRIOR,COVER,COVMETA,ROOT/'src/nai/sim.py']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
    fits=json.loads(FIT.read_text());fmap={x['test_year']:x for x in fits['folds'] if 'action' in x}
    assert set(fmap)=={2022,2023,2024,2025,2026}
    old=json.loads(PRIOR.read_text());prior={pd.Timestamp(x['entry_time']).value:float(x['outcome_hours']) for x in old['prior_exposure_intervals']}
    assert len(prior)==591
    for x in old['blocks']:
        t=pd.Timestamp(x['entry_time']).value;prior[t]=max(prior.get(t,0),6)
    assert len(prior)==681
    cached=np.load(COVER);allns=cached['entry_time_ns'];coverage=cached['all_asset_coverage'].astype(bool)
    ix=pd.DatetimeIndex(allns);base=ix.year.isin(sorted(fmap))&(ix.minute==0)&(ix.hour%6==0)
    calendar=np.ones(len(ix),bool)
    for t,h in prior.items():calendar &= (allns+4*HOUR<=t-50*HOUR)|(allns>=t+h*HOUR)
    embargo=np.array([t.value>=pd.Timestamp(fmap[t.year]['training_end']).value+7*24*HOUR if t.year in fmap else False for t in ix])
    eligible=base&coverage&calendar&embargo;selected=allns[eligible]
    # Cached coverage remains valid only if the original input archives match their recorded hashes.
    cm=json.loads(COVMETA.read_text())
    for asset in ASSETS:
        for tf in ['15m','1m']:
            rel=f'data/raw/intraday/{asset}_{tf}.csv.gz';p=ROOT/rel
            actual=sha(p);assert actual==cm['source_sha256'][rel],('stale coverage cache',rel)
            hashes[rel]=actual
    rows=[];invalid=set()
    for asset in ASSETS:
        px=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_15m.csv.gz',index_col=0,parse_dates=True).sort_index()
        for t in pd.DatetimeIndex(selected):
            snap=build_snapshot(px,t-pd.Timedelta(minutes=15),40,200)
            features={k:float(snap[k]) for k in ['price_real','ma20_now','ma50_now','ret_vis_pct','vol24_ratio','atr14_pct']}
            if not np.isfinite(list(features.values())).all() or features['atr14_pct']<=0 or features['vol24_ratio']<=0:
                invalid.add(t.value);continue
            numeric=np.array([(100-features['ma20_now'])/features['atr14_pct'],(100-features['ma50_now'])/features['atr14_pct'],features['ret_vis_pct']/features['atr14_pct'],np.log(features['vol24_ratio']),np.log(features['atr14_pct'])])
            f=fmap[t.year];x=np.r_[1,(numeric-np.array(f['mu']))/np.array(f['sd']),[float(asset==a) for a in ASSETS[1:]]]
            pred=1/(1+np.exp(-np.clip(x@np.array(f['action']['coefficients']),-700,700)))
            rows.append({'entry_time':str(t),'entry_ns':int(t.value),'asset':asset,'model_year':int(t.year),'training_end':f['training_end'],'pred_short':float(pred),'proxy_fade_side':1 if pred>=.5 else -1,'MA20_fade_side':1 if features['ma20_now']>=100 else -1,**features})
        print('Pre-entry features and frozen predictions complete:',asset,flush=True)
    selected=np.array([t for t in selected if t not in invalid],dtype=np.int64)
    d=pd.DataFrame(rows);d=d[d.entry_ns.isin(selected)].sort_values(['entry_time','asset']).reset_index(drop=True)
    assert len(d)==4*len(selected) and d.groupby('entry_time').asset.apply(set).eq(set(ASSETS)).all()
    assert np.diff(selected).min()>=6*HOUR
    for t,h in prior.items():assert np.all((selected+4*HOUR<=t-50*HOUR)|(selected>=t+h*HOUR))
    # Reproduce existing annual forward predictions without touching any new outcomes.
    refpath=HERE.parent/'information/forward_predictions.csv';sources.append(refpath);hashes[str(refpath.relative_to(ROOT))]=sha(refpath)
    ref=pd.read_csv(refpath);ref=ref[ref.scored_forward_fold.astype(bool)]
    errors=[]
    for row in ref.itertuples(index=False):
        f=fmap[int(row.year)];numeric=np.array([(100-row.ma20_now)/row.atr14_pct,(100-row.ma50_now)/row.atr14_pct,row.ret_vis_pct/row.atr14_pct,np.log(row.vol24_ratio),np.log(row.atr14_pct)])
        x=np.r_[1,(numeric-np.array(f['mu']))/np.array(f['sd']),[float(row.asset==a) for a in ASSETS[1:]]]
        p=1/(1+np.exp(-np.clip(x@np.array(f['action']['coefficients']),-700,700)))
        errors.append(abs(p-row.pred_short))
    assert len(errors)==803 and max(errors)<1e-12
    d.to_csv(HERE/'frozen_features_predictions.csv',index=False)
    dt=pd.DatetimeIndex(selected);years={str(k):int(v) for k,v in pd.Series(dt.year).value_counts().sort_index().items()};quarters={str(k):int(v) for k,v in pd.Series(dt.to_period('Q').astype(str)).value_counts().sort_index().items()}
    result={'study':'frozen_AI_behavior_proxy_fresh_target_replication','created_utc':datetime.now(timezone.utc).isoformat(),'assets':ASSETS,'calendar_blocks':len(selected),'asset_windows':len(d),'entry_times':[str(t) for t in dt],
        'grid':'Every UTC00/06/12/18 time with four-asset coverage, available annual model and no prior-exposure intersection','prior_exposure_intervals':[{'entry_time':str(pd.Timestamp(t)),'history_hours':50,'outcome_hours':h} for t,h in sorted(prior.items())],
        'prior_intervals':len(prior),'coverage_grid_count':len(ix),'utc6h_annual_fit_grid_count':int(base.sum()),'fit_grid_and_coverage':int((base&coverage).sum()),'fit_grid_coverage_exclusion_count':int(eligible.sum()),'excluded_invalid_preentry_feature_blocks':len(invalid),
        'minimum_entry_gap_hours':float(np.diff(selected).min()/HOUR),'years':years,'quarters':quarters,'new_forward_returns_computed':False,'new_forward_return_files_opened':False,'coverage_reused_from_previous_mechanical_checks':True,
        'features_predictions_file':'frozen_features_predictions.csv','features_predictions_sha256':sha(HERE/'frozen_features_predictions.csv'),'existing_prediction_reconciliations':len(errors),'max_existing_prediction_abs_error':max(errors),'source_sha256':hashes}
    assert all(sha(ROOT/k)==h for k,h in hashes.items())
    save('frozen_sample.json',result)
    save('FEASIBILITY.json',{k:result[k] for k in ['calendar_blocks','asset_windows','prior_intervals','utc6h_annual_fit_grid_count','fit_grid_and_coverage','fit_grid_coverage_exclusion_count','excluded_invalid_preentry_feature_blocks','years','quarters','minimum_entry_gap_hours','existing_prediction_reconciliations','max_existing_prediction_abs_error','new_forward_returns_computed']})
    print(json.dumps(json.loads((HERE/'FEASIBILITY.json').read_text()),indent=2),flush=True)

if __name__=='__main__':main()
