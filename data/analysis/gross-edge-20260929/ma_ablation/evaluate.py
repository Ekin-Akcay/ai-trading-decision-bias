"""Frozen paired MA-intervention evaluator. No loading of new prices before release."""
from pathlib import Path
import sys,json,hashlib,math,importlib.util
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('gross_helpers',HERE.parent/'evaluate.py');common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)
stats,save,clean=common.stats,common.save,common.clean
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def interval(v):
    v=np.asarray(v);v=v[np.isfinite(v)]
    return {k:np.quantile(v,q).tolist() if len(v) else [None,None] for k,q in [('ci95',[.025,.975]),('ci99',[.005,.995])]}

def main():
    run=Path(json.loads((HERE/'run.json').read_text())['run_dir']);assert (run/'ALLOW_EVALUATION').exists()
    m=json.loads((run/'manifest.json').read_text());assert sha(ROOT/m['protocol_file'])==m['protocol_sha256']
    assert all(sha(ROOT/p)==h for p,h in m['original_sha256'].items())
    rows=[json.loads(s) for s in (run/'accepted_decisions.jsonl').read_text().splitlines()];assert len(rows)==270 and len({r['thread_id'] for r in rows})==270
    audit=json.loads((run/'isolation_audit.json').read_text());passed={a['agent_path'] for a in audit['audits'] if a['passed']};assert all(r['agent_path'] in passed and not r['tool_calls'] for r in rows)
    decisions={r['case']:r['decision'] for r in rows};cases=pd.DataFrame(m['cases']).sort_values('case')
    for c in m['cases']:
        folder=Path(c['stimulus_dir'])
        for name,key in [('stats.txt','prompt_sha256'),('input.txt','input_sha256'),('chart.png','image_sha256')]:assert sha(folder/name)==c[key]
    for col in ['action','confidence','reason','stop_pct','tp_pct']:cases[col]=[decisions[c][col] for c in cases.case]
    assert cases.case.nunique()==270 and not cases.duplicated(['block','arm']).any()
    assert set(cases.action).issubset({'long','short'})
    d=cases[cases.arm=='MA_A'].sort_values('block').reset_index(drop=True);assert len(d)==90 and d.block.nunique()==90
    d['entry_time']=pd.to_datetime(d.entry_time);actions={a:cases[cases.arm==a].sort_values('block').action.to_numpy() for a in ['MA_A','MA_B','NO_MA']}
    for a in actions:assert cases[cases.arm==a].sort_values('block').window_id.tolist()==d.window_id.tolist()
    minute=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index();paths=[]
    for _,r in d.iterrows():
        q=int(minute.index.searchsorted(r.entry_time));part=minute.iloc[q-1:q+360];assert part.index.equals(pd.date_range(r.entry_time-pd.Timedelta(minutes=1),periods=361,freq='min'))
        p=part[['open','high','low','close']].to_numpy(float);assert np.isfinite(p).all() and (p>0).all() and abs(p[0,3]-r.price_real)<1e-8;paths.append(p)
    paths=np.asarray(paths);np.savez_compressed(run/'paths.npz',paths=paths,block=d.block.to_numpy())
    values=(paths[:,240,3]/paths[:,1,0]-1)*100;delays={k:(paths[:,240,3]/paths[:,k+1,0]-1)*100 for k in [1,5]}
    sol=pd.read_csv(ROOT/'data/raw/SOL-USD.csv',index_col=0,parse_dates=True).sort_index();btc=pd.read_csv(ROOT/'data/raw/BTC-USD.csv',index_col=0,parse_dates=True).sort_index()
    sol['sma']=sol.close.rolling(50).mean();btc['sma']=btc.close.rolling(200).mean();days=d.entry_time.dt.normalize()-pd.Timedelta(days=1)
    assert (sol.reindex(days).close<=sol.reindex(days).sma).all() and (btc.reindex(days).close<=btc.reindex(days).sma).all()
    d['ma_regime']=np.where((d.ma20_now<=100)&(d.ma50_now<=100),'above_both',np.where((d.ma20_now>=100)&(d.ma50_now>=100),'below_both','mixed'))
    d['era']=np.where(d.entry_time.dt.year<=2021,'2020-21',np.where(d.entry_time.dt.year<=2023,'2022-23','2024-26'))
    strata,labels=pd.factorize(d.era+'|'+d.ma_regime,sort=True);quarter,qlabels=pd.factorize(d.entry_time.dt.to_period('Q').astype(str),sort=True)
    rng=np.random.default_rng(2026092997);weights=rng.multinomial(90,np.repeat(1/90,90),size=20000)
    rng=np.random.default_rng(2026092998);qweights=rng.multinomial(len(qlabels),np.repeat(1/len(qlabels),len(qlabels)),size=20000)
    chronological=np.argsort(d.entry_time.to_numpy());eligible=np.ones(90,bool);groups=np.arange(90);result={};vectors={};ledgers=[]
    for arm in actions:
        selected=actions[arm]=='short';opportunity=np.where(selected,values,0)
        bi,bmean,binc=common.boot_for_rule(values,selected,eligible,groups,strata,weights)
        qi,qmean,qinc=common.boot_for_rule(values,selected,eligible,quarter,strata,qweights)
        halves=[stats(values[ids[selected[ids]]]) for ids in np.array_split(chronological,2)]
        thirds=[stats(values[ids[selected[ids]]]) for ids in np.array_split(chronological,3)]
        s=stats(values[selected]);di={str(k):stats(v[selected]) for k,v in delays.items()}
        pcriteria={'at_least50trades':int(selected.sum())>=50,'window99_lower_positive':interval(bmean)['ci99'][0]>0 if selected.any() else False,
                   'quarter95_lower_positive':interval(qmean)['ci95'][0]>0 if selected.any() else False,'both_halves_positive':all(x.get('mean_gross_pct',-np.inf)>0 for x in halves),
                   'both_delays_positive':all(x.get('mean_gross_pct',-np.inf)>0 for x in di.values()),'remove_best3_positive':(s.get('exclude_best3_mean_pct') or 0)>0}
        icriteria={'window99_increment_lower_positive':interval(binc)['ci99'][0]>0 if selected.any() else False,'quarter95_increment_lower_positive':interval(qinc)['ci95'][0]>0 if selected.any() else False}
        qsum=np.bincount(quarter,weights=opportunity,minlength=len(qlabels));qn=np.bincount(quarter,minlength=len(qlabels));oppboot=weights@opportunity/90;qoppboot=(qweights@qsum)/(qweights@qn)
        result[arm]={'role':'primary_profit_replication' if arm=='MA_A' else 'repeat_diagnostic' if arm=='MA_B' else 'MA_input_intervention',
                     'selected':s,'short_calls':int(selected.sum()),'long_calls':int((~selected).sum()),'opportunity':stats(opportunity),
                     'window_profit_intervals':interval(bmean),'quarter_profit_intervals':interval(qmean),'window_increment_intervals':interval(binc),'quarter_increment_intervals':interval(qinc),
                     'standardized_price_baseline_mean_pct':bi['standardized_price_baseline_mean_pct'],'AI_increment_mean_pct':bi['AI_increment_mean_pct'],
                     'price_only_control':stats(values),'below_MA20_price_only_control':stats(values[(d.ma20_now>100).to_numpy()]),'strata':bi['strata'],'strata_with_contrast':bi['strata_with_selected_and_nonselected'],
                     'delays':di,'chronological_halves':halves,'chronological_thirds':thirds,
                     'quarters':{str(q):stats(values[selected&(quarter==j)]) for j,q in enumerate(qlabels)},
                     'profit_criteria':pcriteria,'profit_verified':arm=='MA_A' and all(pcriteria.values()),
                     'AI_increment_criteria':icriteria,'AI_increment_verified':arm=='MA_A' and all(icriteria.values()),'opportunity_intervals':interval(oppboot),'quarter_opportunity_intervals':interval(qoppboot)}
        vectors[arm+'_mean']=bmean;vectors[arm+'_increment']=binc;vectors[arm+'_qmean']=qmean;vectors[arm+'_qincrement']=qinc;vectors[arm+'_opportunity']=opportunity
        for i,r in d.iterrows():
            case=cases[(cases.block==r.block)&(cases.arm==arm)].iloc[0]
            row={'block':int(r.block),'case':int(case.case),'arm':arm,'window_id':r.window_id,'asset':'SOL-USD','entry_time':str(r.entry_time),'AI_action':actions[arm][i],
                 'reason':case.reason,'confidence':float(case.confidence),'selected':bool(selected[i]),'entry_price':paths[i,1,0],'exit_price':paths[i,240,3],
                 'gross_pct':values[i],'opportunity_gross_pct':opportunity[i],'delay1_gross_pct':delays[1][i],'delay5_gross_pct':delays[5][i],
                 'mae_pct':min(0.,(paths[i,1:241,2].min()/paths[i,1,0]-1)*100),'mfe_pct':max(0.,(paths[i,1:241,1].max()/paths[i,1,0]-1)*100)}
            for h in [15,30,60,105,240]:row[f'long_move_{h}m_pct']=(paths[i,h,3]/paths[i,1,0]-1)*100
            ledgers.append(row)
    treatment=actions['NO_MA']!=actions['MA_A'];repeat=actions['MA_B']!=actions['MA_A'];b=int((treatment&~repeat).sum());c=int((~treatment&repeat).sum());nd=b+c
    p=sum(math.comb(nd,k) for k in range(b,nd+1))/(2**nd) if nd else 1.
    delta=treatment.astype(int)-repeat.astype(int);delta_boot=weights@delta/90
    signed=(actions['MA_A']=='short').astype(int)-(actions['NO_MA']=='short').astype(int)
    mechanism={'treatment_flips':int(treatment.sum()),'ordinary_repeat_flips':int(repeat.sum()),'treatment_flip_rate':treatment.mean(),'ordinary_flip_rate':repeat.mean(),'excess_flip_rate':delta.mean(),
               'excess_flip_rate_intervals':interval(delta_boot),'discordant_treatment_only':b,'discordant_repeat_only':c,'exact_one_sided_p':p,'threshold':.01,'MA_information_dependence_verified':p<.01 and delta.mean()>0,
               'short_frequency_reduction_NO_MA_vs_A':signed.mean(),'short_reduction_intervals':interval(weights@signed/90),
               'contingency':pd.DataFrame(actions).value_counts().rename('n').reset_index().to_dict('records')}
    comparisons={}
    for arm in ['MA_B','NO_MA']:
        diff=vectors[arm+'_opportunity']-vectors['MA_A_opportunity'];qsum=np.bincount(quarter,weights=diff,minlength=len(qlabels));qn=np.bincount(quarter,minlength=len(qlabels))
        comparisons[arm+'_minus_MA_A']={'mean_per_opportunity_difference_pct':diff.mean(),'window_intervals':interval(weights@diff/90),'quarter_intervals':interval((qweights@qsum)/(qweights@qn)),'secondary_only':True}
    pd.DataFrame(ledgers).to_csv(run/'strategy_trades.csv',index=False);(run/'strategy_trades.jsonl').write_text(''.join(json.dumps(clean(x))+'\n' for x in ledgers));cases.to_csv(run/'window_results.csv',index=False)
    d['long240_gross_pct']=values;d.to_csv(run/'paired_windows.csv',index=False)
    save(run/'summary.json',{'run_id':m['run_id'],'unique_windows':90,'decisions':270,'quarters':len(qlabels),'cost_bps':0,'arms':result,'mechanism':mechanism,'secondary_per_opportunity_comparisons':comparisons,'stratum_labels':dict(enumerate(labels))})
    np.savez_compressed(run/'bootstrap_arrays.npz',**vectors,weights=weights,quarter_weights=qweights,mechanism_delta_boot=delta_boot)
    preserved={p:sha(ROOT/p)==h for p,h in m['original_sha256'].items()};assert all(preserved.values())
    save(run/'evaluation_audit.json',{'unique_windows':90,'audited_decisions':270,'native_minute_rows':90*361,'all_daily_gates_passed':True,'all_stimulus_hashes_passed':True,'sources_preserved':preserved})
    print(json.dumps(clean({'arms':{k:{'selected':v['selected'],'profit_verified':v['profit_verified'],'AI_increment_verified':v['AI_increment_verified']} for k,v in result.items()},'mechanism':mechanism}),indent=2))

if __name__=='__main__':main()
