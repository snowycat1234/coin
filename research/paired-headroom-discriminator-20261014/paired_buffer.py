"""One fixed paired stress discriminator. Pure arrays; no account or file IO.

The original HEADROOM source is vendored byte-for-byte. Its readiness and
cost/maintenance constants are reused. Execution is deliberately absent here.
"""
from __future__ import annotations

import numpy as np
from vendor import headroom_buffer as original

VERSION = 'paired_five_minute_mark_execution_gap_v1'
MINUTE = original.MINUTE
WINDOW = original.WINDOW
HORIZON = original.HORIZON
PAIR_WIDTH = WINDOW - HORIZON  # 43,195; the latest completed open is t-MINUTE.


def _hurdle(adverse_move, adverse_gap, direction):
    """Required isolated equity / (abs(q) * current mark), same original math."""
    ratio = np.exp(adverse_move)
    fill = ratio * np.exp(adverse_gap) * (1 - direction * original.SPREAD_SLIP)
    return (original.MMR * ratio + np.abs(fill-ratio) + original.FEE * fill
            - direction * (ratio-1))


def pair_hurdles(move, gap):
    """Direction clipping happens within each pair, before taking its maximum.

    Favorable move/gap becomes zero, as the original adverse extrema do.
    No move from one observation is combined with another observation's gap.
    """
    move, gap = np.broadcast_arrays(np.asarray(move, np.float64),
                                    np.asarray(gap, np.float64))
    return {'long': _hurdle(np.minimum(move, 0), np.minimum(gap, 0), 1),
            'short': _hurdle(np.maximum(move, 0), np.maximum(gap, 0), -1)}


def paired_observations(marks, opens):
    """Array j is paired with the strict-prior mark j-1 and start mark j-6."""
    marks = np.asarray(marks, np.float64)
    opens = np.asarray(opens, np.float64)
    if marks.ndim != 1 or opens.shape != marks.shape:
        raise ValueError('Matching one-dimensional mark/open arrays required')
    move = np.full(marks.shape, np.nan)
    gap = np.full(marks.shape, np.nan)
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        logs = np.log(marks)
        move[HORIZON+1:] = logs[HORIZON:-1] - logs[:-HORIZON-1]
        gap[HORIZON+1:] = np.log(opens[HORIZON+1:]) - logs[HORIZON:-1]
    return move, gap


def features(times, marks, opens, derived=None):
    """Produce exactly causal rolling features with the original READY mask.

    times[i] is a trade-bar OPEN clock x_i; marks[i] closes at x_i+MINUTE.
    At current completed close t=x_i+MINUTE, pair j means:
      v=x_j, move=log(marks[j-1]/marks[j-6]),
      gap=log(opens[j]/marks[j-1]).
    Thus P(v)=marks[j-1] strictly precedes modeled execution v+1us.
    Eligible j: i-WINDOW+6 <= j <= i. Equivalently
    v in [t-30DAY+5MINUTE, t-MINUTE], 43,195 paired endpoints.
    Both move endpoints are inside [t-30DAY,t]; the trade bar is completed.
    The last legacy five-minute move ending at t has no completed own open yet
    and is not paired with a substituted or future gap.
    """
    clocks = np.asarray(times)
    if clocks.dtype.kind not in 'iu':
        raise ValueError('Integer UTC microsecond open clocks required')
    base = original.features(times, marks, opens, derived)
    move, gap = paired_observations(marks, opens)
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        hurdles = pair_hurdles(move, gap)
    result = {'ready': base['ready'].copy(), 'reason': base['reason'].copy()}
    for direction in ('long', 'short'):
        _, maximum = original.rolling_extrema(hurdles[direction], PAIR_WIDTH)
        neutral = float(pair_hurdles(0., 0.)[direction])
        maximum = np.maximum(maximum, neutral)
        maximum[~base['ready']] = np.nan
        if not np.isfinite(maximum[base['ready']]).all():
            raise ValueError('Nonfinite paired stress on original READY inputs')
        result[direction+'_hurdle'] = maximum
    # Fixed mechanical controls, not additional candidate recipes. One uses
    # exactly the candidate's eligible endpoint population; the other is the
    # unchanged original HEADROOM. This separates alignment from coupling.
    move_low, move_high = original.rolling_extrema(move, PAIR_WIDTH)
    gap_low, gap_high = original.rolling_extrema(gap, PAIR_WIDTH)
    controls = {
        'aligned_independent_long_hurdle': _hurdle(np.minimum(move_low,0),np.minimum(gap_low,0),1),
        'aligned_independent_short_hurdle': _hurdle(np.maximum(move_high,0),np.maximum(gap_high,0),-1),
        'legacy_independent_long_hurdle': _hurdle(base['a_down'],base['g_down'],1),
        'legacy_independent_short_hurdle': _hurdle(base['a_up'],base['g_up'],-1)}
    for key,value in controls.items():
        value[~base['ready']] = np.nan
        if not np.isfinite(value[base['ready']]).all():
            raise ValueError('Nonfinite mechanical control on original READY inputs')
        result[key] = value
    return result


def assess(q, equity, mark, long_hurdle, short_hurdle):
    """Own current q/E/mark only. No quantity sizing, fill, exit, or PnL."""
    q, equity, mark, long_hurdle, short_hurdle = np.broadcast_arrays(
        *[np.asarray(x, np.float64) for x in
          (q, equity, mark, long_hurdle, short_hurdle)])
    if (not np.isfinite(q).all() or not np.isfinite(equity).all()
            or not np.isfinite(mark).all() or np.any(mark <= 0)):
        raise ValueError('Finite current q/E and positive mark required')
    selected = np.where(q > 0, long_hurdle, short_hurdle)
    with np.errstate(over='ignore',invalid='ignore'):
        required = np.abs(q) * mark * selected
        headroom = equity-required
    ready_invested = (q != 0) & np.isfinite(selected)
    if np.any(ready_invested & (~np.isfinite(required) | ~np.isfinite(headroom))):
        raise ValueError('Nonfinite required equity or headroom on READY owned scalar')
    return {'trigger': (q != 0) & np.isfinite(headroom) & (headroom <= 0),
            'required_isolated_equity': required, 'buffered_headroom': headroom}


def at(feature, index, q, equity, mark, arm='paired'):
    """Explicit NOT_READY behavior: no additional risk signal."""
    if arm not in ('paired','aligned_independent','legacy_independent'):
        raise ValueError('One candidate and its two fixed mechanical controls only')
    prefix = '' if arm == 'paired' else arm+'_'
    index = int(index)
    if not bool(feature['ready'][index]):
        return {'ready': False, 'reason': str(feature['reason'][index]),
                'trigger': False, 'buffered_headroom': None}
    out = assess(q, equity, mark, feature[prefix+'long_hurdle'][index],
                 feature[prefix+'short_hurdle'][index])
    return {'ready': True, 'reason': 'READY',
            **{k: bool(v) if k == 'trigger' else float(v) for k, v in out.items()}}
