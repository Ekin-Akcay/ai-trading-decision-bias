"""Dormant independent scorer for the90-window,270-decision MA experiment.

No raw prices or run data load at import. Root's ALLOW_EVALUATION flag and270
audited decisions are required before replay. No root trading functions import.
"""
from pathlib import Path
import argparse,json,hashlib,math
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
RESEARCH=HERE.parent/'ma_ablation'
ARMS=['MA_A','MA_B','NO_MA']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resolve_run(run_dir=None):
    pointer=RESEARCH/'run.json'
    if run_dir is None and not pointer.is_file():raise RuntimeError('No frozen paired run exists.')
    run=Path(run_dir or json.loads(pointer.read_text())['run_dir']).resolve()
    if not (run/'ALLOW_EVALUATION').is_file():raise RuntimeError('New forward outcomes remain sealed.')
    return run

def replay(run_dir=None):
    run=resolve_run(run_dir)
    import numpy as np
    import pandas as pd
    from PIL import Image

    m=json.loads((run/'manifest.json').read_text());records=sorted([json.loads(x) for x in (run/'accepted_decisions.jsonl').read_text().splitlines() if x.strip()],key=lambda x:x['case'])
    cases=sorted(m['cases'],key=lambda x:x['case'])
    assert m['planned_decisions']==len(cases)==len(records)==270 and m['unique_windows']==90
    assert [x['case'] for x in cases]==[x['case'] for x in records]==list(range(1,271))
    assert len({r['thread_id'] for r in records})==270
    assert all(r['model']=='gpt-5.6-terra' and r['reasoning_effort']=='medium' and not r.get('tool_calls') for r in records)
    assert m['primary_profit_arm']=='MA_A' and m['primary_cost_bps']==0 and m['evaluation_horizon_minutes']==360
    isolation=json.loads((run/'isolation_audit.json').read_text());assert isolation['all_accepted_passed'] and isolation['accepted']==270
    approved={a['agent_path'] for a in isolation['audits'] if a['passed']};assert all(r['agent_path'] in approved for r in records)
    assert sha(ROOT/m['protocol_file'])==m['protocol_sha256']
    for name,h in m['original_sha256'].items():assert sha(ROOT/name)==h,name
    decisions={r['case']:r['decision'] for r in records}
    for c in cases:
        folder=Path(c['stimulus_dir'])
        for name,key in [('stats.txt','prompt_sha256'),('input.txt','input_sha256'),('chart.png','image_sha256')]:assert sha(folder/name)==c[key]
        assert (folder/'input.txt').read_text()==m['contract']+'\n\n'+(folder/'stats.txt').read_text()
        assert decisions[c['case']]['action'] in ('long','short')
    frame=pd.DataFrame(cases);assert frame.block.nunique()==90 and frame.window_id.nunique()==90
    assert not frame.duplicated(['block','arm']).any()
    for block,group in frame.groupby('block'):
        assert len(group)==3 and set(group.arm)==set(ARMS) and group.window_id.nunique()==1
        assert group.entry_time.nunique()==1 and set(group.asset)=={'SOL-USD'}
        byarm=group.set_index('arm');a=byarm.loc['MA_A'];b=byarm.loc['MA_B'];no=byarm.loc['NO_MA']
        assert a.input_sha256==b.input_sha256 and a.image_sha256==b.image_sha256
        full=(Path(a.stimulus_dir)/'stats.txt').read_text();bare=(Path(no.stimulus_dir)/'stats.txt').read_text()
        removed=[line for line in full.splitlines() if line.startswith('Indicators (')]
        assert len(removed)==1 and bare=='\n'.join(line for line in full.splitlines() if not line.startswith('Indicators ('))
        assert 'MA20' not in bare and 'MA50' not in bare
        assert Image.open(Path(a.stimulus_dir)/'chart.png').size==Image.open(Path(no.stimulus_dir)/'chart.png').size
    unique=frame[frame.arm=='MA_A'].sort_values('block').reset_index(drop=True)
    minute=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True,usecols=[0,1,2,3,4]).sort_index()
    bars=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',index_col=0,parse_dates=True,usecols=[0,1,2,3,4]).sort_index()
    assert minute.index.is_unique and bars.index.is_unique
    ma20=bars.close.rolling(20).mean();ma50=bars.close.rolling(50).mean()
    sol=pd.read_csv(ROOT/'data/raw/SOL-USD.csv',index_col=0,parse_dates=True).sort_index();sol['sma']=sol.close.rolling(50,min_periods=50).mean()
    btc=pd.read_csv(ROOT/'data/raw/BTC-USD.csv',index_col=0,parse_dates=True).sort_index();btc['sma']=btc.close.rolling(200,min_periods=200).mean()
    windows=[];rows=[]
    for w in unique.itertuples(index=False):
        ts=pd.Timestamp(w.entry_time);q=int(minute.index.get_indexer([ts])[0]);b=int(bars.index.get_indexer([ts])[0]);assert q>0 and b>=200
        assert ts==pd.Timestamp(w.window_end_ts)+pd.Timedelta(minutes=15)
        span=minute.iloc[q-1:q+360];assert span.index.equals(pd.date_range(ts-pd.Timedelta(minutes=1),periods=361,freq='min'))
        assert np.isfinite(span.to_numpy()).all() and (span.to_numpy()>0).all()
        assert bars.iloc[b-200:b].index.equals(pd.date_range(ts-pd.Timedelta(hours=50),periods=200,freq='15min'))
        original=float(minute.close.iloc[q-1]);ep=float(minute.open.iloc[q]);xp=float(minute.close.iloc[q+239])
        assert abs(original-w.price_real)<1e-8 and abs(original-float(bars.close.iloc[b-1]))<1e-8
        assert abs(ep-float(bars.open.iloc[b]))<1e-8 and abs(xp-float(bars.close.iloc[b+15]))<1e-8
        scaled20=float(ma20.iloc[b-1])/original*100;scaled50=float(ma50.iloc[b-1])/original*100
        assert abs(scaled20-w.ma20_now)<1e-7 and abs(scaled50-w.ma50_now)<1e-7
        previous=ts.normalize()-pd.Timedelta(days=1)
        assert sol.loc[:previous].tail(50).index.equals(pd.date_range(previous-pd.Timedelta(days=49),periods=50,freq='D'))
        assert btc.loc[:previous].tail(200).index.equals(pd.date_range(previous-pd.Timedelta(days=199),periods=200,freq='D'))
        sd=sol.loc[previous];bd=btc.loc[previous]
        assert sd.close<=sd.sma and bd.close<=bd.sma
        assert np.allclose([sd.close,sd.sma,bd.close,bd.sma],[w.asset_daily_close,w.asset_daily_sma50,w.btc_daily_close,w.btc_daily_sma200],atol=1e-8,rtol=1e-12)
        gross=(xp/ep-1)*100;path=minute.iloc[q:q+240]
        common={'block':int(w.block),'window_id':w.window_id,'asset':'SOL-USD','entry_time':str(ts),'entry_price':ep,'exit_price':xp,'gross_pct':gross,
                'delay1_gross_pct':(xp/float(minute.open.iloc[q+1])-1)*100,'delay5_gross_pct':(xp/float(minute.open.iloc[q+5])-1)*100,
                'mae_pct':min(0.,(float(path.low.min())/ep-1)*100),'mfe_pct':max(0.,(float(path.high.max())/ep-1)*100)}
        for h in [15,30,60,105,240]:
            native=float(minute.close.iloc[q+h-1]);assert abs(native-float(bars.close.iloc[b+h//15-1]))<1e-8
            assert minute.index[q+h-1]+pd.Timedelta(minutes=1)==ts+pd.Timedelta(minutes=h)
            common[f'long_move_{h}m_pct']=(native/ep-1)*100
        windows.append({**common,'ma20_now':scaled20,'ma50_now':scaled50,'previous_daily_reference':str(previous),'macro_both_down':True,'below_MA20':scaled20>100})
        for c in frame[frame.block==w.block].itertuples(index=False):
            dec=decisions[c.case];selected=dec['action']=='short'
            rows.append({**common,'case':int(c.case),'arm':c.arm,'AI_action':dec['action'],'reason':dec['reason'],'confidence':dec['confidence'],'selected':selected,'opportunity_gross_pct':gross if selected else 0.})
    df=pd.DataFrame(rows).sort_values('case').reset_index(drop=True);wf=pd.DataFrame(windows).sort_values('block').reset_index(drop=True)
    assert len(df)==270 and df.case.tolist()==list(range(1,271)) and len(wf)==90
    audit={'passed':True,'run_id':m['run_id'],'unique_windows':90,'audited_decisions':270,'source_protocol_and_stimulus_hashes_match':True,
           'exact_MA_A_MA_B_stimulus_identity_pairs':90,'exact_NO_MA_text_removal_pairs':90,'paired_chart_dimensions_equal':True,
           'raw_minute_coverage_windows':90,'native_1m_primary_and_delay_checks':270,'independent_15m_entry_exit_checks':90,
           'independent_15m_horizon_checks':450,'daily_gate_native_checks':90,'pre_entry_MA_checks':180,
           'new_forward_read_only_after_root_release':True,'root_return_functions_not_imported':True,'zero_fees':True}
    return df,wf,audit

def compare_root(df,wf,run_dir=None):
    run=resolve_run(run_dir)
    import numpy as np
    import pandas as pd
    parent=pd.read_json(run/'strategy_trades.jsonl',lines=True,convert_dates=False).set_index('case').sort_index()
    own=df.set_index('case').sort_index();assert parent.index.equals(own.index) and parent.index.is_unique
    cols=['block','arm','window_id','asset','entry_time','AI_action','reason','confidence','selected','entry_price','exit_price','gross_pct','opportunity_gross_pct','delay1_gross_pct','delay5_gross_pct','mae_pct','mfe_pct',*[f'long_move_{h}m_pct' for h in [15,30,60,105,240]]]
    for col in cols:
        if pd.api.types.is_numeric_dtype(own[col]):assert np.allclose(parent[col].to_numpy(float),own[col].to_numpy(float),atol=1e-8,rtol=0,equal_nan=True),col
        else:assert parent[col].astype(str).equals(own[col].astype(str)),col
    summary=json.loads((run/'summary.json').read_text());actions={}
    for arm in ARMS:
        a=own[own.arm==arm].sort_values('block');actions[arm]=a.AI_action.to_numpy();selected=a[a.selected];root=summary['arms'][arm]
        assert len(selected)==root['selected']['n']==root['short_calls']
        if len(selected):
            assert abs(selected.gross_pct.mean()-root['selected']['mean_gross_pct'])<1e-8
            assert int((selected.gross_pct>0).sum())==root['selected']['wins']
            for delay in [1,5]:assert abs(selected[f'delay{delay}_gross_pct'].mean()-root['delays'][str(delay)]['mean_gross_pct'])<1e-8
        assert abs(a.opportunity_gross_pct.mean()-root['opportunity']['mean_gross_pct'])<1e-8
        assert abs(a.gross_pct.mean()-root['price_only_control']['mean_gross_pct'])<1e-8
        below=wf[wf.below_MA20].gross_pct
        assert len(below)==root['below_MA20_price_only_control']['n']
        if len(below):assert abs(below.mean()-root['below_MA20_price_only_control']['mean_gross_pct'])<1e-8
    t=actions['NO_MA']!=actions['MA_A'];r=actions['MA_B']!=actions['MA_A']
    b=int((t&~r).sum());c=int((~t&r).sum());n=b+c
    p=sum(math.comb(n,k) for k in range(b,n+1))/2**n if n else 1.
    mech=summary['mechanism'];assert int(t.sum())==mech['treatment_flips'] and int(r.sum())==mech['ordinary_repeat_flips']
    assert b==mech['discordant_treatment_only'] and c==mech['discordant_repeat_only']
    assert abs(p-mech['exact_one_sided_p'])<1e-12
    assert abs(((actions['MA_A']=='short').astype(int)-(actions['NO_MA']=='short').astype(int)).mean()-mech['short_frequency_reduction_NO_MA_vs_A'])<1e-12
    for arm in ['MA_B','NO_MA']:
        v=(actions[arm]=='short').astype(int)*wf.gross_pct.to_numpy()-(actions['MA_A']=='short').astype(int)*wf.gross_pct.to_numpy()
        assert abs(v.mean()-summary['secondary_per_opportunity_comparisons'][arm+'_minus_MA_A']['mean_per_opportunity_difference_pct'])<1e-8
    return {'passed':True,'compared_arm_rows':270,'fields':len(cols),'individual_field_checks':270*len(cols),'arm_trade_counts_returns_controls_delays_match':True,'paired_mechanism_discordance_and_exact_p_match':True,'secondary_opportunity_contrasts_match':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir');p.add_argument('--compare-root',action='store_true');args=p.parse_args()
    df,wf,audit=replay(args.run_dir)
    if args.compare_root:audit['root_comparison']=compare_root(df,wf,args.run_dir)
    df.to_csv(HERE/'paired90_independent_arm_rows.csv',index=False);wf.to_csv(HERE/'paired90_independent_windows.csv',index=False)
    (HERE/'paired90_independent_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))

if __name__=='__main__':main()
