"""Audit, score and publish the first 20 v3 cases without changing older results."""
from pathlib import Path
import json,hashlib,sys,math,html
from datetime import datetime,timezone
from collections import Counter
import numpy as np,pandas as pd
from run_batch import checkpoint
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];M=json.loads((HERE/'manifest.json').read_text())
sys.path.insert(0,str(ROOT/'src'))
from nai.sim import SimResolver
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
esc=lambda x:html.escape(str(x))
pretty=lambda s:s.replace('gpt-5.6-','').replace('gpt-6-','').replace('-agent','').title()
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,np.integer):return int(x)
    if isinstance(x,np.bool_):return bool(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x
def save(p,x):
    q=p.with_name(p.name+'.tmp');q.write_text(json.dumps(clean(x),indent=2,allow_nan=False));q.replace(p)
def f(x,n=2):return '—' if x is None or not np.isfinite(x) else f'{x:.{n}f}'
def main():
    records,missing=checkpoint();assert records
    original=json.loads((ROOT/'data/sim/pricevolume-v3/source_preservation.json').read_text());assert all(sha(ROOT/p)==v for p,v in original.items())
    assert sha(ROOT/M['protocol_file'])==M['protocol_sha256']
    resolver=SimResolver(['SOL-USD'],time_stop_hours=72)
    paths=np.load(ROOT/'data/analysis/direction-paths-20260929/minute_paths.npz')
    prior=[json.loads(s) for s in (ROOT/'data/sim/decisions/rules2to1-openai-20260926T072414Z.jsonl').read_text().splitlines()]
    pm={(r['model'],r['window_id']):r for r in prior};rows=[];pairs=[]
    for r in records:
        c=M['cases'][r['case']-1];dec=r['decision'];d={k:c[k] for k in ['window_id','asset','window_end_ts','price_real','sigma_vis_pct','sigma_2d_pct','atr14_pct','ret_vis_pct','ma20_now','ma50_now','vol24_ratio']};d.update(dec)
        assert sha(ROOT/c['source_prompt'])==c['prompt_sha256'] and sha(ROOT/c['chart_file'])==c['image_sha256']
        d.update(run_id=M['run_id'],case=c['case'],case_number=c['case'],model=r['model']+'-agent',model_version=r['model']+' via fresh Codex exec',reasoning_effort='medium',visible_bars=40,stimulus='text+image',image=c['chart_file'],prompt_version='sim-v3-15m-window-pricevolume-2to1-noflat',prompt_hash='sha256:'+c['prompt_sha256'][:16],stimulus_text_sha256=c['prompt_sha256'],stimulus_image_sha256=c['image_sha256'],combined_input_sha256=c['input_sha256'],protocol_sha256=M['protocol_sha256'],raw_response=r['raw_response'],ts_decided=r['ts_decided'],thread_id=r['thread_id'],agent_path=r['agent_path'],isolation=r['isolation'],tp_source='harness: exactly 2 * stop_pct',features_supplied='40 OHLC and relative-volume bars plus price/volume-only chart',private_evaluation_features_not_supplied=['ma20_now','ma50_now','atr14_pct','sigma_vis_pct','sigma_2d_pct','ret_vis_pct','vol24_ratio'])
        d.update(resolver.resolve(c['asset'],pd.Timestamp(c['window_end_ts']),d['action'],d['stop_pct'],d['tp_pct']))
        assert abs(d['entry_price']-c['price_real'])<1e-8 and d['tp_pct']==2*d['stop_pct']
        old=pm[d['model'],d['window_id']];sgn=1 if d['action']=='long' else -1;oldsgn=1 if old['action']=='long' else -1
        pair={'case':c['case'],'window_id':c['window_id'],'model':d['model'],'v2_action':old['action'],'v3_action':d['action'],'direction_changed':d['action']!=old['action'],'v2_confidence':old['confidence'],'v3_confidence':d['confidence'],'v2_stop_pct':old['stop_pct'],'v3_stop_pct':d['stop_pct'],'v2_gross_pct':old['pnl_gross_pct'],'v3_gross_pct':d['pnl_gross_pct'],'v2_net_pct':old['pnl_net_pct'],'v3_net_pct':d['pnl_net_pct'],'v2_reason':old['reason'],'v3_reason':d['reason'],'v2_outcome':old['outcome'],'v3_outcome':d['outcome'],'v2_ma20_aligned':oldsgn==(1 if c['ma20_now']<=100 else -1),'v3_ma20_aligned':sgn==(1 if c['ma20_now']<=100 else -1)}
        for h in [15,30,105]:
            raw=paths[c['window_id']][h-1,3];d[f'signed_{h}m_pct']=sgn*raw;pair[f'v2_signed_{h}m_pct']=oldsgn*raw;pair[f'v3_signed_{h}m_pct']=sgn*raw
        rows.append(clean(d));pairs.append(pair)
    ledger=ROOT/'data/sim/decisions'/f"{M['run_id']}.jsonl"
    oldrows=[json.loads(s) for s in ledger.read_text().splitlines()] if ledger.exists() else []
    key=lambda r:(r['model'],r['window_id']);newmap={key(r):r for r in rows};assert len(newmap)==len(rows)
    for r in oldrows:assert newmap[key(r)]==r,'Existing v3 row changed'
    saved={key(r) for r in oldrows}
    with ledger.open('a') as out:out.write(''.join(json.dumps(r,allow_nan=False)+'\n' for r in rows if key(r) not in saved))
    frame=pd.DataFrame(pairs);frame.to_csv(HERE/'paired_v2_v3.csv',index=False);save(HERE/'paired_v2_v3.json',pairs)
    rng=np.random.default_rng(20260929);summary=[];tests=[]
    for model,g in frame.groupby('model'):
        sr={'model':model,'cases':len(g),'direction_changes':int(g.direction_changed.sum())}
        for v in ['v2','v3']:
            sr[v]={'long':int((g[v+'_action']=='long').sum()),'short':int((g[v+'_action']=='short').sum()),'mean_confidence':g[v+'_confidence'].mean(),'median_stop_percent':100*g[v+'_stop_pct'].median(),'ma20_agreement':g[v+'_ma20_aligned'].mean(),'mean_gross_pct':g[v+'_gross_pct'].mean(),'mean_net_pct':g[v+'_net_pct'].mean(),'outcomes':g[v+'_outcome'].value_counts().to_dict()}
            for h in [15,30,105]:sr[v][f'accuracy_{h}m']=(g[f'{v}_signed_{h}m_pct']>0).mean();sr[v][f'mean_signed_{h}m_pct']=g[f'{v}_signed_{h}m_pct'].mean()
        for h in [15,30,105]:
            delta=(g[f'v3_signed_{h}m_pct']-g[f'v2_signed_{h}m_pct']).to_numpy();null=(rng.choice([-1,1],size=(10000,len(delta)))*delta).mean(1);boot=delta[rng.integers(len(delta),size=(10000,len(delta)))].mean(1)
            tests.append({'model':model,'horizon_minutes':h,'n':len(delta),'mean_paired_change_pct':delta.mean(),'ci95_pct':np.quantile(boot,[.025,.975]).tolist(),'p_signflip':float((1+(np.abs(null)>=abs(delta.mean())).sum())/10001)})
        summary.append(sr)
    pv=np.array([t['p_signflip'] for t in tests]);order=np.argsort(pv);q=np.minimum.accumulate((pv[order]*len(pv)/np.arange(1,len(pv)+1))[::-1])[::-1];qs=np.empty(len(pv));qs[order]=np.minimum(q,1)
    for t,q in zip(tests,qs):t['q']=float(q)
    status='complete_first20' if not missing else 'partial_first20'
    save(HERE/'summary.json',{'status':status,'completed_decisions':len(rows),'requested_decisions':60,'canonical_windows_prepared':100,'models':summary,'fixed_horizon_paired_tests':tests,'limitations':['20 shared historical windows, not 60 independent observations','Historical v2 controls, not fresh repeated controls','Whole supplied-indicator reduction and possible chart rescaling, not MA-only causal intervention','Original v2 desktop harness vs fresh CLI for some pairs','All tests exploratory, sign-flip symmetry assumption; bootstrap by window within each model']})
    save(HERE/'paired_tests.json',tests)
    report=ROOT/'data/sim/reports'/f"{M['run_id']}.html"
    table='<table><thead><tr><th>Model</th><th>Direction changes</th><th>Long v2→v3</th><th>MA20 agreement v2→v3</th><th>Confidence v2→v3</th><th>SL median v2→v3</th><th>Gross v2→v3</th><th>Net v2→v3</th></tr></thead><tbody>'
    for s in summary:
        a,b=s['v2'],s['v3'];table+=f"<tr><td>{pretty(s['model'])}</td><td>{s['direction_changes']}/{s['cases']}</td><td>{a['long']} → {b['long']}</td><td>{f(a['ma20_agreement']*100,0)}% → {f(b['ma20_agreement']*100,0)}%</td><td>{f(a['mean_confidence']*100,1)}% → {f(b['mean_confidence']*100,1)}%</td><td>{f(a['median_stop_percent'])}% → {f(b['median_stop_percent'])}%</td><td>{f(a['mean_gross_pct'])}% → {f(b['mean_gross_pct'])}%</td><td>{f(a['mean_net_pct'])}% → {f(b['mean_net_pct'])}%</td></tr>"
    table+='</tbody></table>'
    cards=[]
    for case,g in frame.groupby('case'):
        c=M['cases'][int(case)-1];tab='<table><thead><tr><th>Model / version</th><th>Side</th><th>Confidence</th><th>SL / TP</th><th>15m move</th><th>30m move</th><th>105m move</th><th>Outcome</th><th>Saved explanation</th></tr></thead><tbody>'
        for _,r in g.iterrows():
            for v in ['v2','v3']:
                vals=''.join(f"<td>{f(r[f'{v}_signed_{h}m_pct'])}%</td>" for h in [15,30,105]);tab+=f"<tr class='{v}'><td>{pretty(r['model'])} / {v}</td><td>{r[v+'_action']}</td><td>{f(r[v+'_confidence']*100,0)}%</td><td>{f(r[v+'_stop_pct']*100)}% / {f(r[v+'_stop_pct']*200)}%</td>{vals}<td>{r[v+'_outcome']}</td><td class='reason'>{esc(r[v+'_reason'])}</td></tr>"
        tab+='</tbody></table>'
        cards.append(f"<section id='case-{case}'><h2>Case {int(case):02d} · {esc(c['window_id'])}</h2><p class='muted'>Research metadata only: {esc(c['asset'])} · {esc(c['window_end_ts'])} last-bar open. Neither identity nor historical date was supplied to the model.</p><details><summary>Compare original and price/volume-only input charts</summary><div class='charts'><figure><img loading='lazy' src='../../{esc(c['original_chart_file'].removeprefix('data/'))}' alt='Original v2 chart'><figcaption>Original v2 input</figcaption></figure><figure><img loading='lazy' src='../../{esc(c['chart_file'].removeprefix('data/'))}' alt='Price and volume only v3 chart'><figcaption>V3 price / volume only</figcaption></figure></div></details><div class='scroll'>{tab}</div><p><a href='../../{esc(c['source_prompt'].removeprefix('data/'))}'>Exact v3 text</a></p></section>")
    # Report resides data/sim/reports, so ../../sim/... resolves the original data/sim files.
    title=f"V3 price & volume only · {len(rows)}/60 decisions"
    document=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>body{{font:15px/1.6 system-ui;margin:0;background:#f7f7f2;color:#20372f}}main{{max-width:1500px;margin:auto;padding:40px 28px}}h1{{font-size:36px;line-height:1.2}}h2{{font-size:22px}}a{{color:#17765f}}section{{padding:24px;background:white;border:1px solid #dbe3d9;border-radius:10px;margin:24px 0}}.muted{{color:#627467;font-size:13px}}.notice{{border-left:4px solid #17765f;padding:18px;background:#eaf0e5}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:10px 12px;border-bottom:1px solid #dfe6dc;text-align:left;white-space:nowrap}}th{{background:#eef3e9}}.reason{{white-space:normal;min-width:250px}}.v3{{background:#eff7f2}}.charts{{display:grid;grid-template-columns:1fr 1fr}}figure{{margin:16px 6px}}img{{width:100%;height:auto}}summary{{cursor:pointer}}@media(max-width:800px){{.charts{{grid-template-columns:1fr}}}}</style><main><p class="muted">100 canonical windows prepared · requested pilot: cases 1–20 × three models</p><h1>{esc(title)}</h1><p class="notice"><strong>{'Requested first 20 batch complete.' if not missing else 'Partial batch; collection incomplete.'}</strong> Cases 21–100 remain prepared but unrun. Each accepted decision used a fresh single-turn agent with full anonymized text and chart, no tool calls, and medium reasoning. V3 removes MA, ATR, volatility and derived summaries. It is a price/volume-only treatment, not an MA-only causal experiment.</p><p>Compare each model with its historical v2 decision on the exact same window. The 60 decisions share only 20 market outcomes. Original v2 controls are not concurrent repeated calls and some use a different collection harness. Direction-signed fixed-horizon movements below continue after bracket exits; they are not realized returns. Gross and net bracket means are per trade, not portfolio returns; net subtracts20 bps roundtrip.</p><p><a href="../pricevolume-v3/INSTRUCTIONS.md">Shared protocol</a> · <a href="../decisions/{M['run_id']}.jsonl">New ledger</a> · <a href="../{M['run_id']}/paired_v2_v3.csv">All paired results</a> · <a href="../{M['run_id']}/summary.json">Summary and uncertainty</a> · <a href="../../analysis/exit-policies-20260929/index.html">Separate exit-policy study</a></p><p><a href="../{M['run_id']}/FINDINGS.md">Read the pilot findings</a> · <a href="../{M['run_id']}/v3_overview.pdf">Export figure</a></p><img src="../{M['run_id']}/v3_overview.png" alt="Directional accuracy at 15, 30 and 105 minutes for the three models, comparing v2 and v3"><section><h2>Matched v2 → v3 behavior and bracket outcomes</h2><div class="scroll">{table}</div></section><p>Jump to case: {' · '.join(f'<a href="#case-{c}">{c:02d}</a>' for c in sorted(frame['case'].unique()))}</p>{''.join(cards)}<p class="muted">All original ledgers and reports preserved. Raw attempts, model contexts, tool-access audit and delivered-image hashes retained in the run folder.</p></main></html>'''
    report.write_text(document)
    changed=[p for p,h in original.items() if sha(ROOT/p)!=h];assert not changed
    check={'other_original_files_checked':len(original),'changed':changed,'requested_complete':not missing,'ledger_rows':len(rows),'unique_model_window_pairs':len(newmap),'models':{s['model']:s['cases'] for s in summary},'all_audited_before_scoring':True,'all_tp_exactly_twice_sl':all(r['tp_pct']==2*r['stop_pct'] for r in rows),'all_entries_match':True,'no_cases_after20_run':all(r['case']<=20 for r in rows)};save(HERE/'preservation_check.json',check)
    progress=json.loads((HERE/'progress.json').read_text());progress.update(status=status,ledger=str(ledger.relative_to(ROOT)),report=str(report.relative_to(ROOT)),scored_decisions=len(rows));save(HERE/'progress.json',progress)
    (HERE/'HANDOFF.md').write_text(f'''# V3 price/volume-only — {status}

{len(rows)}/60 requested decisions saved and scored: cases 1–20 on Luna, Terra and Astra. Canonical cases 21–100 are prepared but not authorized/run in this batch. {len(missing)} requested pairs missing.

- New ledger: ../decisions/{M['run_id']}.jsonl
- Report: ../reports/{M['run_id']}.html
- Exact shared 100-window protocol: ../pricevolume-v3/INSTRUCTIONS.md
- Stimuli: ../pricevolume-v3/stimuli/
- Paired historical-v2 comparison: paired_v2_v3.csv / summary.json
- Raw attempts: cli_attempts/; accepted_decisions.jsonl; isolation_audit.json
- Separate existing-data policy study: ../../analysis/exit-policies-20260929/

No old source or result files changed ({len(original)} checks). Fresh Codex exec per decision, medium, attached image+text, tools disabled. Transcript audit verifies single turn, exact model, original attached-image bytes, full text, and zero calls before scoring. At most 3 attempts for contract/delivery failures only. {progress['attempts']-len(rows)} attempts excluded. Same v2 forced 2:1/no-flat and unchanged one-minute 72h resolver.

Only price and per-bar relative volume are supplied. MA/ATR/sigma/move summaries are NOT sent. Evaluation-only original indicators retained in ledger are labeled private. This is broader than MA removal and includes chart rescaling. Comparison uses historical v2 controls; does not isolate removal from stochastic or harness changes. New market data or repeated contemporaneous controls would be needed for stronger conclusions.

CLI controls reference: https://learn.chatgpt.com/docs/developer-commands?surface=cli and https://learn.chatgpt.com/docs/config-file/config-reference (consulted2026-09-29).

Resume only explicitly authorized cases with run_batch.py; current default hard-caps at20. publish.py is idempotent, checks old v3 rows unchanged, and only appends newly audited rows. Do not edit another operator's files.
''')
    print(json.dumps(clean({'status':status,'ledger':str(ledger),'report':str(report),'summary':summary}),indent=2))
if __name__=='__main__':main()
