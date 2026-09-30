"""Read-only collection/audit of fresh subagents; additive evaluation and reporting.

Usage: python -B manage.py audit | finalize
Canonical new records contain only setups 11–60. Cumulative reporting includes the
prior run by reference, so existing decisions are not duplicated in the shared ledger.
"""
import argparse
import hashlib
import html
import json
import math
import re
import shlex
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST = json.loads((HERE/'manifest.json').read_text())
PREFIX = '/root/collect60_060500/'
MODELS = {'luna':'gpt-5.6-luna','terra':'gpt-5.6-terra','astra':'gpt-6-astra'}
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'scripts'))
from nai.prompts import parse_decision


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_record(record, outputs):
    case = MANIFEST['cases'][record['case']-1]
    directory = Path(case['stimulus_dir'])
    prompt, chart = str(directory/'input.txt'), str(directory/'chart.png')
    issues, commands, image_paths, nested = [], [], [], []
    for call in record['tool_calls']:
        if call['name'] not in ('exec','functions.exec'):
            issues.append('Unexpected outer tool: '+call['name'])
            continue
        code = call.get('input','')
        names = re.findall(r'tools\.([A-Za-z_][A-Za-z_0-9]*)\s*\(', code)
        nested.extend(names)
        if set(names)-{'exec_command','view_image'}:
            issues.append('Unexpected nested tools')
        if re.search(r'\b(cua|fetch|eval|Function|load|store|ALL_TOOLS)\b|tools\[', code):
            issues.append('Unexpected dynamic access')
        cmd_matches = re.findall(r'''(?:"cmd"|'cmd'|\bcmd)\s*:\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')''', code)
        for literal in cmd_matches:
            cmd = json.loads(literal) if literal[0]=='"' else literal[1:-1]
            commands.append(cmd)
            if shlex.split(cmd) != ['cat',prompt]:
                issues.append('Unexpected shell command: '+cmd)
        if names.count('exec_command') != len(cmd_matches):
            issues.append('Unverified shell command')
        image_matches = re.findall(r'''(?:"path"|'path'|\bpath)\s*:\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')''', code)
        for literal in image_matches:
            path = json.loads(literal) if literal[0]=='"' else literal[1:-1]
            image_paths.append(path)
            if path != chart:
                issues.append('Unexpected image path: '+path)
        if names.count('view_image') != len(image_matches):
            issues.append('Unverified image path')
    if not commands or not image_paths:
        issues.append('Missing stimulus access')
    texts, image_count = [], 0
    for output in outputs:
        blocks = [{'type':'input_text','text':output}] if isinstance(output,str) else output
        for block in blocks:
            if block.get('type') in ('input_image','image'):
                image_count += 1
            if block.get('type') in ('input_text','text'):
                text = block.get('text','')
                texts.append(text)
                try:
                    obj = json.loads(text)
                    if isinstance(obj,dict) and isinstance(obj.get('output'),str):
                        texts.append(obj['output'])
                except (ValueError,TypeError):
                    pass
    delivered = '\n'.join(texts)
    source_prompt = ROOT/case['source_prompt']
    expected_input = MANIFEST['contract']+'\n\n'+source_prompt.read_text()
    full_input = expected_input in delivered
    if not full_input or image_count != 1:
        issues.append('Full contract/text and single chart delivery not verified')
    if record['contexts'] != [{'model':record['model'],'effort':'medium'}]:
        issues.append('Unexpected model, effort or multiple turns')
    if record['decision']['action']=='error':
        issues.append('Invalid decision JSON/contract')
    assert sha(source_prompt) == case['prompt_sha256']
    assert hashlib.sha256(expected_input.encode()).hexdigest() == case['input_sha256']
    assert sha(ROOT/case['source_row']['image']) == case['image_sha256']
    if Path(prompt).exists():
        assert sha(Path(prompt)) == case['input_sha256']
    if Path(chart).exists():
        assert sha(Path(chart)) == case['image_sha256']
    return {'agent_path':record['agent_path'],'model':record['model'],'case':record['case'],
            'passed':not issues,'issues':issues,'commands':commands,'image_paths':image_paths,
            'nested_tools':nested,'full_input_received':full_input,'received_image_count':image_count}


def collect():
    records, audits = [], []
    excluded_path = HERE/'excluded_attempts.json'
    exclusions = json.loads(excluded_path.read_text())
    for path in sorted(Path('[local-runtime-record]').glob('*/*.jsonl')):
        with path.open() as f:
            line = next(f, '')
            if not line:
                continue
            meta = json.loads(line).get('payload',{})
            agent = meta.get('agent_path','')
            if not agent.startswith(PREFIX):
                continue
            match = re.fullmatch(re.escape(PREFIX)+r'(luna|terra|astra)_(\d{3})(?:_retry\d+)?', agent)
            if not match:
                continue
            events = [json.loads(s) for s in f if s.strip()]
        family, num = match.groups()
        case_num = int(num)
        assert 11 <= case_num <= 60
        contexts, calls, outputs, users, finals = [], [], [], [], []
        for e in events:
            d = e.get('payload',{})
            if e['type']=='turn_context':
                contexts.append({'model':d.get('model'),'effort':d.get('effort')})
            if e['type']!='response_item':
                continue
            if d.get('type') in ('custom_tool_call','function_call'):
                calls.append({k:d[k] for k in ('name','input','arguments') if k in d})
            if d.get('type') in ('custom_tool_call_output','function_call_output'):
                outputs.append(d.get('output',[]))
            if d.get('type')=='message' and d.get('role')=='user':
                users.append('\n'.join(c.get('text','') for c in d.get('content',[])))
            if d.get('type')=='message' and d.get('role')=='assistant' and d.get('phase')=='final_answer':
                finals.append(('\n'.join(c.get('text','') for c in d.get('content',[])),e.get('timestamp')))
        if not finals:
            continue
        assert len(finals)==1, 'Do not select between multiple answers'
        raw, decided = finals[0]
        record = {'case':case_num,'model':MODELS[family],'agent_path':agent,'thread_id':meta['id'],
                  'ts_decided':decided,'reasoning_effort':'medium','contexts':contexts,
                  'raw_response':raw,'decision':parse_decision(raw),'tool_calls':calls,
                  'user_messages':users,'source_transcript':str(path)}
        audit = audit_record(record, outputs)
        out = HERE/'responses'/f'{agent.split("/")[-1]}.json'
        if out.exists():
            assert json.loads(out.read_text())==record
        else:
            out.write_text(json.dumps(record,indent=2))
        if not audit['passed'] and agent not in exclusions:
            exclusions[agent]={'issues':audit['issues'],'excluded_at':datetime.now(timezone.utc).isoformat(),
                               'policy':'Input access/delivery or contract failure; excluded before scoring; preserve and repeat fresh.'}
        records.append(record)
        audits.append(audit)
    excluded_path.write_text(json.dumps(exclusions,indent=2))
    eligible = [r for r in records if r['agent_path'] not in exclusions]
    eligible.sort(key=lambda r:(r['case'],list(MODELS.values()).index(r['model'])))
    keys = [(r['case'],r['model']) for r in eligible]
    assert len(keys)==len(set(keys)), 'Multiple eligible attempts; do not select after outcomes'
    missing = [(i,m) for i in range(11,61) for m in MODELS.values() if (i,m) not in set(keys)]
    audit_doc = {'eligible_decisions':len(eligible),'attempts':len(records),
                 'all_eligible_passed':all(a['passed'] for a in audits if a['agent_path'] not in exclusions),
                 'method':'Fresh subagent per decision; observed tool allowlist and complete contract/text/image delivery. Instruction-based, not an OS sandbox.',
                 'agents':audits,'excluded_attempts':exclusions,'missing':missing}
    (HERE/'isolation_audit.json').write_text(json.dumps(audit_doc,indent=2))
    print(json.dumps({'eligible':len(eligible),'attempts':len(records),'excluded':len(exclusions),
                      'models':dict(Counter(r['model'] for r in eligible)),
                      'failures':{a['agent_path']:a['issues'] for a in audits if not a['passed']},
                      'remaining':len(missing)},indent=2))
    return eligible, audit_doc


def clean(row):
    return {k:None if isinstance(v,float) and not math.isfinite(v) else v for k,v in row.items()}


def write_new(path, text):
    with path.open('x') as f:
        f.write(text)


def cumulative_chart(frame):
    """Sixty bars with sparse case labels; full per-case values remain in cards."""
    vals = frame['pnl_gross_pct'].fillna(0).astype(float).tolist()
    n = len(vals)
    if not n:
        return ''
    width,height,left,right,top,bottom = 900,230,55,15,20,30
    iw,ih = width-left-right,height-top-bottom
    bound = max(0.1,max(abs(v) for v in vals))*1.15
    y = lambda v: top+ih*(bound-v)/(2*bound)
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Gross return by setup number">']
    for value in (-bound/1.15,0,bound/1.15):
        parts.append(f'<line x1="{left}" y1="{y(value):.1f}" x2="{width-right}" y2="{y(value):.1f}" stroke="var(--line)"/>')
        parts.append(f'<text x="{left-7}" y="{y(value):.1f}" text-anchor="end" dominant-baseline="middle" class="ax">{value:+.1f}%</text>')
    for i,(v,(_,row)) in enumerate(zip(vals,frame.iterrows())):
        x = left+iw*(i+0.5)/n
        w = iw/n*0.68
        cls = 'barwin' if v>0 else 'barloss'
        scored = row['outcome'] in ('tp','sl','timeout')
        detail = f"gross {v:+.2f}%; net {row['pnl_net_pct']:+.2f}%" if scored else 'no scored trade return'
        info = html.escape(f"Setup {int(row['case_number'])}: {row['action']}; {row['outcome']}; {detail}")
        style = '' if scored else ' style="fill:var(--muted)"'
        parts.append(f'<a href="#setup-{int(row["case_number"])}"><rect x="{x-w/2:.1f}" y="{min(y(v),y(0)):.1f}" width="{w:.1f}" height="{max(1,abs(y(v)-y(0))):.1f}" class="{cls}"{style}><title>{info}</title></rect></a>')
        if i==0 or (i+1)%10==0:
            parts.append(f'<text x="{x:.1f}" y="{height-8}" text-anchor="middle" class="ax">{int(row["case_number"])}</text>')
    parts.append('</svg><p class="reason">Horizontal axis: setup number. Gray markers indicate no scored trade. Hover for results or click a bar to see that setup.</p>')
    return ''.join(parts)


def finalize(records, audit):
    import pandas as pd
    from nai.sim import SimResolver, summarize_sim
    import sim_report_html as report_module
    from sim_report_html import build, model_table
    assert len(records)==150 and not audit['missing'] and audit['all_eligible_passed']
    evaluation = json.loads((HERE/'evaluation_provenance.json').read_text())
    for source,digest in evaluation['source_sha256'].items():
        assert sha(ROOT/source)==digest, f'Evaluation source changed during collection: {source}'
    resolver = SimResolver(['SOL-USD'],eval_interval='1m',time_stop_hours=72)
    result = []
    for r in records:
        c = MANIFEST['cases'][r['case']-1]
        d = r['decision']
        row = dict(c['source_row'])
        row.update(d)
        row.update(run_id=MANIFEST['run_id'],case_number=r['case'],model=r['model']+'-agent',
                   model_version=r['model']+' via Codex subagent',reasoning_effort='medium',
                   ts_decided=r['ts_decided'],agent_path=r['agent_path'],thread_id=r['thread_id'],
                   raw_response=r['raw_response'],stimulus='text+image',
                   system_prompt_sha256=hashlib.sha256(MANIFEST['contract'].encode()).hexdigest(),
                   stimulus_image_sha256=c['image_sha256'],stimulus_text_sha256=c['prompt_sha256'],
                   combined_input_sha256=c['input_sha256'],
                   isolation='fresh context per decision; tool access and full delivery audited; no hard sandbox')
        row.update(resolver.resolve(c['asset'],pd.Timestamp(c['window_end_ts']),d['action'],d['stop_pct'],d['tp_pct']))
        if d['action'] in ('long','short'):
            assert abs(row['entry_price']-row['price_real'])<1e-9
        result.append(clean(row))
    new_path = ROOT/'data/sim/decisions'/f"{MANIFEST['run_id']}.jsonl"
    write_new(new_path,''.join(json.dumps(r,allow_nan=False)+'\n' for r in result))
    prior_path = ROOT/'data/sim/decisions'/f"{MANIFEST['prior_run']}.jsonl"
    prior = [json.loads(s) for s in prior_path.read_text().splitlines() if s.strip()]
    combined = prior+result
    assert len(combined)==180 and len({(r['model'],r['window_id']) for r in combined})==180
    assert Counter(r['model'] for r in combined)==Counter({m+'-agent':60 for m in MODELS.values()})
    ids = {c['window_id'] for c in MANIFEST['cases']}
    assert {r['window_id'] for r in combined}==ids
    matched = []
    for name in ('agent-demo2-agents','agent-demo2-controls'):
        for s in (ROOT/'data/sim/decisions'/f'{name}.jsonl').read_text().splitlines():
            r = json.loads(s)
            if r['window_id'] in ids:
                matched.append(r)
    write_new(HERE/'matched_claude_and_controls.jsonl',''.join(json.dumps(r)+'\n' for r in matched))
    source_doc = {'canonical_decision_files':[str(prior_path.relative_to(ROOT)),str(new_path.relative_to(ROOT))],
                  'new_decisions':150,'cumulative_decisions':180,'setups_per_model':60,
                  'new_audit_passed':True,'new_excluded_attempts':len(audit['excluded_attempts'])}
    write_new(HERE/'report_sources.json',json.dumps(source_doc,indent=2))
    df, batch = pd.DataFrame(combined),pd.DataFrame(result)
    label = MANIFEST['run_id'].replace('openai-next50-','openai-first60-')
    report_module.pnl_chart_svg = cumulative_chart
    original_card = report_module.window_card
    def numbered_card(group):
        number = int(group.iloc[0]['case_number'])
        return original_card(group).replace('<article class="card">',
            f'<article class="card" id="setup-{number}"><h3 style="margin:0;padding:12px 16px;font-size:1rem">Setup {number:02d}</h3>',1)
    report_module.window_card = numbered_card
    report = build(df,'OpenAI comparison · first 60 SOL setups')
    note = f'''<section><p>180 accepted decisions · 60 identical saved SOL setups · 3 OpenAI models.<br>
    This update adds setups 11–60 (150 decisions) to the preserved first 10 (30 decisions).</p>
    <details><summary>Method, isolation audit and source records</summary>
    <p>Each decision used a fresh subagent, no inherited conversation, medium reasoning, the original
    saved numeric prompt and chart, and the same trade contract. Input files contain the contract
    followed by the original market prompt. Every accepted new agent passed an audit of its tool calls
    and complete text/image delivery. No previous decisions or outcomes were supplied.</p>
    <p>Isolation is instruction-based and audited, not an OS/tool sandbox. {len(audit['excluded_attempts'])}
    new attempts were excluded before scoring and retained separately. The first-10 run retains its
    original eight excluded attempts and documented wrapper changes. Codex and Claude Code harnesses
    differ, so this is not a model-weights-only comparison.</p>
    <p>Existing evaluator: one-minute first passage, 72-hour time stop, 20bps round-trip costs.
    The original prompt does not specify the timeout. Excursions include the full exit bar.
    Per-trade averages are not portfolio returns; these historical masked results are exploratory.</p>
    <p><a href="agent-demo2.html">Original Claude report</a> ·
    <a href="{MANIFEST['prior_run']}.html">Original OpenAI first-10 report</a> ·
    <a href="../{MANIFEST['run_id']}/manifest.json">Manifest</a> ·
    <a href="../{MANIFEST['run_id']}/isolation_audit.json">New isolation audit</a> ·
    <a href="../decisions/{MANIFEST['run_id']}.jsonl">150 new records</a> ·
    <a href="../{MANIFEST['run_id']}/report_sources.json">Cumulative report sources</a></p>
    </details></section>'''
    report = report.replace('</header>','</header>'+note,1)
    extra = '<section><h2>New batch only · setups 11–60</h2>'+model_table(batch)+'</section>'
    extra += '<section><h2>Existing Claude and control results on matching setups</h2>'
    extra += '<p>Original records are unchanged. Haiku and Sonnet cover these 60 setups; Opus has a smaller original sample, shown in the decisions column.</p>'
    extra += model_table(pd.DataFrame(matched))+'</section>'
    report = report.replace('<footer>',extra+'<footer>',1)
    report = report.replace('windows both traded','windows all three traded').replace('<th>trades</th>','<th>decisions</th>')
    report = report.replace('<h2>Models vs controls</h2>','<h2>OpenAI results · all 60 setups</h2>')
    report = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'+report+'</html>'
    report_path = ROOT/'data/sim/reports'/f'{label}.html'
    write_new(report_path,report)
    checks = {'checked_files':len(MANIFEST['original_sha256']),
              'changed_files':[name for name,h in MANIFEST['original_sha256'].items() if sha(ROOT/name)!=h]}
    write_new(HERE/'preservation_check.json',json.dumps(checks,indent=2))
    assert not checks['changed_files'], checks
    summaries = {'cumulative':json.loads(summarize_sim(df).reset_index().to_json(orient='records')),
                 'new_batch':json.loads(summarize_sim(batch).reset_index().to_json(orient='records')),
                 'outcomes':{m:dict(Counter(g['outcome'])) for m,g in df.groupby('model')}}
    write_new(HERE/'summary.json',json.dumps(summaries,indent=2))
    (HERE/'HANDOFF.md').write_text(f'''# OpenAI 60-setup comparison — complete

Added 150 decisions for SOL setups 11–60, using fresh Luna/Terra/Astra subagents at medium reasoning. Original saved market prompts and charts were hash-verified. New accepted decisions passed tool-access and complete input-delivery audits. No outcome feedback was provided. Isolation is audited instruction-based access, not a hard sandbox.

Canonical new records: ../decisions/{MANIFEST['run_id']}.jsonl
Cumulative HTML: ../reports/{label}.html
The cumulative report references the prior first-10 decision file plus the new next-50 file; no duplicate cumulative ledger was added to data/sim/decisions.

{len(audit['excluded_attempts'])} new invalid attempts were excluded before scoring and retained in responses/ and excluded_attempts.json. Existing first-10 exclusions remain as originally recorded. All {checks['checked_files']} pre-existing simulation files are unchanged. Original source code/configuration was not edited.

Use manifest.json for exact case ordering, isolation_audit.json for access verification, report_sources.json for run membership and summary.json for summary values. Collection coordinator: {PREFIX.rstrip('/')}. Raw attempts include model/effort, exact responses, assigned user messages and tool calls; no hidden reasoning was copied.

manage.py audit can recheck collection. Do not rerun finalize; it deliberately refuses to overwrite records.
''')
    print(summarize_sim(df).to_string())
    print('REPORT',report_path)


if __name__=='__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('action',choices=['audit','finalize'])
    args = ap.parse_args()
    records,audit = collect()
    if args.action=='finalize':
        finalize(records,audit)
