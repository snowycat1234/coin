"""Generated-only CSH_H090_CONTROL on pinned native clocks and Decimal finance.

The separate boundary validates both direct and preloaded targets. It preserves
native scheduling, .99 sizing, direction locks, reductions, capacity, funding,
and reviewed terminal60. It does not implement finite/grid ownership or restore.
"""
from copy import deepcopy
from dataclasses import dataclass, asdict
from decimal import Decimal as D
from itertools import product
from types import MappingProxyType
import hashlib,json,math
import numpy as np
from cost_factory import (PORT,ORIGINAL_ACCOUNT,NATIVE,POLICY,COSTS,
                          ORIGINAL_FINANCE,ORIGINAL_TARGETS,h090_factory)
from scripts.investment.resumable_perpetual import DAY,MINUTE,need,HALTS,ZERO
import h090_risk_controller as risk
from calendar_readiness_v2 import SourcePacket,SourceReadinessError
S=POLICY.SYMBOLS


@dataclass(frozen=True)
class NativeH090Descriptor:
    version:str='H090_NATIVE_CONTROL_GENERATED_V1'
    control_id:str='CSH_H090_CONTROL'
    gross_cap:float=.90
    asset_cap:float=.30
    annual_vol_target:float=.15
    original_gross_cap:float=.60
    original_asset_cap:float=.30
    original_annual_vol_target:float=.10
    original_weight_multiplier:float=1.5
    isolated_leverage:int=1
    automatic_topup:bool=False
    initial_cash:str='10000'
    planned_commitment_cap:str='9000'
    maximum_actual_isolated_margin:str='8500'
    increase_free_cash_floor:str='1000'
    def __post_init__(self):
        expected=('H090_NATIVE_CONTROL_GENERATED_V1','CSH_H090_CONTROL',.90,.30,.15,
                  .60,.30,.10,1.5,1,False,'10000','9000','8500','1000')
        if tuple(vars(self).values())!=expected or type(self.isolated_leverage) is not int or type(self.automatic_topup) is not bool:
            raise ValueError('EXACT_FIXED_NATIVE_H090_DESCRIPTOR_REQUIRED')

DESCRIPTOR=NativeH090Descriptor()


@dataclass(frozen=True)
class SyntheticSourceRegistry:
    """Explicit external pins for GENERATED fixtures; never real-source authority.

    Pins are supplied separately from packets. This adapter never chooses an
    approved hash from a packet. Real provider/index/arrival closure is missing,
    so this type is intentionally unable to admit historical execution.
    """
    approvals:object
    scope:str='GENERATED_ONLY_NOT_REAL_PROVIDER_OR_ARRIVAL_CERTIFICATION'
    def __post_init__(self):
        if self.scope!='GENERATED_ONLY_NOT_REAL_PROVIDER_OR_ARRIVAL_CERTIFICATION':
            raise ValueError('SYNTHETIC_SOURCE_REGISTRY_ONLY_HISTORY_NO_GO')
        if not isinstance(self.approvals,dict) or not self.approvals:
            raise ValueError('EXPLICIT_SYNTHETIC_SOURCE_PINS_REQUIRED')
        approved={}
        for t,row in self.approvals.items():
            if type(t) is not int or t<0 or t%DAY or not isinstance(row,dict) or set(row)!={'manifest_SHA256','source_index_SHA256'}:
                raise ValueError('EXACT_DAILY_SYNTHETIC_SOURCE_REGISTRY_SCHEMA')
            for value in row.values():
                if not isinstance(value,str) or len(value)!=64 or any(x not in '0123456789abcdef' for x in value):
                    raise ValueError('SHA256_SOURCE_REGISTRY_PIN_REQUIRED')
            approved[t]=MappingProxyType(dict(row))
        object.__setattr__(self,'approvals',MappingProxyType(approved))

    def check(self,packet,t):
        if t not in self.approvals:
            raise SourceReadinessError('EXTERNAL_SOURCE_APPROVAL_MISSING')
        if type(packet) is not SourcePacket:
            raise SourceReadinessError('PIN_BOUND_SOURCE_PACKET_REQUIRED')
        approved=self.approvals[t]
        if packet.approved_manifest_sha256!=approved['manifest_SHA256']:
            raise SourceReadinessError('EXTERNAL_APPROVED_MANIFEST_MISMATCH')
        try:
            manifest=json.loads(packet.manifest_bytes)
        except (ValueError,UnicodeError,TypeError) as error:
            raise SourceReadinessError('MALFORMED_EXTERNAL_SOURCE_MANIFEST') from error
        if not isinstance(manifest,dict) or manifest.get('source_index_SHA256')!=approved['source_index_SHA256']:
            raise SourceReadinessError('EXTERNAL_APPROVED_SOURCE_INDEX_MISMATCH')

    def identity(self):
        return {str(t):dict(row) for t,row in self.approvals.items()}


def original_weight_guard(weights):
    if not isinstance(weights,dict) or set(weights)!=set(S):
        raise ValueError('EXACT_ORIGINAL_CORE5_TARGET_REQUIRED')
    a=np.asarray([weights[s] for s in S])
    if a.dtype.kind not in 'fi' or a.shape!=(5,):
        raise ValueError('ORIGINAL_FIVE_NUMERIC_WEIGHTS_REQUIRED')
    a=np.asarray(a,dtype=float)
    # This is the exact original scheduler's .30/.60 tolerance, not an
    # invented universal .10 per-asset condition.
    if not np.isfinite(a).all() or np.abs(a).max()>.3+1e-12 or np.abs(a).sum()>.6+1e-12:
        raise ValueError('EXISTING_ORIGINAL_030_060_TARGET_CAPS_REQUIRED')
    return a


def h090_weight_guard(weights,descriptor):
    if type(descriptor) is not NativeH090Descriptor or descriptor!=DESCRIPTOR:
        raise ValueError('EXACT_FIXED_NATIVE_H090_DESCRIPTOR_REQUIRED')
    if not isinstance(weights,dict) or set(weights)!=set(S):
        raise ValueError('EXACT_NATIVE_H090_CORE5_TARGET_REQUIRED')
    return risk.validate_weights([weights[s] for s in S])


def _frame_guard(frame,clocks,*,h090=False):
    pl=PORT.native.pl
    if not isinstance(frame,pl.DataFrame):raise ValueError('EXACT_POLARS_TARGET_FRAME_REQUIRED')
    fields=['available_us','symbol','target_weight']
    if frame.columns not in (fields,fields+['eligibility_reason']):
        raise ValueError('EXACT_NATIVE_TARGET_COLUMNS_REQUIRED')
    if frame.schema['available_us']!=pl.Int64 or frame.schema['symbol']!=pl.String or frame.schema['target_weight']!=pl.Float64:
        raise ValueError('EXACT_NATIVE_TARGET_DTYPES_REQUIRED')
    if frame.height!=len(clocks)*5 or any(frame[f].null_count() for f in fields):
        raise ValueError('COMPLETE_NONNULL_NATIVE_TARGET_FRAME_REQUIRED')
    if not np.array_equal(frame['available_us'].to_numpy(),np.repeat(clocks,5)) or frame['symbol'].to_list()!=list(S)*len(clocks):
        raise ValueError('EXACT_TARGET_CLOCK_AND_CORE5_ORDER_REQUIRED')
    for i,t in enumerate(clocks):
        rows=frame.slice(i*5,5).to_dicts()
        weights={r['symbol']:r['target_weight'] for r in rows}
        h090_weight_guard(weights,DESCRIPTOR) if h090 else original_weight_guard(weights)
        for row in rows:
            reason=row.get('eligibility_reason','ELIGIBLE')
            if reason not in ('ELIGIBLE','POOL_EXIT','WARMUP_OR_DATA_GAP'):
                raise ValueError('ORIGINAL_TARGET_ELIGIBILITY_REASON_REQUIRED')
            if reason!='ELIGIBLE' and row['target_weight']!=0:
                raise ValueError('ORIGINAL_EXIT_CANNOT_ADD_RISK')
    return frame


def original_control(window, cost, unit, *, target_factory=None):
    """Use the unchanged .60 terminal60 class/account, with preload cap checking."""
    wrapped=None
    if target_factory is not None:
        def wrapped(daily,clocks,mode):
            frame,meta=target_factory(daily,clocks,mode)
            return _frame_guard(frame,clocks),meta
    return NATIVE(window,'LONG_SHORT',cost,unit,target_factory=wrapped,account_factory=ORIGINAL_ACCOUNT)


class H090NativeControl(NATIVE):
    VERSION='h090_native_single_control_generated_v1'

    def __init__(self,window,mode,cost,unit,*,source_registry,source_packets=None,
                 target_factory=None,descriptor=DESCRIPTOR,persist_cash_close=False,
                 final_day_target_zero=False):
        if window.get('fixture_scope')!='GENERATED_NATIVE_FINANCE_ONLY' or 'minute_blocks' in window:
            raise ValueError('GENERATED_ONLY_NO_HISTORICAL_ENTRY')
        if type(descriptor) is not NativeH090Descriptor or descriptor!=DESCRIPTOR:
            raise ValueError('EXACT_FIXED_NATIVE_H090_DESCRIPTOR_REQUIRED')
        if type(source_registry) is not SyntheticSourceRegistry or mode!='LONG_SHORT':
            raise ValueError('EXPLICIT_SYNTHETIC_SOURCE_REGISTRY_AND_ORIGINAL_LONG_SHORT_REQUIRED')
        self.descriptor=descriptor
        self.source_registry=source_registry
        self.source_packets=dict(source_packets or {})
        self.original_weights={}
        self.risk_contexts={}
        self.policy_events=[]
        self.reservations=POLICY.ReservationBook()
        self.reservations.reserve('CSH_H090_CONTROL',D('9000'))
        self.processed_native_receipts={}
        wrapped=None
        if target_factory is not None:
            def wrapped(daily,clocks,mode):
                frame,meta=target_factory(daily,clocks,mode)
                _frame_guard(frame,clocks)
                output=[]
                for i,t in enumerate(clocks):
                    t=int(t);rows=frame.slice(i*5,5).to_dicts()
                    original={r['symbol']:r['target_weight'] for r in rows}
                    prepared=self._prepare(t,original,self.source_packets.get(t))
                    for row in rows:
                        output.append(dict(available_us=t,symbol=row['symbol'],
                            target_weight=prepared['weights'][row['symbol']],
                            eligibility_reason=row.get('eligibility_reason','ELIGIBLE') if prepared['ready'] else 'WARMUP_OR_DATA_GAP'))
                result=PORT.native.pl.DataFrame(output)
                _frame_guard(result,clocks,h090=True)
                return result,{**meta,'control_id':'CSH_H090_CONTROL',
                    'fixed_original_weight_multiplier':1.5,'historical_status':'NO_GO',
                    'real_provider_arrival_authority':'UNAVAILABLE'}
        super().__init__(window,mode,cost,unit,target_factory=wrapped,
                         account_factory=h090_factory(cost),
                         persist_cash_close=persist_cash_close,
                         final_day_target_zero=final_day_target_zero)
        self.account.risk_admission=self._atomic_risk_admission
        if tuple(self.symbols)!=S:
            raise ValueError('EXACT_CORE5_NATIVE_ORDER_REQUIRED')

    def _prepare(self,t,original,packet):
        w=original_weight_guard(original)
        self.original_weights[t]=dict(zip(S,w.tolist(),strict=True))
        try:
            self.source_registry.check(packet,t)
            # Both certified risk and signal availability are required here.
            try:
                sized,meta,cov=risk.size_h090(1.5*w,packet,decision_us=t,signal_interval_minutes=1440)
            except risk.RiskGateError as error:
                if str(error) not in ('INVALID_COVARIANCE_RISK','POST_SCALE_VOLATILITY_INVALID'):
                    raise
                raise SourceReadinessError('CERTIFIED_SOURCE_COVARIANCE_INVALID:'+str(error)) from error
            sigma=float(np.sqrt(max(0.,float(w@cov@w))))
            if not math.isfinite(sigma) or sigma>.10+1e-12:
                raise ValueError('FROZEN_ORIGINAL_010_VOL_TARGET_IDENTITY_REQUIRED')
            result={'ready':True,'weights':dict(zip(S,sized.tolist(),strict=True)),
                    'covariance':cov,'risk_metadata':meta,'original_annual_vol':sigma}
        except SourceReadinessError as error:
            # Normalize only the source parser/approval error family. Financial
            # errors, bad descriptors and invalid original targets are not gaps.
            result={'ready':False,'weights':dict.fromkeys(S,0.),'covariance':None,
                    'source_error':str(error)}
        self.risk_contexts[t]=result
        return result

    def _admit_decision(self,t,target_weights,original_csh_weights,source_packet,decision_kinds):
        if target_weights is not None:
            h090_weight_guard(target_weights,self.descriptor)
        original=original_csh_weights if original_csh_weights is not None else self.original_weights.get(t)
        if original is None:
            raise ValueError('FROZEN_ORIGINAL_CSH_TARGET_REQUIRED_NOT_DIRECT_H090_INJECTION')
        packet=source_packet if source_packet is not None else self.source_packets.get(t)
        prepared=self._prepare(t,original,packet)
        if source_packet is not None:self.source_packets[t]=source_packet
        if prepared['ready']:
            expected=prepared['weights']
            if target_weights is not None and any(target_weights[s]!=expected[s] for s in S):
                raise ValueError('DIRECT_H090_TARGET_MUST_EQUAL_CERTIFIED_FIXED15_ORIGINAL_PROPOSAL')
            if target_weights is None and t in self.weights and any(self.weights[t][s]!=expected[s] for s in S):
                raise ValueError('PRELOADED_H090_TARGET_CHANGED_AFTER_ADMISSION')
            self.weights[t]=dict(expected)
            if decision_kinds is not None:
                if not isinstance(decision_kinds,dict) or set(decision_kinds)!=set(S):
                    raise ValueError('EXACT_ORIGINAL_CORE5_DECISION_KINDS_REQUIRED')
                if any(k not in ('DAILY_TARGET','POOL_EXIT','DATA_GAP_EXIT') for k in decision_kinds.values()):
                    raise ValueError('ORIGINAL_DECISION_KINDS_REQUIRED')
                if any(decision_kinds[s]!='DAILY_TARGET' and expected[s]!=0 for s in S):
                    raise ValueError('EXIT_CANNOT_ADD_RISK')
                self.decision_kinds[t]=dict(decision_kinds)
            elif t not in self.decision_kinds:
                self.decision_kinds[t]=dict.fromkeys(S,'DAILY_TARGET')
            self.policy_events.append({'event_us':t,'kind':'H090_SOURCE_AND_TARGET_ADMITTED',
                'manifest_SHA256':packet.approved_manifest_sha256,
                'selected_returns_SHA256':prepared['risk_metadata']['selected_returns_SHA256']})
        else:
            self.weights[t]=dict.fromkeys(S,0.)
            self.decision_kinds[t]=dict.fromkeys(S,'DATA_GAP_EXIT')
            self.policy_events.append({'event_us':t,'kind':'SOURCE_INVALID_REDUCE_ONLY',
                'reason':prepared['source_error'],'inventory_erased':False,'free_closure':False})
        # Explicit new guard runs for EVERY path. The original .60 advance_day
        # stays byte-unchanged; the copied iteration below has no hidden preload
        # bypass and uses this distinct H090 identity before native execution.
        h090_weight_guard(self.weights[t],self.descriptor)

    def _atomic_risk_admission(self,args,kwargs):
        t=self.cursor
        context=self.risk_contexts.get(t)
        event=args[3] if len(args)>3 else kwargs.get('event_us')
        if not context or not context['ready'] or type(event) is not int or not t<=event<min(t+DAY,self.end):
            return {'allow_increases':False,'reason':'SOURCE_FRESHNESS_REQUIRED_FOR_INCREASE'}
        # Preview exact charged finance; this does not mutate the real account.
        raw=self.account.engine
        probe=deepcopy(raw,{id(raw.instrument_profiles):raw.instrument_profiles})
        probe.execute_fill(*args,**kwargs)
        nav=probe.nav()
        if nav<=0:return {'allow_increases':False,'reason':'NONPOSITIVE_ACTUAL_NAV'}
        prices=np.asarray([float(probe.marks[s][-1]['price']) if probe.marks[s]
                           else float(self.daily_prices[s][t]) for s in S])
        endpoints=[]
        for s in S:
            actual=probe.positions[s].quantity
            order=self.pending.get(s)
            target=order['target'] if order is not None else actual
            endpoints.append((actual,target) if target!=actual else (actual,))
        cov=context['covariance']
        worst_gross=worst_asset=worst_sigma=0.
        for point in product(*endpoints):
            w=np.asarray([float(v) for v in point])*prices/float(nav)
            gross=float(np.abs(w).sum());asset=float(np.abs(w).max())
            variance=float(w@cov@w)
            if not math.isfinite(variance) or variance < -1e-15:
                return {'allow_increases':False,'reason':'INVALID_ACTUAL_PENDING_COVARIANCE'}
            sigma=float(np.sqrt(max(variance,0.)))
            worst_gross=max(worst_gross,gross);worst_asset=max(worst_asset,asset);worst_sigma=max(worst_sigma,sigma)
            if gross>.90+1e-12 or asset>.30+1e-12 or sigma>.15+1e-12:
                return {'allow_increases':False,'reason':'SINGLE_OWNER_ACTUAL_PENDING_RISK_ENVELOPE'}
        return {'allow_increases':True,'reason':'PASS_SINGLE_OWNER_ACTUAL_PENDING_CORNER_ENVELOPE',
                'worst_gross':worst_gross,'worst_asset':worst_asset,'worst_annual_vol':worst_sigma}

    def attempt(self,open_us,market_row):
        before=len(self.account.trades)
        # Reuse the reviewed terminal60 attempt method, including both phases,
        # one shared prior-minute capacity, five ordinary and 60 terminal tries.
        super().attempt(open_us,market_row)
        for row in self.account.trades[before:]:
            key=row['fill_id']+':'+row['leg']
            digest=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if key in self.processed_native_receipts and self.processed_native_receipts[key]!=digest:
                raise AssertionError('CONFLICTING_NATIVE_RECEIPT_IDENTITY')
            self.processed_native_receipts[key]=digest

    def snapshot(self):
        result=super().snapshot()
        result['h090_binding']={'descriptor':asdict(self.descriptor),
            'source_registry':self.source_registry.identity(),
            'source_readiness':{str(t):{k:v for k,v in c.items() if k not in ('covariance',)}
                                for t,c in self.risk_contexts.items()},
            'original_weights':{str(t):v for t,v in self.original_weights.items()},
            'reservations':{o:str(v) for o,v in self.reservations.reservations.items()},
            'processed_native_receipts':dict(self.processed_native_receipts),
            'policy_events':deepcopy(self.policy_events),
            'account_class':POLICY.HighRiskToyAccount.VERSION,
            'config_class':'vendor_quant.perpetual_account.PerpetualConfig',
            'full_restore_status':'NOT_IMPLEMENTED_NOT_CERTIFIED_HISTORY_NO_GO'}
        return result

    @classmethod
    def from_snapshot(cls,*args,**kwargs):
        raise ValueError('NO_GO_EXACT_H090_SOURCE_OWNER_PENDING_AND_DECIMAL_RESTORE_PARITY_NOT_IMPLEMENTED')

    def fork(self):
        raise ValueError('NO_GO_H090_FORK_BINDING_NOT_CERTIFIED')

    def result(self):
        result=super().result()
        result['summary'].update(control_id='CSH_H090_CONTROL',historical_status='NO_GO',
            real_provider_arrival_authority='UNAVAILABLE',full_recovery='NOT_IMPLEMENTED_NOT_CERTIFIED',
            finite_program_strategy='NOT_IMPLEMENTED_OUT_OF_SCOPE',
            native_descriptor=asdict(self.descriptor),
            reservation_original_USDT={o:str(v) for o,v in self.reservations.reservations.items()},
            covariance_admission='SINGLE_CONTROL_OWNER_ACTUAL_PLUS_PENDING_CORNERS_PRE_FILL',
            increase_capital_admission='REVIEWED_EXACT_CHARGED_PREVIEW_8500_MARGIN_1000_FREE_CASH')
        result['h090_policy_events']=deepcopy(self.policy_events)
        return result

    def advance_day(self, target_weights=None, *, original_csh_weights=None, source_packet=None, decision_kinds=None):
        need(self.stop is None and self.cursor<self.end,'Cannot advance halted or ended wallet')
        self._admit_decision(self.cursor,target_weights,original_csh_weights,source_packet,decision_kinds)
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

