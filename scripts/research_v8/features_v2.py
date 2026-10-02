"""Active input guard over the preserved V8 fixed-feature definitions."""
from __future__ import annotations

import numpy as np
import polars as pl

from . import features as v1

NAMES, WINDOWS, EndpointFeatures = v1.NAMES, v1.WINDOWS, v1.EndpointFeatures


def endpoint_features(joint: pl.DataFrame, decision_us: int) -> EndpointFeatures:
    # A float such as minute+.75us must never become an accepted minute by int().
    if isinstance(decision_us, (bool, np.bool_)) or not isinstance(decision_us, (int, np.integer)):
        raise ValueError('Decision timestamp must be an explicit integer microsecond')
    decision = int(decision_us)
    if not v1.day_us(v1.START)+720*v1.BAR_US <= decision < v1.day_us(v1.LOCKED):
        raise ValueError('Causal development hour required; locked access forbidden')
    past = joint.filter(pl.col('timestamp').is_between(decision-720*v1.BAR_US, decision, closed='left'))
    for name in ['timestamp']+[f'{stream}__available_us' for stream in v1.STREAMS]:
        times = past[name].to_numpy()
        if not np.isfinite(times).all() or not np.equal(times, np.trunc(times)).all():
            raise ValueError('Input timestamps must contain known integer microseconds')
    for stream in v1.STREAMS:
        flow = past[f'{stream}__flow_imbalance'].to_numpy()
        observed = np.isfinite(flow)
        if np.any(np.abs(flow[observed]) > 1):
            raise ValueError('Observed dimensionless flow must lie in [-1,1]')
    return v1.endpoint_features(past, decision)
