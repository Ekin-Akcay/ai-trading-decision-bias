"""Render the independently selected calendar blocks without scoring outcomes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,sys,shutil
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
from nai.sim import build_snapshot,render_chart,sim_prompt,window_id

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert not (HERE/'run.json').exists(), 'Already prepared; do not replace frozen sample'
    plan=json.loads((HERE/'design/fresh_blocks.json').read_text())
    blocks=plan['blocks']
    assets=plan['assets']
    assert len(blocks)*len(assets)<=json.loads((HERE/'snapshot_budget.json').read_text())['planned_valid_decisions']
    protocol=HERE/'VALIDATION_PROTOCOL.md'
    assert protocol.exists()
    prior_manifest=ROOT/'data/sim/rules2to1-openai-20260926T072414Z/manifest.json'
    contract=json.loads(prior_manifest.read_text())['contract']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_id=f'gross-edge-{len(blocks)*len(assets)}-{stamp}'
    run=ROOT/'data/sim'/run_id
    run.mkdir();(run/'cli_attempts').mkdir()
    px={a:pd.read_csv(ROOT/f'data/raw/intraday/{a}_15m.csv.gz',index_col=0,parse_dates=True).sort_index() for a in assets}
    daily={}
    for a in assets:
        x=pd.read_csv(ROOT/f'data/raw/{a}.csv',index_col=0,parse_dates=True).sort_index()
        x['sma50']=x.close.rolling(50,min_periods=50).mean()
        x['sma200']=x.close.rolling(200,min_periods=200).mean()
        daily[a]=x
    cases=[]
    for b,block in enumerate(blocks,1):
        entry=pd.Timestamp(block['entry_time'])
        if entry.tzinfo is not None: entry=entry.tz_convert('UTC').tz_localize(None)
        ts=entry-pd.Timedelta(minutes=15)
        prev_day=entry.normalize()-pd.Timedelta(days=1)
        for a in assets:
            case=len(cases)+1
            snap=build_snapshot(px[a],ts,40,200)
            hist=px[a].loc[:ts].tail(200)
            assert hist.index.equals(pd.date_range(entry-pd.Timedelta(hours=50),periods=200,freq='15min'))
            d=run/'stimuli'/f'case{case:03d}'
            d.mkdir(parents=True)
            prompt=sim_prompt(snap)
            (d/'stats.txt').write_text(prompt)
            (d/'input.txt').write_text(contract+'\n\n'+prompt)
            render_chart(snap,d/'chart.png')
            dr=daily[a].loc[prev_day];br=daily['BTC-USD'].loc[prev_day]
            assert np.isfinite([dr.close,dr.sma50,br.close,br.sma200]).all()
            c={k:snap[k] for k in ['price_real','sigma_vis_pct','sigma_2d_pct','atr14_pct','ret_vis_pct','ma20_now','ma50_now','vol24_ratio']}
            c.update(case=case,block=b,window_id=window_id(a,ts),asset=a,window_end_ts=str(ts),entry_time=str(entry),visible_bars=40,
                     source_prompt=str((d/'stats.txt').relative_to(ROOT)),prompt_file=str((d/'stats.txt').relative_to(ROOT)),chart_file=str((d/'chart.png').relative_to(ROOT)),stimulus_dir=str(d),
                     prompt_sha256=sha(d/'stats.txt'),input_sha256=sha(d/'input.txt'),image_sha256=sha(d/'chart.png'),
                     asset_daily_close=float(dr.close),asset_daily_sma50=float(dr.sma50),btc_daily_close=float(br.close),btc_daily_sma200=float(br.sma200),
                     macro_both_down=bool(dr.close<=dr.sma50 and br.close<=br.sma200),above_both=bool(snap['ma20_now']<=100 and snap['ma50_now']<=100))
            cases.append(c)
        if b%10==0: print(f'Prepared {len(cases)} snapshots / {b} calendar blocks',flush=True)
    files=[protocol,HERE/'design/fresh_blocks.json',prior_manifest,*sorted((ROOT/'data/sim/decisions').glob('*.jsonl')),*sorted((ROOT/'data/sim/reports').glob('*.html')),ROOT/'src/nai/sim.py',ROOT/'src/nai/backtest.py']
    files += [ROOT/f'data/raw/intraday/{a}_{tf}.csv.gz' for a in assets for tf in ['15m','1m']]
    files += [ROOT/f'data/raw/{a}.csv' for a in assets]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in files}
    manifest={'run_id':run_id,'created_at':datetime.now(timezone.utc).isoformat(),'cases':cases,'models':['gpt-5.6-terra'],'reasoning_effort':'medium','contract':contract,'authorized_cases':list(range(1,len(cases)+1)),
              'planned_decisions':len(cases),'max_attempts':3,'protocol_file':str(protocol.relative_to(ROOT)),'protocol_sha256':sha(protocol),'selection_plan_sha256':sha(HERE/'design/fresh_blocks.json'),
              'original_sha256':hashes,'historical_archive_only':True,'evaluation_horizon_minutes':360,'independent_calendar_blocks':len(blocks),'primary_cost_bps':0,'sampling':plan.get('description','See frozen selection plan')}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (run/'window_list.json').write_text(json.dumps(cases,indent=2)+'\n')
    for p in (HERE/'runner_templates').glob('*.py'):shutil.copy2(p,run/p.name)
    (HERE/'run.json').write_text(json.dumps({'run_id':run_id,'run_dir':str(run)},indent=2)+'\n')
    (run/'HANDOFF.md').write_text('# Gross-return fresh validation\n\nPrepared; collection not yet started. One isolated Terra decision per window. Outcomes remain sealed pending complete collection and audit. See immutable validation protocol in the analysis folder.\n')
    print(json.dumps({'run_dir':str(run),'decisions':len(cases),'calendar_blocks':len(blocks),'original_files_hashed':len(hashes)}),flush=True)

if __name__=='__main__':main()
