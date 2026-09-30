"""Evaluate exactly the two frozen finalists, once fresh collection is complete."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,hashlib
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];STUDY=ROOT/'data/analysis/reversal-deep-20260929'
sys.path.insert(0,str(STUDY/'risk'));sys.path.insert(0,str(ROOT/'src'))
from validation_engine import bracket_batch,donor_matrix
from nai.sim import SimResolver
M=json.loads((HERE/'manifest.json').read_text());B=20000;COST=.2
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.bool_,)):return bool(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x

def save(name,x):
    p=HERE/name;t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(clean(x),indent=2,allow_nan=False)+'\n');t.replace(p)
def ledger(path,rows):
    rows=clean(rows);old=[json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    assert len(old)<=len(rows) and all(a==b for a,b in zip(old,rows)),str(path)+' existing rows differ'
    with path.open('a') as f:
        for r in rows[len(old):]:f.write(json.dumps(r,allow_nan=False)+'\n')

def main():
    assert (HERE/'ALLOW_EVALUATION').exists(),'Fresh outcomes sealed until collection complete'
    records=[json.loads(s) for s in (HERE/'accepted_decisions.jsonl').read_text().splitlines()];records.sort(key=lambda r:r['case']);N=len(records)
    assert N==280 and [r['case'] for r in records]==list(range(1,281))
    assert all(r['model']=='gpt-5.6-terra' and r['reasoning_effort']=='medium' and not r['tool_calls'] for r in records)
    assert sha(ROOT/M['protocol_file'])==M['protocol_sha256']
    original=M['original_sha256']|json.loads((HERE/'additional_source_preservation.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in original.items())
    for w in M['cases']:
        for path,h in [(ROOT/w['source_prompt'],w['prompt_sha256']),(ROOT/w['chart_file'],w['image_sha256']),(Path(w['stimulus_dir'])/'input.txt',w['input_sha256'])]:assert sha(path)==h
    audit=json.loads((HERE/'isolation_audit.json').read_text());assert audit['accepted']==280
    passed={a['agent_path'] for a in audit['audits'] if a['passed']};assert all(r['agent_path'] in passed for r in records)
    px=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index();idx=px.index
    aa=px[['open','high','low','close']].to_numpy(float);paths=[];times=[];source=[]
    resolver=SimResolver.__new__(SimResolver);resolver.bar_min=1;resolver.max_bars=1440;resolver._d={'SOL-USD':(idx,aa[:,0],aa[:,1],aa[:,2],aa[:,3])}
    for w,r in zip(M['cases'],records):
        t=pd.Timestamp(w['entry_time']);p=int(idx.searchsorted(t))-1
        assert idx[p:p+1441].equals(pd.date_range(t-pd.Timedelta(minutes=1),periods=1441,freq='min'))
        a=aa[p:p+1441].copy();assert abs(a[0,3]-w['price_real'])<1e-8;paths.append(a);times.append(t)
        d={k:w[k] for k in ['asset','window_id','window_end_ts','price_real','sigma_vis_pct','sigma_2d_pct','atr14_pct','ret_vis_pct','ma20_now','ma50_now','vol24_ratio']};d.update(r['decision'])
        d.update(run_id=M['run_id'],case=r['case'],case_number=r['case'],model=r['model']+'-agent',reasoning_effort='medium',model_version=r['model']+' via fresh Codex exec',prompt_version='sim-v2-ma-present-validation24h',visible_bars=40,stimulus='text+image',image=w['chart_file'],stimulus_text_sha256=w['prompt_sha256'],stimulus_image_sha256=w['image_sha256'],combined_input_sha256=w['input_sha256'],protocol_sha256=M['protocol_sha256'],raw_response=r['raw_response'],ts_decided=r['ts_decided'],thread_id=r['thread_id'],agent_path=r['agent_path'],isolation=r['isolation'],evaluation_horizon_minutes=1440,evaluation_note='Original model bracket evaluated at 24h only; distinct from S/L finalist policies')
        d.update(resolver.resolve('SOL-USD',pd.Timestamp(w['window_end_ts']),d['action'],d['stop_pct'],d['tp_pct']));source.append(d)
    paths=np.array(paths);times=pd.DatetimeIndex(times);atr=np.array([w['atr14_pct'] for w in M['cases']]);stop=np.array([r['decision']['stop_pct']*100 for r in records]);action_long=np.array([r['decision']['action']=='long' for r in records]);ma20=np.array([w['ma20_now'] for w in M['cases']]);ma50=np.array([w['ma50_now'] for w in M['cases']]);regime=np.where((ma20<=100)&(ma50<=100),'aboveboth',np.where((ma20>100)&(ma50>100),'belowboth','mixed'));era=np.where(times.year<=2021,'2020-21',np.where(times.year<=2023,'2022-23','2024-26'));strata=np.array([a+'/'+b for a,b in zip(era,regime)])
    print('Coverage and inputs verified; scoring frozen policies',flush=True)
    # L: future minute15 closes at original t+15; next minute open index16 is t+15.
    confirm=paths[:,15,3]>paths[:,0,3];lmask=(~action_long)&confirm
    lgross=(paths[:,255,3]/paths[:,16,0]-1)*100
    ldelay={str(delay):(paths[:,255,3]/paths[:,16+delay,0]-1)*100 for delay in [1,5]}
    s=bracket_batch(paths,1.5*stop,sign=-1,rr=2,horizon=240,delay=0);sgross=s['gross_pct'];smask=action_long
    sdelay={str(delay):bracket_batch(paths,1.5*stop,sign=-1,rr=2,horizon=240,delay=delay)['gross_pct'] for delay in [1,5]}
    follow=bracket_batch(paths,1.5*stop,sign=1,rr=2,horizon=240,delay=0)
    atrcontrol=bracket_batch(paths,2*atr,sign=-1,rr=2,horizon=240,delay=0)
    atrdiag=bracket_batch(paths,2*atr,sign=-1,rr=1,horizon=240,delay=0)
    rng=np.random.default_rng(2026092930);draws=rng.integers(0,N,size=(B,N));quarters=times.to_period('Q').astype(str);qcodes,qlabels=pd.factorize(quarters);qdim=len(qlabels);qdraws=rng.integers(0,qdim,size=(B,qdim))
    def stats(gross,mask=None):
        gross=np.asarray(gross,float);mask=np.ones(N,bool) if mask is None else np.asarray(mask,bool);x=gross[mask];net=x-COST;n=len(x)
        if not n:
            z={k:np.nan for k in ['mean_gross_pct','mean_net_pct','median_gross_pct','median_net_pct','gross_win_rate','net_win_rate','mean_net_at30bps_pct','break_even_roundtrip_bps','profit_factor_net','mean_gross_winner_pct','mean_gross_loser_pct','worst_gross_pct','best_gross_pct','sd_gross_pct','mean_net_excluding_best1_pct','mean_net_excluding_best3_pct']}
            z.update(n=0,opportunities=N,gross_positive=0,net_positive=0,mean_net_per_opportunity_pct=0,bootstrap_nonempty=0,quarter_clusters=qdim,chronological_thirds=[{'n':0,'mean_net_pct':np.nan}]*3,leave_one_chronological_third_out_net_means_pct=[np.nan]*3)
            for k in ['ci95_mean_net_pct','simultaneous_ci975_mean_net_pct','quarter_cluster_ci95_net_pct','quarter_cluster_ci975_net_pct']:z[k]=[np.nan,np.nan]
            return z
        bs=mask[draws];den=bs.sum(1);valid=den>0;means=np.sum((gross[draws]-COST)*bs,axis=1)[valid]/den[valid]
        qsum=np.bincount(qcodes,weights=np.where(mask,gross-COST,0),minlength=qdim);qn=np.bincount(qcodes,weights=mask,minlength=qdim);qden=qn[qdraws].sum(1);qvalid=qden>0;qmean=qsum[qdraws].sum(1)[qvalid]/qden[qvalid]
        xorder=net[np.argsort(times[mask])];thirds=[{'n':len(a),'mean_net_pct':a.mean() if len(a) else None} for a in np.array_split(xorder,3)]
        return {'n':n,'opportunities':N,'gross_positive':int((x>0).sum()),'net_positive':int((net>0).sum()),'gross_win_rate':(x>0).mean(),'net_win_rate':(net>0).mean(),'mean_gross_pct':x.mean(),'mean_net_pct':net.mean(),'mean_net_per_opportunity_pct':net.sum()/N,'median_gross_pct':np.median(x),'median_net_pct':np.median(net),'mean_gross_winner_pct':x[x>0].mean() if (x>0).any() else None,'mean_gross_loser_pct':x[x<0].mean() if (x<0).any() else None,'profit_factor_net':net[net>0].sum()/-net[net<0].sum() if (net<0).any() else None,'worst_gross_pct':x.min(),'best_gross_pct':x.max(),'sd_gross_pct':x.std(ddof=1),'ci95_mean_net_pct':np.quantile(means,[.025,.975]),'simultaneous_ci975_mean_net_pct':np.quantile(means,[.0125,.9875]),'quarter_cluster_ci95_net_pct':np.quantile(qmean,[.025,.975]),'quarter_cluster_ci975_net_pct':np.quantile(qmean,[.0125,.9875]),'bootstrap_nonempty':len(means),'quarter_clusters':qdim,'chronological_thirds':thirds,'leave_one_chronological_third_out_net_means_pct':[np.delete(xorder,np.arange(n)[part]).mean() if n>len(np.arange(n)[part]) else None for part in [slice(0,len(np.array_split(xorder,3)[0])),slice(len(np.array_split(xorder,3)[0]),len(np.array_split(xorder,3)[0])+len(np.array_split(xorder,3)[1])),slice(len(np.array_split(xorder,3)[0])+len(np.array_split(xorder,3)[1]),n)]],'mean_net_excluding_best1_pct':np.sort(net)[:-1].mean() if n>1 else None,'mean_net_excluding_best3_pct':np.sort(net)[:-3].mean() if n>3 else None,'mean_net_at30bps_pct':x.mean()-.3,'break_even_roundtrip_bps':x.mean()*100}
    results={'L':stats(lgross,lmask),'S':stats(sgross,smask)}
    results['L']['entry_delay_sensitivity']={k:stats(v,lmask) for k,v in ldelay.items()};results['S']['entry_delay_sensitivity']={k:stats(v,smask) for k,v in sdelay.items()}
    controls={'L_without_AI_confirmation':stats(lgross,confirm),'L_below_MA20_confirmation':stats(lgross,confirm&(ma20>100)),'L_same_AI_short_on_identical_entries':stats(-lgross,lmask),'S_all_windows_AI_width_not_AI_free':stats(sgross),'S_price_only_ATR2_RR2_all':stats(atrcontrol['gross_pct']),'S_price_only_ATR2_RR2_above_MA20':stats(atrcontrol['gross_pct'],ma20<=100),'S_follow_AI_long_same_geometry':stats(follow['gross_pct'],smask),'diagnostic_S_ATR2_RR1_AI_selected':stats(atrdiag['gross_pct'],smask),'diagnostic_S_ATR2_RR1_all':stats(atrdiag['gross_pct'])}
    print('Bootstraps and controls complete; computing conditional AI null',flush=True)
    # Donor rows carry complete action/risk information but preserve receiver ATR scaling.
    payoff=donor_matrix(paths,atr,stop/atr,rr=2,multiplier=1.5,horizon=240,delay=0)
    assert np.allclose(np.diag(payoff),sgross,atol=1e-9), 'Permutation diagonal differs from primary engine'
    prng=np.random.default_rng(2026092931);perms=np.tile(np.arange(N),(B,1))
    for label in sorted(set(strata)):
        group=np.flatnonzero(strata==label);perms[:,group]=group[np.argsort(prng.random((B,len(group))),axis=1)]
    perm_long=action_long[perms];lm=(~perm_long)&confirm;ld=lm.sum(1);lnull=((lgross-COST)*lm).sum(1)[ld>0]/ld[ld>0]
    sden=perm_long.sum(1);snull=np.sum((payoff[np.arange(N)[None,:],perms]-COST)*perm_long,axis=1)[sden>0]/sden[sden>0]
    for key,null in [('L',lnull),('S',snull)]:
        obs=results[key]['mean_net_pct']
        if not len(null) or not np.isfinite(obs):
            results[key]['AI_selection']={'observed_selected_mean_net_pct':obs,'conditional_null_mean_net_pct':np.nan,'increment_over_conditional_null_pct':np.nan,'p_one_sided':1.,'null_ci95_pct':[np.nan,np.nan],'valid_permutations':len(null),'reason':'No executed trades or no valid shuffled selections'}
            continue
        results[key]['AI_selection']={'observed_selected_mean_net_pct':obs,'conditional_null_mean_net_pct':null.mean(),'increment_over_conditional_null_pct':obs-null.mean(),'p_one_sided':(1+(null>=obs-1e-14).sum())/(1+len(null)),'null_ci95_pct':np.quantile(null,[.025,.975]),'valid_permutations':len(null)}
    pv=np.array([results[k]['AI_selection']['p_one_sided'] for k in ['L','S']]);order=np.argsort(pv);adj=np.minimum(1,np.maximum.accumulate(pv[order]*np.array([2,1])));q=np.empty(2);q[order]=adj
    for key,val in zip(['L','S'],q):
        r=results[key];r['AI_selection']['p_holm_two_tests']=val
        r['verification']={'at_least50_executed':r['n']>=50,'simultaneous_net_CI_positive':r['simultaneous_ci975_mean_net_pct'][0]>0,'quarter_cluster_CI_positive':r['quarter_cluster_ci975_net_pct'][0]>0,'all_chronological_third_means_positive':all(t['mean_net_pct']>0 for t in r['chronological_thirds']),'30bps_mean_positive':r['mean_net_at30bps_pct']>0,'both_delay_means_positive':all(t['mean_net_pct']>0 for t in r['entry_delay_sensitivity'].values()),'AI_increment_positive_and_significant':r['AI_selection']['increment_over_conditional_null_pct']>0 and val<.05}
        r['passes_frozen_profit_tests']=all(r['verification'][k] for k in ['at_least50_executed','simultaneous_net_CI_positive','30bps_mean_positive','both_delay_means_positive'])
        r['passes_frozen_primary_tests']=r['passes_frozen_profit_tests'] and r['verification']['AI_increment_positive_and_significant']
        r['single_period_dependence_check_passed']=all(v is not None and v>0 for v in r['leave_one_chronological_third_out_net_means_pct'])
        r['verified_AI_strategy']=r['passes_frozen_primary_tests'] and r['single_period_dependence_check_passed']
    perwindow=[];trades=[]
    for i,(w,r) in enumerate(zip(M['cases'],records)):
        case=w['case'];t=times[i];common={'case':case,'window_id':w['window_id'],'asset':'SOL-USD','original_entry_time':str(t),'ai_action':r['decision']['action'],'ai_stop_pct':r['decision']['stop_pct'],'confidence':r['decision']['confidence'],'reason':r['decision']['reason'],'regime':str(regime[i]),'era':str(era[i]),'atr14_pct':atr[i],'ma20_now':ma20[i],'ma50_now':ma50[i],'thread_id':r['thread_id']}
        perwindow.append(dict(common,L_confirmed=confirm[i],L_selected=lmask[i],L_gross_pct=lgross[i],L_net_pct=lgross[i]-COST,L_entry_price=paths[i,16,0],L_exit_price=paths[i,255,3],S_selected=smask[i],S_gross_pct=sgross[i],S_net_pct=sgross[i]-COST,S_outcome=str(s['outcome'][i]),S_held_minutes=int(s['held_minutes'][i]),S_entry_price=paths[i,0,3],S_exit_price=s['exit_price'][i],S_stop_percent=1.5*stop[i],S_target_percent=3*stop[i],S_ATR2_RR2_gross_pct=atrcontrol['gross_pct'][i],S_ATR2_RR1_gross_pct=atrdiag['gross_pct'][i],**{f'L_delay{k}_gross_pct':v[i] for k,v in ldelay.items()},**{f'S_delay{k}_gross_pct':v[i] for k,v in sdelay.items()}))
        for key,mask,g in [('L',lmask,lgross),('S',smask,sgross)]:
            if not mask[i]:continue
            islong=key=='L';start=t+pd.Timedelta(minutes=15) if islong else t;end=t+pd.Timedelta(minutes=255) if islong else t+pd.Timedelta(minutes=int(s['exit_index'][i]));trade=dict(common,strategy=key,strategy_side='long' if islong else 'short',entry_time=str(start),exit_minute_close_time=str(end),entry_price=paths[i,16,0] if islong else paths[i,0,3],exit_price=paths[i,255,3] if islong else s['exit_price'][i],gross_pct=g[i],net_pct=g[i]-COST,minutes_held=240 if islong else int(s['held_minutes'][i]),outcome='time' if islong else str(s['outcome'][i]),exit_timestamp_note='Fixed time close' if islong else 'Minute close bound; bracket may execute earlier inside this minute, gap at minute open',**{f'delay{k}_gross_pct':(ldelay if islong else sdelay)[k][i] for k in ['1','5']});trades.append(trade)
    ledger(HERE/'strategy_trades.jsonl',trades);ledger(HERE/'window_results.jsonl',perwindow);pd.DataFrame(clean(trades)).to_csv(HERE/'strategy_trades.csv',index=False);pd.DataFrame(clean(perwindow)).to_csv(HERE/'window_results.csv',index=False)
    ledger(ROOT/'data/sim/decisions'/f"{M['run_id']}.jsonl",source)
    np.savez_compressed(HERE/'permutation_nulls.npz',L=lnull,S=snull)
    summary={'run_id':M['run_id'],'status':'scored_pending_independent_review','windows':N,'model':'gpt-5.6-terra','ai_long':int(action_long.sum()),'ai_short':int((~action_long).sum()),'cost_bps':20,'strategies':results,'controls':controls,'strata':pd.Series(strata).value_counts().to_dict(),'hypothesis_count':2,'bootstrap_draws':B,'permutations':B,'bootstrap_seed':2026092930,'permutation_seed':2026092931,'source_files_preserved':len(original),'protocol_sha256':M['protocol_sha256'],'limitations':['Historical SOL-only sample; not live or chronological future holdout','Prior expansive discovery and limited fresh sample; all chosen finalists reported','Primary short entry assumes instantaneous inference, delay stresses reported','Fixed20bpscost; funding/borrow/impact not modeled','Conditional permutation controls broad regime/era and volatility, not all price features','Some calendar/regime dependence can remain']}
    save('summary.json',summary)
    assert all(sha(ROOT/p)==h for p,h in original.items());save('scoring_audit.json',{'source_files_unchanged':len(original),'all280input_hashes_match':True,'protocol_matches':True,'minute_coverage_checks':N,'permutation_diagonal_checks':N,'canonical_original_bracket_horizon_minutes':1440,'strategy_trade_count':len(trades),'all_decisions_before_evaluation':True})
    print(json.dumps(clean(summary),indent=2,allow_nan=False))
if __name__=='__main__':main()
