from pathlib import Path
import json,html
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
s=pd.read_csv(HERE/'policy_summary.csv');c=pd.read_csv(HERE/'paired_vs_original.csv');b=pd.read_csv(HERE/'benchmark_contrasts.csv');halves=pd.read_csv(HERE/'half_summary.csv');sessions=pd.read_csv(HERE/'utc_session_summary.csv');p=pd.read_csv(HERE/'per_trade_policies.csv');audit=json.loads((HERE/'audit.json').read_text());pooled=s[s.group=='pooled'].set_index('policy');H=[5,15,30,60,105,240];scales=[1,.75,.5,.25]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#344358','text.color':'#172b41','axes.edgecolor':'#aab7c4','figure.facecolor':'#f5f7fa','axes.facecolor':'white','savefig.facecolor':'#f5f7fa'})
fig,axs=plt.subplots(2,2,figsize=(14,10),layout='constrained')
a=axs[0,0];z=pooled.loc[[f'time_{h}m' for h in H]];idx=np.arange(len(H));a.bar(idx-.17,z.gross_mean_pct,.34,label='Gross',color='#348a95');a.bar(idx+.17,z.net_mean_pct,.34,label='Net after 20 bps',color='#d16b51');a.axhline(0,c='#8795a4',lw=.8);a.set_xticks(idx,[f'{h} min' for h in H]);a.set_title('Time exits: small gross moves, fixed cost');a.set_ylabel('Mean return per decision (%)');a.legend(frameon=False,fontsize=9)
a=axs[0,1];z=pooled.loc[[f'bracket_{q:g}' for q in scales]];ix=np.arange(4);a.errorbar(ix,z.net_mean_pct,yerr=[z.net_mean_pct-z.net_ci_low,z.net_ci_high-z.net_mean_pct],fmt='o-',c='#6153a4',capsize=4);a.axhline(0,c='#8795a4',lw=.8);a.set_xticks(ix,['Original','75% width','50% width','25% width']);a.set_ylabel('Mean net return (%)');a.set_title('Narrower brackets do not improve mean return');a.text(.40,.95,'95% window bootstrap intervals\n25% excludes 2 ambiguous rows; full bounds in report',transform=a.transAxes,fontsize=8,color='#56687c',va='top');
a=axs[1,0];z=pooled.loc[[f'bracket_{q:g}' for q in scales]];a.bar(ix,z.median_minutes,color='#348a95');a.set_xticks(ix,['Original','75%','50%','25%']);a.set_title('Median holding time falls sharply');a.set_ylabel('Minutes among active decisions');
for j,v in enumerate(z.median_minutes):a.text(j,v+2,f'{v:g}',ha='center')
a=axs[1,1];keys=['bracket_1','time_15m','time_30m','time_105m','bracket_0.5','bracket_0.25'];pv=s[(s.group!='pooled') & s.policy.isin(keys)].pivot(index='group',columns='policy',values='net_mean_pct').reindex(columns=keys);im=a.imshow(pv,vmin=-.4,vmax=.4,cmap='RdBu',aspect='auto');a.set_yticks(np.arange(len(pv)),[x.replace('claude-','').replace('gpt-5.6-','').replace('gpt-6-','').replace('-agent','') for x in pv.index],fontsize=8);a.set_xticks(np.arange(6),['Original','15m','30m','105m','50%','25%'],fontsize=8);a.set_title('Every model/protocol: net return (%)');
for i in range(len(pv)):
 for j in range(6):a.text(j,i,f'{pv.iloc[i,j]:+.2f}',ha='center',va='center',fontsize=8,color='white' if abs(pv.iloc[i,j])>.23 else '#172b41')
fig.colorbar(im,ax=a,shrink=.7,label='Net return (%)');fig.suptitle('Exit-policy study · 100 market windows, 1,000 decisions',fontsize=17,fontweight='bold');fig.savefig(HERE/'exit_policy_overview.png',dpi=170);fig.savefig(HERE/'exit_policy_overview.pdf');plt.close(fig)
# Descriptive costs: break-even cost is pre-cost mean per active decision.
be=[]
for policy,g in p.groupby('policy'):
 active=g[g.effective_sign!=0];be.append({'policy':policy,'active_rows':len(active),'ambiguous':int((g.outcome=='ambiguous').sum()),'gross_mean_active_pct':active.gross_pct.mean(),'break_even_round_trip_bps_excluding_ambiguous':active.gross_pct.mean()*100})
pd.DataFrame(be).to_csv(HERE/'break_even_costs.csv',index=False)
notes='''# Exit-policy results — exploratory, 2026-09-29

## What changed when we exited earlier or shrank the brackets?

Neither change produced a credible net improvement on these existing windows. Smaller percentage returns partly reflect mechanically smaller risk width; they do not alone establish weaker directional expectancy. The risk-normalized appendix below separates gross expectancy from fee burden. The clearest pattern is mechanical: shrinking both levels makes trades resolve much faster while their small gross movement increasingly struggles to cover the same 20-basis-point cost. This is evidence about this sample, not proof that every short-duration strategy is unprofitable.

All results below average decisions within each market window, then average the 100 windows. The same ten decisions share each market path; they are not 1,000 independent observations. The main grid includes both v1 and v2 and all five models. Original flat decisions remain zero-return and zero-cost. Figures are percentage points of entry, without leverage or position sizing.

| Policy | Gross mean | Net mean | Median holding time |
|---|---:|---:|---:|
| Original brackets | +0.114% | −0.081% | 96 min |
| Exit after 15 min / 1 candle | +0.047% | −0.148% | 15 min |
| Exit after 30 min / 2 candles | +0.043% | −0.152% | 30 min |
| Exit after 105 min / 7 candles | +0.015% | −0.180% | 105 min |
| Both brackets at 75% width | +0.054% | −0.141% | 50 min |
| Both brackets at 50% width | +0.039% | −0.156% | 20 min |
| Both brackets at 25% width | +0.017% | approximately −0.177% | 6 min |

The 25%-width row excludes two ambiguous outcomes from its displayed gross mean; assigning each ambiguous trade to its stop or target puts the mean net result across all 1,000 rows between −0.1776% and −0.1764%. The precise exclusion-only mean is −0.1777%; because exclusions change within-window weights, it need not lie between those all-row bounds.

The six primary paired changes have negative observed mean differences versus original brackets, but their 95% difference intervals all include zero. Each has BH-adjusted q = 0.543 in the six-test primary family. Thus we have not established that modifying the policy helps, or a statistically decisive ranking between them. Negative net point estimates are not the same claim as statistically established negative expected returns.

## Costs are larger than the movement captured

For active trades, the gross mean at 15 minutes supports only about **4.85 bps** of break-even round-trip cost; at 30 minutes, **4.45 bps**; at 105 minutes, **1.54 bps**. The assumed cost is **20 bps**. These are descriptive break-even calculations, not revised fee assumptions or validated edges at lower fees. Original brackets support about **11.70 bps** in this sample. Fee realism matters, but lowering a backtest's fee assumption after seeing results does not establish a strategy.

Original target-hit frequency is 390/975 = 40.0% of active trades. It becomes 38.7%, 40.2% and 39.3% at 75%, 50% and 25% width respectively (25% excludes two ambiguous trades from the denominator). Smaller geometry changes speed far more clearly than success frequency. These pooled hit rates combine v1's variable reward/risk and v2's fixed 2:1, so use the per-model/protocol table for geometry-specific interpretation.

## What about combining time exits with narrow brackets, or reversing direction?

All twelve frozen scale-by-time combinations (four scales × 15/30/105 minutes) remain negative after the same costs. None has a significant paired improvement over the original. All six reversed-direction time policies also have negative pooled net means. Reversing direction does not remove the cost burden.

An always-short benchmark at 105 minutes has a positive point estimate, +0.063% net, but a wide 95% interval [−0.191%, +0.329%]. Its improvement over the AI time exit is +0.243 percentage points, with interval [−0.051%, +0.556%] and adjusted q = 0.967 across the 24 benchmark contrasts. This is a warning to control for the underlying sample's downward drift, not a confirmed always-short strategy. MA20 and visible-momentum benchmarks, reversal, every horizon and every combined policy remain visible in the full tables.

## Stability and sessions

Original brackets averaged +0.042% net in the chronologically earlier 50 windows and −0.204% in the later 50. The primary 15/30/105-minute exits and 50%/25% brackets were negative in both halves. The earlier/later split is a sensitivity summary, not a held-out test: these windows were already studied.

Entry times are also grouped into four fixed six-hour UTC sessions. Those small groups are descriptive and unadjusted; the report lists every session/policy cell. They do not define a time-of-day trading rule. No best-session filter has been selected.

## How this relates to the v3 MA-removal experiment

Do not change the v3 prompt or choose an exit using these outcomes while v3 is collecting. V3 keeps only the raw 40-candle OHLCV chart and data: it removes MA lines/values, ATR/sigma, derived movement and aggregate volume summaries. This is a broader indicator-removal experiment, not an MA-only causal test. The v2 controls are historical, not concurrent. Apply the same frozen 15/30/105-minute evaluation to both versions once outputs exist. Compare paired direction changes, confidence and uncensored paths; keep bracket variants secondary. Any chosen duration or reversal rule requires future windows untouched by this exploration.

## Verification and limits

* Reused the unmodified `nai.backtest._scan_bracket` engine: realistic gap-open fills and ambiguous simultaneous touches.
* **All 1,000 original outcomes, holding times, gross returns and net returns reproduced exactly** to numerical tolerance (4,000 checks).
* **All 100 windows have complete native one-minute OHLC through 72 hours** after entry, without missing-minute shifts.
* Evaluated **46 policies × 1,000 decisions = 46,000 policy rows**; 25 flats remain flat in all paired policies. Momentum abstains on one additional zero-input window; its paired contrast excludes that window from both sides. Original scale-1 results contain zero ambiguities. Two distinct decisions become ambiguous at 25% width; they recur in that width's capped variants.
* Window bootstrap: 10,000 resamples. Primary and secondary tests use separate prespecified BH families. Temporal-cluster sensitivity combines neighboring events at most 72 hours apart into 92 groups; its intervals also include zero for every primary difference.
* The five models and two protocols are correlated evaluations of the same 100 SOL windows. Their repetitions do not broaden market coverage. Most resumed v2 OpenAI calls changed collection harness, which limits clean protocol attribution.
* Minute OHLC cannot order two touches in the same minute. Paired tests exclude ambiguous pairs; full stop-first/target-first bounds are provided, without claiming either order.
* Results are per-decision means, not portfolio returns. No capital constraints, funding, extra slippage, market impact or sizing optimization are modeled. No result is an independent confirmation or out-of-sample strategy validation.
* Input and source hashes were checked after analysis; original files remain unchanged.

## Files

- `index.html`: standalone local report and complete grouped tables.
- `per_trade_policies.csv`: all 46,000 individual policy outcomes, original comparison and ambiguity bounds.
- `policy_summary.csv`: all pooled and model/protocol policy cells with window-bootstrap intervals.
- `paired_vs_original.csv`: every primary/secondary paired test, ambiguity bounds and temporal-group sensitivity.
- `benchmark_contrasts.csv`: all baseline/reversal comparisons.
- `half_summary.csv`, `utc_session_summary.csv`, `break_even_costs.csv`: descriptive diagnostics.
- `PLAN.md`, `run.py`, `build_report.py`, `audit.json`, `engine_audit.json`: frozen plan, reproducible computation and audit.
'''
appendix=pd.read_csv(HERE/'posthoc_regime_direction.csv')
notes+='''
## Post-hoc appendix: regime and original direction

This appendix was requested after the pooled results were available. All pre-entry MA regimes × original action cells are reported, for all seven primary/reference policies; no significance tests or selected filter are claimed. Flat rows are kept visible. Means first average the available decisions within each window and then average windows. Long and short strata can cover different overlapping sets of windows, so their difference is not a paired causal comparison.

The 456 original **short decisions below both MAs** cover all 50 below-both windows. Their equal-window gross/net averages are **+0.201%/+0.001% at 15 minutes**, **+0.197%/−0.003% at 30 minutes**, and **+0.258%/+0.058% at 105 minutes**. Because every one of those 50 windows has a short decision, the pure-time result is exactly what simply shorting every below-both window would produce. It does not establish an AI contribution.

The earlier **68%** first-candle directional accuracy refers to **34 of 50 v2 majority decisions/windows**, not every model row. In this appendix, 314/456 below-both short model decisions have positive gross 15-minute movement (68.9%); 220/456 do at 105 minutes (48.2%). Those counts weight windows according to how many models shorted, so they are different estimands. Accuracy can fall while mean return rises because movement sizes also differ.

The 243 **long decisions above both MAs** cover 29 windows. Equal-window gross averages are **−0.128%, −0.086% and −0.386%** at 15, 30 and 105 minutes; net averages are **−0.328%, −0.286% and −0.586%**. This is a descriptive continuation-failure pattern worth retaining for fresh-window evaluation, not a validated filter or a reason to select a reversal policy now.

See `posthoc_regime_direction.csv` for every pooled/v1/v2 cell and its decision/window counts and ambiguity bounds. Small countertrend and mixed-regime cells are included rather than hidden.
'''
risk=pd.read_csv(HERE/'posthoc_risk_normalization.csv')
notes+='''
## Post-hoc risk normalization: smaller width is not automatically weaker direction

This descriptive diagnostic was added after inspecting the percentage-return results. One R is the trade's **scaled stop distance**: gross R = gross return percent / (original stop fraction × scale × 100), with net R defined the same way. The table averages active, unambiguous decision rows; flats and ambiguous rows are excluded. It is not an executable position-sizing or leverage recommendation. No new significance tests are performed.

| Protocol | Width scale | Known / active | Ambiguous | Target hits | Gross R | Fee R | Net R |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | 1.00 | 475 / 475 | 0 | 42.74% | +0.082 | 0.234 | −0.152 |
| v1 | 0.75 | 475 / 475 | 0 | 42.74% | +0.097 | 0.312 | −0.216 |
| v1 | 0.50 | 475 / 475 | 0 | 42.95% | +0.099 | 0.469 | −0.370 |
| v1 | 0.25 | 474 / 475 | 1 | 42.83% | +0.105 | 0.937 | −0.832 |
| v2 | 1.00 | 500 / 500 | 0 | 37.40% | +0.122 | 0.246 | −0.124 |
| v2 | 0.75 | 500 / 500 | 0 | 34.80% | +0.044 | 0.327 | −0.283 |
| v2 | 0.50 | 500 / 500 | 0 | 37.60% | +0.128 | 0.491 | −0.363 |
| v2 | 0.25 | 499 / 500 | 1 | 35.87% | +0.076 | 0.982 | −0.906 |

**The half-width v2 gross expectancy is essentially unchanged in the observed sample: +0.128 R versus +0.122 R originally.** The quarter-width value is +0.076 R; the pattern across widths is not monotonic. Meanwhile fees rise from 0.246 R to 0.491 R at half width and 0.982 R at quarter width. V1 gross expectancy also stays in a narrow +0.082 to +0.105 R range. Therefore falling percentage returns should not be presented as proof of weaker directional expectancy; shrinking risk distance mechanically reduces the percentage scale while magnifying fixed fees in R.

V1 has variable target/stop ratios, so its hit rate cannot be interpreted using v2's fixed 2:1 payoff assumption. Exact gap-open fills can produce small differences from idealized +2 R/−1 R payoffs in v2. Counts are correlated decisions on the same windows, not independent samples. `posthoc_risk_normalization.csv` and `.json` include all four scales, ambiguity counts and supplementary equal-window means.
'''
(HERE/'FINDINGS.md').write_text(notes)
def table(df):
 t=df.copy()
 for col in t.select_dtypes(include='number'):t[col]=t[col].map(lambda v:'' if pd.isna(v) else f'{v:.4f}' if isinstance(v,float) else str(v))
 return t.to_html(index=False,classes='data',border=0,escape=True)
primary=pooled.loc[['bracket_1','time_15m','time_30m','time_105m','bracket_0.75','bracket_0.5','bracket_0.25']].reset_index()[['policy','gross_mean_pct','net_mean_pct','net_ci_low','net_ci_high','ambiguous','median_minutes']]
summarycols=['group','policy','gross_mean_pct','net_mean_pct','net_ci_low','net_ci_high','net_all_lower_pct','net_all_upper_pct','active','ambiguous','median_minutes']
report='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI trade exit-policy study</title><style>
:root{font:16px/1.6 system-ui,sans-serif;color:#172b41;background:#f4f7fa}body{max-width:1380px;margin:auto;padding:32px}h1{font-size:clamp(28px,4vw,48px);line-height:1.15;max-width:1000px}h2{font-size:25px;margin-top:38px}h3{font-size:18px}p{max-width:1000px}.eyebrow{font-size:12px;letter-spacing:.14em;color:#536a83;text-transform:uppercase}.lead{font-size:21px;max-width:1040px}.muted,small{color:#536a83}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px}.card{background:white;border:1px solid #dae3eb;padding:22px;border-radius:10px}.big{font-size:30px;font-weight:700;display:block}.callout{border-left:4px solid #348a95;background:#e6f1f3;padding:16px 22px}.warning{border-left-color:#d16b51;background:#f8eeeb}.scroll{overflow:auto;background:white;border:1px solid #d8e1e9;border-radius:8px;max-height:670px}table{border-collapse:collapse;font-size:13px;white-space:nowrap;width:100%}th{position:sticky;top:0;background:#eaf0f6;text-align:left;font-weight:600;padding:11px}td{padding:9px 11px;border-top:1px solid #e6ebf0}tr:hover td{background:#f1f6fa}img{width:100%;height:auto;border-radius:12px;border:1px solid #dbe4ec}details{margin:18px 0}summary{cursor:pointer;font-weight:650;padding:12px;background:#eaf0f6;border-radius:6px}a{color:#17677b}code{background:#e7edf3;padding:2px 5px}input,select{font:inherit;padding:9px;border:1px solid #aebdcb;border-radius:5px;margin-right:10px;margin-bottom:12px}footer{margin-top:50px;font-size:13px;color:#536a83;border-top:1px solid #d7e0e8;padding-top:20px}li{margin:7px 0}
</style><div class="eyebrow">Retrospective research · 29 September 2026 · exploratory</div><h1>Earlier exits and smaller brackets: faster trades, insufficient gross movement</h1><p class="lead">Neither modification establishes an improvement on these 100 windows. Shortening the trade reduces exposure, but the average movement captured is small relative to the unchanged 20-basis-point round-trip cost.</p>
<div class="cards"><div class="card"><span class="big">100</span>distinct market windows</div><div class="card"><span class="big">1,000</span>AI decisions · five models × two protocols</div><div class="card"><span class="big">46,000</span>individual policy outcomes</div><div class="card"><span class="big">4,000 / 4,000</span>original-engine reproduction checks</div></div>
<p><a href="FINDINGS.md">Detailed findings</a> · <a href="PLAN.md">Frozen analysis plan</a> · <a href="per_trade_policies.csv">All individual policy outcomes (CSV)</a> · <a href="audit.json">Audit</a></p><img src="exit_policy_overview.png" alt="Four charts showing time-exit gross and net returns, bracket-width return intervals, shorter holding times, and negative model/protocol return cells"><p class="muted">All return figures are percent of entry. Point estimates average decisions within each window, then average windows. Intervals resample windows, not individual AI decisions. They are pointwise exploratory intervals.</p>
<h2>Primary policies</h2><div class="scroll">PRIMARY</div><p>Each primary change has a negative observed difference versus the original, but all paired 95% intervals include zero. All six primary adjusted p-values are <strong>q = 0.543</strong>. This does not establish a reliable ranking between policies.</p><div class="callout"><strong>The clearest pattern is duration.</strong> Scaling both levels to 75%, 50% and 25% reduces median holding time from 96 minutes to 50, 20 and 6 minutes. Target-hit frequency stays near 39–40%. Narrower levels change speed more clearly than success frequency.</div>
<h2>Risk normalization: lower percentage returns do not prove weaker direction</h2><p>This <strong>post-hoc descriptive diagnostic</strong> divides each active trade's gross/net percent by its scaled stop distance. Ambiguous outcomes and flats are excluded. It is a unit conversion, not an executable sizing or leverage policy; no new significance tests are claimed.</p><div class="scroll">RISKTABLE</div><p>At half width, <strong>v2 gross expectancy is +0.128 R versus +0.122 R originally</strong>, essentially unchanged as an observed point estimate, while fees double from 0.246 R to 0.491 R. At quarter width gross expectancy is +0.076 R and fees 0.982 R. V1 gross expectancy remains between +0.082 and +0.105 R. The lower percentage returns partly mechanically reflect smaller risk distances; fixed fees become more burdensome in R.</p><p>These are means across active unambiguous decisions. Target-hit rates have protocol-specific denominators; v1 has variable reward/risk. <a href="posthoc_risk_normalization.csv">Complete risk-normalization CSV</a> includes counts and equal-window means.</p><h2>The cost threshold is the central constraint</h2><p>Active trades at 15, 30 and 105 minutes capture an average gross move equivalent to only <strong>4.85, 4.45 and 1.54 bps</strong> of break-even round-trip cost. The study charges 20 bps. These are descriptive thresholds, not proof of an edge under a lower fee assumption.</p><p>All 12 scale-and-time combinations remain negative net. All six reversed-direction time policies also remain negative net. An always-short 105-minute benchmark is positive at +0.063% net, but its interval is wide [−0.191%, +0.329%], and its adjusted comparison against AI is not significant.</p>
<h2>Paired differences versus original brackets</h2><p>Positive values would favor the modified policy. P-values use whole-window sign flips; BH adjustment is separate for the six primary and fifteen secondary contrasts. Temporal sensitivity resamples 92 groups of neighboring windows.</p><div class="scroll">CONTRASTS</div>
<h2>Every model, protocol and policy</h2><p>All 506 grouped cells remain visible. Filter labels to compare versions or models. 25%-width ambiguity bounds retain all rows; exclusion-only means use a different denominator.</p><input id="filter" placeholder="Filter, e.g. v2 / gpt-6-astra" aria-label="Filter policy table"><span id="shown" class="muted"></span><div class="scroll" id="allTable">ALLTABLE</div>
<details><summary>Simple benchmarks and direction reversal — all 24 paired comparisons</summary><p>Differences are benchmark minus AI under the same time exit and common coverage. The momentum input is exactly zero on one window; its paired comparisons exclude that window from both sides (99 windows). Other benchmarks retain all 100 and the original active/flat mask.</p><div class="scroll">BENCHMARKS</div></details>
<details><summary>Chronological halves — every policy</summary><p>Original net return changes from +0.042% in the earlier 50 windows to −0.204% in the later 50. Primary fixed-time exits and smaller brackets are negative in both halves. These are already inspected windows, not a held-out test.</p><div class="scroll">HALVES</div></details>
<details><summary>UTC entry sessions — descriptive only</summary><p>Four fixed six-hour entry sessions are shown in full. These small subgroup summaries are not adjusted tests and have not been used to choose a trading rule.</p><div class="scroll">SESSIONS</div></details>
<h2>Post-hoc regime and original-direction appendix</h2><p>This section was requested after pooled results were known. It is descriptive: all cells are shown, no significance claim or chosen filter. Long and short strata can cover different overlapping window subsets.</p><p><strong>Below both MAs, short calls:</strong> 456 decisions across 50 windows average +0.201%, +0.197%, +0.258% gross at 15/30/105 minutes, or +0.001%, −0.003%, +0.058% net. Since every one of these 50 windows contains a short, the equal-window pure-time means are exactly those of a simple below-both-MAs short rule.</p><p><strong>Above both MAs, long calls:</strong> 243 decisions across 29 windows average −0.128%, −0.086%, −0.386% gross at those horizons. This is descriptive continuation failure, not a validated reversal rule.</p><p>The corrected 68% first-bar accuracy is 34 of 50 <strong>v2 majority/window decisions</strong>. Among all below-both short model rows here, it is 314/456 (68.9%) at 15 minutes and 220/456 (48.2%) at 105 minutes. Model-row counts and equal-window returns weight observations differently.</p><details><summary>All post-hoc regime × action cells, with counts</summary><div class="scroll">APPENDIX</div></details><h2>Interpretation for the MA-removal experiment</h2><p>Keep the v3 prompt and entry list fixed while collecting decisions. Apply the same frozen 15/30/105-minute comparison to v2 and v3; first test whether removing supplied indicators changes direction and confidence. V3 removes MA, ATR/sigma and derived summaries while preserving the raw 40-bar OHLCV history. It is broader than an MA-only intervention, with historical rather than concurrent v2 controls. Any selected exit or reversal rule needs fresh windows before it can be treated as evidence of a strategy.</p>
<div class="callout warning"><strong>This is exploratory reuse of existing data.</strong> Ten decisions share each market path, and the sample is all SOL. The OpenAI v2 collection also changed harness for resumed calls. These results are trade-level diagnostics, not a tradable portfolio simulation.</div>
<h2>Audit and execution assumptions</h2><ul><li>Unmodified native engine; exact next-minute entry alignment; gap-through-level fills at the open.</li><li>All 100 windows contain 4,320 consecutive future minute bars. Original source hashes remain unchanged.</li><li>All 1,000 scale-1 outcomes, durations, gross and net returns match originals.</li><li>Two trades have simultaneous one-minute SL/TP touches at 25% width. Paired tests exclude those two; bounds assign each to SL or TP. Full all-row net bounds are −0.1776% to −0.1764%.</li><li>25 original flat decisions remain flat and pay zero fees. All active trades pay the same 0.20% cost.</li><li>No funding, extra market impact, dynamic sizing or portfolio capital constraint is modeled.</li></ul>
<p><a href="policy_summary.csv">Policy table CSV</a> · <a href="paired_vs_original.csv">Paired tests CSV</a> · <a href="break_even_costs.csv">Break-even costs CSV</a> · <a href="exit_policy_overview.pdf">Export figure PDF</a> · <a href="run.py">Reproduce computations</a></p><footer>Seed 20260929 · 10,000 bootstrap resamples · Separate primary / secondary / benchmark test families · Original data preserved</footer><script>const f=document.getElementById('filter');const rows=[...document.querySelectorAll('#allTable tbody tr')];function filter(){let n=0;for(const r of rows){let yes=r.textContent.toLowerCase().includes(f.value.toLowerCase());r.hidden=!yes;n+=yes}document.getElementById('shown').textContent=n+' / '+rows.length+' rows'}f.addEventListener('input',filter);filter();</script></html>'''
for key,val in {'PRIMARY':table(primary),'CONTRASTS':table(c),'ALLTABLE':table(s[summarycols]),'BENCHMARKS':table(b),'HALVES':table(halves),'SESSIONS':table(sessions),'APPENDIX':table(appendix),'RISKTABLE':table(risk[['protocol','bracket_scale','known_decisions','active_decisions','ambiguous','tp_rate_known','mean_gross_r','mean_fee_r_same_known_rows','mean_net_r']])}.items():report=report.replace(key,val)
(HERE/'index.html').write_text(report)
print('Report and scientific figures written')
