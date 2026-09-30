"""Test the estimator on synthetic data only. No experiment outputs are read."""
from pathlib import Path
import importlib.util,json
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('gross_evaluator_under_review',HERE.parent/'evaluate.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
values=np.array([1.,-2.,3.,4.,-1.,2.,.5,-3.,4.,-.5,1.5,2.])
groups=np.repeat(np.arange(3),4)
strata=np.tile(np.arange(4),3)
eligible=np.array([1,1,1,0,1,1,1,1,1,1,0,1],dtype=bool)
selected=np.array([1,0,1,0,0,1,1,0,1,1,0,0],dtype=bool)
weights=np.random.default_rng(913).multinomial(3,[1/3]*3,size=250)

def explicit(weights,selected):
    means=[];deltas=[]
    for w in weights:
        ids=np.repeat(np.arange(len(values)),w[groups])
        chosen=ids[selected[ids]]
        if not len(chosen):means.append(np.nan);deltas.append(np.nan);continue
        baseline=0.
        for s in np.unique(strata[chosen]):
            available=ids[eligible[ids]&(strata[ids]==s)]
            count=(strata[chosen]==s).sum()
            baseline+=count*values[available].mean()
        mean=values[chosen].mean()
        means.append(mean);deltas.append(mean-baseline/len(chosen))
    return np.array(means),np.array(deltas)

checks={}
for label,mask in [('partial_selection',selected),('all_eligible_selected',eligible),('no_selection',np.zeros(len(values),bool))]:
    result,mean,delta=module.boot_for_rule(values,mask,eligible,groups,strata,weights)
    expected_mean,expected_delta=explicit(weights,mask)
    assert np.allclose(mean,expected_mean,rtol=0,atol=1e-12,equal_nan=True)
    assert np.allclose(delta,expected_delta,rtol=0,atol=1e-12,equal_nan=True)
    if mask.any():
        finite=expected_delta[np.isfinite(expected_delta)]
        assert np.allclose(result['AI_increment']['simultaneous97_5'],np.quantile(finite,[.0125,.9875]))
    else:
        assert result['profit']['valid_resamples']==0 and result['AI_increment']['valid_resamples']==0
    checks[label]=True
result={'passed':True,'synthetic_resamples_per_scenario':250,'scenarios':checks,
        'method':'Explicit duplication of complete groups and direct within-stratum means, compared with aggregate matrix estimator',
        'fresh_data_or_model_outputs_read':False}
(HERE/'synthetic_bootstrap_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
