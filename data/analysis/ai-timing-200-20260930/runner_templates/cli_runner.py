"""Fresh noninteractive Codex process per fresh reversal-test decision; no model tools permitted."""
import json,subprocess,hashlib,os,tempfile,time,fcntl,shutil
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
M=json.loads((HERE/'manifest.json').read_text())
CODEX='/Applications/ChatGPT.app/Contents/Resources/codex'
DISABLE=['shell_tool','unified_exec','view_image','code_mode','code_mode_host','apps','browser_use','browser_use_external','computer_use','in_app_browser','multi_agent','plugins','hooks','memories','skill_search','image_generation','sleep_tool','goals','workspace_dependencies']

def reserve_budget(case,model,attempt):
    budget=Path(M['budget_file'])
    with budget.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        b=json.loads(budget.read_text())
        authorization_bytes=(HERE/'stage_authorization.json').read_bytes()
        authorized=json.loads(authorization_bytes)
        assert case in authorized['authorized_cases'] and model in M['models'], 'Case/model not authorized in current stage'
        assert hashlib.sha256(Path(b['old_budget_file_absolute']).read_bytes()).hexdigest()==b['old_budget_sha256'], 'Old budget changed'
        assert hashlib.sha256(Path(M['protocol_file_absolute']).read_bytes()).hexdigest()==M['protocol_sha256'], 'Frozen protocol changed'
        assert hashlib.sha256(Path(M['selection_plan_file_absolute']).read_bytes()).hexdigest()==M['selection_plan_sha256'], 'Frozen selection changed'
        if len(b['reserved_attempts'])>=b['authorized_maximum_attempts']:raise RuntimeError('New 200-attempt allowance exhausted')
        key={'run_id':M['run_id'],'case':case,'model':model,'attempt':attempt}
        assert not any(all(v.get(k)==value for k,value in key.items()) for v in b['reserved_attempts']), 'Duplicate reservation'
        b['reserved_attempts'].append(dict(key,reserved_at=datetime.now(timezone.utc).isoformat(),stage=authorized['stage'],authorization_sha256=hashlib.sha256(authorization_bytes).hexdigest()))
        tmp=budget.with_suffix('.tmp');tmp.write_text(json.dumps(b,indent=2)+'\n');tmp.replace(budget)
        fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
        return authorized,authorization_bytes

def run_one(case,model,attempt=1):
    c=M['cases'][case-1]
    assert c['case']==case
    original_prompt=Path(c['stimulus_dir'])/'input.txt'; original_chart=Path(c['stimulus_dir'])/'chart.png'
    assert hashlib.sha256(original_prompt.read_bytes()).hexdigest()==c['input_sha256']
    assert hashlib.sha256(original_chart.read_bytes()).hexdigest()==c['image_sha256']
    authorization,authbytes=reserve_budget(case,model,attempt)
    c=M['cases'][case-1];family=model.split('-')[-1];d=HERE/'cli_attempts'/f'{family}_{case:03d}_attempt{attempt}';d.mkdir()
    work=Path(tempfile.mkdtemp(prefix='trader-'))
    prompt=original_prompt;img=work/'chart.png'
    shutil.copyfile(original_chart,img)
    text=prompt.read_text()+'\n\nUse only the supplied text and attached chart. No tools, external data, file access, or identity/date searches. Return only the required JSON.'
    args=[CODEX,'exec','--ignore-user-config','--ignore-rules','--skip-git-repo-check','--json','--color','never','-s','read-only','-C',str(work),'-m',model,'-c','model_reasoning_effort="medium"','-c','web_search="disabled"','-c','project_doc_max_bytes=0','-c','approval_policy="never"','--enable','skip_host_skill_discovery']
    for f in DISABLE:args+=['--disable',f]
    args+=['-i',str(img),'-o',str(work/'final.txt'),'-']
    meta={'case':case,'model':model,'reasoning_effort':'medium','attempt':attempt,'started_at':datetime.now(timezone.utc).isoformat(),'command':args,'cwd':str(work),'prompt_sha256':hashlib.sha256(text.encode()).hexdigest(),'chart_sha256':hashlib.sha256(img.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(prompt.read_bytes()).hexdigest(),'harness':'fresh Codex exec with attached image and full text; model tools disabled; v2 full MA-present input; uninformed of conditional sampling and delayed-entry evaluation; neutral attachment path'}
    (d/'authorization.json').write_bytes(authbytes)
    meta['stage']=c['stage'];meta['authorization_sha256']=hashlib.sha256(authbytes).hexdigest()
    (d/'request.txt').write_text(text);(d/'request.json').write_text(json.dumps(meta,indent=2))
    env=os.environ.copy()
    # Prevent inheritance of parent-task identity or plugin runtime coordinates.
    for k in list(env):
        if k.startswith(('CODEX_THREAD','CODEX_PARENT','CODEX_TASK','CODEX_MCP','CODEX_INTERNAL','OPENAI_API_KEY')):env.pop(k,None)
    try:
        with (d/'events.jsonl').open('w') as out,(d/'stderr.txt').open('w') as err:
            p=subprocess.run(args,input=text,text=True,stdout=out,stderr=err,env=env,timeout=240)
        result={'returncode':p.returncode}
    except subprocess.TimeoutExpired:
        result={'returncode':None,'error':'runner timeout'}
    if (work/'final.txt').exists():shutil.copyfile(work/'final.txt',d/'final.txt')
    result['finished_at']=datetime.now(timezone.utc).isoformat();(d/'execution.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'case':case,'model':model,**result,'directory':str(d)}),flush=True)
    return d

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('case',type=int);p.add_argument('model');p.add_argument('--attempt',type=int,default=1);a=p.parse_args();run_one(a.case,a.model,a.attempt)
