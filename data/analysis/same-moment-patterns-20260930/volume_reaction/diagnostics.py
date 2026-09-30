from pathlib import Path
import json,sys,hashlib
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run import bootstrap,save,sha,ROOT

def main():
    w=pd.read_csv(HERE/'features.csv');w.entry_time=pd.to_datetime(w.entry_time)
    p=np.load(ROOT/'data/analysis/new-angles-20260930/target_exhaustion/paths.npz')['paths']
    v=np.load(HERE/'vectors.npz');names=list(v['policies']);base=names.index('quiet_up_extension_short__noAI');selected=v['selected'][:,base];coverage=v['coverage']
    geometry=coverage&((w.early_close-w.early_open).to_numpy()>=.5*w.early_open.to_numpy()*w.atr14_pct.to_numpy()/100)
    short0=-100*(p[:,150,3]/p[:,31,0]-1)
    defs=[('up_geometry_only_short',geometry,short0,-1,31,150),('unconditional_delayed_short',coverage,short0,-1,31,150)]
    for delay in [1,5]:defs.append((f'quiet_up_short_delay{delay}',selected,-100*(p[:,150+delay,3]/p[:,31+delay,0]-1),-1,31+delay,150+delay))
    defs += [('quiet_up_short_AI_SHORT',selected&w.action.eq('short').to_numpy(),short0,-1,31,150),('quiet_up_short_AI_LONG',selected&w.action.eq('long').to_numpy(),short0,-1,31,150)]
    longsel=v['selected'][:,names.index('quiet_down_extension_long__noAI')]&w.action.eq('long').to_numpy()
    defs += [('quiet_down_long_AI_LONG',longsel,-short0,1,31,150)]
    y=np.column_stack([np.where(mask,ret,0) for _,mask,ret,_,_,_ in defs]);mask=np.column_stack([mask for _,mask,_,_,_,_ in defs])
    draw,weights=bootstrap(y,mask.astype(float),w.quarter,v['quarter_weights'])
    opp,_=bootstrap(y,np.tile(coverage[:,None],(1,len(defs))),w.quarter,weights)
    summary=[];ledger=[]
    for j,(name,m,ret,side,entry,exit) in enumerate(defs):
        rr=ret[m];temp=pd.DataFrame({'time':w.entry_time,'y':y[:,j],'n':m.astype(int)}).groupby('time')[['y','n']].sum();best=temp[temp.n>0].nlargest(3,'y').index
        ex=m&~w.entry_time.isin(best).to_numpy()
        halves=[ret[m&w.half.eq(h).to_numpy()].mean() for h in [1,2]]
        summary.append(dict(policy=name,post_score=True,trades=int(m.sum()),blocks=w.loc[m,'entry_time'].nunique(),gross_mean_pct=rr.mean(),median_pct=np.median(rr),win_rate=(rr>0).mean(),worst_pct=rr.min(),best_pct=rr.max(),opportunity_mean_pct=y[:,j].sum()/coverage.sum(),without_best3_blocks_pct=ret[ex].mean(),halves=halves,quarter95_ci_pct=np.nanquantile(draw[:,j],[.025,.975])))
        for i in range(len(w)):
            ledger.append(dict(policy=name,window_id=w.window_id[i],asset=w.asset[i],cohort=w.cohort[i],original_entry_time=str(w.entry_time[i]),AI_action=w.action[i],selected=bool(m[i]),coverage=bool(coverage[i]),side=side,entry_time=str(w.entry_time[i]+pd.Timedelta(minutes=entry-1)) if m[i] else None,exit_time=str(w.entry_time[i]+pd.Timedelta(minutes=exit)) if m[i] else None,entry_price=p[i,entry,0] if m[i] else None,exit_price=p[i,exit,3] if m[i] else None,gross_pct=ret[i] if m[i] else None,opportunity_gross_pct=y[i,j] if coverage[i] else None))
    comp=[]
    for j in [0,1]:
        delta=v['opportunity_bootstrap'][:,base]-opp[:,j]
        comp.append(dict(candidate=names[base],control=defs[j][0],post_score=True,candidate_trades=int(selected.sum()),control_trades=int(mask[:,j].sum()),opportunity_difference_pp=(v['returns'][:,base]-y[:,j]).sum()/coverage.sum(),quarter95_ci_pp=np.nanquantile(delta,[.025,.975]),two_comparison_simultaneous_ci_pp=np.nanquantile(delta,[.0125,.9875])))
    save('diagnostics_summary.json',summary);save('diagnostics_comparisons.json',comp)
    pd.DataFrame(ledger).to_csv(HERE/'diagnostics_trade_ledger.csv',index=False)
    np.savez_compressed(HERE/'diagnostics_vectors.npz',policies=np.array([d[0] for d in defs]),returns=y,selected=mask,coverage=coverage,quarter_bootstrap=draw,opportunity_bootstrap=opp)
    print(pd.DataFrame(summary)[['policy','trades','gross_mean_pct','without_best3_blocks_pct']].to_string(index=False))
    print(json.dumps(comp,default=lambda x:x.tolist(),indent=2))

if __name__=='__main__':main()
