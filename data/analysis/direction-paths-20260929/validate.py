"""Independent raw-bar, coverage, provenance and report validation."""
from pathlib import Path
import json,hashlib,re
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
w=pd.read_csv(HERE/'windows.csv');d=pd.read_csv(HERE/'decisions_enriched.csv');a=json.loads((HERE/'dataset_audit.json').read_text());m=json.loads((HERE/'analysis_metadata.json').read_text());paths=np.load(HERE/'minute_paths.npz')
assert len(w)==120 and len(d)==1052 and d.decision_id.is_unique
assert d.main.sum()==1000 and d[d.main].window_id.nunique()==100
assert len(d[d.main].groupby(['protocol','model']))==10
assert (d[d.main].groupby(['protocol','model']).size()==100).all()
assert w.all_1440_complete.all() and (w.valid_minutes==1440).all()
checks=[];errors=[]
for asset,g in w.groupby('asset'):
    native=pd.read_csv(ROOT/f'data/raw/intraday/{asset}_15m.csv.gz',index_col=0,parse_dates=True)
    for r in g.itertuples():
        ts=pd.Timestamp(r.window_end_ts);entry=native.loc[ts,'close'];assert abs(entry-r.price_real)<1e-8
        for h in [15,30,45,60,75,90,105]:
            expected=(native.loc[ts+pd.Timedelta(minutes=h),'close']/entry-1)*100
            observed=paths[r.window_id][h-1,3]
            errors.append(abs(expected-observed));assert abs(expected-observed)<1e-8,(r.window_id,h,expected,observed)
            checks.append([r.window_id,h])
source_fail=[]
for rel,expected in a['source_sha256'].items():
    actual=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
    if actual!=expected:source_fail.append(rel)
assert not source_fail,source_fail
main=w[w['case'].notna()];pairs=0
for i,r in main.iterrows():
    for j,s in main.iterrows():
        if i>=j:continue
        if abs((pd.Timestamp(r.entry_time)-pd.Timestamp(s.entry_time)).total_seconds())<=72*3600:
            assert m['folds_by_window'][r.window_id]==m['folds_by_window'][s.window_id];pairs+=1
page=(HERE/'index.html').read_text();packet=json.loads(re.search(r'<script id="research-data" type="application/json">(.*?)</script>',page,re.S).group(1))
assert len(packet['windows'])==120 and sum(len(x['decisions']) for x in packet['windows'])==1052
assert all(len(x['path'])==1440 for x in packet['windows'])
assert all((HERE/x['image']).is_file() for x in packet['windows'])
result={'status':'passed','ai_decisions':len(d),'main_decisions':int(d.main.sum()),'unique_windows':len(w),'main_windows':100,'native_15m_future_close_checks':len(checks),'max_abs_future_close_error_percentage_points':max(errors),'entry_price_checks':len(w),'complete_1440_minute_windows':int(w.all_1440_complete.sum()),'unchanged_source_files':len(a['source_sha256']),'source_hash_mismatches':source_fail,'nearby_72h_pairs_kept_in_same_CV_fold':pairs,'report_windows':len(packet['windows']),'report_decisions':sum(len(x['decisions']) for x in packet['windows']),'original_chart_links_valid':True,'browser_preview_verified':False,'browser_preview_note':'Local-file URL was blocked by browser policy; no alternate browser route attempted.'}
(HERE/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
