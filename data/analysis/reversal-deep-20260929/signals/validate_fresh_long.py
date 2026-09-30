"""Dormant independent native-price replay of locked fresh long strategy L.

No files are read and no evaluation occurs at import. evaluate_long() refuses to
load model decisions or price data until the root-created ALLOW_EVALUATION flag
exists in the run directory. Root must explicitly release evaluation only after
the entire fixed280-decision collection has completed.

run.json is resolved from the parent research directory. A caller may pass an
explicit run directory for independently constructed test fixtures. Running the
module saves results only under this signals directory. Parent-ledger comparison
accepts an explicit column map once root supplies its row format.
"""
from pathlib import Path
import argparse,hashlib,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def resolve_run(run_dir=None):
    if run_dir is not None:
        run=Path(run_dir).resolve()
    else:
        pointer=HERE.parent/'run.json'
        if not pointer.is_file():
            raise RuntimeError('Validation run has not been frozen; no evaluation performed.')
        obj=json.loads(pointer.read_text())
        run=Path(obj['run_dir']).resolve()
    if not (run/'ALLOW_EVALUATION').is_file():
        raise RuntimeError('Root has not released this validation: ALLOW_EVALUATION is absent. No outcomes loaded.')
    return run

def evaluate_long(run_dir=None):
    """Return (all-window DataFrame, audit) after gated independent L replay.

    hypothetical_* values describe a fixed hypothetical long on every window;
    L_selected, control_selected, below_ma20_control_selected identify executed
    policies. Policy-prefixed return columns are NaN for skips. No source file is
    written. Inputs/outputs are native simple percentage returns, without leverage.
    """
    run=resolve_run(run_dir)
    import numpy as np
    import pandas as pd

    manifest=json.loads((run/'manifest.json').read_text())
    records=[json.loads(line) for line in (run/'accepted_decisions.jsonl').read_text().splitlines() if line.strip()]
    cases=sorted(manifest['cases'],key=lambda c:c['case'])
    records.sort(key=lambda r:r['case'])
    assert manifest['planned_decisions']==280 and len(cases)==len(records)==280, 'Fixed collection is incomplete'
    assert [w['case'] for w in cases]==[r['case'] for r in records]==list(range(1,281))
    assert len({r['thread_id'] for r in records})==280
    assert all(r['model']=='gpt-5.6-terra' and not r.get('tool_calls') for r in records)
    isolation=json.loads((run/'isolation_audit.json').read_text())
    assert isolation['all_accepted_passed'] and isolation['accepted']==280
    assert all(r['decision']['action'] in ('long','short') for r in records)
    protocol=ROOT/manifest['protocol_file']
    assert digest(protocol)==manifest['protocol_sha256'], 'Locked protocol changed'
    for relative,expected in manifest['original_sha256'].items():
        assert digest(ROOT/relative)==expected, relative
    for w in cases:
        assert digest(ROOT/w['source_prompt'])==w['prompt_sha256']
        assert digest(ROOT/w['chart_file'])==w['image_sha256']
        assert digest(Path(w['stimulus_dir'])/'input.txt')==w['input_sha256']

    raw1=ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz'
    raw15=ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz'
    minute=pd.read_csv(raw1,index_col=0,parse_dates=True,usecols=[0,1,4]).sort_index()
    bars=pd.read_csv(raw15,index_col=0,parse_dates=True,usecols=[0,1,4]).sort_index()
    assert minute.index.is_unique and bars.index.is_unique
    assert list(minute.columns)==list(bars.columns)==['open','close']
    ma20=bars.close.rolling(20).mean();ma50=bars.close.rolling(50).mean()
    output=[]
    for w,r in zip(cases,records):
        ts=pd.Timestamp(w['entry_time'])
        assert ts==pd.Timestamp(w['window_end_ts'])+pd.Timedelta(minutes=15)
        q=int(minute.index.get_indexer([ts])[0]);b=int(bars.index.get_indexer([ts])[0])
        assert q>0 and b>0
        span=minute.index[q-1:q+255]
        assert len(span)==256 and np.all(np.diff(span.as_unit('ns').asi8)==60_000_000_000)
        original=float(minute.close.iloc[q-1]);confirmed=float(minute.close.iloc[q+14])
        exit_px=float(minute.close.iloc[q+254])
        assert abs(original-w['price_real'])<1e-8
        assert abs(float(bars.close.iloc[b-1])-original)<1e-8
        assert abs(float(bars.close.iloc[b])-confirmed)<1e-8
        assert bars.index[b+16]+pd.Timedelta(minutes=15)==ts+pd.Timedelta(minutes=255)
        assert abs(float(bars.close.iloc[b+16])-exit_px)<1e-8
        scaled20=float(ma20.iloc[b-1])/original*100
        scaled50=float(ma50.iloc[b-1])/original*100
        assert abs(scaled20-w['ma20_now'])<1e-7 and abs(scaled50-w['ma50_now'])<1e-7
        positive=confirmed>original
        selected=positive and r['decision']['action']=='short'
        below20=original<float(ma20.iloc[b-1])
        row={'case':int(w['case']),'window_id':w['window_id'],'ai_action':r['decision']['action'],
             'original_entry_time':str(ts),'original_price':original,'confirmation_close_time':str(ts+pd.Timedelta(minutes=15)),
             'confirmation_close':confirmed,'positive_confirmation':bool(positive),
             'original_below_ma20':bool(below20),'ma20_now':scaled20,'ma50_now':scaled50,
             'L_selected':bool(selected),'control_selected':bool(positive),'below_ma20_control_selected':bool(positive and below20),
             'primary_entry_time':str(ts+pd.Timedelta(minutes=15)),
             'exit_time':str(ts+pd.Timedelta(minutes=255)),'exit_px':exit_px}
        for delay in [0,1,5]:
            actual_entry=ts+pd.Timedelta(minutes=15+delay)
            entry_px=float(minute.open.iloc[q+15+delay])
            assert minute.index[q+15+delay]==actual_entry
            if delay==0:
                assert bars.index[b+1]==actual_entry
                assert abs(float(bars.open.iloc[b+1])-entry_px)<1e-8
            gross=(exit_px/entry_px-1)*100
            row[f'entry_delay{delay}_time']=str(actual_entry)
            row[f'entry_delay{delay}_px']=entry_px
            row[f'held_delay{delay}_minutes']=240-delay
            row[f'hypothetical_long_delay{delay}_gross_pct']=gross
            row[f'hypothetical_long_delay{delay}_net20_pct']=gross-.20
            row[f'hypothetical_long_delay{delay}_net30_pct']=gross-.30
            for prefix,mask in [('L',selected),('control',positive),('below_ma20_control',positive and below20)]:
                row[f'{prefix}_delay{delay}_gross_pct']=gross if mask else np.nan
                row[f'{prefix}_delay{delay}_net20_pct']=gross-.20 if mask else np.nan
                row[f'{prefix}_delay{delay}_net30_pct']=gross-.30 if mask else np.nan
            row[f'same_AI_short_delay{delay}_net20_pct']=-gross-.20 if selected else np.nan
        output.append(row)
    df=pd.DataFrame(output)
    assert df.window_id.nunique()==280 and df.case.nunique()==280
    audit={'passed':True,'run_id':manifest['run_id'],'fixed_collection_complete':True,'cases':280,
           'root_release_flag_exists':True,'protocol_hash_matches':True,'original_hashes_match':True,
           'all_stimulus_hashes_match':True,'independent_native_1m_entry_exit_checks':840,
           'independent_15m_primary_entry_exit_checks':280,'independent_15m_confirmation_checks':280,
           'independent_pre_entry_MA_checks':560,'future_price_loading_gated':True,
           'no_parent_evaluator_functions_imported':True,'late_entry_preserves_original_exit_clock':True,
           'L_selected':int(df.L_selected.sum()),'control_selected':int(df.control_selected.sum()),
           'below_ma20_control_selected':int(df.below_ma20_control_selected.sum()),
           'protocol_sha256':manifest['protocol_sha256'],'raw1m_sha256':digest(raw1),'raw15m_sha256':digest(raw15)}
    return df,audit

def compare_parent(independent,parent,column_map,key='case',parent_key=None,tolerance=1e-8):
    """Compare explicit root column names to independent names, keyed by case.

    column_map is {root_column: independent_column}. Parent must contain all280
    windows exactly once. Numeric NaNs for skipped policies must agree; callers
    should map hypothetical columns for root ledgers retaining skipped returns.
    """
    import numpy as np
    import pandas as pd
    parent_key=parent_key or key
    a=independent.set_index(key).sort_index();b=parent.set_index(parent_key).sort_index()
    assert a.index.is_unique and b.index.is_unique and a.index.equals(b.index)
    checked=0
    for parent_col,own_col in column_map.items():
        left=b[parent_col];right=a[own_col]
        if pd.api.types.is_numeric_dtype(right):
            assert np.allclose(pd.to_numeric(left).to_numpy(float),right.to_numpy(float),atol=tolerance,rtol=0,equal_nan=True), parent_col
        else:
            assert left.astype(str).equals(right.astype(str)), parent_col
        checked+=len(a)
    return {'passed':True,'rows':len(a),'fields':len(column_map),'individual_field_checks':checked}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir');args=parser.parse_args()
    df,audit=evaluate_long(args.run_dir)
    df.to_csv(HERE/'fresh_long_independent_trades.csv',index=False)
    (HERE/'fresh_long_independent_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))

if __name__=='__main__':main()
