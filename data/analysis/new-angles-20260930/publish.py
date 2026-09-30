"""Publish the data-only correction study without altering any earlier report."""
from pathlib import Path
import json,html,hashlib
import pandas as pd

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
def read(rel):return json.loads((P/rel).read_text())
def f(x):return f'{x:+.3f}%'
target=read('target_exhaustion/summary.json')
relative=read('relative_value/summary.json')['policies']
information=pd.read_csv(P/'information/candidate_summary.csv')
calibration=read('information/model_calibration.json')
proxy=read('proxy_replication/summary.json')
scored=sum(r['n'] for r in calibration)
correct=sum(round(r['short_accuracy']*r['n']) for r in calibration)
budget=ROOT/'data/analysis/gross-edge-20260929/snapshot_budget.json'
b=json.loads(budget.read_text());attempts=len(b['reserved_attempts'])
assert attempts==771

target_lines=['# Confirmed target exhaustion: rejected for further calls','',
'This tests a new ordered event: the original AI bracket reaches its target before its stop; a later completed minute closes back inside that target; take the opposite direction at the next minute open and hold 60 minutes. It is distinct from previous immediate reversals and stopout fades. All outcomes were previously available, so this is discovery only.',
'','The source set contains 1020 distinct asset windows grouped into 645 original entry-time clusters. One Terra MA-present decision per window is used. Cohorts have different selection rules; pooled means weight asset opportunities, not calendar baskets or a constructed portfolio. Costs are zero; returns use unlevered initial notional.','',
'| Policy | Trades | Mean gross per trade | Without best 3 entry-time clusters | Positive chronological folds |',
'|---|---:|---:|---:|---:|']
for r in target:
    target_lines.append(f"| {r['policy']} | {r['trades']} | {f(r['mean_gross_pct'])} | {f(r['without_best3_blocks_pct'])} | {r['positive_folds']}/5 |")
target_lines += ['',
'The main long policy loses 0.0834% on 175 positions. Its two chronological halves average −0.3414% and +0.2160%; after the best 3 contributing market events are removed, it loses 0.2068%. The short policy makes 0.0499% on 66 positions, but its first half and its result after removing the best 3 events are negative. Neither is a credible candidate.',
'','No policy passes the pre-calculation discovery screen. All eight AI-minus-control opportunity-return intervals include zero. The exact AI target offers no demonstrated advantage over the same state machine using ATR levels. Donor widths are AI-derived; only the two fixed-direction ATR policies are fully price-only controls.',
'','The 11-policy simultaneous block intervals, whole-quarter intervals, cohort/fold results, excursions, 1/5-minute execution-latency sensitivities and every skipped/traded event are saved. Latency sensitivities do not replace the original execution. The positive +0.0034% pooled 5-minute-latency mean is descriptive, not a newly selected rule.',
'','Files: PLAN.md freezes the family; event_ledger.csv stores 5100 window/geometry replays including 241 primary AI trades; summary.json and comparisons.json preserve all definitions; breakdown.csv contains cohort/time detail; family_arrays.npz preserves common resamples. Earlier reports and model decisions are unchanged.']
(P/'target_exhaustion/RESULTS.md').write_text('\n'.join(target_lines)+'\n')
(P/'target_exhaustion/CANDIDATE_GATE.json').write_text(json.dumps(dict(status='NO_CANDIDATE',distinct_mechanism=True,additional_model_calls=0,original_windows=1020,entry_time_clusters=645,policy_count=11,passed_discovery_screens=0,positive_simultaneous_AI_control_differences=0,request_more_calls=False,reason='No positive stable policy with demonstrated incremental value over controls.',seen_outcome_discovery_only=True),indent=2)+'\n')

lines=['# New research after the budget correction','',
'The previous 771 attempts were allocated to 500 new snapshots of earlier strategy candidates, 270 paired MA/repeat snapshots, and one failed attempt. That allocation did not follow the requested priority of discovering a different mechanism. This correction uses existing data and spends zero additional trade-agent credits; 29 of the 800 allowance remain.',
'','Three bounded new research families were defined before their calculations, followed by a frozen behavior-proxy test on different historical price windows. Every policy, comparison and failure is retained. The first three reuse previously inspected outcomes; the final test excludes all previously exposed target intervals and uses unchanged annual fits. Fees are zero. None produced a candidate ready for another agent wave.',
'','## What was actually tested','',
'| New mechanism | Evidence | Result |',
'|---|---|---|',
'| Cross-asset relative value |125 synchronized four-asset snapshots; 12 fixed AI/control rankings | All three inverted AI rankings lose. Reversing signed confidence averages −0.133% per active basket. |',
'| AI information beyond price patterns | Prior-year models predict AI behavior, then score 11 fixed surprise/reason/disagreement rules | Unexpected SHORT→buy loses −0.285% on 57 trades. Unexpected LONG→sell makes +0.294% on 60, but adds −0.050 percentage points versus matched raw direction. |',
'| Target reached, then rejected/reclaimed |1020 windows; 11 fixed geometry/side policies | Buy after a downside-target reclaim loses −0.083% on 175 positions. The short equivalent makes +0.050% on 66, falling negative after removing its three best events. |',
'| Reverse a frozen imitation of the AI |783 different calendar windows / 3132 asset trades; no model calls or refits | Mean basket return +0.00883%; weekly 99% interval −0.09351% to +0.10856%. Both the gross-profit and MA20-increment claims fail. |',
'','These per-trade and per-basket means have different exposure conventions; they are not comparable portfolio returns. The full reports retain opportunity means and matched controls.',
'','## Concrete behavioral finding','',
f'A small forward-trained model using five price/volume features plus asset identifiers reproduces {correct}/{scored} ({100*correct/scored:.2f}%) of later AI directions. Training uses only earlier calendar years with a seven-day embargo. This is accuracy at predicting what the AI says, not predicting the market. It shows substantial redundancy with supplied price features, but does not establish a causal MA effect or psychological retail behavior. The unusual choices did not supply a stable contrarian advantage.',
'','## The free test on different price windows','',
'On the previously studied 803 scored asset windows, reversing predicted AI choices averaged +0.1612%, very close to reversing actual choices (+0.1648%). The synchronized four-asset subset averaged +0.23349% across 96 baskets. These older and newer sampling populations differ; their difference is not a paired estimate of performance decay. This motivated one additional test that needed no new AI opinions. The annual models, threshold, four-hour exit, four assets and price-only comparator were frozen before opening the new targets.',
'','All 783 eligible 00/06/12/18 UTC calendar blocks were used, covering 192 weeks and 19 quarters. Their target intervals avoid all 681 earlier exposed history/outcome intervals across all four assets. Each basket allocates one quarter of initial notional per asset. The 783 baskets are the economic observations; 3132 asset trades are not independent samples.',
'','The frozen proxy earns +0.00883% per basket, versus −0.00185% for MA20 fade and +0.01760% for unconditional long. The proxy-minus-MA20 advantage is +0.01069 percentage points, with a weekly 99% interval from −0.08886 to +0.10952 points. The proxy quarter 95% interval also includes zero. Its first half loses −0.00600%; removing its three best baskets leaves −0.01377%. Both locked claims fail.',
'','For the requested long emphasis, the descriptive long leg has 2022 trades averaging +0.02047%; the short leg has 1110 averaging −0.01237%. These legs were recorded before scoring as decompositions of the primary policy, and neither is promoted as another strategy. The positive old-data mean did not transfer reliably to different target windows.',
'','## Positive observations retained, not promoted','',
'Following the confidence-based asset ranking earns +0.133% per active basket, the opposite of the proposed AI-is-wrong mechanism. Its interval includes zero and 77% of its aggregate contribution comes from ETH. It does not demonstrate an incremental advantage over price rankings.',
'','Following the no-MA opinion when identical-input repeats disagree earns +1.071% on only 10 windows; its interval crosses zero. A confident unexpected bullish-call reversal earns +2.969% on only four trades. Such small cells are explicitly retained and rejected as insufficient evidence; they are not profitable-strategy claims.',
'','## Files and accounting','',
'- [Relative-value report](relative_value/RESULTS.md): every basket, asset weight, control, fold and uncertainty calculation.',
'- [Information report](information/RESULTS.md): annual fits, all 11 candidate vectors, reasons and controls.',
'- [Target-exhaustion report](target_exhaustion/RESULTS.md): every target event, confirmation, entry, exit and skipped opportunity.',
'- [Frozen proxy transfer report](proxy_replication/RESULTS.md): all 783 baskets, 3132 positions, controls, sample exclusions and locked claim checks.',
'- [Research contract](audit/EVALUATION_CONTRACT.md) and prior experiment inventory distinguish these mechanisms from previous failures.',
'- index.html provides a compact overview and inspection of the 241 primary target-reaction positions.',
'','No existing source decision, failed validation result, prior HTML report or budget entry was changed. Independent audit artifacts live in audit/. Research-analysis workers did not request new trade-agent decisions. The 771-used/29-remaining balance is unchanged.']
(P/'RESULTS.md').write_text('\n'.join(lines)+'\n')

def table(headers,rows):
    return '<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'
rvrows=[]
for name,item in relative.items():
    s=item['summary'];rvrows.append([name,s['active'],f(s['mean_per_active_pct']),f(s['mean_per_opportunity_pct']),f(s['ex_best3_active_mean_pct'])])
inforows=[[r.candidate,r.n,f(r.gross_mean_pct),f(r.direction_increment_pct),'No'] for r in information.itertuples()]
trrows=[[r['policy'],r['trades'],f(r['mean_gross_pct']),f(r['without_best3_blocks_pct']),'No'] for r in target]
led=pd.read_csv(P/'target_exhaustion/event_ledger.csv');w=pd.read_csv(P/'target_exhaustion/windows.csv')
trades=led[(led.geometry=='ai')&(led.status=='trade')].merge(w[['window_id','reason']],on='window_id',validate='one_to_one')
position_rows=[]
for r in trades.itertuples():
    position_rows.append([r.window_id,r.asset,r.cohort,r.position,r.position_entry_time,r.position_exit_time,f'{r.entry_price:.6g}',f'{r.exit_price:.6g}',f(r.gross_pct),f(r.mfe_pct),f(r.mae_pct),r.reason])
body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>New-angle research · September30</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;background:#101621;color:#e8edf4;margin:0;padding:32px;max-width:1500px}}h1,h2{{line-height:1.2}}p{{max-width:950px}}a{{color:#94caff}}.note{{padding:18px;background:#1d2939;border-left:4px solid #83b9e7}}.wrap{{overflow:auto;margin:20px 0}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;border-bottom:1px solid #334256;text-align:left;vertical-align:top}}th{{background:#1d2939;position:sticky;top:0}}input{{font:inherit;padding:10px;width:min(600px,90%);background:#1d2939;color:white;border:1px solid #607087}}.positions{{max-height:700px;overflow:auto}}small{{color:#abb9c9}}</style>
<h1>New-angle research</h1><p>Three new mechanism families tested using existing decisions. <strong>Zero new trade calls. 29 credits preserved.</strong></p>
<div class="note">No candidate passed. The first three studies reuse known outcomes; the frozen proxy was also tested on different historical targets. Returns are gross, zero-cost, unlevered arithmetic returns. All failures and positive small-sample observations are retained.</div>
<p>The prior 771-call allocation focused on replication and MA ablation. It missed the requested priority of finding a new mechanism. This report records the corrective analysis; it does not change or replace earlier failed validations.</p>
<p><a href="RESULTS.md">Full findings</a> · <a href="audit/EVALUATION_CONTRACT.md">Evaluation contract</a> · <a href="audit/PRIOR_EXPERIMENT_INVENTORY.json">Earlier experiment inventory</a></p>
<h2>Behavior: AI decisions are largely reproducible from prices</h2><p>A small model trained on earlier years reproduced <strong>{correct}/{scored} ({100*correct/scored:.2f}%)</strong> of later AI directions using supplied price/volume features and asset identifiers. That predicts the AI's choice, not the market. Unexpected choices did not establish a stable contrarian edge.</p>
<h2>Cross-asset rankings</h2><p>125 synchronized baskets, four assets, +0.5 long/−0.5 short notional when active, four-hour holding period. Dollar neutral does not mean beta neutral. Every inverted AI ranking lost on average. Confidence-follow is an uncertain opposite-hypothesis observation, not a promoted strategy.</p><div class="wrap">{table(['Ranking','Active baskets','Mean/active','Mean/opportunity','Remove best 3'],rvrows)}</div>
<h2>Information beyond raw direction</h2><p>Annual forward fits; fixed definitions; five-year scoring. Positive tiny samples do not count as verified strategies. All eleven rules fail the complete recommendation screen.</p><div class="wrap">{table(['Rule','Trades','Mean gross','Increment beyond raw direction','Promoted'],inforows)}</div>
<h2>Frozen proxy: test on different historical targets</h2><p>The old four-asset subset averaged +0.23349% over 96 baskets; the frozen rule averaged <strong>+0.00883% per basket</strong> over 783 different calendar blocks and 3132 asset positions. The samples have different calendar distributions, so this is a transfer test rather than a paired decay estimate. Weekly 99% interval: −0.09351% to +0.10856%. The first chronological half loses, and removing the three best baskets produces −0.01377%. Both frozen claims fail. No new AI calls or refits were made.</p><p>The paired advantage over MA20 fade is +0.01069 percentage points, with an interval crossing zero. Descriptive long positions average +0.02047% across 2022 trades; shorts average −0.01237% across 1110. Neither leg is promoted. <a href="proxy_replication/RESULTS.md">Full transfer report</a> · <a href="proxy_replication/window_results.csv">All 3132 asset trades</a> · <a href="proxy_replication/basket_results.csv">All 783 baskets</a></p>
<figure style="margin:24px 0"><img src="proxy_replication/proxy_replication.png" alt="Frozen proxy return intervals include zero; yearly returns vary in sign" style="width:100%;max-width:1250px;height:auto;background:white"></figure>
<h2>Target exhaustion with confirmation</h2><p>TP before SL within 240 minutes; a later minute closes back inside the target within 15 minutes; reverse at the next open and hold 60 minutes. 1020 asset windows across 645 original entry times; pooled means weight asset opportunities, not equal-capital calendar baskets. AI long/short labels below denote the new position.</p><div class="wrap">{table(['Policy','Trades','Mean gross','Remove best 3 events','Promoted'],trrows)}</div>
<h2>Inspect the 241 primary target-reaction positions</h2><p>Every underlying geometry, including skips, is saved in <a href="target_exhaustion/event_ledger.csv">event_ledger.csv</a>. MFE and MAE are favorable/adverse excursions during the new 60-minute position.</p><input id="filter" aria-label="Filter positions" placeholder="Filter asset, side, date, window or reason…"><p><small id="count">241 positions</small></p><div class="positions" id="positions">{table(['Window','Asset','Cohort','Position','Entry time','Exit time','Entry','Exit','Gross','MFE','MAE','Original AI reason'],position_rows)}</div>
<script>const rows=Array.from(document.querySelectorAll('#positions tbody tr'));document.getElementById('filter').addEventListener('input',e=>{{const q=e.target.value.toLowerCase();let n=0;for(const r of rows){{const yes=r.textContent.toLowerCase().includes(q);r.hidden=!yes;if(yes)n++;}}document.getElementById('count').textContent=n+' positions';}});</script></html>'''
(P/'index.html').write_text(body)
account=dict(status='complete',additional_trade_calls=0,used_allowance=attempts,remaining_allowance=800-attempts,budget_sha256=hashlib.sha256(budget.read_bytes()).hexdigest(),discovery_asset_windows=1020,discovery_entry_times=645,new_discovery_families=3,fixed_discovery_policy_definitions=34,extra_frozen_proxy_calendar_blocks=783,extra_frozen_proxy_asset_trades=3132,proxy_refits=0,proxy_gross_claim_passed=proxy['gross_profit_gate']['passed'],proxy_MA20_increment_claim_passed=proxy['increment_over_MA20_gate']['passed'],promoted_candidates=0,independent_profit_verification=False,source_reports_preserved=True)
(P/'completion.json').write_text(json.dumps(account,indent=2)+'\n')
print(json.dumps(account,indent=2))
