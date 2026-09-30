"""Build a local, dependency-free explorer and exportable research figure."""
from pathlib import Path
import json,os,html
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
read=lambda n:json.loads((HERE/(n+'.json')).read_text())
name=lambda m:m.replace('claude-','').replace('gpt-5.6-','').replace('gpt-6-','').replace('-agent','').title()
def make_figures():
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'#faf9f5','axes.facecolor':'#faf9f5','savefig.facecolor':'#faf9f5'})
    fig,axs=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    e=pd.DataFrame(read('ensemble_horizons')); b=pd.DataFrame(read('baselines'))
    for proto,color in [('v1','#648ab3'),('v2','#17765f')]:
        x=e[(e.protocol==proto)&e.horizon_minutes.between(15,105)]
        axs[0,0].plot(x.horizon_minutes,x.accuracy*100,'o-',label=proto.upper()+' majority',color=color)
    x=b[(b.baseline=='ma20')&b.horizon_minutes.between(15,105)]
    axs[0,0].plot(x.horizon_minutes,x.accuracy*100,'--',label='Price vs MA20',color='#a5672c')
    axs[0,0].axhline(50,color='#888',lw=.8);axs[0,0].set(ylim=(30,75),xticks=list(range(15,106,15)),xlabel='Minutes after entry',ylabel='Direction correct (%)',title='A. Early direction does not persist reliably');axs[0,0].legend(fontsize=9)
    beh=pd.DataFrame(read('behavior'));x=beh[beh.protocol=='v2'];labels=[name(m) for m in x.model];yy=np.arange(5)
    axs[0,1].barh(yy-.18,x.ma20_agreement*100,height=.34,label='Follows MA20',color='#17765f');axs[0,1].barh(yy+.18,x.visible_trend_agreement*100,height=.34,label='Follows visible trend',color='#648ab3');axs[0,1].set(yticks=yy,yticklabels=labels,xlim=(0,100),xlabel='Decisions (%)',title='B. Shared indicator-following behavior (v2)');axs[0,1].set_ylim(-.6,5.5);axs[0,1].legend(fontsize=9,loc='upper right')
    c=pd.DataFrame(read('confidence_tests'));c=c[c.protocol=='v2']
    for metric,offset,color,label in [('agrees_ma20',-.18,'#17765f','MA20 alignment'),('correct_105m',.18,'#b9574c','105m correctness')]:
        vals=[c[(c.model==m)&(c.metric==metric)].pearson_r.iloc[0] for m in x.model]
        axs[1,0].barh(yy+offset,vals,height=.34,label=label,color=color)
    axs[1,0].axvline(0,color='#888',lw=.8);axs[1,0].set(yticks=yy,yticklabels=labels,xlim=(-.3,.65),xlabel='Correlation with stated confidence',title='C. Confidence tracks the setup, not proven accuracy');axs[1,0].legend(fontsize=9,loc='lower right')
    z=e[(e.protocol=='v2')&e.horizon_minutes.isin([15,30,45,60,75,90,105])]
    ci=np.array(z.ci_atr.tolist());v=z.mean_atr_all_cases.to_numpy()
    axs[1,1].errorbar(z.horizon_minutes,v,yerr=np.array([v-ci[:,0],ci[:,1]-v]),fmt='o-',capsize=3,color='#17765f');axs[1,1].axhline(0,color='#888',lw=.8);axs[1,1].set(xticks=list(range(15,106,15)),xlabel='Minutes after entry',ylabel='Mean direction-signed move (entry ATR)',title='D. V2 majority: uncertainty includes zero')
    fig.suptitle('Behavioral regularity is clearer than predictive value',fontsize=18,fontweight='bold')
    fig.supxlabel('100 shared SOL windows • descriptive / exploratory • panel D: 95% window-bootstrap intervals',fontsize=10)
    fig.savefig(HERE/'research_overview.png',dpi=170);fig.savefig(HERE/'research_overview.pdf');plt.close(fig)

def main():
    make_figures()
    records=[json.loads(s) for s in (HERE/'decisions_enriched.jsonl').read_text().splitlines()]
    wins=json.loads(pd.read_csv(HERE/'windows.csv').to_json(orient='records'))
    paths=np.load(HERE/'minute_paths.npz');mainkeys=['decision_id','model','model_version','protocol','action','sign','confidence','reason','outcome','minutes_held','stop_pct','tp_pct','source_file','source_line','main','path_15_to_105','first_favorable_close_minutes','crossings_105m','favorable_first_05atr','agrees_ma20','agrees_visible_trend','ts_decided']
    for h in [15,30,45,60,75,90,105,240,1440]:mainkeys += [f'signed_{h}m_pct',f'signed_{h}m_atr',f'mfe_{h}m_pct',f'mae_{h}m_pct',f'fraction_favorable_{h}m']
    for w in wins:
        rr=[r for r in records if r['window_id']==w['window_id']]
        w['image']=os.path.relpath(ROOT/rr[0]['image'],HERE)
        w['path']=np.round(paths[w['window_id']],6).tolist()
        w['decisions']=[{k:r.get(k) for k in mainkeys} for r in rr]
        w['label']=f"Case {int(w['case']):03d}" if w['case'] is not None else 'Pilot '+w['window_id']
    wins.sort(key=lambda w:(w['case'] is None,w['case'] or 0,w['asset'],w['entry_time']))
    packet={'windows':wins,'count':len(records)}
    template=(HERE/'report_template.html').read_text()
    output=template.replace('__DATA__',json.dumps(packet,separators=(',',':'),allow_nan=False).replace('</','<\\/'))
    (HERE/'index.html').write_text(output)
    print(json.dumps({'report':str(HERE/'index.html'),'windows':len(wins),'decisions':len(records),'bytes':len(output)}))
if __name__=='__main__':main()
