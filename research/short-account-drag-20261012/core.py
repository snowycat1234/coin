from decimal import Decimal,localcontext
from bisect import bisect_left

def split_money(trades,funds,positions,marks):
    symbols=tuple(positions);q={s:Decimal(0) for s in symbols};history={s:[] for s in symbols}
    out={(s,side):dict(gross=Decimal(0),fees=Decimal(0),execution=Decimal(0),funding=Decimal(0),realized_fillbasis=Decimal(0)) for s in symbols for side in ('LONG','SHORT')}
    for r in trades:
        s=r['symbol'];x=r['decimal_strings'];before=Decimal(x['quantity_before']);after=Decimal(x['quantity_after']);delta=Decimal(x['position_delta'])
        if before!=q[s] or after!=before+delta or before*after<0:raise ValueError('Exact quantity chain')
        owner=before if r['leg']=='CLOSE' else delta;v=out[s,'LONG' if owner>0 else 'SHORT']
        v['gross']-=delta*Decimal(x['mid_price']);v['fees']+=Decimal(x['fee_amount']);v['execution']+=Decimal(x['execution_cost']);v['realized_fillbasis']+=Decimal(x['realized_PnL']);q[s]=after;history[s].append((r['event_us'],after))
    for r in funds:
        own=history[r['symbol']];prior=bisect_left([x[0] for x in own],r['event_us'])-1;quantity=own[prior][1] if prior>=0 else Decimal(0)
        reported=Decimal(r['decimal_strings']['quantity']) if r['quantity'] else Decimal(0)
        if quantity!=reported:raise ValueError('Actual funding quantity ownership')
        if r['quantity']:
            x=r['decimal_strings'];owner=Decimal(x['quantity']);out[r['symbol'],'LONG' if owner>0 else 'SHORT']['funding']+=Decimal(x['signed_funding_USDT'])
        elif r['signed_funding_USDT']!=0:raise ValueError('Zero ownership funding')
    for s,p in positions.items():
        exact=Decimal(p['decimal_strings']['quantity'])
        if exact!=q[s]:raise ValueError('Remaining inventory cannot be removed')
        if exact:out[s,'LONG' if exact>0 else 'SHORT']['gross']+=exact*Decimal(str(marks[s]))
    for v in out.values():v['net']=v['gross']-v['fees']-v['execution']+v['funding']
    return out

def expiry_class(row,step='1e-8'):
    remaining=abs(Decimal(str(row['remaining_signed_quantity'])))
    return 'SUBSTEP_REMAINDER' if remaining<Decimal(step) else 'AT_LEAST_ONE_EXECUTABLE_STEP'
