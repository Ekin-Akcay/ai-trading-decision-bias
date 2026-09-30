from pathlib import Path
import pandas as pd,numpy as np
H=Path(__file__).resolve().parent
x=pd.read_csv(H/'per_trade_policies.csv');x=x[(x.kind=='bracket') & (x.effective_sign!=0)].copy()
x['risk_width_pct']=x.stop_pct*x.scale*100
x['gross_r']=x.gross_pct/x.risk_width_pct
x['net_r']=x.net_pct/x.risk_width_pct
x['fee_r']=.2/x.risk_width_pct
rows=[]
for (protocol,scale),g in x.groupby(['protocol','scale']):
 k=g[g.gross_r.notna()]
 assert np.allclose(k.gross_r-k.fee_r,k.net_r)
 rows.append(dict(protocol=protocol,bracket_scale=scale,active_decisions=len(g),known_decisions=len(k),windows=g.window_id.nunique(),ambiguous=int((g.outcome=='ambiguous').sum()),tp_count=int((k.outcome=='tp').sum()),sl_count=int((k.outcome=='sl').sum()),tp_rate_known=float((k.outcome=='tp').mean()),mean_gross_r=k.gross_r.mean(),mean_fee_r_same_known_rows=k.fee_r.mean(),mean_net_r=k.net_r.mean(),equal_window_mean_gross_r=k.groupby('window_id').gross_r.mean().mean(),equal_window_mean_net_r=k.groupby('window_id').net_r.mean().mean(),median_risk_width_pct=k.risk_width_pct.median()))
r=pd.DataFrame(rows).sort_values(['protocol','bracket_scale'],ascending=[True,False]);r.to_csv(H/'posthoc_risk_normalization.csv',index=False);(H/'posthoc_risk_normalization.json').write_text(r.to_json(orient='records',indent=2));print(r.to_string(index=False))
