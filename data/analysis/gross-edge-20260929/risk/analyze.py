from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'data/analysis/reversal-deep-20260929/risk'
P=json.loads((R/'fresh_grid/policies.json').read_text());origids=np.array([p['policy_id'] for p in P]);oldw=pd.read_csv(R/'windows.csv');neww=pd.read_csv(R/'fresh_grid/windows.csv');old=np.load(R/'all_trade_results.npz')['gross_pct'][origids];new=np.load(R/'fresh_grid/all_trade_results.npz')['gross_pct']

def metrics(x,ids,w):
 x=np.asarray(x);ids=np.asarray(ids);order=np.argsort(w.iloc[ids].entry_time.to_numpy());z=x[order];n=len(x)
 if not n:return {'n':0}
 out={'n':n,'mean_gross_pct':x.mean(),'median_gross_pct':np.median(x),'gross_win_rate':(x>0).mean(),'profit_factor_gross':x[x>0].sum()/-x[x<0].sum() if (x<0).any() else None,'worst_gross_pct':x.min(),'best_gross_pct':x.max(),'gross_without_best3_pct':np.sort(x)[:-3].mean() if n>3 else None,'best3_share_of_total_gross':np.sort(x)[-3:].sum()/x.sum() if abs(x.sum())>1e-12 else None,'gross_sd_pct':x.std(ddof=1) if n>1 else None}
 mid=n//2
 for name,v in [('early',z[:mid]),('late',z[mid:])]:out[name+'_n']=len(v);out[name+'_gross_pct']=v.mean() if len(v) else None
 for j,v in enumerate(np.array_split(z,3)):out['third'+str(j+1)+'_n']=len(v);out['third'+str(j+1)+'_gross_pct']=v.mean() if len(v) else None
 return out

def main():
 summ=[]
 for dataset,w,G in [('old150',oldw,old),('newer280',neww,new)]:
  N=len(w);groups={'all':np.ones(N,bool),'above_both':w.above_both.to_numpy(),'below_both':w.below_both.to_numpy()};rev=w.ai_action.eq('long').astype(int).to_numpy().copy();comb=[]
  for gate,gm in groups.items():
   for s in ['reverse_all','reverse_long_to_short','reverse_short_to_long','always_long','always_short']:
    ds=rev.copy();m=gm.copy()
    if s=='reverse_long_to_short':m &= w.ai_action.eq('long').to_numpy()
    if s=='reverse_short_to_long':m &= w.ai_action.eq('short').to_numpy()
    if s=='always_long':ds[:]=0
    if s=='always_short':ds[:]=1
    ids=np.flatnonzero(m);comb.append((gate,s,ids,ds,int(gm.sum())))
  for pi,p in enumerate(P):
   for gate,s,ids,ds,eligible in comb:
    x=G[pi,ids,ds[ids]];out={'dataset':dataset,**p,'gate':gate,'strategy':s,**metrics(x,ids,w),'eligible_windows':eligible,'sample_windows':N,'frequency_all_windows':len(ids)/N,'frequency_gate_eligible':len(ids)/eligible if eligible else None,'mean_gross_per_eligible_pct':x.sum()/eligible if eligible else None}
    if dataset=='old150':
     for label in ['original100','latest50']:
      sub=w.iloc[ids].batch.eq(label).to_numpy();out[label+'_n']=int(sub.sum());out[label+'_gross_pct']=x[sub].mean() if sub.any() else None
    summ.append(out)
 out=pd.DataFrame(summ);out.to_csv(H/'risk_gross_all_trials.csv',index=False);a=out[out.dataset=='old150'].drop(columns='dataset');b=out[out.dataset=='newer280'].drop(columns='dataset');d=a.merge(b,on=['policy_id','unit','stop','ratio','horizon','gate','strategy'],suffixes=('_old','_new'),validate='one_to_one')
 sub=d[(d.n_old>=20)&(d.n_new>=40)&d.strategy.str.startswith('reverse')].copy();halfcols=[f'{s}_gross_pct_{dataset}' for dataset in ['old','new'] for s in ['early','late']];thirdcols=[f'third{j}_gross_pct_{dataset}' for dataset in ['old','new'] for j in [1,2,3]];sub['min_half_gross_pct']=sub[halfcols].min(axis=1);sub['min_third_gross_pct']=sub[thirdcols].min(axis=1);sub['all_halves_positive']=sub.min_half_gross_pct>1e-10;sub['all_thirds_positive']=sub.min_third_gross_pct>1e-10;sub['both_exbest3_positive']=(sub.gross_without_best3_pct_old>1e-10)&(sub.gross_without_best3_pct_new>1e-10)
 sub.sort_values(['all_halves_positive','all_thirds_positive','both_exbest3_positive','min_third_gross_pct','min_half_gross_pct'],ascending=False).to_csv(H/'risk_gross_ranked.csv',index=False);d.to_csv(H/'risk_gross_old_new.csv',index=False)
 cols=['policy_id','unit','stop','ratio','horizon','gate','strategy','n_old','n_new','mean_gross_pct_old','mean_gross_pct_new','min_half_gross_pct','min_third_gross_pct','gross_without_best3_pct_old','gross_without_best3_pct_new']
 stable=sub[sub.all_halves_positive&sub.all_thirds_positive&sub.both_exbest3_positive];print('STABLE',len(stable));print(stable.sort_values('min_third_gross_pct',ascending=False)[cols].head(35).to_string(index=False),flush=True)
 # Hedge family: values are saved gross returns, not net with an assumed fixed shift.
 hedge=[];HP=json.loads((R/'hedge_study/policies.json').read_text());HW=pd.read_csv(R/'hedge_study/windows.csv')
 for dataset in ['old150','fresh280']:
  w=HW[HW.dataset==dataset].reset_index(drop=True);A=np.load(R/f'hedge_study/{dataset}_payoffs.npz')
  for p in HP:
   i=p['policy_id'];ids=np.flatnonzero(A['active'][i])
   for unit,key in [('SOL_notional','gross_SOL_notional_pct'),('total_gross_notional','gross_total_notional_pct')]:
    x=A[key][i,ids];hedge.append({'dataset':dataset,**p,'units':unit,**metrics(x,ids,w),'sample_windows':len(w),'frequency_all_windows':len(ids)/len(w)})
 pd.DataFrame(hedge).to_csv(H/'hedge_gross_all_trials.csv',index=False)
 summary={'fee_assumption':0,'all_data_is_discovery':True,'risk_policies':len(P),'eligible_reversal_cells':len(sub),'positive_four_halves':int(sub.all_halves_positive.sum()),'positive_all_six_thirds':int(sub.all_thirds_positive.sum()),'positive_halves_thirds_exbest3':len(stable),'hedge_strategy_cells':16,'hedge_controls':12,'hedge_notional_conventions':2,'model_calls':0}
 (H/'analysis_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
