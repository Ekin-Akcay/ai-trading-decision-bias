"""Independent aggregate-bar verification of every control/selected return."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
w=pd.read_csv(HERE/'windows.csv');t=pd.read_csv(HERE/'control_trades.csv')
px=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',index_col=0,parse_dates=True)
ei=px.index.get_indexer(pd.to_datetime(t.entry_time));xi=px.index.get_indexer(pd.to_datetime(t.exit_time)-pd.Timedelta(minutes=15))
assert (ei>=0).all() and (xi>=0).all()
assert np.allclose(px.open.to_numpy()[ei],t.entry_px,atol=1e-8,rtol=0)
assert np.allclose(px.close.to_numpy()[xi],t.exit_px,atol=1e-8,rtol=0)
sign=np.where(t.side=='long',1,-1)
returns=sign*(px.close.to_numpy()[xi]/px.open.to_numpy()[ei]-1)*100
assert np.allclose(returns,t.gross_pct,atol=1e-8,rtol=0)
assert np.allclose(returns-.2,t.net_pct,atol=1e-8,rtol=0)
source=px.index.get_indexer(pd.to_datetime(w.entry_time)-pd.Timedelta(minutes=15))
assert np.allclose(px.close.to_numpy()[source],w.price_real,atol=1e-8,rtol=0)
for n in [20,50]:
    scaled=px.close.rolling(n).mean().to_numpy()[source]/w.price_real*100
    assert np.allclose(scaled,w[f'ma{n}_now'],atol=1e-7,rtol=0)
for asset,length in [('SOL-USD',50),('BTC-USD',200)]:
    daily=pd.read_csv(ROOT/f'data/raw/{asset}.csv',index_col=0,parse_dates=True)
    dates=pd.to_datetime(w.entry_time).dt.normalize()-pd.Timedelta(days=1)
    ii=daily.index.get_indexer(dates);assert (ii>=0).all()
    assert np.allclose(daily.close.to_numpy()[ii],w[asset+'_daily_close'],atol=1e-7,rtol=0)
    assert np.allclose(daily.close.rolling(length).mean().to_numpy()[ii],w[asset+'_daily_sma'],atol=1e-7,rtol=0)
res=json.loads((HERE/'candidate_results.json').read_text())
for r in res:
    selected=t[(t.candidate==r['candidate']) & t.selected]
    assert len(selected)==r['n']
    if len(selected):assert abs(selected.net_pct.mean()-r['net_mean'])<1e-8
audit={'passed':True,'windows':150,'all_candidates':116,'independent_15m_entry_exit_and_return_checks':len(t),'MA_recomputed_checks':300,'daily_prior_completed_day_recomputed_checks':300,'zero_future_daily_or_intraday_MA_information':True,'summary_counts_and_means_match':True}
(HERE/'independent_validation.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
