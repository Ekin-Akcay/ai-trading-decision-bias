"""Run only the authorized50new cases; durable outputs; audit before scoring."""
from pathlib import Path
import json,math,re,concurrent.futures as cf,sys
from datetime import datetime,timezone
from cli_runner import run_one
from cli_audit import collect_cli
HERE=Path(__file__).resolve().parent;M=json.loads((HERE/'manifest.json').read_text())
def parse(raw):
    try:
        obj=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip()));s=obj['stop_loss_pct'];c=obj['confidence'];reason=obj['reason']
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
    missing=[(c,m) for c in M['authorized_cases'] for m in M['models'] if (c,m) not in keys]
    progress={'status':'decisions_collected' if not missing else 'collecting','accepted':len(accepted),'planned_this_batch':50,'planned_canonical_windows':50,'authorized_case_range':[1,50],'pending_unrequested_case_range':None,'missing_requested_pairs':missing,'models':{m:sum(r['model']==m for r in accepted) for m in M['models']},'attempts':len(records),'excluded_attempts':[a for a in audits if not a['passed']],'updated_at':datetime.now(timezone.utc).isoformat()}
    for name,data in [('progress.json',progress),('isolation_audit.json',{'all_accepted_passed':True,'audits':audits,'accepted':len(accepted),'excluded':sum(not a['passed'] for a in audits)})]:
        tmp=HERE/(name+'.tmp');tmp.write_text(json.dumps(data,indent=2));tmp.replace(HERE/name)
    tmp=HERE/'accepted_decisions.jsonl.tmp';tmp.write_text(''.join(json.dumps(r)+'\n' for r in accepted));tmp.replace(HERE/'accepted_decisions.jsonl')
    print(json.dumps({'accepted':len(accepted),'requested_remaining':len(missing),'excluded':len(progress['excluded_attempts']),'models':progress['models']}),flush=True)
    return accepted,missing

def main():
    limit=int(sys.argv[1]) if len(sys.argv)>1 else 50
    assert 1<=limit<=50
    for wave in range(3):
        _,missing=checkpoint();tasks=[]
        for c,m in missing:
            if c>limit:continue
            count=len(list((HERE/'cli_attempts').glob(f'{m.split("-")[-1]}_{c:03d}_attempt*')))
            if count<3:tasks.append((c,m,count+1))
        if not tasks:break
        # Fresh process, cwd, context, no tool calls, per decision; four requests maximum.
        with cf.ThreadPoolExecutor(max_workers=4) as pool:
            fs={pool.submit(run_one,*t):t for t in tasks};count=0
            for f in cf.as_completed(fs):
                try:f.result()
                except Exception as e:
                    with (HERE/'runner_errors.log').open('a') as log:log.write(repr((fs[f],e))+'\n')
                count+=1
                if count%4==0:checkpoint()
        checkpoint()
    _,missing=checkpoint();requested=[x for x in missing if x[0]<=limit]
    if requested:raise SystemExit(2)
if __name__=='__main__':main()
