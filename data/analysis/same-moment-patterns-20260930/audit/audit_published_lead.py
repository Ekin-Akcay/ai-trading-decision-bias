from pathlib import Path
from datetime import datetime,timezone
import json,re
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;P=H.parent;ROOT=H.parents[3]
def eq(a,b):assert np.allclose(a,b,rtol=0,atol=1e-10,equal_nan=True),(a,b)
w=pd.read_csv(P/'volume_reaction/features.csv');v=np.load(P/'volume_reaction/vectors.npz');paths=np.load(ROOT/'data/analysis/new-angles-20260930/target_exhaustion/paths.npz')['paths'];j=list(v['policies']).index('quiet_up_extension_short__noAI');take=v['selected'][:,j];assert take.sum()==56
csv=pd.read_csv(P/'quiet_rally_trades.csv');assert len(csv)==56 and set(csv.window_id)==set(w.window_id[take]);page=(P/'index.html').read_text();payload=json.loads(re.search(r'const trades=(.*);\n',page).group(1));assert len(payload)==56
for t in payload:
 i=int(np.flatnonzero(w.window_id.eq(t['window']).to_numpy())[0]);row=csv[csv.window_id==t['window']].iloc[0];assert t['AI']==w.action[i] and t['reason']==w.reason[i] and t['asset']==w.asset[i];eq(t['entryPrice'],paths[i,31,0]);eq(t['exitPrice'],paths[i,150,3]);eq(t['gross'],v['returns'][i,j]);eq(t['volume'],w.volume_ratio[i]);eq(row.gross_pct,t['gross']);eq(t['curve'],np.round(np.r_[100.,paths[i,1:151,3]/paths[i,1,0]*100],5));eq(t['tradeEntry'],paths[i,31,0]/paths[i,1,0]*100);eq(t['tradeExit'],paths[i,150,3]/paths[i,1,0]*100)
for link in re.findall(r'href="([^"]+)"',page):
 if not link.startswith(('http','#')):assert (P/link).exists(),link
r=v['returns'][take,j];out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'selected_csv_and_interactive_trade_payloads_checked':56,'all_reasons_action_labels_and_prices_match':True,'all151_point_price_curves_match_native_cache':True,'all_local_report_links_resolve':True,'gross_mean_pct':float(r.mean()),'median_pct':float(np.median(r)),'wins':int((r>0).sum()),'winner_mean_pct':float(r[r>0].mean()),'loser_mean_pct':float(r[r<0].mean()),'profit_factor':float(r[r>0].sum()/-r[r<0].sum())};(H/'published_lead_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
