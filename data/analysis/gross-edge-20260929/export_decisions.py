"""Save original model brackets separately from the tested reversal strategies."""
from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'data/analysis/reversal-deep-20260929/risk'))
from validation_engine import bracket_batch

def main():
    run=Path(json.loads((HERE/'run.json').read_text())['run_dir'])
    assert (run/'ALLOW_EVALUATION').exists()
    m=json.loads((run/'manifest.json').read_text())
    d=pd.read_csv(run/'window_results.csv')
    paths=np.load(run/'paths.npz')['paths']
    dec={r['case']:r for r in map(json.loads,(run/'accepted_decisions.jsonl').read_text().splitlines())}
    assert len(d)==len(paths)==len(dec)==500
    original=bracket_batch(paths,d.stop_pct.to_numpy()*100,sign=np.where(d.action=='long',1,-1),rr=2,horizon=360)
    rows=[]
    for i,r in d.iterrows():
        out=r.to_dict();case=int(r['case']);source=dec[case]
        out.update(model='gpt-5.6-terra-agent',model_runtime='gpt-5.6-terra',run_id=m['run_id'],experiment='gross_edge_fresh_target',protocol='forced_2to1_no_flat_MA_present',
                   evaluation_horizon_minutes=360,evaluation_horizon_hours=6,cost_bps_roundtrip=0,fee_assumption='zero costs by user instruction; historical research only',
                   outcome=str(original['outcome'][i]),entry_price=float(original['entry_price'][i]),exit_price=float(original['exit_price'][i]),
                   minutes_held=int(original['held_minutes'][i]),exit_ts=str(pd.Timestamp(r.entry_time)+pd.Timedelta(minutes=int(original['exit_index'][i])-(1 if original['exit_at_open'][i] else 0))),
                   pnl_gross_pct=float(original['gross_pct'][i]),pnl_net_pct=float(original['gross_pct'][i]),
                   ambiguous=bool(original['ambiguous'][i]),gap=bool(original['gap'][i]),thread_id=source['thread_id'],agent_path=source['agent_path'],ts_decided=source['ts_decided'],
                   distinction='This is the original AI bracket, not either L048 or S508 reversal trade. Those positions are in strategy_trades.jsonl.')
        rows.append(out)
    target=ROOT/'data/sim/decisions'/f'{m["run_id"]}.jsonl'
    content=''.join(json.dumps(r,allow_nan=False)+'\n' for r in rows)
    if target.exists():assert target.read_text()==content,'Refuse to overwrite different canonical data'
    else:target.write_text(content)
    (run/'original_AI_trades.jsonl').write_text(content)
    print(json.dumps({'canonical_ledger':str(target),'records':len(rows),'horizon_minutes':360,'cost_bps_roundtrip':0}))

if __name__=='__main__':main()
