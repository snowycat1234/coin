"""Read-only causal execution_headroom_buffer_v1. No account/strategy imports."""
from __future__ import annotations
from collections import deque
from decimal import Decimal, ROUND_FLOOR
import math
import numpy as np

MINUTE = 60_000_000
DAY = 86_400_000_000
WINDOW = 30 * 1440
HORIZON = 5
MMR = .005
SPREAD_SLIP = .0008
FEE = .00055
STEP = Decimal('0.00000001')
PARTICIPATION = Decimal('.001')
VERSION = 'execution_headroom_buffer_v1'


def rolling_extrema(values, width):
    """Inclusive trailing extrema. NaNs are ignored only in calculation;
    readiness independently rejects every invalid input in its exact window.
    """
    values = np.asarray(values, dtype=np.float64)
    lo = np.full(len(values), np.nan); hi = lo.copy()
    low = deque(); high = deque()
    for i, x in enumerate(values):
        left = i-width+1
        while low and low[0] < left: low.popleft()
        while high and high[0] < left: high.popleft()
        if math.isfinite(x):
            while low and values[low[-1]] >= x: low.pop()
            while high and values[high[-1]] <= x: high.pop()
            low.append(i); high.append(i)
        if low: lo[i] = values[low[0]]
        if high: hi[i] = values[high[0]]
    return lo, hi


def trailing_any(bad, width):
    counts = np.r_[0, np.cumsum(np.asarray(bad, dtype=np.int64))]
    right = np.arange(1, len(bad)+1)
    return counts[right] - counts[np.maximum(0, right-width)] > 0


def features(times, marks, opens, derived=None):
    """Inputs are minute OPEN times; mark closes at times+MINUTE.

    At close t, use exactly 43201 mark endpoints [t-30DAY,t], 43196
    within-window five-minute returns, and 43200 already-completed trade
    opens v in [t-30DAY,t-MINUTE]. Basis pairs each open with its prior mark.
    No element after index i contributes to feature/readiness at index i.
    """
    times = np.asarray(times, dtype=np.int64)
    marks = np.asarray(marks, dtype=np.float64)
    opens = np.asarray(opens, dtype=np.float64)
    if times.ndim != 1 or marks.shape != times.shape or opens.shape != times.shape:
        raise ValueError('Matching one-dimensional source arrays required')
    if derived is None: derived = np.zeros(len(times), dtype=bool)
    derived = np.asarray(derived, dtype=bool)
    if derived.shape != times.shape: raise ValueError('Derived-cell mask shape')
    mark_bad = ~np.isfinite(marks) | (marks <= 0)
    open_bad = ~np.isfinite(opens) | (opens <= 0)
    gaps = np.r_[False, np.diff(times) != MINUTE]
    ready = np.arange(len(times)) >= WINDOW
    reasons = np.full(len(times), 'READY', dtype='<U32')
    checks = [('BAD_MARK', trailing_any(mark_bad, WINDOW+1)),
              ('DERIVED_OR_UNKNOWN_MARK', trailing_any(derived, WINDOW+1)),
              ('BAD_TRADE_OPEN', trailing_any(open_bad, WINDOW)),
              ('NONCONTIGUOUS_MINUTE_CLOCK', trailing_any(gaps, WINDOW))]
    for name, bad in checks:
        reasons[bad] = name; ready &= ~bad
    reasons[np.arange(len(times)) < WINDOW] = 'WARMUP_30_COMPLETE_DAYS'
    with np.errstate(divide='ignore', invalid='ignore'):
        logm = np.log(marks)
        returns = np.full(len(times), np.nan)
        returns[HORIZON:] = logm[HORIZON:] - logm[:-HORIZON]
        basis = np.full(len(times), np.nan)
        basis[1:] = np.log(opens[1:]) - logm[:-1]
    a_down, a_up = rolling_extrema(returns, WINDOW-HORIZON+1)
    g_down, g_up = rolling_extrema(basis, WINDOW)
    result = {'ready': ready, 'reason': reasons,
              'a_down': np.minimum(0., a_down), 'a_up': np.maximum(0., a_up),
              'g_down': np.minimum(0., g_down), 'g_up': np.maximum(0., g_up)}
    for key in ('a_down','a_up','g_down','g_up'):
        result[key][~ready] = np.nan
    return result


def assess(q, equity, mark, a_down, a_up, g_down, g_up):
    """Point-in-time buffer only, with full-exit cost reserve at stressed mark."""
    arrays = np.broadcast_arrays(*[np.asarray(x,dtype=np.float64) for x in
                                  (q,equity,mark,a_down,a_up,g_down,g_up)])
    q,equity,mark,a_down,a_up,g_down,g_up = arrays
    adverse = np.where(q>0, a_down, a_up)
    gap = np.where(q>0, g_down, g_up)
    stressed_mark = mark*np.exp(adverse)
    stressed_mid = stressed_mark*np.exp(gap)
    stressed_fill = stressed_mid*np.where(q>0, 1-SPREAD_SLIP, 1+SPREAD_SLIP)
    stressed_equity = equity+q*(stressed_mark-mark)
    maintenance = np.abs(q)*stressed_mark*MMR
    reserve = np.abs(q)*np.abs(stressed_fill-stressed_mark)+np.abs(q)*stressed_fill*FEE
    headroom = stressed_equity-maintenance-reserve
    trigger = (q!=0) & np.isfinite(headroom) & (stressed_equity<=maintenance+reserve)
    return {'trigger':trigger, 'stressed_mark':stressed_mark,
            'stressed_mid':stressed_mid, 'stressed_fill':stressed_fill,
            'stressed_equity':stressed_equity, 'maintenance':maintenance,
            'closecost_reserve':reserve, 'buffered_headroom':headroom}


def spend_capacity(requested, quote_volume, open_price, already_used=Decimal(0)):
    """One real symbol/open shared bucket, including finer-grid floor.
    Callers must pass cumulative already_used for additional same-open legs.
    """
    requested = abs(Decimal(str(requested)))
    quote_volume = Decimal(str(quote_volume)); open_price = Decimal(str(open_price))
    already_used = Decimal(str(already_used))
    if not all(x.is_finite() for x in (requested,quote_volume,open_price,already_used)):
        raise ValueError('Finite capacity operands')
    if quote_volume<0 or open_price<=0 or already_used<0:
        raise ValueError('Valid real quote/open and nonnegative consumed quantity')
    total = quote_volume*PARTICIPATION/open_price
    available = max(Decimal(0), total-already_used)
    fill = (min(requested,available)/STEP).to_integral_value(rounding=ROUND_FLOOR)*STEP
    return fill, total


def exit_witness(q, signal_us, source_times, opens, quotes):
    """Hindsight price/quantity/fee witness; no account transition or PnL.
    The original one-minute contract skips open at t. At most five distinct
    true opens t+MINUTE through t+5MINUTE, each modeled at open+1us.
    """
    qd = Decimal(str(q)); remaining=abs(qd); fills=[]
    side='SELL' if qd>0 else 'BUY'
    times=np.asarray(source_times,dtype=np.int64)
    for j in range(1,HORIZON+1):
        at=int(signal_us)+j*MINUTE
        left=int(np.searchsorted(times,at,side='left'));right=int(np.searchsorted(times,at,side='right'))
        if right-left!=1:
            fills.append({'open_us':at,'event_us':at+1,'status':'MISSING_OR_DUPLICATE_REAL_OPEN'})
            continue
        k=left
        if k==0 or times[k-1]!=at-MINUTE:
            fills.append({'open_us':at,'event_us':at+1,'status':'MISSING_REAL_PRIOR_QUOTE'})
            continue
        try:
            fill,total=spend_capacity(remaining,quotes[k-1],opens[k])
        except (ValueError, __import__('decimal').InvalidOperation):
            fills.append({'open_us':at,'event_us':at+1,'status':'INVALID_REAL_QUOTE_OR_OPEN'})
            continue
        mid=Decimal(str(opens[k])); price=mid*(Decimal('.9992') if qd>0 else Decimal('1.0008'))
        fee=fill*price*Decimal('.00055'); cost=fill*abs(price-mid)
        remaining-=fill
        fills.append({'open_us':at,'event_us':at+1,'source_index':k,'status':'FILLED' if fill else 'ZERO_CAPACITY',
            'quantity':str(fill),'raw_capacity_quantity':str(total),'remaining_quantity':str(remaining),
            'prior_quote_volume':str(quotes[k-1]),'side':side,'mid_price':str(mid),'fill_price':str(price),
            'fee_USDT':str(fee),'execution_cost_USDT':str(cost)})
        if remaining==0:break
    return {'signal_us':int(signal_us),'first_eligible_event_us':int(signal_us)+MINUTE+1,
            'fifth_eligible_event_us':int(signal_us)+5*MINUTE+1,
            'first_eligible_latency_us':MINUTE+1,'fifth_eligible_latency_us':5*MINUTE+1,
            'remaining_quantity':str(remaining),'capacity_complete':remaining==0,
            'completion_event_us':fills[-1]['event_us'] if remaining==0 else None,
            'total_fee_USDT':str(sum((Decimal(x.get('fee_USDT','0')) for x in fills),Decimal(0))),
            'total_execution_cost_USDT':str(sum((Decimal(x.get('execution_cost_USDT','0')) for x in fills),Decimal(0))),
            'attempts':fills,'account_transitions':0,'hypothetical_PnL':None,
            'scope':'POSTHOC_FROZEN_TRIGGER_QUANTITY_REAL_SOURCE_CAPACITY_AND_COST_WITNESS_ONLY'}
