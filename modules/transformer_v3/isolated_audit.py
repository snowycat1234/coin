"""Exchange-event journal witness adapter to the mature independent cash auditor.

Only a validated Mark-observation liquidation receives priority before funding
at the same clock. No cash, price, ownership or time is changed or imputed.
"""
import inspect,json
from decimal import Decimal as D,localcontext
from pathlib import Path
from scripts.investment import audit_shared_direction as auditor

def event_priorities(directory):
    directory=Path(directory);trades=json.loads((directory/'trades.json').read_text())
    liquidations=json.loads((directory/'liquidations.json').read_text())
    witnesses={w['id']:w for w in liquidations}
    if len(witnesses)!=len(liquidations):raise ValueError('Duplicate liquidation witness')
    seen=set();priorities={}
    for i,row in enumerate(trades):
        if row.get('liquidation_takeover'):
            w=witnesses.get(row['fill_id']);exact=row['decimal_strings']
            if w is None or row['symbol']!=w['symbol'] or row['event_us']!=w['event_us']:raise ValueError('Liquidation journal identity disagreement')
            q,margin,entry=map(D,(w['quantity'],w['isolated_margin_lost'],w['entry_price']))
            if not q or margin<0:raise ValueError('Invalid bankruptcy witness')
            with localcontext() as ctx:
                ctx.prec=50
                price=entry-(1 if q>0 else -1)*margin/abs(q)
            if abs(price-D(w['bankruptcy_price']))>D('1e-24') or D(exact['fill_price'])!=D(w['bankruptcy_price']) or D(exact['quantity_before'])!=q or D(exact['position_delta'])!=-q or D(exact['quantity_after'])!=0:
                raise ValueError('Bankruptcy takeover price/quantity witness disagreement')
            if w['phase'] not in ('MARK_OBSERVATION','AFTER_FUNDING','BEFORE_FILL','AFTER_OPEN','AFTER_CLOSE','RESTORE'):raise ValueError('Unknown liquidation event phase')
            if w['phase']=='MARK_OBSERVATION':priorities[i]=-1
            seen.add(w['id'])
        elif row.get('liquidation_partial_IOC'):
            # Actual research uses unknown tier caps, so this cannot be guessed.
            phase=row.get('liquidation_phase')
            if phase not in ('MARK_OBSERVATION','AFTER_FUNDING','BEFORE_FILL','AFTER_OPEN','AFTER_CLOSE','RESTORE'):raise ValueError('Partial IOC phase witness required')
            if phase=='MARK_OBSERVATION':priorities[i]=-1
    if seen!=set(witnesses):raise ValueError('Missing takeover trade for liquidation witness')
    return priorities

def verify(directory,symbols,unit_scale):
    if 'event_priorities' not in inspect.signature(auditor.verify).parameters:raise RuntimeError('Event-ordering adapter awaits committed and tested mature-auditor extension')
    priorities=event_priorities(directory)
    result=auditor.verify(directory,symbols,unit_scale,event_priorities=priorities)
    result.update(exchange_event_ordering='VALIDATED_MARK_TAKEOVER_BEFORE_SAME_CLOCK_FUNDING; FUNDING_BEFORE_FUNDING_TRIGGERED_TAKEOVER',
                  mark_phase_priority_trade_count=len(priorities),no_economic_journal_mutation=True)
    return result
