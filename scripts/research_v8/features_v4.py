"""Require truthful Boolean empty masks before the preserved feature adapter."""
from __future__ import annotations

import numpy as np
import polars as pl

from . import features as definition
from . import features_v3 as prior

NAMES, WINDOWS, EndpointFeatures = prior.NAMES, prior.WINDOWS, prior.EndpointFeatures


def endpoint_features(joint: pl.DataFrame, decision_us: int) -> EndpointFeatures:
    # Original decision guards run without inspecting/coercing future rows.
    if not isinstance(decision_us,(int,np.integer)) or isinstance(decision_us,(bool,np.bool_)):
        raise ValueError('Original integer decision required')
    past=joint.filter(pl.col('timestamp').is_between(int(decision_us)-720*definition.BAR_US,int(decision_us),closed='left'))
    for stream in definition.STREAMS:
        empty=past[f'{stream}__empty_bin']
        if empty.dtype != pl.Boolean or empty.null_count():
            raise ValueError('Known Boolean empty-bin state required; no coercion')
        flag=empty.to_numpy()
        counts=[]
        for name in ('trade_count','agg_count','interarrival_count'):
            val=past[f'{stream}__{name}'].to_numpy()
            if not np.isfinite(val).all() or np.any((val<0)|(val!=np.trunc(val))):
                raise ValueError('Known nonnegative integral activity count required')
            counts.append(val)
        trade,aggregate,interarrival=counts
        if not np.array_equal(flag,trade==0) or not np.array_equal(trade,aggregate):
            raise ValueError('Empty flag, trade and aggregate counts disagree')
        for name in ('quote_notional','base_volume'):
            val=past[f'{stream}__{name}'].to_numpy()
            if not np.isfinite(val).all() or np.any(val<0) or np.any(val[flag]!=0):
                raise ValueError('Empty bins cannot conceal positive or unknown activity')
        if np.any(interarrival[flag]!=0):
            raise ValueError('Empty bins cannot contain interarrival observations')
    return prior.endpoint_features(joint,decision_us)
