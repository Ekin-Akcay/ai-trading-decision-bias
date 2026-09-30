"""Causal bar-resolution exit replay, using updates only on subsequent bars."""
import numpy as np

CANDIDATES=['BE_after_1ATR','TRAIL_1ATR_after_1ATR','HALF_at_1ATR_then_BE']
CONTROLS=['FIXED_1ATR_stop','RAW_hold_240']
POLICIES=CANDIDATES+CONTROLS
CONTACT_EPS_MULTIPLIER=32

def replay(path,atr_pct,sign,policy,horizon=240,events=False):
    p=np.asarray(path,float);assert p.ndim==2 and p.shape[1]==4 and len(p)>horizon
    assert sign in [-1,1] and policy in POLICIES and atr_pct>0
    entry=float(p[1,0]);ez=sign*entry;R=entry*float(atr_pct)/100;stop=ez-R;target=ez+R
    # Inclusive price contacts must survive arithmetic roundoff in computed
    # levels. This is a machine-epsilon tolerance, not a tick or price buffer.
    contact_tol=CONTACT_EPS_MULTIPLIER*np.finfo(float).eps*entry
    remaining=1.;realized=0.;highwater=ez;armed=False;armed_bar=0;partial_bar=0;partial_at_open=False
    partial_price=np.nan;partial=policy=='HALF_at_1ATR_then_BE';partial_pending=partial
    partial_ambiguous=False;trigger_and_stop=False;overrun=False;adverse_open_move=False;updates=0;trace=[]
    final_price=np.nan;final_at_open=False;outcome='timeout';exit_bar=horizon
    def event(kind,k,**kw):
        if events:trace.append({'event':kind,'minute':int(k),**kw})
    for k in range(1,horizon+1):
        o,h,l,c=map(float,p[k]);oz=sign*o;fz=max(sign*h,sign*l);az=min(sign*h,sign*l)
        has_stop=policy!='RAW_hold_240'
        # The opening execution uses a level fixed no later than the previous close.
        if has_stop and oz<=stop+contact_tol:
            overrun=oz<stop-contact_tol;adverse_open_move=oz<sign*float(p[k-1,3])-contact_tol;realized+=remaining*(oz-ez)/entry*100
            final_price=o;final_at_open=True;outcome='stop_open';exit_bar=k
            event('stop_open',k,fill=o,fraction=remaining,active_stop_price=sign*stop,strictly_beyond_stop=bool(overrun),adverse_open_move_from_prior_close=bool(adverse_open_move));remaining=0.;break
        # A favorable target gap is certain at open, before a later intraminute stop.
        if partial_pending and oz>=target-contact_tol:
            realized+=.5*(target-ez)/entry*100;remaining-=.5;partial_pending=False;partial_bar=k;partial_at_open=True;partial_price=sign*target
            event('partial_target_open',k,fill=partial_price,fraction=.5,actual_open=o)
        if has_stop and az<=stop+contact_tol:
            partial_ambiguous=bool(partial_pending and fz>=target-contact_tol)
            trigger_and_stop=bool(policy in CANDIDATES and not armed and fz>=target-contact_tol)
            realized+=remaining*(stop-ez)/entry*100;final_price=sign*stop;outcome='stop_touch';exit_bar=k
            event('stop_touch',k,fill=final_price,fraction=remaining,active_stop_price=sign*stop,unfilled_partial_target_also_touched=partial_ambiguous,protection_trigger_same_bar=trigger_and_stop);remaining=0.;break
        if partial_pending and fz>=target-contact_tol:
            realized+=.5*(target-ez)/entry*100;remaining-=.5;partial_pending=False;partial_bar=k;partial_price=sign*target
            event('partial_target_touch',k,fill=partial_price,fraction=.5)
        highwater=max(highwater,fz)
        if k==horizon:
            realized+=remaining*(sign*c-ez)/entry*100;final_price=c;outcome='timeout';exit_bar=k
            event('timeout',k,fill=c,fraction=remaining);remaining=0.;break
        # No update below can affect this minute. This is essential when a bar's
        # high follows its low, or its proposed trail lies beyond its own close.
        trigger=(highwater>=target-contact_tol) if not partial else not partial_pending
        if policy in CANDIDATES and trigger:
            if not armed:armed=True;armed_bar=k;event('protection_armed',k,active_from_minute=k+1)
            proposed=highwater-R if policy=='TRAIL_1ATR_after_1ATR' else ez
            newstop=max(stop,proposed)
            if newstop>stop:
                updates+=1;event('stop_update',k,old_stop_price=sign*stop,new_stop_price=sign*newstop,active_from_minute=k+1,completed_bar_close=c)
            stop=newstop
    assert remaining==0 and np.isfinite(final_price)
    final_elapsed=exit_bar-1 if final_at_open else exit_bar
    equivalent_exit=entry*(1+sign*realized/100)
    result={'gross_pct':realized,'entry_price':entry,'final_exit_price':final_price,'weighted_equivalent_exit_price':equivalent_exit,'outcome':outcome,
        'exit_minute_index':exit_bar,'exit_elapsed_upper_minutes':final_elapsed,'exit_at_open':final_at_open,'final_active_stop_price':sign*stop if policy!='RAW_hold_240' else np.nan,
        'protection_armed':armed,'armed_after_minute':armed_bar,'stop_updates':updates,'partial_executed':partial_bar>0,'partial_minute_index':partial_bar,'partial_at_open':partial_at_open,'partial_price':partial_price,
        'partial_elapsed_upper_minutes':partial_bar-1 if partial_at_open else partial_bar,'partial_fraction':.5 if partial_bar else 0.,'ambiguous_partial_target_stop':partial_ambiguous,
        'trigger_and_stop_same_bar':trigger_and_stop,'adverse_open_overrun_of_stop':overrun,'adverse_open_move_from_previous_close':adverse_open_move}
    return (result,trace) if events else result
