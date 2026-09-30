from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
s=json.loads((HERE/'summary.json').read_text())
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'#f7f7f2','axes.facecolor':'#f7f7f2','savefig.facecolor':'#f7f7f2'})
fig,axs=plt.subplots(1,3,figsize=(12,4.5),layout='constrained')
for ax,m in zip(axs,s['models']):
    for v,style,color,label in [('v2','o--','#8d9e9b','v2 historical'),('v3','o-','#17765f','v3 price/volume')]:
        ax.plot([15,30,105],[100*m[v][f'accuracy_{h}m'] for h in [15,30,105]],style,color=color,label=label)
    ax.axhline(50,color='#bfc5bb',lw=.8);ax.set(title=m['model'].replace('gpt-5.6-','').replace('gpt-6-','').replace('-agent','').title()+f" · {m['direction_changes']}/20 direction changes",xlabel='Minutes after entry',xticks=[15,30,105],ylim=(25,80),ylabel='Direction correct (%)')
    ax.legend(fontsize=8,loc='upper right')
fig.suptitle('V3 pilot: most directions persist; Terra improves early',fontsize=16,fontweight='bold')
fig.supxlabel('20 shared windows • historical controls • no model/horizon paired-return test survives multiple-test correction',fontsize=9)
fig.savefig(HERE/'v3_overview.png',dpi=170);fig.savefig(HERE/'v3_overview.pdf');plt.close(fig)
