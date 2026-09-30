"""Independent precollection audit: source coverage/features only; no outcomes."""
from pathlib import Path
import hashlib, json, sys
from datetime import datetime, timezone
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from nai.sim import build_snapshot, sim_prompt, window_id

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
run = Path(json.loads((STUDY / 'run.json').read_text())['run_dir'])
m = json.loads((run / 'manifest.json').read_text())
assert len(m['cases']) == 280
assert m['authorized_cases'] == list(range(1, 281))
assert m['models'] == ['gpt-5.6-terra'] and m['reasoning_effort'] == 'medium'
assert m['seed'] == 20260929 and m['max_attempts'] == 3
assert m['protocol_sha256'] == sha(ROOT / m['protocol_file'])
assert not list((run / 'cli_attempts').glob('*')), 'Collection already started'
assert not json.loads((STUDY / 'snapshot_budget.json').read_text())['reserved_attempts']
assert json.loads((STUDY / 'snapshot_budget.json').read_text())['authorized_maximum_attempts'] == 300
old = json.loads((ROOT / 'data/sim/rules2to1-openai-20260926T072414Z/manifest.json').read_text())
assert m['contract'] == old['contract']
preservation = {p: sha(ROOT / p) == h for p, h in m['original_sha256'].items()}
assert all(preservation.values()), preservation
prior = set()
for p in (ROOT / 'data/sim/decisions').glob('*.jsonl'):
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get('asset') == 'SOL-USD':
                prior.add(pd.Timestamp(r['window_end_ts']) + pd.Timedelta(minutes=15))
assert len(prior) == 156
assert sorted(prior) == list(pd.to_datetime(m['prior_SOL_entry_times']))
px = pd.read_csv(ROOT / 'data/raw/intraday/SOL-USD_15m.csv.gz', index_col=0, parse_dates=True).sort_index()
minute = pd.read_csv(ROOT / 'data/raw/intraday/SOL-USD_1m.csv.gz', index_col=0, parse_dates=True).sort_index()
assert px.index.is_unique and minute.index.is_unique
times = pd.DatetimeIndex([w['entry_time'] for w in m['cases']]).as_unit('ns')
oldtimes = pd.DatetimeIndex(sorted(prior)).as_unit('ns')
assert len(set(times)) == 280
assert len(set(w['window_id'] for w in m['cases'])) == 280
new_gaps = np.diff(np.sort(times.asi8)) / 3600e9
assert new_gaps.min() >= 74
deltas = (times.asi8[:, None] - oldtimes.asi8[None, :]) / 3600e9
assert not ((deltas > -74) & (deltas < 122)).any()
counts = dict(aboveboth=0, belowboth=0, mixed=0)
for n, w in enumerate(m['cases'], 1):
    ts, entry = pd.Timestamp(w['window_end_ts']), pd.Timestamp(w['entry_time'])
    assert w['case'] == n and w['asset'] == 'SOL-USD' and w['visible_bars'] == 40
    assert entry == ts + pd.Timedelta(minutes=15)
    assert w['window_id'] == window_id('SOL-USD', ts)
    i = px.index.get_loc(ts)
    history = px.iloc[i-199:i+1]
    assert history.index.equals(pd.date_range(ts-pd.Timedelta(minutes=199*15), periods=200, freq='15min'))
    e = int(minute.index.searchsorted(entry))
    covered = minute.iloc[e-1:e+1440]
    assert covered.index.equals(pd.date_range(entry-pd.Timedelta(minutes=1), periods=1441, freq='1min'))
    # Integrity only. No future returns, price moves, or strategy outcomes calculated.
    for data in [history, covered]:
        values = data[['open', 'high', 'low', 'close']].to_numpy(float)
        assert np.isfinite(values).all() and (values > 0).all()
        assert (values[:, 1] >= np.max(values[:, [0, 2, 3]], axis=1)).all()
        assert (values[:, 2] <= np.min(values[:, [0, 1, 3]], axis=1)).all()
    assert float(history.close.iloc[-1]) == float(covered.close.iloc[0]) == w['price_real']
    snap = build_snapshot(px, ts, 40, 200)
    prompt = sim_prompt(snap)
    folder = Path(w['stimulus_dir'])
    assert (folder / 'stats.txt').read_text() == prompt
    assert (folder / 'input.txt').read_text() == m['contract'] + '\n\n' + prompt
    assert sha(folder / 'stats.txt') == w['prompt_sha256']
    assert sha(folder / 'input.txt') == w['input_sha256']
    assert sha(folder / 'chart.png') == w['image_sha256']
    assert 'SOL' not in prompt and str(ts.date()) not in prompt
    for field in ['price_real', 'sigma_vis_pct', 'sigma_2d_pct', 'atr14_pct', 'ret_vis_pct', 'ma20_now', 'ma50_now', 'vol24_ratio']:
        assert np.isclose(snap[field], w[field], rtol=1e-13, atol=1e-13), field
    above20, above50 = snap['ma20_now'] <= 100, snap['ma50_now'] <= 100
    regime = 'aboveboth' if above20 and above50 else 'belowboth' if not above20 and not above50 else 'mixed'
    counts[regime] += 1

# Independently reproduce exact frozen random ordering and selection.
ns = (px.index + pd.Timedelta(minutes=15)).as_unit('ns').asi8
mi = minute.index.as_unit('ns').asi8
oldns = oldtimes.asi8
pos = np.searchsorted(oldns, ns)
before = np.where(pos > 0, ns-oldns[np.clip(pos-1, 0, len(oldns)-1)], np.inf)
after = np.where(pos < len(oldns), oldns[np.clip(pos, 0, len(oldns)-1)]-ns, np.inf)
static_ok = (before >= 122*3600e9) & (after >= 74*3600e9)
ep = np.searchsorted(mi, ns)
end = ep + 1440
bounded = (ep > 0) & (end <= len(mi))
ep = np.clip(ep, 1, len(mi)-1)
end = np.minimum(end, len(mi))
bad = minute[['open','high','low','close']].isna().any(axis=1).to_numpy()
badprefix = np.r_[0, np.cumsum(bad)]
gapprefix = np.r_[0, np.cumsum(np.r_[False, np.diff(mi) != 60e9])]
histprefix = np.r_[0, np.cumsum(np.r_[False, np.diff(ns) != 900e9])]
i = np.arange(len(px))
static_ok &= bounded & (mi[ep] == ns) & (mi[ep-1] == ns-60e9)
static_ok &= (badprefix[end]-badprefix[ep-1] == 0) & (gapprefix[end]-gapprefix[ep] == 0)
static_ok &= histprefix[i+1]-histprefix[np.maximum(i-199,0)+1] == 0
selected = []
for j in np.random.default_rng(20260929).permutation(np.arange(200,len(px))):
    t = ns[j]
    if not static_ok[j]:
        continue
    if selected and np.min(abs(np.asarray(selected)-t)) < 74*3600e9:
        continue
    selected.append(t)
    if len(selected) == 280:
        break
assert np.array_equal(np.asarray(selected), times.asi8), 'Selection/order not reproducible'
result = {
    'passed': True, 'audited_at': datetime.now(timezone.utc).isoformat(),
    'run_id': m['run_id'], 'protocol_sha256': m['protocol_sha256'],
    'prepare_sha256': sha(STUDY/'prepare_validation.py'),
    'cases': 280, 'prior_unique_SOL_entries': 156,
    'new_new_min_separation_hours': float(new_gaps.min()),
    'new_after_old_min_separation_hours': float(deltas[deltas>=0].min()),
    'new_before_old_min_separation_hours': float((-deltas[deltas<0]).min()),
    'exact_seed_and_case_order_reproduced': True,
    'all200_bar_histories_contiguous': True,
    'all1441_minute_timestamps_contiguous': True,
    'selected_OHLC_finite_positive_and_well_formed': True,
    'all280_prompts_reconstructed_from_preentry_data': True,
    'all840_stimulus_hashes_match': True,
    'protocol_hash_matches': True, 'unchanged_v2_contract': True,
    'source_hashes_preserved': len(preservation),
    'regime_counts': counts, 'model_calls_at_audit': 0,
    'global300_call_reservation_lock_reviewed': True,
    'forward_returns_or_strategy_outcomes_inspected': False,
    'limitations': ['Historical unused-window sample; not live or unknown-to-model-training',
                   'Conditional permutations assume within-stratum exchangeability; not causal attribution',
                   '280 windows may leave rare-trigger profitability statistically inconclusive']
}
(HERE/'validation_precollection_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
