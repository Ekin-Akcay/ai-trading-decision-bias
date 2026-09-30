"""Post-score, fixed identical-coverage AI/MA20 direction diagnostic; no calls."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent

def clean(x):
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.bool_,)):return bool(x)
    if isinstance(x,(float,np.floating)):
        if np.isnan(x):return None
        if np.isinf(x):return '-Infinity' if x<0 else 'Infinity'
        return float(x)
    return x
def interval(v):
    finite=np.isfinite(v);lower=np.where(finite,v,-np.inf)
    return {'ordinary95_finite_draw_interval':np.quantile(v[finite],[.025,.975],method='inverted_cdf') if finite.any() else [None,None],
            'ordinary95_lower_undefined_minus_infinity':np.quantile(lower,.025,method='inverted_cdf'),
            'undefined_fraction':(~finite).mean(),'family_adjusted':False}
def fmt(x):return f'{x:+.3f}' if isinstance(x,(int,float,np.number)) else str(x)

def main():
    plan=HERE/'POST_SCORE_PLAN.md';assert plan.is_file()
    run=Path(json.loads((HERE.parent/'run.json').read_text())['run_dir'])
    assert json.loads((run/'score_release.json').read_text())['stage']=='confirmation'
    assert json.loads((run/'confirmation/scoring_audit.json').read_text())['passed']
    results={};vectors=[];bootstrap={};checks=0
    for stage in ['screen','confirmation']:
        rows=[json.loads(x) for x in (run/stage/'trade_ledger.jsonl').read_text().splitlines()]
        f=pd.DataFrame(rows);f=f[(f.direction=='up') & f.valid_coverage].sort_values(['t0','case']).copy()
        f['follow_AI_pct']=f.gate_gross_pct*np.where(f.AI_action=='short',1.,-1.)
        f['follow_MA20_pct']=f.gate_gross_pct*np.where(f.above_equal_MA20,-1.,1.)
        f['AI_minus_MA20_pp']=f.follow_AI_pct-f.follow_MA20_pct
        # Independently check each algebraic sign against audited entry/exit prices.
        direct=100*(f.exit_price-f.entry_price)/f.entry_price
        assert np.allclose(f.follow_AI_pct,direct*np.where(f.AI_action=='long',1.,-1.),atol=1e-10,rtol=0)
        assert np.allclose(f.follow_MA20_pct,direct*np.where(f.ma20_now<=100,1.,-1.),atol=1e-10,rtol=0)
        assert np.allclose(f.loc[(f.AI_action=='long')==f.above_equal_MA20,'AI_minus_MA20_pp'],0,atol=1e-12)
        checks+=2*len(f)
        frozen=np.load(run/stage/'bootstrap_arrays.npz');qs=list(frozen['quarters']);w=frozen['quarter_weights'];assert len(w)==40000
        codes=np.array([qs.index(q) for q in f.quarter]);counts=np.bincount(codes,minlength=len(qs));den=w@counts
        n=len(f);r={'gates':n,'AI_short_n':int((f.AI_action=='short').sum()),'AI_long_n':int((f.AI_action=='long').sum()),
                   'MA_short_n':int((~f.above_equal_MA20).sum()),'MA_long_n':int(f.above_equal_MA20.sum()),
                   'AI_MA_agreement_n':int(((f.AI_action=='long')==f.above_equal_MA20).sum()),
                   'quarter_universe':qs,'bootstrap_draws':len(w),'bootstrap_seed':2026093051,'vectors':{}}
        for key in ['follow_AI_pct','follow_MA20_pct','AI_minus_MA20_pp']:
            v=f[key].to_numpy(float);num=w@np.bincount(codes,weights=v,minlength=len(qs));bs=np.divide(num,den,out=np.full(len(w),np.nan),where=den>0)
            halves=[{'n':len(g),'mean':g[key].mean()} for g in [f.iloc[:(n+1)//2],f.iloc[(n+1)//2:]]]
            trimmed={};order=f[f[key]>0].sort_values([key,'case'],ascending=[False,True])
            for k in [1,3]:
                removed=order.case.iloc[:k].tolist();kept=f[~f.case.isin(removed)]
                trimmed[str(k)]={'removed_cases':removed,'n':len(kept),'mean':kept[key].mean() if len(kept) else None}
            r['vectors'][key]={'n':n,'mean':v.mean(),'median':np.median(v),'positive_n':int((v>0).sum()),'negative_n':int((v<0).sum()),
                               'zero_n':int((v==0).sum()),'interval':interval(bs),'chronological_halves':halves,'removed_largest_positive_events':trimmed}
            bootstrap[stage+'__'+key]=bs
        results[stage]=r;vectors.append(f)
    frame=pd.concat(vectors,ignore_index=True);frame.to_csv(HERE/'identical_coverage_vectors.csv',index=False)
    np.savez_compressed(HERE/'identical_coverage_bootstrap.npz',**bootstrap)
    out={'post_score_diagnostic':True,'not_frozen_confirmation':True,'no_new_calls':True,'same_clock_same_coverage':True,
         'plan_sha256':hashlib.sha256(plan.read_bytes()).hexdigest(),'sign_checks':checks,'stages':results}
    (HERE/'identical_coverage.json').write_text(json.dumps(clean(out),indent=2,allow_nan=False)+'\n')
    lines=['# Identical-coverage AI versus MA20 direction','',
           'This diagnostic was specified after viewing the completed confirmation results. It is retrospective, has no new model calls or outcomes, and does not change the frozen failed confirmation verdict. Both policies trade every quiet-UP gate with the same 30-minute delayed entry and 120-minute hold. Returns are gross and unleveraged, with zero costs.','',
           'The AI policy follows the original AI direction, including long calls that the frozen short-only rule skipped. The MA20 policy shorts when the original snapshot price is below MA20 and buys when above/equal. Both use the original snapshot, not later indicators.','',
           '| Stage | Gates | Always follow AI | Always follow MA20 | Paired AI − MA20 |',
           '|---|---:|---:|---:|---:|']
    for stage,r in results.items():
        v=r['vectors'];lines.append(f"| {stage} | {r['gates']} | {fmt(v['follow_AI_pct']['mean'])}% | {fmt(v['follow_MA20_pct']['mean'])}% | {fmt(v['AI_minus_MA20_pp']['mean'])} pp |")
    lines+=['','Intervals below reuse the original 40,000 complete-quarter resamples and include quarters without UP trades. They are ordinary, unadjusted descriptive intervals; this post-score comparison is not an additional successful validation. Screen and confirmation are never pooled.','']
    for stage,r in results.items():
        lines += [f'## {stage.capitalize()}','',
                  f"AI directions: {r['AI_short_n']} short, {r['AI_long_n']} long. MA20 directions: {r['MA_short_n']} short, {r['MA_long_n']} long. They agree on {r['AI_MA_agreement_n']}/{r['gates']} gates.",'',
                  '| Vector | Mean | Ordinary quarter 95% interval | First / second half | Remove best one | Remove best three |',
                  '|---|---:|---:|---:|---:|---:|']
        for key,v in r['vectors'].items():
            unit=' pp' if key=='AI_minus_MA20_pp' else '%';ci=v['interval']['ordinary95_finite_draw_interval'];half=v['chronological_halves'];tail=v['removed_largest_positive_events']
            lines.append(f"| {key} | {fmt(v['mean'])}{unit} | [{fmt(ci[0])}, {fmt(ci[1])}]{unit} | {fmt(half[0]['mean'])} / {fmt(half[1]['mean'])}{unit} | {fmt(tail['1']['mean'])}{unit} | {fmt(tail['3']['mean'])}{unit} |")
        lines+=['','Concentration diagnostics remove the largest positive contributions separately for each vector; the removed case sets can differ. Full masks, removed case IDs and undefined bootstrap fractions are retained in `identical_coverage.json`.','']
    c=results['confirmation']['vectors'];delta=c['AI_minus_MA20_pp']['mean'];ci=c['AI_minus_MA20_pp']['interval']['ordinary95_finite_draw_interval']
    lines += ['## Interpretation','',
              f"In confirmation, always following the AI returned {fmt(c['follow_AI_pct']['mean'])}% per gate, while always following MA20 returned {fmt(c['follow_MA20_pct']['mean'])}%. The paired AI increment was {fmt(delta)} percentage points, with ordinary 95% interval [{fmt(ci[0])}, {fmt(ci[1])}].",
              'The sign and uncertainty of this paired difference describe whether AI improved on this specific simple direction comparator in the observed sample. A positive mean for either post-score policy is not independently verified profitability. This comparison does not establish AI dependence, causal use of moving averages, or value beyond all price features.','']
    (HERE/'IDENTICAL_COVERAGE.md').write_text('\n'.join(lines))
    print(json.dumps(clean(out),indent=2))

if __name__=='__main__':main()
