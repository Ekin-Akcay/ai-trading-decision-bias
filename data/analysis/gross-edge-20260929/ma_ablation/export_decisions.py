"""Original agent brackets; arm identifiers preserve intentionally paired opinions."""
from pathlib import Path
import sys,json
import pandas as pd,numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'data/analysis/reversal-deep-20260929/risk'))
from validation_engine import bracket_batch
run=Path(json.loads((HERE/'run.json').read_text())['run_dir']);assert (run/'ALLOW_EVALUATION').exists()
m=json.loads((run/'manifest.json').read_text());d=pd.read_csv(run/'window_results.csv').sort_values('case').reset_index(drop=True)
p=np.load(run/'paths.npz');positions={int(b):i for i,b in enumerate(p['block'])};paths=p['paths'][[positions[int(b)] for b in d.block]]
dec={r['case']:r for r in map(json.loads,(run/'accepted_decisions.jsonl').read_text().splitlines())};assert len(dec)==len(d)==270
out=bracket_batch(paths,d.stop_pct.to_numpy()*100,sign=np.where(d.action=='long',1,-1),rr=2,horizon=360)
records=[]
for i,row in d.iterrows():
    r=row.to_dict();source=dec[int(row['case'])]
    r.update(model='gpt-5.6-terra-agent',model_runtime='gpt-5.6-terra',run_id=m['run_id'],experiment='paired_MA_intervention_SOL90',
             stimulus_condition=str(row.arm),independent_repeat='MA_B'==row.arm,evaluation_horizon_minutes=360,evaluation_horizon_hours=6,
             cost_bps_roundtrip=0,fee_assumption='zero costs by user instruction; research only',outcome=str(out['outcome'][i]),
             entry_price=float(out['entry_price'][i]),exit_price=float(out['exit_price'][i]),minutes_held=int(out['held_minutes'][i]),
             exit_ts=str(pd.Timestamp(row.entry_time)+pd.Timedelta(minutes=int(out['exit_index'][i])-(1 if out['exit_at_open'][i] else 0))),
             pnl_gross_pct=float(out['gross_pct'][i]),pnl_net_pct=float(out['gross_pct'][i]),ambiguous=bool(out['ambiguous'][i]),gap=bool(out['gap'][i]),
             thread_id=source['thread_id'],agent_path=source['agent_path'],ts_decided=source['ts_decided'],
             distinction='Original AI bracket, not L048. Same underlying window intentionally appears in three arms; key by run_id+case or window_id+arm, never treat as three independent market samples.')
    records.append(r)
text=''.join(json.dumps(r,allow_nan=False)+'\n' for r in records)
target=ROOT/'data/sim/decisions'/f'{m["run_id"]}.jsonl'
if target.exists():assert target.read_text()==text
else:target.write_text(text)
(run/'original_AI_trades.jsonl').write_text(text)
print(json.dumps({'canonical_ledger':str(target),'records':270,'unique_windows':90,'arm_required_for_unique_key':True}))
