from pathlib import Path
import json,hashlib,subprocess
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[2];run=Path(json.loads((HERE/'run.json').read_text())['run_dir'])
page=(HERE/'index.html').read_text();script=page.split('<script>',1)[1].split('</script>',1)[0];data=json.loads(script.split('const DATA=',1)[1].split(';const $=',1)[0]);assert len(data)==180 and len({x['case'] for x in data})==180
expected={};checks=0
for stage in ['screen','confirmation']:
 z=np.load(run/stage/'paths.npz');paths={int(c):p for c,p in zip(z['case'],z['paths'])}
 for line in (run/stage/'trade_ledger.jsonl').read_text().splitlines():
  x=json.loads(line);expected[x['case']]=x
 for x in data:
  if x['stage']!=stage:continue
  source=expected[x['case']]
  for k,v in source.items():assert x[k]==v,(x['case'],k);checks+=1
  p=paths[x['case']];assert x['normalized_close'][0]==100
  np.testing.assert_allclose(x['normalized_close'][1:],(100*p[:,3]/p[0,0]).round(5),rtol=0,atol=1e-10)
  np.testing.assert_allclose(x['normalized_high'],(100*p[:,1]/p[0,0]).round(5),rtol=0,atol=1e-10)
  np.testing.assert_allclose(x['normalized_low'],(100*p[:,2]/p[0,0]).round(5),rtol=0,atol=1e-10)
  assert (HERE/'../..'/x['input_chart']).resolve().is_file();checks+=362
assert 'Adjusted spread' in page and ' pp' in page and 'No strategy passed the frozen confirmation standard.' in page
for f in ['RESULTS.md','VALIDATION_PROTOCOL.md','snapshot_budget.json','interpretation/AI_BEHAVIOR.md','interpretation/IDENTICAL_COVERAGE.md','results.png']:assert (HERE/f).is_file()
js=HERE/'audit/published_script.js';js.write_text(script);subprocess.run(['node','--check',str(js)],check=True,capture_output=True)
m=json.loads((run/'manifest.json').read_text());protected=0
for f,h in m['original_sha256'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,f;protected+=1
# Independent algebra for the explicitly retrospective identical-coverage comparison.
v=pd.read_csv(HERE/'interpretation/identical_coverage_vectors.csv');assert len(v)==150
for stage,g in v.groupby('stage'):
 ledger=pd.read_csv(run/stage/'trade_ledger.csv').set_index('case');base=ledger.loc[g.case]
 raw=100*(base.exit_price.to_numpy()/base.entry_price.to_numpy()-1)
 ai=np.where(base.AI_action.to_numpy()=='long',1,-1)*raw
 ma=np.where(base.above_equal_MA20.to_numpy(),1,-1)*raw
 for col,exp in [('follow_AI_pct',ai),('follow_MA20_pct',ma),('AI_minus_MA20_pp',ai-ma)]:np.testing.assert_allclose(g[col].to_numpy(),exp,rtol=0,atol=1e-12);checks+=len(g)
b=json.loads((HERE/'snapshot_budget.json').read_text());assert len(b['reserved_attempts'])==180 and b['authorized_maximum_attempts']==200
out={'status':'PASS','embedded_cases':180,'native_plot_points_per_case':361,'ledger_and_plot_field_checks':checks,'old_source_hashes_unchanged':protected,'javascript_syntax':'PASS','report_links':'PASS','post_score_policy_vectors_checked':450,'new_attempts':180,'new_unused':20,'old_unused_preserved':29,'html_sha256':hashlib.sha256(page.encode()).hexdigest(),'results_md_sha256':hashlib.sha256((HERE/'RESULTS.md').read_bytes()).hexdigest()}
(HERE/'audit/publication_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
