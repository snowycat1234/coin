"""Independent-audit primitive mutations and legitimate masks on invented data."""
from pathlib import Path
import sys

import numpy as np
import polars as pl
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.research_v8 import features_v2 as v2, features_v3 as v3
from test_v8_features import joint, decision


@pytest.mark.parametrize('field,value,last', [
    ('close',None,False),('vwap',None,True),('mean_trade_size',None,False),
    ('mean_trade_size',-.5,False),('max_trade_size',None,False),
    ('large_trade_share',None,False),('std_interarrival',None,False),
])
def test_unmasked_primitives_rejected(joint,decision,field,value,last):
    stamp=decision-5_000_000 if last else decision-300_000_000
    col='spot_BTCUSDT__'+field
    changed=joint.with_columns(pl.when(pl.col('timestamp')==stamp).then(value).otherwise(pl.col(col)).alias(col))
    with pytest.raises(ValueError):v3.endpoint_features(changed,decision)


def test_original_definitions_and_legitimate_undefined_masks_preserved(joint,decision):
    assert np.array_equal(v2.endpoint_features(joint,decision).values,v3.endpoint_features(joint,decision).values)
    stamp=decision-300_000_000
    columns=[]
    for field,value in [('return_5s',None),('signed_price_impact',None),('interarrival_count',0),
                        ('mean_interarrival',None),('std_interarrival',None)]:
        col='spot_BTCUSDT__'+field
        columns.append(pl.when(pl.col('timestamp')==stamp).then(value).otherwise(pl.col(col)).alias(col))
    changed=joint.with_columns(columns)
    assert np.array_equal(v2.endpoint_features(changed,decision).values,v3.endpoint_features(changed,decision).values)


def test_future_primitive_corruption_is_unobserved(joint,decision):
    changed=joint.with_columns(pl.when(pl.col('timestamp')>=decision).then(None)
        .otherwise(pl.col('spot_BTCUSDT__vwap')).alias('spot_BTCUSDT__vwap'))
    assert np.array_equal(v3.endpoint_features(joint,decision).values,v3.endpoint_features(changed,decision).values)
