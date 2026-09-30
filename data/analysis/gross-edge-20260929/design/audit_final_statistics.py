"""Independent final audit; run only after root explicitly releases the seal.

This file does not import the production evaluator or execution engine.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,hashlib
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;STUDY=HERE.parent;ROOT=HERE.parents[3]

def eq(actual,claimed,tolerance=1e-10):
    def numeric(v):
        if isinstance(v,(list,tuple,np.ndarray)):return [numeric(x) for x in v]
        return np.nan if v is None else v
    assert np.allclose(numeric(actual),numeric(claimed),rtol=0,atol=tolerance,equal_nan=True),(actual,claimed)

def scalar_bracket(path,stop_percent,sign=-1,delay=0):
    entry=path[delay+1,0] if delay else path[0,3]
    sl=entry*(1-sign*stop_percent/100)
    tp=entry*(1+sign*stop_percent/100)
    for j in range(delay+1,241):
        op,hi,lo,cl=path[j]
        if (op<=sl if sign==1 else op>=sl):price=op;outcome='sl_gap'
        elif (op>=tp if sign==1 else op<=tp):price=tp;outcome='tp_gap_capped'
        else:
            stops=lo<=sl if sign==1 else hi>=sl
            targets=hi>=tp if sign==1 else lo<=tp
            if stops:price=sl;outcome='sl_ambiguous' if targets else 'sl'
            elif targets:price=tp;outcome='tp'
            else:continue
        return sign*(price/entry-1)*100,outcome,j
    return sign*(path[240,3]/entry-1)*100,'timeout',240

def row_weight_estimator(values,selected,eligible,strata,groups,group_weights):
    """Independent direct observation weights, without group×stratum matrices."""
    B=len(group_weights);means=np.full(B,np.nan);deltas=np.full(B,np.nan)
    for start in range(0,B,250):
        w=group_weights[start:start+250][:,groups]
        count=w[:,selected].sum(axis=1)
        mean=np.divide(w[:,selected]@values[selected],count,
                       out=np.full(len(w),np.nan),where=count>0)
        baseline_numerator=np.zeros(len(w))
        for s in sorted(set(strata[selected])):
            take=selected&(strata==s);available=eligible&(strata==s)
            ntake=w[:,take].sum(axis=1);navailable=w[:,available].sum(axis=1)
            control=np.divide(w[:,available]@values[available],navailable,
                              out=np.zeros(len(w)),where=navailable>0)
            baseline_numerator+=ntake*control
        baseline=np.divide(baseline_numerator,count,
                           out=np.full(len(w),np.nan),where=count>0)
        means[start:start+len(w)]=mean;deltas[start:start+len(w)]=mean-baseline
    return means,deltas

def quantiles(values):
    z=values[np.isfinite(values)]
    return {'ci95':np.quantile(z,[.025,.975]) if len(z) else [np.nan,np.nan],
            'simultaneous97_5':np.quantile(z,[.0125,.9875]) if len(z) else [np.nan,np.nan],
            'valid_resamples':len(z)}

def main():
    assert '--released-by-root' in sys.argv,'Explicit root outcome release required'
    run=Path(json.loads((STUDY/'run.json').read_text())['run_dir'])
    assert (run/'ALLOW_EVALUATION').exists(),'Forward outcomes remain sealed'
    manifest=json.loads((run/'manifest.json').read_text())
    records=sorted([json.loads(x) for x in (run/'accepted_decisions.jsonl').read_text().splitlines()],key=lambda r:r['case'])
    summary=json.loads((run/'summary.json').read_text())
    ledger=pd.DataFrame([json.loads(x) for x in (run/'strategy_trades.jsonl').read_text().splitlines()])
    cached=np.load(run/'bootstrap_arrays.npz');paths_archive=np.load(run/'paths.npz');paths=paths_archive['paths']
    d=pd.DataFrame(manifest['cases']).sort_values('case').reset_index(drop=True)
    N=len(d);assert N==len(records)==500 and paths.shape==(500,361,4)
    assert np.array_equal(d.case,np.arange(1,501)) and np.array_equal(d.case,paths_archive['case'])
    assert [r['case'] for r in records]==list(range(1,501))
    assert len(ledger)==1000 and summary['cost_bps']==0
    audit=json.loads((run/'isolation_audit.json').read_text())
    passed={a['agent_path'] for a in audit['audits'] if a['passed']}
    assert all(r['agent_path'] in passed and r['model']=='gpt-5.6-terra' and not r['tool_calls'] for r in records)
    assert len({r['thread_id'] for r in records})==500
    budget=json.loads((STUDY/'snapshot_budget.json').read_text())
    calls=len(budget['reserved_attempts'])
    assert calls<=budget['authorized_maximum_attempts']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert all(sha(ROOT/p)==v for p,v in manifest['original_sha256'].items())
    for w in manifest['cases']:
        assert sha(ROOT/w['source_prompt'])==w['prompt_sha256']
        assert sha(ROOT/w['chart_file'])==w['image_sha256']
        assert sha(Path(w['stimulus_dir'])/'input.txt')==w['input_sha256']
    times=pd.DatetimeIndex(d.entry_time)
    action_long=np.array([r['decision']['action']=='long' for r in records])
    above=(d.ma20_now.to_numpy()<=100)&(d.ma50_now.to_numpy()<=100)
    below=(d.ma20_now.to_numpy()>=100)&(d.ma50_now.to_numpy()>=100)
    regime=np.where(above,'above_both',np.where(below,'below_both','mixed'))
    era=np.where(times.year<=2021,'2020-21',np.where(times.year<=2023,'2022-23','2024-26'))
    stratum_names=np.array([str(a)+'|'+str(b)+'|'+str(c) for a,b,c in zip(d.asset,era,regime)])
    stratum_labels=sorted(set(stratum_names));strata=np.array([stratum_labels.index(s) for s in stratum_names])
    assert np.array_equal(np.array(stratum_labels),cached['stratum_labels'])
    block_labels=sorted(set(d.block));blocks=np.array([block_labels.index(x) for x in d.block])
    quarter_names=times.to_period('Q').astype(str);quarter_labels=sorted(set(quarter_names))
    quarters=np.array([quarter_labels.index(s) for s in quarter_names])
    assert len(block_labels)==125
    bw=np.random.default_rng(2026092951).multinomial(125,np.full(125,1/125),size=20000)
    G=len(quarter_labels);qw=np.random.default_rng(2026092952).multinomial(G,np.full(G,1/G),size=20000)
    assert np.array_equal(bw,cached['block_weights']) and np.array_equal(qw,cached['quarter_weights'])
    chronological_blocks=d[['block','entry_time']].drop_duplicates().sort_values('entry_time').block.to_numpy()
    results={};scalar_checks=0
    for rule in ['L048','S508']:
        claimed=summary['rules'][rule]
        if rule=='L048':
            eligible=(d.asset_daily_close.to_numpy()<=d.asset_daily_sma50.to_numpy())&(d.btc_daily_close.to_numpy()<=d.btc_daily_sma200.to_numpy())
            selected=eligible&~action_long
            gross=100*(paths[:,240,3]/paths[:,1,0]-1)
            delay={str(k):100*(paths[:,240,3]/paths[:,k+1,0]-1) for k in [1,5]}
            outcomes=np.array(['timeout']*N);exits=np.full(N,240)
        else:
            eligible=above;selected=eligible&action_long
            replay=[scalar_bracket(p,2*a) for p,a in zip(paths,d.atr14_pct)]
            gross=np.array([x[0] for x in replay]);outcomes=np.array([x[1] for x in replay]);exits=np.array([x[2] for x in replay])
            delay={str(k):np.array([scalar_bracket(p,2*a,delay=k)[0] for p,a in zip(paths,d.atr14_pct)]) for k in [1,5]}
            scalar_checks+=1500
        saved=ledger[ledger.rule==rule].sort_values('case')
        assert np.array_equal(saved.selected,selected) and np.array_equal(saved.eligible,eligible)
        eq(gross,saved.gross_pct);eq(gross,saved.net_at_zero_cost_pct)
        assert np.array_equal(outcomes,saved.outcome) and np.array_equal(exits,saved.exit_minute_index)
        for k in ['1','5']:eq(delay[k],saved['entry_delay'+k+'_gross_pct'])
        count=int(selected.sum());selected_blocks=len(set(d.block[selected]))
        assert count==claimed['selected']['n'] and selected_blocks==claimed['selected_blocks']
        eq(gross[selected].mean() if count else np.nan,claimed['selected'].get('mean_gross_pct'))
        eq(np.where(selected,gross,0).mean(),claimed['opportunity_mean_gross_pct'])
        eq(gross[eligible].mean() if eligible.any() else np.nan,claimed['eligible_price_only'].get('mean_gross_pct'))
        group_results={}
        for label,groups,weights in [('block',blocks,bw),('quarter',quarters,qw)]:
            mean,delta=row_weight_estimator(gross,selected,eligible,strata,groups,weights)
            eq(mean,cached[rule+'_mean_'+label]);eq(delta,cached[rule+'_increment_'+label])
            inf=claimed[label+'_inference']
            for kind,values in [('profit',mean),('AI_increment',delta)]:
                computed=quantiles(values)
                for interval in ['ci95','simultaneous97_5']:eq(computed[interval],inf[kind][interval])
                assert computed['valid_resamples']==inf[kind]['valid_resamples']
            _,original_delta=row_weight_estimator(gross,selected,eligible,strata,np.zeros(N,dtype=int),np.ones((1,1)))
            eq(original_delta[0],inf['AI_increment_mean_pct'])
            observed=gross[selected].mean() if count else np.nan
            eq(observed-original_delta[0],inf['standardized_price_baseline_mean_pct'])
            group_results[label]={'profit':quantiles(mean),'increment':quantiles(delta)}
        half_means=[]
        for ids,stored in zip(np.array_split(chronological_blocks,2),claimed['chronological_halves']):
            chosen=selected&d.block.isin(ids).to_numpy();v=gross[chosen]
            eq(v.mean() if len(v) else np.nan,stored.get('mean_gross_pct'));half_means.append(v.mean() if len(v) else np.nan)
        for ids,stored in zip(np.array_split(chronological_blocks,3),claimed['chronological_thirds']):
            chosen=selected&d.block.isin(ids).to_numpy();v=gross[chosen]
            eq(v.mean() if len(v) else np.nan,stored.get('mean_gross_pct'))
        leave=[]
        for asset in d.asset.unique():
            own=selected&(d.asset==asset).to_numpy();other=selected&(d.asset!=asset).to_numpy()
            eq(gross[own].mean() if own.any() else np.nan,claimed['assets'][asset].get('mean_gross_pct'))
            eq(gross[other].mean() if other.any() else np.nan,claimed['leave_one_asset_out'][asset].get('mean_gross_pct'))
            leave.append(gross[other].mean() if other.any() else np.nan)
        profit=(count>=50 and selected_blocks>=30 and group_results['block']['profit']['simultaneous97_5'][0]>0
                and group_results['quarter']['profit']['ci95'][0]>0
                and all(delay[k][selected].mean()>0 for k in ['1','5']) and all(v>0 for v in half_means))
        ai=(group_results['block']['increment']['simultaneous97_5'][0]>0 and group_results['quarter']['increment']['ci95'][0]>0)
        broad=profit and all(v>0 for v in leave)
        assert bool(profit)==claimed['profit_verified'] and bool(ai)==claimed['AI_contribution_verified']
        assert bool(broad)==claimed['broad_cross_asset_verified']
        results[rule]={'trades':count,'selected_blocks':selected_blocks,
                       'mean_gross_pct':float(gross[selected].mean()) if count else None,
                       'all_bootstrap_mean_and_increment_arrays_match':True,
                       'all_profit_and_AI_increment_intervals_match':True,
                       'profit_verified':bool(profit),'AI_contribution_verified':bool(ai),
                       'broad_cross_asset_verified':bool(broad)}
    out={'passed':True,'audited_at':datetime.now(timezone.utc).isoformat(),'run_id':manifest['run_id'],
         'decisions':N,'physical_calls':calls,'calendar_blocks':125,'quarters':G,'cost_bps':0,
         'independent_scalar_short_brackets':scalar_checks,'model_decision_masks_verified':1000,
         'bootstrap_draws_per_scheme':20000,'whole_block_and_quarter_weights_reproduced':True,
         'explicit_observation_weight_stratified_baselines_used':True,
         'production_evaluator_or_engine_imported':False,'strategies':results}
    (HERE/'final_statistics_audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
