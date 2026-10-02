"""Active input-contract mutations; preserved V1 tests remain unchanged."""
from pathlib import Path
import sys

import numpy as np
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.research_v8 import features as v1, features_v2 as v2
from test_v8_features import joint, decision


def test_v1_decision_float_counterexample_is_blocked_by_v2(joint, decision):
    # Demonstrate, preserve and block the actual silent truncation counterexample.
    assert np.array_equal(v1.endpoint_features(joint, float(decision)+.75).values,
                          v1.endpoint_features(joint, decision).values)
    with pytest.raises(ValueError, match='integer'):
        v2.endpoint_features(joint, float(decision)+.75)


def test_definitions_unchanged_and_future_values_do_not_matter(joint, decision):
    before = v2.endpoint_features(joint, decision)
    assert before.names == v1.NAMES and np.array_equal(before.values, v1.endpoint_features(joint, decision).values)
    changed = joint.with_columns(pl.when(pl.col('timestamp') >= decision).then(100.)
        .otherwise(pl.col('spot_BTCUSDT__flow_imbalance')).alias('spot_BTCUSDT__flow_imbalance'))
    assert np.array_equal(before.values, v2.endpoint_features(changed, decision).values)


def test_past_invalid_flow_and_fractional_availability_rejected(joint, decision):
    for field, value in [('flow_imbalance', 100.), ('available_us', float(decision)-.25)]:
        col = 'spot_BTCUSDT__'+field
        changed = joint.with_columns(pl.when(pl.col('timestamp') == decision-5_000_000).then(value)
            .otherwise(pl.col(col)).alias(col))
        with pytest.raises(ValueError):
            v2.endpoint_features(changed, decision)
