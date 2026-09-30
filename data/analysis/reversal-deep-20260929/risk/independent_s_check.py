"""Independent fresh-S check; DO NOT run until root explicitly releases evaluation.

Three gates precede all fresh outcome reads: exact --release RUN_ID authorization,
ALLOW_EVALUATION marker, and 280 unique accepted decisions. Uses a separate scalar
native-minute implementation, then compares the vector engine and root outputs.
"""
from pathlib import Path
import argparse,json,hashlib,sys
import numpy as np
import pandas as pd
from validation_engine import bracket_batch
H=Path(__file__).resolve().parent
ROOT=H.parents[3]
EXPECTED_RUN='reversal-validation280-20260929T194012Z'


def scalar_native(px, t0, stop, sign=-1, rr=2.0, delay=0, horizon=240):
    """Clock-indexed scalar replay; independent of the vector engine implementation."""
    one=pd.Timedelta(minutes=1)
    entry=float(px.loc[t0+one*delay,'open']) if delay else float(px.loc[t0-one,'close'])
    stop_price=entry*(1-sign*stop/100)
    target_price=entry*(1+sign*stop*rr/100)
    for minute in range(delay,horizon):
        row=px.loc[t0+one*minute]
        o,hi,lo=float(row['open']),float(row['high']),float(row['low'])
        stop_open=o<=stop_price if sign>0 else o>=stop_price
        target_open=o>=target_price if sign>0 else o<=target_price
        stop_hit=lo<=stop_price if sign>0 else hi>=stop_price
        target_hit=hi>=target_price if sign>0 else lo<=target_price
        if stop_open:code,exit_price,ambiguity,gap='sl_gap',o,False,True
        elif target_open:code,exit_price,ambiguity,gap='tp_gap_capped',target_price,False,True
        elif stop_hit:code,exit_price,ambiguity,gap=('sl_ambiguous' if target_hit else 'sl'),stop_price,target_hit,False
        elif target_hit:code,exit_price,ambiguity,gap='tp',target_price,False,False
        else:continue
        return {'gross_pct':sign*(exit_price/entry-1)*100,'entry_price':entry,'exit_price':exit_price,'outcome':code,'held_minutes':minute-delay+1,'exit_index':minute+1,'ambiguous':ambiguity,'gap':gap}
    exit_price=float(px.loc[t0+one*(horizon-1),'close'])
    return {'gross_pct':sign*(exit_price/entry-1)*100,'entry_price':entry,'exit_price':exit_price,'outcome':'timeout','held_minutes':horizon-delay,'exit_index':horizon,'ambiguous':False,'gap':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release',required=True,help='Root must explicitly supply exact run ID after collection/evaluation release')
    args=parser.parse_args()
    if args.release!=EXPECTED_RUN:raise SystemExit('No root release for this exact run: fresh outcomes remain sealed')
    run=ROOT/'data/sim'/EXPECTED_RUN
    if not (run/'ALLOW_EVALUATION').is_file():raise SystemExit('ALLOW_EVALUATION absent; fresh outcomes remain sealed')
    records=[json.loads(s) for s in (run/'accepted_decisions.jsonl').read_text().splitlines()]
    records.sort(key=lambda x:x['case'])
    if len(records)!=280 or [r['case'] for r in records]!=list(range(1,281)):
        raise SystemExit('Require all 280 unique accepted decisions before fresh outcome reads')
    # Only after all gates: read fresh manifest and native outcomes/root scored outputs.
    manifest=json.loads((run/'manifest.json').read_text())
    assert manifest['run_id']==EXPECTED_RUN
    assert [w['case'] for w in manifest['cases']]==list(range(1,281))
    root_rows=[json.loads(s) for s in (run/'window_results.jsonl').read_text().splitlines()]
    assert len(root_rows)==280 and [r['case'] for r in root_rows]==list(range(1,281))
    summary=json.loads((run/'summary.json').read_text())
    root_trades=[json.loads(s) for s in (run/'strategy_trades.jsonl').read_text().splitlines()]
    root_short={r['case']:r for r in root_trades if r['strategy']=='S'}
    raw=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index()
    assert raw.index.is_unique
    paths=[];times=[];stops=[];atrs=[];islong=[];ma20=[]
    for w,r in zip(manifest['cases'],records):
        t=pd.Timestamp(w['entry_time'])
        assert t==pd.Timestamp(w['window_end_ts'])+pd.Timedelta(minutes=15)
        labels=pd.date_range(t-pd.Timedelta(minutes=1),periods=241,freq='min')
        slab=raw.loc[labels,['open','high','low','close']]
        assert slab.index.equals(labels) and len(slab)==241
        assert abs(float(slab.iloc[0]['close'])-w['price_real'])<1e-8
        paths.append(slab.to_numpy(float));times.append(t)
        stops.append(r['decision']['stop_pct']*100*1.5)
        atrs.append(w['atr14_pct']);islong.append(r['decision']['action']=='long');ma20.append(w['ma20_now'])
    paths=np.array(paths);stops=np.array(stops);atrs=np.array(atrs);islong=np.array(islong);ma20=np.array(ma20)
    configurations=[('S',stops,-1,2,0),('S_delay1',stops,-1,2,1),('S_delay5',stops,-1,2,5),('follow',stops,1,2,0),('ATR2_RR2',2*atrs,-1,2,0),('ATR2_RR1',2*atrs,-1,1,0)]
    checks=0;max_error=0.;payoffs={};primary_native=[]
    def equal(a,b,label):
        nonlocal checks,max_error
        if isinstance(a,(int,float,np.integer,np.floating)) and not isinstance(a,(bool,np.bool_)):
            delta=abs(float(a)-float(b));max_error=max(max_error,delta)
            assert delta<1e-8,(label,a,b)
        else:assert a==b,(label,a,b)
        checks+=1
    root_fields={'S':'S_gross_pct','S_delay1':'S_delay1_gross_pct','S_delay5':'S_delay5_gross_pct','ATR2_RR2':'S_ATR2_RR2_gross_pct','ATR2_RR1':'S_ATR2_RR1_gross_pct'}
    for name,width,sign,rr,delay in configurations:
        vector=bracket_batch(paths,width,sign=sign,rr=rr,horizon=240,delay=delay)
        numbers=[]
        for i,t in enumerate(times):
            native=scalar_native(raw,t,width[i],sign,rr,delay)
            for field,value in native.items():equal(value,vector[field][i],(name,i+1,field,'engine'))
            numbers.append(native['gross_pct'])
            if name in root_fields:equal(native['gross_pct'],root_rows[i][root_fields[name]],(name,i+1,'root_gross'))
            if name=='S':
                primary_native.append(native)
                for field,rfield in [('entry_price','S_entry_price'),('exit_price','S_exit_price'),('outcome','S_outcome'),('held_minutes','S_held_minutes')]:equal(native[field],root_rows[i][rfield],('S',i+1,rfield))
                equal(bool(islong[i]),root_rows[i]['S_selected'],('S',i+1,'selection'))
                equal(stops[i],root_rows[i]['S_stop_percent'],('S',i+1,'stop_percent'))
                equal(2*stops[i],root_rows[i]['S_target_percent'],('S',i+1,'target_percent'))
                equal(native['gross_pct']-.2,root_rows[i]['S_net_pct'],('S',i+1,'net'))
                if islong[i]:
                    rt=root_short[i+1]
                    for field in ['entry_price','exit_price','gross_pct','outcome']:equal(native[field],rt[field],('S',i+1,'trade_'+field))
                    equal(str(t),rt['entry_time'],('S',i+1,'entry_time'))
                    equal(str(t+pd.Timedelta(minutes=native['exit_index'])),rt['exit_minute_close_time'],('S',i+1,'exit_close_bound'))
                    equal(native['held_minutes'],rt['minutes_held'],('S',i+1,'minutes_held'))
        payoffs[name]=np.array(numbers)
    assert len(root_short)==int(islong.sum())
    def stats_check(values,mask,target,label):
        x=values[mask];net=x-.2
        stats={'n':len(x),'gross_positive':int((x>0).sum()),'net_positive':int((net>0).sum()),'mean_gross_pct':x.mean(),'mean_net_pct':net.mean(),'mean_net_per_opportunity_pct':net.sum()/280,'gross_win_rate':(x>0).mean(),'net_win_rate':(net>0).mean(),'median_gross_pct':np.median(x),'median_net_pct':np.median(net),'worst_gross_pct':x.min(),'best_gross_pct':x.max(),'mean_net_at30bps_pct':x.mean()-.3,'break_even_roundtrip_bps':x.mean()*100}
        for k,v in stats.items():equal(v,target[k],(label,k))
    stats_check(payoffs['S'],islong,summary['strategies']['S'],'primary_summary')
    for delay in [1,5]:stats_check(payoffs['S_delay'+str(delay)],islong,summary['strategies']['S']['entry_delay_sensitivity'][str(delay)],'delay'+str(delay)+'_summary')
    allmask=np.ones(280,bool)
    controls=[('S_all_windows_AI_width_not_AI_free','S',allmask),('S_price_only_ATR2_RR2_all','ATR2_RR2',allmask),('S_price_only_ATR2_RR2_above_MA20','ATR2_RR2',ma20<=100),('S_follow_AI_long_same_geometry','follow',islong),('diagnostic_S_ATR2_RR1_AI_selected','ATR2_RR1',islong),('diagnostic_S_ATR2_RR1_all','ATR2_RR1',allmask)]
    for label,key,mask in controls:stats_check(payoffs[key],mask,summary['controls'][label],label)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result={'passed':True,'run_id':EXPECTED_RUN,'release_explicit':args.release,'evaluation_marker_checked':True,'accepted_decisions':280,'native_scalar_replays':280*len(configurations),'comparison_checks':checks,'maximum_numeric_error':max_error,'short_trades':int(islong.sum()),'full_minute_paths_checked':280,'gross_net_cost_pp':.2,'control_configurations_checked':len(controls),'primary_and_delay_configs_checked':3,'clock_and_geometry_verified':True,'window_results_sha256':digest(run/'window_results.jsonl'),'accepted_decisions_sha256':digest(run/'accepted_decisions.jsonl'),'engine_sha256':digest(H/'validation_engine.py'),'checker_sha256':digest(Path(__file__))}
    (H/'independent_S_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
