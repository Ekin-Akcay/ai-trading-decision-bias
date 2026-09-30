from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,ast,re
H=Path(__file__).resolve().parent;ROOT=H.parents[2]
x=pd.read_csv(H/'per_trade_policies.csv');d=pd.read_csv(ROOT/'data/analysis/direction-paths-20260929/decisions_enriched.csv');d=d[d.main].set_index('decision_id');a=json.loads((H/'audit.json').read_text())
checks={}
checks['rows_46000']=len(x)==46000
checks['unique_decision_policy']=not x.duplicated(['decision_id','policy']).any()
checks['1000_rows_each_policy']=bool((x.groupby('policy').size()==1000).all())
checks['100_windows_each_policy']=bool((x.groupby('policy').window_id.nunique()==100).all())
checks['1000_originals_all_match']=all(all(r[k] for k in ['outcome','minutes','gross','net']) for r in json.loads((H/'engine_audit.json').read_text()))
known=x.net_pct.notna();checks['cost_identity']=bool(np.allclose(x.loc[known,'gross_pct']-x.loc[known,'net_pct'],np.where(x.loc[known,'effective_sign']!=0,.2,0)))
checks['bound_order']=bool((x.net_lower_pct<=x.net_upper_pct+1e-12).all())
checks['flats_zero']=bool((x.loc[x.sign==0,['gross_pct','net_pct','minutes_held']]==0).all().all())
for h in [5,15,30,60,105,240]:
 q=x[x.policy==f'time_{h}m'].set_index('decision_id').reindex(d.index);r=x[x.policy==f'reverse_{h}m'].set_index('decision_id').reindex(d.index)
 checks[f'uncensored_return_{h}m_matches_independent_prior_study']=bool(np.allclose(q.gross_pct,d[f'signed_{h}m_pct'].fillna(0)))
 checks[f'reversal_identity_{h}m']=bool(np.allclose(q.gross_pct,-r.gross_pct))
checks['capped_exits_within_cap']=bool((x[x.kind=='combined'].minutes_held<=x[x.kind=='combined'].horizon_minutes).all())
checks['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in a['source_sha256'].items())
checks['full_72h_all_windows']=len(a['coverage'])==100 and all(z['complete_72h'] for z in a['coverage'])
b=pd.read_csv(H/'benchmark_contrasts.csv');checks['momentum_common_99_windows']=bool((b.loc[b.policy.str.startswith('momentum'),'windows']==99).all())
checks['others_100_windows']=bool((b.loc[~b.policy.str.startswith('momentum'),'windows']==100).all())
txt=(H/'index.html').read_text();links=re.findall(r'(?:href|src)="([^"]+)"',txt);checks['all_local_artifact_links_exist']=all((H/v).exists() for v in links)
checks['all_html_placeholders_resolved']=not any('>'+s+'<' in txt for s in ['PRIMARY','CONTRASTS','ALLTABLE','BENCHMARKS','HALVES','SESSIONS','APPENDIX','RISKTABLE'])
checks['report_v3_broad_removal_caveat']='ATR/sigma' in txt and 'historical rather than concurrent' in txt
checks['python_scripts_parse']=all(ast.parse((H/f).read_text()) for f in ['run.py','appendix.py','risk_diagnostic.py','build_report.py','validate.py'])
pd.read_csv(H/'posthoc_regime_direction.csv')
checks['posthoc_cells_visible']='All post-hoc regime' in txt
risk=pd.read_csv(H/'posthoc_risk_normalization.csv')
checks['risk_grid_eight_cells']=len(risk)==8 and not risk.duplicated(['protocol','bracket_scale']).any()
checks['risk_net_identity']=bool(np.allclose(risk.mean_gross_r-risk.mean_fee_r_same_known_rows,risk.mean_net_r))
checks['risk_ambiguities_one_per_protocol_at_quarter']=int(risk.ambiguous.sum())==2 and bool((risk.loc[risk.bracket_scale==.25,'ambiguous']==1).all())
checks['risk_excludes_flats_and_ambiguous']=bool((risk.known_decisions+risk.ambiguous==risk.active_decisions).all())
checks['risk_caveat_in_report']='lower percentage returns do not prove weaker direction' in txt.lower()
for k,v in checks.items():assert v,k
(H/'report_ui.js').write_text(re.search(r'<script>(.*?)</script>',txt,re.S).group(1))
(H/'validation.json').write_text(json.dumps(dict(status='passed',checks=checks,checked_links=links,notes=['Scientific figure visually inspected.','Localhost page rendered before final textual appendix changes; final content and links statically verified.','Temporary preview tab and local server closed.','No browser file URL was used by this subtask.']),indent=2))
print(json.dumps({'status':'passed','checks':len(checks),'links':len(links)},indent=2))
