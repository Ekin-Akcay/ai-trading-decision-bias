"""Dormant independent native-price/statistical auditor; explicit release required.

This module performs no IO at import. No post-entry native price is read until
the command-line release and stage-specific hashed release artifact pass.
"""
from pathlib import Path
import argparse
import csv
import gzip
import hashlib
import json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
ROOT=STUDY.parents[2]
SEED=2026093051
DRAWS=40000

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def timestamp(value):
    ts=pd.Timestamp(value)
    return ts.tz_convert('UTC').tz_localize(None) if ts.tzinfo else ts

def native_case(minute,case):
    """Independent scalar gate and delayed-time-trade accounting."""
    t0=timestamp(case['t0']);i=minute.index.get_loc(t0)
    original=minute.iloc[i-3000:i]
    gate=minute.iloc[i:i+30]
    held=minute.iloc[i+30:i+150]
    assert len(original)==3000 and len(gate)==30 and len(held)==120
    alltimes=minute.index[i-3000:i+150]
    assert alltimes.equals(pd.date_range(t0-pd.Timedelta(minutes=3000),periods=3150,freq='1min'))
    assert held.index[0]==timestamp(case['entry_time'])
    assert held.index[-1]+pd.Timedelta(minutes=1)==timestamp(case['horizon_end'])
    volume=original.volume.to_numpy(float)
    assert np.isfinite(volume).all() and (volume>=0).all()
    chunks=np.array([volume[j:j+30].sum() for j in range(0,3000,30)])
    gate_volume=float(gate.volume.sum());median=float(np.median(chunks))
    assert median>0
    ratio=gate_volume/median
    move=100*(float(gate.close.iloc[-1])/float(gate.open.iloc[0])-1)
    assert abs(move)>=.5*float(case['atr14_pct']) and ratio<=.75
    assert (move>0)==(case['direction']=='up')
    ohlc=held[['open','high','low','close']].to_numpy(float)
    assert np.isfinite(ohlc).all() and (ohlc>0).all()
    sign=-1 if case['direction']=='up' else 1
    entry=float(ohlc[0,0]);exit_price=float(ohlc[-1,3])
    gross=sign*100*(exit_price-entry)/entry
    signed_extremes=sign*100*(ohlc[:,1:3]-entry)/entry
    return {
        'case':int(case.get('case',case.get('case_id'))),'window_id':case['window_id'],
        'direction':case['direction'],'asset':case['asset'],'side':sign,
        'gate_move_pct':move,'volume_ratio':ratio,'entry_price':entry,'exit_price':exit_price,
        'gross_pct':gross,'mfe_pct':max(0.,float(signed_extremes.max())),
        'mae_pct':min(0.,float(signed_extremes.min())),
        'entry_time':str(held.index[0]),'last_held_minute':str(held.index[-1]),
        'exit_time':str(held.index[-1]+pd.Timedelta(minutes=1)),
    },ohlc

def weighted_fixed_effect(y,aligned,strata,weights):
    """Within-stratum centering with per-draw weights, independently expressed."""
    y=np.asarray(y,float);a=np.asarray(aligned,float)
    w=np.atleast_2d(np.asarray(weights,float))
    numer=np.zeros(len(w));denom=np.zeros(len(w))
    for label in np.unique(strata):
        mask=strata==label;local=w[:,mask]
        n=local.sum(axis=1);ones=local@a[mask]
        mean_a=np.divide(ones,n,out=np.zeros_like(ones),where=n>0)
        # Algebraically equivalent centered cross-product, but this audit
        # constructs residualized alignment instead of scorer group totals.
        resid=a[mask][None,:]-mean_a[:,None]
        numer+=(local*resid)@y[mask]
        denom+=(local*resid*resid).sum(axis=1)
    return np.divide(numer,denom,out=np.full(len(w),np.nan),where=denom>1e-12)

def bootstrap_direction(frame,weights):
    y=frame.gross_pct.to_numpy(float);a=frame.aligned.to_numpy(bool)
    # Root quarter draws are mapped to actual per-case replication weights.
    aligned_count=weights[:,a].sum(axis=1)
    aligned_sum=weights[:,a]@y[a]
    mean=np.divide(aligned_sum,aligned_count,out=np.full(len(weights),np.nan),where=aligned_count>0)
    stratum=(frame.asset.astype(str)+'|'+frame.ma20_above.astype(int).astype(str)).to_numpy(str)
    beta=weighted_fixed_effect(y,a,stratum,weights)
    return np.column_stack([mean,beta])

def descriptive(values):
    values=np.asarray(values,float)
    if not len(values):return {'n':0}
    wins=values[values>0];losses=values[values<0]
    return {'n':len(values),'mean':float(values.mean()),'median':float(np.median(values)),
        'wins':len(wins),'losses':len(losses),'zeros':int((values==0).sum()),
        'win_rate':float((values>0).mean()),'best':float(values.max()),'worst':float(values.min()),
        'mean_win':float(wins.mean()) if len(wins) else None,'mean_loss':float(losses.mean()) if len(losses) else None,
        'profit_factor':float(wins.sum()/-losses.sum()) if len(losses) else None}

def native_subset(asset,cases,interval):
    """Parse numeric OHLCV only within released cases' required time ranges."""
    needed=set()
    for case in cases:
        t=timestamp(case['t0'])
        start=t-pd.Timedelta(minutes=3000 if interval=='1m' else 3015)
        n=3150 if interval=='1m' else 201
        needed.update(str(x) for x in pd.date_range(start,periods=n,freq=interval.replace('m','min')))
    path=ROOT/f'data/raw/intraday/{asset}_{interval}.csv.gz'
    rows=[];times=[]
    with gzip.open(path,'rt',newline='') as f:
        reader=csv.DictReader(f)
        for row in reader:
            time=row['ts'].replace('T',' ').removesuffix('+00:00').removesuffix('Z')
            if time in needed:
                times.append(time);rows.append([float(row[k]) for k in ['open','high','low','close','volume']])
    assert len(times)==len(set(times))==len(needed),(asset,interval,'Incomplete native audit coverage')
    return pd.DataFrame(rows,index=pd.to_datetime(times),columns=['open','high','low','close','volume']).sort_index()

def basic_reference(x):
    x=np.asarray(x,float);v=descriptive(x)
    if not len(x):return {'n':0,'mean_gross_pct':None}
    return {'n':len(x),'mean_gross_pct':v['mean'],'median_gross_pct':v['median'],'sum_trade_pct_not_portfolio':float(x.sum()),
        'wins':v['wins'],'losses':v['losses'],'zero_returns':v['zeros'],'win_rate':v['win_rate'],
        'profit_factor':v['profit_factor'] if v['losses'] else (np.inf if v['wins'] else None),
        'mean_winner_pct':v['mean_win'],'mean_loser_pct':v['mean_loss'],'best_pct':v['best'],'worst_pct':v['worst']}

def interval_reference(x):
    finite=np.isfinite(x);valid=x[finite];all_draws=np.where(finite,x,-np.inf)
    return {'ordinary95_finite_draw_interval':np.quantile(valid,[.025,.975],method='inverted_cdf') if len(valid) else [None,None],
        'ordinary95_lower_with_undefined_as_minus_infinity':np.quantile(all_draws,.025,method='inverted_cdf'),
        'simultaneous98_75_one_sided_lower':np.quantile(all_draws,.0125,method='inverted_cdf'),
        'undefined_draws':int((~finite).sum()),'undefined_fraction':float((~finite).mean()),'total_draws':len(x),'family_size':4,'quantile_method':'inverted_cdf'}

def all_bootstraps(frame,case_weights):
    y=frame.gross_pct.to_numpy(float);a=frame.aligned.to_numpy(bool);ma=frame.ma_selected.to_numpy(bool)
    masks={'aligned':a,'opposed':~a,'price_only':np.ones(len(frame),bool),'MA20_control':ma}
    denominator=case_weights.sum(axis=1);out={}
    safe=lambda num,den:np.divide(num,den,out=np.full(len(den),np.nan),where=den>0)
    for name,mask in masks.items():
        total=case_weights[:,mask]@y[mask];n=case_weights[:,mask].sum(axis=1)
        out[name+'_mean']=safe(total,n)
        per_gate=name if name!='MA20_control' else 'MA20'
        out[per_gate+'_per_gate']=safe(total,denominator)
    out['raw_aligned_minus_opposed']=out['aligned_mean']-out['opposed_mean']
    out['aligned_minus_price_per_gate']=out['aligned_per_gate']-out['price_only_per_gate']
    out['aligned_minus_MA20_per_gate']=out['aligned_per_gate']-out['MA20_per_gate']
    strata=(frame.asset.astype(str)+'|'+frame.ma20_above.astype(int).astype(str)).to_numpy(str)
    out['adjusted_AI_spread']=weighted_fixed_effect(y,a,strata,case_weights)
    return out

def clean(value):
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):return [clean(v) for v in value]
    if isinstance(value,(bool,np.bool_)):return bool(value)
    if isinstance(value,(int,np.integer)):return int(value)
    if isinstance(value,(float,np.floating)):
        return float(value) if np.isfinite(value) else ('Infinity' if value>0 else '-Infinity' if value<0 else None)
    return value

def release_guard(run,stage):
    release_path=run/'score_release.json'
    assert release_path.is_file(),'Explicit root score release is required before native post-entry reads.'
    release=json.loads(release_path.read_text())
    assert release['stage']==stage
    for field,filename in [('manifest_sha256','manifest.json'),('isolation_audit_sha256','isolation_audit.json'),
                           ('progress_sha256','progress.json'),('accepted_decisions_sha256','accepted_decisions.jsonl')]:
        assert release[field]==sha(run/filename),(field,'Release does not match current collected inputs')
    progress=json.loads((run/'progress.json').read_text())
    isolation=json.loads((run/'isolation_audit.json').read_text())
    assert progress['status']=='decisions_collected' and not progress['missing_requested_pairs']
    assert isolation['all_accepted_passed'] is True
    ids=list(map(int,release['case_ids']))
    assert len(ids)==len(set(ids)) and set(ids)<=set(progress['authorized_cases'])
    records=[json.loads(line) for line in (run/'accepted_decisions.jsonl').read_text().splitlines() if line.strip()]
    accepted=[row for row in records if int(row['case']) in ids]
    assert len(accepted)==len(ids) and {int(row['case']) for row in accepted}==set(ids)
    assert all(row['model']=='gpt-5.6-terra' and row['decision']['action'] in ['long','short'] for row in accepted)
    return release

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--release',required=True,help='Exact run ID released by root.')
    parser.add_argument('--stage',required=True,choices=['screen','confirmation'])
    parser.add_argument('--evidence-dir',help='Immutable stage inputs, when subsequent collection changed live checkpoints.')
    args=parser.parse_args()
    run=ROOT/'data/sim'/args.release
    assert run.is_dir() and run.name.startswith('ai-timing-200-')
    evidence=Path(args.evidence_dir) if args.evidence_dir else run
    release=release_guard(evidence,args.stage)
    manifest=json.loads((evidence/'manifest.json').read_text());bycase={int(c['case']):c for c in manifest['cases']}
    ids=sorted(map(int,release['case_ids']));cases=[bycase[i] for i in ids]
    assert all(c['stage']==args.stage for c in cases)
    if args.stage=='screen':assert ids==sorted(c['case'] for c in manifest['cases'] if c['stage']=='screen')
    else:assert ids==sorted(json.loads((run/'screen/continuation.json').read_text())['selected_confirmation_case_ids'])
    records={int(r['case']):r for r in [json.loads(x) for x in (evidence/'accepted_decisions.jsonl').read_text().splitlines() if x.strip()]}
    out=run/args.stage
    assert (out/'scoring_audit.json').exists(),'Wait for root scorer to finish before independent replay.'
    reported=pd.read_csv(out/'trade_ledger.csv').set_index('case')
    summary=json.loads((out/'summary.json').read_text())
    saved_paths=np.load(out/'paths.npz');saved_boot=np.load(out/'bootstrap_arrays.npz')
    assert np.array_equal(saved_paths['case'],ids)
    checks=0;max_error=0.
    def compare(expected,actual,label):
        nonlocal checks,max_error
        if isinstance(expected,dict):
            for k,v in expected.items():compare(v,actual[k],label+'.'+k)
        elif isinstance(expected,(list,tuple,np.ndarray)):
            assert len(expected)==len(actual),(label,'length')
            for i,(a,b) in enumerate(zip(expected,actual)):compare(a,b,label+f'[{i}]')
        elif expected is None:assert actual is None,(label,actual)
        elif isinstance(expected,(str,bool,np.bool_)):assert expected==actual,(label,expected,actual)
        else:
            a=float(expected);b=float(actual) if actual is not None else np.nan
            if np.isnan(a):assert np.isnan(b),(label,a,b)
            elif np.isinf(a):assert a==b,(label,a,b)
            else:
                error=abs(a-b);max_error=max(max_error,error)
                assert np.isfinite(b) and error<=2e-9,(label,a,b,error)
        checks+=1
    refs=[];native_hashes={}
    for asset in sorted({c['asset'] for c in cases}):
        subset=[c for c in cases if c['asset']==asset]
        minute=native_subset(asset,subset,'1m');bars=native_subset(asset,subset,'15m')
        for tf in ['1m','15m']:
            rel=f'data/raw/intraday/{asset}_{tf}.csv.gz';native_hashes[rel]=sha(ROOT/rel)
            assert native_hashes[rel]==manifest['original_sha256'][rel]
        for case in subset:
            row,path=native_case(minute,case);cid=row['case'];dec=records[cid]['decision'];actual=reported.loc[cid]
            h=bars.loc[timestamp(case['t0'])-pd.Timedelta(minutes=3015):timestamp(case['t0'])-pd.Timedelta(minutes=15)]
            assert len(h)==201
            hc=h.close.to_numpy();hh=h.high.to_numpy();hl=h.low.to_numpy()
            tr=np.maximum(hh[1:]-hl[1:],np.maximum(abs(hh[1:]-hc[:-1]),abs(hl[1:]-hc[:-1])))
            atr=tr[-14:].mean()/hc[-1]*100;ma=hc[-20:].mean()/hc[-1]*100
            compare(atr,case['atr14_pct'],f'{cid}.ATR');compare(ma,case['ma20_now'],f'{cid}.MA20')
            compare(row['gate_move_pct'],case['gate_move_pct'],f'{cid}.gate_move')
            compare(row['volume_ratio'],case['volume_ratio'],f'{cid}.gate_volume')
            aligned=dec['action']==('short' if row['side']==-1 else 'long');above=ma<=100;ma_selected=above if row['side']==1 else not above
            row.update(aligned=aligned,ma20_above=above,ma_selected=ma_selected,t0=str(timestamp(case['t0'])),year=timestamp(case['t0']).year,quarter=str(timestamp(case['t0']).to_period('Q')))
            fields={'window_id':case['window_id'],'asset':asset,'direction':case['direction'],'stage':args.stage,'trade_side':row['side'],
                'AI_action':dec['action'],'AI_confidence':dec['confidence'],'AI_reason':dec['reason'],'AI_aligned':bool(aligned),
                'above_equal_MA20':bool(above),'MA20_control_selected':bool(ma_selected),'valid_coverage':True,'exclusion':'none','held_minutes':120,
                'entry_time':row['entry_time'],'horizon_end':row['exit_time'],'last_exit_bar_time':row['last_held_minute'],
                'entry_price':row['entry_price'],'exit_price':row['exit_price'],'gate_gross_pct':row['gross_pct'],'mfe_pct':row['mfe_pct'],'mae_pct':row['mae_pct'],
                'AI_opportunity_gross_pct':row['gross_pct'] if aligned else 0.,'opposed_opportunity_gross_pct':0. if aligned else row['gross_pct'],
                'MA20_opportunity_gross_pct':row['gross_pct'] if ma_selected else 0.}
            compare(fields,actual.to_dict(),str(cid))
            np.testing.assert_allclose(path,saved_paths['paths'][ids.index(cid)],rtol=0,atol=0)
            checks+=path.size;refs.append(row)
        print('Native audit passed',asset,len(subset),flush=True)
    frame=pd.DataFrame(refs).sort_values('case').reset_index(drop=True)
    quarters=sorted(frame.quarter.unique());qcount=len(quarters)
    weights=np.random.default_rng(SEED).multinomial(qcount,np.full(qcount,1/qcount),size=DRAWS)
    assert np.array_equal(saved_boot['quarter_weights'],weights)
    assert np.array_equal(saved_boot['quarters'],quarters)
    checks+=weights.size
    point_results={}
    for direction in ['up','down']:
        g=frame[frame.direction.eq(direction)].sort_values(['t0','case'])
        if not len(g):continue
        d=summary['directions'][direction];a=g[g.aligned];o=g[~g.aligned];ma=g[g.ma_selected]
        for name,subset in [('aligned',a),('opposed',o),('price_only',g),('MA20_control',ma)]:compare(basic_reference(subset.gross_pct),d[name],direction+'.'+name)
        case_weights=weights[:,[quarters.index(q) for q in g.quarter]]
        bootstrap=all_bootstraps(g,case_weights)
        for name,array in bootstrap.items():
            reference=saved_boot[direction+'__'+name]
            np.testing.assert_allclose(array,reference,rtol=0,atol=2e-9,equal_nan=True)
            checks+=array.size
        for key,stat in [('primary_aligned_mean_interval','aligned_mean'),('primary_adjusted_spread_interval','adjusted_AI_spread'),('raw_spread_interval','raw_aligned_minus_opposed')]:compare(interval_reference(bootstrap[stat]),d[key],direction+'.'+key)
        strata=(g.asset.astype(str)+'|'+g.ma20_above.astype(int).astype(str)).to_numpy(str)
        point=weighted_fixed_effect(g.gross_pct,g.aligned,strata,np.ones((1,len(g))))[0]
        compare(point,d['fixed_effects']['adjusted_aligned_minus_opposed_pct'],direction+'.FE')
        mixed_a=mixed_o=mixed=0
        for label in np.unique(strata):
            local=g.iloc[np.flatnonzero(strata==label)];an=int(local.aligned.sum());on=len(local)-an
            if an and on:mixed+=1;mixed_a+=an;mixed_o+=on
        compare({'mixed_aligned_n':mixed_a,'mixed_opposed_n':mixed_o,'mixed_strata':mixed},d['fixed_effects'],direction+'.mixed')
        for field in ['asset','year','quarter']:
            for value,local in g.groupby(field):
                reference={name:basic_reference(z.gross_pct) for name,z in [('price_only',local),('aligned',local[local.aligned]),('opposed',local[~local.aligned])]}
                compare(reference,d['breakdowns'][field][str(value)],direction+'.'+field+'.'+str(value))
        half_means=[]
        for i,half in enumerate(np.array_split(g.case.to_numpy(),2)):
            stats=basic_reference(a[a.case.isin(half)].gross_pct);half_means.append(stats['mean_gross_pct'])
            compare({'half':i+1,'price_gate_cases':len(half),**stats},d['chronological_halves'][i],direction+'.half')
        winners=a[a.gross_pct>0].sort_values(['gross_pct','case'],ascending=[False,True]);best3=None
        for n in [1,3]:
            omitted=winners.case.iloc[:n].tolist();stats=basic_reference(a[~a.case.isin(omitted)].gross_pct)
            compare({'removed_cases':omitted,**stats},d['remove_largest_winning_events'][str(n)],direction+'.tail')
            if n==3:best3=stats['mean_gross_pct']
        for name,subset in [('aligned',a),('opposed',o),('price_only',g),('MA20',ma)]:
            compare({'trades':len(subset),'valid_gates':len(g),'per_gate_mean_pct':subset.gross_pct.sum()/len(g),'conditional_mean_pct':subset.gross_pct.mean() if len(subset) else None},d['controls'][name],direction+'.controls.'+name)
        for name in ['aligned_per_gate','opposed_per_gate','price_only_per_gate','MA20_per_gate','aligned_minus_price_per_gate','aligned_minus_MA20_per_gate']:
            compare(interval_reference(bootstrap[name]),d['controls'][name+'_interval'],direction+'.controls.'+name)
        spread=a.gross_pct.mean()-o.gross_pct.mean() if len(a) and len(o) else None
        screen={'at_least5_aligned':len(a)>=5,'at_least5_opposed':len(o)>=5,'positive_aligned_mean':len(a)>0 and a.gross_pct.mean()>0,'positive_raw_spread':spread is not None and spread>0}
        confirm={'aligned_mean_simultaneous_lower_positive':interval_reference(bootstrap['aligned_mean'])['simultaneous98_75_one_sided_lower']>0,'adjusted_spread_simultaneous_lower_positive':interval_reference(bootstrap['adjusted_AI_spread'])['simultaneous98_75_one_sided_lower']>0,
            'at_least10_aligned_in_mixed_strata':mixed_a>=10,'at_least10_opposed_in_mixed_strata':mixed_o>=10,'aligned_positive_in_both_halves':all(v is not None and v>0 for v in half_means),'positive_after_removing_best3_winners':best3 is not None and best3>0}
        compare(screen,d['screen_criteria'],direction+'.screen');compare(all(screen.values()),d['screen_pass'],direction+'.screen_pass')
        compare(confirm,d['confirmation_criteria'],direction+'.confirmation');compare(args.stage=='confirmation' and all(confirm.values()),d['confirmed'],direction+'.confirmed')
        point_results[direction]={'aligned_n':len(a),'opposed_n':len(o),'aligned_mean_pct':a.gross_pct.mean() if len(a) else None,'adjusted_spread_pct':point,'screen_pass':all(screen.values()),'confirmed':args.stage=='confirmation' and all(confirm.values())}
    # Guard against any model/checkpoint mutation during the audit.
    release_guard(evidence,args.stage)
    result={'passed':True,'run_id':run.name,'stage':args.stage,'released_cases':ids,'native_paths':len(ids),'numeric_and_field_checks':checks,
        'max_compared_scalar_error':max_error,'quarter_bootstrap_draws':DRAWS,'quarter_universe':quarters,'native_source_sha256':native_hashes,
        'score_release_sha256':sha(evidence/'score_release.json'),'evidence_directory':str(evidence),'scorer_sha256':json.loads((out/'scoring_audit.json').read_text())['source_code_sha256'],'auditor_sha256':sha(Path(__file__)),
        'unused_confirmation_targets_scored':False,'new_model_calls':0,'directions':point_results}
    (HERE/f'{args.stage}_replay_audit.json').write_text(json.dumps(clean(result),indent=2,allow_nan=False)+'\n')
    frame.to_csv(HERE/f'{args.stage}_independent_native_trades.csv',index=False)
    print(json.dumps(clean(result),indent=2),flush=True)

if __name__=='__main__':main()
