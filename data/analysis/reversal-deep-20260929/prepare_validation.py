from pathlib import Path
from datetime import datetime,timezone
import json,sys,hashlib
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
from nai.sim import build_snapshot,render_chart,sim_prompt,window_id
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if (HERE/'run.json').exists():raise SystemExit('Run already frozen; use existing manifest.')
    old=json.loads((ROOT/'data/sim/rules2to1-openai-20260926T072414Z/manifest.json').read_text())
    prior=[];hashes={}
    for p in sorted((ROOT/'data/sim/decisions').glob('*.jsonl')):
        hashes[str(p.relative_to(ROOT))]=sha(p)
        for s in p.read_text().splitlines():
            if not s.strip():continue
            r=json.loads(s)
            if r.get('asset')=='SOL-USD':prior.append(pd.Timestamp(r['window_end_ts'])+pd.Timedelta(minutes=15))
    prior=sorted(set(prior));before=[*sorted((ROOT/'data/sim/reports').glob('*.html')),ROOT/'src/nai/sim.py',ROOT/'src/nai/backtest.py',ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz']
    hashes.update({str(p.relative_to(ROOT)):sha(p) for p in before})
    px=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',index_col=0,parse_dates=True).sort_index()
    minute=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index()
    assert px.index.is_unique and minute.index.is_unique
    ma20=px.close.rolling(20).mean();ma50=px.close.rolling(50).mean()
    eligible=np.arange(200,len(px))
    rng=np.random.default_rng(20260929);ordered=rng.permutation(eligible)
    selected=[];times=[];rejected={'prior_overlap':0,'new_overlap':0,'coverage':0}
    # Bad minute-count prefix only checks data coverage, not subsequent returns.
    bad=(minute[['open','high','low','close']].isna().any(axis=1).to_numpy());prefix=np.r_[0,np.cumsum(bad)]
    dif=np.r_[False,np.diff(minute.index.as_unit("ns").asi8)!=60*10**9];gap=np.r_[0,np.cumsum(dif)]
    for i in ordered:
        ts=px.index[i];entry=ts+pd.Timedelta(minutes=15)
        if any(-74*3600<(entry-t).total_seconds()<122*3600 for t in prior):rejected['prior_overlap']+=1;continue
        if any(abs((entry-t).total_seconds())<74*3600 for t in times):rejected['new_overlap']+=1;continue
        e=int(minute.index.searchsorted(entry));end=e+1440
        okay=e>0 and end<=len(minute) and minute.index[e]==entry and minute.index[e-1]==entry-pd.Timedelta(minutes=1)
        okay=okay and prefix[end]-prefix[e-1]==0 and gap[end]-gap[e]==0 and px.index[i-199:i+1].equals(pd.date_range(ts-pd.Timedelta(minutes=199*15),periods=200,freq='15min'))
        if not okay:rejected['coverage']+=1;continue
        assert abs(float(minute.close.iloc[e-1])-float(px.close.iloc[i]))<1e-8
        selected.append(int(i));times.append(entry)
        if len(selected)==280:break
    assert len(selected)==280, (len(selected),rejected)
    run_id='reversal-validation280-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');run=ROOT/'data/sim'/run_id;run.mkdir();(run/'cli_attempts').mkdir();cases=[]
    for case,i in enumerate(selected,1):
        ts=px.index[i];snap=build_snapshot(px,ts,40,200)
        folder=run/'stimuli'/f'case{case:03d}';folder.mkdir(parents=True);prompt=sim_prompt(snap)
        (folder/'stats.txt').write_text(prompt);(folder/'input.txt').write_text(old['contract']+'\n\n'+prompt);render_chart(snap,folder/'chart.png')
        c={k:snap[k] for k in ['price_real','sigma_vis_pct','sigma_2d_pct','atr14_pct','ret_vis_pct','ma20_now','ma50_now','vol24_ratio']}
        c.update(case=case,window_id=window_id('SOL-USD',ts),asset='SOL-USD',window_end_ts=str(ts),entry_time=str(ts+pd.Timedelta(minutes=15)),visible_bars=40,source_prompt=str((folder/'stats.txt').relative_to(ROOT)),prompt_file=str((folder/'stats.txt').relative_to(ROOT)),chart_file=str((folder/'chart.png').relative_to(ROOT)),stimulus_dir=str(folder),prompt_sha256=sha(folder/'stats.txt'),input_sha256=sha(folder/'input.txt'),image_sha256=sha(folder/'chart.png'))
        cases.append(c)
        if case%20==0:print('Prepared',case,'of280',flush=True)
    manifest={'run_id':run_id,'created_at':datetime.now(timezone.utc).isoformat(),'cases':cases,'models':['gpt-5.6-terra'],'reasoning_effort':'medium','contract':old['contract'],'authorized_cases':list(range(1,281)),'planned_decisions':280,'max_attempts':3,'protocol_file':str((HERE/'VALIDATION_PROTOCOL.md').relative_to(ROOT)),'protocol_sha256':sha(HERE/'VALIDATION_PROTOCOL.md'),'seed':20260929,'sampling_condition':'all MA regimes; >=74h new/new, asymmetric122h after/74h beforeold separation; no outcome selection','prior_SOL_entry_times':[str(x) for x in prior],'original_sha256':hashes,'selection':{'candidate_bars':len(eligible),'rejections_before280':rejected,'earliest_selected_entry':str(min(times)),'latest_selected_entry':str(max(times))},'historical_archive_only':True}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2));(run/'window_list.json').write_text(json.dumps(cases,indent=2));(HERE/'run.json').write_text(json.dumps({'run_id':run_id,'run_dir':str(run)},indent=2))
    (run/'HANDOFF.md').write_text('# Terra reversal test — PREPARED\n\n280 random new eligible windows frozen; zero decisions collected. One Terra call per window. See locked two-finalist validation protocol. Same v2 MA-present input. Model not informed of hypotheses.\n')
    print(json.dumps({'run_dir':str(run),'sampled':280,'prior_SOL_windows':len(prior),'selection':manifest['selection']}),flush=True)
if __name__=='__main__':main()
