"""Independent vectorized first-event audit and original-trigger ambiguity flags."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
m=pd.read_csv(HERE/'windows.csv');ledger=pd.read_csv(HERE/'all_window_paths.csv.gz')
policies={p['policy']:p for p in json.loads((HERE/'policies.json').read_text())}
px=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index();prices=px[['open','high','low','close']].to_numpy(float)
positions=px.index.get_indexer(pd.to_datetime(m.entry_time));assert (positions>0).all()
for q in positions:
    path=prices[q:q+480];assert path.shape==(480,4) and np.isfinite(path).all() and (path>0).all()
meta=m.set_index('window_id');positions={wid:int(p) for wid,p in zip(m.window_id,positions)}

def independent_first(q,length,entry,sign,width):
    block=prices[q:q+length];op=block[:,0];hi=block[:,1];lo=block[:,2]
    stop=entry*(1-sign*width);target=entry*(1+sign*2*width)
    opstop=op<=stop if sign==1 else op>=stop;optarget=op>=target if sign==1 else op<=target
    stophit=lo<=stop if sign==1 else hi>=stop;targethit=hi>=target if sign==1 else lo<=target
    events=np.flatnonzero(opstop|optarget|stophit|targethit)
    if len(events)==0:return 'timeout',length-1,block[-1,3]
    k=int(events[0])
    if opstop[k]:return 'sl_gap',k,op[k]
    if optarget[k]:return 'tp_gap_capped',k,target
    if stophit[k]:return ('sl_ambiguous' if targethit[k] else 'sl'),k,stop
    return 'tp',k,target

origchecks=0;tradechecks=0
for row in ledger.itertuples(index=False):
    w=meta.loc[row.window_id];q=positions[row.window_id];p=policies[row.policy];sign=1 if p['side']=='long' else -1
    width=w.stop_pct if row.width=='AI_width' else w.atr14_pct/100
    outcome,k,exitpx=independent_first(q,p['max_wait'],w.price_real,sign,width)
    assert outcome==row.original_first_outcome and k==row.original_first_bar and abs(exitpx-row.original_exit_price)<1e-8
    assert row.stop_first==outcome.startswith('sl')
    assert row.AI_selected==(row.stop_first and w.action==p['side']);origchecks+=1
    if not row.stop_first:continue
    newq=q+k+1;newpx=prices[newq,0]
    assert pd.Timestamp(row.entry_time)==px.index[newq] and abs(newpx-row.entry_price)<1e-8
    assert pd.Timestamp(row.trigger_bar_close_time)==px.index[newq]
    if p['exit']=='time':result='time';held=p['hold'];finalpx=prices[newq+held-1,3]
    else:result,newk,finalpx=independent_first(newq,p['hold'],newpx,sign,w.atr14_pct/100);held=newk+1
    gross=sign*(finalpx/newpx-1)*100
    assert result==row.strategy_outcome and abs(finalpx-row.exit_price)<1e-8 and held==row.held_minutes
    assert abs(gross-row.gross_pct)<1e-8 and abs(gross-.2-row.net20_pct)<1e-8
    assert pd.Timestamp(row.exit_minute_close_time)==px.index[newq]+pd.Timedelta(minutes=held)
    tradechecks+=1

ledger['ambiguous_original_trigger']=ledger.original_first_outcome.eq('sl_ambiguous')
ledger.to_csv(HERE/'all_window_paths.csv.gz',index=False)
bundle=np.load(HERE/'family_vectors.npz');arrays={key:bundle[key] for key in bundle.files};flags=[];sens=[]
for label in arrays['policylabels']:
    policy,group=label.split('/');width='ATR_width' if group=='ATR_width_price_only_control' else 'AI_width'
    subset=ledger[(ledger.policy==policy)&(ledger.width==width)]
    flags.append(subset[subset.cohort=='new280'].sort_values('case').ambiguous_original_trigger.to_numpy(bool))
    for cohort in ['old150','new280']:
        frame=subset[subset.cohort==cohort];mask=frame.AI_selected if group=='AI_selected_stopout_fade' else frame.stop_first
        primary=frame.loc[mask];excluded=primary[primary.ambiguous_original_trigger];kept=primary[~primary.ambiguous_original_trigger]
        sens.append({'policy':policy,'group':group,'cohort':cohort,'primary_n':len(primary),'ambiguous_original_trigger_count':len(excluded),'primary_net_mean':primary.net20_pct.mean(),'exclude_ambiguous_n':len(kept),'exclude_ambiguous_net_mean':kept.net20_pct.mean(),'sensitivity_only_no_change_to_primary':True})
arrays['ambiguous_original_trigger']=np.array(flags)
assert arrays['ambiguous_original_trigger'].shape==arrays['selected'].shape==(48,280)
tmp=HERE/'family_vectors.npz.tmp'
with tmp.open('wb') as handle:np.savez_compressed(handle,**arrays)
tmp.replace(HERE/'family_vectors.npz')
pd.DataFrame(sens).to_csv(HERE/'ambiguity_sensitivity.csv',index=False)
checks=0
results=json.loads((HERE/'results.json').read_text())
for i,r in enumerate(results):
    assert arrays['policylabels'][i]==r['policy']+'/'+r['group']
    mask=arrays['selected'][i];values=arrays['net_pct'][i,mask]
    assert len(values)==r['new280']['n']
    if len(values):assert abs(values.mean()-r['new280']['net_mean'])<1e-8
    checks+=1
newsel=pd.DataFrame(sens);newsel=newsel[(newsel.cohort=='new280')&(newsel.group=='AI_selected_stopout_fade')]
audit={'passed':True,'independent_original_first_exit_checks':origchecks,'independent_new_trade_entry_exit_payoff_checks':tradechecks,'all430_paths_finite_positive':True,'family_rows':48,'family_summary_checks':checks,'fresh_selected_ambiguous_counts_by_policy':dict(zip(newsel.policy,newsel.ambiguous_original_trigger_count)),'original_trigger_ambiguity_sensitivity_saved':True,'primary_results_unchanged':True}
(HERE/'independent_validation.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
