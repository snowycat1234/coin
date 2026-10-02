"""Fixed-feature causality and failure cases on invented data only."""
from datetime import date
from pathlib import Path
import sys

import numpy as np
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.research_v8 import features as v8
from quant.research_fast.dataset import BAR_US, STREAMS, day_us


@pytest.fixture
def joint():
    n = 900
    times = day_us(date(2025, 7, 2)) + np.arange(n, dtype=np.int64)*BAR_US
    rows = {'timestamp': times}
    for i, stream in enumerate(STREAMS):
        close = np.full(n, 100.+10*i)
        rows.update({f'{stream}__available_us': times+BAR_US,
                     f'{stream}__quality': np.zeros(n, np.int32),
                     f'{stream}__close': close, f'{stream}__vwap': close,
                     f'{stream}__high': close+1, f'{stream}__low': close-1,
                     f'{stream}__flow_imbalance': np.full(n, .1*(i+1)),
                     f'{stream}__return_5s': np.full(n, .001*(i+1)),
                     f'{stream}__large_trade_share': np.full(n, .2),
                     f'{stream}__signed_price_impact': np.full(n, .01),
                     f'{stream}__interarrival_count': np.full(n, 4),
                     f'{stream}__empty_bin': np.zeros(n, bool)})
        for field in ('quote_notional', 'base_volume', 'trade_count', 'agg_count',
                      'mean_trade_size', 'max_trade_size', 'mean_interarrival', 'std_interarrival'):
            rows[f'{stream}__{field}'] = np.full(n, 10.+i)
    return pl.DataFrame(rows)


@pytest.fixture
def decision(joint):
    return int(joint['timestamp'][0])+3900_000_000


def test_joint_spec_cross_flow_and_original_summary(joint, decision):
    out = v8.endpoint_features(joint, decision)
    assert out.available_us == decision
    assert len(out.names) == len(set(out.names)) == 478
    assert out.values.shape == (478,) and not out.values.flags.writeable
    lookup = dict(zip(out.names, out.values))
    assert lookup['BTCUSDT__spot_perp_log_price_divergence'] == pytest.approx(np.log(100/120))
    assert lookup['spot__BTC_ETH_flow_difference__3600s'] == pytest.approx(-.1)
    assert lookup['ETHUSDT__spot_perp_flow_divergence__300s'] == pytest.approx(-.2)
    assert lookup['spot_BTCUSDT__observed_return_fraction__3600s'] == 1


def test_future_perturbation_including_quality_and_availability(joint, decision):
    original = v8.endpoint_features(joint, decision)
    changed = joint.with_columns([
        pl.when(pl.col('timestamp') >= decision).then(99999.).otherwise(pl.col(f'{s}__flow_imbalance')).alias(f'{s}__flow_imbalance')
        for s in STREAMS
    ]).with_columns([
        pl.when(pl.col('timestamp') >= decision).then(None).otherwise(pl.col(f'{s}__available_us')).alias(f'{s}__available_us')
        for s in STREAMS
    ])
    assert np.array_equal(original.values, v8.endpoint_features(changed, decision).values)


@pytest.mark.parametrize('mutation', ['late', 'null_quality', 'missing', 'null_notional', 'negative_notional', 'missing_close'])
def test_input_failure_abstains_instead_of_imputing(joint, decision, mutation):
    stamp = decision-50_000_000
    stream = STREAMS[0]
    if mutation == 'missing':
        changed = joint.filter(pl.col('timestamp') != stamp)
    else:
        field, value = {
            'late': ('available_us', decision+1),
            'null_quality': ('quality', None),
            'null_notional': ('quote_notional', None),
            'negative_notional': ('quote_notional', -1.),
            'missing_close': ('close', None),
        }[mutation]
        if mutation == 'missing_close':
            stamp = decision-BAR_US
        col = f'{stream}__{field}'
        changed = joint.with_columns(pl.when(pl.col('timestamp') == stamp).then(value).otherwise(pl.col(col)).alias(col))
    with pytest.raises(ValueError):
        v8.endpoint_features(changed, decision)


def test_locked_decision_refused_before_source_selection(joint):
    with pytest.raises(ValueError, match='locked'):
        v8.endpoint_features(joint, day_us(date(2026, 3, 1)))
