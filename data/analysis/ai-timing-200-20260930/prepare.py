"""Prepare frozen conditional windows; never read post-entry OHLC/returns."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,shutil
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
from nai.sim import build_snapshot,render_chart,sim_prompt,window_id

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not (HERE/'run.json').exists(), 'Already prepared; never overwrite an existing run'
    selection=HERE/'design/fresh_windows.json';plan=json.loads(selection.read_text())
    blocks=plan['cases'];protocol=HERE/'VALIDATION_PROTOCOL.md'
    assert len(blocks) in (180,300)
    prior=ROOT/'data/sim/rules2to1-openai-20260926T072414Z/manifest.json'
    contract=json.loads(prior.read_text())['contract']
    run_id='ai-timing-200-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');run=ROOT/'data/sim'/run_id
    run.mkdir();(run/'cli_attempts').mkdir()
    assets=sorted(set(b['asset'] for b in blocks))
    px={a:pd.read_csv(ROOT/f'data/raw/intraday/{a}_15m.csv.gz',index_col=0,parse_dates=True).sort_index() for a in assets}
    cases=[]
    for b in blocks:
        case=int(b.get('case',b.get('case_id')));assert case==len(cases)+1
        t0=pd.Timestamp(b['t0']);ts=t0-pd.Timedelta(minutes=15)
        if t0.tzinfo is not None:t0=t0.tz_convert('UTC').tz_localize(None);ts=ts.tz_convert('UTC').tz_localize(None)
        a=b['asset'];hist=px[a].loc[:ts].tail(200)
        assert hist.index.equals(pd.date_range(t0-pd.Timedelta(hours=50),periods=200,freq='15min'))
        snap=build_snapshot(px[a],ts,40,200);assert window_id(a,ts)==b['window_id']
        if 'atr14_pct' in b:assert np.isclose(snap['atr14_pct'],b['atr14_pct'],rtol=1e-10,atol=1e-12)
        d=run/'stimuli'/f'case{case:03d}';d.mkdir(parents=True)
        prompt=sim_prompt(snap);(d/'stats.txt').write_text(prompt);(d/'input.txt').write_text(contract+'\n\n'+prompt)
        render_chart(snap,d/'chart.png')
        c=dict(b);c.update({k:snap[k] for k in ['price_real','sigma_vis_pct','sigma_2d_pct','atr14_pct','ret_vis_pct','ma20_now','ma50_now','vol24_ratio']})
        c.update(case=case,window_end_ts=str(ts),t0=str(t0),visible_bars=40,source_prompt=str((d/'stats.txt').relative_to(ROOT)),
                 prompt_file=str((d/'stats.txt').relative_to(ROOT)),chart_file=str((d/'chart.png').relative_to(ROOT)),stimulus_dir=str(d),
                 prompt_sha256=sha(d/'stats.txt'),input_sha256=sha(d/'input.txt'),image_sha256=sha(d/'chart.png'))
        cases.append(c)
        if case%30==0:print(f'Prepared {case}/{len(blocks)} sealed-input snapshots; no outcome scores',flush=True)
    oldfiles=[prior,ROOT/'src/nai/sim.py',ROOT/'src/nai/backtest.py',ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json']
    oldfiles+=sorted((ROOT/'data/sim/decisions').glob('*.jsonl'))+sorted((ROOT/'data/sim/reports').glob('*.html'))
    oldfiles+=[ROOT/f'data/raw/intraday/{a}_{tf}.csv.gz' for a in assets for tf in ['1m','15m']]
    original_hashes={str(p.relative_to(ROOT)):sha(p) for p in oldfiles}
    manifest={'run_id':run_id,'created_at':datetime.now(timezone.utc).isoformat(),'cases':cases,'models':['gpt-5.6-terra'],
              'reasoning_effort':'medium','contract':contract,'runtime_instruction_lock':json.loads((HERE/'design/runtime_instruction_lock.json').read_text()),'planned_valid_decisions':180,'potential_windows':len(cases),
              'budget_file':str(HERE/'snapshot_budget.json'),'protocol_file_absolute':str(protocol),'protocol_sha256':sha(protocol),
              'selection_plan_file_absolute':str(selection),'selection_plan_sha256':sha(selection),'original_sha256':original_hashes,
              'historical_archive_only':True,'entry_delay_minutes':30,'hold_minutes':120,'primary_cost_bps':0,
              'sampling':'Frozen pre-execution quiet-move gates, one global UTC day each, exclusions recorded in selection manifest'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(run/'window_list.json').write_text(json.dumps(cases,indent=2)+'\n')
    screen=[c['case'] for c in cases if c['stage']=='screen'];assert len(screen)==60
    (run/'stage_authorization.json').write_text(json.dumps({'stage':'screen','authorized_cases':screen,'reason':'Frozen 60-case screening batch; no outcomes scored','at':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
    for p in (HERE/'runner_templates').glob('*.py'):shutil.copy2(p,run/p.name)
    (HERE/'run.json').write_text(json.dumps({'run_id':run_id,'run_dir':str(run)},indent=2)+'\n')
    (run/'HANDOFF.md').write_text('# AI timing study\n\nScreening cases authorized; collection has not started. See analysis/ai-timing-200-20260930/VALIDATION_PROTOCOL.md and separate snapshot budget. All 300 potential windows are fixed; only 60 screen and at most120 confirmation decisions may be requested. No post-entry outcomes scored.\n')
    print(json.dumps({'run_id':run_id,'potential_cases':len(cases),'authorized_screen_cases':len(screen),'run_dir':str(run)}),flush=True)
if __name__=='__main__':main()
