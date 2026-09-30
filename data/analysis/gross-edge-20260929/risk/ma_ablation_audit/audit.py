"""Dormant independent payoff/report audit. No fresh forward reads without release."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
RUN_ID='ma-ablation-sol90-20260929T210853Z'
ARMS=['MA_A','MA_B','NO_MA']

def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,np.bool_):return bool(x)
    if isinstance(x,np.integer):return int(x)
    if isinstance(x,(np.floating,float)):return float(x) if np.isfinite(x) else None
    return x

def metrics(x):
    x=np.asarray(x,float);n=len(x)
    if not n:return {'n':0}
    order=np.sort(x);pos=x[x>0];neg=x[x<0]
    win=pos.mean() if len(pos) else np.nan;loss=-neg.mean() if len(neg) else np.nan
    return {'n':n,'mean_gross_pct':x.mean(),'median_gross_pct':np.median(x),'gross_sum_pct':x.sum(),'wins':int((x>0).sum()),'win_rate':(x>0).mean(),
        'mean_winner_pct':win,'mean_loser_pct':-loss,'profit_factor':pos.sum()/-neg.sum() if len(neg) else np.nan,
        'best_pct':x.max(),'worst_pct':x.min(),'exclude_best1_mean_pct':order[:-1].mean() if n>1 else np.nan,
        'exclude_best3_mean_pct':order[:-3].mean() if n>3 else np.nan,'break_even_roundtrip_bps':x.mean()*100,
        'breakeven_win_rate_at_observed_payouts':loss/(loss+win) if len(pos) and len(neg) else np.nan,
        'top3_trade_sum_pct':order[-3:].sum(),'top3_share_of_total_trade_sum':order[-3:].sum()/x.sum() if x.sum()!=0 else np.nan}

def interval(x):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    return {'ci95':np.quantile(x,[.025,.975]) if len(x) else [None,None],
        'ci99':np.quantile(x,[.005,.995]) if len(x) else [None,None]}

def favorable_lower(x,level):
    lo=x[level][0];return lo is not None and np.isfinite(lo) and lo>0

def selftest():
    x=np.array([3.,-2.,1.,-1.]);a=np.array([True,True,False,False]);b=np.array([False,True,True,False])
    ao=np.where(a,x,0);bo=np.where(b,x,0)
    assert metrics(x[a])['mean_gross_pct']==.5 and metrics(ao)['mean_gross_pct']==.25
    assert (bo-ao).mean()==-.5 and x[b].mean()==-.5
    assert metrics(x)['exclude_best3_mean_pct']==-2
    assert metrics(np.array([0.,0.]))['win_rate']==0
    assert not favorable_lower({'ci95':[None,None]},'ci95')
    # Whole-quarter means use sampled opportunity counts, not equal-quarter means.
    nums=np.array([4.,-2.]);den=np.array([2,1]);w=np.array([1,2])
    assert (w@nums)/(w@den)==0
    print('PASS: synthetic skip/denominator/tail arithmetic; no fresh files opened')

def main(release):
    assert release==RUN_ID,'Explicit matching root release is required'
    run=ROOT/'data/sim'/RUN_ID
    assert (run/'ALLOW_EVALUATION').exists(),'Fresh economic data remain sealed'
    accepted=[json.loads(x) for x in (run/'accepted_decisions.jsonl').read_text().splitlines()]
    assert len(accepted)==270 and len({x['thread_id'] for x in accepted})==270
    isolation=json.loads((run/'isolation_audit.json').read_text());passed={x['agent_path'] for x in isolation['audits'] if x['passed']}
    assert all(x['agent_path'] in passed and not x['tool_calls'] for x in accepted)
    accepted_by_case={x['case']:x for x in accepted};assert len(accepted_by_case)==270
    sourcefiles=[run/'strategy_trades.csv',run/'summary.json',run/'paired_windows.csv',run/'bootstrap_arrays.npz',ROOT/'data/analysis/gross-edge-20260929/ma_ablation/PROTOCOL.md',ROOT/'data/analysis/gross-edge-20260929/ma_ablation/evaluate.py']
    ledger=pd.read_csv(sourcefiles[0]);summary=json.loads(sourcefiles[1].read_text());meta=pd.read_csv(sourcefiles[2]).sort_values('block').reset_index(drop=True);arrays=np.load(sourcefiles[3])
    assert len(ledger)==270 and ledger.case.nunique()==270 and set(ledger.arm)==set(ARMS)
    assert len(meta)==90 and meta.block.nunique()==90
    assert set(ledger.AI_action)=={'long','short'} or set(ledger.AI_action).issubset({'long','short'})
    times=pd.to_datetime(meta.entry_time);chron=np.argsort(times.to_numpy());quarter,qlabels=pd.factorize(times.dt.to_period('Q').astype(str),sort=True)
    w=arrays['weights'];qw=arrays['quarter_weights'];assert w.shape==(20000,90) and qw.shape==(20000,len(qlabels))
    assert np.all(w.sum(1)==90) and np.all(qw.sum(1)==len(qlabels))
    comparisons=[];max_error=0.;checks=0
    def eq(label,got,expected):
        nonlocal max_error,checks
        if isinstance(expected,dict):
            for k,v in expected.items():eq(label+'.'+str(k),got[k],v)
            return
        if isinstance(expected,(str,bool,np.bool_)):
            assert got==expected,(label,got,expected);checks+=1;return
        if expected is None or (np.isscalar(expected) and not np.isfinite(expected)):
            assert got is None or (np.isscalar(got) and not np.isfinite(got)),(label,got,expected);checks+=1;return
        aa=np.asarray(got,float);bb=np.asarray(expected,float);assert aa.shape==bb.shape,(label,aa.shape,bb.shape)
        err=float(np.max(np.abs(aa-bb))) if aa.size else 0.;assert np.allclose(aa,bb,rtol=0,atol=1e-10,equal_nan=True),(label,err)
        checks+=int(aa.size);max_error=max(max_error,err)
    def checkmetrics(label,observed,values):
        mine=metrics(values)
        eq(label,observed,{k:mine[k] for k in observed if k in mine})
        return mine
    payoff=None;opps={};details={};economic_rows=[]
    for arm in ARMS:
        r=ledger[ledger.arm.eq(arm)].sort_values('block').reset_index(drop=True)
        eq(arm+'.blocks',r.block.to_numpy(),meta.block.to_numpy())
        assert r.window_id.tolist()==meta.window_id.tolist() and pd.to_datetime(r.entry_time).equals(times)
        assert r.asset.eq('SOL-USD').all() and len(r)==90
        for row in r.itertuples(index=False):
            assert row.AI_action==accepted_by_case[row.case]['decision']['action']
        v=(r.exit_price.to_numpy()/r.entry_price.to_numpy()-1)*100
        eq(arm+'.gross_from_prices',r.gross_pct.to_numpy(),v)
        eq(arm+'.240_path',r.long_move_240m_pct.to_numpy(),v)
        if payoff is None:payoff=v.copy()
        else:eq(arm+'.same_market_payoff',v,payoff)
        sel=r.AI_action.eq('short').to_numpy();eq(arm+'.selected',r.selected.to_numpy().astype(int),sel.astype(int))
        opp=np.where(sel,v,0);opps[arm]=opp;eq(arm+'.opportunity_rows',r.opportunity_gross_pct.to_numpy(),opp);eq(arm+'.saved_opportunity_vector',arrays[arm+'_opportunity'],opp)
        s=summary['arms'][arm];mine=checkmetrics(arm+'.selected_stats',s['selected'],v[sel]);checkmetrics(arm+'.opportunity_stats',s['opportunity'],opp)
        checkmetrics(arm+'.price_only',s['price_only_control'],v)
        checkmetrics(arm+'.belowMA20',s['below_MA20_price_only_control'],v[(meta.ma20_now>100).to_numpy()])
        eq(arm+'.short_calls',s['short_calls'],int(sel.sum()));eq(arm+'.long_calls',s['long_calls'],int((~sel).sum()))
        hstats=[];tstats=[]
        for divisor,target,store in [(2,'chronological_halves',hstats),(3,'chronological_thirds',tstats)]:
            for j,ids in enumerate(np.array_split(chron,divisor)):
                store.append(checkmetrics(f'{arm}.{target}.{j}',s[target][j],v[ids[sel[ids]]]))
        qstats={}
        for j,q in enumerate(qlabels):qstats[q]=checkmetrics(arm+'.quarter.'+q,s['quarters'][q],v[sel&(quarter==j)])
        dstats={}
        for delay in [1,5]:dstats[str(delay)]=checkmetrics(f'{arm}.delay{delay}',s['delays'][str(delay)],r.loc[sel,f'delay{delay}_gross_pct'].to_numpy())
        assert (r.mae_pct<=1e-10).all() and (r.mfe_pct>=-1e-10).all()
        for key,arrkey in [('window_profit_intervals','_mean'),('quarter_profit_intervals','_qmean'),('window_increment_intervals','_increment'),('quarter_increment_intervals','_qincrement')]:eq(arm+'.'+key,s[key],interval(arrays[arm+arrkey]))
        # This audits serialized opportunity arithmetic, leaving independent inference validation to the design reviewer.
        qsum=np.bincount(quarter,weights=opp,minlength=len(qlabels));qn=np.bincount(quarter,minlength=len(qlabels))
        eq(arm+'.opportunity_interval',s['opportunity_intervals'],interval(w@opp/90))
        eq(arm+'.quarter_opportunity_interval',s['quarter_opportunity_intervals'],interval((qw@qsum)/(qw@qn)))
        expected={'at_least50trades':int(sel.sum())>=50,'window99_lower_positive':favorable_lower(s['window_profit_intervals'],'ci99'),
            'quarter95_lower_positive':favorable_lower(s['quarter_profit_intervals'],'ci95'),'both_halves_positive':all(x.get('mean_gross_pct',-np.inf)>0 for x in hstats),
            'both_delays_positive':all(x.get('mean_gross_pct',-np.inf)>0 for x in dstats.values()),'remove_best3_positive':mine.get('exclude_best3_mean_pct',-np.inf)>0}
        eq(arm+'.profit_criteria',s['profit_criteria'],expected)
        eq(arm+'.profit_verified',s['profit_verified'],arm=='MA_A' and all(expected.values()))
        iexpected={'window99_increment_lower_positive':favorable_lower(s['window_increment_intervals'],'ci99'),
            'quarter95_increment_lower_positive':favorable_lower(s['quarter_increment_intervals'],'ci95')}
        eq(arm+'.AI_increment_criteria',s['AI_increment_criteria'],iexpected)
        eq(arm+'.AI_increment_verified',s['AI_increment_verified'],arm=='MA_A' and all(iexpected.values()))
        eq(arm+'.role',s['role'],'primary_profit_replication' if arm=='MA_A' else 'repeat_diagnostic' if arm=='MA_B' else 'MA_input_intervention')
        qs=pd.Series(qsum,index=qlabels).sort_values(ascending=False);qnsel=np.bincount(quarter,weights=sel,minlength=len(qlabels))
        leave=[v[sel&(quarter!=j)].mean() for j in range(len(qlabels)) if (sel&(quarter!=j)).any()]
        top3ids=np.flatnonzero(sel)[np.argsort(v[sel])[-3:]]
        details[arm]={'selected':mine,'selected_frequency':sel.mean(),'selected_quarters':int((qnsel>0).sum()),'sample_quarters':len(qlabels),
            'chronological_halves':hstats,'chronological_thirds':tstats,'quarters':qstats,'quarter_selected_counts':dict(zip(qlabels,qnsel.astype(int))),
            'quarter_sum_trade_percentages_not_portfolio_returns':dict(qs),'top3_quarter_share_of_sum':qs.iloc[:3].sum()/v[sel].sum() if sel.any() and v[sel].sum()!=0 else np.nan,
            'leave_one_quarter_out_min_mean_pct':min(leave) if leave else np.nan,'top3_winning_windows':r.iloc[top3ids][['block','window_id','entry_time','gross_pct']].to_dict('records'),
            'failed_primary_conditions':[k for k,x in expected.items() if not x],'profit_verified':arm=='MA_A' and all(expected.values()),'secondary_cannot_rescue_primary':arm!='MA_A'}
        for i,row in r.iterrows():economic_rows.append({'arm':arm,'block':int(row.block),'window_id':row.window_id,'entry_time':row.entry_time,'selected':bool(sel[i]),'gross_pct':v[i],'opportunity_gross_pct':opp[i]})
    for arm in ['MA_B','NO_MA']:
        diff=opps[arm]-opps['MA_A'];name=arm+'_minus_MA_A';s=summary['secondary_per_opportunity_comparisons'][name]
        qsum=np.bincount(quarter,weights=diff,minlength=len(qlabels));qn=np.bincount(quarter,minlength=len(qlabels))
        expected={'mean_per_opportunity_difference_pct':diff.mean(),'window_intervals':interval(w@diff/90),'quarter_intervals':interval((qw@qsum)/(qw@qn)),'secondary_only':True}
        eq(name,s,expected);comparisons.append({'comparison':name,**expected})
    report={'passed':True,'audit_scope':'Payoff/skip economics, support, quarters/halves, concentration, frozen claim criteria; native paths and independent inference checked separately',
        'run_id':RUN_ID,'independent_comparisons':checks,'max_abs_error_pct':max_error,'arms':details,'paired_per_opportunity_comparisons':comparisons,
        'interpretation':'MA_A alone is the profit replication. Skips are zero opportunities, not losing executed trades. Arithmetic sums are not portfolio returns.',
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sourcefiles}}
    (HERE/'economic_audit.json').write_text(json.dumps(clean(report),indent=2,allow_nan=False)+'\n')
    pd.DataFrame(economic_rows).to_csv(HERE/'economic_window_vectors.csv',index=False)
    print(json.dumps(clean({'passed':True,'comparisons':checks,'max_abs_error_pct':max_error,'MA_A':details['MA_A'],'paired_per_opportunity':comparisons}),indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--release');ap.add_argument('--self-test',action='store_true');args=ap.parse_args()
    if args.self_test:selftest()
    elif args.release:main(args.release)
    else:ap.error('Use --self-test, or --release with the exact released run id')
