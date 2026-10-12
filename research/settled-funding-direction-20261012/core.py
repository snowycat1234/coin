"""Frozen financing direction and unchanged shared quantity-reference API."""
import importlib.util
from pathlib import Path
import numpy as np
from modules.collector_research.pipeline.economics import proxy_step
DAY=86_400_000_000; JITTER=60_000_000; EXEC=60_000_001
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('unchanged_funding_risk',ROOT/'research/portfolio-risk-budget-20261012/risk_budget.py');risk=importlib.util.module_from_spec(spec);spec.loader.exec_module(risk)

def daily_rates(times,rates,hours,days):
    t,r,h=map(np.asarray,(times,rates,hours));assert np.all(np.diff(t)>0)
    values=np.full(len(days),np.nan);last=np.full(len(days),-1,dtype=np.int64)
    for i,day in enumerate(days):
        ix=(t>=day)&(t<day+DAY);a,b,c=t[ix],r[ix],h[ix]
        if not len(a):continue
        valid=(np.isfinite(b).all() and np.isfinite(c).all() and (c>0).all()
               and abs(float(c.sum())-24)<1e-9 and 0<=a[0]-day<=JITTER
               and abs(int(a[-1]+c[-1]*3_600_000_000-day-DAY))<=JITTER
               and np.all(np.abs(np.diff(a)-c[1:]*3_600_000_000)<=JITTER))
        if valid:values[i]=float(b.sum());last[i]=int(a[-1])
    return values,last

def directions(days,values,decisions):
    days=np.asarray(days,np.int64);values=np.asarray(values,float);d=np.asarray(decisions,np.int64)
    assert values.shape==(len(days),5) and np.all(np.diff(days)==DAY)
    out=np.zeros((len(d),5));means=np.full_like(out,np.nan);known=np.zeros_like(out,dtype=bool)
    for i,at in enumerate(d):
        ix=(days>=at-22*DAY)&(days<at-DAY)
        assert ix.sum()==21 and np.max(days[ix]+2*DAY)<=at
        known[i]=np.isfinite(values[ix]).all(0)
        means[i,known[i]]=values[ix][:,known[i]].mean(0)
        out[i,known[i]]=-np.sign(means[i,known[i]])
    return out,means,known

def targets(t,p,d,days,values):
    intent,means,known=directions(days,values,d);out={a:np.zeros((len(d),5)) for a in ('CARRY','SHORT')};proof=[]
    for i,at in enumerate(d):
        k=int(np.searchsorted(t,at));assert k>=30 and k<len(t) and t[k]==at
        past=p[k-30:k+1];eligible=np.isfinite(past).all(0)&(past>0).all(0)
        # Unknown asset is CASH, not filled; only available risk submatrix is used.
        c=np.zeros((5,5));ids=np.flatnonzero(eligible)
        if len(ids):
            r=np.diff(past[:,ids],axis=0)/past[:-1,ids];c[np.ix_(ids,ids)]=np.atleast_2d(np.cov(r,rowvar=False,ddof=1))*365
        row=dict(decision_us=int(at),latest_funding_input_day_available_us=int(at),latest_price_available_us=int(t[k]),eligible=eligible.tolist(),arms={})
        for arm,raw in [('CARRY',.12*intent[i]*eligible),('SHORT',-.12*eligible.astype(float))]:out[arm][i],row['arms'][arm]=risk.scale(raw,c)
        proof.append(row)
    return out,proof,means,known

def reference(d,w,p0,p1,fp,valid):
    nav=10000.;q=np.zeros(5);rows=[];stop=None;terminal=0.
    for i,at in enumerate(d):
        before=nav
        try:nav,q,cost,fund,turn,pnl=proxy_step(nav,q,w[i],p0[i],p1[i],fp[i],valid[i],.00135)
        except ValueError as e:stop={'decision_us':int(at),'reason':str(e)};break
        rows.append(dict(decision_us=int(at),execution_us=int(at+EXEC),owned_end_us=int(at+EXEC+DAY),conservative_mature_us=int(at+2*DAY),nav_before=before,nav_after=nav,daily_return=nav/before-1,price_pnl=pnl,trading_cost_proxy=cost,funding_debit_proxy=fund,turnover_USDT=turn,held_quantity=q.tolist()))
    if stop is None:
        owned=q!=0;assert np.isfinite(p1[-1,owned]).all() and (p1[-1,owned]>0).all()
        terminal=float(np.dot(np.abs(q[owned]),p1[-1,owned]))*.00135
        if nav-terminal<=0:stop={'reason':'TERMINAL_COST_EXHAUSTS_NAV'}
        else:
            nav-=terminal;rows[-1]['nav_after']=nav;rows[-1]['daily_return']=nav/rows[-1]['nav_before']-1;rows[-1]['trading_cost_proxy']+=terminal;q*=0
    full=stop is None and len(rows)==len(d);v=np.r_[10000.,[r['nav_after'] for r in rows]];r=np.array([r['daily_return'] for r in rows])
    return dict(status='COMPLETE_CONDITIONAL_DAILY_QUANTITY_REFERENCE' if full else 'STOP_OWNED_GAP_OR_NAV',days=len(rows),planned_days=len(d),net_USDT=nav-10000. if full else None,marked_NAV=nav,terminal_cost_proxy_USDT=terminal,hypothetical_cost_terminal=full,positions=q.tolist(),stop=stop,price_pnl=sum(x['price_pnl'] for x in rows),trading_cost=sum(x['trading_cost_proxy'] for x in rows),funding_cash=-sum(x['funding_debit_proxy'] for x in rows),annual_vol=float(r.std(ddof=1)*np.sqrt(365)) if len(r)>1 else None,drawdown=float(np.max(1-v/np.maximum.accumulate(v))),worst30=float(np.min(v[30:]/v[:-30]-1)) if len(v)>30 else None),rows

def paired_ci(delta,seed):
    rng=np.random.default_rng(seed);samples=[]
    for _ in range(1000):
        starts=rng.integers(0,len(delta),int(np.ceil(len(delta)/14)));idx=((starts[:,None]+np.arange(14))%len(delta)).ravel()[:len(delta)];samples.append(float(delta[idx].mean()))
    return [float(x) for x in np.quantile(samples,[.025,.975])]
