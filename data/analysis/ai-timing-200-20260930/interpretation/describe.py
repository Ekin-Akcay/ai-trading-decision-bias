"""Dormant, descriptive-only review of released stage ledgers and saved paths."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
KEYWORDS={
    'moving_averages':['moving average','ma20','ma50','20ma','50ma','20-period','50-period'],
    'continuation_trend':['trend','continuation','lower high','lower low','higher high','higher low'],
    'exhaustion_reversal':['exhaust','reversal','overextend','overbought','oversold','rebound'],
    'breakout_rejection':['breakout','breakdown','reject','failed','failure'],
    'levels':['support','resistance','range','swing'],
    'volume':['volume'],
}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stats(values):
    v=np.asarray(values,float);v=v[np.isfinite(v)]
    if not len(v):return {'n':0}
    return {'n':len(v),'mean':float(v.mean()),'median':float(np.median(v)),
            'q25':float(np.quantile(v,.25)),'q75':float(np.quantile(v,.75)),
            'min':float(v.min()),'max':float(v.max())}
def pct(x):return 'undefined' if x is None else f'{x:+.3f}%'
def cells(frame):
    return [{'AI_action':a,'above_equal_MA20':bool(m20),'above_equal_MA50':bool(m50),'n':len(g)}
            for (a,m20,m50),g in frame.groupby(['AI_action','above_equal_MA20','above_equal_MA50'],sort=True)]
def describe(frame):
    selected=frame[frame.AI_aligned & frame.valid_coverage]
    groups={'all_calls':frame,'selected':selected,'opposed':frame[~frame.AI_aligned & frame.valid_coverage],
            'selected_winners':selected[selected.gate_gross_pct>0],'selected_losers':selected[selected.gate_gross_pct<0]}
    output={'opinions':len(frame),'selected_trades':len(selected),'AI_long_calls':int((frame.AI_action=='long').sum()),
            'AI_short_calls':int((frame.AI_action=='short').sum()),'MA20_agreement_n':int(frame.AI_agrees_MA20.sum()),
            'MA50_agreement_n':int(frame.AI_agrees_MA50.sum()),'MA_joint_cells':cells(frame),'groups':{}}
    for label,g in groups.items():
        counts={tag:int(g['reason_'+tag].sum()) for tag in KEYWORDS}
        out={'n':len(g),'confidence':stats(g.AI_confidence),'reason_category_counts':counts}
        if label.startswith('selected'):
            out['position_path']={key:stats(g[key]) for key in ['return_15m_pct','return_30m_pct','return_60m_pct','gate_gross_pct','mfe_pct','mae_pct','first_mfe_minute','first_mae_minute']}
        output['groups'][label]=out
    return output

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--confirmation-released',action='store_true');args=parser.parse_args()
    if not args.confirmation_released:raise RuntimeError('Explicit completed-confirmation release is required.')
    run=Path(json.loads((HERE.parent/'run.json').read_text())['run_dir'])
    active=json.loads((run/'score_release.json').read_text());assert active['stage']=='confirmation'
    confirm_audit=json.loads((run/'confirmation/scoring_audit.json').read_text());assert confirm_audit['passed']
    assert confirm_audit['score_release_sha256']==sha(run/'score_release.json')
    frames=[];path_map={};source_hashes={};summaries={}
    for stage in ['screen','confirmation']:
        folder=run/stage;release=json.loads((folder/'evidence/score_release.json').read_text())
        manifest=json.loads((folder/'evidence/manifest.json').read_text());lookup={c['case']:c for c in manifest['cases']}
        ledger=folder/'trade_ledger.jsonl';f=pd.DataFrame([json.loads(x) for x in ledger.read_text().splitlines() if x.strip()])
        assert sorted(f.case)==sorted(release['case_ids'])
        z=np.load(folder/'paths.npz');assert list(z['case'])==list(f.case)
        for i,row in f.iterrows():
            p=z['paths'][i];case=int(row.case);c=lookup[case]
            assert row.stage==stage
            f.loc[i,'ma50_now']=float(c['ma50_now'])
            f.loc[i,'gate_move_pct']=float(c['gate_move_pct']);f.loc[i,'volume_ratio']=float(c['volume_ratio'])
            if not row.valid_coverage:continue
            assert np.isfinite(p).all() and (p>0).all()
            side=int(row.trade_side);entry=p[0,0];signed_close=side*100*(p[:,3]/entry-1)
            assert abs(signed_close[-1]-row.gate_gross_pct)<1e-10
            favorable=100*(p[:,1]/entry-1) if side==1 else 100*(1-p[:,2]/entry)
            adverse=100*(p[:,2]/entry-1) if side==1 else 100*(1-p[:,1]/entry)
            for hold in [15,30,60]:f.loc[i,f'return_{hold}m_pct']=signed_close[hold-1]
            f.loc[i,'first_mfe_minute']=int(np.argmax(favorable))+1 if favorable.max()>0 else 0
            f.loc[i,'first_mae_minute']=int(np.argmin(adverse))+1 if adverse.min()<0 else 0
            path_map[(stage,case)]={'signed_close_pct':np.r_[0.,signed_close].tolist(),
                                    'favorable_pct':favorable.tolist(),'adverse_pct':adverse.tolist()}
        f['above_equal_MA50']=f.ma50_now<=100
        f['AI_agrees_MA20']=(f.AI_action=='long')==f.above_equal_MA20
        f['AI_agrees_MA50']=(f.AI_action=='long')==f.above_equal_MA50
        for tag,words in KEYWORDS.items():f['reason_'+tag]=f.AI_reason.str.lower().apply(lambda text:any(word in text for word in words))
        frames.append(f);summaries[stage]={'all':describe(f),'directions':{k:describe(g) for k,g in f.groupby('direction')},
                                         'assets':{k:describe(g) for k,g in f.groupby('asset')}}
        source_hashes[str(ledger)]=sha(ledger);source_hashes[str(folder/'paths.npz')]=sha(folder/'paths.npz')
    allrows=pd.concat(frames,ignore_index=True)
    chosen=allrows[(allrows.stage=='confirmation') & allrows.AI_aligned & allrows.valid_coverage].sort_values(['gate_gross_pct','case'])
    examples=[];seen=set()
    if len(chosen):
        for label,idx in [('best',len(chosen)-1),('worst',0),('lower_median',(len(chosen)-1)//2)]:
            row=chosen.iloc[idx];case=int(row.case)
            if case in seen:continue
            seen.add(case);example=row.to_dict();example['selection_rank']=label;examples.append(example)
    # No learned cutoffs, significance tests, policy selection, or additional returns.
    results={'descriptive_only':True,'no_new_model_calls':True,'no_unused_reserve_paths':True,
             'confidence_not_assumed_calibrated':True,'keyword_dictionary':KEYWORDS,'stages':summaries,
             'examples':examples,'sources':source_hashes,'plan_sha256':sha(HERE/'PLAN.md')}
    (HERE/'behavior.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
    allrows.to_csv(HERE/'descriptive_positions.csv',index=False)
    lines=['# What the AI said and how the positions moved','',
           'This is a descriptive review of completed screening and confirmation trades. It changes no trading rule and adds no statistical test. Screening and confirmation are shown separately; the frozen confirmation verdict remains authoritative. Returns are gross, with zero fees, funding and leverage.','',
           'The AI saw the snapshot at t0. It did not see the following 30-minute move or volume gate; the evaluated policy enters at t0+30 and closes after 120 minutes. This review therefore describes the delayed policy, not the outcome of the original AI bracket.','']
    cf=summaries['confirmation']['all'];wg=cf['groups']['selected_winners'];lg=cf['groups']['selected_losers']
    below=[x for x in cf['MA_joint_cells'] if not x['above_equal_MA20'] and not x['above_equal_MA50']]
    above=[x for x in cf['MA_joint_cells'] if x['above_equal_MA20'] and x['above_equal_MA50']]
    lines += [f"The clearest descriptive finding is action agreement with moving averages: {cf['MA20_agreement_n']}/{cf['opinions']} confirmation opinions agreed with MA20 direction and {cf['MA50_agreement_n']}/{cf['opinions']} with MA50 direction. When the original price was below both averages, {sum(x['n'] for x in below if x['AI_action']=='short')}/{sum(x['n'] for x in below)} calls were short; above both, {sum(x['n'] for x in above if x['AI_action']=='long')}/{sum(x['n'] for x in above)} were long. This does not establish that the model used the averages rather than correlated price structure.",'',
              f"Confidence barely differed between selected winners and losers in this sample: means {wg['confidence']['mean']:.3f} and {lg['confidence']['mean']:.3f}, with medians {wg['confidence']['median']:.2f} and {lg['confidence']['median']:.2f}. The best and worst declared-rank examples both described weak rebounds below moving averages, yet their delayed shorts ended at opposite extremes. Similar wording is therefore not a reliable explanation of why these individual outcomes differed.",'',
              'The observed first 30-minute move runs against the selected AI direction by construction. It is not evidence that the AI is statistically wrong. Later winning/losing path differences are also outcome-conditioned descriptions, not tested entry or exit rules.','']
    lines+=['## Action, moving averages, and confidence','',
            'MA agreement means long above/equal to the original moving average and short below it. Agreement is an association; it does not identify what caused the decision. Confidence is self-reported and is not treated as a win probability.','',
            '| Stage / gate | Opinions | AI long / short | MA20 agreement | MA50 agreement | Selected / opposed confidence median |',
            '|---|---:|---:|---:|---:|---:|']
    for stage,s in summaries.items():
        for direction,r in s['directions'].items():
            cm=lambda group:r['groups'][group]['confidence'].get('median')
            lines.append(f"| {stage} / {direction} | {r['opinions']} | {r['AI_long_calls']} / {r['AI_short_calls']} | {r['MA20_agreement_n']}/{r['opinions']} | {r['MA50_agreement_n']}/{r['opinions']} | {cm('selected')} / {cm('opposed')} |")
    lines+=['','Full MA cross-tabs, asset counts, confidence means, ranges and interquartile ranges are retained in `behavior.json`. The gates are selected populations, so these agreement rates are not estimates over all market times.','',
            '## Wording and position paths','',
            'Reason categories use the exact literal substring dictionary in PLAN.md. They overlap and summarize language; a mention does not prove causal reasoning. This deliberately literal dictionary can miss variants such as the bare word “averages”, so category counts are not exhaustive semantic counts. Winning/losing groups below are defined from the eventual outcome and cannot be used as entry signals.','']
    for stage,s in summaries.items():
        for direction,r in s['directions'].items():
            lines += [f'### {stage}: {direction} gate','',
                      '| Selected group | n | Confidence median | 15m return median | 30m | 60m | 120m | MFE median | MAE median |',
                      '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
            for group in ['selected_winners','selected_losers']:
                g=r['groups'][group];p=g['position_path'];vals=[pct(p[k].get('median')) for k in ['return_15m_pct','return_30m_pct','return_60m_pct','gate_gross_pct','mfe_pct','mae_pct']]
                lines.append('| '+' | '.join([group,str(g['n']),str(g['confidence'].get('median'))]+vals)+' |')
            lines+=['','| Reason category | All calls | Selected winners | Selected losers |','|---|---:|---:|---:|']
            for tag in KEYWORDS:lines.append('| '+tag+' | '+' | '.join(str(r['groups'][g]['reason_category_counts'][tag]) for g in ['all_calls','selected_winners','selected_losers'])+' |')
            lines.append('')
    lines+=['## Three declared-rank confirmation examples','',
            'Examples are the best, worst and lower-median selected confirmation returns, chosen by the rule written before confirmation outcomes were opened. Extremes are exceptional observations, not representative estimates. Intrabar high/low order is unknown.','']
    for e in examples:
        lines += [f"### {e['selection_rank'].replace('_',' ')}: case {e['case']}, {e['asset']}",'',
                  f"Original AI: **{e['AI_action']}**, confidence {e['AI_confidence']}. Original price was {'above/equal to' if e['above_equal_MA20'] else 'below'} MA20 and {'above/equal to' if e['above_equal_MA50'] else 'below'} MA50.",'',
                  '> '+e['AI_reason'].replace('\n','\n> '),'',
                  f"The first 30 minutes moved {pct(e['gate_move_pct'])}, with volume ratio {e['volume_ratio']:.3f}. Delayed {'long' if e['trade_side']==1 else 'short'} entry: {e['entry_time']} UTC at {e['entry_price']}; exit: {e['horizon_end']} UTC at {e['exit_price']}.",
                  f"Signed returns at 15/30/60/120 minutes: {pct(e['return_15m_pct'])} / {pct(e['return_30m_pct'])} / {pct(e['return_60m_pct'])} / **{pct(e['gate_gross_pct'])}**. MFE {pct(e['mfe_pct'])} first reached in minute {int(e['first_mfe_minute'])}; MAE {pct(e['mae_pct'])} first reached in minute {int(e['first_mae_minute'])}.",'']
    if examples:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(len(examples),1,figsize=(10,3*len(examples)),squeeze=False,constrained_layout=True)
        for ax,e in zip(axes[:,0],examples):
            p=path_map[('confirmation',int(e['case']))]
            ax.fill_between(np.arange(1,121),p['adverse_pct'],p['favorable_pct'],color='#9ab8ce',alpha=.35,label='Minute high/low signed range')
            ax.plot(np.arange(121),p['signed_close_pct'],color='#245c91',label='Minute close return')
            ax.axhline(0,color='#555',lw=.7);ax.set_title(f"{e['selection_rank'].replace('_',' ').title()} · case {e['case']} · {e['asset']} · {pct(e['gate_gross_pct'])}",loc='left')
            ax.set_ylabel('Signed return (%)');ax.set_xlabel('Minutes after delayed entry');ax.grid(alpha=.15)
        fig.savefig(HERE/'confirmation_examples.png',dpi=160);plt.close(fig)
        lines+=['![Best, worst and lower-median selected confirmation position paths](confirmation_examples.png)','']
    lines+=['## Limits','',
            'These descriptive differences cannot rescue a failed confirmation criterion, establish that moving averages caused the calls, or show that the AI acts like a losing retail trader. The rationale is a short self-reported explanation. Asset and calendar composition can explain apparent differences between winning and losing groups. No new threshold, model, exit or direction rule was selected from this review.','']
    (HERE/'AI_BEHAVIOR.md').write_text('\n'.join(lines))
    print(json.dumps({'descriptive_only':True,'stage_opinions':{s:v['all']['opinions'] for s,v in summaries.items()},'example_cases':[e['case'] for e in examples],'output':str(HERE/'AI_BEHAVIOR.md')}))

if __name__=='__main__':main()
