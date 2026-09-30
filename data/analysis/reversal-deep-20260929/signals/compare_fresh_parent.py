"""Compare root's completed fresh L ledger to the independent native replay."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from validate_fresh_long import resolve_run,compare_parent,HERE

run=resolve_run()
own=pd.read_csv(HERE/'fresh_long_independent_trades.csv')
parent=pd.read_json(run/'window_results.jsonl',lines=True,convert_dates=False)
mapping={
    'window_id':'window_id','ai_action':'ai_action','L_selected':'L_selected',
    'L_confirmed':'positive_confirmation',
    'L_gross_pct':'hypothetical_long_delay0_gross_pct',
    'L_net_pct':'hypothetical_long_delay0_net20_pct',
    'L_entry_price':'entry_delay0_px','L_exit_price':'exit_px',
    'L_delay1_gross_pct':'hypothetical_long_delay1_gross_pct',
    'L_delay5_gross_pct':'hypothetical_long_delay5_gross_pct',
    'original_entry_time':'original_entry_time','ma20_now':'ma20_now','ma50_now':'ma50_now'}
audit=compare_parent(own,parent,mapping)
summary=json.loads((run/'summary.json').read_text())
result=summary['strategies']['L'];selected=own[own.L_selected]
assert result['n']==len(selected)
assert abs(selected.L_delay0_gross_pct.mean()-result['mean_gross_pct'])<1e-8
assert abs(selected.L_delay0_net20_pct.mean()-result['mean_net_pct'])<1e-8
assert result['gross_positive']==int((selected.L_delay0_gross_pct>0).sum())
assert result['net_positive']==int((selected.L_delay0_net20_pct>0).sum())
for delay in [1,5]:
    root=result['entry_delay_sensitivity'][str(delay)]
    assert abs(selected[f'L_delay{delay}_gross_pct'].mean()-root['mean_gross_pct'])<1e-8
for col,key in [('control_selected','L_without_AI_confirmation'),('below_ma20_control_selected','L_below_MA20_confirmation')]:
    vals=own.loc[own[col],'hypothetical_long_delay0_net20_pct']
    assert len(vals)==summary['controls'][key]['n']
    assert abs(vals.mean()-summary['controls'][key]['mean_net_pct'])<1e-8
audit.update(run_id=summary['run_id'],L_selected=len(selected),L_mean_gross_pct=selected.L_delay0_gross_pct.mean(),L_mean_net_pct=selected.L_delay0_net20_pct.mean(),L_gross_wins=int((selected.L_delay0_gross_pct>0).sum()),L_net_wins=int((selected.L_delay0_net20_pct>0).sum()),L_delay1_net_pct=selected.L_delay1_net20_pct.mean(),L_delay5_net_pct=selected.L_delay5_net20_pct.mean(),L_control_count=int(own.control_selected.sum()),L_control_mean_net_pct=own.loc[own.control_selected,'hypothetical_long_delay0_net20_pct'].mean(),L_below_MA20_control_count=int(own.below_ma20_control_selected.sum()),summary_counts_returns_delays_controls_match=True,root_fields=mapping)
(HERE/'fresh_parent_comparison.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit,indent=2))
