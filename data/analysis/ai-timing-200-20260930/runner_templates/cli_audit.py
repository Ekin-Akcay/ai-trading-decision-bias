"""Fail-closed transcript delivery audit for the new isolated timing experiment.
No model call is made by this module. CLI runtime wrappers are permitted only in
an exact shape derived from a prior fresh Codex exec transcript. The model's
standard runtime/system instructions remain a documented non-experimental input.
"""
import base64,hashlib,json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SUFFIX='\n\nUse only the supplied text and attached chart. No tools, external data, file access, or identity/date searches. Return only the required JSON.'
SESSION_ROOT=Path('[local-runtime-record]')
ALLOWED_RESPONSE_TYPES={'message','reasoning'}

def sha_bytes(x):return hashlib.sha256(x).hexdigest()
def environment_wrapper(cwd,started_at):
    local_date=datetime.fromisoformat(started_at.replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Istanbul')).date().isoformat()
    return ('<environment_context>\n'
        f'  <cwd>{cwd}</cwd>\n'
        '  <shell>zsh</shell>\n'
        f'  <current_date>{local_date}</current_date>\n'
        '  <timezone>Europe/Istanbul</timezone>\n'
        f'  <filesystem><workspace_roots><root>{cwd}</root></workspace_roots><permission_profile type="managed"><file_system type="restricted"><entry access="read"><special>:root</special></entry></file_system></permission_profile></filesystem>\n'
        '</environment_context>')

def inspect_transcript(events,request,expected,image_sha,thread_id):
    """Pure audit; useful with synthetic mutated transcripts without any calls."""
    issues=[];contexts=[];user_messages=[];developer_messages=[];system_messages=[];finals=[];calls=[];meta=[];end=None
    for e in events:
        p=e.get('payload',{})
        if e.get('type')=='session_meta':meta.append(p)
        if e.get('type')=='turn_context':contexts.append({'model':p.get('model'),'effort':p.get('effort')})
        if e.get('type')!='response_item':continue
        typ=p.get('type')
        if typ not in ALLOWED_RESPONSE_TYPES:calls.append({'type':typ,**{k:p[k] for k in ('name','input','arguments') if k in p}})
        if typ!='message':continue
        role=p.get('role');content=p.get('content',[])
        if role=='user':user_messages.append(content)
        elif role=='developer':developer_messages.append(content)
        elif role=='system':system_messages.append(content)
        elif role=='assistant':
            if p.get('phase')=='final_answer':
                if any(b.get('type')!='output_text' for b in content):issues.append('Unexpected final content type')
                finals.append('\n'.join(b.get('text','') for b in content));end=e.get('timestamp')
            else:issues.append('Unexpected nonfinal assistant message')
        else:issues.append('Unknown message role')
    cwd=request['cwd'];image_path=str(Path(cwd)/'chart.png')
    if len(meta)!=1:issues.append('Expected exactly one session metadata record')
    else:
        x=meta[0]
        if x.get('id',x.get('session_id'))!=thread_id:issues.append('Session metadata ID mismatch')
        if x.get('session_id') not in (None,thread_id):issues.append('Conflicting session IDs')
        if x.get('cwd')!=cwd or x.get('source')!='exec' or x.get('originator')!='codex_exec':issues.append('Wrong session origin or working directory')
        if any(x.get(k) for k in ('forked_from_id','parent_thread_id','parent_session_id','resumed_from')):issues.append('Inherited/resumed session metadata')
    if contexts!=[{'model':request['model'],'effort':'medium'}]:issues.append('Wrong model/effort or not exactly one fresh turn')
    if len(user_messages)!=2:issues.append('Expected runtime wrapper plus one assigned user turn only')
    else:
        env=user_messages[0]
        if env!=[{'type':'input_text','text':environment_wrapper(cwd,request['started_at'])}]:issues.append('Unexpected runtime environment wrapper')
        msg=user_messages[1]
        wrapper=f'<image name=[Image #1] path="{image_path}">'
        if len(msg)!=4 or [b.get('type') for b in msg]!=['input_text','input_image','input_text','input_text']:
            issues.append('Unexpected assigned user content structure')
        else:
            if [msg[0].get('text'),msg[2].get('text'),msg[3].get('text')]!=[wrapper,'</image>',expected]:issues.append('Unexpected extra user text, attachment path, or request')
            uri=msg[1].get('image_url','')
            try:
                assert re.fullmatch(r'data:image/(?:png|jpeg);base64,[A-Za-z0-9+/=\r\n]+',uri)
                received=sha_bytes(base64.b64decode(uri.split(',',1)[1],validate=True))
            except Exception:received=None
            if received!=image_sha:issues.append('Delivered image bytes do not match frozen chart')
    if calls:issues.append('Disallowed tool call or unknown response item')
    if len(finals)!=1:issues.append('Missing unique final answer')
    # Developer/runtime instructions are not silently treated as an absent input.
    runtime_hashes=[sha_bytes(json.dumps(x,sort_keys=True,separators=(',',':')).encode()) for x in developer_messages]
    return {'issues':issues,'contexts':contexts,'calls':calls,'raw':finals[0] if len(finals)==1 else '', 'end':end,'developer_instruction_sha256':runtime_hashes,'system_message_count':len(system_messages),'base_instructions_sha256':sha_bytes(json.dumps(meta[0].get('base_instructions'),sort_keys=True).encode()) if len(meta)==1 else None,'user_message_count':len(user_messages)}

def collect_cli(here,manifest,parse_decision):
    records=[];audits=[];seen_sessions={};seen_cwds={}
    cases={c['case']:c for c in manifest['cases']}
    assert len(cases)==len(manifest['cases'])
    runtime_lock=manifest.get('runtime_instruction_lock')
    budget=json.loads(Path(manifest['budget_file']).read_text())
    assert len(budget['reserved_attempts'])<=budget['authorized_maximum_attempts']<=200
    assert sha_bytes(Path(budget['old_budget_file_absolute']).read_bytes())==budget['old_budget_sha256']
    for d in sorted((here/'cli_attempts').glob('*')):
        if not (d/'execution.json').exists():continue
        req=json.loads((d/'request.json').read_text());exe=json.loads((d/'execution.json').read_text());issues=[]
        case=cases.get(req.get('case'))
        if case is None:raise RuntimeError('Unknown case in attempt metadata')
        if req.get('model') not in manifest['models']:issues.append('Unplanned model')
        auth_path=d/'authorization.json'
        if not auth_path.exists():issues.append('Missing durable launch authorization')
        else:
            try:
                auth=json.loads(auth_path.read_text())
                if sha_bytes(auth_path.read_bytes())!=req.get('authorization_sha256'):issues.append('Launch authorization hash mismatch')
                if req['case'] not in auth['authorized_cases']:issues.append('Case not authorized at launch')
                if auth.get('stage')!=case.get('stage') or req.get('stage')!=case.get('stage'):issues.append('Launch authorization/manifest/request stage mismatch')
            except Exception as exc:issues.append('Invalid launch authorization: '+repr(exc))
        reserved=[r for r in budget['reserved_attempts'] if r.get('run_id')==manifest['run_id'] and r.get('case')==req['case'] and r.get('model')==req['model'] and r.get('attempt')==req['attempt']]
        if len(reserved)!=1:issues.append('Missing or duplicate durable budget reservation')
        elif reserved[0].get('stage') not in (None,case.get('stage')):issues.append('Budget reservation stage mismatch')
        prompt=Path(case['stimulus_dir'])/'input.txt';expected=prompt.read_text()+SUFFIX
        if sha_bytes(prompt.read_bytes())!=case['input_sha256']:issues.append('Frozen input file changed')
        if sha_bytes((Path(case['stimulus_dir'])/'chart.png').read_bytes())!=case['image_sha256']:issues.append('Frozen image file changed')
        if (d/'request.txt').read_text()!=expected:issues.append('Request file differs from exact frozen input and suffix')
        if req.get('input_sha256')!=case['input_sha256'] or req.get('chart_sha256')!=case['image_sha256'] or req.get('prompt_sha256')!=sha_bytes(expected.encode()):issues.append('Request metadata hash mismatch')
        try:ev=[json.loads(s) for s in (d/'events.jsonl').read_text().splitlines() if s.strip()]
        except Exception:ev=[];issues.append('Malformed events transcript')
        tids=[e['thread_id'] for e in ev if e.get('type')=='thread.started'];matches=list(SESSION_ROOT.rglob('*'+tids[0]+'.jsonl')) if len(tids)==1 else []
        if len(matches)==1:
            source=matches[0]
            try:
                trans=[json.loads(s) for s in source.read_text().splitlines() if s.strip()]
                audit=inspect_transcript(trans,req,expected,case['image_sha256'],tids[0]);issues+=audit['issues']
            except Exception as exc:
                audit={'raw':'','contexts':[],'calls':[],'end':None};issues.append('Transcript cannot be fully audited: '+repr(exc))
        else:source=None;audit={'raw':'','contexts':[],'calls':[],'end':None};issues.append('Unique fresh transcript not found')
        if runtime_lock:
            if audit.get('developer_instruction_sha256')!=runtime_lock['developer_instruction_sha256'] or audit.get('base_instructions_sha256')!=runtime_lock['base_instructions_sha256'] or audit.get('system_message_count')!=runtime_lock.get('system_message_count',0):issues.append('CLI runtime instruction bundle differs from frozen reference')
        else:issues.append('No frozen runtime instruction bundle')
        if exe.get('returncode')!=0:issues.append('Runner did not exit successfully')
        raw=audit['raw'];decision=parse_decision(raw)
        if decision.get('action')=='error':issues.append('Invalid forced decision contract')
        if (d/'final.txt').exists() and (d/'final.txt').read_text().strip()!=raw.strip():issues.append('Final output file/transcript disagree')
        tid=tids[0] if len(tids)==1 else None
        if tid in seen_sessions:
            issues.append('Session ID reused by another attempt');audits[seen_sessions[tid]]['issues'].append('Session ID reused by another attempt');audits[seen_sessions[tid]]['passed']=False
        elif tid:seen_sessions[tid]=len(audits)
        cwd=req.get('cwd')
        if cwd in seen_cwds:
            issues.append('Working directory reused by another attempt');audits[seen_cwds[cwd]]['issues'].append('Working directory reused by another attempt');audits[seen_cwds[cwd]]['passed']=False
        elif cwd:seen_cwds[cwd]=len(audits)
        aid='/cli/'+d.name
        rec={'case':req['case'],'stage':case['stage'],'model':req['model'],'agent_path':aid,'thread_id':tid,'ts_decided':audit['end'] or exe['finished_at'],'reasoning_effort':'medium','contexts':audit['contexts'],'raw_response':raw,'decision':decision,'tool_calls':audit['calls'],'source_transcript':str(source) if source else None,'harness':'Codex exec','isolation':'Fresh single exec, neutral attachment, exact allowed user wrappers and frozen runtime bundle; no tool access','attempt_directory':str(d),'request_sha256':req['prompt_sha256']}
        out=d/'audited_response.json'
        if out.exists():assert json.loads(out.read_text())==rec
        else:out.write_text(json.dumps(rec,indent=2)+'\n')
        records.append(rec)
        audits.append({'agent_path':aid,'model':req['model'],'case':req['case'],'passed':not issues,'issues':issues,'full_input_received':not any('user' in x or 'input' in x or 'Request' in x for x in issues),'received_image_count':1 if not any('image' in x or 'content structure' in x for x in issues) else None,'tool_calls':audit['calls'],'source_transcript':str(source),'delivery':'exact full text and neutral image attachment','user_message_count':audit.get('user_message_count'),'developer_instruction_sha256':audit.get('developer_instruction_sha256'),'base_instructions_sha256':audit.get('base_instructions_sha256'),'system_message_count':audit.get('system_message_count')})
    return records,audits
