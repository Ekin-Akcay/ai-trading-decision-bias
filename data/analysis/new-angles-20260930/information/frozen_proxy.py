"""Inference-only annual price-to-AI-direction proxy. No outcomes and no fitting."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ASSETS={'SOL-USD','BTC-USD','ETH-USD','DOGE-USD'}

def predict_short_probability(frame, fits_path=None):
    """Return probability of the historical Terra AI choosing SHORT, not price falling.

    Required columns: entry_time, asset, ma20_now, ma50_now, atr14_pct,
    ret_vis_pct, vol24_ratio. Use full precision build_snapshot(...,40,200)
    metadata from completed bars through entry_time minus fifteen minutes.
    The returned Series retains the input index. Dates outside frozen annual
    epochs2022–2026 and unsupported assets are rejected, never extrapolated.
    """
    data=frame.copy();dates=pd.to_datetime(data.entry_time)
    if dates.dt.tz is not None:dates=dates.dt.tz_convert('UTC').dt.tz_localize(None)
    assert data.asset.isin(ASSETS).all(), 'Unsupported asset; no unregistered extrapolation.'
    assert dates.dt.year.isin([2022,2023,2024,2025,2026]).all(), 'No frozen coefficients for this year.'
    assert data.atr14_pct.gt(0).all() and data.vol24_ratio.gt(0).all()
    numeric=np.column_stack([(100-data.ma20_now)/data.atr14_pct,(100-data.ma50_now)/data.atr14_pct,data.ret_vis_pct/data.atr14_pct,np.log(data.vol24_ratio),np.log(data.atr14_pct)])
    assert np.isfinite(numeric).all()
    dummy=np.column_stack([data.asset.eq(s).to_numpy(float) for s in ['BTC-USD','ETH-USD','DOGE-USD']])
    doc=json.loads(Path(fits_path or HERE/'model_fits.json').read_text())
    fits={f['test_year']:f for f in doc['folds']};out=np.full(len(data),np.nan)
    for year in sorted(dates.dt.year.unique()):
        fit=fits[int(year)];take=dates.dt.year.eq(year).to_numpy()
        assert pd.Timestamp(fit['training_end'])+pd.Timedelta(days=7)<pd.Timestamp(f'{year}-01-01')
        assert (dates[take]>pd.Timestamp(fit['training_end'])+pd.Timedelta(days=7)).all()
        numeric_scaled=(numeric[take]-np.array(fit['mu']))/np.array(fit['sd'])
        X=np.column_stack([np.ones(take.sum()),numeric_scaled,dummy[take]])
        beta=np.array(fit['action']['coefficients']);assert X.shape[1]==len(beta)==9
        out[take]=1/(1+np.exp(-np.clip(X@beta,-700,700)))
    assert np.isfinite(out).all() and ((out>=0)&(out<=1)).all()
    return pd.Series(out,index=data.index,name='predicted_AI_short_probability')

def fade_predicted_direction(frame, fits_path=None):
    """+1 buys if predicted AI SHORT probability>=.5; -1 otherwise sells."""
    p=predict_short_probability(frame,fits_path)
    return pd.Series(np.where(p>=.5,1,-1),index=frame.index,name='proxy_fade_direction')
