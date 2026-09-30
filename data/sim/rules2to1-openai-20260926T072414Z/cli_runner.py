"""Fresh noninteractive Codex process per missing decision; no model tools permitted."""
import json,subprocess,hashlib,os,tempfile,time
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
M=json.loads((HERE/'manifest.json').read_text())
CODEX='/Applications/ChatGPT.app/Contents/Resources/codex'
DISABLE=['shell_tool','unified_exec','view_image','code_mode','code_mode_host','apps','browser_use','browser_use_external','computer_use','in_app_browser','multi_agent','plugins','hooks','memories','skill_search','image_generation','sleep_tool','goals','workspace_dependencies']

def run_one(case,model,attempt=1):
    c=M['cases'][case-1];family=model.split('-')[-1];d=HERE/'cli_attempts'/f'{family}_{case:03d}_attempt{attempt}';d.mkdir()
    work=Path(tempfile.mkdtemp(prefix='trader-'))
    prompt=Path(c['stimulus_dir'])/'input.txt';img=Path(c['stimulus_dir'])/'chart.png'
    text=prompt.read_text()+'\n\nUse only the supplied text and attached chart. No tools, external data, file access, or identity/date searches. Return only the required JSON.'
    args=[CODEX,'exec','--ignore-user-config','--ignore-rules','--skip-git-repo-check','--json','--color','never','-s','read-only','-C',str(work),'-m',model,'-c','model_reasoning_effort="medium"','-c','web_search="disabled"','-c','project_doc_max_bytes=0','-c','approval_policy="never"','--enable','skip_host_skill_discovery']
    for f in DISABLE:args+=['--disable',f]
    args+=['-i',str(img),'-o',str(d/'final.txt'),'-']
    meta={'case':case,'model':model,'reasoning_effort':'medium','attempt':attempt,'started_at':datetime.now(timezone.utc).isoformat(),'command':args,'cwd':str(work),'prompt_sha256':hashlib.sha256(text.encode()).hexdigest(),'chart_sha256':hashlib.sha256(img.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(prompt.read_bytes()).hexdigest(),'harness':'fresh Codex exec with attached image and full text; model tools disabled; changed from desktop subagents on resumption'}
    (d/'request.txt').write_text(text);(d/'request.json').write_text(json.dumps(meta,indent=2))
    env=os.environ.copy()
    # Prevent inheritance of parent-task identity or plugin runtime coordinates.
    for k in list(env):
        if k.startswith(('CODEX_THREAD','CODEX_PARENT','CODEX_TASK','CODEX_MCP','CODEX_INTERNAL','OPENAI_API_KEY')):env.pop(k,None)
    try:
        with (d/'events.jsonl').open('w') as out,(d/'stderr.txt').open('w') as err:
            p=subprocess.run(args,input=text,text=True,stdout=out,stderr=err,env=env,timeout=180)
        result={'returncode':p.returncode}
    except subprocess.TimeoutExpired:
        result={'returncode':None,'error':'runner timeout'}
    result['finished_at']=datetime.now(timezone.utc).isoformat();(d/'execution.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'case':case,'model':model,**result,'directory':str(d)}),flush=True)
    return d

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('case',type=int);p.add_argument('model');p.add_argument('--attempt',type=int,default=1);a=p.parse_args();run_one(a.case,a.model,a.attempt)
