"""Vectorized, conservative bracket replay for the locked fresh-validation protocol.

This module reads no files and makes no model calls. It accepts native OHLC paths.

Path layout: (N, T, 4), columns open/high/low/close. Index 0 is the minute
immediately preceding the original entry; index 1 starts at original entry t0.
Thus the close at index 240 is the t0+240-minute close. A delay of 1 enters at
index 2's OPEN (t0+1 minute), while the fixed timeout stays at index 240's CLOSE.

Stop inputs are percentage points: 1.5 means 1.5% of the actual entry price.
Primary delay=0 enters at paths[:,0,3]. Delayed entry recenters both levels on
paths[:,delay+1,0]. The entry minute participates in the bracket scan.

Gap stops fill at adverse open; favorable gap targets are capped at target.
When both levels touch within a minute with neither crossed at open, stop wins.
A stopped trade is never restored because a later candle recovers.
"""
from __future__ import annotations
import numpy as np

_OUTCOMES = np.array(['timeout', 'sl', 'tp', 'sl_gap',
                      'tp_gap_capped', 'sl_ambiguous'])


def _inputs(paths, horizon, delay):
    paths = np.asarray(paths, dtype=float)
    if paths.ndim != 3 or paths.shape[2] != 4:
        raise ValueError('paths must have shape (N, T, 4), OHLC columns')
    if not isinstance(horizon, (int, np.integer)) or not 1 <= horizon < paths.shape[1]:
        raise ValueError('horizon must index an available future minute close')
    if not isinstance(delay, (int, np.integer)) or not 0 <= delay < horizon:
        raise ValueError('delay must be an integer from 0 through horizon-1')
    relevant = paths[:, :horizon+1, :]
    if not np.all(np.isfinite(relevant)) or np.any(relevant <= 0):
        raise ValueError('all relevant OHLC prices must be finite and positive')
    return paths


def _run(paths, stop_grid, sign, rr, horizon, delay):
    """Internal (receiver, geometry) grid; paths are never materialized per donor."""
    n = len(paths)
    stops = np.asarray(stop_grid, dtype=float)
    if stops.ndim != 2 or stops.shape[0] != n or not np.all(np.isfinite(stops)) or np.any(stops <= 0):
        raise ValueError('stop grid must be positive finite (N, M) percentages')
    if not np.isscalar(rr) or not np.isfinite(rr) or rr <= 0:
        raise ValueError('rr must be a positive finite scalar')
    signs = np.broadcast_to(np.asarray(sign, dtype=float), (n,)).reshape(n, 1)
    if np.any((signs != -1) & (signs != 1)):
        raise ValueError('sign must be +1/-1, scalar or length N')
    long = signs > 0
    entry = (paths[:, delay+1, 0] if delay else paths[:, 0, 3])[:, None]
    sl_px = entry * (1 - signs * stops / 100)
    tp_px = entry * (1 + signs * stops * rr / 100)
    shape = stops.shape
    outcome_code = np.zeros(shape, dtype=np.int8)
    exit_price = np.broadcast_to(paths[:, horizon, 3, None], shape).copy()
    held = np.full(shape, horizon-delay, dtype=np.int32)
    exit_index = np.full(shape, horizon, dtype=np.int32)
    ambiguous = np.zeros(shape, dtype=bool)
    gaps = np.zeros(shape, dtype=bool)

    for j in range(delay+1, horizon+1):
        active = outcome_code == 0
        if not np.any(active):
            break
        op, hi, lo = [paths[:, j, col, None] for col in range(3)]
        open_sl = active & np.where(long, op <= sl_px, op >= sl_px)
        open_tp = active & ~open_sl & np.where(long, op >= tp_px, op <= tp_px)
        touch_sl = np.where(long, lo <= sl_px, hi >= sl_px)
        touch_tp = np.where(long, hi >= tp_px, lo <= tp_px)
        intraday = active & ~open_sl & ~open_tp
        both = intraday & touch_sl & touch_tp
        stopped = open_sl | (intraday & touch_sl)
        targeted = open_tp | (intraday & ~touch_sl & touch_tp)
        hit = stopped | targeted
        exit_price = np.where(stopped, np.where(open_sl, op, sl_px), exit_price)
        exit_price = np.where(targeted, tp_px, exit_price)
        outcome_code[stopped] = 1
        outcome_code[targeted] = 2
        outcome_code[open_sl] = 3
        outcome_code[open_tp] = 4
        outcome_code[both] = 5
        held[hit] = j-delay
        exit_index[hit] = j
        ambiguous |= both
        gaps |= open_sl | open_tp

    gross = signs * (exit_price / entry - 1) * 100
    # held_minutes counts minute bars through the exit bar, matching the prior
    # discovery engine. Gaps occur at that minute's open; their exact elapsed
    # clock is one minute less. Intrabar touch time is unknown inside its minute.
    elapsed = np.where(gaps, held-1, held)
    return {
        'gross_pct': gross,
        'held_minutes': held,
        'outcome': _OUTCOMES[outcome_code],
        'exit_price': exit_price,
        'ambiguous': ambiguous,
        'entry_price': np.broadcast_to(entry, shape).copy(),
        'exit_index': exit_index,
        'gap': gaps,
        'exit_elapsed_minutes': elapsed,
        'exit_at_open': gaps.copy(),
    }


def bracket_batch(paths, stop_pct, sign=-1, rr=2.0, horizon=240, delay=0):
    """Replay one bracket per window; return a dict of length-N arrays.

    stop_pct: scalar or N supplied strategy stop distances in percentage points.
    sign: -1 short / +1 long; scalar or N-vector.
    rr: target distance / stop distance, default 2.
    horizon: timeout close index measured from original t0, default 240.
    delay: 0=original visible close; 1/5=corresponding later minute OPEN.

    Returns gross_pct, held_minutes, outcome, exit_price, ambiguous and additional
    audit arrays. held_minutes is a conservative minute-bar count through exit;
    exit_elapsed_minutes gives exact elapsed time for gaps and the upper bound
    for intraminute touches. No costs are deducted by this engine.
    """
    paths = _inputs(paths, horizon, delay)
    stops = np.broadcast_to(np.asarray(stop_pct, dtype=float), (len(paths),))
    result = _run(paths, stops[:, None], sign, rr, horizon, delay)
    return {name: values[:, 0] for name, values in result.items()}


def donor_matrix(paths, atr_pct, donor_stop_atr_ratio, rr=2.0,
                 multiplier=1.5, horizon=240, delay=0):
    """Return gross payoff matrix [receiver window, donor decision geometry].

    The donor's original AI stop/ATR ratio is transplanted to the receiver:
        strategy_stop_pct[i,j] = multiplier * ATR_pct[i] * donor_ratio[j]
    Every matrix element replays an actual SHORT bracket on receiver i's path.
    The caller permutes the paired action label and donor column within the
    frozen strata; skipped signals and costs are handled by the caller.
    NxM is supported; usual validation input is NxN. No repeated OHLC cube is
    built, and no identity/date/outcome data is read from disk.
    """
    paths = _inputs(paths, horizon, delay)
    atr = np.asarray(atr_pct, dtype=float)
    donors = np.asarray(donor_stop_atr_ratio, dtype=float)
    if atr.shape != (len(paths),) or donors.ndim != 1:
        raise ValueError('atr_pct must have length N; donor ratios must be 1-D')
    if not np.all(np.isfinite(atr)) or np.any(atr <= 0):
        raise ValueError('ATR values must be positive finite percentages')
    if not np.all(np.isfinite(donors)) or np.any(donors <= 0):
        raise ValueError('donor ratios must be positive and finite')
    if not np.isscalar(multiplier) or not np.isfinite(multiplier) or multiplier <= 0:
        raise ValueError('multiplier must be a positive finite scalar')
    stops = multiplier * atr[:, None] * donors[None, :]
    return _run(paths, stops, -1, rr, horizon, delay)['gross_pct']
