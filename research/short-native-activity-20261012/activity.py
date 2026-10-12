from decimal import Decimal,localcontext
import numpy as np

def targets(d,w,start,end,fit,day=86400000000):
    d=np.asarray(d,np.int64);w=np.asarray(w,float)
    if not np.array_equal(d,np.arange(start,end,day)) or fit>start or w.shape!=(len(d),5) or not np.isfinite(w).all():raise ValueError('Exact causal full target calendar')
    if np.abs(w).max()>.3+1e-12 or np.abs(w).sum(1).max()>.6+1e-12:raise ValueError('Original shared caps')
    return w

def episodes(trades,symbols):
    quantity={s:Decimal(0) for s in symbols};active={};out=[];ids=set()
    for r in trades:
        s=r['symbol'];x=r['decimal_strings'];before=Decimal(x['quantity_before']);after=Decimal(x['quantity_after']);delta=Decimal(x['position_delta'])
        if before!=quantity[s] or after!=before+delta or before*after<0:raise ValueError('Actual per-symbol quantity chain/no implicit reversal')
        key=(s,r['event_us'],r.get('fill_id',len(ids)))
        if key in ids:raise ValueError('Repeated fill identity')
        ids.add(key)
        if before==0 and after<0:active[s]=dict(symbol=s,entry_us=r['event_us'],exit_us=None,fill_legs=0)
        if s in active:active[s]['fill_legs']+=1
        if before<0 and after==0:active[s]['exit_us']=r['event_us'];out.append(active.pop(s))
        quantity[s]=after
    out.extend(active.values());return out,quantity

def nav_bridge(trades,funds,quantity,marks,nav):
    with localcontext() as ctx:
        ctx.prec=50;gross=fees=execution=funding=Decimal(0)
        for r in trades:
            x=r['decimal_strings'];gross-=Decimal(x['position_delta'])*Decimal(x['mid_price']);fees+=Decimal(x['fee_amount']);execution+=Decimal(x['execution_cost'])
        for r in funds:
            if r['quantity']!=0:funding+=Decimal(r['decimal_strings']['signed_funding_USDT'])
            elif r['signed_funding_USDT']!=0:raise ValueError('Zero ownership cannot fund')
        gross+=sum((q*Decimal(str(marks[s])) for s,q in quantity.items() if q),Decimal(0))
        expected=Decimal(10000)+gross-fees-execution+funding;error=abs(expected-Decimal(str(nav)))
        if error>Decimal('1e-8'):raise ValueError('Independent financial NAV bridge')
    return dict(gross_price_USDT=str(gross),fees_USDT=str(fees),execution_USDT=str(execution),funding_cash_USDT=str(funding),NAV=str(expected),maximum_error_USDT=str(error))
