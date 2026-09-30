"""Publish all audited completed decisions, with explicit partial-run status.

Safe to rerun after collection: append only missing keys to this run's own ledger;
assert existing rows match exactly. Never fabricate missing decisions or modify
another run's artifacts. No model calls are made here.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
import pandas as pd
import manage as collector

HERE, ROOT, M = collector.HERE, collector.ROOT, collector.MANIFEST
from nai.sim import SimResolver, summarize_sim
import sim_report_html as report


def atomic(path, text):
    temp = path.with_name(path.name+'.tmp')
    temp.write_text(text)
    temp.replace(path)


def main():
    # Snapshot other simulation files to distinguish our writes from pre-existing changes.
    ledger = ROOT/'data/sim/decisions'/f"{M['run_id']}.jsonl"
    html_path = ROOT/'data/sim/reports'/f"{M['run_id']}.html"
    before = {p:collector.sha(p) for p in (ROOT/'data/sim').rglob('*')
              if p.is_file() and HERE not in p.parents and p not in (ledger,html_path)}
    records, audit = collector.collect()
    assert records and audit['all_eligible_passed']
    provenance = json.loads((HERE/'evaluation_provenance.json').read_text())
    for source,digest in provenance['source_sha256'].items():
        assert collector.sha(ROOT/source)==digest, f'Evaluation source changed: {source}'
    assert collector.sha(ROOT/M['protocol_file'])==M['protocol_sha256']
    resolver = SimResolver(['SOL-USD'],eval_interval='1m',time_stop_hours=72)
    rows=[]
    for r in records:
        c=M['cases'][r['case']-1]; d=r['decision']
        assert d['action'] in ('long','short') and d['tp_pct']==2*d['stop_pct']
        row={k:v for k,v in c.items() if k not in ('stimulus_dir','input_sha256','source_prompt')}
        row.update(d)
        row.update(run_id=M['run_id'],case_number=c['case'],model=r['model']+'-agent',
                   model_version=r['model']+' via '+r.get('harness','Codex subagent'),reasoning_effort='medium',
                   visible_bars=40,stimulus='text+image',image=c['chart_file'],
                   prompt_version='sim-v2-15m-window-2to1-noflat',
                   prompt_hash='sha256:'+c['prompt_sha256'][:16],
                   stimulus_text_sha256=c['prompt_sha256'],stimulus_image_sha256=c['image_sha256'],
                   combined_input_sha256=c['input_sha256'],protocol_sha256=M['protocol_sha256'],
                   raw_response=r['raw_response'],ts_decided=r['ts_decided'],
                   thread_id=r['thread_id'],agent_path=r['agent_path'],
                   tp_source='harness: exactly 2 * stop_pct; any emitted target ignored',
                   isolation=r.get('isolation',M['isolation']))
        row.update(resolver.resolve(c['asset'],pd.Timestamp(c['window_end_ts']),d['action'],d['stop_pct'],2*d['stop_pct']))
        assert abs(row['entry_price']-c['price_real'])<1e-9
        rows.append(collector.clean(row))
    key=lambda r:(r['model'],r['window_id'])
    current={key(r):r for r in rows}; assert len(current)==len(rows)
    existing=[json.loads(s) for s in ledger.read_text().splitlines() if s.strip()] if ledger.exists() else []
    assert len({key(r) for r in existing})==len(existing)
    for r in existing: assert current[key(r)]==r, 'Existing ledger row changed'
    saved={key(r) for r in existing}
    additions=[r for r in rows if key(r) not in saved]
    if additions:
        with ledger.open('a') as f:
            f.write(''.join(json.dumps(r,allow_nan=False)+'\n' for r in additions))
    df=pd.DataFrame(rows)
    complete=not audit['missing'] and len(rows)==300
    status='complete' if complete else 'partial'
    counts=dict(Counter(r['model'] for r in rows))
    progress={'status':status,'planned_decisions':300,'accepted_decisions':len(rows),
              'remaining_decisions':len(audit['missing']),'attempts':audit['attempts'],
              'excluded_attempts':len(audit['excluded_attempts']),'counts_by_model':counts,
              'cases_by_model':{m:[r['case_number'] for r in rows if r['model']==m] for m in counts},
              'missing_case_model_pairs':audit['missing'],
              'last_model_decision_at':max(r['ts_decided'] for r in rows),
              'published_at':datetime.now(timezone.utc).isoformat()}
    atomic(HERE/'progress.json',json.dumps(progress,indent=2))
    prior=[json.loads(s) for run in M['prior_runs'] for s in (ROOT/'data/sim/decisions'/f'{run}.jsonl').read_text().splitlines() if s.strip()]
    matched=[r for r in prior if key(r) in current]
    assert len(matched)==len(rows)
    summary={'status':status,'completed':len(rows),'planned':300,'remaining':len(audit['missing']),
             'current':json.loads(summarize_sim(df).reset_index().to_json(orient='records')),
             'v1_matching_completed_cases':json.loads(summarize_sim(pd.DataFrame(matched)).reset_index().to_json(orient='records')),
             'outcomes':{m:dict(Counter(g['outcome'])) for m,g in df.groupby('model')}}
    atomic(HERE/'summary.json',json.dumps(summary,indent=2))
    report.pnl_chart_svg=collector.cumulative_chart
    orig=report.window_card
    def numbered(group):
        n=int(group.iloc[0]['case_number'])
        return orig(group).replace('<article class="card">',f'<article class="card" id="setup-{n}"><h3 style="padding:12px 16px;margin:0">Setup {n:02d}</h3>',1)
    report.window_card=numbered
    title=f"{'PARTIAL · ' if not complete else ''}OpenAI forced 2:1 · {len(rows)}/300 decisions"
    document=report.build(df,title)
    banner=f'''<section><h2>{'Complete' if complete else 'Incomplete run — recovered results'}</h2>
    <p><strong>{len(rows)} of 300 decisions saved; {len(audit['missing'])} still missing.</strong>
    Luna: {counts.get('gpt-5.6-luna-agent',0)}/100 · Terra: {counts.get('gpt-5.6-terra-agent',0)}/100 · Astra: {counts.get('gpt-6-astra-agent',0)}/100.</p>
    <p>These are completed historical decisions only. Missing cases are not counted as flat trades or zero returns.
    Each accepted decision used a fresh context, exact original chart/text, the shared overriding wrapper, and medium reasoning.
    Isolation is instruction-based and audited, not an OS sandbox. {len(audit['excluded_attempts'])} invalid attempts were preserved and excluded before scoring.</p>
    <p>Resumption on September 29 uses fresh Codex CLI processes with tool access disabled and directly attached inputs; the first 86 decisions used desktop subagents. Model IDs and reasoning effort are unchanged, but the harness differs and is recorded in each row.</p>
    <p>Long or short only. The harness sets TP = exactly 2 × SL. Gross return is the headline;
    the secondary net column includes 20 bps round-trip costs. Unchanged 1m evaluator, 72-hour timeout, ambiguous exits excluded.
    These are exploratory per-trade averages, not portfolio returns.</p>
    <p><a href="../decisions/{M['run_id']}.jsonl">Decision ledger</a> ·
    <a href="../{M['run_id']}/progress.json">Exact coverage and missing cases</a> ·
    <a href="../{M['run_id']}/isolation_audit.json">Audit</a> ·
    <a href="../rules2to1/INSTRUCTIONS.md">Shared protocol</a> ·
    <a href="rules2to1.html">Claude's separate report</a></p></section>'''
    document=document.replace('</header>','</header>'+banner,1)
    comparison='<section><h2>Original free-geometry results on these same completed model/case pairs</h2><p>Matched separately per model. Original flat decisions remain included in the decision count; return means use executed, scored trades. The treatment changes both geometry and permission to stay flat, and repeats model sampling.</p>'+report.model_table(pd.DataFrame(matched))+'</section>'
    document=document.replace('<footer>',comparison+'<footer>',1)
    document=document.replace('windows both traded','windows all three traded').replace('<th>trades</th>','<th>decisions</th>')
    document=document.replace('harness: gpt-5.6-luna via Codex subagent','harness: fresh Luna / Terra / Astra Codex subagents, medium reasoning')
    atomic(html_path,'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'+document+'</html>')
    changed=[str(p.relative_to(ROOT)) for p,h in before.items() if not p.exists() or collector.sha(p)!=h]
    check={'other_simulation_files_checked':len(before),'changed_files':changed,
           'original_manifest_files_changed':[p for p,h in M['original_sha256'].items() if not (ROOT/p).exists() or collector.sha(ROOT/p)!=h]}
    atomic(HERE/'preservation_check.json',json.dumps(check,indent=2));assert not changed
    atomic(HERE/'HANDOFF.md',f'''# Forced 2:1 OpenAI — {status.upper()}

{len(rows)} / 300 accepted decisions are saved and evaluated. {len(audit['missing'])} decisions remain unfinished. {'All 100 canonical setups are complete on each model.' if complete else 'This is not a complete 100-setup experiment.'}

- Luna: {counts.get('gpt-5.6-luna-agent',0)} / 100
- Terra: {counts.get('gpt-5.6-terra-agent',0)} / 100
- Astra: {counts.get('gpt-6-astra-agent',0)} / 100

Ledger: ../decisions/{M['run_id']}.jsonl
Report: ../reports/{M['run_id']}.html
Summary: summary.json
Exact missing cases: progress.json
Raw attempts: responses/ (desktop) and cli_attempts/ (resumption); audit: isolation_audit.json; excluded attempts: excluded_attempts.json.

On 2026-09-29 recovery collected six completed responses beyond the old 80-response audit, yielding 86 accepted decisions. The original run was interrupted before finishing collection and never had a scoring/publishing stage. No missing decisions were invented. Subsequent authorized resumption uses fresh Codex exec processes with the exact original model IDs, medium reasoning, full original text/chart, and no tool calls. Model/version and isolation fields distinguish the two harnesses. {len(audit['excluded_attempts'])} attempts are excluded before scoring; raw attempts remain preserved. TP is derived by the harness as exactly twice SL; all sources match the original evaluation hashes.

Publishing command: .venv/bin/python -B {str((HERE/'publish_partial.py').relative_to(ROOT))}
It audits first, appends only missing accepted rows to this run's ledger, checks existing rows are identical, and refreshes the current completion status. It does not launch agents. Existing Claude outputs, prior runs, source code and scripts were not modified. The recovery's preservation check covers {len(before)} other simulation files.
''')
    print(json.dumps({'status':status,'written':len(additions),'accepted':len(rows),'remaining':len(audit['missing']),'ledger':str(ledger),'report':str(html_path),'outcomes':summary['outcomes']},indent=2))


if __name__=='__main__':main()
