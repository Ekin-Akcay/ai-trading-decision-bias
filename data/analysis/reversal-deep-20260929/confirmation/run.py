from pathlib import Path
import sys,json,itertools
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
paths=[ROOT/'data/sim/decisions/rules2to1-openai-20260926T072414Z.jsonl',ROOT/'data/sim/decisions/reversal-terra50-20260929T184044Z.jsonl']
rows=[]
for file in paths:
    for line in file.read_text().splitlines():
        r=json.loads(line)
        if r['model']=='gpt-5.6-terra-agent':r['cohort']='old100' if 'rules2to1' in file.name else 'new50';rows.append(r)
assert len(rows)==150 and len({r['window_id'] for r in rows})==150
px=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index();ix=px.index;arr=px[['open','high','low','close']].to_numpy(float);cache=[]
for r in rows:
    t=pd.Timestamp(r['window_end_ts'])+pd.Timedelta(minutes=15);p=ix.searchsorted(t)-1;entry=arr[p,3];assert abs(entry-r['price_real'])<1e-8
    assert ix[p:p+4321].equals(pd.date_range(t-pd.Timedelta(minutes=1),periods=4321,freq='min'))
    cache.append((entry,arr[p+1:p+4321].copy(),t))
def resolve(a,j,h,sign,atr,bracket):
    entry=a[j,0];future=a[j:j+h]
    if not bracket:return sign*(future[-1,3]/entry-1)*100,h,'time'
    stop=entry*(1-sign*atr/100);tp=entry*(1+sign*2*atr/100)
    for k,(o,hi,lo,c) in enumerate(future):
        if sign*(o-stop)<=0:return sign*(o/entry-1)*100,k+1,'gap_sl'
        if sign*(o-tp)>=0:return 2*atr,k+1,'gap_tp'
        sh=(lo<=stop if sign==1 else hi>=stop);th=(hi>=tp if sign==1 else lo<=tp)
        if sh:return -atr,k+1,'both_sl' if th else 'sl'
        if th:return 2*atr,k+1,'tp'
    return sign*(future[-1,3]/entry-1)*100,h,'time'
per=[];summ=[]
for threshold,wait,hold,bracket,sign in itertools.product(['atr0.5','atr1','ai_stop'],[105,240,720],[240,720,1440],[False,True],[1,-1]):
    policy=f'{threshold}_wait{wait}_hold{hold}_{"bracket" if bracket else "time"}_{"long" if sign==1 else "short"}';rr=[]
    for r,(entry,a,t) in zip(rows,cache):
        atr=r['atr14_pct'];dist=(r['stop_pct']*100 if threshold=='ai_stop' else atr*(.5 if threshold=='atr0.5' else 1));level=entry*(1+sign*dist/100)
        hits=np.flatnonzero(a[:wait,1]>=level if sign==1 else a[:wait,2]<=level)
        if not len(hits):continue
        j=int(hits[0])+1;gross,duration,out=resolve(a,j,hold,sign,atr,bracket)
        v={'policy':policy,'window_id':r['window_id'],'cohort':r['cohort'],'entry_time':str(t+pd.Timedelta(minutes=j)),'ai_selected':r['action']==('short' if sign==1 else 'long'),'side':'long' if sign==1 else 'short','trigger_minutes':j,'gross_pct':gross,'net_pct':gross-.2,'held_minutes':duration,'outcome':out,'entry_price':a[j,0]};rr.append(v);per.append(v)
    d=pd.DataFrame(rr);s=d[d.ai_selected].sort_values('entry_time');n=len(s)
    def mean(g):return float(g.net_pct.mean()) if len(g) else None
    summ.append({'policy':policy,'n':n,'gross_mean_pct':float(s.gross_pct.mean()) if n else None,'net_mean_pct':mean(s),'net_positive':int((s.net_pct>0).sum()),'ai_lift_vs_all_triggered_pct':mean(s)-mean(d) if n else None,'all_triggered_n':len(d),'all_triggered_net_pct':mean(d),'control_is_price_only':threshold!='ai_stop','old100_n':int((s.cohort=='old100').sum()),'old100_net_pct':mean(s[s.cohort=='old100']),'new50_n':int((s.cohort=='new50').sum()),'new50_net_pct':mean(s[s.cohort=='new50']),'early_net_pct':mean(s.iloc[:n//2]),'late_net_pct':mean(s.iloc[n//2:]),'ambiguous':int((s.outcome=='both_sl').sum())})
pd.DataFrame(per).to_csv(HERE/'all_trade_policies.csv',index=False);result=pd.DataFrame(summ).sort_values('net_mean_pct',ascending=False);result.to_csv(HERE/'all_policy_summaries.csv',index=False);print(result[result.n>=25].head(15).to_string(index=False));print('Policies',len(result),'rows',len(per))
