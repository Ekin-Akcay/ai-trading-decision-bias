"""Independent 500-window S508 audit, gated until root explicitly unseals outcomes.

Do not invoke with --release until root authorizes it. No fresh price file is
read before exact release, ALLOW_EVALUATION, and 500 accepted-decision gates.
"""
from pathlib import Path
import argparse,json,hashlib,sys
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;STUDY=H.parent;ROOT=H.parents[3]
EXPECTED_RUN='gross-edge-500-20260929T204545Z'
sys.path.insert(0,str(ROOT/'data/analysis/reversal-deep-20260929/risk'))
from validation_engine import bracket_batch


def native_scalar(px,t0,stop_percent,sign=-1,delay=0,horizon=240):
    """Independent time-indexed scalar 1:1 bracket, percentage-point stop input."""
    step=pd.Timedelta(minutes=1)
    entry=float(px.loc[t0+step*delay,'open']) if delay else float(px.loc[t0-step,'close'])
    stop=entry*(1-sign*stop_percent/100)
    target=entry*(1+sign*stop_percent/100)
    for minute in range(delay,horizon):
        r=px.loc[t0+step*minute]
        op,hi,lo=float(r['open']),float(r['high']),float(r['low'])
        open_stop=(op<=stop) if sign>0 else (op>=stop)
        open_target=(op>=target) if sign>0 else (op<=target)
        touch_stop=(lo<=stop) if sign>0 else (hi>=stop)
        touch_target=(hi>=target) if sign>0 else (lo<=target)
        if open_stop:outcome,exit_px,ambiguous,gap='sl_gap',op,False,True
        elif open_target:outcome,exit_px,ambiguous,gap='tp_gap_capped',target,False,True
        elif touch_stop:outcome,exit_px,ambiguous,gap=('sl_ambiguous' if touch_target else 'sl'),stop,touch_target,False
        elif touch_target:outcome,exit_px,ambiguous,gap='tp',target,False,False
        else:continue
        return {'gross_pct':sign*(exit_px/entry-1)*100,'entry_price':entry,'exit_price':exit_px,'outcome':outcome,'held_minutes':minute-delay+1,'exit_index':minute+1,'ambiguous':ambiguous,'gap':gap}
    exit_px=float(px.loc[t0+step*(horizon-1),'close'])
    return {'gross_pct':sign*(exit_px/entry-1)*100,'entry_price':entry,'exit_price':exit_px,'outcome':'timeout','held_minutes':horizon-delay,'exit_index':horizon,'ambiguous':False,'gap':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release',required=True,help='Exact run ID, supplied only after root explicitly unseals outcomes')
    args=parser.parse_args()
    if args.release!=EXPECTED_RUN:raise SystemExit('Explicit root release for this exact run is required')
    config=json.loads((STUDY/'run.json').read_text());run=Path(config['run_dir'])
    if config['run_id']!=EXPECTED_RUN or not (run/'ALLOW_EVALUATION').is_file():raise SystemExit('Fresh outcomes remain sealed')
    accepted=[json.loads(s) for s in (run/'accepted_decisions.jsonl').read_text().splitlines()]
    accepted.sort(key=lambda r:r['case'])
    if len(accepted)!=500 or [r['case'] for r in accepted]!=list(range(1,501)):
        raise SystemExit('Require 500 unique accepted decisions before any fresh outcome read')
    isolation=json.loads((run/'isolation_audit.json').read_text())
    assert isolation['accepted']==500 and isolation['all_accepted_passed']
    # All gates have passed. Read manifest, scored outputs and native prices now.
    m=json.loads((run/'manifest.json').read_text());assert m['run_id']==EXPECTED_RUN and m['planned_decisions']==500
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(ROOT/m['protocol_file'])==m['protocol_sha256']
    cases=sorted(m['cases'],key=lambda r:r['case']);assert [r['case'] for r in cases]==list(range(1,501))
    decisions={r['case']:r['decision'] for r in accepted}
    ledger=[json.loads(s) for s in (run/'strategy_trades.jsonl').read_text().splitlines()]
    roots={r['case']:r for r in ledger if r['rule']=='S508'};assert len(roots)==500
    summary=json.loads((run/'summary.json').read_text())['rules']['S508']
    frame=pd.DataFrame(cases).sort_values('case').reset_index(drop=True)
    frame['entry_time']=pd.to_datetime(frame.entry_time)
    frame['action']=[decisions[c]['action'] for c in frame.case]
    eligible=((frame.ma20_now<=100)&(frame.ma50_now<=100)).to_numpy()
    selected=eligible&frame.action.eq('long').to_numpy()
    values={key:np.zeros(500) for key in ['primary','delay1','delay5','mirrored']}
    comparisons=0;replays=0;feature_checks=0;max_error=0.;geometry_counts={};history_coverage=0
    def equal(a,b,label):
        nonlocal comparisons,max_error
        if isinstance(a,(int,float,np.integer,np.floating)) and not isinstance(a,(bool,np.bool_)):
            error=abs(float(a)-float(b));assert error<1e-8,(label,a,b);max_error=max(max_error,error)
        else:assert a==b,(label,a,b)
        comparisons+=1
    for asset in sorted(frame.asset.unique()):
        px=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_1m.csv.gz',index_col=0,parse_dates=True).sort_index();assert px.index.is_unique
        px15=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_15m.csv.gz',index_col=0,parse_dates=True).sort_index();assert px15.index.is_unique
        positions=np.flatnonzero(frame.asset.eq(asset).to_numpy());paths=[];stops=[]
        for i in positions:
            w=frame.iloc[i];t=w.entry_time
            equal(str(t),str(pd.Timestamp(w.window_end_ts)+pd.Timedelta(minutes=15)),('original_clock',int(w.case)))
            labels=pd.date_range(t-pd.Timedelta(minutes=1),periods=361,freq='min');part=px.loc[labels,['open','high','low','close']]
            assert part.index.equals(labels) and np.isfinite(part.to_numpy()).all() and (part.to_numpy()>0).all()
            paths.append(part.to_numpy(float));equal(float(part.iloc[0]['close']),w.price_real,('visible_close',int(w.case)))
            histlabels=pd.date_range(t-pd.Timedelta(minutes=15*200),periods=200,freq='15min');hist=px15.loc[histlabels,['open','high','low','close']]
            assert hist.index.equals(histlabels) and np.isfinite(hist.to_numpy()).all() and (hist.to_numpy()>0).all();history_coverage+=1
            cl=hist.close.to_numpy();hi=hist.high.to_numpy();lo=hist.low.to_numpy();previous=np.r_[np.nan,cl[:-1]]
            tr=np.maximum(hi-lo,np.maximum(np.abs(hi-previous),np.abs(lo-previous)));atr=np.mean(tr[-14:])/cl[-1]*100
            equal(atr,w.atr14_pct,('ATR14',int(w.case)));equal(cl[-20:].mean()/cl[-1]*100,w.ma20_now,('MA20',int(w.case)));equal(cl[-50:].mean()/cl[-1]*100,w.ma50_now,('MA50',int(w.case)));feature_checks+=3
            stops.append(2*w.atr14_pct)
        paths=np.array(paths);stops=np.array(stops)
        for label,sign,delay in [('primary',-1,0),('delay1',-1,1),('delay5',-1,5),('mirrored',1,0)]:
            engine=bracket_batch(paths,stops,sign=sign,rr=1,horizon=240,delay=delay)
            for local,i in enumerate(positions):
                w=frame.iloc[i];t=w.entry_time;case=int(w.case);root=roots[case]
                ref=native_scalar(px,t,stops[local],sign,delay);replays+=1
                for field,value in ref.items():equal(value,engine[field][local],(label,case,field,'engine'))
                values[label][i]=ref['gross_pct']
                if label=='primary':
                    for field in ['gross_pct','entry_price','exit_price','outcome','held_minutes','ambiguous','gap']:equal(ref[field],root[field],('primary',case,field,'root'))
                    equal(ref['exit_index'],root['exit_minute_index'],('primary',case,'exit_minute_index'))
                    equal(ref['gross_pct'],root['net_at_zero_cost_pct'],('primary',case,'zero_cost'))
                    equal(bool(eligible[i]),root['eligible'],('primary',case,'eligible'));equal(bool(selected[i]),root['selected'],('primary',case,'selected'))
                    equal(str(t),root['entry_time'],('primary',case,'entry_time'))
                    equal(w.asset,root['asset'],('primary',case,'asset'));equal(decisions[case]['action'],root['AI_action'],('primary',case,'AI_action'))
                    end=ref['exit_index'];ext=paths[local,1:end+1];entry=ref['entry_price']
                    mfe=max(0.,(1-ext[:,2].min()/entry)*100);mae=min(0.,(1-ext[:,1].max()/entry)*100)
                    equal(mfe,root['mfe_through_exit_bar_pct'],('primary',case,'MFE'));equal(mae,root['mae_through_exit_bar_pct'],('primary',case,'MAE'))
                    for h in [15,30,60,105,240]:equal(-(float(px.loc[t+pd.Timedelta(minutes=h-1),'close'])/entry-1)*100,root[f'scheduled_direction_move_{h}m_pct'],('primary',case,h,'scheduled_move'))
                    geometry_counts[ref['outcome']]=geometry_counts.get(ref['outcome'],0)+1
                elif label.startswith('delay'):equal(ref['gross_pct'],root['entry_'+label+'_gross_pct'],(label,case,'root_gross'))
        print('Verified native S508 paths for',asset,'windows',len(positions),flush=True)
    def summary_check(x,target,label):
        x=np.asarray(x);n=len(x);equal(n,target['n'],(label,'n'))
        if not n:return
        z=np.sort(x);measure={'mean_gross_pct':x.mean(),'median_gross_pct':np.median(x),'gross_sum_pct':x.sum(),'wins':int((x>0).sum()),'win_rate':(x>0).mean(),'best_pct':x.max(),'worst_pct':x.min(),'exclude_best1_mean_pct':z[:-1].mean() if n>1 else None,'exclude_best3_mean_pct':z[:-3].mean() if n>3 else None,'break_even_roundtrip_bps':x.mean()*100,'mean_winner_pct':x[x>0].mean() if (x>0).any() else None,'mean_loser_pct':x[x<0].mean() if (x<0).any() else None,'profit_factor':x[x>0].sum()/-x[x<0].sum() if (x<0).any() else None}
        for field,value in measure.items():equal(value,target[field],(label,field))
    summary_check(values['primary'][selected],summary['selected'],'selected')
    summary_check(values['primary'][eligible],summary['eligible_price_only'],'price_only')
    summary_check(values['primary'][eligible&~selected],summary['complementary_AI_group'],'complementary')
    for delay in [1,5]:summary_check(values['delay'+str(delay)][selected],summary['delay_sensitivities'][str(delay)],'delay'+str(delay))
    summary_check(values['mirrored'][selected],summary['same_selected_AI_direction'],'mirrored')
    equal(np.unique(frame.loc[selected,'block']).size,summary['selected_blocks'],'selected_blocks')
    equal(np.where(selected,values['primary'],0).mean(),summary['opportunity_mean_gross_pct'],'opportunity_mean')
    for asset in frame.asset.unique():
        am=frame.asset.eq(asset).to_numpy();summary_check(values['primary'][selected&am],summary['assets'][asset],'asset/'+asset);summary_check(values['primary'][selected&~am],summary['leave_one_asset_out'][asset],'leave/'+asset)
    chronological=frame[['block','entry_time']].drop_duplicates().sort_values('entry_time').block.to_numpy()
    for splits,key in [(2,'chronological_halves'),(3,'chronological_thirds')]:
        for j,part in enumerate(np.array_split(chronological,splits)):summary_check(values['primary'][selected&frame.block.isin(part).to_numpy()],summary[key][j],key+'/'+str(j))
    # Independently reproduce the observed standardized price-only mean. Root's
    # block/quarter bootstrap inference is reviewed separately by the design worker.
    regime=np.where((frame.ma20_now<=100)&(frame.ma50_now<=100),'above_both',np.where((frame.ma20_now>=100)&(frame.ma50_now>=100),'below_both','mixed'))
    era=np.where(frame.entry_time.dt.year<=2021,'2020-21',np.where(frame.entry_time.dt.year<=2023,'2022-23','2024-26'))
    strata=np.array([str(a)+'|'+str(e)+'|'+str(r) for a,e,r in zip(frame.asset,era,regime)])
    weighted=0.
    for st in set(strata):
        here=strata==st;count=int((selected&here).sum())
        if count:weighted+=count*values['primary'][eligible&here].mean()
    baseline=weighted/selected.sum() if selected.any() else np.nan
    for key in ['block_inference','quarter_inference']:
        equal(baseline,summary[key]['standardized_price_baseline_mean_pct'],(key,'baseline'))
        equal(values['primary'][selected].mean()-baseline,summary[key]['AI_increment_mean_pct'],(key,'AI_increment'))
    assert all(digest(ROOT/p)==h for p,h in m['original_sha256'].items())
    result={'passed':True,'run_id':EXPECTED_RUN,'release_explicit':args.release,'evaluation_marker_checked':True,'accepted_decisions':500,'assets':sorted(frame.asset.unique()),'calendar_blocks':int(frame.block.nunique()),'S508_selected':int(selected.sum()),'S508_eligible':int(eligible.sum()),'native_scalar_replays':replays,'field_comparisons':comparisons,'maximum_numeric_error':max_error,'full_minute_paths_checked':500,'minute_bars_per_path':361,'pre_entry_200bar_history_checks':history_coverage,'ATR_MA_checks':feature_checks,'primary_all_window_outcomes':geometry_counts,'MFE_MAE_include_entry':True,'gross_equals_zero_cost_net':True,'delayed_stops_recentered':True,'mirrored_brackets_independently_replayed':True,'original_files_preserved':True,'strategy_ledger_sha256':digest(run/'strategy_trades.jsonl'),'accepted_decisions_sha256':digest(run/'accepted_decisions.jsonl'),'checker_sha256':digest(Path(__file__))}
    (H/'independent_S508_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
