"""Read-only collection/audit of fresh subagents; additive evaluation and reporting.

Usage: python -B manage.py
Collect and audit desktop subagents and fresh CLI resumption attempts.
Use publish_partial.py to append evaluated records and refresh reports.
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
PREFIX = '/root/v2_'
MODELS = {'luna':'gpt-5.6-luna','terra':'gpt-5.6-terra','astra':'gpt-6-astra'}
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'scripts'))
def parse_decision(raw):
    try:
        txt=raw.strip()
        if txt.startswith('```'):
            txt=re.sub(r'^```(?:json)?\s*|\s*```$', '', txt)
        obj=json.loads(txt)
        stop=obj.get('stop_loss_pct')
        if obj.get('action') not in ('long','short') or isinstance(stop,bool) or not isinstance(stop,(int,float)) or not math.isfinite(stop) or not 0.05<=stop<=50:
            raise ValueError('Invalid direction or stop outside 0.05–50 percent')
        conf=obj.get('confidence')
        if isinstance(conf,bool) or not isinstance(conf,(int,float)) or not 0<=conf<=1:
            raise ValueError('Invalid confidence')
        return {'action':obj['action'],'stop_pct':stop/100,'tp_pct':2*(stop/100),'confidence':conf,'reason':str(obj.get('reason',''))}
    except (ValueError,TypeError,AttributeError):
        return {'action':'error','stop_pct':0,'tp_pct':0,'confidence':0,'reason':'Invalid forced 2:1 decision'}



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
    if not full_input:
        issues.append('Complete contract/text delivery not verified')
    if image_count < 1:
        issues.append(f'No chart delivered; observed {image_count}')
    if record['contexts'] != [{'model':record['model'],'effort':'medium'}]:
        issues.append('Unexpected model, effort or multiple turns')
    if record['decision']['action']=='error':
        issues.append('Invalid decision JSON/contract')
    assert sha(source_prompt) == case['prompt_sha256']
    assert hashlib.sha256(expected_input.encode()).hexdigest() == case['input_sha256']
    assert sha(ROOT/case['chart_file']) == case['image_sha256']
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
            match = re.fullmatch(re.escape(PREFIX)+r'(luna|terra|astra)(\d{3})(?:_retry\d+)?', agent)
            if not match:
                continue
            events = [json.loads(s) for s in f if s.strip()]
        family, num = match.groups()
        case_num = int(num)
        assert 1 <= case_num <= 100
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
    from cli_audit import collect_cli
    cli_records,cli_audits=collect_cli(HERE,MANIFEST,parse_decision)
    for a in cli_audits:
        if not a['passed'] and a['agent_path'] not in exclusions:
            exclusions[a['agent_path']]={'issues':a['issues'],'excluded_at':datetime.now(timezone.utc).isoformat(),'policy':'Pre-scoring validity/access failure; preserve and fresh rerun, at most three attempts.'}
    records.extend(cli_records)
    audits.extend(cli_audits)
    excluded_path.write_text(json.dumps(exclusions,indent=2))
    eligible = [r for r in records if r['agent_path'] not in exclusions]
    eligible.sort(key=lambda r:(r['case'],list(MODELS.values()).index(r['model'])))
    keys = [(r['case'],r['model']) for r in eligible]
    assert len(keys)==len(set(keys)), 'Multiple eligible attempts; do not select after outcomes'
    missing = [(i,m) for i in range(1,101) for m in MODELS.values() if (i,m) not in set(keys)]
    audit_doc = {'eligible_decisions':len(eligible),'attempts':len(records),
                 'all_eligible_passed':all(a['passed'] for a in audits if a['agent_path'] not in exclusions),
                 'method':'Fresh subagent per decision; observed tool allowlist and complete contract/text/image delivery. Instruction-based, not an OS sandbox; TP derived only by harness.',
                 'agents':audits,'excluded_attempts':exclusions,'missing':missing}
    (HERE/'isolation_audit.json').write_text(json.dumps(audit_doc,indent=2))
    print(json.dumps({'eligible':len(eligible),'attempts':len(records),'excluded':len(exclusions),
                      'models':dict(Counter(r['model'] for r in eligible)),
                      'failures':{a['agent_path']:a['issues'] for a in audits if not a['passed']},
                      'remaining':len(missing), 'recent_missing':missing[:6]},indent=2))
    return eligible, audit_doc


def clean(row):
    return {k:None if isinstance(v,float) and not math.isfinite(v) else v for k,v in row.items()}


def write_new(path, text):
    with path.open('x') as f:
        f.write(text)


def cumulative_chart(frame):
    """One hundred bars with sparse case labels; full per-case values remain in cards."""
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


if __name__=='__main__':
    collect()
