"""Record the independently identified numerical correction, without reselecting rules."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ARCHIVE = HERE / 'archive_before_numerical_correction'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

manifest = json.loads((ARCHIVE / 'ARCHIVE_MANIFEST.json').read_text())
assert all(sha(ARCHIVE / k) == v['sha256'] for k,v in manifest.items())
assert sha(HERE / 'PLAN.md') == sha(ARCHIVE / 'PLAN.md')
old_freeze = json.loads((ARCHIVE / 'SCORING_FREEZE.json').read_text())
new_freeze = json.loads((HERE / 'SCORING_FREEZE.json').read_text())
assert old_freeze['source_sha256'].keys() == new_freeze['source_sha256'].keys()
for name, expected in new_freeze['source_sha256'].items():
    assert sha(ROOT / name) == expected
    if 'target_exhaustion/' in name or name.endswith('/PLAN.md') or name.endswith('/run.py'):
        assert expected == old_freeze['source_sha256'][name]
old = pd.read_csv(ARCHIVE / 'trade_ledger.csv')
new = pd.read_csv(HERE / 'trade_ledger.csv')
assert old[['window_id','policy']].equals(new[['window_id','policy']])
diff = new.gross_pct - old.gross_pct
time_changed = new.exit_minute_index != old.exit_minute_index
economic_changed = diff.abs() > 1e-10
assert economic_changed.sum() == 1 and time_changed.sum() == 5
assert set(new.loc[time_changed, 'window_id']) == {'828f59aa38','46108acd70'}
changed = []
for i in new.index[time_changed | economic_changed]:
    changed.append({
        'policy': new.loc[i,'policy'], 'window_id': new.loc[i,'window_id'],
        'old_gross_pct': float(old.loc[i,'gross_pct']), 'new_gross_pct': float(new.loc[i,'gross_pct']),
        'difference_pp': float(diff[i]),
        'old_exit_minute': int(old.loc[i,'exit_minute_index']), 'new_exit_minute': int(new.loc[i,'exit_minute_index']),
        'payoff_changed': bool(economic_changed[i]),
    })
old_boot = np.load(ARCHIVE / 'bootstrap_arrays.npz')
new_boot = np.load(HERE / 'bootstrap_arrays.npz')
assert np.array_equal(old_boot['block_weights'],new_boot['block_weights'])
assert np.array_equal(old_boot['quarter_weights'],new_boot['quarter_weights'])
old_s = json.loads((ARCHIVE / 'summary.json').read_text())
new_s = json.loads((HERE / 'summary.json').read_text())
correction = {
    'type': 'NUMERICAL_CORRECTION', 'strategy_change': False,
    'reason': 'Inclusive price contacts missed by binary floating-point roundoff.',
    'contact_tolerance': '32 * float64_machine_epsilon * actual_entry_price',
    'new_calls': 0, 'input_and_plan_hashes_unchanged': True,
    'archive_hashes_verified': True, 'bootstrap_draws_unchanged': True,
    'economic_changes': int(economic_changed.sum()), 'timing_only_changes': int((time_changed & ~economic_changed).sum()),
    'changed_trades': changed,
    'mean_gross_pct': {name: {
        'before': old_s['policies'][name]['pooled']['mean_gross_pct'],
        'after': value['pooled']['mean_gross_pct'],
        'difference_pp': value['pooled']['mean_gross_pct'] - old_s['policies'][name]['pooled']['mean_gross_pct'],
    } for name,value in new_s['policies'].items()},
    'selected_candidates_before': [], 'selected_candidates_after': [],
    'original_freeze_sha256': sha(ARCHIVE / 'SCORING_FREEZE.json'),
    'corrected_freeze_sha256': sha(HERE / 'SCORING_FREEZE.json'),
    'corrected_joint_vectors_sha256': sha(HERE / 'joint_family_vectors.npz'),
}
(HERE / 'NUMERICAL_CORRECTION.json').write_text(json.dumps(correction,indent=2)+'\n')
print(json.dumps(correction,indent=2))
