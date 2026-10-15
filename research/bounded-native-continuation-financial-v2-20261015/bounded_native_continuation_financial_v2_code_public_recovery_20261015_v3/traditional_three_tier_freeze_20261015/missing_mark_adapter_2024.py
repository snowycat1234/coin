"""Separate proposed causal mark-quality adapter, with no financial algorithms.

Original source bytes are preserved. Only the two known absent mark bars are
projected to last-genuine close estimates. This is an explicit execution-policy
change from the invalid future-looking interpolation and needs separate review.
Feed decompression never changes quality state: quality is resolved from the
actual event and installed account mark clocks, including after day prefetch.
"""
from __future__ import annotations
from types import MappingProxyType
import numpy as np

VERSION = 'CAUSAL_LAST_GENUINE_MARK_ESTIMATE_AND_INNER_STALE_INCREASE_GUARD_2024_V1'
MINUTE = 60_000_000
MISSING_OPENS = (1723456920000000,1723456980000000)
LAST_GENUINE_OPEN = 1723456860000000
LAST_GENUINE_AVAILABLE = LAST_GENUINE_OPEN+MINUTE
FIRST_MISSING_KNOWN = MISSING_OPENS[0]+MINUTE
NEXT_GENUINE_OPEN = MISSING_OPENS[-1]+MINUTE
RESUME_AVAILABLE = NEXT_GENUINE_OPEN+MINUTE
SYMBOLS = ('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')


def qualification():
    return dict(version=VERSION, status='PROPOSED_SEPARATE_CAUSAL_ADAPTER_REQUIRES_REVIEW_AND_ROOT_GO',
        original_interpolation_execution_admitted=False, original_source_bytes_preserved=True,
        estimate='CARRY_ONLY_LAST_GENUINE_COMPLETED_MARK_CLOSE',
        missing_bar_open_us=list(MISSING_OPENS), last_genuine_bar_open_us=LAST_GENUINE_OPEN,
        last_genuine_source_available_us=LAST_GENUINE_AVAILABLE,
        stale_observation_us=[at+MINUTE for at in MISSING_OPENS],
        increase_block_interval_us=[FIRST_MISSING_KNOWN,RESUME_AVAILABLE],
        block_interval_convention='LEFT_CLOSED_RIGHT_OPEN; resume only after genuine mark installed',
        earliest_resume_fill_us=RESUME_AVAILABLE+1,
        missingness_known_before_first_expected_close=False,
        valuation_is_estimate=True, estimate_is_current_venue_mark=False,
        provider_publication_arrival_certified=False,
        feed_prefetch_advances_quality_state=False, reductions='DELEGATE_NATIVE_REDUCE_ONLY_PAID_TRADE_PRICE_PATH',
        native_halt_and_duplicate_identity='DELEGATE_EXISTING_INTERCEPTOR_FIRST')


def project_month(arrays):
    """Pure copied feed projection. No state machine or future mark is read."""
    times = arrays['times']
    if not len(times) or not int(times[0]) <= MISSING_OPENS[0] < int(times[-1])+MINUTE:
        return arrays, ()
    prior = int(np.searchsorted(times,LAST_GENUINE_OPEN))
    if prior >= len(times) or int(times[prior]) != LAST_GENUINE_OPEN:
        raise ValueError('LAST_GENUINE_MARK_BAR_REQUIRED_IN_CAPTURED_MONTH')
    indices = [int(np.searchsorted(times,at)) for at in MISSING_OPENS]
    if any(i>=len(times) or int(times[i])!=at for i,at in zip(indices,MISSING_OPENS)):
        raise ValueError('EXACT_DECLARED_MISSING_MARK_BAR_CLOCKS_REQUIRED')
    projected = dict(arrays);sidecar=[]
    for symbol in SYMBOLS:
        original = arrays[symbol+'_mark'];copy=original.copy()
        for i,at in zip(indices,MISSING_OPENS):
            copy[i]=original[prior]
            sidecar.append(dict(symbol=symbol,bar_open_us=at,valuation_observation_us=at+MINUTE,
                valuation_estimate=float(original[prior]),last_genuine_bar_open_us=LAST_GENUINE_OPEN,
                last_genuine_source_available_us=LAST_GENUINE_AVAILABLE,
                stale_age_us=at+MINUTE-LAST_GENUINE_AVAILABLE,
                source_missing=True,derived=True,stale=True,is_actual_current_venue_mark=False))
        copy.setflags(write=False);projected[symbol+'_mark']=copy
    return projected,tuple(MappingProxyType(row) for row in sidecar)

