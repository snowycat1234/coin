"""Reject unmasked primitive corruption; retain frozen feature definitions."""
from __future__ import annotations

import numpy as np
import polars as pl

from . import features_v2 as v2
from . import features as definition

NAMES, WINDOWS, EndpointFeatures = v2.NAMES, v2.WINDOWS, v2.EndpointFeatures


def endpoint_features(joint: pl.DataFrame, decision_us: int) -> EndpointFeatures:
    # Run original availability/grid/decision guards before inspecting primitives.
    result = v2.endpoint_features(joint, decision_us)
    decision = int(decision_us)
    past = joint.filter(pl.col('timestamp').is_between(decision-720*definition.BAR_US, decision, closed='left'))
    for stream in definition.STREAMS:
        empty = past[f'{stream}__empty_bin']
        if empty.null_count():
            raise ValueError('Unknown traded/empty state cannot define primitive masks')
        traded = ~empty.to_numpy().astype(bool)
        def values(field):
            return past[f'{stream}__{field}'].to_numpy().astype(np.float64)
        # Only primitives actually used by the unchanged 68 definitions are
        # required. Legitimate empty bins retain the original has_trade mask.
        for field in ('close', 'high', 'low', 'vwap'):
            val = values(field)
            if not np.isfinite(val[traded]).all() or np.any(val[traded] <= 0):
                raise ValueError('Traded price primitive missing/invalid; no silent zero')
        for field in ('mean_trade_size', 'max_trade_size'):
            val = values(field)
            if not np.isfinite(val[traded]).all() or np.any(val[traded] < 0):
                raise ValueError('Traded size primitive missing/negative; no silent zero')
        for field in ('flow_imbalance', 'large_trade_share'):
            val = values(field)
            lower = -1 if field == 'flow_imbalance' else 0
            if not np.isfinite(val[traded]).all() or np.any((val[traded] < lower)|(val[traded] > 1)):
                raise ValueError('Traded ratio primitive missing/outside physical units')
        ret = values('return_5s')
        impact = values('signed_price_impact')
        if np.any(np.isfinite(ret)&~np.isfinite(impact)):
            raise ValueError('Signed impact missing with observed return')
        count = values('interarrival_count')
        if not np.isfinite(count).all() or np.any((count < 0)|(count != np.trunc(count))):
            raise ValueError('Known nonnegative integral interarrival count required')
        defined = count > 0
        for field in ('mean_interarrival', 'std_interarrival'):
            val = values(field)
            if not np.isfinite(val[defined]).all() or np.any(val[defined] < 0):
                raise ValueError('Defined interarrival primitive missing/negative')
    return result
