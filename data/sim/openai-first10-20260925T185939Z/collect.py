"""Collect original subagent outputs and provenance; --finalize resolves and reports.

No model calls. Never modifies Claude inputs or reports. Run with python -B.
"""
import argparse
import hashlib
import html
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST = json.loads((HERE / 'manifest.json').read_text())
MODELS = {'luna': 'gpt-5.6-luna', 'terra': 'gpt-5.6-terra', 'astra': 'gpt-6-astra'}
PARENT = '[local-session-id]'
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect():
    found = []
    for path in sorted(Path('[local-runtime-record]').glob('*.jsonl')):
        with path.open() as f:
            first = json.loads(next(f))
            meta = first.get('payload', {})
            match = re.fullmatch(r'/root/(luna|terra|astra)_(\d\d)(?:_clean|_restricted)?', meta.get('agent_path', ''))
            if not match or meta.get('parent_thread_id') != PARENT:
                continue
            events = [first] + [json.loads(s) for s in f if s.strip()]
        family, num = match.groups()
        case = int(num)
        assert 1 <= case <= 10
        context, calls, users, final, final_ts = [], [], [], None, None
        for event in events:
            item = event.get('payload', {})
            if event['type'] == 'turn_context':
                context.append({'model': item.get('model'), 'effort': item.get('effort')})
            if event['type'] != 'response_item':
                continue
            if item.get('type') in ('function_call', 'custom_tool_call'):
                calls.append({k: item[k] for k in ('name', 'arguments', 'input') if k in item})
            if item.get('type') == 'message' and item.get('role') == 'user':
                users.append('\n'.join(c.get('text', '') for c in item.get('content', [])))
            if item.get('type') == 'message' and item.get('role') == 'assistant' and item.get('phase') == 'final_answer':
                assert final is None, 'More than one answer; never silently select a retry'
                final = '\n'.join(c.get('text', '') for c in item.get('content', []))
                final_ts = event.get('timestamp')
        if final is None:
            continue
        assert len(context) == 1 and context[0]['model'] == MODELS[family]
        assert context[0]['effort'] == 'medium'
        decision = json.loads(final)
        stimulus = Path(MANIFEST['cases'][case - 1]['stimulus_dir'])
        assert sha(stimulus/'prompt.txt') == MANIFEST['cases'][case-1]['prompt_sha256']
        assert sha(stimulus/'chart.png') == MANIFEST['cases'][case-1]['image_sha256']
        # Preserve calls verbatim for the root's explicit tool-access audit.
        record = {'case': case, 'model': MODELS[family], 'agent_path': meta['agent_path'],
                  'thread_id': meta['id'], 'ts_decided': final_ts, 'reasoning_effort': 'medium',
                  'raw_response': final, 'decision': decision, 'tool_calls': calls,
                  'user_messages': users, 'source_transcript': str(path)}
        out = HERE/'responses'/f"{meta['agent_path'].split('/')[-1]}.json"
        body = json.dumps(record, indent=2)
        if out.exists():
            assert json.loads(out.read_text()) == record
        else:
            out.write_text(body)
        found.append(record)
    exclusions = json.loads((HERE/'excluded_attempts.json').read_text())
    attempted = len(found)
    found = [r for r in found if r['agent_path'] not in exclusions]
    found.sort(key=lambda r: (r['case'], list(MODELS.values()).index(r['model'])))
    print(f'Collected {len(found)}/30 eligible decisions; {attempted-len(found)} excluded attempts preserved.')
    return found


def finalize(records):
    import pandas as pd
    from nai.prompts import parse_decision, SYSTEM_PROMPT
    from nai.sim import SimResolver, summarize_sim
    from sim_report_html import build, model_table

    assert len(records) == 30
    assert len({(r['case'], r['model']) for r in records}) == 30
    audit = json.loads((HERE/'isolation_audit.json').read_text())
    assert audit['all_passed'] and len(audit['agents']) == 30
    resolver = SimResolver(['SOL-USD'], eval_interval='1m', time_stop_hours=72)
    rows = []
    for r in records:
        case = MANIFEST['cases'][r['case']-1]
        d = parse_decision(r['raw_response'])
        assert d['action'] != 'error'
        row = dict(case['source_row'])
        row.update(d)
        row.update(run_id=MANIFEST['run_id'], case_number=r['case'], model=r['model']+'-agent',
                   model_version=r['model']+' via Codex subagent', reasoning_effort='medium',
                   ts_decided=r['ts_decided'], agent_path=r['agent_path'], thread_id=r['thread_id'],
                   raw_response=r['raw_response'], stimulus='text+image',
                   system_prompt_sha256=hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
                   stimulus_image_sha256=case['image_sha256'],
                   stimulus_text_sha256=case['prompt_sha256'],
                   isolation='fresh context per decision; tool access audited; no hard sandbox')
        row.update(resolver.resolve(case['asset'], pd.Timestamp(case['window_end_ts']),
                                    d['action'], d['stop_pct'], d['tp_pct']))
        row = {k:None if isinstance(v,float) and not math.isfinite(v) else v for k,v in row.items()}
        rows.append(row)
    df = pd.DataFrame(rows)
    out = ROOT/'data/sim/decisions'/f"{MANIFEST['run_id']}.jsonl"
    assert not out.exists(), 'Never overwrite or append duplicate evaluated records'
    out.write_text(''.join(json.dumps(r, allow_nan=False)+'\n' for r in rows))
    matched = []
    ids = {c['window_id'] for c in MANIFEST['cases']}
    for name in ('agent-demo2-agents', 'agent-demo2-controls'):
        for line in (ROOT/'data/sim/decisions'/f'{name}.jsonl').read_text().splitlines():
            r = json.loads(line)
            if r['window_id'] in ids:
                matched.append(r)
    (HERE/'matched_claude_and_controls.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in matched))
    report = build(df, 'OpenAI comparison · first 10 SOL setups')
    note = '''<section><p>30 accepted decisions · 10 identical saved setups · fresh context per decision · medium reasoning.</p><details><summary>Experiment provenance and isolation audit — 8 excluded attempts</summary>
<p>30 new decisions: 10 original SOL windows × GPT-5.6 Luna, GPT-5.6 Terra, GPT-6 Astra.
Windows follow first appearance in the original Claude decision log. Every decision used a fresh
subagent with no inherited conversation, medium reasoning, the original saved text and chart,
and no feedback. The tool-call audit confirmed only the assigned stimulus files were accessed.
Isolation was instruction-based and audited, not a hard filesystem or tool sandbox.
Seven Terra attempts across four cases queried the computer app inventory; those attempts were excluded
before scoring, preserved in the run folder, and repeated with fresh contexts. A fixed, single
read-only tool call was introduced after verbal restrictions alone failed.
One Astra attempt failed to load the numeric prompt due to a mistyped file path and was also
excluded and repeated. Eight excluded attempts are retained separately. The wrapper instructions
therefore changed during collection; saved user messages document each version. The original market
prompt, chart and trade contract were preserved. All eligible attempts were audited.</p>
<p>The saved input text hashes match the Claude records. Chart bytes were fingerprinted for this run;
the original Claude logs do not carry image hashes. Codex and Claude Code have different harnesses,
so this comparison does not isolate model weights alone. No historical Claude record was rewritten.</p>
<p>Evaluation: unchanged existing one-minute first-passage engine, 72-hour timeout,
20 basis points round-trip costs. The prompt does not state the timeout. Excursions include
the full exit bar. Per-trade averages are not portfolio returns. Ten windows are exploratory.</p>
<p><a href="agent-demo2.html">Original full Claude report (unchanged)</a> ·
<a href="../RUN/manifest.json">Run manifest</a> ·
<a href="../RUN/isolation_audit.json">Isolation audit</a> ·
<a href="../decisions/RUN.jsonl">OpenAI decision records</a></p></details></section>'''.replace('RUN', MANIFEST['run_id'])
    report = report.replace('</header>', '</header>'+note, 1)
    comparison = '<section><h2>Existing Claude and control results on these same 10 windows</h2>'
    comparison += '<p>Copied for comparison only; the original findings remain unchanged. Model sample counts are shown below.</p>'
    comparison += model_table(pd.DataFrame(matched))+'</section>'
    report = report.replace('<footer>', comparison+'<footer>', 1)
    report = report.replace('windows both traded', 'windows all three traded')
    report = report.replace('<th>trades</th>', '<th>decisions</th>').replace('<h2>Models vs controls</h2>', '<h2>OpenAI results</h2>')
    report = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'+report+'</html>'
    html_path = ROOT/'data/sim/reports'/f"{MANIFEST['run_id']}.html"
    assert not html_path.exists()
    html_path.write_text(report)
    changed = [name for name, digest in MANIFEST['original_sha256'].items() if sha(ROOT/name) != digest]
    (HERE/'preservation_check.json').write_text(json.dumps({'checked_files':len(MANIFEST['original_sha256']), 'changed_files':changed}, indent=2))
    assert not changed, f'Original files changed concurrently: {changed}'
    print(summarize_sim(df).to_string())
    print(f'Report: {html_path}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--finalize', action='store_true')
    args = ap.parse_args()
    records = collect()
    if args.finalize:
        finalize(records)
