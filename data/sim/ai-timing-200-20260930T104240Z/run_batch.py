"""Run only the frozen validation cases; durable outputs; audit before scoring."""
from pathlib import Path
import json,math,re,concurrent.futures as cf,sys
from datetime import datetime,timezone
from cli_runner import run_one
from cli_audit import collect_cli
HERE=Path(__file__).resolve().parent;M=json.loads((HERE/'manifest.json').read_text())
def parse(raw):
    try:
        obj=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip()));s=obj['stop_loss_pct'];c=obj['confidence'];reason=obj['reason']
        assert set(obj)=={'action','stop_loss_pct','confidence','reason'}
        assert obj['action'] in ('long','short') and type(s) in (int,float) and math.isfinite(s) and .05<=s<=50
        assert type(c) in (int,float) and math.isfinite(c) and 0<=c<=1
        assert isinstance(reason,str) and 1<=len(reason.split())<=20
        return {'action':obj['action'],'stop_pct':s/100,'tp_pct':2*s/100,'confidence':c,'reason':reason}
    except Exception:return {'action':'error','stop_pct':0,'tp_pct':0,'confidence':0,'reason':'Invalid response contract'}
def checkpoint():
    records,audits=collect_cli(HERE,M,parse);passed={a['agent_path'] for a in audits if a['passed']};accepted=[r for r in records if r['agent_path'] in passed]
    # No choosing among answers: duplicate valid attempts are a hard error.
    keys={(r['case'],r['model']) for r in accepted};assert len(keys)==len(accepted)
    accepted.sort(key=lambda r:(r['case'],M['models'].index(r['model'])))
    authorized=json.loads((HERE/'stage_authorization.json').read_text())['authorized_cases']
    missing=[(c,m) for c in authorized for m in M['models'] if (c,m) not in keys]
    progress={'status':'decisions_collected' if not missing else 'collecting','accepted':len(accepted),'planned_this_batch':len(authorized),'planned_canonical_windows':len(M['cases']),'authorized_cases':authorized,'pending_unrequested_case_range':None,'missing_requested_pairs':missing,'models':{m:sum(r['model']==m for r in accepted) for m in M['models']},'attempts':len(records),'excluded_attempts':[a for a in audits if not a['passed']],'updated_at':datetime.now(timezone.utc).isoformat()}
    for name,data in [('progress.json',progress),('isolation_audit.json',{'all_accepted_passed':True,'audits':audits,'accepted':len(accepted),'excluded':sum(not a['passed'] for a in audits)})]:
        tmp=HERE/(name+'.tmp');tmp.write_text(json.dumps(data,indent=2));tmp.replace(HERE/name)
    tmp=HERE/'accepted_decisions.jsonl.tmp';tmp.write_text(''.join(json.dumps(r)+'\n' for r in accepted));tmp.replace(HERE/'accepted_decisions.jsonl')
    budget=json.loads(Path(M['budget_file']).read_text())
    status={'status':progress['status'],'run_dir':str(HERE),'stage':json.loads((HERE/'stage_authorization.json').read_text())['stage'],'accepted_decisions':len(accepted),'pending_authorized_decisions':len(missing),'new_attempts':len(budget['reserved_attempts']),'new_remaining':budget['authorized_maximum_attempts']-len(budget['reserved_attempts']),'old_unused_preserved':29,'updated_at':progress['updated_at']}
    statusfile=Path(M['budget_file']).parent/'STATUS.json';tmp=statusfile.with_suffix('.tmp');tmp.write_text(json.dumps(status,indent=2)+'\n');tmp.replace(statusfile)
    print(json.dumps({'accepted':len(accepted),'requested_remaining':len(missing),'excluded':len(progress['excluded_attempts']),'models':progress['models']}),flush=True)
    return accepted,missing

def main():
    limit=int(sys.argv[1]) if len(sys.argv)>1 else len(M["cases"])
    assert 1<=limit<=len(M["cases"])
    for wave in range(3):
        _,missing=checkpoint();tasks=[]
        for c,m in missing:
            if c>limit:continue
            budget=json.loads(Path(M['budget_file']).read_text())
            count=max([r['attempt'] for r in budget['reserved_attempts'] if r['run_id']==M['run_id'] and r['case']==c and r['model']==m],default=0)
            if count<3:tasks.append((c,m,count+1))
        if not tasks:break
        # Fresh process and context per opinion. At most six simultaneous calls; every physical attempt reserved.
        for offset in range(0,len(tasks),6):
            batch=tasks[offset:offset+6]
            with cf.ThreadPoolExecutor(max_workers=6) as pool:
                fs={pool.submit(run_one,*t):t for t in batch}
                for f in cf.as_completed(fs):
                    try:f.result()
                    except Exception as e:
                        with (HERE/'runner_errors.log').open('a') as log:log.write(repr((fs[f],e))+'\n')
            checkpoint()
            audits=json.loads((HERE/'isolation_audit.json').read_text())['audits']
            fatal=[a for a in audits if any(('runtime instruction' in i or 'user text' in i or 'environment wrapper' in i or 'content structure' in i or 'Disallowed tool' in i or 'Session ID reused' in i or 'Wrong model' in i or 'Unplanned model' in i or 'Hash mismatch' in i) for i in a['issues'])]
            if fatal:raise RuntimeError('Isolation failure: stop dispatch and review before any retry')
        checkpoint()
    _,missing=checkpoint();requested=[x for x in missing if x[0]<=limit]
    if requested:raise SystemExit(2)
if __name__=='__main__':main()
