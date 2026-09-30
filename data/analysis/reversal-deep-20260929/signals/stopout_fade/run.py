from pathlib import Path
import hashlib,json,itertools
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];RESEARCH=HERE.parents[1]
pointer=json.loads((RESEARCH/'run.json').read_text());RUN=Path(pointer['run_dir'])
assert (RUN/'ALLOW_EVALUATION').exists()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
    if isinstance(v,(np.integer,)):return int(v)
    if isinstance(v,(np.bool_,)):return bool(v)
    if isinstance(v,(float,np.floating)):return float(v) if np.isfinite(v) else None
    return v
def save(name,v):(HERE/name).write_text(json.dumps(clean(v),indent=2,allow_nan=False)+'\n')

def first_exit(path,start,count,entry,sign,stop_fraction):
    """Return first-exit record. A normal both-hit minute is an adverse stop."""
    end=start+count;assert len(path)>=end and stop_fraction>0
    sl=entry*(1-sign*stop_fraction);tp=entry*(1+sign*2*stop_fraction)
    for k in range(start,end):
        op,hi,lo,cl=path[k]
        adverse_open=(op<=sl) if sign==1 else (op>=sl)
        target_open=(op>=tp) if sign==1 else (op<=tp)
        hit_stop=(lo<=sl) if sign==1 else (hi>=sl)
        hit_target=(hi>=tp) if sign==1 else (lo<=tp)
        if adverse_open:return {'outcome':'sl_gap','exit_px':op,'bar':k,'held':k-start+1}
        if target_open:return {'outcome':'tp_gap_capped','exit_px':tp,'bar':k,'held':k-start+1}
        if hit_stop:return {'outcome':'sl_ambiguous' if hit_target else 'sl','exit_px':sl,'bar':k,'held':k-start+1}
        if hit_target:return {'outcome':'tp','exit_px':tp,'bar':k,'held':k-start+1}
    return {'outcome':'timeout','exit_px':path[end-1,3],'bar':end-1,'held':count}

sources=[ROOT/'data/sim/decisions/rules2to1-openai-20260926T072414Z.jsonl',ROOT/'data/sim/decisions/reversal-terra50-20260929T184044Z.jsonl',RUN/'manifest.json',RUN/'accepted_decisions.jsonl',ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',HERE/'PLAN.md']
hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
rows=[]
for subgroup,file in [('original100',sources[0]),('latest50',sources[1])]:
    for line in file.read_text().splitlines():
        r=json.loads(line)
        if r['model']!='gpt-5.6-terra-agent':continue
        rows.append({**r,'cohort':'old150','subcohort':subgroup,'entry_time':str(pd.Timestamp(r['window_end_ts'])+pd.Timedelta(minutes=15))})
manifest=json.loads((RUN/'manifest.json').read_text());decisions=sorted([json.loads(x) for x in (RUN/'accepted_decisions.jsonl').read_text().splitlines()],key=lambda x:x['case'])
assert len(decisions)==280
for w,r in zip(manifest['cases'],decisions):
    assert w['case']==r['case'];rows.append({**w,**r['decision'],'cohort':'new280','subcohort':'new280'})
meta=pd.DataFrame(rows).sort_values(['cohort','case']).reset_index(drop=True)
assert len(meta)==430 and meta.window_id.nunique()==430 and (meta.cohort=='new280').sum()==280
meta['entry_time']=pd.to_datetime(meta.entry_time)
px=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_1m.csv.gz',index_col=0,parse_dates=True).sort_index()
aa=px[['open','high','low','close']].to_numpy();q=px.index.get_indexer(meta.entry_time);assert (q>0).all()
paths=np.array([aa[k:k+480] for k in q]);assert paths.shape==(430,480,4)
assert np.isfinite(paths).all() and (paths>0).all()
assert np.allclose(aa[q-1,3],meta.price_real,atol=1e-8,rtol=0)
for k in q:
    span=px.index[k-1:k+480];assert len(span)==481 and np.all(np.diff(span.as_unit('ns').asi8)==60_000_000_000)
keep=['case','window_id','cohort','subcohort','entry_time','price_real','action','stop_pct','atr14_pct','ma20_now','ma50_now','confidence']
meta[keep].to_csv(HERE/'windows.csv',index=False)
policies=[{'policy':f'{i:02d}_{side}_wait{wait}_hold{hold}_{exitkind}','side':side,'max_wait':wait,'hold':hold,'exit':exitkind} for i,(side,wait,hold,exitkind) in enumerate(itertools.product(['long','short'],[105,240],[60,240],['time','ATR1_RR2']),1)]
assert len(policies)==16;save('policies.json',policies)

# Edge-case verification uses only synthetic arrays, covering all conservative fills.
assert first_exit(np.array([[100,103,97,100]],float),0,1,100,1,.01)['outcome']=='sl_ambiguous'
assert first_exit(np.array([[98,100,97,99]],float),0,1,100,1,.01)['exit_px']==98
assert first_exit(np.array([[103,104,102,103]],float),0,1,100,1,.01)['exit_px']==102
assert first_exit(np.array([[100,102,97,100]],float),0,1,100,-1,.01)['outcome']=='sl_ambiguous'
assert first_exit(np.array([[102,103,101,102]],float),0,1,100,-1,.01)['exit_px']==102
assert first_exit(np.array([[97,98,96,97]],float),0,1,100,-1,.01)['exit_px']==98

trigger_cache={};results=[];ledger=[];matrix=[];rng=np.random.default_rng(2026092971)
def st(values,indices,ci=False):
    values=np.asarray(values,float);indices=np.asarray(indices,int);v=values[indices];v=v[np.isfinite(v)];n=len(v)
    if not n:return {'n':0}
    net=v-.2
    result={'n':n,'gross_mean':v.mean(),'net_mean':net.mean(),'net30_mean':v.mean()-.3,'median_net':np.median(net),'gross_wins':int((v>0).sum()),'net_wins':int((net>0).sum()),'gross_winrate':(v>0).mean(),'net_winrate':(net>0).mean(),'profit_factor_net':net[net>0].sum()/-net[net<0].sum() if (net<0).any() else None,'net_excluding_best1':np.sort(net)[:-1].mean() if n>1 else None,'net_excluding_best3':np.sort(net)[:-3].mean() if n>3 else None,'worst_gross':v.min(),'best_gross':v.max(),'mean_gross_winner':v[v>0].mean() if (v>0).any() else None,'mean_gross_loser':v[v<0].mean() if (v<0).any() else None}
    if ci and n>=2:
        boot=net[rng.integers(n,size=(10000,n))].mean(1);result['net_ci95']=np.quantile(boot,[.025,.975])
    return result

for policy in policies:
    sign=1 if policy['side']=='long' else -1
    for width in ['AI_width','ATR_width']:
        gross=np.full(430,np.nan);trigger=np.zeros(430,bool);stop_first=np.zeros(430,bool)
        for i,r in meta.iterrows():
            key=(i,sign,policy['max_wait'],width)
            if key not in trigger_cache:
                fraction=r.stop_pct if width=='AI_width' else r.atr14_pct/100
                trigger_cache[key]=first_exit(paths[i],0,policy['max_wait'],r.price_real,sign,fraction)
            original=trigger_cache[key];stopped=original['outcome'].startswith('sl');stop_first[i]=stopped
            actualselected=stopped and r.action==policy['side']
            row={'policy':policy['policy'],'width':width,'case':int(r['case']),'window_id':r.window_id,'cohort':r.cohort,'subcohort':r.subcohort,'ai_action':r.action,'strategy_side':policy['side'],'signal_time':str(r.entry_time),'original_first_outcome':original['outcome'],'ambiguous_original_trigger':original['outcome']=='sl_ambiguous','original_first_bar':original['bar'],'original_exit_price':original['exit_px'],'stop_first':stopped,'AI_selected':actualselected}
            if stopped:
                k=original['bar']+1;newentry=float(paths[i,k,0]);assert 1<=k<=policy['max_wait']
                if policy['exit']=='time':out={'outcome':'time','exit_px':paths[i,k+policy['hold']-1,3],'bar':k+policy['hold']-1,'held':policy['hold']}
                else:out=first_exit(paths[i],k,policy['hold'],newentry,sign,r.atr14_pct/100)
                gross[i]=sign*(out['exit_px']/newentry-1)*100;trigger[i]=True
                row.update(trigger_bar_open_time=str(r.entry_time+pd.Timedelta(minutes=original['bar'])),trigger_bar_close_time=str(r.entry_time+pd.Timedelta(minutes=k)),entry_time=str(r.entry_time+pd.Timedelta(minutes=k)),entry_price=newentry,exit_minute_close_time=str(r.entry_time+pd.Timedelta(minutes=out['bar']+1)),exit_price=out['exit_px'],held_minutes=out['held'],strategy_outcome=out['outcome'],gross_pct=gross[i],net20_pct=gross[i]-.2,net30_pct=gross[i]-.3)
                assert row['entry_time']==row['trigger_bar_close_time'] and out['bar']+1<=480
            ledger.append(row)
        side_mask=(meta.action.to_numpy()==policy['side'])
        if width=='AI_width':
            groups=[('AI_selected_stopout_fade',trigger & side_mask),('AI_width_control_not_AI_free',trigger)]
        else:groups=[('ATR_width_price_only_control',trigger)]
        for label,mask in groups:
            entry={'policy':policy['policy'],'group':label,**policy}
            cohorts={}
            for cohort in ['old150','new280']:
                ids=np.flatnonzero(mask & (meta.cohort==cohort).to_numpy());ids=ids[np.argsort(meta.iloc[ids].entry_time.to_numpy())]
                mid=len(ids)//2;part=st(gross,ids,True)
                part['halves']=[st(gross,j) for j in [ids[:mid],ids[mid:]]]
                part['thirds']=[st(gross,j) for j in np.array_split(ids,3)]
                part['net_per_opportunity']=float(np.nansum(np.where(mask & (meta.cohort==cohort).to_numpy(),gross-.2,0))/(150 if cohort=='old150' else 280))
                cohorts[cohort]=part
            entry.update(cohorts);results.append(entry)
            fresh=(meta.cohort=='new280').to_numpy();matrix.append({'label':policy['policy']+'/'+label,'gross':gross[fresh],'mask':mask[fresh]})

assert len(results)==48 and len(ledger)==16*430*2
for i in range(0,len(results),3):
    a,ai_control,atr_control=results[i:i+3]
    assert a['group']=='AI_selected_stopout_fade'
    old=a['old150'];new=a['new280'];ctrl=ai_control['new280'];atr=atr_control['new280']
    a['fresh_increment_vs_AI_width_control']=new.get('net_mean',np.nan)-ctrl.get('net_mean',np.nan)
    a['fresh_increment_vs_ATR_price_control']=new.get('net_mean',np.nan)-atr.get('net_mean',np.nan)
    screen={'old_n20':old['n']>=20,'fresh_n40':new['n']>=40,'old_net_positive':old.get('net_mean',-999)>0,'fresh_net_positive':new.get('net_mean',-999)>0,'fresh30bps_positive':new.get('net30_mean',-999)>0,'halves_positive':all(x.get('net_mean',-999)>0 for x in new['halves']),'thirds_positive':all(x.get('net_mean',-999)>0 for x in new['thirds']),'best3_removal_positive':new.get('net_excluding_best3',-999)>0 if new['n']>3 else False,'beats_AI_width_control':a['fresh_increment_vs_AI_width_control']>0}
    a['screen']=screen;a['passes_screen']=all(screen.values())
save('results.json',results)
flat=[]
for r in results:
    f={k:v for k,v in r.items() if not isinstance(v,(dict,list))}
    for cohort in ['old150','new280']:
        f.update({cohort+'_'+k:v for k,v in r[cohort].items() if not isinstance(v,(dict,list,np.ndarray))})
        for n,t in enumerate(r[cohort]['thirds'],1):f[f'{cohort}_third{n}_net']=t.get('net_mean')
        for n,t in enumerate(r[cohort]['halves'],1):f[f'{cohort}_half{n}_net']=t.get('net_mean')
        ci=r[cohort].get('net_ci95',[None,None]);f[cohort+'_ci_low']=ci[0];f[cohort+'_ci_high']=ci[1]
    flat.append(f)
table=pd.DataFrame(flat);table.to_csv(HERE/'results.csv',index=False)
pd.DataFrame(ledger).to_csv(HERE/'all_window_paths.csv.gz',index=False)
freshmeta=meta[meta.cohort=='new280'];assert freshmeta.case.tolist()==list(range(1,281))
np.savez_compressed(HERE/'family_vectors.npz',net_pct=np.array([m['gross']-.2 for m in matrix]),gross_pct=np.array([m['gross'] for m in matrix]),selected=np.array([m['mask'] for m in matrix]),policylabels=np.array([m['label'] for m in matrix]),window_id=freshmeta.window_id.to_numpy(dtype=str),case=freshmeta.case.to_numpy(),entry_time=freshmeta.entry_time.astype(str).to_numpy(dtype=str))
audit={'passed':True,'exploratory_reuse_not_holdout':True,'policies':16,'policies_with_controls':48,'windows':430,'old':150,'new':280,'rows_in_path_ledger':len(ledger),'maximum_elapsed_minutes':480,'SL_before_original_TP_required':True,'gap_stop_actual_and_target_capped':True,'normal_bar_both_hit_stop_first':True,'new_position_enters_after_trigger_bar_close':True,'synthetic_edge_cases_passed':6,'new_model_calls':0,'source_sha256':hashes,'source_hashes_still_match':all(sha(ROOT/p)==h for p,h in hashes.items()),'candidate_screen_passes':int(table.passes_screen.fillna(False).sum())}
assert audit['source_hashes_still_match'];save('audit.json',audit)
show=['policy','old150_n','old150_net_mean','new280_n','new280_net_mean','new280_net30_mean','new280_third1_net','new280_third2_net','new280_third3_net','new280_net_excluding_best3','new280_ci_low','fresh_increment_vs_AI_width_control','passes_screen']
print(table[table.group=='AI_selected_stopout_fade'].sort_values('new280_net_mean',ascending=False)[show].to_string(index=False));print('Screen passes:',audit['candidate_screen_passes'])
