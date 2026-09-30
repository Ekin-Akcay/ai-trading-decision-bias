"""Generate immutable price/volume-only stimuli for all 100 original windows."""
from pathlib import Path
import json,hashlib,sys,re
from datetime import datetime,timezone
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
from nai.sim import build_snapshot,UP,DOWN
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def chart(s,path):
    n=s['visible_bars'];x=np.arange(n);o,h,l,c=s['ohlc'].T;up=c>=o
    fig,(ax,av)=plt.subplots(2,1,figsize=(max(8,n*.24),5.5),dpi=110,sharex=True,gridspec_kw={'height_ratios':[3,1],'hspace':.06})
    for i in range(n):
        color=UP if up[i] else DOWN
        ax.plot([x[i],x[i]],[l[i],h[i]],color=color,linewidth=1.1,zorder=2)
        ax.add_patch(plt.Rectangle((x[i]-.32,min(o[i],c[i])),.64,max(abs(c[i]-o[i]),1e-4),facecolor=color,edgecolor=color,zorder=3))
    ax.axhline(100,color='#888888',linewidth=.7,linestyle=':',zorder=1);ax.set_ylabel('price (now = 100)',fontsize=9);ax.grid(alpha=.22,linewidth=.5);ax.set_xlim(-.8,n+1.6)
    av.bar(x,s['vol_ratio'],width=.64,color=[UP if u else DOWN for u in up],alpha=.55)
    av.axhline(1,color='#888888',linewidth=.7,linestyle=':');av.set_ylabel('vol ÷ avg',fontsize=9);av.grid(alpha=.22,linewidth=.5)
    ticks=list(range(0,n-2,10))+[n-1];av.set_xticks(ticks);av.set_xticklabels(['now' if t==n-1 else str(t-(n-1)) for t in ticks],fontsize=8)
    for a in (ax,av):
        for side in ('top','right'):a.spines[side].set_visible(False)
        a.tick_params(labelsize=8)
    assert len(ax.lines)==41 # forty wicks + entry reference; no indicator overlays
    assert len(ax.texts)==0
    fig.savefig(path,bbox_inches='tight');plt.close(fig)
def main():
    if (HERE/'openai_run.json').exists():raise SystemExit('Stimuli and run already prepared; preserve them and use the existing manifest.')
    canonical=ROOT/'data/sim/rules2to1/window_list.json';cases=json.loads(canonical.read_text());old=json.loads((ROOT/'data/sim/rules2to1-openai-20260926T072414Z/manifest.json').read_text())
    original={str(p.relative_to(ROOT)):sha(p) for p in [canonical,ROOT/'src/nai/sim.py',ROOT/'src/nai/backtest.py',*sorted((ROOT/'data/sim/decisions').glob('*.jsonl')),*sorted((ROOT/'data/sim/reports').glob('*.html'))]}
    raw=ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz';original[str(raw.relative_to(ROOT))]=sha(raw);p1=ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz';original[str(p1.relative_to(ROOT))]=sha(p1)
    px=pd.read_csv(raw,index_col=0,parse_dates=True);records=[]
    for c in cases:
        folder=HERE/'stimuli'/f"case{c['case']:03d}";folder.mkdir(parents=True,exist_ok=True)
        source=ROOT/c['prompt_file'];original[str(source.relative_to(ROOT))]=sha(source);original[c['chart_file']]=sha(ROOT/c['chart_file'])
        lines=source.read_text().splitlines();removed=[s for s in lines if s.startswith(('Indicators','Volatility','Move over'))];assert len(removed)==3
        text='\n'.join(s for s in lines if s not in removed)
        assert not re.search(r'\bMA\d*\b|moving average|ATR|volatility|std of',text,re.I)
        original_bars=[s for s in lines if re.search(r': O=',s)];new_bars=[s for s in text.splitlines() if re.search(r': O=',s)];assert len(new_bars)==40 and new_bars==original_bars
        snap=build_snapshot(px,pd.Timestamp(c['window_end_ts']),40,200);assert abs(snap['price_real']-c['price_real'])<1e-8
        (folder/'stats.txt').write_text(text);(folder/'input.txt').write_text(old['contract']+'\n\n'+text);chart(snap,folder/'chart.png')
        # Raw anonymous series explicitly stored for independent equality audits; no dates/asset.
        series={'ohlc':snap['ohlc'].tolist(),'volume_ratio':snap['vol_ratio'].tolist()};(folder/'series.json').write_text(json.dumps(series))
        r=dict(c);r.update(source_prompt=str((folder/'stats.txt').relative_to(ROOT)),original_prompt_file=c['prompt_file'],original_chart_file=c['chart_file'],prompt_file=str((folder/'stats.txt').relative_to(ROOT)),chart_file=str((folder/'chart.png').relative_to(ROOT)),stimulus_dir=str(folder),prompt_sha256=sha(folder/'stats.txt'),input_sha256=sha(folder/'input.txt'),image_sha256=sha(folder/'chart.png'),series_sha256=sha(folder/'series.json'))
        records.append(r)
    (HERE/'window_list.json').write_text(json.dumps(records,indent=2));(HERE/'source_preservation.json').write_text(json.dumps(original,indent=2))
    audit={'canonical_count':100,'canonical_order_exact':[(c['case'],c['window_id']) for c in cases]==[(c['case'],c['window_id']) for c in records],'identical_text_ohlcv_rows':4000,'chart_ohlcv_from_original_snapshot':True,'chart_indicators_removed':True,'removed_text_sections':['Indicators (MA20/MA50)','Volatility (sigma/ATR)','Move and aggregate volume summary'],'visible_bars':40,'entry_rebase':100,'volume_normalization':'unchanged: trailing 200-bar average','chart_axis':'price-only autoscale; removing lines can change vertical limits','protocol':'price/volume-only input, not MA-only causal ablation','generated_at':datetime.now(timezone.utc).isoformat()}
    (HERE/'stimulus_audit.json').write_text(json.dumps(audit,indent=2))
    runid='pricevolume-v3-openai-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');run=ROOT/'data/sim'/runid;run.mkdir()
    manifest={'run_id':runid,'created_at':datetime.now(timezone.utc).isoformat(),'cases':records,'models':old['models'],'reasoning_effort':'medium','contract':old['contract'],'protocol_file':str((HERE/'INSTRUCTIONS.md').relative_to(ROOT)),'protocol_sha256':sha(HERE/'INSTRUCTIONS.md'),'canonical_case_count':100,'authorized_cases':list(range(1,21)),'planned_decisions_this_batch':60,'max_attempts':3,'stimulus_audit':str((HERE/'stimulus_audit.json').relative_to(ROOT)),'harness':'fresh Codex exec, attached chart, no tools; same CLI configuration as v2 resumption','comparison_limitations':'Historical v2 controls, not concurrent repeat controls; input removes all supplied indicators/summaries and can change chart y scale.'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2));(HERE/'openai_run.json').write_text(json.dumps({'run_id':runid,'run_dir':str(run)},indent=2));(run/'cli_attempts').mkdir();(run/'HANDOFF.md').write_text('# V3 first 20 — PREPARED\n\n100 canonical windows prepared. Only cases 1–20 authorized in this batch; 60 OpenAI decisions planned. Models: Luna, Terra, Astra. No decisions collected yet.\n')
    print(json.dumps({'run_dir':str(run),'stimuli':100,'batch_decisions':60}))
if __name__=='__main__':main()
