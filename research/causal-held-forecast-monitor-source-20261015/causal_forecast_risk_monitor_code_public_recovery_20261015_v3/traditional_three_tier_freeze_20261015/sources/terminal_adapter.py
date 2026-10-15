"""Fixed terminal60 adapter; Decimal finance and nonterminal expiry unchanged.

The copied attempt method is byte-identical to the frozen scheduler after two
explicit terminal-only expiry substitutions. No runtime source rewriting.
"""
from scripts.investment.resumable_perpetual import NativeDailySimulator
from scripts.investment.resumable_perpetual import ExecutionContractV2,D,ZERO,HALTS
MINUTE=60_000_000
TERMINAL_OPENS=60

class EarlierTerminalSimulator(NativeDailySimulator):
    VERSION='fixed_60_real_minute_terminal_exit_v1'

    def __init__(self,*args,**kwargs):
        if kwargs.get('persist_cash_close',False) or kwargs.get('final_day_target_zero',False):
            raise ValueError('Original daily retry and final-day targets must stay unchanged')
        super().__init__(*args,**kwargs)
        if self.end-self.start<61*MINUTE:
            raise ValueError('At least 61 real minutes needed for terminal60')
        self.terminal_signal_us=self.end-61*MINUTE

    def schedule(self,target,signal,kind,only_symbols=None):
        if kind=='TERMINAL':
            if signal!=self.terminal_signal_us:
                # The inherited 23:54 branch is a duplicate of the fixed earlier
                # exit and must not reset its signal, attempt counter or target.
                if self.terminal and signal==self.end-6*MINUTE:
                    return
                raise ValueError('Only fixed terminal60 signal is allowed')
            if any(D(str(target[s]))!=ZERO for s in self.symbols):
                raise ValueError('Terminal cannot increase or reverse inventory')
        elif self.terminal:
            raise ValueError('Daily/risk instructions cannot replace terminal exit')
        super().schedule(target,signal,kind,only_symbols)

    def funding_through(self,limit,inclusive):
        # Native order: signal, funding at open+1, attempt at open+1, intraminute
        # funding, close mark. This hook fires at the same signal phase.
        if inclusive and limit==self.terminal_signal_us+1 and not self.terminal:
            self.terminal=True
            self.schedule(dict.fromkeys(self.symbols,ZERO),self.terminal_signal_us,'TERMINAL')
        super().funding_through(limit,inclusive)

    def attempt(self,open_us,market_row):
        event=int(open_us)+1;due={s:o for s,o in self.pending.items()
            if event>=ExecutionContractV2().earliest_execution_us(o['signal_us'])+1}
        capacity={s:D(str(self.previous_quote[s]))*D('.001')/D(str(market_row[s]['open']))
                  if self.previous_quote is not None and s in market_row else ZERO for s in self.symbols}
        # Every symbol gets at most one attempt-minute; reductions precede every increase.
        for phase in ('REDUCE','INCREASE'):
            for s in self.symbols:
                if s not in due or s not in market_row:continue
                order=due[s];position=self.account.positions[s].quantity;target=order['target'];delta=target-position
                if s not in self.pending or self.pending[s] is not order:continue
                if delta==0:continue
                reducing=position!=0 and position*delta<0
                if phase=='REDUCE':
                    if not reducing:continue
                    requested=min(abs(delta),abs(position));reduce_only=True
                    if order['kind']=='RISK_REDUCTION':
                        from decimal import ROUND_CEILING
                        step=self.account.instrument_profiles[s].quantity_step
                        requested=min(abs(position),(requested/step).to_integral_value(rounding=ROUND_CEILING)*step)
                else:
                    if reducing or order['kind'] in ('RISK_REDUCTION','TERMINAL','POOL_EXIT','DATA_GAP_EXIT','PROTECTIVE_STOP'):continue
                    if self.account.status!='ACTIVE':
                        self.rejections.append(dict(symbol=s,event_us=event,reason='RISK_PRIORITY_NO_INCREASE',order_id=order['order_id']));continue
                    requested=abs(delta);reduce_only=False
                if requested==0:continue
                side='BUY' if delta>0 else 'SELL'
                fill_id=f'{order["order_id"]}:{order["attempts"]}:{phase}'
                before=len(self.account.trades)
                receipt=self.account.execute_fill(s,side,requested,event,order['signal_us'],fill_id,
                    execution_mid_price=D(str(market_row[s]['open'])),quote_available_us=int(open_us),
                    available_quantity=capacity[s],reduce_only=reduce_only)
                used=sum((D(r['decimal_strings']['quantity']) for r in self.account.trades[before:] if not r.get('liquidation_takeover')),ZERO)
                capacity[s]=max(ZERO,capacity[s]-used)
                if used>0 and order['kind']=='RISK_REDUCTION':
                    witness=next(r for r in reversed(self.breaches) if r['signal_us']==order['signal_us'])
                    if 'first_reduction_fill_us' not in witness:
                        witness.update(first_reduction_fill_us=event,reduction_latency_us=event-order['signal_us'])
                if self.account.trades[before:] and self.first_entry is None:self.first_entry=event
                if receipt['status']!='FILLED':self.rejections.append(dict(symbol=s,event_us=event,
                    order_id=order['order_id'],phase=phase,**{k:v for k,v in receipt.items() if k!='fills'}))
                self.observe(event,'AFTER_'+phase)
                if self.account.status in HALTS:
                    self.completion='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED';self.stop=event;return
        for s,order in due.items():
            if s not in self.pending or self.pending[s] is not order:continue
            order['attempts']+=1
            remaining=order['target']-self.account.positions[s].quantity
            reached=(remaining==0 or order['kind'] in ('RISK_REDUCTION','TERMINAL','POOL_EXIT','DATA_GAP_EXIT')
                and (self.account.positions[s].quantity==0 or order['target']*self.account.positions[s].quantity>0
                     and abs(self.account.positions[s].quantity)<=abs(order['target'])))
            if reached:self.pending.pop(s,None)
            elif order['attempts']>=(60 if order['kind']=='TERMINAL' else 5):
                if order['kind']=='PROTECTIVE_STOP':continue
                if self.persist_cash_close and order['kind']=='DAILY_TARGET' and order['target']==ZERO:
                    # Still capacity limited and reduce-only. A newer target,
                    # hard-risk instruction or terminal order may supersede it.
                    continue
                self.rejections.append(dict(symbol=s,event_us=event,order_id=order['order_id'],reason='SIXTY_TERMINAL_ATTEMPTS_EXPIRED' if order['kind']=='TERMINAL' else 'FIVE_ATTEMPTS_EXPIRED',
                    remaining_signed_quantity=float(remaining),kind=order['kind']))
                self.pending.pop(s,None)
                if order['kind']=='RISK_REDUCTION' and self.account.status=='BOUND_BREACH_REDUCTION_REQUIRED':
                    self.completion='NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION';self.stop=event;return
                if order['kind'] in ('POOL_EXIT','DATA_GAP_EXIT') and self.account.positions[s].quantity:
                    self.completion='NOT_EVALUABLE_UNEXECUTABLE_ASSET_EXIT';self.stop=event;return

