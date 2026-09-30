"""Dormant independent native-data audit of the frozen500-case L048 study.

Importing this module reads no run data or prices. All evaluation entrypoints
require run/ALLOW_EVALUATION and500 complete audited model decisions before any
raw forward price file is loaded. No evaluator functions from root are imported.
After root explicitly releases outcomes, run this script with --compare-root to
compare every L048 row in root's completed ledger and corresponding summaries.
"""
from pathlib import Path
import argparse,hashlib,json

HERE=Path(__file__).resolve().parent
RESEARCH=HERE.parent
ROOT=HERE.parents[3]
ASSETS={'SOL-USD','BTC-USD','ETH-USD','DOGE-USD'}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def resolve_run(run_dir=None):
    if run_dir is None:
        pointer=RESEARCH/'run.json'
        if not pointer.is_file():
            raise RuntimeError('No frozen500-case run exists yet; no outcomes loaded.')
        run=Path(json.loads(pointer.read_text())['run_dir']).resolve()
    else:
        run=Path(run_dir).resolve()
    if not (run/'ALLOW_EVALUATION').is_file():
        raise RuntimeError('Forward outcomes remain sealed: ALLOW_EVALUATION is absent.')
    return run

def evaluate_L048(run_dir=None):
    """Read after seal release only; return all500 hypothetical rows and audit.

    eligible is the independently reconstructed daily price gate. selected also
    requires actual audited AI actionSHORT. gross_pct remains hypothetical for
    skipped windows, matching root's all-window ledger. primaryreturns use0fees.
    """
    run=resolve_run(run_dir)
    import numpy as np
    import pandas as pd

    manifest=json.loads((run/'manifest.json').read_text())
    records=sorted([json.loads(x) for x in (run/'accepted_decisions.jsonl').read_text().splitlines() if x.strip()],key=lambda x:x['case'])
    cases=sorted(manifest['cases'],key=lambda x:x['case'])
    assert manifest['planned_decisions']==500 and len(cases)==len(records)==500
    assert [w['case'] for w in cases]==[r['case'] for r in records]==list(range(1,501))
    assert len({r['thread_id'] for r in records})==500
    assert all(r['model']=='gpt-5.6-terra' and r['reasoning_effort']=='medium' and not r.get('tool_calls') for r in records)
    assert all(r['decision']['action'] in {'long','short'} for r in records)
    isolation=json.loads((run/'isolation_audit.json').read_text())
    assert isolation['all_accepted_passed'] and isolation['accepted']==500
    approved={a['agent_path'] for a in isolation['audits'] if a['passed']}
    assert all(r['agent_path'] in approved for r in records)
    assert manifest['primary_cost_bps']==0 and manifest['evaluation_horizon_minutes']==360
    assert manifest['independent_calendar_blocks']==125
    assert sha(ROOT/manifest['protocol_file'])==manifest['protocol_sha256']
    assert sha(RESEARCH/'design/fresh_blocks.json')==manifest['selection_plan_sha256']
    for relative,expected in manifest['original_sha256'].items():
        assert sha(ROOT/relative)==expected, relative
    for w in cases:
        assert sha(ROOT/w['source_prompt'])==w['prompt_sha256']
        assert sha(ROOT/w['chart_file'])==w['image_sha256']
        assert sha(Path(w['stimulus_dir'])/'input.txt')==w['input_sha256']
        assert (Path(w['stimulus_dir'])/'input.txt').read_text()==manifest['contract']+'\n\n'+(ROOT/w['source_prompt']).read_text()

    frame=pd.DataFrame(cases).set_index('case').sort_index()
    frame['entry_time']=pd.to_datetime(frame.entry_time)
    assert set(frame.asset)==ASSETS and frame.block.nunique()==125
    for _,block in frame.groupby('block'):
        assert len(block)==4 and set(block.asset)==ASSETS and block.entry_time.nunique()==1
    decision={r['case']:r['decision'] for r in records}

    daily={}
    for asset in sorted(ASSETS):
        d=pd.read_csv(ROOT/f'data/raw/{asset}.csv',index_col=0,parse_dates=True).sort_index()
        assert d.index.is_unique
        d['sma50']=d.close.rolling(50,min_periods=50).mean()
        d['sma200']=d.close.rolling(200,min_periods=200).mean()
        daily[asset]=d

    result=[];source_files=[]
    for asset in sorted(ASSETS):
        raw1=ROOT/f'data/raw/intraday/{asset}_1m.csv.gz'
        raw15=ROOT/f'data/raw/intraday/{asset}_15m.csv.gz'
        minute=pd.read_csv(raw1,index_col=0,parse_dates=True,usecols=[0,1,2,3,4]).sort_index()
        bars=pd.read_csv(raw15,index_col=0,parse_dates=True,usecols=[0,1,2,3,4]).sort_index()
        assert minute.index.is_unique and bars.index.is_unique
        assert list(minute.columns)==list(bars.columns)==['open','high','low','close']
        ma20=bars.close.rolling(20).mean();ma50=bars.close.rolling(50).mean()
        for case,w in frame[frame.asset==asset].iterrows():
            ts=w.entry_time
            assert ts==pd.Timestamp(w.window_end_ts)+pd.Timedelta(minutes=15)
            q=int(minute.index.get_indexer([ts])[0]);b=int(bars.index.get_indexer([ts])[0])
            assert q>0 and b>=200
            span=minute.iloc[q-1:q+360]
            assert span.index.equals(pd.date_range(ts-pd.Timedelta(minutes=1),periods=361,freq='min'))
            assert np.isfinite(span.to_numpy()).all() and (span.to_numpy()>0).all()
            hist=bars.iloc[b-200:b]
            assert hist.index.equals(pd.date_range(ts-pd.Timedelta(hours=50),periods=200,freq='15min'))
            original=float(minute.close.iloc[q-1]);ep=float(minute.open.iloc[q]);xp=float(minute.close.iloc[q+239])
            assert abs(original-w.price_real)<1e-8
            assert abs(float(bars.close.iloc[b-1])-original)<1e-8
            assert abs(float(bars.open.iloc[b])-ep)<1e-8
            assert bars.index[b+15]+pd.Timedelta(minutes=15)==ts+pd.Timedelta(minutes=240)
            assert abs(float(bars.close.iloc[b+15])-xp)<1e-8
            scaled20=float(ma20.iloc[b-1])/original*100
            scaled50=float(ma50.iloc[b-1])/original*100
            assert abs(scaled20-w.ma20_now)<1e-7 and abs(scaled50-w.ma50_now)<1e-7

            previous=ts.normalize()-pd.Timedelta(days=1)
            ad=daily[asset];bd=daily['BTC-USD']
            assert ad.loc[:previous].tail(50).index.equals(pd.date_range(previous-pd.Timedelta(days=49),periods=50,freq='D'))
            assert bd.loc[:previous].tail(200).index.equals(pd.date_range(previous-pd.Timedelta(days=199),periods=200,freq='D'))
            asset_close=float(ad.loc[previous,'close']);asset_average=float(ad.loc[previous,'sma50'])
            btc_close=float(bd.loc[previous,'close']);btc_average=float(bd.loc[previous,'sma200'])
            native=[asset_close,asset_average,btc_close,btc_average]
            stored=[w.asset_daily_close,w.asset_daily_sma50,w.btc_daily_close,w.btc_daily_sma200]
            assert np.isfinite(native).all() and np.allclose(native,stored,atol=1e-8,rtol=1e-12)
            macro=asset_close<=asset_average and btc_close<=btc_average
            assert macro==bool(w.macro_both_down)
            ai_action=decision[case]['action'];selected=macro and ai_action=='short'
            below20=original<float(ma20.iloc[b-1])
            gross=(xp/ep-1)*100
            slice_=minute.iloc[q:q+240]
            row={'rule':'L048','case':int(case),'block':int(w.block),'asset':asset,'window_id':w.window_id,
                 'entry_time':str(ts),'exit_close_time':str(ts+pd.Timedelta(minutes=240)),
                 'AI_action':ai_action,'eligible':bool(macro),'selected':bool(selected),'direction':'long',
                 'entry_price':ep,'exit_price':xp,'gross_pct':gross,'net_at_zero_cost_pct':gross,
                 'outcome':'timeout','held_minutes':240,'exit_minute_index':240,'ambiguous':False,'gap':False,
                 'mfe_through_exit_bar_pct':(float(slice_.high.max())/ep-1)*100,
                 'mae_through_exit_bar_pct':(float(slice_.low.min())/ep-1)*100,
                 'ma20_now':scaled20,'ma50_now':scaled50,'previous_daily_reference':str(previous),
                 'asset_daily_close':asset_close,'asset_daily_sma50':asset_average,
                 'btc_daily_close':btc_close,'btc_daily_sma200':btc_average,
                 'below_MA20_price_control':bool(macro and below20),
                 'complementary_AI_group':bool(macro and ai_action=='long'),
                 'same_selected_AI_direction_gross_pct':-gross if selected else np.nan}
            for delay in [1,5]:
                delayed=float(minute.open.iloc[q+delay])
                assert minute.index[q+delay]==ts+pd.Timedelta(minutes=delay)
                row[f'entry_delay{delay}_price']=delayed
                row[f'entry_delay{delay}_gross_pct']=(xp/delayed-1)*100
                row[f'entry_delay{delay}_held_minutes']=240-delay
            for h in [15,30,60,105,240]:
                assert minute.index[q+h-1]+pd.Timedelta(minutes=1)==ts+pd.Timedelta(minutes=h)
                expected=float(bars.close.iloc[b+h//15-1])
                actual=float(minute.close.iloc[q+h-1]);assert abs(actual-expected)<1e-8
                row[f'scheduled_direction_move_{h}m_pct']=(actual/ep-1)*100
            result.append(row)
        source_files.extend([str(raw1.relative_to(ROOT)),str(raw15.relative_to(ROOT))])
    df=pd.DataFrame(result).sort_values('case').reset_index(drop=True)
    assert df.case.tolist()==list(range(1,501)) and df.window_id.nunique()==500
    audit={'passed':True,'run_id':manifest['run_id'],'model_decisions_complete_and_audited':500,
           'calendar_blocks':125,'assets':sorted(ASSETS),'root_release_flag_exists':True,
           'future_price_loading_gated':True,'zero_fees':True,'old_source_hashes_match':True,
           'protocol_and_selection_hashes_match':True,'all_stimulus_and_combined_prompt_hashes_match':True,
           'native_minute_coverage_cases':500,'native_1m_primary_and_delay_return_checks':1500,
           'independent_15m_primary_entry_exit_checks':500,'independent_15m_scheduled_exit_checks':2500,
           'pre_entry_MA_checks':1000,'previous_completed_day_macro_checks':500,
           'daily_history_contiguous_for_50_and_200_day_averages':True,
           'no_root_evaluator_functions_imported':True,'L_selected':int(df.selected.sum()),
           'L_selected_blocks':int(df.loc[df.selected,'block'].nunique()),
           'L_macro_eligible':int(df.eligible.sum()),'source_native_files':source_files}
    return df,audit

def compare_root(independent,run_dir=None):
    """Compare root's completed L ledger and key summaries to native replay."""
    run=resolve_run(run_dir)
    import numpy as np
    import pandas as pd
    root=pd.read_json(run/'strategy_trades.jsonl',lines=True,convert_dates=False)
    root=root[root.rule=='L048'].set_index('case').sort_index()
    ours=independent.set_index('case').sort_index()
    assert root.index.equals(ours.index) and root.index.is_unique
    cols=['rule','block','asset','window_id','entry_time','AI_action','eligible','selected','direction',
          'entry_price','exit_price','gross_pct','net_at_zero_cost_pct','outcome','held_minutes',
          'exit_minute_index','ambiguous','gap','entry_delay1_gross_pct','entry_delay5_gross_pct',
          'mfe_through_exit_bar_pct','mae_through_exit_bar_pct',
          *[f'scheduled_direction_move_{h}m_pct' for h in [15,30,60,105,240]]]
    for col in cols:
        if pd.api.types.is_numeric_dtype(ours[col]):
            assert np.allclose(root[col].to_numpy(float),ours[col].to_numpy(float),atol=1e-8,rtol=0,equal_nan=True),col
        else:
            assert root[col].astype(str).equals(ours[col].astype(str)),col
    manifest_frame=pd.read_csv(run/'window_results.csv').set_index('case').sort_index()
    for col in ['asset_daily_close','asset_daily_sma50','btc_daily_close','btc_daily_sma200','ma20_now','ma50_now']:
        assert np.allclose(manifest_frame[col],ours[col],atol=1e-7,rtol=1e-12),col
    assert np.array_equal(manifest_frame.macro_both_down,ours.eligible)
    summary=json.loads((run/'summary.json').read_text())['rules']['L048']
    for mask,key in [(ours.selected,'selected'),(ours.eligible,'eligible_price_only'),
                     (ours.complementary_AI_group,'complementary_AI_group'),
                     (ours.below_MA20_price_control,'additional_belowMA20_price_control')]:
        x=ours.loc[mask,'gross_pct'];s=summary[key]
        assert len(x)==s['n'],key
        if len(x):
            assert abs(x.mean()-s['mean_gross_pct'])<1e-8,key
            assert int((x>0).sum())==s['wins'],key
    for delay in [1,5]:
        x=ours.loc[ours.selected,f'entry_delay{delay}_gross_pct'];s=summary['delay_sensitivities'][str(delay)]
        assert len(x)==s['n']
        if len(x):assert abs(x.mean()-s['mean_gross_pct'])<1e-8
    assert summary['selected_blocks']==int(ours.loc[ours.selected,'block'].nunique())
    for asset in sorted(ASSETS):
        x=ours.loc[ours.selected&ours.asset.eq(asset),'gross_pct'];s=summary['assets'][asset]
        assert len(x)==s['n']
        if len(x):assert abs(x.mean()-s['mean_gross_pct'])<1e-8
    return {'passed':True,'L_rows':500,'matched_fields':len(cols),'individual_field_checks':500*len(cols),
            'macro_inputs_and_MAs_recomputed_and_match':True,'selected_control_complement_delay_asset_summaries_match':True}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir');parser.add_argument('--compare-root',action='store_true');args=parser.parse_args()
    df,audit=evaluate_L048(args.run_dir)
    if args.compare_root:audit['root_comparison']=compare_root(df,args.run_dir)
    df.to_csv(HERE/'fresh_L048_independent_rows.csv',index=False)
    (HERE/'fresh_L048_independent_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))

if __name__=='__main__':main()
