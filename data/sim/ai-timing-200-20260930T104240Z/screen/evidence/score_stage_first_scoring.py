"""Dormant stage scorer. No file reads at import; explicit audited release required."""
from pathlib import Path
import argparse,csv,gzip,hashlib,json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BOOTSTRAPS=40_000;SEED=2026093051

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,np.integer):return int(x)
    if isinstance(x,np.bool_):return bool(x)
    if isinstance(x,(float,np.floating)):
        if np.isnan(x):return None
        if np.isneginf(x):return '-Infinity'
        if np.isposinf(x):return 'Infinity'
        return float(x)
    if isinstance(x,pd.Timestamp):return str(x)
    return x
def save(path,value):Path(path).write_text(json.dumps(clean(value),indent=2,allow_nan=False)+'\n')
def stamp(value):
    t=pd.Timestamp(value)
    return t.tz_convert('UTC').tz_localize(None) if t.tzinfo is not None else t
def ratio(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    return np.divide(a,b,out=np.full(np.broadcast_shapes(a.shape,b.shape),np.nan),where=b>0)

def bootstrap_interval(values):
    values=np.asarray(values,float);finite=np.isfinite(values)
    lower_distribution=np.where(finite,values,-np.inf)
    # Finite-only ordinary interval is labelled conditional; decisions retain all draws.
    ordinary=np.quantile(values[finite],[.025,.975],method='inverted_cdf') if finite.any() else [None,None]
    return {'ordinary95_finite_draw_interval':ordinary,'ordinary95_lower_with_undefined_as_minus_infinity':np.quantile(lower_distribution,.025,method='inverted_cdf'),
            'simultaneous98_75_one_sided_lower':np.quantile(lower_distribution,.0125,method='inverted_cdf'),
            'undefined_draws':int((~finite).sum()),'undefined_fraction':float((~finite).mean()),'total_draws':len(values),'quantile_method':'inverted_cdf','family_size':4}

def basic(values):
    x=np.asarray(values,float);x=x[np.isfinite(x)];n=len(x)
    if not n:return {'n':0,'mean_gross_pct':None}
    pos=x[x>0];neg=x[x<0]
    return {'n':n,'mean_gross_pct':x.mean(),'median_gross_pct':np.median(x),'sum_trade_pct_not_portfolio':x.sum(),'wins':int((x>0).sum()),'losses':int((x<0).sum()),'zero_returns':int((x==0).sum()),'win_rate':float((x>0).mean()),'profit_factor':pos.sum()/-neg.sum() if len(neg) else (np.inf if len(pos) else None),'mean_winner_pct':pos.mean() if len(pos) else None,'mean_loser_pct':neg.mean() if len(neg) else None,'best_pct':x.max(),'worst_pct':x.min()}

def fixed_effects(frame):
    rows=[];numerator=0.;denominator=0.;aligned_mixed=0;opposed_mixed=0
    for (asset,above),g in frame.groupby(['asset','above_equal_MA20'],sort=True):
        a=g.AI_aligned.to_numpy(float);r=g.gate_gross_pct.to_numpy(float);n=len(g);sa=a.sum();sr=r.sum();sar=(a*r).sum()
        mixed=0<sa<n
        numerator+=sar-sa*sr/n;denominator+=sa-sa*sa/n
        if mixed:aligned_mixed+=int(sa);opposed_mixed+=int(n-sa)
        rows.append({'asset':asset,'MA20_side':'above_or_equal' if above else 'below','n':n,'aligned_n':int(sa),'opposed_n':int(n-sa),'mixed':mixed,'aligned_mean_pct':r[a==1].mean() if sa else None,'opposed_mean_pct':r[a==0].mean() if n-sa else None})
    return {'adjusted_aligned_minus_opposed_pct':numerator/denominator if denominator>1e-12 else None,'within_sum_squares':denominator,'mixed_aligned_n':aligned_mixed,'mixed_opposed_n':opposed_mixed,'mixed_strata':sum(x['mixed'] for x in rows),'strata':rows}

def bootstrap_direction(frame,quarters,weights):
    qlookup={q:i for i,q in enumerate(quarters)};codes=np.array([qlookup[q] for q in frame.quarter],int);qn=len(quarters)
    r=frame.gate_gross_pct.to_numpy(float);a=frame.AI_aligned.to_numpy(bool);ma=frame.MA20_control_selected.to_numpy(bool)
    def aggregate(value):return np.bincount(codes,weights=value,minlength=qn)
    alln=weights@aggregate(np.ones(len(frame)));an=weights@aggregate(a);on=weights@aggregate(~a);mn=weights@aggregate(ma)
    ay=weights@aggregate(np.where(a,r,0));oy=weights@aggregate(np.where(~a,r,0));my=weights@aggregate(np.where(ma,r,0));ry=weights@aggregate(r)
    result={'aligned_mean':ratio(ay,an),'opposed_mean':ratio(oy,on),'price_only_mean':ratio(ry,alln),'MA20_control_mean':ratio(my,mn),'aligned_per_gate':ratio(ay,alln),'opposed_per_gate':ratio(oy,alln),'price_only_per_gate':ratio(ry,alln),'MA20_per_gate':ratio(my,alln),'aligned_minus_price_per_gate':ratio(ay-ry,alln),'aligned_minus_MA20_per_gate':ratio(ay-my,alln)}
    result['raw_aligned_minus_opposed']=result['aligned_mean']-result['opposed_mean']
    numerator=np.zeros(len(weights));denominator=np.zeros(len(weights))
    for _,g in frame.groupby(['asset','above_equal_MA20'],sort=True):
        cc=np.array([qlookup[q] for q in g.quarter],int);aa=g.AI_aligned.to_numpy(float);rr=g.gate_gross_pct.to_numpy(float)
        agg=lambda x:np.bincount(cc,weights=x,minlength=qn)
        n=weights@agg(np.ones(len(g)));sa=weights@agg(aa);sr=weights@agg(rr);sar=weights@agg(aa*rr)
        mean_a=np.divide(sa,n,out=np.zeros(len(n)),where=n>0)
        numerator+=sar-mean_a*sr;denominator+=sa-mean_a*sa
    result['adjusted_AI_spread']=ratio(numerator,np.where(denominator>1e-12,denominator,0))
    return result

def analyse_frame(frame,stage):
    """Pure statistics entry point; synthetic data may be passed without any raw file access."""
    quarters=sorted(frame.quarter.unique());qn=len(quarters);assert qn>0
    weights=np.random.default_rng(SEED).multinomial(qn,np.full(qn,1/qn),size=BOOTSTRAPS)
    output={'stage':stage,'cost_bps':0,'released_cases':len(frame),'coverage_valid_cases':int(frame.valid_coverage.sum()),'excluded_cases':int((~frame.valid_coverage).sum()),'quarter_universe':quarters,'bootstrap_seed':SEED,'bootstrap_draws':BOOTSTRAPS,'hypothesis_family_size':2,'primary_statistic_family_size':4,'directions':{}}
    boot={}
    for direction in ['up','down']:
        allcases=frame[frame.direction==direction].sort_values(['t0','case']);g=allcases[allcases.valid_coverage].copy()
        if not len(allcases):continue
        aligned=g[g.AI_aligned];opposed=g[~g.AI_aligned];ma=g[g.MA20_control_selected]
        main=basic(aligned.gate_gross_pct);other=basic(opposed.gate_gross_pct)
        raw=main['mean_gross_pct']-other['mean_gross_pct'] if len(aligned) and len(opposed) else None
        fe=fixed_effects(g);bs=bootstrap_direction(g,quarters,weights)
        boot.update({direction+'__'+k:v for k,v in bs.items()})
        halves=[];half_ids=np.array_split(allcases.case.to_numpy(),2)
        for h,ids in enumerate(half_ids,1):
            sub=aligned[aligned.case.isin(ids)];halves.append({'half':h,'price_gate_cases':len(ids),**basic(sub.gate_gross_pct)})
        tail={}
        winners=aligned[aligned.gate_gross_pct>0].sort_values(['gate_gross_pct','case'],ascending=[False,True])
        for n in [1,3]:
            omitted=winners.case.iloc[:n].tolist();tail[str(n)]={'removed_cases':omitted,**basic(aligned[~aligned.case.isin(omitted)].gate_gross_pct)}
        d={'hypothesis':'SHORT_after_quiet_rally' if direction=='up' else 'LONG_after_quiet_decline','released_price_gates':len(allcases),'valid_price_gates':len(g),'aligned':main,'opposed':other,'price_only':basic(g.gate_gross_pct),'MA20_control':basic(ma.gate_gross_pct),'raw_aligned_minus_opposed_pct':raw,'fixed_effects':fe,'primary_aligned_mean_interval':bootstrap_interval(bs['aligned_mean']),'primary_adjusted_spread_interval':bootstrap_interval(bs['adjusted_AI_spread']),'raw_spread_interval':bootstrap_interval(bs['raw_aligned_minus_opposed']),'chronological_halves':halves,'remove_largest_winning_events':tail,'controls':{},'breakdowns':{}}
        for label,subset in [('aligned',aligned),('opposed',opposed),('price_only',g),('MA20',ma)]:
            d['controls'][label]={'trades':len(subset),'valid_gates':len(g),'per_gate_mean_pct':subset.gate_gross_pct.sum()/len(g) if len(g) else None,'conditional_mean_pct':subset.gate_gross_pct.mean() if len(subset) else None}
        for field in ['aligned_per_gate','opposed_per_gate','price_only_per_gate','MA20_per_gate','aligned_minus_price_per_gate','aligned_minus_MA20_per_gate']:
            d['controls'][field+'_interval']=bootstrap_interval(bs[field])
        for field in ['asset','year','quarter']:
            d['breakdowns'][field]={str(label):{'price_only':basic(sub.gate_gross_pct),'aligned':basic(sub[sub.AI_aligned].gate_gross_pct),'opposed':basic(sub[~sub.AI_aligned].gate_gross_pct)} for label,sub in g.groupby(field,sort=True)}
        screen={'at_least5_aligned':len(aligned)>=5,'at_least5_opposed':len(opposed)>=5,'positive_aligned_mean':main['mean_gross_pct'] is not None and main['mean_gross_pct']>0,'positive_raw_spread':raw is not None and raw>0}
        confirm={'aligned_mean_simultaneous_lower_positive':d['primary_aligned_mean_interval']['simultaneous98_75_one_sided_lower']>0,'adjusted_spread_simultaneous_lower_positive':d['primary_adjusted_spread_interval']['simultaneous98_75_one_sided_lower']>0,'at_least10_aligned_in_mixed_strata':fe['mixed_aligned_n']>=10,'at_least10_opposed_in_mixed_strata':fe['mixed_opposed_n']>=10,'aligned_positive_in_both_halves':all(x['mean_gross_pct'] is not None and x['mean_gross_pct']>0 for x in halves),'positive_after_removing_best3_winners':tail['3']['mean_gross_pct'] is not None and tail['3']['mean_gross_pct']>0}
        d['screen_criteria']=screen;d['screen_pass']=all(screen.values())
        d['confirmation_criteria']=confirm;d['confirmed']=stage=='confirmation' and all(confirm.values())
        d['claim_status']='screen_pass_not_confirmation' if stage=='screen' and d['screen_pass'] else ('screen_stop_not_statistical_falsification' if stage=='screen' else ('historical_conditional_hypothesis_confirmed' if d['confirmed'] else 'not_confirmed'))
        output['directions'][direction]=d
    return output,weights,boot

def load_release(run,stage):
    release_file=run/'score_release.json'
    if not release_file.is_file():raise RuntimeError('No score_release.json: post-entry prices remain sealed.')
    release=json.loads(release_file.read_text());assert release['stage']==stage,'Wrong released stage'
    for filename,key in [('manifest.json','manifest_sha256'),('accepted_decisions.jsonl','accepted_decisions_sha256'),('isolation_audit.json','isolation_audit_sha256'),('progress.json','progress_sha256')]:
        assert sha(run/filename)==release[key],f'Release hash mismatch: {filename}'
    manifest=json.loads((run/'manifest.json').read_text());cases=manifest['cases'];bycase={int(c['case']):c for c in cases}
    assert len(bycase)==len(cases)
    ids=sorted(map(int,release['case_ids']));assert len(ids)==len(set(ids))
    if stage=='screen':
        expected=sorted(int(c['case']) for c in cases if c['stage']=='screen')
        assert len(expected)==60 and all(sum(c['stage']=='screen' and c['direction']==d for c in cases)==30 for d in ['up','down'])
    else:
        continuation=json.loads((run/'screen'/'continuation.json').read_text())
        assert continuation['manifest_sha256']==release['manifest_sha256']
        expected=sorted(continuation['selected_confirmation_case_ids']);assert expected,'Screen authorized no confirmation'
    assert ids==expected,'Release does not match the complete frozen stage allocation'
    assert all(bycase[i]['stage']==stage for i in ids)
    records=[json.loads(x) for x in (run/'accepted_decisions.jsonl').read_text().splitlines() if x.strip()]
    assert len({r['case'] for r in records})==len(records) and len({r['thread_id'] for r in records})==len(records)
    audit=json.loads((run/'isolation_audit.json').read_text());progress=json.loads((run/'progress.json').read_text())
    assert audit['all_accepted_passed'] and audit['accepted']==len(records) and progress['accepted']==len(records)
    assert not progress['missing_requested_pairs'] and progress['status']=='decisions_collected'
    approved={r['agent_path'] for r in audit['audits'] if r['passed']}
    rec={r['case']:r for r in records};assert all(i in rec for i in ids)
    for i in ids:
        r=rec[i];assert r['agent_path'] in approved and r['model']=='gpt-5.6-terra' and r['reasoning_effort']=='medium' and not r['tool_calls']
        assert r['decision']['action'] in ['long','short']
    assert sha(manifest['protocol_file_absolute'])==manifest['protocol_sha256']
    assert sha(manifest['selection_plan_file_absolute'])==manifest['selection_plan_sha256']
    assert manifest['entry_delay_minutes']==30 and manifest['hold_minutes']==120 and manifest['primary_cost_bps']==0
    for i in ids:
        c=bycase[i];folder=Path(c['stimulus_dir'])
        for f,key in [('input.txt','input_sha256'),('stats.txt','prompt_sha256'),('chart.png','image_sha256')]:assert sha(folder/f)==c[key]
    budget=json.loads(Path(manifest['budget_file']).read_text());assert len(budget['reserved_attempts'])<=200
    assert sha(budget['old_budget_file_absolute'])==budget['old_budget_sha256']
    return manifest,[bycase[i] for i in ids],{i:rec[i] for i in ids},release,sha(release_file)

def native_trade_paths(cases):
    """Convert OHLC only for released120-minute grids; no unused-reserve payoff reads."""
    paths=np.full((len(cases),120,4),np.nan);hashes={}
    for asset in sorted({c['asset'] for c in cases}):
        file=ROOT/f'data/raw/intraday/{asset}_1m.csv.gz';hashes[str(file.relative_to(ROOT))]=sha(file)
        locations={}
        for i,c in enumerate(cases):
            if c['asset']!=asset:continue
            t0=stamp(c['t0']);entry=stamp(c['entry_time']);end=stamp(c['horizon_end'])
            assert entry==t0+pd.Timedelta(minutes=30) and end==t0+pd.Timedelta(minutes=150)
            for j,t in enumerate(pd.date_range(entry,periods=120,freq='min')):
                key=str(t);assert key not in locations,'Overlapping released trade intervals'
                locations[key]=(i,j)
        seen=set()
        with gzip.open(file,'rt',newline='') as handle:
            reader=csv.reader(handle);header=next(reader);ti=header.index('ts');cols=[header.index(x) for x in ['open','high','low','close']]
            for row in reader:
                key=row[ti].replace('T',' ').removesuffix('+00:00').removesuffix('Z')
                if key not in locations:continue
                assert key not in seen,'Duplicate minute in released grid';seen.add(key)
                i,j=locations[key]
                try:paths[i,j]=[float(row[k]) for k in cols]
                except (ValueError,IndexError):pass
    return paths,hashes

def build_ledger(cases,records,paths):
    rows=[]
    for i,c in enumerate(cases):
        p=paths[i];dec=records[c['case']]['decision'];side=-1 if c['direction']=='up' else 1
        complete=np.isfinite(p).all();positive=complete and bool((p>0).all())
        valid=positive and bool((p[:,1]>=p[:,[0,2,3]].max(1)).all()) and bool((p[:,2]<=p[:,[0,1,3]].min(1)).all())
        reason='none' if valid else ('missing_or_nonfinite_OHLC' if not complete else 'nonpositive_or_inconsistent_OHLC')
        ep=float(p[0,0]) if valid else None;xp=float(p[-1,3]) if valid else None
        gross=side*100*(xp/ep-1) if valid else np.nan
        if valid:
            mfe=max(0.,100*(p[:,1].max()/ep-1) if side==1 else 100*(1-p[:,2].min()/ep))
            mae=min(0.,100*(p[:,2].min()/ep-1) if side==1 else 100*(1-p[:,1].max()/ep))
        else:mfe=mae=np.nan
        t0=stamp(c['t0']);above=float(c['ma20_now'])<=100;aligned=dec['action']==('short' if side==-1 else 'long');ma=above if side==1 else not above
        rows.append({'case':int(c['case']),'stage':c['stage'],'direction':c['direction'],'asset':c['asset'],'window_id':c['window_id'],'t0':str(t0),'entry_time':str(stamp(c['entry_time'])),'horizon_end':str(stamp(c['horizon_end'])),'last_exit_bar_time':str(stamp(c['horizon_end'])-pd.Timedelta(minutes=1)),'year':t0.year,'quarter':str(t0.to_period('Q')),'trade_side':side,'AI_action':dec['action'],'AI_confidence':dec['confidence'],'AI_reason':dec['reason'],'AI_stop_pct':dec.get('stop_pct'),'AI_tp_pct':dec.get('tp_pct'),'ma20_now':float(c['ma20_now']),'above_equal_MA20':above,'AI_aligned':aligned,'MA20_control_selected':ma,'valid_coverage':valid,'exclusion':reason,'entry_price':ep,'exit_price':xp,'gate_gross_pct':gross,'AI_opportunity_gross_pct':gross if valid and aligned else (0. if valid else np.nan),'opposed_opportunity_gross_pct':gross if valid and not aligned else (0. if valid else np.nan),'MA20_opportunity_gross_pct':gross if valid and ma else (0. if valid else np.nan),'mfe_pct':mfe,'mae_pct':mae,'held_minutes':120 if valid else None,'thread_id':records[c['case']]['thread_id']})
    frame=pd.DataFrame(rows);assert frame.case.is_unique
    assert pd.to_datetime(frame.t0).dt.normalize().is_unique,'Protocol requires one global event per UTC day'
    return frame

def continuation(summary,manifest,manifest_hash):
    passed=[d for d in ['up','down'] if summary['directions'][d]['screen_pass']]
    number=60 if len(passed)==2 else (120 if len(passed)==1 else 0)
    chosen={}
    for d in passed:
        options=sorted([c for c in manifest['cases'] if c['stage']=='confirmation' and c['direction']==d],key=lambda c:int(c['confirmation_rank']))
        assert [int(c['confirmation_rank']) for c in options]==list(range(1,len(options)+1))
        assert len(options)>=number,'Frozen protocol needs more reserved confirmation cases; no silent fallback'
        chosen[d]=[int(c['case']) for c in options[:number]]
    return {'stage':'screen','screen_is_noninferential':True,'manifest_sha256':manifest_hash,'passing_directions':passed,'cases_per_passing_direction':number,'selected_confirmation_by_direction':chosen,'selected_confirmation_case_ids':sorted(i for ids in chosen.values() for i in ids),'decision':'continue_fixed_confirmation' if passed else 'stop_preserve_unused_attempts','new_calls_launched_by_scorer':0}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',required=True,choices=['screen','confirmation']);parser.add_argument('--run-dir');args=parser.parse_args()
    run=Path(args.run_dir or json.loads((HERE/'run.json').read_text())['run_dir']).resolve()
    manifest,cases,records,release,release_hash=load_release(run,args.stage)
    # No post-entry OHLC conversion occurs before every guard above succeeds.
    paths,native_hashes=native_trade_paths(cases)
    for path,expected in native_hashes.items():assert expected==manifest['original_sha256'][path]
    frame=build_ledger(cases,records,paths);summary,weights,boot=analyse_frame(frame,args.stage)
    summary['run_id']=manifest['run_id'];summary['score_release_sha256']=release_hash
    out=run/args.stage;out.mkdir(exist_ok=True)
    auditfile=out/'scoring_audit.json'
    if auditfile.exists():assert json.loads(auditfile.read_text())['score_release_sha256']==release_hash,'Do not overwrite results from a different release'
    frame.to_csv(out/'trade_ledger.csv',index=False)
    (out/'trade_ledger.jsonl').write_text(''.join(json.dumps(clean(row),allow_nan=False)+'\n' for row in frame.to_dict('records')))
    save(out/'summary.json',summary)
    np.savez_compressed(out/'paths.npz',paths=paths,case=frame.case.to_numpy(),window_id=frame.window_id.to_numpy(str),columns=np.array(['open','high','low','close']))
    np.savez_compressed(out/'bootstrap_arrays.npz',quarter_weights=weights,quarters=np.array(summary['quarter_universe']),**boot)
    if args.stage=='screen':save(out/'continuation.json',continuation(summary,manifest,release['manifest_sha256']))
    audit={'passed':True,'stage':args.stage,'score_release_sha256':release_hash,'release':release,'released_cases':frame.case.tolist(),'valid_cases':int(frame.valid_coverage.sum()),'coverage_exclusions':frame.loc[~frame.valid_coverage,['case','exclusion']].to_dict('records'),'native_source_sha256':native_hashes,'source_code_sha256':sha(Path(__file__)),'protocol_sha256':manifest['protocol_sha256'],'quarter_universe_includes_all_released_cases':True,'unused_reserves_not_scored':True,'no_calls_made':True,'old_budget_hash_checked':True,'undefined_bootstrap_lower_bounds_minus_infinity':True,'all_hashes_still_match':all(sha(run/f)==release[k] for f,k in [('manifest.json','manifest_sha256'),('accepted_decisions.jsonl','accepted_decisions_sha256'),('isolation_audit.json','isolation_audit_sha256'),('progress.json','progress_sha256')])}
    assert audit['all_hashes_still_match'];save(auditfile,audit)
    print(json.dumps(clean({'run_id':manifest['run_id'],'stage':args.stage,'valid_cases':audit['valid_cases'],'directions':{d:{'aligned_n':r['aligned']['n'],'mean_pct':r['aligned']['mean_gross_pct'],'FE_spread_pct':r['fixed_effects']['adjusted_aligned_minus_opposed_pct'],'screen_pass':r['screen_pass'],'confirmed':r['confirmed']} for d,r in summary['directions'].items()}}),indent=2))

if __name__=='__main__':main()
