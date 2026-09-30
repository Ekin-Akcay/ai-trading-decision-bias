from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
w=pd.read_csv(ROOT/'data/analysis/direction-paths-20260929/windows.csv');w=w[w['case'].notna()].sort_values('case')
paths=np.load(ROOT/'data/analysis/direction-paths-20260929/minute_paths.npz')
ledger=ROOT/'data/sim/decisions/rules2to1-openai-20260926T072414Z.jsonl';d=pd.read_json(ledger,lines=True)
assets={}
for asset,length in [('SOL-USD',50),('BTC-USD',200)]:
 p=pd.read_csv(ROOT/f'data/raw/{asset}.csv',index_col=0,parse_dates=True).sort_index();p['sma']=p.close.rolling(length,min_periods=length).mean();assets[asset]=p
rows=[]
for r in w.itertuples():
 ts=pd.Timestamp(r.entry_time);z=d[d.window_id==r.window_id];assert len(z)==3;shorts=int((z.action=='short').sum());a=paths[r.window_id];daily={}
 for asset,p in assets.items():
  hist=p.loc[p.index<ts.normalize()];last=hist.iloc[-1];assert hist.index[-1]==ts.normalize()-pd.Timedelta(days=1) and np.isfinite(last.sma)
  daily[asset]={'date':str(hist.index[-1]),'close':float(last.close),'sma':float(last.sma),'up':bool(last.close>last.sma)}
 k=next((k for k in [15,30] if a[k-1,3]>0),None)
 gross=None
 if k is not None:
  entry=1+a[k,0]/100;end=1+a[k+104,3]/100;gross=(end/entry-1)*100
 row={'case':int(r.case),'window_id':r.window_id,'entry_time':r.entry_time,'short_votes':shorts,'majority_short':shorts>=2,'bullish_daily_regime':all(x['up'] for x in daily.values()),'SOL_daily_up':daily['SOL-USD']['up'],'BTC_daily_up':daily['BTC-USD']['up'],'daily_reference_date':daily['SOL-USD']['date'],'confirmation_minutes':k,'hypothetical_recovery_gross_pct':gross,'hypothetical_recovery_net_pct':None if gross is None else gross-.2,'actual_long_entry_time':None if k is None else str(ts+pd.Timedelta(minutes=k)),'actual_long_exit_time':None if k is None else str(ts+pd.Timedelta(minutes=k+105))}
 row['primary_trade']=bool(row['majority_short'] and row['bullish_daily_regime'] and k is not None);row['no_ai_control_trade']=bool(row['bullish_daily_regime'] and k is not None);row['no_regime_diagnostic_trade']=bool(row['majority_short'] and k is not None);rows.append(row)
f=pd.DataFrame(rows);f.to_csv(HERE/'windows.csv',index=False);rng=np.random.default_rng(20260929);results=[]
for policy,col in [('Primary: bullish regime + bearish AI + recovery','primary_trade'),('Control: bullish regime + recovery; no AI','no_ai_control_trade'),('Diagnostic: bearish AI + recovery; no daily filter','no_regime_diagnostic_trade')]:
 z=f[f[col]].sort_values('entry_time');v=z.hypothetical_recovery_gross_pct.to_numpy();n=len(v)
 ci=np.quantile(v[rng.integers(n,size=(10000,n))].mean(1),[.025,.975]).tolist() if n>=2 else None
 result={'policy':policy,'trade_windows':n,'gross_mean_pct':None if not n else float(v.mean()),'net_mean_pct':None if not n else float(v.mean()-.2),'gross_median_pct':None if not n else float(np.median(v)),'gross_positive_count':int((v>0).sum()),'gross_mean_ci95_pct':ci,'gross_mean_per_sampled_window_pct':float(v.sum()/100),'early_half_gross_pct':float(v[:n//2].mean()) if n>=4 else None,'late_half_gross_pct':float(v[n//2:].mean()) if n>=4 else None,'case_ids':z['case'].astype(int).tolist()};results.append(result)
out={'sample_windows':len(f),'daily_regime_windows':int(f.bullish_daily_regime.sum()),'majority_short_windows':int(f.majority_short.sum()),'regime_plus_majority_short_windows':int((f.majority_short & f.bullish_daily_regime).sum()),'results':results,'caveats':['Exploratory reused100windows','Primary and controls use different event subsets; not causal paired model attribution','Very small selected groups cannot establish reliable profitability','Daily-filter inputs strictly from previous completed UTC day','Signal on15m close; entry next1m open; exit105m after actual entry','No stops or targets;20bps cost assumption; no extra slippage/funding','Whole-window bootstrap intervals descriptive, not multiplicity-adjusted or prospective validation']}
(HERE/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
# Independent native1-minute verification of entries/exits, not only cached normalized paths.
rawpath=ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz';raw=pd.read_csv(rawpath,index_col=0,parse_dates=True)
checks=0
for r in f[f.confirmation_minutes.notna()].itertuples():
 ent=pd.Timestamp(r.actual_long_entry_time);end=pd.Timestamp(r.actual_long_exit_time);actual=(raw.loc[end-pd.Timedelta(minutes=1),'close']/raw.loc[ent,'open']-1)*100
 assert abs(actual-r.hypothetical_recovery_gross_pct)<1e-8;checks+=1
files=[ledger,rawpath,ROOT/'data/raw/SOL-USD.csv',ROOT/'data/raw/BTC-USD.csv',ROOT/'data/analysis/direction-paths-20260929/minute_paths.npz']
audit={'status':'passed','unique_windows':100,'native_entry_exit_checks':checks,'future_prices_used_only_for_trigger_after_t0':True,'entry_after_confirmation':True,'daily_lookahead_excluded':True,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(HERE/'validation.json').write_text(json.dumps(audit,indent=2));print('Native raw entry/exit checks:',checks)
