"""Verify fresh CLI transcripts and actual delivered stimulus before scoring."""
import base64,hashlib,json
from pathlib import Path

def collect_cli(here,manifest,parse_decision):
    records,audits=[],[]
    session_root=Path('[local-runtime-record]')
    for d in sorted((here/'cli_attempts').glob('*')):
        if not (d/'execution.json').exists():continue
        req=json.loads((d/'request.json').read_text());exe=json.loads((d/'execution.json').read_text())
        ev=[json.loads(s) for s in (d/'events.jsonl').read_text().splitlines() if s.strip()]
        tids=[e['thread_id'] for e in ev if e['type']=='thread.started']
        matches=list(session_root.rglob('*'+tids[0]+'.jsonl')) if len(tids)==1 else []
        issues=[];ctx=[];calls=[];texts=[];images=[];finals=[];end=None;source=None
        if len(matches)==1:
            source=matches[0]
            for s in source.read_text().splitlines():
                e=json.loads(s);p=e.get('payload',{})
                if e['type']=='turn_context':ctx.append({'model':p.get('model'),'effort':p.get('effort')})
                if e['type']!='response_item':continue
                if p.get('type') in ('function_call','custom_tool_call'):calls.append({k:p[k] for k in ('name','input','arguments') if k in p})
                if p.get('type')=='message' and p.get('role')=='user':
                    for b in p.get('content',[]):
                        if b.get('type')=='input_text':texts.append(b.get('text',''))
                        if b.get('type')=='input_image':images.append(b.get('image_url',''))
                if p.get('type')=='message' and p.get('role')=='assistant' and p.get('phase')=='final_answer':
                    finals.append('\n'.join(b.get('text','') for b in p.get('content',[])));end=e.get('timestamp')
        else:issues.append('Unique transcript not found')
        c=manifest['cases'][req['case']-1]
        expected=(d/'request.txt').read_text()
        base=manifest['contract']+'\n\n'+(here.parents[2]/c['source_prompt']).read_text()
        if not expected.startswith(base) or expected not in texts:issues.append('Full assigned input delivery not verified')
        if hashlib.sha256(expected.encode()).hexdigest()!=req['prompt_sha256']:issues.append('Request hash mismatch')
        if len(images)!=1:issues.append('Expected exactly one attached image')
        else:
            try: image_hash=hashlib.sha256(base64.b64decode(images[0].split(',',1)[1])).hexdigest()
            except Exception:image_hash=None
            if image_hash!=c['image_sha256']:issues.append('Delivered image differs from original')
        if ctx!=[{'model':req['model'],'effort':'medium'}]:issues.append('Wrong model/effort or not a fresh single turn')
        if calls:issues.append('Disallowed tool access')
        if exe['returncode']!=0:issues.append('Runner did not exit successfully')
        if len(finals)!=1:issues.append('Missing unique final response')
        raw=finals[0] if len(finals)==1 else ''
        decision=parse_decision(raw)
        if decision['action']=='error':issues.append('Invalid forced 2:1 decision')
        aid='/cli/'+d.name
        rec={'case':req['case'],'model':req['model'],'agent_path':aid,'thread_id':tids[0] if tids else None,
             'ts_decided':end or exe['finished_at'],'reasoning_effort':'medium','contexts':ctx,'raw_response':raw,
             'decision':decision,'tool_calls':calls,'source_transcript':str(source) if source else None,
             'harness':'Codex exec','isolation':'fresh CLI process and empty working directory; model tools disabled; complete text and original image bytes audited',
             'attempt_directory':str(d),'request_sha256':req['prompt_sha256']}
        out=d/'audited_response.json'
        if out.exists():assert json.loads(out.read_text())==rec
        else:out.write_text(json.dumps(rec,indent=2))
        records.append(rec)
        audits.append({'agent_path':aid,'model':req['model'],'case':req['case'],'passed':not issues,'issues':issues,
                       'full_input_received':expected in texts,'received_image_count':len(images),'tool_calls':calls,
                       'source_transcript':str(source),'delivery':'direct full text + original image attachment'})
    return records,audits
