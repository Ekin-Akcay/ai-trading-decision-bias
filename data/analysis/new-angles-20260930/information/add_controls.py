from pathlib import Path
import json
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
w=pd.read_csv(HERE/'forward_predictions.csv');z=np.load(HERE/'quarter_bootstrap_draws.npz')
valid=w.scored_forward_fold.to_numpy(bool);r=w.gross_240_pct.to_numpy()
lookup={q:i for i,q in enumerate(z['quarter'])};q=np.array([lookup[x] for x in w.quarter])
pred_sign=np.where(w.pred_short>=.5,-1,1);actual_sign=np.where(w.AI_short,-1,1)
def stats(v,m):
    ids=np.flatnonzero(m);x=v[m]
    if not len(x):return {'n':0}
    counts=np.bincount(q,weights=m,minlength=len(lookup));sums=np.bincount(q,weights=np.where(m,v,0),minlength=len(lookup))
    den=z['weights']@counts;ok=den>0;sample=(z['weights']@sums)[ok]/den[ok]
    return {'n':len(x),'unique_entry_time_blocks':int(w.entry_time[m].nunique()),'mean_pct':float(x.mean()),'win_rate':float((x>0).mean()),'ci95_quarter':np.quantile(sample,[.025,.975]).tolist()}
out=[]
for name,v in [('price_model_predicted_AI_direction_follow',pred_sign*r),('price_model_predicted_AI_direction_fade',-pred_sign*r),('actual_AI_direction_fade',-actual_sign*r),('actual_AI_fade_minus_price_model_fade',(-actual_sign+pred_sign)*r)]:
    out.append({'name':name,'all':stats(v,valid),'cohorts':{c:stats(v,valid&w.cohort.eq(c).to_numpy()) for c in sorted(w.cohort.unique())},'years':{str(y):stats(v,valid&w.year.eq(y).to_numpy()) for y in sorted(w.year[valid].unique())},'added_after_candidate_scoring':True,'diagnostic_only_no_new_candidate':True,'no_additional_fits':True})
(HERE/'price_distillation_controls.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps([{r['name']:r['all']}for r in out],indent=2))
