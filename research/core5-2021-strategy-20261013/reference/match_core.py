"""Allocation/risk comparison only; unchanged public CS and economic proxy."""
import numpy as np
from scripts.research.public_cross_section_momentum import public_targets
from modules.collector_research.pipeline.economics import proxy_step
DAY=86400000000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
ARMS=('CS_ORIGINAL','VOL_ORIGINAL','CS_MATCHED','VOL_MATCHED','CASH')

def match(clocks,close,decisions,vol,vol_assets):
    t=np.asarray(clocks,np.int64);p=np.asarray(close,float);d=np.asarray(decisions,np.int64);v=np.asarray(vol,float);va=np.asarray(vol_assets,bool)
    if v.shape!=(len(d),5) or va.shape!=v.shape or np.any(np.diff(d)!=DAY):raise ValueError('Full daily target calendar and CORE5 order')
    cs,diag=public_targets(p,t,d,SYMBOLS,SYMBOLS);ca=np.asarray(diag['current_eligible'],bool)
    out=dict(CS_ORIGINAL=cs,VOL_ORIGINAL=v.copy(),CS_MATCHED=np.zeros_like(cs),VOL_MATCHED=np.zeros_like(cs),CASH=np.zeros_like(cs));proof=[];state=[]
    for j,at in enumerate(d):
        k=int(np.searchsorted(t,at));status='READY'
        if k<63 or k>=len(t) or t[k]!=at or np.any(np.diff(t[k-63:k+1])!=DAY):status='MISSING_CURRENT_OR_PAST_CLOCK'
        elif not (ca[j].all() and va[j].all() and np.isfinite(p[k-30:k+1]).all() and (p[k-30:k+1]>0).all()):status='CURRENT_MEMBER_OR_PAST_RISK_UNREADY'
        if status!='READY':proof.append(dict(decision_us=int(at),status=status,common_sigma=0.));state.append('UNKNOWN');continue
        r=np.diff(p[k-30:k+1],axis=0)/p[k-30:k];c=np.cov(r,rowvar=False,ddof=1)*365
        sigma=lambda w:float(np.sqrt(max(0.,w@c@w)))
        sc,sv=sigma(cs[j]),sigma(v[j]);common=min(.10,sc,sv)
        out['CS_MATCHED'][j]=cs[j]*(common/sc) if sc>0 else 0.
        out['VOL_MATCHED'][j]=v[j]*(common/sv) if sv>0 else 0.
        if abs(sigma(out['CS_MATCHED'][j])-sigma(out['VOL_MATCHED'][j]))>1e-12:raise ValueError('Matched exante risk')
        proof.append(dict(decision_us=int(at),status=status,last_price_available_us=int(t[k]),past_return_count=30,original_CS_sigma=sc,original_VOL_sigma=sv,common_sigma=common))
        btc21=p[k,0]/p[k-21,0]-1;btc63=p[k,0]/p[k-63,0]-1
        state.append('SIDEWAYS' if abs(btc63)<.05 else ('UP' if btc21>=0 and btc63>=0 else 'PULLBACK' if btc21<0 and btc63>=0 else 'REBOUND' if btc21>=0 else 'DOWN'))
    for a,w in out.items():
        if not np.isfinite(w).all() or np.abs(w).max()>.3+1e-12 or np.abs(w).sum(1).max()>.6+1e-12:raise ValueError('Original caps/finite weights')
    return out,proof,np.array(state),diag

def quantity_reference(d,w,p0,p1,fp,good,complete,cost=.00135):
    """No reset after an owned hole; preserve last genuine state and STOP."""
    nav=10000.;q=np.zeros(5);rows=[];stop=None;lastmark=None
    for i,at in enumerate(d):
        valid=good[i]&bool(complete[i]);before=nav
        try:after,nq,fees,fund,notional,pnl=proxy_step(nav,q,w[i],p0[i],p1[i],fp[i],valid,cost)
        except ValueError as exc:stop=dict(decision_us=int(at),reason=str(exc));break
        nav,q=after,nq;lastmark=p1[i].copy();rows.append(dict(decision_us=int(at),nav_before=before,nav_after=nav,daily_return=nav/before-1,price_pnl=pnl,cost=fees,funding_cash=-fund,turnover_USDT=notional))
    paid=False;terminal=0.
    if stop is None:
        own=q!=0
        if not len(rows) or (own&(~np.isfinite(lastmark)|(lastmark<=0))).any():raise ValueError('Paid reference terminal price')
        requested=float(np.dot(np.abs(q[own]),lastmark[own]))*cost
        if not np.isfinite(nav-requested) or nav-requested<=0:
            stop=dict(decision_us=int(d[-1]),reason='TERMINAL_COST_EXHAUSTS_NAV',requested_terminal_cost_USDT=requested)
        else:
            terminal=requested;nav-=terminal;rows[-1]['nav_after']=nav;rows[-1]['cost']+=terminal;rows[-1]['daily_return']=nav/rows[-1]['nav_before']-1;q=np.zeros(5);paid=True
    status='COMPLETE_CONDITIONAL_QUANTITY_REFERENCE' if paid else ('STOP_REFERENCE_TERMINAL_COST_UNPAYABLE' if stop['reason']=='TERMINAL_COST_EXHAUSTS_NAV' else 'STOP_OWNED_REFERENCE_SOURCE_GAP')
    return dict(status=status,planned_days=len(d),completed_days=len(rows),paid_terminal=paid,terminal_cost_USDT=terminal,last_known_NAV=nav,net_USDT=nav-10000 if paid else None,positions=q.tolist(),stop=stop),rows
