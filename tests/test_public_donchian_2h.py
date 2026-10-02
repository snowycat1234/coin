"""Only the new fixed2h boundaries and unchanged default1h contract."""
import importlib.util
import numpy as np
import polars as pl
import pytest
from scripts.investment import compare_simple_strategies as common
from scripts.research_v8 import public_donchian_adapter as public


@pytest.fixture(scope="module")
def prices():
    start = common.day_us(common.date(2025, 8, 1))
    stamps = np.arange(start - 31 * common.DAY_US, start + 6 * public.HOUR_US, common.MINUTE_US, dtype=np.int64)
    # Bounded deterministic minute prices with a trend and an entry/exit shock.
    t = np.arange(len(stamps), dtype=np.float64)
    shape = 100. + t * .0001 + np.sin(t / 180.) * .1
    shape[stamps >= start + 2 * public.HOUR_US] += 2.
    shape[stamps >= start + 4 * public.HOUR_US] -= 5.
    frames = []
    for symbol, scale in (("BTCUSDT",100.),("ETHUSDT",10.)):
        close = shape * scale
        frames.append(pl.DataFrame({"symbol":[symbol]*len(stamps),"open_us":stamps,
            "high":close+scale*.02,"low":close-scale*.02,"close":close,
            "available_us":stamps+common.MINUTE_US}))
    return pl.concat(frames), start


def test_2h_alignment_missing_delayed_and_future_causality(prices):
    frame,start=prices
    calendar=np.arange(start,start+5*public.HOUR_US,common.MINUTE_US,dtype=np.int64)
    bars=public.closed_hours(frame,timeframe_minutes=120)
    assert (bars['count']==120).all() and (bars['close_us']%(2*public.HOUR_US)==0).all()
    assert (bars['first_us']==bars['hour_open_us']).all()
    assert (bars['last_us']==bars['hour_open_us']+2*public.HOUR_US-common.MINUTE_US).all()
    plan=public.fixed_targets(frame,calendar,timeframe_minutes=120)
    assert plan.strategy_id==public.STRATEGY_2H_ID and not plan.receipt['warmup_failed']
    assert plan.receipt['timeframe_minutes']==120 and plan.receipt['donchian_period']==20 and plan.receipt['trend_sma_period']==200
    cutoff=start+2*public.HOUR_US
    changed=frame.with_columns([pl.when(pl.col('open_us')>=cutoff).then(pl.col(key)*4).otherwise(pl.col(key)).alias(key)
        for key in ('high','low','close')])
    altered=public.fixed_targets(changed,calendar,timeframe_minutes=120)
    assert plan.calendar_ledger.filter(pl.col('decision_us')<=cutoff).equals(altered.calendar_ledger.filter(pl.col('decision_us')<=cutoff))
    # One missing minute invalidates the relevant full2h warmup, not a119-row candle.
    missing=frame.filter(~((pl.col('symbol')=='BTCUSDT')&(pl.col('open_us')==start-common.MINUTE_US)))
    assert public.fixed_targets(missing,calendar,timeframe_minutes=120).receipt['warmup_failed']
    delayed=frame.with_columns(pl.when((pl.col('symbol')=='BTCUSDT')&(pl.col('open_us')==start-common.MINUTE_US))
        .then(start+common.MINUTE_US).otherwise(pl.col('available_us')).alias('available_us'))
    assert public.fixed_targets(delayed,calendar,timeframe_minutes=120).receipt['warmup_failed']
    for unsupported in (30,240,120.,True):
        with pytest.raises(ValueError,match='Only fixed60/120'):
            public.closed_hours(frame,timeframe_minutes=unsupported)


def test_default_1h_valid_targets_equal_archived_fixture_and_reference_scope(prices):
    frame,start=prices
    path=common.ROOT/'docs/archive/PUBLIC_DONCHIAN_BEFORE_NULL_GUARD_20261002_V1.py'
    assert common.file_sha(path)=='0cbd141f3ef60280826013137e67dfcdd59756f51b29ad77a46e7ca15d46c344'
    spec=importlib.util.spec_from_file_location('scripts.research_v8.public_donchian_before_null_guard',path)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    calendar=np.arange(start,start+5*public.HOUR_US,common.MINUTE_US,dtype=np.int64)
    expected,actual=old.fixed_targets(frame,calendar),public.fixed_targets(frame,calendar)
    assert expected.targets.equals(actual.targets) and expected.calendar_ledger.equals(actual.calendar_ledger)
    assert expected.receipt==actual.receipt
    protocol=common.read_json(common.ROOT/'protocols/PUBLIC_DONCHIAN_2H_122D_V1.json')
    strategies,windows,count=common.comparison_plan(protocol)
    assert strategies==(public.STRATEGY_2H_ID,) and count==3 and len(windows)==1
    assert (windows[0][3]-windows[0][2])//common.DAY_US==122
    previous=common.read_json(common.ROOT/protocol['reused_reference_report'])
    assert common.file_sha(common.ROOT/protocol['reused_reference_report'])==protocol['reused_reference_report_sha256']
    report={}
    common.bind_reused_reference(protocol,previous['minute_source'],report)
    assert report['reused_reference_binding']['reused_accounts']==12
    assert not report['reused_reference_binding']['existing_reference_accounts_replayed']
