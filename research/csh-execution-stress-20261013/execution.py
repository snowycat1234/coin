"""One fixed capacity factor around the unchanged scheduler's fill attempt."""
from decimal import Decimal

def capacity_half_class(base):
 class CapacityHalfSimulator(base):
  def attempt(self,open_us,market_row):
   # The original scheduler calls attempt once per minute. Reject accidental
   # duplicate or backward calls before fills/attempt counters can change.
   last=getattr(self,'_capacity_last_attempt_open_us',None)
   if last is not None and open_us<=last:
    raise RuntimeError('Capacity budget already admitted for this minute')
   self._capacity_last_attempt_open_us=open_us
   original=self.previous_quote
   try:
    if original is not None:
     self.previous_quote={s:Decimal(str(q))*Decimal('0.5') for s,q in original.items()}
    return super().attempt(open_us,market_row)
   finally:
    self.previous_quote=original
 return CapacityHalfSimulator
