"""Isolated bankruptcy takeover specialization of the shared Decimal wallet.

Public Bybit formulas are implemented under declared minute-mark observations.
Without a native risk snapshot, the existing .005 MMR remains an explicit
research assumption; it is never represented as verified lowest-tier data.
"""
from copy import deepcopy
from decimal import Decimal as D,localcontext,ROUND_CEILING
from .perpetual_account import USDTLinearPerpetualAccount,decimal,_numbers,ZERO

def liquidation_price(entry,quantity,leverage,extra,mmr,fee,deduction,side):
    e,q,l,x,m,f,d=map(decimal,(entry,quantity,leverage,extra,mmr,fee,deduction))
    if e<=0 or q<=0 or l<=0 or not 0<=m<1 or not 0<=f<1 or d<0:raise ValueError('Invalid liquidation formula inputs')
    if side=='LONG':return (e*q-e*q/l-x/(1-f)-d)/(q-q*m)
    if side=='SHORT':return (e*q+e*q/l+x/(1+f)+d)/(q+q*m)
    raise ValueError('Explicit side required')

def validated_tiers(rows):
    out=[]
    for r in rows:
        cap=None if r['riskLimitValue'] is None else decimal(r['riskLimitValue'])
        mm=decimal(r['maintenanceMargin']);ded=decimal(r['mmDeduction'] or '0')
        if cap is not None and cap<=0 or not 0<mm<1 or ded<0:raise ValueError('Invalid risk tier values')
        out.append(dict(riskLimitValue=None if cap is None else str(cap),maintenanceMargin=str(mm),mmDeduction=str(ded),
                        initialMargin=str(decimal(r['initialMargin'])),maxLeverage=str(decimal(r['maxLeverage'])),isLowestRisk=int(r['isLowestRisk'])))
    if not out or out[0]['isLowestRisk']!=1 or any(r['isLowestRisk'] for r in out[1:]):raise ValueError('Ordered lowest tier required')
    if any(r['riskLimitValue'] is None for r in out) and len(out)!=1:raise ValueError('Unknown cap cannot be mixed with certified ladder')
    if any(decimal(a['riskLimitValue'])>=decimal(b['riskLimitValue']) or decimal(a['maintenanceMargin'])>decimal(b['maintenanceMargin']) for a,b in zip(out,out[1:])):
        raise ValueError('Risk ladder must increase')
    return out

class BybitIsolatedAccount(USDTLinearPerpetualAccount):
    VERSION='bybit_style_isolated_bankruptcy_takeover_v1'

    def __init__(self,config=None,*,risk_tiers=None,risk_authority='LEGACY005_UNCERTIFIED_RESEARCH_ASSUMPTION',liquidation_journal=None,**kwargs):
        self.risk_authority=risk_authority;self.liquidations=deepcopy(liquidation_journal or [])
        self.liquidation_callback=None;self.liquidation_ioc_capacity={};self._inside_liquidation=False
        self.blocked_signals={};self.reentries={};self.max_observed_notional={};self.upper_tier_observations=0
        kwargs.setdefault('closing_min_notional_exempt',True)
        super().__init__(config,**kwargs)
        default=[dict(riskLimitValue=None,maintenanceMargin='.005',initialMargin='1',mmDeduction='0',maxLeverage='1',isLowestRisk=1)]
        if risk_tiers is not None and set(risk_tiers)!=set(self.symbols):raise ValueError('Exact configured symbol risk snapshots required')
        self.risk_tiers={s:validated_tiers(default if risk_tiers is None else risk_tiers[s]) for s in self.symbols}

    def contract_metadata(self):
        out=super().contract_metadata()
        out.update(liquidation_semantics='PER_POSITION_MARK_TRIGGER_BANKRUPTCY_TAKEOVER_NO_SURPLUS_REFUND_WALLET_CONTINUES',
                   risk_authority=self.risk_authority,risk_tiers=self.risk_tiers,
                   native_risk_tiers_available=all(r[0]['riskLimitValue'] is not None for r in self.risk_tiers.values()),
                   native_liquidation_certified=False,historical_risk_tiers_certified=False,
                   liquidation_observation_scope='CAUSALLY_AVAILABLE_MINUTE_MARK_CLOSE; NOT_INTRAMINUTE_EXCHANGE_CERTIFICATION')
        return out

    def _tier(self,symbol,notional):
        rows=self.risk_tiers[symbol]
        for i,r in enumerate(rows):
            if r['riskLimitValue'] is None or notional<=decimal(r['riskLimitValue']):return i,r
        return len(rows)-1,rows[-1]

    def _lp(self,position,tier):
        q=abs(position.quantity);extra=position.isolated_balance-q*position.entry_price/self.config.leverage
        return liquidation_price(position.entry_price,q,self.config.leverage,extra,tier['maintenanceMargin'],self.config.fee_rate,tier['mmDeduction'],
                                 'LONG' if position.quantity>0 else 'SHORT')

    def _takeover(self,symbol,mark,phase,tier):
        p=self.positions[symbol];q=p.quantity;amount=abs(q);margin=p.isolated_balance;entry=p.entry_price
        direction=D(1) if q>0 else D(-1)
        # Effective bankruptcy changes with actual remaining isolated collateral.
        bankruptcy=entry-direction*margin/amount
        if bankruptcy<0:raise ValueError('Negative bankruptcy takeover price is inconsistent with a triggered long')
        event=self.clock_us;identity=f'LIQUIDATION:{symbol}:{event}:{len(self.liquidations)}'
        row=_numbers(dict(symbol=symbol,side='SELL' if q>0 else 'BUY',leg='CLOSE',fill_id=identity,event_us=event,signal_us=event,
                          quantity=amount,gross_quantity=amount,position_delta=-q,execution_mid_price=bankruptcy,mid_price=bankruptcy,fill_price=bankruptcy,
                          mark_price=mark,fee_asset='USDT',fee_amount=ZERO,fee_USDT_mid=ZERO,execution_cost=ZERO,realized_PnL=-margin,cash_delta=-margin,
                          free_cash_delta=ZERO,isolated_balance_delta=-margin,margin_allocated=ZERO,margin_released=margin,
                          quantity_before=q,quantity_after=ZERO,entry_price_before=entry,entry_price_after=ZERO,
                          liquidation_takeover=True,takeover_margin_loss=margin,price_role='BANKRUPTCY_TAKEOVER_NOT_MARKET_FILL',
                          liquidation_fees_scope='TOTAL_REMAINING_COLLATERAL_FORFEITED; NO_ADDITIONAL_FEE_OR_INSURANCE_SURPLUS_CREDIT'))
        witness=dict(id=identity,symbol=symbol,event_us=event,phase=phase,mark_price=str(mark),bankruptcy_price=str(bankruptcy),
                     isolated_margin_lost=str(margin),quantity=str(q),entry_price=str(entry),tier=deepcopy(tier),lowest_risk_snapshot_proven=tier['riskLimitValue'] is not None)
        self.trades.append(row);self.liquidations.append(witness);self.realized_PnL-=margin;self.gross_fill_turnover+=amount*bankruptcy
        p.quantity=p.isolated_balance=p.entry_price=ZERO;p.opened_us=None;self.blocked_signals[symbol]=event
        if self.liquidation_callback is not None:self.liquidation_callback(symbol,event)

    def _risk(self,phase):
        if self._inside_liquidation:return
        for symbol,p in self.positions.items():
            if not p.quantity:continue
            mark=self._mark(symbol);notional=abs(p.quantity)*mark
            self.max_observed_notional[symbol]=max(self.max_observed_notional.get(symbol,ZERO),notional)
            index,tier=self._tier(symbol,notional);self.upper_tier_observations+=int(index>0)
            hit=mark<=self._lp(p,tier) if p.quantity>0 else mark>=self._lp(p,tier)
            if not hit:continue
            if self.liquidation_callback is not None:self.liquidation_callback(symbol,self.clock_us)
            self._inside_liquidation=True
            try:
                # Laddered IOC uses only explicitly supplied observable capacity.
                while index>0 and p.quantity:
                    lower=self.risk_tiers[symbol][index-1];cap=decimal(lower['riskLimitValue'])
                    requested=max(ZERO,abs(p.quantity)-cap/mark)
                    step=self.instrument_profiles[symbol].quantity_step
                    requested=min(abs(p.quantity),(requested/step).to_integral_value(rounding=ROUND_CEILING)*step)
                    capacity=decimal(self.liquidation_ioc_capacity.get(symbol,0));filled=self._floor(symbol,min(requested,capacity))
                    if not filled:break
                    side='SELL' if p.quantity>0 else 'BUY';direction=D(1) if side=='BUY' else D(-1)
                    fill=mark*(1+direction*(self.config.half_spread_bps+self.config.slippage_bps)/10000)
                    identity=f'LIQUIDATION_IOC:{symbol}:{self.clock_us}:{len(self.trades)}'
                    previous_strategy_fill=self.last_fill_us
                    self._leg(symbol,side,filled,mark,fill,self.clock_us,max(0,self.clock_us-60_000_001),identity,'CLOSE')
                    self.last_fill_us=previous_strategy_fill
                    self.trades[-1]['liquidation_partial_IOC']=True
                    # Partial IOC is an exchange instruction, not a strategy request.
                    self.trades[-1]['exchange_liquidation_instruction']=True
                    self.trades[-1]['liquidation_phase']=phase
                    self.liquidation_ioc_capacity[symbol]=capacity-filled
                    if not p.quantity:break
                    index,tier=self._tier(symbol,abs(p.quantity)*mark)
                    hit=mark<=self._lp(p,tier) if p.quantity>0 else mark>=self._lp(p,tier)
                    if not hit:break
                if p.quantity and hit:self._takeover(symbol,mark,phase,tier)
            finally:self._inside_liquidation=False
        nav=self.nav()
        if nav<=0:
            self.status='BANKRUPT_HALT';self.halt_witness=_numbers(dict(event_us=self.clock_us,NAV=nav,scope='REAL_WHOLE_WALLET_INSOLVENCY_AFTER_ISOLATED_TAKEOVERS'));return
        values=[abs(p.quantity)*self._mark(s) if p.quantity else ZERO for s,p in self.positions.items()]
        breach=any(v>self.config.max_asset_weight*nav for v in values) or sum(values,ZERO)>self.config.max_gross_weight*nav
        self.status='BOUND_BREACH_REDUCTION_REQUIRED' if breach else 'ACTIVE'

    def execute_fill(self,symbol,side,quantity,event_us,signal_us,fill_id,**kwargs):
        if symbol in self.blocked_signals and signal_us<=self.blocked_signals[symbol] and not kwargs.get('reduce_only',False):
            return _numbers(dict(fill_id=fill_id,requested_quantity=decimal(quantity),executed_quantity=ZERO,remaining_quantity=decimal(quantity),
                                 status='REJECTED',reason='LIQUIDATED_WAIT_NEXT_NORMAL_REBALANCE',account_status=self.status,fills=[]))
        flat=not self.positions[symbol].quantity
        result=super().execute_fill(symbol,side,quantity,event_us,signal_us,fill_id,**kwargs)
        if flat and self.positions[symbol].quantity and symbol in self.blocked_signals:
            self.reentries[symbol]=self.reentries.get(symbol,0)+1;self.blocked_signals.pop(symbol)
        return result

    def summary(self):
        result=super().summary()
        result.update(liquidation_count=len(self.liquidations),liquidation_loss_USDT=float(sum((decimal(r['isolated_margin_lost']) for r in self.liquidations),ZERO)),
                      liquidation_counts_by_symbol={s:sum(r['symbol']==s for r in self.liquidations) for s in self.symbols},
                      reentry_after_liquidation=dict(self.reentries),upper_tier_observations=self.upper_tier_observations,
                      maximum_observed_position_notional={s:float(v) for s,v in self.max_observed_notional.items()},risk_authority=self.risk_authority)
        return result

    def snapshot(self):
        result=super().snapshot();result.update(risk_tiers=deepcopy(self.risk_tiers),risk_authority=self.risk_authority,liquidations=deepcopy(self.liquidations),
                                               blocked_signals=dict(self.blocked_signals),reentries=dict(self.reentries),
                                               max_observed_notional={s:str(v) for s,v in self.max_observed_notional.items()},upper_tier_observations=self.upper_tier_observations)
        return result

    def _snapshot_trade_is_external(self,row):
        return bool(row.get('liquidation_takeover') or row.get('exchange_liquidation_instruction'))

    def _validate_snapshot_trade(self,row,rate):
        if not row.get('liquidation_takeover'):return super()._validate_snapshot_trade(row,rate)
        e=row['decimal_strings'];q=decimal(e['quantity_before']);margin=decimal(e['takeover_margin_loss']);entry=decimal(e['entry_price_before'])
        expected=entry-(D(1) if q>0 else D(-1))*margin/abs(q)
        witness=next((w for w in self.liquidations if w['id']==row['fill_id']),None)
        if witness is None or decimal(e['fill_price'])!=expected or decimal(e['position_delta'])!=-q or decimal(e['quantity_after'])!=0 or decimal(e['realized_PnL'])!=-margin:
            raise ValueError('Liquidation snapshot takeover identity mismatch')
        if decimal(e['fee_amount'])!=0 or decimal(e['execution_cost'])!=0 or str(margin)!=witness['isolated_margin_lost']:
            raise ValueError('Liquidation snapshot collateral/cost mismatch')

    @classmethod
    def from_snapshot(cls,snapshot,**kwargs):
        result=super().from_snapshot(snapshot,constructor_kwargs=dict(risk_tiers=snapshot['risk_tiers'],risk_authority=snapshot['risk_authority'],liquidation_journal=snapshot['liquidations']),**kwargs)
        result.blocked_signals=dict(snapshot['blocked_signals']);result.reentries=dict(snapshot['reentries'])
        result.max_observed_notional={s:decimal(v) for s,v in snapshot['max_observed_notional'].items()};result.upper_tier_observations=snapshot['upper_tier_observations']
        return result
