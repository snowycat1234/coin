"""Pure local source projection and original deterministic targets; no accounts.

The physically stored daily member has wider seen-DEV dates. Decode only its
three permitted fields, immediately mask before calculations, and bind actual
used 200-close prefixes. Never create an execution scope or iterate a provider.
"""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import importlib.util
import json
from pathlib import Path
import sys
from types import MappingProxyType
import numpy as np
import polars as pl

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
FROZEN=ROOT/'traditional_three_tier_freeze_20261015'
if str(FROZEN) not in sys.path:sys.path.insert(0,str(FROZEN))
import frozen_grid as g
if Path(g.__file__).resolve()!=FROZEN/'frozen_grid.py':raise ValueError('EXACT_FROZEN_GRID_REQUIRED')
S=g.SYMBOLS; DAY=g.DAY; MINUTE=60_000_000
YEAR=2021; FULL_START=1609459200000000; START=1617321600000000; END=1640995200000000
DAYS=274; MINUTES=394560
SOURCE_ROOT=ROOT/'native_2021_source_restore_20261015'
FINAL_PINS='4a54692b30be89882386a4c0eab93507743819c9ba765577351a5bfded0b0061'
QUALIFICATION='05be5842c31007a5924e5fb5b6545743263adfa1c36a47c1beff27dfb1131b85'
DAILY_MEMBER='small_inputs/Y2023.npz'
DAILY_SHA='1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f'
ALLOWED_START=1592265600000000 # 2020-06-16 UTC source-only warmup boundary
CONFIGS=tuple(s+'_'+t for s,t in g.CONFIGS)

def sha(b):return sha256(b).hexdigest()
def canonical(v):return json.dumps(plain(v),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def jsha(v):return sha(canonical(v))
def plain(v):
    if hasattr(v,'items'):return {k:plain(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [plain(x) for x in v]
    return v

def immutable(v):
    if isinstance(v,dict):return MappingProxyType({k:immutable(x) for k,x in v.items()})
    if isinstance(v,(tuple,list)):return tuple(immutable(x) for x in v)
    return v

def exact(path,digest,size=None):
    p=Path(path)
    if not p.is_file() or p.is_symlink() or any(x.is_symlink() for x in p.parents):raise ValueError('ORDINARY_EXACT_SOURCE_FILE_REQUIRED:'+str(p))
    b=p.read_bytes()
    if sha(b)!=digest or size is not None and len(b)!=size:raise ValueError('SOURCE_PIN_CHANGED:'+str(p))
    return b

def _source_pins(root):
    raw=exact(root/'FINAL_LOCAL_SOURCE_PINS.json',FINAL_PINS)
    receipt=json.loads(raw)
    if (receipt['historical_runs']!=0 or receipt['wallets_created']!=0 or receipt['holdout_reads']!=0
            or receipt['targets_generated']!=0 or receipt['denial_or_transfer_stop'] is not False):
        raise ValueError('EXACT_SOURCE_ONLY_COMPLETION_RECEIPT_REQUIRED')
    pins={r['path']:{'SHA256':r['SHA256'],'bytes':r['bytes']} for r in receipt['files']}
    pins['FINAL_LOCAL_SOURCE_PINS.json']={'SHA256':FINAL_PINS,'bytes':len(raw)}
    daily=exact(root/DAILY_MEMBER,DAILY_SHA)
    pins[DAILY_MEMBER]={'SHA256':DAILY_SHA,'bytes':len(daily)}
    bodies={name:exact(root/name,p['SHA256'],p['bytes']) for name,p in pins.items()}
    if pins['SOURCE_QUALIFICATION_2021_APR_DEC.json']['SHA256']!=QUALIFICATION:raise ValueError('EXACT_APR_DEC_QUALIFICATION_REQUIRED')
    return pins,bodies

def _month_arrays(raw,start,count):
    # Validate exact original container namespace, then project native fields.
    with np.load(BytesIO(raw),allow_pickle=False) as z:
        expected={'times','available_us'}|{s+'_'+k for s in S for k in
            ('open','high','low','close','volume','quote_volume','mark_open','mark_high','mark_low','mark')}
        if set(z.files)!=expected:raise ValueError('EXACT_ORIGINAL_2021_MONTH_NAMESPACE_REQUIRED')
        times=z['times'].copy();available=z['available_us'].copy()
        if (times.dtype!=np.dtype('int64') or times.shape!=(count,)
                or not np.array_equal(times,np.arange(start,start+count*MINUTE,MINUTE,dtype=np.int64))
                or not np.array_equal(available,times+MINUTE)):
            raise ValueError('EXACT_2021_SOURCE_OPEN_CLOSE_CLOCKS_REQUIRED')
        a={'times':times}
        for s in S:
            for k in ('open','close','quote_volume','mark'):
                v=z[s+'_'+k].copy()
                if (v.dtype!=np.dtype('float64') or v.shape!=(count,) or not np.isfinite(v).all()
                        or ((v<0).any() if k=='quote_volume' else (v<=0).any())):
                    raise ValueError('FINITE_GENUINE_NATIVE_2021_QUOTES_REQUIRED')
                a[s+'_'+k]=v
    for v in a.values():v.setflags(write=False)
    return a

@dataclass(frozen=True,slots=True)
class CapturedMinuteProvider:
    year:int
    months:tuple
    @property
    def identity(self):return [[name,start,count,sha(body),len(body),lo,hi] for name,start,count,body,lo,hi in self.months]
    def __call__(self):
        if self.year!=YEAR:raise ValueError('ONLY_PARTIAL_2021_PROVIDER_ALLOWED')
        cursor=START
        for name,start,count,body,lo,hi in self.months:
            a=_month_arrays(body,start,count)
            if start+lo*MINUTE!=cursor:raise ValueError('EXACT_PARTIAL_SOURCE_PROVIDER_ORDER_REQUIRED')
            for off in range(lo,hi,1440):
                stop=min(off+1440,hi)
                yield {'times':a['times'][off:stop],'market':{s:{k:a[s+'_'+k][off:stop]
                    for k in ('open','close','quote_volume','mark')} for s in S}}
            cursor=start+hi*MINUTE
        if cursor!=END:raise ValueError('EXACT_PARTIAL_SOURCE_END_REQUIRED')

def project(source_root=SOURCE_ROOT):
    root=Path(source_root).resolve();pins,bodies=_source_pins(root)
    index=json.loads(bodies['prepared_2021/SOURCE_INDEX.json'])
    qual=json.loads(bodies['SOURCE_QUALIFICATION_2021_APR_DEC.json'])
    if (index['status']!='PASS_FULL2021_REAL_TRADE_MARK_SOURCE_ONLY' or index['days']!=365
            or index['missing_minute_rows']!=0 or index['monthly_streams']!=120
            or index['true_daily_repair_added_minutes']!=21600
            or qual['decision_dates']!=DAYS or qual['selected_funding_events']!=4110
            or qual['full_Jan1_200close_admitted'] is not False):raise ValueError('EXACT_COMPLETE_2021_PARTIAL_READY_SOURCE_REQUIRED')
    # Only these three members are decompressed. The initial mask precedes
    # every price statistic, target, covariance or strategy calculation.
    with np.load(BytesIO(bodies[DAILY_MEMBER]),allow_pickle=False) as z:
        symbols=z['symbol_order'].copy();stored_times=z['close_available_us'].copy();stored_close=z['close'].copy()
    if tuple(symbols)!=S or len(stored_times)!=1463:raise ValueError('EXACT_STORED_DAILY_MEMBER_NAMESPACE_REQUIRED')
    allowed=(stored_times>=ALLOWED_START)&(stored_times<=END)
    t=stored_times[allowed].copy();p=stored_close[allowed].copy()
    projection=dict(stored_clock_rows=len(stored_times),stored_first_us=int(stored_times[0]),stored_last_us=int(stored_times[-1]),
        decompressed_fields=['symbol_order','close_available_us','close'],physically_decompressed_close_shape=list(stored_close.shape),
        immediate_permitted_projection_calendar=[ALLOWED_START,END],permitted_projection_rows=len(t),
        later_DEV_rows_enter_target_or_covariance_calculation=False,
        target_projection_calendar=[START-199*DAY,END-DAY],target_projection_rows=473,
        per_decision_maximum_source_available_equals_decision=True)
    del stored_times,stored_close
    use=(t>=START-199*DAY)&(t<END)
    target_t=t[use].copy();target_p=p[use].copy()
    decisions=np.arange(START,END,DAY,dtype=np.int64)
    if (len(target_t)!=473 or not np.isfinite(target_p).all() or (target_p<=0).any()
            or not np.array_equal(target_t,np.arange(START-199*DAY,END,DAY,dtype=np.int64))):
        raise ValueError('EXACT_PAST_ONLY_473_FULL_FIVE_CLOSES_REQUIRED')
    d,targets,covariance,proofs=g.build_target_grid(target_p,target_t,target_t.copy(),decisions)
    if len(d)!=DAYS:raise ValueError('EXACT_PARTIAL_274_DECISIONS_REQUIRED')
    for at,w in zip(d,qual['all_274_200close_windows'],strict=True):
        k=int(np.searchsorted(target_t,at));tt=target_t[k-199:k+1];pp=target_p[k-199:k+1]
        if (int(at)!=w['decision_us'] or sha(tt.tobytes())!=w['clock_SHA256']
                or sha(pp.tobytes())!=w['close_C_order_SHA256']):raise ValueError('TARGET_200_CLOSE_BITS_DIFFER_FROM_SOURCE_QUALIFICATION')
    with np.load(BytesIO(bodies['prepared_2021/DAILY_OHLC.npz']),allow_pickle=False) as z:
        if tuple(z['symbol_order'])!=S or not z['ready'].all():raise ValueError('EXACT_REAL_DAILY_CORE5_REQUIRED')
        actual_t=z['available_us'].copy();actual_close=z['close'].copy()
    k=np.searchsorted(t,actual_t)
    if not np.array_equal(t[k],actual_t) or p[k].tobytes()!=actual_close.tobytes():raise ValueError('ALL1825_ACTUAL_DAILY_BITS_MUST_MATCH_SAVED_CLOSES')
    rows=tuple(MappingProxyType(dict(symbol=s,close_us=int(at),available_us=int(at),close=float(target_p[i,j])))
        for i,at in enumerate(target_t) for j,s in enumerate(S))
    daily=pl.DataFrame([dict(symbol=s,close_us=int(at),close=float(target_p[i,j]))
        for i,at in enumerate(target_t) if START<=at<END for j,s in enumerate(S)])
    source_events=[r for r in json.loads(bodies['prepared_2021/EVENTS.json']) if START<=r['event_us']<END]
    events=[{k:r[k] for k in ('symbol','event_us','raw_rate','reported_interval_hours','raw_rate_unit')} for r in source_events]
    if len(events)!=4110 or len({(r['event_us'],r['symbol']) for r in events})!=4110:raise ValueError('EXACT4110_PARTIAL_FUNDING_EVENTS_REQUIRED')
    for e in source_events:
        q=e['strict_prior_mark']
        if (q is None or q['mark_available_us']>=e['event_us'] or not 0<q['strict_prior_age_us']<=MINUTE
                or e['reported_interval_hours']!=8. or e['raw_rate_unit']!='UNCONFIRMED'):
            raise ValueError('REAL_STRICT_PRIOR_PARTIAL_FUNDING_MARK_REQUIRED')
    provider=[];cursor=FULL_START;minute_checks=[]
    for rec in index['months']:
        name='prepared_2021/months/'+rec['month']+'.npz';b=bodies[name];count=rec['minutes']
        a=_month_arrays(b,cursor,count)
        if sha(b)!=rec['source_NPZ_SHA256'] or len(b)!=rec['source_NPZ_bytes']:raise ValueError('EXACT_ORIGINAL_MONTH_CONTAINER_REQUIRED')
        # Verify native daily closure and funding mark/capacity quotations from
        # captured bytes directly. Do not iterate CapturedMinuteProvider.
        for at in range(cursor+DAY,cursor+count*MINUTE+1,DAY):
            row=int(np.searchsorted(actual_t,at));off=(at-cursor)//MINUTE-1
            for j,s in enumerate(S):
                if a[s+'_close'][off].tobytes()!=actual_close[row,j].tobytes():raise ValueError('MONTHLY_TO_DAILY_PARITY_REQUIRED')
        for e in source_events:
            q=e['strict_prior_mark'];at=q['mark_open_us']
            if cursor<=at<cursor+count*MINUTE:
                off=(at-cursor)//MINUTE
                if a[e['symbol']+'_mark'][off].tobytes()!=np.float64(q['mark_close']).tobytes():raise ValueError('EXACT_NATIVE_FUNDING_MARK_QUOTE_REQUIRED')
        hi=count;lo=max(0,(START-cursor)//MINUTE)
        if lo<hi:
            provider.append((name,cursor,count,b,lo,hi))
            minute_checks.append(dict(month=rec['month'],first_native_open_us=cursor+lo*MINUTE,
                last_native_open_us=cursor+(hi-1)*MINUTE,native_minutes=hi-lo,
                all_previous_minute_quote_volumes_finite_nonnegative=True,
                initial_prior_volume_ignored_by_unchanged_coldstart=True))
        cursor+=count*MINUTE
    if sum(x['native_minutes'] for x in minute_checks)!=MINUTES:raise ValueError('EXACT394560_PARTIAL_NATIVE_MINUTES_REQUIRED')
    sidecar=dict(schema='GENUINE_2021_PARTIAL_NATIVE_MARK_PROVENANCE_V1',calendar=[START,END],
        quality_intervals=[],derived_mark_cells=0,forward_fill=False,trade_mark_substitution=False,
        full_source_completion_SHA256=FINAL_PINS,qualification_SHA256=QUALIFICATION,
        source_index_SHA256=pins['prepared_2021/SOURCE_INDEX.json']['SHA256'],
        all_4110_funding_prior_marks_recomputed_from_exact_captured_native_quotes=True,
        minute_quote_capacity_bindings=minute_checks,
        initial_signal_us=START,earliest_native_coldstart_increase_us=START+MINUTE+1,
        source_funding_coverage_is_not_ownership=True,old_Jan1_ownership_flag_omitted=True,
        funding_ownership='CURRENT_NATIVE_ACTUAL_QUANTITY_ONLY_AFTER_PAID_FILLS',
        terminal_signal_us=END-61*MINUTE,terminal_eligible_open_range=[END-60*MINUTE,END-MINUTE],
        latest_native_terminal_fill_us=END-MINUTE+1,
        source_end_plus_one_witness_is_not_execution_authority=True)
    window=MappingProxyType(dict(start=START,end=END,symbols=S,daily=daily,events=immutable(events),
        minute_blocks=CapturedMinuteProvider(YEAR,tuple(provider)),derived_mark_cells=0,
        original_missing_mark_open_ms=(),original_overlay_future_looking=False,
        original_overlay_execution_admitted=False,causal_mark_adapter=immutable(sidecar)))
    for a in (d,covariance,*targets.values()):a.setflags(write=False)
    return dict(source_files=pins,captured=bodies,source_identity=jsha(dict(source_files=pins,calendar=[START,END],
        source_scope='ORIGINAL_FULLFIVE200_APR2_DEC31_ONLY',used_daily_projection=projection)),
        decisions=d,targets=targets,covariance=covariance,proofs=proofs,window=window,source_rows=rows,
        sidecar=sidecar,sidecar_raw=canonical(sidecar)+b'\n',projection=projection,
        quality=dict(fullfive200_decisions=274,warmup_only_before=START,derived_mark_cells=0,actual_source=True,
            imputed=False,publication_arrival_certified=False,funding_units_certified=False,native_venue_certified=False))
