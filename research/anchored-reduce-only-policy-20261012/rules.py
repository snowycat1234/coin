"""Offline readiness: notional exemption never supplies missing lot evidence."""
from decimal import Decimal as D
def quantity_gate(quantity,profile):
    q=abs(D(str(quantity)))
    if profile is None:return dict(status='UNKNOWN_SYMBOL_FILTERS_NOT_NATIVE_READY',tradable=False,quantity=str(q))
    m,step,cap=map(lambda k:D(str(profile[k])),('minQty','stepSize','maxQty'))
    if not 0<m<=cap or step<=0:raise ValueError('Positive explicit quantity limits required')
    errors=[]
    if q<m:errors.append('BELOW_MIN_QUANTITY')
    if q>cap:errors.append('ABOVE_MAX_QUANTITY')
    if (q-m)%step!=0:errors.append('OFF_QUANTITY_GRID')
    return dict(status='QUANTITY_PASS_ONLY_NOT_VENUE_CERTIFIED' if not errors else 'BLOCKED_QUANTITY_FILTER',tradable=not errors,errors=errors,quantity=str(q),no_roundup=True)
