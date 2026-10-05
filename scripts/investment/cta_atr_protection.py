"""Initial public 2ATR stop adapter; shared account still owns all finances.

TSMOM signal/size remain frozen. Daily ATR uses the already pinned Jesse Rust
kernel and original Turtle go_long/go_short formula. Actual first-fill anchor,
minute-close observation and next-month re-entry are explicit COIN adaptations.
"""
from datetime import datetime,UTC
import math
import numpy as np
import polars as pl
from scripts.investment.turtle_perpetual_bridge import official_context

DAY=86_400_000_000
MINUTE=60_000_000
RULES=dict(ATR_period=20,ATR_multiplier=2,anchor='FIRST_ACTUAL_FILL_PRICE',
    indicator='PINNED_JESSE_RUST1.3.0_ORIGINAL_SCALAR_LAST240_DAILY_CANDLES',
    stop='FIXED_INITIAL_NO_TRAIL_NO_ADD_REARM',symmetric=True,
    observation='COMPLETED_TRADE_MINUTE_HIGH_LOW_ARMED_BEFORE_OPEN',
    execution='ORIGINAL_DELAY_REAL_OPEN_CAPACITY_PAID_REDUCE_ONLY_PERSIST',
    reentry='NEXT_UTC_MONTH_DECISION_AND_ACTUAL_FLAT',
    full_Turtle_replication=False)

def next_month(t):
    d=datetime.fromtimestamp(int(t)/1e6,UTC)
    return int(datetime(d.year+(d.month==12),d.month%12+1,1,tzinfo=UTC).timestamp())*1_000_000

class InitialATRProtection:
    rules=RULES

    def prepare(self,bars,symbols,start,end):
        self.stops={};self.blocks={};self.journal=[];self.values={}
        cls,self.receipt=official_context()
        self.journal.append(dict(kind='UPSTREAM_REUSE_RECEIPT',receipt=self.receipt))
        for s in symbols:
            b=bars.filter(pl.col('symbol')==s).sort('close_us')
            stamps=b['close_us'].to_numpy();available=b['available_us'].to_numpy()
            assert len(stamps)>20 and np.all(np.diff(stamps)==DAY) and np.all(available>=stamps)
            candles=np.column_stack((b['open_us'].to_numpy()/1000,b.select('open','close','high','low','volume').to_numpy()))
            for t in range(start,end,DAY):
                j=int(np.searchsorted(stamps,t,side='right'))
                assert j>=20 and stamps[j-1]==t and np.all(available[:j]<=t)
                obj=cls();obj.before();obj.candles=candles[:j];obj.balance=10000.;obj.price=float(candles[j-1,2])
                atr=float(obj.atr);assert math.isfinite(atr) and atr>0
                # Original public stop formulas, not a replacement ATR recurrence.
                obj.go_long();long_distance=obj.price-float(obj.stop_loss[1])
                obj.go_short();short_distance=float(obj.stop_loss[1])-obj.price
                assert np.isclose(long_distance,2*atr,rtol=1e-10,atol=0) and np.isclose(short_distance,2*atr,rtol=1e-10,atol=0)
                self.values[(s,t)]=dict(atr=atr,distance=2*atr,source_available_us=int(available[j-1]))

    def blocked(self,s):return s in self.blocks

    def on_decision(self,t,positions):
        for s,release in list(self.blocks.items()):
            if t>=release and positions[s].quantity==0:
                del self.blocks[s]
                self.journal.append(dict(kind='REENTRY_RELEASE',symbol=s,event_us=int(t),release_us=release))
            else:self.journal.append(dict(kind='DAILY_ALPHA_SUPPRESSED',symbol=s,event_us=int(t),release_us=release))

    def on_fills(self,trades,order_kind):
        for r in trades:
            s=r['symbol'];q0=r['quantity_before'];q1=r['quantity_after'];t=r['event_us']
            if order_kind=='PROTECTIVE_STOP':
                self.journal.append(dict(kind='PROTECTIVE_FILL',symbol=s,event_us=t,signal_us=r['signal_us'],
                    quantity_before=q0,quantity_after=q1,quantity=r['quantity'],fill_price=r['fill_price'],
                    fees=r['fee_USDT_mid'],execution_cost=r['execution_cost'],order_kind=order_kind))
            if q1==0:self.stops.pop(s,None)
            elif q0==0:
                assert not self.blocked(s),'Protection never opens a blocked position'
                v=self.values[(s,t//DAY*DAY)];sign=1 if q1>0 else -1
                price=float(r['fill_price'])-sign*v['distance']
                assert price>0,'Initial protective stop must have a meaningful positive price'
                self.stops[s]=dict(price=price,sign=sign,armed_us=t,**v)
                self.journal.append(dict(kind='ARM',symbol=s,event_us=t,entry_fill_price=r['fill_price'],
                    stop_price=price,sign=sign,**v))

    def observe(self,close,market,positions):
        triggered=[]
        for s,stop in list(self.stops.items()):
            if not positions[s].quantity or self.blocked(s):continue
            assert s in market and market[s]['high']>=market[s]['low']>0
            if stop['armed_us']>close-MINUTE:continue
            crossed=(market[s]['low']<=stop['price'] if stop['sign']>0 else market[s]['high']>=stop['price'])
            if crossed:
                self.blocks[s]=next_month(close)
                self.journal.append(dict(kind='OBSERVED_STOP_TRIGGER',symbol=s,event_us=int(close),
                    minute_open_us=int(close-MINUTE),high=float(market[s]['high']),low=float(market[s]['low']),
                    stop_price=stop['price'],armed_us=stop['armed_us'],release_us=self.blocks[s]))
                triggered.append(s)
        return triggered
