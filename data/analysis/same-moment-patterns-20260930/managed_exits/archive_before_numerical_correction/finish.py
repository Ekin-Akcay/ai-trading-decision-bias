"""Export the already-scored frozen family and its descriptive research gate."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = ROOT / 'data/analysis/new-angles-20260930/target_exhaustion/windows.csv'
summary = json.loads((HERE / 'summary.json').read_text())
contrasts = json.loads((HERE / 'matched_control_differences.json').read_text())
vectors = np.load(HERE / 'policy_vectors.npz')
windows = pd.read_csv(SOURCE)
assert np.array_equal(windows.window_id.astype(str), vectors['window_id'])
policies = vectors['policy'].astype(str)
roles = np.array(['candidate'] * 3 + ['control'] * 2)
returns = vectors['gross_pct'].T
assert returns.shape == (1020, 5) and np.isfinite(returns).all()
quarter = pd.to_datetime(windows.entry_time).dt.to_period('Q').astype(str).to_numpy(dtype=str)
assert np.array_equal(quarter, windows.quarter.astype(str))
destination = HERE / 'joint_family_vectors.npz'
np.savez_compressed(
    destination, returns_pct=returns, selected=np.ones(returns.shape, dtype=bool),
    policy=policies, role=roles, window_id=vectors['window_id'], quarter=quarter,
    entry_time=vectors['entry_time'], asset=vectors['asset'], cohort=vectors['cohort'],
    position_side=vectors['position_side'], calendar_block=vectors['calendar_block'],
)
manifest = {
    'file': str(destination.relative_to(ROOT)),
    'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
    'returns_pct_shape': list(returns.shape), 'axis_order': ['window', 'policy'],
    'units': 'gross percentage points per original position notional',
    'selected': 'All 1020 opportunities are entered by every policy.',
    'policy': policies.tolist(), 'role': roles.tolist(),
    'window_id': 'Identical order to target_exhaustion/windows.csv.',
    'quarter': 'UTC entry-time calendar quarter, YYYYQn; shared with source windows.csv.',
    'new_model_calls': 0, 'source_files_modified': False,
}
(HERE / 'joint_family_schema.json').write_text(json.dumps(manifest, indent=2) + '\n')

gate = {
    'phase': 'reused_outcome_discovery_exit_extension',
    'conclusion': 'No candidate selected. All three managed exits lose gross and underperform both matched controls.',
    'new_model_calls': 0, 'remaining_snapshot_credits_unchanged': 29,
    'windows': 1020, 'calendar_blocks': 645, 'quarters': 25,
    'primary_research_candidates': [], 'fresh_validation_claim': False,
    'ai_increment_claim': False,
    'controls_are_not_promoted_as_new_candidates': True,
    'policies': {},
}
for policy in policies[:3]:
    value = summary['policies'][policy]
    gate['policies'][policy] = {
        'mean_gross_pct': value['pooled']['mean_gross_pct'],
        'block_ci95': value['block_ci95'], 'quarter_ci95': value['quarter_ci95'],
        'chronological_half_means_pct': [row['mean_gross_pct'] for row in value['halves']],
        'positive_cohorts': sum(row['mean_gross_pct'] > 0 for row in value['cohorts'].values()),
        'exclude_best3_mean_pct': value['pooled']['exclude_best3_mean_pct'],
        'matched_control_differences_pct': {
            row['control']: row['all']['mean_gross_pct'] for row in contrasts if row['candidate'] == policy
        },
        'discovery_triage': value['discovery_triage'],
    }
(HERE / 'CANDIDATE_GATE.json').write_text(json.dumps(gate, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
