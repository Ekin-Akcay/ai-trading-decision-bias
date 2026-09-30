"""Offline numerical replay of published research. No model or network calls."""
from pathlib import Path
import importlib.util,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
ANALYSIS=ROOT/'data/analysis/ai-timing-200-20260930'
RUN=ROOT/'data/sim/ai-timing-200-20260930T104240Z'

def main():
    spec=importlib.util.spec_from_file_location('published_scorer',ANALYSIS/'score_stage.py')
    scorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(scorer)
    count=0
    for stage in ['screen','confirmation']:
        ledger=pd.read_csv(RUN/stage/'trade_ledger.csv')
        arrays=np.load(RUN/stage/'paths.npz',allow_pickle=False)
        paths={int(case):path for case,path in zip(arrays['case'],arrays['paths'])}
        assert ledger.valid_coverage.all()
        for row in ledger.itertuples():
            p=paths[row.case];assert p.shape==(120,4)
            assert pd.Timestamp(row.entry_time)==pd.Timestamp(row.t0)+pd.Timedelta(minutes=30)
            assert pd.Timestamp(row.horizon_end)==pd.Timestamp(row.t0)+pd.Timedelta(minutes=150)
            np.testing.assert_allclose([row.entry_price,row.exit_price],[p[0,0],p[-1,3]],rtol=0,atol=1e-10)
            expected=row.trade_side*100*(p[-1,3]/p[0,0]-1)
            np.testing.assert_allclose(row.gate_gross_pct,expected,rtol=0,atol=1e-10)
            count+=1
        result,weights,boot=scorer.analyse_frame(ledger,stage)
        recorded=json.loads((RUN/stage/'summary.json').read_text())
        for direction,stats in result['directions'].items():
            target=recorded['directions'][direction]
            for policy in ['aligned','opposed','price_only','MA20_control']:
                assert stats[policy]['n']==target[policy]['n']
                np.testing.assert_allclose(stats[policy]['mean_gross_pct'],target[policy]['mean_gross_pct'],rtol=0,atol=1e-10)
            for field in ['primary_aligned_mean_interval','primary_adjusted_spread_interval']:
                np.testing.assert_allclose(stats[field]['simultaneous98_75_one_sided_lower'],target[field]['simultaneous98_75_one_sided_lower'],rtol=0,atol=1e-9)
            assert stats['screen_pass']==target['screen_pass'] and stats['confirmed']==target['confirmed']
            print(f"{stage} {direction}: {stats['aligned']['n']} selected, mean {stats['aligned']['mean_gross_pct']:+.6f}%, confirmed={stats['confirmed']}")
        saved=np.load(RUN/stage/'bootstrap_arrays.npz',allow_pickle=False)
        np.testing.assert_array_equal(weights,saved['quarter_weights'])
        for name,values in boot.items():np.testing.assert_allclose(values,saved[name],rtol=0,atol=1e-9,equal_nan=True)
    vectors=pd.read_csv(ANALYSIS/'interpretation/identical_coverage_vectors.csv')
    raw=100*(vectors.exit_price/vectors.entry_price-1)
    ai=np.where(vectors.AI_action=='long',1,-1)*raw
    ma=np.where(vectors.above_equal_MA20,1,-1)*raw
    np.testing.assert_allclose(vectors.follow_AI_pct,ai,rtol=0,atol=1e-10)
    np.testing.assert_allclose(vectors.follow_MA20_pct,ma,rtol=0,atol=1e-10)
    np.testing.assert_allclose(vectors.AI_minus_MA20_pp,ai-ma,rtol=0,atol=1e-10)
    assert count==180
    print('PASS: 180 native trade returns, both 40,000-draw stage analyses, and retrospective direction comparison reproduce.')
    print('Economic verdict: no hypothesis passed the frozen confirmation standard.')
if __name__=='__main__':main()
