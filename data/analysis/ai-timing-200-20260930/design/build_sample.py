"""Conditional sampling using only pre-entry features and coverage, never payoffs."""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import sys
from datetime import datetime, timezone
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'src'))
from nai.sim import build_snapshot, window_id
ASSETS=['SOL-USD','BTC-USD','ETH-USD','DOGE-USD']
SEED=2026093017
MINUTE=60*10**9
HOUR=60*MINUTE
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
iso=lambda n:pd.Timestamp(int(n),tz='UTC').isoformat().replace('+00:00','Z')

def save(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def bad_ohlc(values,volume=False):
    o,h,l,c=values[:,:4].T
    bad=(~np.isfinite(values)).any(axis=1)|(values[:,:4]<=0).any(axis=1)
    bad|=(h<np.maximum.reduce([o,l,c]))|(l>np.minimum.reduce([o,h,c]))
    if volume:bad|=values[:,4]<0
    return bad

def exclusions():
    ma_path=ROOT/'data/analysis/gross-edge-20260929/ma_ablation/design/fresh_blocks.json'
    proxy_path=ROOT/'data/analysis/new-angles-20260930/proxy_replication/frozen_sample.json'
    ma=json.loads(ma_path.read_text());proxy=json.loads(proxy_path.read_text())
    prior={pd.Timestamp(x['entry_time']).value:(float(x['history_hours']),float(x['outcome_hours'])) for x in ma['prior_exposure_intervals']}
    assert len(prior)==591
    for row in ma['blocks']:
        prior[pd.Timestamp(row['entry_time']).value]=(50.,6.)
    assert len(prior)==681
    proxy_prior={pd.Timestamp(x['entry_time']).value:(float(x['history_hours']),float(x['outcome_hours'])) for x in proxy['prior_exposure_intervals']}
    assert prior==proxy_prior
    intervals=[{'kind':'old_snapshot_history_and_outcome','start_ns':int(t-h*HOUR),'end_ns':int(t+f*HOUR),'original_t0_ns':int(t)} for t,(h,f) in sorted(prior.items())]
    assert len(proxy['entry_times'])==783
    intervals += [{'kind':'proxy_target','start_ns':int(pd.Timestamp(t).value),'end_ns':int(pd.Timestamp(t).value+4*HOUR)} for t in proxy['entry_times']]
    merged=[]
    for row in sorted(intervals,key=lambda r:r['start_ns']):
        a,b=row['start_ns'],row['end_ns']
        if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],b)
        else:merged.append([a,b])
    return intervals,np.array(merged,dtype=np.int64),set(prior),[ma_path,proxy_path]

def selection(pool,extended=True):
    """Fixed scarce-stratum greedy allocation with stage-specific year balance."""
    rng=np.random.default_rng(SEED)
    pool=pool.sort_values(['t0','asset']).reset_index(drop=True).copy()
    pool['random_priority']=rng.random(len(pool))
    used_days=set();chosen=[];stage_summaries={};blocked=np.zeros(len(pool),dtype=bool)
    # Exact asset totals:15 each screen,30 each confirmation; rounding is
    # opposite across directions in screen and exact in confirmation.
    quotas={'screen':{'up':[8,8,7,7],'down':[7,7,8,8]},
            'confirmation_core':{'up':[15]*4,'down':[15]*4}}
    if extended:quotas['confirmation_extension']={'up':[15]*4,'down':[15]*4}
    for tier in quotas:
        stage='screen' if tier=='screen' else 'confirmation'
        remaining={(direction,asset):quotas[tier][direction][i] for direction in ['up','down'] for i,asset in enumerate(ASSETS)}
        years={int(y):0 for y in sorted(pool.year.unique())}
        picked=[]
        while sum(remaining.values()):
            available=pool.loc[~blocked]
            candidates=[]
            for (direction,asset),needed in remaining.items():
                if not needed:continue
                sub=available[available.direction.eq(direction)&available.asset.eq(asset)]
                daycount=sub.utc_day.nunique()
                if not daycount:
                    return pool,pd.DataFrame(chosen+picked),{'success':False,'tier':tier,'unfilled':{f'{d}:{a}':n for (d,a),n in remaining.items() if n},'completed_tiers':stage_summaries}
                # Prioritize the least available calendar days per outstanding slot.
                candidates.append((daycount/needed,direction,asset,sub))
            _,direction,asset,sub=min(candidates,key=lambda z:z[:3])
            sub=sub.assign(year_used=sub.year.map(years))
            row=sub.sort_values(['year_used','random_priority','t0','asset']).iloc[0].to_dict()
            row['stage']=stage;row['selection_tier']=tier;picked.append(row);used_days.add(row['utc_day']);years[int(row['year'])]+=1;remaining[(direction,asset)]-=1
            blocked |= pool.utc_day.eq(row['utc_day']).to_numpy() | (np.abs(pool.t0_ns.to_numpy()-row['t0_ns'])<120*MINUTE)
        # Random priority orders each frozen stage; it does not affect inclusion.
        picked=sorted(picked,key=lambda r:r['random_priority'])
        chosen.extend(picked)
        stage_summaries[tier]={'count':len(picked),'years':{str(k):v for k,v in years.items()},'direction_asset_quota':quotas[tier]}
    return pool,pd.DataFrame(chosen),{'success':True,'stages':stage_summaries,'unique_UTC_days':len(used_days)}

def main(freeze=False):
    assert not (HERE/'fresh_windows.json').exists(),'Sample already frozen'
    intervals,merged,old_t0,sourcefiles=exclusions()
    sourcefiles += [HERE/'PLAN.md',Path(__file__),ROOT/'src/nai/sim.py']
    basepath=ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz'
    baseidx=pd.read_csv(basepath,usecols=[0],index_col=0,parse_dates=True).index
    ns=(baseidx+pd.Timedelta(minutes=15)).as_unit('ns').asi8
    ns=ns[ns%(30*MINUTE)==0]
    # Target interval starts after the complete30m pre-entry gate.
    entry=ns+30*MINUTE;end=ns+150*MINUTE
    ix=np.searchsorted(merged[:,0],end,side='left')-1
    calendar=(ix<0)|(merged[np.maximum(ix,0),1]<=entry)
    calendar &= ~np.isin(ns,np.array(sorted(old_t0),dtype=np.int64))
    allrows=[];counts={};hashes={str(p.relative_to(ROOT)):sha(p) for p in sourcefiles}
    for asset in ASSETS:
        p15=ROOT/f'data/raw/intraday/{asset}_15m.csv.gz';p1=ROOT/f'data/raw/intraday/{asset}_1m.csv.gz'
        for p in [p15,p1]:hashes[str(p.relative_to(ROOT))]=sha(p)
        bars=pd.read_csv(p15,index_col=0,parse_dates=True).sort_index()
        minute=pd.read_csv(p1,index_col=0,parse_dates=True).sort_index()
        assert bars.index.is_unique and minute.index.is_unique
        bns=bars.index.as_unit('ns').asi8;mns=minute.index.as_unit('ns').asi8
        bp=np.searchsorted(bns,ns-15*MINUTE);bsafe=np.clip(bp,0,len(bars)-1)
        hist=(bp>=200)&(bp<len(bars))&(bns[bsafe]==ns-15*MINUTE)
        bbad=bad_ohlc(bars[['open','high','low','close','volume']].to_numpy(float),True)
        pref=np.r_[0,np.cumsum(bbad)];gaps=np.r_[0,np.cumsum(np.r_[False,np.diff(bns)!=15*MINUTE])];first=np.maximum(bsafe-199,0)
        hist &= (pref[bsafe+1]-pref[first]==0)&(gaps[bsafe+1]-gaps[first+1]==0)
        mp=np.searchsorted(mns,ns);msafe=np.clip(mp,3000,len(minute)-150)
        # Baseline has3000 complete minute volumes; only validity is inspected
        # in future minute OHLC. Future prices are never emitted or scored.
        coverage=(mp>=3000)&(mp+150<=len(minute))&(mns[msafe]==ns)
        start=msafe-3000;stop=msafe+150
        gaps=np.r_[0,np.cumsum(np.r_[False,np.diff(mns)!=MINUTE])]
        coverage &= (gaps[stop]-gaps[start+1]==0)
        v=minute.volume.to_numpy(float)
        vbad=~np.isfinite(v)|(v<0);vp=np.r_[0,np.cumsum(vbad)]
        coverage &= (vp[msafe+30]-vp[start]==0)
        mbad=bad_ohlc(minute[['open','high','low','close']].to_numpy(float));op=np.r_[0,np.cumsum(mbad)]
        coverage &= (op[stop]-op[msafe-1]==0)
        prior_close=minute.close.to_numpy(float)[msafe-1]
        coverage &= np.isclose(prior_close,bars.close.to_numpy(float)[bsafe],rtol=0,atol=1e-8)
        # ATR is exactly the last14 true ranges used by original build_snapshot.
        close=bars.close
        tr=np.maximum(bars.high-bars.low,np.maximum((bars.high-close.shift()).abs(),(bars.low-close.shift()).abs()))
        atr=(tr.rolling(14).mean()/close*100).to_numpy(float)[bsafe]
        # Resampling at UTC00/30 produces the100 preceding nonoverlapping bins.
        vol30=minute.volume.resample('30min').sum(min_count=30)
        baseline=vol30.rolling(100,min_periods=100).median().shift(1)
        lookup=vol30.index.get_indexer(pd.DatetimeIndex(ns));safe=np.maximum(lookup,0)
        num=vol30.to_numpy(float)[safe];den=baseline.to_numpy(float)[safe]
        valid=calendar&hist&coverage&(lookup>=0)&np.isfinite(atr)&(atr>0)&np.isfinite(den)&(den>0)&np.isfinite(num)
        ids=np.flatnonzero(valid)
        # Only the gate's last close is accessed for economic conditioning.
        firstopen=minute.open.to_numpy(float)[msafe[ids]]
        lastclose=minute.close.to_numpy(float)[msafe[ids]+29]
        moves=100*(lastclose/firstopen-1)
        ratios=num[ids]/den[ids]
        gate=(np.abs(moves)>=.5*atr[ids])&(ratios<=.75)
        chosen=ids[gate];mov=moves[gate];rat=ratios[gate]
        for j,m,r in zip(chosen,mov,rat):
            t=int(ns[j]);dt=pd.Timestamp(t)
            allrows.append({'asset':asset,'window_id':window_id(asset,pd.Timestamp(t-15*MINUTE)),
                'window_end_ts':str(pd.Timestamp(t-15*MINUTE)),'t0':iso(t),'entry_time':iso(t+30*MINUTE),'horizon_end':iso(t+150*MINUTE),
                't0_ns':t,'utc_day':str(dt.date()),'year':int(dt.year),'quarter':str(dt.to_period('Q')),
                'direction':'up' if m>0 else 'down','atr14_pct':float(atr[j]),'gate_move_pct':float(m),
                'gate_move_atr':float(m/atr[j]),'gate_volume_ratio':float(r),'gate_volume':float(num[j]),'baseline_volume_median':float(den[j]),
                'visible_bars':40,'history15m_bars':200,'baseline_volume_minutes':3000,'gate_minutes':30,'trade_minutes':120})
        counts[asset]={'grid':len(ns),'calendar_pass':int(calendar.sum()),'history_pass':int(hist.sum()),'minute_coverage_pass':int(coverage.sum()),
            'all_coverage_and_exclusions':len(ids),'quiet_candidates':len(chosen),'up':int((mov>0).sum()),'down':int((mov<0).sum())}
        print(asset,counts[asset],flush=True)
        del bars,minute,bns,mns,mbad,v,vbad,vp,op,tr,close,vol30,baseline
        gc.collect()
    pool=pd.DataFrame(allrows)
    pool,selected,allocation=selection(pool,extended=True)
    extension_attempt=allocation.copy()
    if not allocation['success']:
        pool,selected,allocation=selection(pool,extended=False)
    allocation['extension_attempt']=extension_attempt
    pool.to_csv(HERE/'candidate_metadata.csv',index=False)
    selected.to_csv(HERE/'draft_selected_sample.csv',index=False)
    interval_records=[{k:v for k,v in r.items()} for r in intervals]
    save('exclusion_intervals.json',{'half_open':True,'old_exposures':681,'proxy_targets':783,'intervals':interval_records,'merged_intervals_ns':merged.tolist()})
    feasibility={'candidate_rows':len(pool),'unique_t0':pool.t0.nunique(),'unique_UTC_days':pool.utc_day.nunique(),
        'direction_counts':{str(k):int(v) for k,v in pool.direction.value_counts().items()},
        'direction_unique_days':{d:int(pool.loc[pool.direction.eq(d),'utc_day'].nunique()) for d in ['up','down']},
        'year_direction_counts':pool.groupby(['year','direction']).size().unstack(fill_value=0).to_dict(),
        'asset_counts':counts,'draft_allocation':allocation,'draft_rows':len(selected),
        'post_entry_returns_computed':False,'post_entry_prices_exported':False,'model_calls':0,'source_sha256':hashes}
    # Python ints required for JSON dictionary keys/counts.
    feasibility['year_direction_counts']={d:{str(y):int(n) for y,n in v.items()} for d,v in feasibility['year_direction_counts'].items()}
    save('FEASIBILITY.json',feasibility)
    print(json.dumps({k:v for k,v in feasibility.items() if k not in ['source_sha256','asset_counts']},indent=2),flush=True)
    if not freeze:return
    assert allocation['success'] and len(selected) in [180,300],'Capacity insufficient; sample not frozen'
    potential=len(selected)
    assert selected.utc_day.nunique()==potential
    selected=selected.reset_index(drop=True)
    selected['case_id']=np.arange(1,potential+1)
    selected['volume_ratio']=selected.gate_volume_ratio
    selected['confirmation_rank']=0
    for direction in ['up','down']:
        mask=selected.stage.eq('confirmation')&selected.direction.eq(direction)
        selected.loc[mask,'confirmation_rank']=np.arange(1,mask.sum()+1)
    # Independently recheck every chosen native gate and snapshot feature.
    for asset in ASSETS:
        bars=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_15m.csv.gz',index_col=0,parse_dates=True).sort_index()
        minute=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_1m.csv.gz',index_col=0,parse_dates=True).sort_index()
        for _,row in selected[selected.asset.eq(asset)].iterrows():
            t=pd.Timestamp(int(row.t0_ns));mp=minute.index.get_loc(t)
            snap=build_snapshot(bars,t-pd.Timedelta(minutes=15),40,200)
            assert np.isclose(snap['atr14_pct'],row.atr14_pct,rtol=0,atol=1e-12)
            baseline=minute.volume.iloc[mp-3000:mp].to_numpy().reshape(100,30).sum(axis=1)
            ratio=minute.volume.iloc[mp:mp+30].sum()/np.median(baseline)
            assert np.isclose(ratio,row.gate_volume_ratio,rtol=1e-12,atol=1e-12)
            move=100*(minute.close.iloc[mp+29]/minute.open.iloc[mp]-1)
            assert abs(move)>=.5*snap['atr14_pct'] and ratio<=.75
            assert np.isclose(move,row.gate_move_pct,rtol=0,atol=1e-12)
            a=int(row.t0_ns)+30*MINUTE;b=int(row.t0_ns)+150*MINUTE
            for old in intervals:assert b<=old['start_ns'] or a>=old['end_ns']
        del bars,minute;gc.collect()
    for a,b in zip(np.sort(selected.t0_ns.to_numpy())[:-1],np.sort(selected.t0_ns.to_numpy())[1:]):assert b-a>=120*MINUTE
    assert all(sha(ROOT/p)==h for p,h in hashes.items())
    selected.to_csv(HERE/'selected_sample.csv',index=False)
    records=json.loads(selected.to_json(orient='records',double_precision=15))
    result={'study':'ai_timing_quiet_move_200_call_budget','seed':SEED,'created_at':datetime.now(timezone.utc).isoformat(),
        'potential_windows':potential,'maximum_valid_calls':180,'screen_windows':60,'maximum_confirmation_calls':120,'potential_confirmation_windows':potential-60,'physical_call_budget':200,'physical_retry_reserve':20,
        'older_remaining_credits_untouched':29,'stage_order':['screen','confirmation'],'cases':records,
        'continuation_allocation':'Both directions pass: first60 confirmation ranks each. One direction passes: all120 of that direction if extension available, otherwise its60. Neither passes: stop. No substitution or newly sampled windows.',
        'sampler':'scarce direction/asset stratum first, then least-represented stage year, then fixed random priority; one global UTC day',
        'allocation':allocation,'freshness':'specific future targets only; historical feature reuse permitted',
        'exclusions':{'old_global_history_and_outcome_intervals':681,'proxy_global_4h_targets':783},
        'no_post_entry_return_computation':True,'no_post_entry_price_export':True,'no_model_calls':True,
        'source_sha256':hashes,'candidate_metadata_sha256':sha(HERE/'candidate_metadata.csv'),
        'selected_sample_sha256':sha(HERE/'selected_sample.csv'),'exclusion_intervals_sha256':sha(HERE/'exclusion_intervals.json')}
    save('fresh_windows.json',result)
    save('sampling_audit.json',{'passed':True,'frozen_sample_sha256':sha(HERE/'fresh_windows.json'),'potential_windows':potential,'maximum_valid_calls':180,'unique_global_UTC_days':potential,
        'native_preentry_snapshot_and_volume_rechecks':potential,'direct_interval_comparisons':potential*len(intervals),'all_sources_unchanged':True,
        'post_entry_returns_computed':False,'post_entry_prices_exported':False,'model_calls':0})
    print('FROZEN',sha(HERE/'fresh_windows.json'),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true')
    main(parser.parse_args().freeze)
