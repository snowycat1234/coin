"""One fixed SHORT collateral loss budget; existing engine owns every order/cash.

This is tail protection, not a new directional forecast or native Bybit rule.
"""
from decimal import Decimal as D, localcontext
import math

RULES=dict(id='SHORT_HALF_COLLATERAL_SIGNAL_RESET',equity_floor_fraction=.5,
    direction='SHORT_ONLY',observation='COMPLETED_MINUTE_MARK_AFTER_FUNDING',
    execution='ORIGINAL_DELAY_REAL_OPEN_CAPACITY_PAID_PERSISTENT_REDUCE_ONLY',
    reentry='ORIGINAL_SHORT_MEMBERSHIP_ENDS_AT_DAILY_DECISION_AND_ACTUAL_FLAT',
    margin_topup=False,bankruptcy_rescue=False,native_Bybit_certified=False)


class ShortCollateralProtection:
    requires_ohlcv=False
    rules=RULES

    def __init__(self,targets):
        self.targets=targets

    def prepare(self,bars,symbols,start,end):
        self.symbols=tuple(symbols);self.blocks=set();self.journal=[];self.choice={}
        for r in self.targets.iter_rows(named=True):
            k=(int(r['available_us']),r['symbol']);v=float(r['target_weight'])
            assert start<=k[0]<end and k[1] in self.symbols and math.isfinite(v) and k not in self.choice
            self.choice[k]=v
        for s in symbols:assert (start,s) in self.choice

    def blocked(self,s):return s in self.blocks

    def on_decision(self,t,positions):
        for s in self.symbols:
            assert (t,s) in self.choice
            if s in self.blocks and self.choice[t,s]>=0 and positions[s].quantity==0:
                self.blocks.remove(s)
                self.journal.append(dict(kind='ORIGINAL_SHORT_SIGNAL_RESET',symbol=s,event_us=int(t),
                    original_target=self.choice[t,s]))

    def on_fills(self,trades,order_kind):
        if order_kind!='PROTECTIVE_STOP':return
        for r in trades:
            self.journal.append(dict(kind='PROTECTIVE_FILL',symbol=r['symbol'],event_us=r['event_us'],
                signal_us=r['signal_us'],quantity_before=r['quantity_before'],quantity_after=r['quantity_after'],
                fees=r['fee_USDT_mid'],execution_cost=r['execution_cost']))

    def observe(self,close,market,positions):
        stopped=[]
        with localcontext() as ctx:
            ctx.prec=40
            for s in self.symbols:
                p=positions[s]
                if p.quantity>=0 or self.blocked(s):continue
                assert s in market
                mark=D(str(market[s]['mark']));assert mark.is_finite() and mark>0
                equity=p.isolated_balance+p.quantity*(mark-p.entry_price)
                if equity<=p.isolated_balance*D('.5'):
                    self.blocks.add(s);stopped.append(s)
                    self.journal.append(dict(kind='OBSERVED_SHORT_COLLATERAL_FLOOR',symbol=s,event_us=int(close),
                        mark=str(mark),quantity=str(p.quantity),entry_price=str(p.entry_price),
                        isolated_collateral=str(p.isolated_balance),isolated_equity=str(equity),floor_fraction=.5))
        return stopped
