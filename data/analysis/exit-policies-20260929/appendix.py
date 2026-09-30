from pathlib import Path
import pandas as pd,numpy as np,json
H=Path(__file__).resolve().parent
x=pd.read_csv(H/'per_trade_policies.csv');keys=['bracket_1','bracket_0.75','bracket_0.5','bracket_0.25','time_15m','time_30m','time_105m'];x=x[x.policy.isin(keys)]
rows=[]
for group,f in [('pooled',x)]+list(x.groupby('protocol')):
 for (regime,action,policy),g in f.groupby(['ma_regime','action','policy']):
  a=g.groupby('window_id');gross=a.gross_pct.mean();net=a.net_pct.mean()
  rows.append(dict(group=group,ma_regime=regime,action=action,policy=policy,decisions=len(g),windows=g.window_id.nunique(),ambiguous=int((g.outcome=='ambiguous').sum()),gross_mean_pct=gross.mean(),net_mean_pct=net.mean(),net_all_lower_pct=a.net_lower_pct.mean().mean(),net_all_upper_pct=a.net_upper_pct.mean().mean(),direction_positive_rows=int((g.gross_pct>0).sum()),known_active_rows=int(((g.effective_sign!=0)&g.gross_pct.notna()).sum())))
r=pd.DataFrame(rows);r.to_csv(H/'posthoc_regime_direction.csv',index=False)
(H/'posthoc_regime_direction.json').write_text(r.to_json(orient='records',indent=2))
print(r[(r.group=='pooled') & r.policy.isin(['time_15m','time_30m','time_105m'])].to_string(index=False))
print('V2 belowbothshort',r[(r.group=='v2') & (r.action=='short') & (r.ma_regime=='below_both')].to_string(index=False))
