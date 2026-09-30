from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib,shutil
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'src'))
from nai.sim import build_snapshot,sim_prompt,window_id
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def chart_pair(snap,full,bare):
    n=snap['visible_bars'];x=np.arange(n);o,h,l,c=snap['ohlc'].T;up=c>=o
    colors=np.where(up,'#26a69a','#ef5350')
    fig,(ax,av)=plt.subplots(2,1,figsize=(max(8.,n*.24),5.5),dpi=110,sharex=True,gridspec_kw={'height_ratios':[3,1],'hspace':.06})
    for i in range(n):
        ax.plot([x[i],x[i]],[l[i],h[i]],color=colors[i],linewidth=1.1,zorder=2)
        ax.add_patch(plt.Rectangle((x[i]-.32,min(o[i],c[i])),.64,max(abs(o[i]-c[i]),1e-4),facecolor=colors[i],edgecolor=colors[i],zorder=3))
    line20,=ax.plot(x,snap['ma20_vis'],color='#1976d2',linewidth=1.4,zorder=4)
    line50,=ax.plot(x,snap['ma50_vis'],color='#f39c12',linewidth=1.4,zorder=4)
    label20=ax.text(x[-1]+.4,snap['ma20_vis'][-1],'MA20',color='#1976d2',fontsize=8,va='center')
    label50=ax.text(x[-1]+.4,snap['ma50_vis'][-1],'MA50',color='#f39c12',fontsize=8,va='center')
    ax.axhline(100,color='#888888',linewidth=.7,linestyle=':',zorder=1);ax.set_ylabel('price (now = 100)',fontsize=9);ax.grid(alpha=.22,linewidth=.5);ax.set_xlim(-.8,n+1.6)
    av.bar(x,snap['vol_ratio'],width=.64,color=colors,alpha=.55);av.axhline(1,color='#888888',linewidth=.7,linestyle=':');av.set_ylabel('vol ÷ avg',fontsize=9);av.grid(alpha=.22,linewidth=.5)
    ticks=list(range(0,n-2,5 if n<=30 else 10))+[n-1];av.set_xticks(ticks);av.set_xticklabels(['now' if v==n-1 else str(v-(n-1)) for v in ticks],fontsize=8)
    for a in (ax,av):
        for side in ('top','right'):a.spines[side].set_visible(False)
        a.tick_params(labelsize=8)
    fig.canvas.draw()
    fixed_bbox=fig.get_tightbbox(fig.canvas.get_renderer()).padded(.1)
    fig.savefig(full,bbox_inches=fixed_bbox,pad_inches=0)
    limits=ax.get_ylim()
    for artist in (line20,line50,label20,label50):artist.remove()
    ax.set_ylim(limits) # preserve chart scaling, including any MA-implied extent
    fig.savefig(bare,bbox_inches=fixed_bbox,pad_inches=0);plt.close(fig)

def main():
    assert not (HERE/'run.json').exists()
    plan=json.loads((HERE/'design/fresh_blocks.json').read_text());assert len(plan['blocks'])==90
    protocol=HERE/'PROTOCOL.md';contract=json.loads((ROOT/'data/sim/rules2to1-openai-20260926T072414Z/manifest.json').read_text())['contract']
    run_id='ma-ablation-sol90-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');run=ROOT/'data/sim'/run_id;run.mkdir();(run/'cli_attempts').mkdir()
    px=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',index_col=0,parse_dates=True).sort_index()
    sol=pd.read_csv(ROOT/'data/raw/SOL-USD.csv',index_col=0,parse_dates=True).sort_index();sol['sma']=sol.close.rolling(50).mean()
    btc=pd.read_csv(ROOT/'data/raw/BTC-USD.csv',index_col=0,parse_dates=True).sort_index();btc['sma']=btc.close.rolling(200).mean()
    rng=np.random.default_rng(2026092996);cases=[];pairs=[]
    for b,block in enumerate(plan['blocks'],1):
        entry=pd.Timestamp(block['entry_time']).tz_convert('UTC').tz_localize(None);ts=entry-pd.Timedelta(minutes=15)
        snap=build_snapshot(px,ts,40,200);pair=run/'paired_stimuli'/f'window{b:03d}';pair.mkdir(parents=True)
        chart_pair(snap,pair/'full_MA.png',pair/'no_MA.png')
        full=sim_prompt(snap);lines=full.splitlines();removed=[x for x in lines if x.startswith('Indicators (')];assert len(removed)==1
        bare='\n'.join(x for x in lines if not x.startswith('Indicators ('))
        assert 'MA20' not in bare and 'MA50' not in bare
        sd=sol.loc[entry.normalize()-pd.Timedelta(days=1)];bd=btc.loc[entry.normalize()-pd.Timedelta(days=1)]
        assert sd.close<=sd.sma and bd.close<=bd.sma
        order=rng.permutation(['MA_A','MA_B','NO_MA']).tolist()
        for arm in order:
            case=len(cases)+1;folder=run/'stimuli'/f'case{case:03d}';folder.mkdir(parents=True)
            text=bare if arm=='NO_MA' else full
            (folder/'stats.txt').write_text(text);(folder/'input.txt').write_text(contract+'\n\n'+text)
            shutil.copyfile(pair/('no_MA.png' if arm=='NO_MA' else 'full_MA.png'),folder/'chart.png')
            c={k:snap[k] for k in ['price_real','sigma_vis_pct','sigma_2d_pct','atr14_pct','ret_vis_pct','ma20_now','ma50_now','vol24_ratio']}
            c.update(case=case,block=b,arm=arm,window_id=window_id('SOL-USD',ts),asset='SOL-USD',window_end_ts=str(ts),entry_time=str(entry),visible_bars=40,
                     source_prompt=str((folder/'stats.txt').relative_to(ROOT)),prompt_file=str((folder/'stats.txt').relative_to(ROOT)),chart_file=str((folder/'chart.png').relative_to(ROOT)),stimulus_dir=str(folder),
                     prompt_sha256=sha(folder/'stats.txt'),input_sha256=sha(folder/'input.txt'),image_sha256=sha(folder/'chart.png'),
                     asset_daily_close=float(sd.close),asset_daily_sma50=float(sd.sma),btc_daily_close=float(bd.close),btc_daily_sma200=float(bd.sma),macro_both_down=True)
            cases.append(c)
        base=[c for c in cases[-3:] if c['arm']!='NO_MA'];assert base[0]['input_sha256']==base[1]['input_sha256'] and base[0]['image_sha256']==base[1]['image_sha256']
        pairs.append({'block':b,'arm_order':order,'removed_text':removed[0],'axis_limits_preserved':True,'MA_repeats_byte_identical':True})
        if b%10==0:print(f'Prepared {b} windows, {len(cases)} isolated inputs',flush=True)
    files=[protocol,HERE/'design/fresh_blocks.json',ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',ROOT/'data/raw/SOL-USD.csv',ROOT/'data/raw/BTC-USD.csv',ROOT/'src/nai/sim.py',ROOT/'src/nai/backtest.py']
    files+=sorted((ROOT/'data/sim/decisions').glob('*.jsonl'));files+=sorted((ROOT/'data/sim/reports').glob('*.html'))
    manifest={'run_id':run_id,'created_at':datetime.now(timezone.utc).isoformat(),'cases':cases,'models':['gpt-5.6-terra'],'reasoning_effort':'medium','contract':contract,
              'authorized_cases':list(range(1,271)),'planned_decisions':270,'unique_windows':90,'max_attempts':3,'protocol_file':str(protocol.relative_to(ROOT)),
              'protocol_sha256':sha(protocol),'original_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},'primary_cost_bps':0,'evaluation_horizon_minutes':360,
              'sample_seed':2026092995,'arm_order_seed':2026092996,'arms':['MA_A','MA_B','NO_MA'],'primary_profit_arm':'MA_A','same_model_all_arms':True}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(run/'window_list.json').write_text(json.dumps(cases,indent=2)+'\n');(run/'paired_stimulus_audit.json').write_text(json.dumps(pairs,indent=2)+'\n')
    for p in (HERE.parent/'runner_templates').glob('*.py'):shutil.copy2(p,run/p.name)
    runner=run/'cli_runner.py';source=runner.read_text().replace("v2 full MA-present input; uninformed of reversal evaluation","assigned MA or MA-removed input; uninformed of reversal evaluation")
    runner.write_text(source)
    (run/'HANDOFF.md').write_text('# Paired MA study — prepared\n\n270 isolated calls planned;90 fresh SOL windows. Forward outcomes sealed. MA_A is the fixed profit primary; MA_B is a repeat control; NO_MA changes only explicit MA information.\n')
    (HERE/'run.json').write_text(json.dumps({'run_id':run_id,'run_dir':str(run)},indent=2)+'\n')
    print(json.dumps({'run_dir':str(run),'unique_windows':90,'planned_calls':270}),flush=True)

if __name__=='__main__':main()
