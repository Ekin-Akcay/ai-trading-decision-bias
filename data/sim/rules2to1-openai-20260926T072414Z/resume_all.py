"""Resume exactly the missing model/case slots with bounded parallelism and checkpoints."""
import concurrent.futures as cf
import json,subprocess,sys,hashlib,time
from pathlib import Path
from datetime import datetime,timezone
import manage
from cli_runner import run_one
HERE=Path(__file__).resolve().parent

def checkpoint():
    p=subprocess.run([sys.executable,'-B',str(HERE/'publish_partial.py')],capture_output=True,text=True)
    with (HERE/'resume_checkpoints.log').open('a') as f:f.write(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError('Checkpoint failed; inspect resume_checkpoints.log')
    progress=json.loads((HERE/'progress.json').read_text())
    print(json.dumps({'checkpoint':progress['accepted_decisions'],'remaining':progress['remaining_decisions'],'models':progress['counts_by_model']}),flush=True)


def main():
    records,audit=manage.collect()
    ledger=HERE.parents[2]/'data/sim/decisions'/f"{manage.MANIFEST['run_id']}.jsonl"
    start=HERE/'resume_started.json'
    if not start.exists():
        start.write_text(json.dumps({'started_at':datetime.now(timezone.utc).isoformat(),'initial_ledger_sha256':hashlib.sha256(ledger.read_bytes()).hexdigest(),'initial_ledger_rows':len(ledger.read_text().splitlines()),'initial_accepted':len(records),'parallel_workers':8,'runner':'Codex exec','protocol_unchanged':True,'model_ids_unchanged':True,'reasoning_effort':'medium','harness_change':'Direct text/image attachment; disabled tools; empty per-decision cwd; actual single-turn transcripts audited.'},indent=2))
        (HERE/'resume_initial_ledger.jsonl').write_bytes(ledger.read_bytes())
    checkpoint()
    for wave in range(1,4):
        _,audit=manage.collect()
        if not audit['missing']:break
        tasks=[]
        for case,model in audit['missing']:
            family=model.split('-')[-1]
            prev=list((HERE/'cli_attempts').glob(f'{family}_{case:03d}_attempt*'))
            n=len(prev)+1
            if n<=3:tasks.append((case,model,n))
        if not tasks:break
        with cf.ThreadPoolExecutor(max_workers=8) as pool:
            todo=iter(tasks);active={}
            def fill():
                while len(active)<8:
                    try:a=next(todo)
                    except StopIteration:break
                    active[pool.submit(run_one,*a)]=a
            fill();count=0
            while active:
                done,_=cf.wait(active,timeout=15,return_when=cf.FIRST_COMPLETED)
                for fut in done:
                    args=active.pop(fut)
                    try:fut.result()
                    except Exception as exc:
                        (HERE/'runner_errors.log').open('a').write(repr((args,exc))+'\n')
                    count+=1
                fill()
                if done and count>=8:
                    checkpoint();count=0
        checkpoint()
    _,audit=manage.collect()
    final={'finished_at':datetime.now(timezone.utc).isoformat(),'accepted':audit['eligible_decisions'],'missing':audit['missing'],'excluded':len(audit['excluded_attempts'])}
    (HERE/'resume_finished.json').write_text(json.dumps(final,indent=2))
    print(json.dumps(final),flush=True)
    if audit['missing']:sys.exit(2)

if __name__=='__main__':main()
