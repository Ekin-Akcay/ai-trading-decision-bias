"""Reconstruct uncensored future paths from canonical, immutable decision ledgers."""
from pathlib import Path
import json,hashlib,re
from collections import Counter
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
HORIZONS=[1,5,15,30,45,60,75,90,105,120,180,240,360,720,1440]
MAIN=['claude-haiku-agent','claude-sonnet-agent','gpt-5.6-luna-agent','gpt-5.6-terra-agent','gpt-6-astra-agent']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str,allow_nan=False))
def run():
    canonical=json.loads((ROOT/'data/sim/rules2to1/window_list.json').read_text())
    case_map={c['window_id']:c['case'] for c in canonical}
    allrows=[];inventory=[];hashes={}
    for p in sorted((ROOT/'data/sim/decisions').glob('*.jsonl')):
        rows=[json.loads(s) for s in p.read_text().splitlines() if s.strip()]
        inventory.append({'file':str(p.relative_to(ROOT)),'rows':len(rows),'models':dict(Counter(r['model'] for r in rows))})
        hashes[str(p.relative_to(ROOT))]=sha(p)
        for line,r in enumerate(rows,1):
            if not r['model'].endswith('-agent'):continue
            r=dict(r);r['source_file']=str(p.relative_to(ROOT));r['source_line']=line
            r['protocol']='v2' if r.get('prompt_version','').endswith('2to1-noflat') else 'v1'
            r['case']=case_map.get(r['window_id']);r['main']=r['window_id'] in case_map and r['model'] in MAIN
            r['sign']={'long':1,'short':-1,'flat':0}.get(r['action'],np.nan)
            r['decision_id']=f"{r['protocol']}:{r['model']}:{r['window_id']}"
            allrows.append(r)
    d=pd.DataFrame(allrows);assert d['decision_id'].is_unique
    assert len(d[d.main])==1000
    windows=d.drop_duplicates('window_id').copy();arrays={};windowrows=[];quality=[]
    for asset,group in windows.groupby('asset'):
        p=ROOT/f'data/raw/intraday/{asset}_1m.csv.gz';hashes[str(p.relative_to(ROOT))]=sha(p)
        minute=pd.read_csv(p,index_col=0,parse_dates=True).sort_index()
        p15=ROOT/f'data/raw/intraday/{asset}_15m.csv.gz';hashes[str(p15.relative_to(ROOT))]=sha(p15)
        bars=pd.read_csv(p15,index_col=0,parse_dates=True).sort_index()
        assert minute.index.is_unique and bars.index.is_unique
        for _,r in group.iterrows():
            ts=pd.Timestamp(r.window_end_ts);start=ts+pd.Timedelta(minutes=15)
            entry=float(minute.loc[start-pd.Timedelta(minutes=1),'close'])
            assert abs(entry-float(r.price_real))<1e-8
            for v in d.loc[d.window_id==r.window_id,'entry_price'].dropna():assert abs(entry-v)<1e-8
            index=pd.date_range(start,periods=1440,freq='min');future=minute.reindex(index)
            valid=future[['open','high','low','close']].notna().all(axis=1).to_numpy()
            # A horizon is valid only if ALL required minutes exist, without shifting gaps.
            ret=(future[['open','high','low','close']].to_numpy()/entry-1)*100
            close=ret[:,3];high=ret[:,1];low=ret[:,2]
            arrays[r.window_id]=ret
            past=bars.loc[:ts].tail(200);vis=past.tail(int(r.visible_bars))
            assert abs(float(vis.close.iloc[-1])-entry)<1e-8
            atr=float(r.atr14_pct)
            fields={k:r[k] for k in ['window_id','asset','window_end_ts','price_real','atr14_pct','ret_vis_pct','ma20_now','ma50_now','vol24_ratio','sigma_vis_pct']}
            fields.update(case=case_map.get(r.window_id),entry_time=str(start),entry_date=str(start.date()),year=start.year,
                          above20=100>=r.ma20_now,above50=100>=r.ma50_now,
                          ma20dist_atr=(100-r.ma20_now)/atr,ma50dist_atr=(100-r.ma50_now)/atr,
                          past_move_atr=r.ret_vis_pct/atr,
                          last_bar_pct=(vis.close.iloc[-1]/vis.open.iloc[-1]-1)*100,
                          last5_pct=(vis.close.iloc[-1]/past.close.iloc[-6]-1)*100,
                          last5_volume_ratio=vis.volume.iloc[-5:].mean()/past.volume.mean(),
                          last_volume_ratio=vis.volume.iloc[-1]/past.volume.mean(),
                          ma20_slope_pct=(past.close.tail(20).mean()/past.close.iloc[-25:-5].mean()-1)*100,
                          valid_minutes=int(valid.sum()),all_1440_complete=bool(valid.all()))
            fields['ma_regime']='above_both' if fields['above20'] and fields['above50'] else 'below_both' if not fields['above20'] and not fields['above50'] else 'mixed'
            for h in HORIZONS:
                ok=valid[:h].all()
                fields[f'return_{h}m_pct']=float(close[h-1]) if ok else None
                fields[f'high_{h}m_pct']=float(high[:h].max()) if ok else None
                fields[f'low_{h}m_pct']=float(low[:h].min()) if ok else None
                fields[f'fraction_up_{h}m']=float((close[:h]>0).mean()) if ok else None
                fields[f'realized_vol_{h}m']=float(np.std(np.diff(np.r_[0,close[:h]]))*np.sqrt(h)) if ok else None
            for threshold in [.5,1.0]:
                up=high[:105]>=threshold*atr;down=low[:105]<=-threshold*atr
                ui=np.flatnonzero(up);di=np.flatnonzero(down)
                ut=int(ui[0]+1) if len(ui) else None;dt=int(di[0]+1) if len(di) else None
                fields[f'first_up_{threshold}atr_minutes']=ut;fields[f'first_down_{threshold}atr_minutes']=dt
                fields[f'first_touch_{threshold}atr']=('neither' if ut is None and dt is None else 'up' if dt is None else 'down' if ut is None else 'ambiguous' if ut==dt else 'up' if ut<dt else 'down')
            windowrows.append(fields)
            quality.append({'window_id':r.window_id,'entry_verified':True,'missing_minutes_24h':int((~valid).sum())})
        del minute,bars
    w=pd.DataFrame(windowrows).sort_values(['asset','window_end_ts']);w.to_csv(HERE/'windows.csv',index=False)
    np.savez_compressed(HERE/'minute_paths.npz',**arrays)
    overlap=[]
    for asset,g in w.groupby('asset'):
        times=pd.to_datetime(g.entry_time).to_numpy()
        for i in range(len(g)):
            for j in range(i+1,len(g)):
                dist=abs((times[i]-times[j])/np.timedelta64(1,'m'))
                if dist<1440:overlap.append({'asset':asset,'window1':g.iloc[i].window_id,'window2':g.iloc[j].window_id,'distance_minutes':float(dist)})
    merge_cols=[x for x in w if x not in d.columns or x=='window_id']
    d=d.merge(w[merge_cols],on='window_id',validate='many_to_one')
    # The following dictionary is fixed before inspecting forward path associations.
    tags={'trend':r'trend|momentum|continuation|lower highs|higher lows|lower lows|higher highs',
          'moving_average':r'\bma\d*\b|averages',
          'breakout_breakdown':r'breakout|breakdown|broke|breaks|break above|break below',
          'rejection_failure':r'reject|fail|stall',
          'support_resistance':r'support|resistance|range|consolidat',
          'weak_volume':r'low.volume|weak.volume|subdued volume|fading volume|light volume|declining volume',
          'strong_volume':r'high.volume|strong.volume|elevated volume|surging volume|rising.*volume|volume.backed',
          'reversal_exhaustion':r'reversal|reversion|exhaust|capitulat|oversold|overbought|extended'}
    for tag,pat in tags.items():d['reason_'+tag]=d.reason.fillna('').str.contains(pat,case=False,regex=True)
    outrows=[]
    for _,r in d.iterrows():
        z=r.to_dict();a=arrays[r.window_id];s=r.sign;atr=r.atr14_pct
        z['stop_atr']=r.stop_pct*100/atr;z['tp_atr']=r.tp_pct*100/atr
        z['agrees_visible_trend']=bool(s==np.sign(r.ret_vis_pct)) if s else None
        z['agrees_ma20']=bool(s==(1 if r.above20 else -1)) if s else None
        z['agrees_ma50']=bool(s==(1 if r.above50 else -1)) if s else None
        for h in HORIZONS:
            valid=np.isfinite(a[:h]).all() and s in (-1,1)
            z[f'signed_{h}m_pct']=s*a[h-1,3] if valid else None
            z[f'signed_{h}m_atr']=s*a[h-1,3]/atr if valid else None
            z[f'correct_{h}m']=bool(s*a[h-1,3]>0) if valid and a[h-1,3]!=0 else None
            z[f'fraction_favorable_{h}m']=float((s*a[:h,3]>0).mean()) if valid else None
            z[f'mfe_{h}m_pct']=float(max(0,(a[:h,1] if s==1 else -a[:h,2]).max())) if valid else None
            z[f'mae_{h}m_pct']=float(min(0,(a[:h,2] if s==1 else -a[:h,1]).min())) if valid else None
        if s:
            close=s*a[:105,3]
            z['path_15_to_105']='correct_then_wrong' if close[14]>0 and close[104]<0 else 'wrong_then_correct' if close[14]<0 and close[104]>0 else 'correct_both' if close[14]>0 and close[104]>0 else 'wrong_both' if close[14]<0 and close[104]<0 else 'includes_zero'
            ix=np.flatnonzero(close>0);z['first_favorable_close_minutes']=int(ix[0]+1) if len(ix) else None
            z['crossings_105m']=int(np.sum(np.diff(np.sign(close))!=0))
            z['favorable_first_05atr']=('favorable' if r['first_touch_0.5atr']==('up' if s==1 else 'down') else 'adverse' if r['first_touch_0.5atr'] in ('up','down') else r['first_touch_0.5atr'])
        outrows.append(z)
    out=pd.DataFrame(outrows);out.to_csv(HERE/'decisions_enriched.csv',index=False)
    out.to_json(HERE/'decisions_enriched.jsonl',orient='records',lines=True,date_format='iso')
    save_json(HERE/'dataset_audit.json',{'ai_decisions':len(out),'unique_windows':len(w),'main_decisions':int(out.main.sum()),'main_windows':out[out.main].window_id.nunique(),'inventory':inventory,'quality':quality,'overlapping_24h_windows':overlap,'source_sha256':hashes,'entry_convention':'last visible 15m bar closes at window_end_ts+15m; exact subsequent 1m bars; unconditioned on exits','reason_tag_dictionary':tags})
    print(json.dumps({'rows':len(out),'windows':len(w),'main_rows':int(out.main.sum()),'missing_future_windows':sum(q['missing_minutes_24h']>0 for q in quality),'overlap_pairs':len(overlap),'models':{str(k):int(v) for k,v in out.groupby(['protocol','model']).size().items()}},default=str))
if __name__=='__main__':run()
