"""Independent empty-mask counterexamples and genuine no-trade control."""
from pathlib import Path
import sys
import numpy as np
import polars as pl
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.research_v8 import features_v3 as prior,features_v4 as active
from test_v8_features import joint,decision


def change(joint,decision,fields):
    stamp=decision-300_000_000
    return joint.with_columns([pl.when(pl.col('timestamp')==stamp).then(value)
        .otherwise(pl.col('spot_BTCUSDT__'+field)).alias('spot_BTCUSDT__'+field)
        for field,value in fields.items()])


def test_false_empty_mask_cannot_hide_missing_primitives(joint,decision):
    changed=change(joint,decision,{'empty_bin':True,'close':None,'vwap':None,
                                  'mean_trade_size':None,'max_trade_size':None})
    with pytest.raises(ValueError,match='disagree'):active.endpoint_features(changed,decision)


def test_integer_empty_state_is_not_boolean(joint,decision):
    changed=joint.with_columns(pl.col('spot_BTCUSDT__empty_bin').cast(pl.Int64))
    with pytest.raises(ValueError,match='Boolean'):active.endpoint_features(changed,decision)


@pytest.mark.parametrize('field,value',[('trade_count',10.5),('agg_count',11),('interarrival_count',-.5)])
def test_corrupt_count_cannot_define_masks(joint,decision,field,value):
    with pytest.raises(ValueError):active.endpoint_features(change(joint,decision,{field:value}),decision)


def test_genuine_empty_and_legitimate_undefined_masks_preserved(joint,decision):
    changed=change(joint,decision,{'empty_bin':True,'trade_count':0,'agg_count':0,
       'interarrival_count':0,'base_volume':0.,'quote_notional':0.,'flow_imbalance':0.,
       'close':None,'high':None,'low':None,'vwap':None,'mean_trade_size':None,
       'max_trade_size':None,'large_trade_share':None,'return_5s':None,
       'signed_price_impact':None,'mean_interarrival':None,'std_interarrival':None})
    assert np.array_equal(prior.endpoint_features(changed,decision).values,
                          active.endpoint_features(changed,decision).values)


def test_future_mask_corruption_remains_unobserved(joint,decision):
    changed=joint.with_columns(pl.when(pl.col('timestamp')>=decision).then(True)
          .otherwise(pl.col('spot_BTCUSDT__empty_bin')).alias('spot_BTCUSDT__empty_bin'))
    assert np.array_equal(active.endpoint_features(joint,decision).values,
                          active.endpoint_features(changed,decision).values)
