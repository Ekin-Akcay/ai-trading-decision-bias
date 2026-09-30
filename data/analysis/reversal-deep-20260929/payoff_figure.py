from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;R=H.parents[2];s=json.loads((R/'data/sim/reversal-validation280-20260929T194012Z/summary.json').read_text())
curves=[('Earlier short reversal',24/42,.7639769382588106,1.4979701871569715,'#818b91')]
for k,label,color in [('S','New capped short','#b75a20'),('L','New confirmed long','#13796d')]:
 v=s['strategies'][k];curves.append((label,v['gross_win_rate'],v['mean_gross_winner_pct'],-v['mean_gross_loser_pct'],color))
fig,ax=plt.subplots(figsize=(10,5));p=np.linspace(.3,.85,300)
for label,observed,w,l,color in curves:
 y=p*w-(1-p)*l-.2;need=(l+.2)/(w+l);current=observed*w-(1-observed)*l-.2
 ax.plot(p*100,y,color=color,lw=2,label=f'{label}: break-even {need:.1%}');ax.scatter([observed*100],[current],color=color,s=60,zorder=4)
 ax.annotate(f'{observed:.1%} wins\n{current:+.3f}% net',xy=(observed*100,current),xytext=(8,-38 if label=='New capped short' else 14),textcoords='offset points',fontsize=9,color=color)
ax.axhline(0,color='#222',lw=1);ax.set_xlabel('Gross winning-trade rate (%)');ax.set_ylabel('Expected net return per trade (%)');ax.set_title('Win rate must be considered with payoff size and costs');ax.spines[['top','right']].set_visible(False);ax.legend(loc='upper left',fontsize=9);fig.text(.5,.02,'Each line holds that sample’s average winner/loss fixed; it does not predict what changing stops would do. Cost: 20 bps.',ha='center',fontsize=8);fig.tight_layout(rect=[0,.05,1,1]);fig.savefig(H/'payoff_geometry.png',dpi=180);fig.savefig(H/'payoff_geometry.pdf');plt.close(fig)
