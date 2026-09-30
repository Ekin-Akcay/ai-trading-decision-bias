"""Evaluate only the sealed, frozen two-rule gross-return study."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'data/analysis/reversal-deep-20260929/risk'))
from validation_engine import bracket_batch

def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,(np.bool_,)):return bool(x)
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.floating,float)):return float(x) if np.isfinite(x) else None
    return x

def save(p,x):p.write_text(json.dumps(clean(x),indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def stats(v):
    v=np.asarray(v,float);v=v[np.isfinite(v)];n=len(v)
    if not n:return {'n':0}
    ordered=np.sort(v)
    return {'n':n,'mean_gross_pct':v.mean(),'median_gross_pct':np.median(v),'gross_sum_pct':v.sum(),'wins':int((v>0).sum()),'win_rate':(v>0).mean(),
            'mean_winner_pct':v[v>0].mean() if (v>0).any() else None,'mean_loser_pct':v[v<0].mean() if (v<0).any() else None,
            'profit_factor':v[v>0].sum()/-v[v<0].sum() if (v<0).any() else None,'best_pct':v.max(),'worst_pct':v.min(),
            'exclude_best1_mean_pct':ordered[:-1].mean() if n>1 else None,'exclude_best3_mean_pct':ordered[:-3].mean() if n>3 else None,
            'break_even_roundtrip_bps':v.mean()*100}

def aggregate(values,groups,count=None):
    n=int(groups.max())+1
    if count is None:return np.bincount(groups,weights=values,minlength=n)
    out=np.zeros((n,count));np.add.at(out,groups,values);return out

def boot_for_rule(values,selected,eligible,groups,strata,weights):
    """Whole-group resampling; re-estimate selected-stratum standardized control."""
    ng=weights.shape[1];ns=int(strata.max())+1
    a=np.zeros((ng,ns));b=np.zeros_like(a);c=np.zeros_like(a)
    np.add.at(a,(groups,strata),selected.astype(float))
    np.add.at(b,(groups,strata),eligible.astype(float))
    np.add.at(c,(groups,strata),np.where(eligible,values,0))
    numerator=np.bincount(groups,weights=np.where(selected,values,0),minlength=ng)
    denominator=a.sum(1)
    sel_n=weights@denominator
    mean=np.divide(weights@numerator,sel_n,out=np.full(len(weights),np.nan),where=sel_n>0)
    sa=weights@a;eb=weights@b;ec=weights@c
    ebmean=np.divide(ec,eb,out=np.zeros_like(ec),where=eb>0)
    base=np.divide((sa*ebmean).sum(1),sel_n,out=np.full(len(weights),np.nan),where=sel_n>0)
    def interval(x):
        z=x[np.isfinite(x)]
        if not len(z):return {'ci95':np.array([np.nan,np.nan]),'simultaneous97_5':np.array([np.nan,np.nan]),'valid_resamples':0}
        return {'ci95':np.quantile(z,[.025,.975]),'simultaneous97_5':np.quantile(z,[.0125,.9875]),'valid_resamples':len(z)}
    original_sel=a.sum(0);original_eligible=b.sum(0);original_sum=c.sum(0)
    sm=np.divide(original_sum,original_eligible,out=np.zeros(ns),where=original_eligible>0)
    baseline=(original_sel*sm).sum()/original_sel.sum() if original_sel.sum() else np.nan
    strata_rows=[{'stratum_code':s,'selected':int(original_sel[s]),'eligible':int(original_eligible[s]),'nonselected':int(original_eligible[s]-original_sel[s]),'control_mean_gross_pct':sm[s]} for s in range(ns) if original_eligible[s]>0]
    return {'profit':interval(mean),'AI_increment':interval(mean-base),'standardized_price_baseline_mean_pct':baseline,
            'AI_increment_mean_pct':values[selected].mean()-baseline if selected.any() else np.nan,'strata':strata_rows,
            'strata_with_selected_and_nonselected':sum(r['selected']>0 and r['nonselected']>0 for r in strata_rows)},mean,mean-base

def main():
    run=Path(json.loads((HERE/'run.json').read_text())['run_dir'])
    assert (run/'ALLOW_EVALUATION').exists(), 'Forward outcomes remain sealed'
    m=json.loads((run/'manifest.json').read_text())
    assert sha(ROOT/m['protocol_file'])==m['protocol_sha256']
    assert all(sha(ROOT/p)==h for p,h in m['original_sha256'].items()), 'Frozen source changed before scoring'
    for c in m['cases']:
        folder=Path(c['stimulus_dir'])
        assert sha(folder/'stats.txt')==c['prompt_sha256']
        assert sha(folder/'input.txt')==c['input_sha256']
        assert sha(folder/'chart.png')==c['image_sha256']
    dec=[json.loads(s) for s in (run/'accepted_decisions.jsonl').read_text().splitlines()]
    assert len(dec)==m['planned_decisions']
    audit=json.loads((run/'isolation_audit.json').read_text());assert audit['all_accepted_passed'] and audit['accepted']==len(dec)
    passed={a['agent_path'] for a in audit['audits'] if a['passed']}
    assert all(r['agent_path'] in passed for r in dec)
    d=pd.DataFrame(m['cases']).sort_values('case').reset_index(drop=True)
    dd={x['case']:x['decision'] for x in dec};assert len(dd)==len(d)
    for col in ['action','stop_pct','tp_pct','confidence','reason']:d[col]=[dd[c][col] for c in d.case]
    d['entry_time']=pd.to_datetime(d.entry_time)
    paths=np.empty((len(d),361,4));coverage=[]
    for asset in d.asset.unique():
        px=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_1m.csv.gz',index_col=0,parse_dates=True).sort_index()
        assert px.index.is_unique
        for i,row in d[d.asset==asset].iterrows():
            q=int(px.index.searchsorted(row.entry_time));part=px.iloc[q-1:q+360]
            assert part.index.equals(pd.date_range(row.entry_time-pd.Timedelta(minutes=1),periods=361,freq='min'))
            arr=part[['open','high','low','close']].to_numpy(float);assert np.isfinite(arr).all() and (arr>0).all()
            assert np.isclose(arr[0,3],row.price_real,atol=1e-8,rtol=0)
            paths[i]=arr;coverage.append({'case':int(row.case),'native_minute_count':361,'last_visible_close_matches':True})
    np.savez_compressed(run/'paths.npz',paths=paths,case=d.case.to_numpy(),window_id=d.window_id.to_numpy(dtype=str))
    d['above_both']=(d.ma20_now<=100)&(d.ma50_now<=100)
    d['below_both']=(d.ma20_now>=100)&(d.ma50_now>=100)
    d['ma_regime']=np.where(d.above_both,'above_both',np.where(d.below_both,'below_both','mixed'))
    d['era']=np.where(d.entry_time.dt.year<=2021,'2020-21',np.where(d.entry_time.dt.year<=2023,'2022-23','2024-26'))
    d['stratum']=d.asset+'|'+d.era+'|'+d.ma_regime
    strata,labels=pd.factorize(d.stratum,sort=True)
    blocks,block_labels=pd.factorize(d.block,sort=True)
    quarters,quarter_labels=pd.factorize(d.entry_time.dt.to_period('Q').astype(str),sort=True)
    rng=np.random.default_rng(2026092951);bw=rng.multinomial(len(block_labels),np.repeat(1/len(block_labels),len(block_labels)),size=20000)
    rng=np.random.default_rng(2026092952);qw=rng.multinomial(len(quarter_labels),np.repeat(1/len(quarter_labels),len(quarter_labels)),size=20000)
    rules={};ledgers=[];summaries={};boot_arrays={}
    for name in ['L048','S508']:
        if name=='L048':
            eligible=d.macro_both_down.to_numpy(bool);selected=eligible&(d.action=='short').to_numpy();sign=1
            ep=paths[:,1,0];xp=paths[:,240,3];values=(xp/ep-1)*100
            outputs={'entry_price':ep,'exit_price':xp,'exit_index':np.full(len(d),240),'held_minutes':np.full(len(d),240),'outcome':np.repeat('timeout',len(d)),'ambiguous':np.zeros(len(d),bool),'gap':np.zeros(len(d),bool)}
            delays={str(k):(paths[:,240,3]/paths[:,k+1,0]-1)*100 for k in [1,5]}
        else:
            eligible=d.above_both.to_numpy(bool);selected=eligible&(d.action=='long').to_numpy();sign=-1
            outputs=bracket_batch(paths,2*d.atr14_pct.to_numpy(),sign=-1,rr=1,horizon=240,delay=0)
            ep=outputs['entry_price'];xp=outputs['exit_price'];values=outputs['gross_pct']
            delays={str(k):bracket_batch(paths,2*d.atr14_pct.to_numpy(),sign=-1,rr=1,horizon=240,delay=k)['gross_pct'] for k in [1,5]}
        rules[name]={'eligible':eligible,'selected':selected,'gross_pct':values}
        bi,bmean,bdelta=boot_for_rule(values,selected,eligible,blocks,strata,bw)
        qi,qmean,qdelta=boot_for_rule(values,selected,eligible,quarters,strata,qw)
        boot_arrays[name+'_mean_block']=bmean;boot_arrays[name+'_increment_block']=bdelta
        boot_arrays[name+'_mean_quarter']=qmean;boot_arrays[name+'_increment_quarter']=qdelta
        dates=d[['block','entry_time']].drop_duplicates().sort_values('entry_time').block.to_numpy()
        halves=[stats(values[selected&d.block.isin(part).to_numpy()]) for part in np.array_split(dates,2)]
        thirds=[stats(values[selected&d.block.isin(part).to_numpy()]) for part in np.array_split(dates,3)]
        leave_assets={a:stats(values[selected&(d.asset!=a).to_numpy()]) for a in d.asset.unique()}
        delay_stats={k:stats(v[selected]) for k,v in delays.items()}
        selected_blocks=int(d.loc[selected,'block'].nunique())
        criteria={'at_least50trades':int(selected.sum())>=50,'at_least30blocks':selected_blocks>=30,'block_simultaneous_profit_lower_positive':bi['profit']['simultaneous97_5'][0]>0,
                  'quarter95_profit_lower_positive':qi['profit']['ci95'][0]>0,'both_delays_positive':all(v.get('mean_gross_pct',-np.inf)>0 for v in delay_stats.values()),
                  'both_chrono_halves_positive':all(v.get('mean_gross_pct',-np.inf)>0 for v in halves)}
        ai_criteria={'block_simultaneous_increment_lower_positive':bi['AI_increment']['simultaneous97_5'][0]>0,'quarter95_increment_lower_positive':qi['AI_increment']['ci95'][0]>0}
        summary={'selected':stats(values[selected]),'selected_blocks':selected_blocks,'eligible_price_only':stats(values[eligible]),'complementary_AI_group':stats(values[eligible&~selected]),
                 'opportunity_mean_gross_pct':np.where(selected,values,0).mean(),'block_inference':bi,'quarter_inference':qi,'delay_sensitivities':delay_stats,'chronological_halves':halves,'chronological_thirds':thirds,
                 'assets':{a:stats(values[selected&(d.asset==a).to_numpy()]) for a in d.asset.unique()},'leave_one_asset_out':leave_assets,'profit_criteria':criteria,'profit_verified':all(criteria.values()),
                 'AI_contribution_criteria':ai_criteria,'AI_contribution_verified':all(ai_criteria.values()),'broad_cross_asset_verified':all(criteria.values()) and all(v.get('mean_gross_pct',-np.inf)>0 for v in leave_assets.values())}
        if name=='L048':
            summary['additional_belowMA20_price_control']=stats(values[eligible&(d.ma20_now>100).to_numpy()])
            summary['same_selected_AI_direction']=stats(-values[selected])
        else:
            follow=bracket_batch(paths,2*d.atr14_pct.to_numpy(),sign=1,rr=1,horizon=240,delay=0)
            summary['same_selected_AI_direction']=stats(follow['gross_pct'][selected])
        for i,row in d.iterrows():
            end=int(outputs['exit_index'][i]);slice_=paths[i,1:end+1]
            # Entry-to-exit-bar extrema, including the complete last minute: exact intraminute exit time is unavailable.
            mfe=max(0.,(slice_[:,1].max()/ep[i]-1)*100 if sign==1 else (1-slice_[:,2].min()/ep[i])*100)
            mae=min(0.,(slice_[:,2].min()/ep[i]-1)*100 if sign==1 else (1-slice_[:,1].max()/ep[i])*100)
            record={'rule':name,'case':int(row.case),'block':int(row.block),'asset':row.asset,'window_id':row.window_id,'entry_time':str(row.entry_time),'AI_action':row.action,
                    'eligible':bool(eligible[i]),'selected':bool(selected[i]),'direction':'long' if sign==1 else 'short','entry_price':ep[i],'exit_price':xp[i],'gross_pct':values[i],
                    'net_at_zero_cost_pct':values[i],'outcome':str(outputs['outcome'][i]),'held_minutes':int(outputs['held_minutes'][i]),'exit_minute_index':end,'ambiguous':bool(outputs['ambiguous'][i]),'gap':bool(outputs['gap'][i]),
                    'entry_delay1_gross_pct':delays['1'][i],'entry_delay5_gross_pct':delays['5'][i],'mfe_through_exit_bar_pct':mfe,'mae_through_exit_bar_pct':mae}
            for h in [15,30,60,105,240]:record[f'scheduled_direction_move_{h}m_pct']=sign*(paths[i,h,3]/ep[i]-1)*100
            ledgers.append(record)
        summaries[name]=summary
    assert not np.any(rules['L048']['selected']&rules['S508']['selected'])
    basket=np.zeros(len(d))
    for r in rules.values():basket+=np.where(r['selected'],r['gross_pct'],0)
    portfolio=pd.DataFrame({'block':d.block,'entry_time':d.entry_time,'gross_pct':basket}).groupby('block').agg(entry_time=('entry_time','first'),basket_return_pct=('gross_pct','mean')).sort_values('entry_time')
    portfolio['equity']=np.cumprod(1+portfolio.basket_return_pct.to_numpy()/100)
    portfolio['drawdown_pct']=(portfolio.equity/np.maximum.accumulate(np.r_[1,portfolio.equity.to_numpy()])[1:]-1)*100
    portfolio.to_csv(run/'sampled_basket.csv')
    secondary={}
    s179=bracket_batch(paths,np.ones(len(d)),sign=-1,rr=1.5,horizon=105)
    mask=(d.action=='long').to_numpy();secondary['S179_fixed_percent']={'selected':stats(s179['gross_pct'][mask]),'control':stats(s179['gross_pct'])}
    former=(paths[:,255,3]/paths[:,16,0]-1)*100;eligible=paths[:,15,3]>paths[:,0,3];mask=eligible&(d.action=='short').to_numpy()
    secondary['former_L_confirm15_hold240']={'selected':stats(former[mask]),'control':stats(former[eligible])}
    pd.DataFrame(ledgers).to_csv(run/'strategy_trades.csv',index=False)
    (run/'strategy_trades.jsonl').write_text(''.join(json.dumps(clean(x))+'\n' for x in ledgers))
    d.to_csv(run/'window_results.csv',index=False)
    np.savez_compressed(run/'bootstrap_arrays.npz',**boot_arrays,block_weights=bw,quarter_weights=qw,stratum_labels=np.asarray(labels,dtype=str))
    preservation={p:sha(ROOT/p)==h for p,h in m['original_sha256'].items()}
    assert all(preservation.values()), 'Frozen source changed during scoring'
    save(run/'summary.json',{'phase':'fresh_target_gross_validation','run_id':m['run_id'],'snapshots':len(d),'calendar_blocks':len(block_labels),'quarters':len(quarter_labels),'cost_bps':0,'rules':summaries,
                            'combined_sampled_basket':{'final_return_pct':(portfolio.equity.iloc[-1]-1)*100,'maximum_drawdown_pct':portfolio.drawdown_pct.min(),'block_stats':stats(portfolio.basket_return_pct),'interpretation':'Sparse sampled equal-quarter-notional basket; not annualized or continuously deployed'},
                            'secondary_only':secondary,'AI_actions_by_asset':pd.crosstab(d.asset,d.action).to_dict(),'AI_actions_by_MA_regime':pd.crosstab(d.ma_regime,d.action).to_dict(),
                            'stratum_labels':dict(enumerate(labels)),'sources_preserved':preservation})
    save(run/'evaluation_audit.json',{'full_forward_rows_checked':len(coverage),'minute_bars_per_window':361,'native_coverage':coverage,'protocol_hash_verified':True,'costs_exactly_zero':True,'overlapping_L_S_positions':0,'original_model_decisions_unchanged':True})
    print(json.dumps(clean({k:{'selected':v['selected'],'profit_verified':v['profit_verified'],'AI_contribution_verified':v['AI_contribution_verified']} for k,v in summaries.items()}),indent=2))

if __name__=='__main__':main()
