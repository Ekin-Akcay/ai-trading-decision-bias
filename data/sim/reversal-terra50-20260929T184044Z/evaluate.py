"""Score the frozen 50-window protocol; no search or parameter optimization."""
from pathlib import Path
from datetime import datetime, timezone
import sys,json,hashlib
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
from nai.sim import SimResolver
M=json.loads((HERE/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(tuple,list,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.bool_,)):return bool(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x

def save(name,value):
    (HERE/name).write_text(json.dumps(clean(value),indent=2,allow_nan=False)+'\n')

def append_verified(path,rows):
    old=[json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    assert len(old)<=len(rows) and all(a==b for a,b in zip(old,rows)), 'Existing ledger differs'
    with path.open('a') as f:
        for r in rows[len(old):]:f.write(json.dumps(clean(r),allow_nan=False)+'\n')

def main():
    records=[json.loads(s) for s in (HERE/'accepted_decisions.jsonl').read_text().splitlines()]
    records.sort(key=lambda r:r['case'])
    assert len(records)==50 and [r['case'] for r in records]==list(range(1,51))
    audit=json.loads((HERE/'isolation_audit.json').read_text())
    assert audit['all_accepted_passed'] and len(audit['audits'])==50
    assert all(r['model']=='gpt-5.6-terra' and not r['tool_calls'] for r in records)
    assert sha(ROOT/M['protocol_file'])==M['protocol_sha256']
    assert all(sha(ROOT/p)==h for p,h in M['original_sha256'].items())
    resolver=SimResolver(['SOL-USD'],time_stop_hours=72)
    idx,o,hi,lo,c=resolver._d['SOL-USD']
    px15=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',index_col=0,parse_dates=True)
    rows=[];ledger=[]
    for r,w in zip(records,M['cases']):
        assert r['case']==w['case'] and max(w['ma20_now'],w['ma50_now'])<=100+1e-10
        for p,h in [(ROOT/w['source_prompt'],w['prompt_sha256']),(ROOT/w['chart_file'],w['image_sha256']),(Path(w['stimulus_dir'])/'input.txt',w['input_sha256'])]:assert sha(p)==h
        d=r['decision'];entrytime=pd.Timestamp(w['entry_time']);p=int(idx.searchsorted(entrytime))-1
        assert idx[p]+pd.Timedelta(minutes=1)==entrytime
        entry=float(c[p]);assert abs(entry-w['price_real'])<1e-8
        h=105 if d['action']=='long' else 30;sign=-1 if d['action']=='long' else 1
        exittime=entrytime+pd.Timedelta(minutes=h);exitpx=float(c[p+h]);gross=sign*(exitpx/entry-1)*100
        row={'case':r['case'],'window_id':w['window_id'],'asset':w['asset'],'entry_time':str(entrytime),'exit_time':str(exittime),'model':r['model'],'ai_action':d['action'],'strategy_action':'long' if sign==1 else 'short','hypothesis':'H-LONG' if sign==1 else 'H-SHORT','horizon_minutes':h,'entry_price':entry,'exit_price':exitpx,'gross_pct':gross,'net_pct':gross-.20,'same_ai_direction_gross_pct':-gross,'same_ai_direction_net_pct':-gross-.20,'next_open_entry_price':float(o[p+1]),'next_open_gross_pct':sign*(exitpx/o[p+1]-1)*100,'confidence':d['confidence'],'stop_pct':d['stop_pct'],'tp_pct':d['tp_pct'],'reason':d['reason'],'thread_id':r['thread_id']}
        row['next_open_net_pct']=row['next_open_gross_pct']-.20
        for horizon in [30,105]:
            assert idx[p+horizon]+pd.Timedelta(minutes=1)==entrytime+pd.Timedelta(minutes=horizon)
            expected=float(px15.loc[entrytime+pd.Timedelta(minutes=horizon-15),'close'])
            assert abs(expected-c[p+horizon])<1e-8
            row[f'raw_{horizon}m_pct']=(float(c[p+horizon])/entry-1)*100
        # Descriptive path audit only: these do not alter the frozen entry/exit policy.
        signed_closes=sign*(c[p+1:p+h+1]/entry-1)*100
        row['mfe_pct']=float(max(0,np.max((hi[p+1:p+h+1]/entry-1)*100 if sign==1 else (1-lo[p+1:p+h+1]/entry)*100)))
        row['mae_pct']=float(min(0,np.min((lo[p+1:p+h+1]/entry-1)*100 if sign==1 else (1-hi[p+1:p+h+1]/entry)*100)))
        row['positive_minute_closes']=int((signed_closes>0).sum())
        original={k:w[k] for k in ['window_id','asset','window_end_ts','price_real','sigma_vis_pct','sigma_2d_pct','atr14_pct','ret_vis_pct','ma20_now','ma50_now','vol24_ratio']}
        original.update(d)
        original.update(run_id=M['run_id'],case=r['case'],case_number=r['case'],model=r['model']+'-agent',model_version=r['model']+' via fresh Codex exec',reasoning_effort='medium',visible_bars=40,stimulus='text+image',image=w['chart_file'],prompt_version='sim-v2-15m-window-2to1-noflat-reversal-validation',stimulus_text_sha256=w['prompt_sha256'],stimulus_image_sha256=w['image_sha256'],combined_input_sha256=w['input_sha256'],protocol_sha256=M['protocol_sha256'],raw_response=r['raw_response'],ts_decided=r['ts_decided'],thread_id=r['thread_id'],agent_path=r['agent_path'],isolation=r['isolation'],tp_source='harness: exactly 2 * stop_pct')
        original.update(resolver.resolve(w['asset'],pd.Timestamp(w['window_end_ts']),d['action'],d['stop_pct'],d['tp_pct']))
        assert original['entry_price']==entry and d['tp_pct']==2*d['stop_pct']
        row.update(original_bracket_outcome=original['outcome'],original_bracket_gross_pct=original['pnl_gross_pct'],original_bracket_net_pct=original['pnl_net_pct'],original_bracket_minutes=original['minutes_held'])
        rows.append(clean(row));ledger.append(clean(original))
    append_verified(ROOT/'data/sim/decisions'/f"{M['run_id']}.jsonl",ledger)
    append_verified(HERE/'strategy_trades.jsonl',rows)
    df=pd.DataFrame(rows);df.to_csv(HERE/'strategy_trades.csv',index=False)
    rng=np.random.default_rng(2026092902);draws=rng.integers(0,50,size=(10000,50))
    def stats(values,mask=None):
        values=np.asarray(values,float);mask=np.ones(50,bool) if mask is None else np.asarray(mask,bool)
        x=values[mask];bootmask=mask[draws];den=bootmask.sum(1)
        means=np.sum(values[draws]*bootmask,axis=1)/np.maximum(den,1);means=means[den>0]
        if not len(x):return {'n':0}
        ci=np.quantile(means,[.025,.975])
        return {'n':len(x),'gross_positive':int((x>0).sum()),'net_positive':int((x>.20).sum()),'gross_win_rate':float((x>0).mean()),'net_win_rate':float((x>.20).mean()),'mean_gross_pct':x.mean(),'mean_net_pct':x.mean()-.20,'median_gross_pct':np.median(x),'median_net_pct':np.median(x)-.20,'sd_gross_pct':x.std(ddof=1) if len(x)>1 else None,'ci95_mean_gross_pct':ci,'ci95_mean_net_pct':ci-.20,'bootstrap_nonempty_replicates':len(means)}
    baseline={f'{side}_{h}m':stats(df[f'raw_{h}m_pct']*sgn) for h in [30,105] for side,sgn in [('long',1),('short',-1)]}
    hypotheses={};ai_long=(df.ai_action=='long').to_numpy();permuted=np.array([rng.permutation(ai_long) for _ in range(10000)])
    for name,side,h,mask,labels in [('H-SHORT','short',105,ai_long,permuted),('H-LONG','long',30,~ai_long,~permuted)]:
        values=df[f'raw_{h}m_pct'].to_numpy()*(1 if side=='long' else -1)
        result=stats(values,mask);result.update(strategy_side=side,horizon_minutes=h,trigger_ai_side='long' if side=='short' else 'short',baseline=baseline[f'{side}_{h}m'],same_ai_direction=stats(-values,mask),next_open_entry_sensitivity=stats(df.next_open_gross_pct,mask))
        if mask.any() and not mask.all():
            delta=values[mask].mean()-values.mean();null=(labels*values).sum(1)/mask.sum()-values.mean()
            result['selection_test']={'selected_minus_all_eligible_pct':delta,'p_two_sided':(1+(np.abs(null)>=abs(delta)-1e-14).sum())/10001,'permutations':10000,'null':'shuffle AI long/short labels across all 50 windows, preserving counts'}
        else:result['selection_test']={'selected_minus_all_eligible_pct':None,'p_two_sided':None,'reason':'No selection variation'}
        ids=df.loc[mask].sort_values('entry_time').index.to_numpy();mid=len(ids)//2;halves={}
        for label,sub in [('earlier',ids[:mid]),('later',ids[mid:])]:
            x=values[sub];halves[label]={'n':len(x),'mean_gross_pct':x.mean() if len(x) else None,'mean_net_pct':x.mean()-.20 if len(x) else None,'gross_positive':int((x>0).sum())}
        result['chronological_halves']=halves;hypotheses[name]=result
    tests=[hypotheses[k]['selection_test'] for k in ['H-SHORT','H-LONG']];pvals=np.array([t['p_two_sided'] if t['p_two_sided'] is not None else 1 for t in tests]);order=np.argsort(pvals);q=np.minimum.accumulate((pvals[order]*2/np.arange(1,3))[::-1])[::-1];qs=np.empty(2);qs[order]=np.minimum(q,1)
    for t,qval in zip(tests,qs):t['q_bh_two_tests']=qval if t['p_two_sided'] is not None else None
    summary={'run_id':M['run_id'],'status':'complete','model':'gpt-5.6-terra','n':50,'attempts':50,'cost_roundtrip_bps':20,'bootstrap_seed':2026092902,'bootstrap_method':'resample all 50 complete window rows, then compute each triggered subgroup mean; percentile 95% intervals','hypotheses':hypotheses,'combined':stats(df.gross_pct),'combined_next_open_sensitivity':stats(df.next_open_gross_pct),'baselines':baseline,'ai_long':int(ai_long.sum()),'ai_short':int((~ai_long).sum()),'original_bracket_outcomes':df.original_bracket_outcome.value_counts().to_dict(),'original_bracket_mean_gross_pct':df.original_bracket_gross_pct.mean(),'original_bracket_mean_net_pct':df.original_bracket_net_pct.mean(),'limitations':['Historical SOL archive, fresh to this experiment; not chronological or live holdout','50 total windows, split across rules, not 50 per strategy','Terra and rules selected using earlier exploratory findings','At/above both intraday moving averages, not a daily macro regime filter','Fixed fee estimate; no funding/borrow/latency/market impact','Bootstrap and permutations treat windows as exchangeable; market-regime dependence can remain','No parameter search in this batch; no causal claim that reversing arbitrary AI is profitable']}
    save('summary.json',summary)
    assert all(sha(ROOT/p)==h for p,h in M['original_sha256'].items())
    save('validation.json',{'passed':True,'decisions':50,'strategy_rows':50,'unique_windows':len(set(df.window_id)),'unique_sessions':len(set(df.thread_id)),'source_files_preserved':len(M['original_sha256']),'source_hashes_match':True,'all_input_hashes_match':True,'protocol_hash_matches':True,'zero_model_tool_calls':True,'bracket_entries_match':True,'independent_15m_exit_price_checks':100,'native_1m_exit_timestamps_checked':100,'rules_exact':True,'gross_net_difference_pct':.20})
    print(json.dumps(clean(summary),indent=2,allow_nan=False))
if __name__=='__main__':main()
