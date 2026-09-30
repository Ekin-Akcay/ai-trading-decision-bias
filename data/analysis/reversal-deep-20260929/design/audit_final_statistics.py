"""Independent numerical validation, authorized after all 280 outputs collected.

Does not import the production evaluator or bracket engine. Replays donor
brackets using first-touch matrices, then reconstructs bootstrap/permutation
statistics with independent summation implementations.
"""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[2]
RUN = Path(json.loads((STUDY/'run.json').read_text())['run_dir'])
assert (RUN/'ALLOW_EVALUATION').exists()
summary = json.loads((RUN/'summary.json').read_text())
manifest = json.loads((RUN/'manifest.json').read_text())
records = [json.loads(s) for s in (RUN/'accepted_decisions.jsonl').read_text().splitlines()]
records.sort(key=lambda r:r['case'])
windows = [json.loads(s) for s in (RUN/'window_results.jsonl').read_text().splitlines()]
windows.sort(key=lambda r:r['case'])
assert len(records) == len(windows) == len(manifest['cases']) == 280
N, B, COST = 280, 20000, .2
calls = json.loads((STUDY/'snapshot_budget.json').read_text())['reserved_attempts']
assert len(calls) == 280 and all(c['attempt'] == 1 for c in calls)
audit = json.loads((RUN/'isolation_audit.json').read_text())
passed = {a['agent_path'] for a in audit['audits'] if a['passed']}
assert len(passed) == 280 and all(r['agent_path'] in passed for r in records)
assert len(set(r['thread_id'] for r in records)) == 280
times = pd.DatetimeIndex([w['entry_time'] for w in manifest['cases']])
action_long = np.array([r['decision']['action']=='long' for r in records])
stop = np.array([r['decision']['stop_pct']*100 for r in records])
atr = np.array([w['atr14_pct'] for w in manifest['cases']])
ma20 = np.array([w['ma20_now'] for w in manifest['cases']])
ma50 = np.array([w['ma50_now'] for w in manifest['cases']])
raw = pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index()
path = []
for t in times:
    p = int(raw.index.searchsorted(t))-1
    path.append(raw.iloc[p:p+256][['open','high','low','close']].to_numpy(float))
path = np.array(path)
confirm = path[:,15,3] > path[:,0,3]
lgross = 100*(path[:,255,3]/path[:,16,0]-1)
lmask = ~action_long & confirm

def short_donor_payoffs(paths, percentages):
    """Independent first-touch lookup; percentages shape (receivers, donors)."""
    ans = np.empty(percentages.shape)
    for receiver, prices in enumerate(paths):
        entry = prices[0,3]
        sl = entry*(1+percentages[receiver]/100)
        tp = entry*(1-2*percentages[receiver]/100)
        op, high, low = prices[1:241,:3].T
        hit = (high[:,None] >= sl[None,:]) | (low[:,None] <= tp[None,:])
        event = hit.any(axis=0)
        first = np.argmax(hit,axis=0)
        opening, highest = op[first], high[first]
        event_exit = np.where(opening >= sl, opening,
                             np.where(opening <= tp, tp,
                                      np.where(highest >= sl, sl, tp)))
        exits = np.where(event,event_exit,prices[240,3])
        ans[receiver] = 100*(1-exits/entry)
    return ans

payoff = short_donor_payoffs(path,1.5*atr[:,None]*(stop/atr)[None,:])
sgross = payoff.diagonal()
for i,w in enumerate(windows):
    assert w['L_selected'] == bool(lmask[i]) and w['S_selected'] == bool(action_long[i])
    assert w['L_confirmed'] == bool(confirm[i])
    assert np.isclose(w['L_gross_pct'],lgross[i],rtol=0,atol=1e-11)
    assert np.isclose(w['S_gross_pct'],sgross[i],rtol=0,atol=1e-11)
    assert np.isclose(w['L_net_pct'],lgross[i]-COST,rtol=0,atol=1e-11)
    assert np.isclose(w['S_net_pct'],sgross[i]-COST,rtol=0,atol=1e-11)

# Recreate frozen draws, but evaluate each resample via multiplicity dot-products.
rng = np.random.default_rng(2026092930)
draws = rng.integers(0,N,size=(B,N))
counts = np.zeros((B,N),dtype=np.int16)
np.add.at(counts,(np.arange(B)[:,None],draws),1)
quarters = times.to_period('Q').astype(str)
labels = list(dict.fromkeys(quarters))
codes = np.array([labels.index(q) for q in quarters])
qd = len(labels)
qdraws = rng.integers(0,qd,size=(B,qd))
qcounts = np.zeros((B,qd),dtype=np.int16)
np.add.at(qcounts,(np.arange(B)[:,None],qdraws),1)
checked = {}

def eq(a,b,tol=1e-11):
    assert np.allclose(a,b,rtol=0,atol=tol,equal_nan=True),(a,b)

for key,gross,mask in [('L',lgross,lmask),('S',sgross,action_long)]:
    claimed = summary['strategies'][key]
    values = gross[mask]
    net = values-COST
    weighted = np.where(mask,gross-COST,0)
    boot_n = counts@mask.astype(float)
    boot = (counts@weighted)[boot_n>0]/boot_n[boot_n>0]
    qsum = np.array([weighted[codes==i].sum() for i in range(qd)])
    qn = np.array([mask[codes==i].sum() for i in range(qd)])
    cluster_n = qcounts@qn
    cluster = (qcounts@qsum)[cluster_n>0]/cluster_n[cluster_n>0]
    eq(values.mean(),claimed['mean_gross_pct'])
    eq(net.mean(),claimed['mean_net_pct'])
    eq(net.sum()/N,claimed['mean_net_per_opportunity_pct'])
    eq((values>0).mean(),claimed['gross_win_rate'])
    eq((net>0).mean(),claimed['net_win_rate'])
    eq(np.quantile(boot,[.025,.975]),claimed['ci95_mean_net_pct'])
    eq(np.quantile(boot,[.0125,.9875]),claimed['simultaneous_ci975_mean_net_pct'])
    eq(np.quantile(cluster,[.025,.975]),claimed['quarter_cluster_ci95_net_pct'])
    eq(np.quantile(cluster,[.0125,.9875]),claimed['quarter_cluster_ci975_net_pct'])
    ordered = net[np.argsort(times[mask])]
    thirds = np.array_split(ordered,3)
    leave_out = [(ordered.sum()-part.sum())/(len(ordered)-len(part)) for part in thirds]
    eq(leave_out,claimed['leave_one_chronological_third_out_net_means_pct'])
    eq([x.mean() for x in thirds],[x['mean_net_pct'] for x in claimed['chronological_thirds']])
    for delay in ['1','5']:
        v = np.array([w[f'{key}_delay{delay}_gross_pct'] for w in windows])[mask]-.2
        eq(v.mean(),claimed['entry_delay_sensitivity'][delay]['mean_net_pct'])
    verified_profit = (len(net)>=50 and np.quantile(boot,.0125)>0
                       and gross[mask].mean()-.3>0
                       and all(claimed['entry_delay_sensitivity'][d]['mean_net_pct']>0 for d in ['1','5']))
    assert verified_profit == claimed['passes_frozen_profit_tests']
    checked[key] = {'n':len(net),'mean_gross_pct':float(values.mean()),
                    'mean_net_pct':float(net.mean()),
                    'bootstrap_CIs_match':True,'quarter_cluster_CIs_match':True,
                    'chronological_sensitivity_matches':True,
                    'passes_frozen_profit_tests':bool(verified_profit)}

regime = np.where((ma20<=100)&(ma50<=100),'aboveboth',
                  np.where((ma20>100)&(ma50>100),'belowboth','mixed'))
era = np.where(times.year<=2021,'2020-21',np.where(times.year<=2023,'2022-23','2024-26'))
strata = np.array([a+'/'+b for a,b in zip(era,regime)])
prng = np.random.default_rng(2026092931)
permutations = np.tile(np.arange(N),(B,1))
for label in sorted(set(strata)):
    g = np.flatnonzero(strata==label)
    for_values = prng.random((B,len(g)))
    permutations[:,g] = g[np.argsort(for_values,axis=1)]

# Independently aggregate each permutation by selecting its explicit indices.
nulls = {'L':np.empty(B),'S':np.empty(B)}
for j,donors in enumerate(permutations):
    longs = action_long[donors]
    li = np.flatnonzero(~longs & confirm)
    si = np.flatnonzero(longs)
    nulls['L'][j] = (lgross[li]-COST).mean()
    nulls['S'][j] = (payoff[si,donors[si]]-COST).mean()
stored = np.load(RUN/'permutation_nulls.npz')
pvals = []
for key in ['L','S']:
    null = nulls[key]
    eq(null,stored[key])
    c = summary['strategies'][key]['AI_selection']
    observed = checked[key]['mean_net_pct']
    p = (np.count_nonzero(null>=observed-1e-14)+1)/(B+1)
    eq(null.mean(),c['conditional_null_mean_net_pct'])
    eq(observed-null.mean(),c['increment_over_conditional_null_pct'])
    eq(p,c['p_one_sided'])
    eq(np.quantile(null,[.025,.975]),c['null_ci95_pct'])
    pvals.append(p)
    checked[key].update(p_one_sided=float(p),all20000_null_draws_match=True,
                        conditional_increment_pct=float(observed-null.mean()))
# Closed-form two-hypothesis Holm, independently written.
if pvals[0]<=pvals[1]:
    corrected = [min(1,2*pvals[0]),min(1,max(2*pvals[0],pvals[1]))]
else:
    corrected = [min(1,max(pvals[0],2*pvals[1])),min(1,2*pvals[1])]
for key,p in zip(['L','S'],corrected):
    c = summary['strategies'][key]
    eq(p,c['AI_selection']['p_holm_two_tests'])
    ai_pass = checked[key]['conditional_increment_pct']>0 and p<.05
    primary = checked[key]['passes_frozen_profit_tests'] and ai_pass
    single_period = all(v>0 for v in c['leave_one_chronological_third_out_net_means_pct'])
    assert primary == c['passes_frozen_primary_tests']
    assert (primary and single_period) == c['verified_AI_strategy']
    checked[key].update(p_holm_two_tests=float(p),verification_labels_match=True)
result = {'passed':True,'audited_at':datetime.now(timezone.utc).isoformat(),
          'run_id':manifest['run_id'],'model_calls':len(calls),'valid_decisions':len(records),
          'independent_native_data_primary_trade_checks':560,
          'independent_first_touch_donor_brackets':N*N,
          'bootstrap_draws':B,'permutations':B,
          'production_evaluator_or_engine_imported':False,
          'zero_count_and_audit_guards_reviewed':True,
          'strategies':checked,
          'conclusion':'Both primary net means are slightly positive but neither strategy passes frozen profit or AI-value confirmation.'}
(HERE/'validation_final_statistics_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
