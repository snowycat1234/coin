"""Resumable daily scheduler extracted from perpetual_directional.simulate.

Finance remains in the existing Decimal account. Only the global last six
minutes schedule terminal fills. Forks never revalidate or replay past journals.
The original simulate entry point and frozen sources are left unchanged.
"""
from __future__ import annotations
from copy import deepcopy
from types import MappingProxyType
import hashlib
import json
import math
import numpy as np
import polars as pl
from quant.execution_contract import ExecutionContractV2
from quant.perpetual_account import USDTLinearPerpetualAccount, D, ZERO, HALTS
from scripts.investment import public_sma_perpetual as strategy
from scripts.investment.bybit_cost_inputs import account_for_cost
from scripts.investment.perpetual_directional import MINUTE, DAY, need


class MarketTape:
    """One shared immutable day, with a single sequential market reader.

    Array windows and the existing minute_blocks callback are supported.
    A block callback is read once, irrespective of the number of wallet forks.
    """
    def __init__(self, window, symbols):
        self.window=window
        self.symbols=symbols
        self.cache_start=None
        self.cache=None
        self.expected=window['start']
        self.reader=self._rows()

    def _rows(self):
        window=self.window
        if 'minute_blocks' not in window:
            for i,t in enumerate(range(window['start'],window['end'],MINUTE)):
                yield t,{s:{k:float(window['market'][s][k][i]) for k in
                             ('open','close','quote_volume','mark')} for s in self.symbols}
            return
        expected=window['start']
        for block in window['minute_blocks']():
            stamps=np.asarray(block['times'])
            need(stamps.dtype.kind in ('i','u') and 0<len(stamps)<=1440,
                 'One UTC day or smaller actual execution block')
            need(np.array_equal(stamps,np.arange(expected,expected+len(stamps)*MINUTE,MINUTE)),
                 'Execution blocks cover scoring dates without gaps')
            need(set(block['market'])<=set(self.symbols),'Unknown market symbol')
            for data in block['market'].values():
                need(set(data)=={'open','close','quote_volume','mark'} and
                     all(len(v)==len(stamps) for v in data.values()),'Exact daily market schema')
            for i,t in enumerate(stamps):
                yield int(t),{s:{k:float(v[i]) for k,v in data.items()}
                              for s,data in block['market'].items()}
            expected+=len(stamps)*MINUTE
        need(expected==window['end'],'Complete market calendar')

    def day(self, stamp):
        if self.cache_start==stamp:return self.cache
        need(stamp==self.expected,'Day tape advances sequentially; branches must share the current day')
        end=min(stamp+DAY,self.window['end'])
        rows=[]
        for t in range(stamp,end,MINUTE):
            try:actual,row=next(self.reader)
            except StopIteration:raise ValueError('Truncated market day') from None
            need(actual==t,'Complete synchronous minute clock')
            rows.append((t,MappingProxyType({s:MappingProxyType(v) for s,v in row.items()})))
        self.cache_start=stamp
        self.cache=tuple(rows)
        self.expected=end
        if end==self.window['end']:
            try:next(self.reader)
            except StopIteration:pass
            else:raise ValueError('Market callback extends beyond the global end')
        return self.cache


class NativeDailySimulator:
    VERSION='native_daily_scheduler_v1'

    def __init__(self, window, mode, cost, unit, *, target_factory=None,
                 account_factory=USDTLinearPerpetualAccount, persist_cash_close=False,
                 final_day_target_zero=False):
        self.window=window
        self.symbols=strategy.symbol_order(window.get('symbols',strategy.SYMBOLS))
        self.mode=mode
        self.cost=deepcopy(cost)
        self.unit=deepcopy(unit)
        self.start,self.end=int(window['start']),int(window['end'])
        need(self.start%DAY==0 and self.end>self.start and self.end%MINUTE==0,
             'Fixed UTC daily decisions and complete minutes')
        need(type(persist_cash_close) is bool,'Explicit cash retry policy')
        self.persist_cash_close=persist_cash_close
        need(type(final_day_target_zero) is bool,'Explicit global terminal convention')
        self.final_day_target_zero=final_day_target_zero
        self.decisions=np.arange(self.start,self.end,DAY,dtype=np.int64)
        self.weights={}
        self.decision_kinds={}
        self.targets=None
        self.meta={'source':'RUNTIME_CAUSAL_DAILY_TARGETS'}
        if target_factory is not None:
            self.targets,self.meta=target_factory(window['daily'],self.decisions,mode)
            need(self.targets.height==len(self.symbols)*len(self.decisions),'Complete target calendar')
            for t in self.decisions:
                rows=self.targets.filter(pl.col('available_us')==t)
                need(rows.height==len(self.symbols) and set(rows['symbol'].to_list())==set(self.symbols),
                     'Each decision contains every symbol once')
                self.weights[int(t)]={r['symbol']:r['target_weight'] for r in rows.iter_rows(named=True)}
                self.decision_kinds[int(t)]={}
                for r in rows.iter_rows(named=True):
                    reason=r.get('eligibility_reason','ELIGIBLE')
                    kind=('POOL_EXIT' if reason=='POOL_EXIT' else
                          'DATA_GAP_EXIT' if reason=='WARMUP_OR_DATA_GAP' else 'DAILY_TARGET')
                    need(kind=='DAILY_TARGET' or r['target_weight']==0,'Exit cannot add risk')
                    self.decision_kinds[int(t)][r['symbol']]=kind
        self.daily_prices={s:dict(zip(window['daily'].filter(pl.col('symbol')==s)['close_us'].to_list(),
            window['daily'].filter(pl.col('symbol')==s)['close'].to_list(),strict=True)) for s in self.symbols}
        self.account=account_for_cost(cost,self.symbols,account_factory)
        self.rows_written=0
        self.event_cursor=0
        self.pending={}
        self.sequence=0
        self.terminal=False
        self.funding_journal=[]
        self.rejections=[]
        self.breaches=[]
        self.extrema=[]
        self.peak=self.min_nav=self.min_free=10000.
        self.mdd=self.max_gross=0.
        self.max_asset={s:0. for s in self.symbols}
        self.completion='COMPLETE_CONDITIONAL_ACCOUNT'
        self.stop=self.first_entry=None
        self.previous_quote=None
        self.cursor=self.start
        self.minute_chunks=[]
        self.target_rows=[]
        self.budget=None
        self.controller_state={}
        self.tape=MarketTape(window,self.symbols)
        self._bind_callback()

    def _bind_callback(self):
        if hasattr(self.account,'liquidation_callback'):
            self.account.liquidation_callback=self._cancel_liquidated_intents

    def _cancel_liquidated_intents(self,symbol,event_us):
        order=self.pending.pop(symbol,None)
        if order is not None:
            self.rejections.append(dict(symbol=symbol,event_us=event_us,order_id=order['order_id'],
                                        reason='CANCELLED_BY_ISOLATED_LIQUIDATION'))

    def fork(self):
        """Trusted in-process fork; deep financial copy, shared read-only tape/chunks.

        The account class's validated from_snapshot remains the disk recovery
        path. It is deliberately not used for each candidate action.
        """
        branch=object.__new__(type(self))
        shared={'window','symbols','decisions','daily_prices','tape','targets','meta'}
        for name,value in vars(self).items():
            if name in shared:setattr(branch,name,value)
            elif name=='minute_chunks':setattr(branch,name,list(value))
            elif name=='account':
                callback=getattr(value,'liquidation_callback',None)
                memo={id(callback):None} if callback is not None else {}
                # Profiles are a read-only mapping of frozen dataclass values.
                memo[id(value.instrument_profiles)]=value.instrument_profiles
                setattr(branch,name,deepcopy(value,memo))
            else:setattr(branch,name,deepcopy(value))
        branch._bind_callback()
        return branch

    def snapshot(self):
        """Full portable recovery including exact journal and scheduling state."""
        keys=('rows_written','event_cursor','pending','sequence','terminal','funding_journal',
              'rejections','breaches','extrema','peak','mdd','min_nav','min_free','max_gross',
              'max_asset','completion','stop','first_entry','previous_quote','cursor','budget',
              'controller_state','weights','decision_kinds','target_rows')
        state={k:deepcopy(getattr(self,k)) for k in keys}
        state['pending']={s:{**o,'target':str(o['target'])} for s,o in self.pending.items()}
        state['weights']={str(t):v for t,v in self.weights.items()}
        state['decision_kinds']={str(t):v for t,v in self.decision_kinds.items()}
        return dict(version=self.VERSION,market_range=[self.start,self.end],symbols=list(self.symbols),
                    mode=self.mode,cost=self.cost,unit=self.unit,persist_cash_close=self.persist_cash_close,
                    final_day_target_zero=self.final_day_target_zero,target_meta=self.meta,
                    targets=self.targets.to_dicts() if self.targets is not None else None,
                    account=self.account.snapshot(),state=state,
                    minute_chunks=[chunk.tolist() for chunk in self.minute_chunks])

    @classmethod
    def from_snapshot(cls,snapshot,window,*,account_class=USDTLinearPerpetualAccount):
        need(snapshot['version']==cls.VERSION and snapshot['market_range']==[window['start'],window['end']],
             'Scheduler version and exact global calendar')
        result=cls(window,snapshot['mode'],snapshot['cost'],snapshot['unit'],
                   persist_cash_close=snapshot['persist_cash_close'],
                   final_day_target_zero=snapshot['final_day_target_zero'])
        need(list(result.symbols)==snapshot['symbols'],'Exact symbol order')
        result.account=account_class.from_snapshot(snapshot['account'],expected_symbols=result.symbols)
        result.meta=deepcopy(snapshot['target_meta'])
        result.targets=pl.DataFrame(snapshot['targets']) if snapshot['targets'] is not None else None
        for k,v in snapshot['state'].items():setattr(result,k,deepcopy(v))
        result.pending={s:{**o,'target':D(o['target'])} for s,o in result.pending.items()}
        result.weights={int(t):v for t,v in result.weights.items()}
        result.decision_kinds={int(t):v for t,v in result.decision_kinds.items()}
        result.minute_chunks=[np.asarray(chunk,dtype=np.float64) for chunk in snapshot['minute_chunks']]
        for chunk in result.minute_chunks:chunk.flags.writeable=False
        need(result.cursor==result.start+result.rows_written*MINUTE or result.stop is not None,
             'Recovery minute cursor mismatch')
        while result.tape.expected<result.cursor:
            result.tape.day(result.tape.expected)
        result._bind_callback()
        return result

    def state_hash(self):
        # Past append-only receipt bodies do not affect transition state; their
        # identities and totals do. Include all scheduler/controller live state.
        account={k:v for k,v in vars(self.account).items() if k not in
                 ('trades','funding','liquidations','liquidation_callback')}
        live={k:v for k,v in vars(self).items() if k not in
              ('window','tape','account','minute_chunks','targets','meta','target_rows',
               'funding_journal','rejections','extrema','weights','decision_kinds','daily_prices')}
        def exact(v):
            if isinstance(v,dict):return {str(k):exact(x) for k,x in v.items()}
            if isinstance(v,(tuple,list)):return [exact(x) for x in v]
            if isinstance(v,np.ndarray):return v.tolist()
            if hasattr(v,'__dataclass_fields__'):return {k:exact(getattr(v,k)) for k in v.__dataclass_fields__}
            if isinstance(v,(str,int,float,bool)) or v is None:return v
            return str(v)
        payload=dict(account=exact(account),scheduler=exact(live),
                     journal_counts=[len(self.account.trades),len(self.account.funding),
                                     len(getattr(self.account,'liquidations',[]))])
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

    def observe(self,stamp,cause):
        nav=float(self.account.nav());need(math.isfinite(nav),'Finite account NAV')
        self.min_free=min(self.min_free,float(self.account.free_cash))
        before=(self.peak,self.min_nav,self.mdd);self.peak=max(self.peak,nav);self.min_nav=min(self.min_nav,nav)
        if self.peak>0:self.mdd=max(self.mdd,1-nav/self.peak)
        signed={s:float(self.account.positions[s].quantity)*float(self.account.marks[s][-1]['price'])
                if self.account.positions[s].quantity else 0. for s in self.symbols}
        gross=sum(abs(x) for x in signed.values())/nav if nav>0 else None
        if gross is not None:
            self.max_gross=max(self.max_gross,gross)
            for s in self.symbols:self.max_asset[s]=max(self.max_asset[s],abs(signed[s])/nav)
        if before!=(self.peak,self.min_nav,self.mdd):
            # Only final extrema witnesses, not a second unbounded minute ledger.
            for label,changed in [('MAX_PEAK',before[0]!=self.peak),('MIN_NAV',before[1]!=self.min_nav),('MAX_DRAWDOWN',before[2]!=self.mdd)]:
                if changed:
                    self.extrema[:]=[r for r in self.extrema if r['kind']!=label]
                    self.extrema.append(dict(kind=label,event_us=int(stamp),cause=cause,NAV=nav,
                        peak_NAV=self.peak,max_drawdown=self.mdd,account_status=self.account.status))
        return nav

    def schedule(self,target,signal,kind,only_symbols=None):
        for s in self.symbols if only_symbols is None else only_symbols:
            order_kind=kind[s] if isinstance(kind,dict) else kind
            if s in self.pending:self.rejections.append(dict(symbol=s,event_us=int(signal),
                reason='SUPERSEDED_BY_'+order_kind,old_signal_us=self.pending[s]['signal_us']))
            self.sequence+=1
            self.pending[s]=dict(target=D(str(target[s])),signal_us=int(signal),kind=order_kind,attempts=0,
                order_id=f'{self.mode}-{self.cost["id"]}-{self.unit["id"]}-{self.sequence}')

    def risk_schedule(self,stamp):
        if self.account.status!='BOUND_BREACH_REDUCTION_REQUIRED' or self.terminal:return
        if any(o['kind']=='RISK_REDUCTION' for o in self.pending.values()):return
        nav=self.account.nav();notionals=[abs(self.account.positions[s].quantity)*self.account.marks[s][-1]['price']
                                   if self.account.positions[s].quantity else ZERO for s in self.symbols]
        scale=min(D(1),self.account.config.max_asset_weight*D('.99')*nav/max(notionals) if max(notionals)>0 else D(1),
                  self.account.config.max_gross_weight*D('.99')*nav/sum(notionals,ZERO) if sum(notionals,ZERO)>0 else D(1))
        self.breaches.append(dict(signal_us=int(stamp),gross_weight=float(sum(notionals,ZERO)/nav),
            asset_weights={s:float(v/nav) for s,v in zip(self.symbols,notionals,strict=True)},
            phase='ACTUAL_DRIFT_BEFORE_CAPACITY_LIMITED_REDUCTION',scale=float(scale)))
        self.schedule({s:self.account.positions[s].quantity*scale for s in self.symbols},stamp,'RISK_REDUCTION')

    def funding_through(self,limit,inclusive):
        while self.event_cursor<len(self.window['events']):
            raw=self.window['events'][self.event_cursor];e=raw['event_us']
            if e>limit or not inclusive and e==limit:break
            s=raw['symbol'];quantity=self.account.positions[s].quantity
            rate=D(str(raw['raw_rate']))*D(str(self.unit['scale']))
            self.observe(e,'BEFORE_FUNDING')
            if not self.account.marks[s]:
                need(quantity==0,
                     'No past mark permits only this instrument\'s verified zero ownership')
                receipt=dict(symbol=s,event_us=e,event_id=f'{s}:{e}',owned=False,quantity=0.,
                    signed_funding_USDT=0.,mark_price=None,mark_close_us=None,
                    status='NO_POSITION_NO_PAST_MARK',account_status=self.account.status)
            else:
                receipt=self.account.apply_funding(s,f'{s}:{e}',e,rate,e)
            self.funding_journal.append({**receipt,**raw,'conditional_rate_scale':self.unit['scale'],
                'assumed_fraction_decimal':str(rate),'raw_rate_unit':'UNCONFIRMED',
                'rate_publication_assumption':'EVENT_TIME_CONDITIONAL_NOT_CERTIFIED'})
            self.event_cursor+=1;self.observe(e,'AFTER_FUNDING')
            if self.account.status in HALTS:
                self.completion='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED';self.stop=e;return
            self.risk_schedule(e)

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
            elif order['attempts']>=5:
                if order['kind']=='PROTECTIVE_STOP':continue
                if self.persist_cash_close and order['kind']=='DAILY_TARGET' and order['target']==ZERO:
                    # Still capacity limited and reduce-only. A newer target,
                    # hard-risk instruction or terminal order may supersede it.
                    continue
                self.rejections.append(dict(symbol=s,event_us=event,order_id=order['order_id'],reason='FIVE_ATTEMPTS_EXPIRED',
                    remaining_signed_quantity=float(remaining),kind=order['kind']))
                self.pending.pop(s,None)
                if order['kind']=='RISK_REDUCTION' and self.account.status=='BOUND_BREACH_REDUCTION_REQUIRED':
                    self.completion='NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION';self.stop=event;return
                if order['kind'] in ('POOL_EXIT','DATA_GAP_EXIT') and self.account.positions[s].quantity:
                    self.completion='NOT_EVALUABLE_UNEXECUTABLE_ASSET_EXIT';self.stop=event;return

    def advance_day(self, target_weights=None, *, decision_kinds=None):
        """Continue exactly one day. The global final day keeps charged terminal fills."""
        need(self.stop is None and self.cursor<self.end,'Cannot advance halted or ended wallet')
        if target_weights is not None:
            need(set(target_weights)==set(self.symbols),'Exact ordered daily portfolio')
            w=np.asarray([target_weights[s] for s in self.symbols],dtype=float)
            need(np.isfinite(w).all() and np.abs(w).max()<=.3+1e-12 and np.abs(w).sum()<=.6+1e-12,
                 'Existing .30 asset and .60 gross target caps')
            self.weights[self.cursor]=dict(zip(self.symbols,w.tolist(),strict=True))
            self.decision_kinds[self.cursor]=decision_kinds or dict.fromkeys(self.symbols,'DAILY_TARGET')
        need(self.cursor in self.weights,'Explicit target required for each decision')
        if self.final_day_target_zero and self.cursor+DAY>=self.end:
            self.weights[self.cursor]=dict.fromkeys(self.symbols,0.)
        self.target_rows.extend(dict(available_us=self.cursor,symbol=s,target_weight=self.weights[self.cursor][s])
                                for s in self.symbols)
        values=[]
        before=self.account.nav()
        day_end=min(self.cursor+DAY,self.end)
        for t,market_row in self.tape.day(self.cursor):
            absent=set(self.symbols)-set(market_row)
            if any(self.account.positions[s].quantity for s in absent):
                self.completion='NOT_EVALUABLE_MISSING_HELD_ASSET_EXECUTION_OR_MARK';self.stop=t
                self.rejections.append(dict(event_us=t,reason='MISSING_HELD_MARK_OR_EXECUTION',symbols=sorted(absent)))
                break
            need(all(math.isfinite(float(v)) and (v>=0 if k in ('quote_volume','volume') else v>0)
                     for row in market_row.values() for k,v in row.items()),'Finite actual block values')
            t=int(t);close=t+MINUTE
            if t in self.weights and not self.terminal:
                # All signal quantities freeze before rates later than this decision and future opens.
                nav=self.account.nav()
                desired={s:D(str(self.weights[t][s]))*D('.99')*nav/D(str(self.daily_prices[s][t]))
                         if self.weights[t][s]!=0 else ZERO for s in self.symbols}
                if self.account.status=='ACTIVE':self.schedule(desired,t,self.decision_kinds[t])
            if t==self.end-6*MINUTE:
                self.terminal=True;self.schedule(dict.fromkeys(self.symbols,ZERO),t,'TERMINAL')
            self.funding_through(t+1,True)
            if self.stop is not None:break
            self.attempt(t,market_row)
            if self.stop is not None:break
            self.funding_through(close,False)
            if self.stop is not None:break
            self.account.update_marks(close,{s:dict(price=D(str(market_row[s]['mark'])),
                close_us=close,available_us=close) for s in market_row})
            self.observe(close,'MINUTE_MARK')
            if self.account.status in HALTS:
                self.completion='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED';self.stop=close;break
            self.funding_through(close,True)
            if self.stop is not None:break
            self.risk_schedule(close)
            nav=self.account.nav();signed={s:self.account.positions[s].quantity*self.account.marks[s][-1]['price']
                                     if self.account.positions[s].quantity else ZERO for s in self.symbols}
            equities={s:self.account.positions[s].isolated_balance+self.account.positions[s].quantity*
                (self.account.marks[s][-1]['price']-self.account.positions[s].entry_price)
                if self.account.positions[s].quantity else self.account.positions[s].isolated_balance for s in self.symbols}
            values.append([float(nav),float(self.account.free_cash),float(sum((p.isolated_balance for p in self.account.positions.values()),ZERO)),
                float(sum((abs(v) for v in signed.values()),ZERO)),float(sum(signed.values(),ZERO)),float(self.account.fees),
                float(self.account.execution_cost),float(self.account.funding_cash),float(self.account.gross_fill_turnover),
                *[float(self.account.positions[s].quantity) for s in self.symbols],*[float(signed[s]) for s in self.symbols],
                *[float(self.account.positions[s].isolated_balance) for s in self.symbols],*[float(equities[s]) for s in self.symbols],
                *[float(signed[s]/nav) if nav>0 else 0. for s in self.symbols],
                float(sum((abs(v) for v in signed.values()),ZERO)/nav) if nav>0 else 0.,
                float(sum(signed.values(),ZERO)/nav) if nav>0 else 0.])
            self.rows_written+=1
            self.previous_quote={s:market_row[s]['quote_volume'] if s in market_row else 0. for s in self.symbols}
        chunk=np.asarray(values,dtype=np.float64).reshape((-1,11+5*len(self.symbols)))
        chunk.flags.writeable=False
        self.minute_chunks.append(chunk)
        self.cursor=day_end if self.stop is None else int(self.stop)
        return dict(start_us=day_end-DAY,end_us=day_end,net_increment_USDT=float(self.account.nav()-before),
                    completed=self.stop is None,completion=self.completion,stop_us=self.stop)

    def result(self):
        values=np.concatenate(self.minute_chunks,axis=0) if self.minute_chunks else np.empty((0,11+5*len(self.symbols)))
        n=(self.end-self.start)//MINUTE
        nearest_funding_ties=[]
        for r in self.funding_journal:
            near=[f['event_us'] for f in self.account.trades if f['symbol']==r['symbol']
                  and abs(f['event_us']-r['event_us'])<=5_000_000]
            if near:nearest_funding_ties.append(dict(symbol=r['symbol'],event_us=r['event_us'],nearby_fill_us=near,
                ownership_native_certified=False))
        columns=['nav','free_cash','isolated_balance','gross_notional','net_signed_notional','cumulative_fees',
            'cumulative_execution_costs','cumulative_funding','cumulative_turnover',
            *[s+'_quantity' for s in self.symbols],*[s+'_signed_marked_notional' for s in self.symbols],
            *[s+'_isolated_balance' for s in self.symbols],*[s+'_isolated_equity' for s in self.symbols],
            *[s+'_signed_weight' for s in self.symbols],'gross_weight','net_signed_weight']
        minute=pl.DataFrame(values,schema=columns,orient='row').with_columns(
            pl.Series('close_us',np.arange(self.start,self.start+self.rows_written*MINUTE,MINUTE,dtype=np.int64)+MINUTE))
        summary=self.account.summary()
        terminal_prices={s:float(self.account.marks[s][-1]['price']) if self.account.marks[s] else None for s in self.symbols}
        terminal_signed={s:float(self.account.positions[s].quantity)*terminal_prices[s]
                         if self.account.positions[s].quantity else 0. for s in self.symbols}
        summary.update(symbols=list(self.symbols),completion=self.completion,mode=self.mode,cost_scenario=self.cost,unit_scenario=self.unit,
            funding_rate_unit='UNCONFIRMED',unit_certified=False,publication_certified=False,
            completed_minutes=self.rows_written,required_minutes=n,stop_us=self.stop,all_observation_max_drawdown=self.mdd,
            maximum_actual_gross_weight=self.max_gross,maximum_actual_asset_weights=self.max_asset,
            funding_original_events=len(self.window['events']),funding_observed_events=len(self.funding_journal),
            funding_account_applied_events=len(self.account.funding),
            fresh_flat_no_past_mark_events=sum(r.get('status')=='NO_POSITION_NO_PAST_MARK' for r in self.funding_journal),
            funding_owned_events=sum(bool(r['owned']) for r in self.funding_journal),
            funding_deferred_after_halt_events=len(self.window['events'])-self.event_cursor,
            first_entry_us=self.first_entry,terminal_marked_notional=summary['gross_notional'],
            terminal_mark_prices=terminal_prices,terminal_signed_marked_notional=terminal_signed,
            terminal_cash_realized=all(p.quantity==0 for p in self.account.positions.values()),
            terminal_not_forced_free_fill=True,pending_orders_at_stop={s:{**r,'target':str(r['target'])} for s,r in self.pending.items()},
            funding_fill_5second_uncertainty_witnesses=nearest_funding_ties,candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE')
        summary['minimum_actual_free_cash_all_observations_USDT']=self.min_free
        if self.persist_cash_close:
            summary['cash_close_retry_policy']='PERSIST_DAILY_ZERO_TARGET_UNTIL_FILLED_OR_SUPERSEDED_NO_FREE_FILL'
        summary['actual_caps_instantaneously_guaranteed']=False
        summary['margin_risk_observation_scope']='CAUSALLY_AVAILABLE_MINUTE_CLOSE_MARKS_PLUS_FILLS_AND_FUNDING_NOT_INTRAMINUTE_MARK_EXTREMES_OR_NATIVE_RISK_TIERS'
        summary['risk_reduction_signal_count']=len(self.breaches)
        delays=[r['reduction_latency_us'] for r in self.breaches if 'reduction_latency_us' in r]
        summary['maximum_observed_first_risk_reduction_latency_us']=max(delays) if delays else None
        result=dict(summary=summary,targets=(self.targets if self.targets is not None else pl.DataFrame(self.target_rows)),target_meta=self.meta,minute=minute,trades=self.account.trades,
            funding=self.funding_journal,rejections=self.rejections,breaches=self.breaches,extrema=self.extrema)
        if hasattr(self.account,'liquidations'):result['liquidations']=self.account.liquidations
        return result
