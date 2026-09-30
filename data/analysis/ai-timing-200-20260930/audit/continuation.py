"""Reconstruct continuation from independently audited screening economics."""
from pathlib import Path
import argparse
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release',required=True);args=parser.parse_args()
    run=ROOT/'data/sim'/args.release;evidence=run/'screen/evidence'
    manifest=json.loads((evidence/'manifest.json').read_text())
    audit_path=HERE/'screen_replay_audit.json';audit=json.loads(audit_path.read_text())
    assert audit['passed'] and audit['stage']=='screen' and audit['run_id']==args.release
    assert audit['score_release_sha256']==sha(evidence/'score_release.json')
    passing=[d for d in ['up','down'] if audit['directions'][d]['screen_pass']]
    count=60 if len(passing)==2 else 120 if len(passing)==1 else 0
    expected={}
    for direction in passing:
        rows=sorted([r for r in manifest['cases'] if r['stage']=='confirmation' and r['direction']==direction],key=lambda r:int(r['confirmation_rank']))
        assert [int(r['confirmation_rank']) for r in rows]==list(range(1,len(rows)+1))
        assert len(rows)>=count
        expected[direction]=[int(r['case']) for r in rows[:count]]
    ids=sorted(i for values in expected.values() for i in values)
    reported=json.loads((run/'screen/continuation.json').read_text())
    fields={'passing_directions':passing,'cases_per_passing_direction':count,'selected_confirmation_by_direction':expected,'selected_confirmation_case_ids':ids,
        'decision':'continue_fixed_confirmation' if passing else 'stop_preserve_unused_attempts','manifest_sha256':sha(evidence/'manifest.json'),'new_calls_launched_by_scorer':0}
    for key,value in fields.items():assert reported[key]==value,(key,reported[key],value)
    assert len(ids)<=120 and not set(ids)&set(audit['released_cases'])
    result={'passed':True,'run_id':args.release,'screen_native_audit_sha256':sha(audit_path),'confirmation_outcomes_opened':False,'new_calls':0,**fields}
    (HERE/'continuation_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'passing_directions':passing,'confirmation_count':len(ids)},indent=2))

if __name__=='__main__':main()
