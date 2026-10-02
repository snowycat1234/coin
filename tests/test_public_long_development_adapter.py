"""One new synthetic date/source/count/cost routing case; no account replay."""
from datetime import date
from types import SimpleNamespace
import numpy as np
import polars as pl
import pytest
from scripts.investment import public_long_development_adapter as adapter

def test_isolated_547d_calendar_single_cost_source_and_native_date_route():
    spec=dict(strategy_ids=list(adapter.SLEEVES),planned_ledgers=3,
        folds=[dict(id='CONT547',period_start='2024-01-01',period_end_exclusive='2025-07-01')],
        source_scope=adapter.SCOPE,source_calendar=list(adapter.MONTHS),source_days_per_symbol=578,
        fee_settlement='BYBIT_SPOT_RECEIVED_ASSET_V1',
        costs=dict(spread_bps=[8],nominal_roundtrip_bps=[36],fee_bps_per_side=10,slippage_bps_per_side=4),
        common_config=dict(initial_cash=10000,target_annual_vol=.10,gross_cap=.6,per_symbol_cap=.3,
            latency_minutes=1,vol_window_days=30,min_vol_days=20,participation_rate=.001,max_order_wait_minutes=5,liquidate_at_end=True))
    before=(adapter.old.START,adapter.old.LOCKED,adapter.timeguard.BEGIN,adapter.timeguard.END,
        adapter.native.BEGIN_US,adapter.native.END_US,adapter.public.common,adapter.hybrid.public)
    ns=adapter.context(spec); strategies,windows,planned=ns['comparison_plan'](spec)
    _,lower,start,end=windows[0]
    assert planned==3 and strategies==adapter.SLEEVES and (end-start)//adapter.old.DAY_US==547
    assert (start-lower)//adapter.old.DAY_US==31 and (end-start)//adapter.old.MINUTE_US==787680
    source=dict(status=adapter.SOURCE_STATUS,binding=dict(spec=dict(source_scope=adapter.SCOPE,source_calendar=list(adapter.MONTHS))),
        source_files=38,days_per_symbol=578,actual_minute_rows=1664640,sources=[])
    for symbol in adapter.old.SYMBOLS:
        for month in adapter.MONTHS:
            first=date.fromisoformat(month+'-01'); following=date(first.year+first.month//12,first.month%12+1,1)
            count=(following-first).days*1440
            quality=dict(rows=count,expected_rows=count,first_open_us=adapter.old.day_us(first),
                last_open_us=adapter.old.day_us(following)-adapter.old.MINUTE_US,incomplete_days=[],quarantined_days=[])
            quality.update({key:0 for key in ('missing_rows','duplicate_rows','bad_timestamps','bad_values','gaps','quarantined_rows')})
            source['sources'].append(dict(symbol=symbol,month=month,rows=count,old_quality=quality,
                normalized_path=str(adapter.ROOT/'data/normalized/spot'/symbol/'1m'/(month+'.parquet'))))
    assert ns['verify_source_calendar'](spec,source)==578
    assert sum(r['rows'] for r in source['sources'])==1664640
    assert next(r['rows'] for r in source['sources'] if r['month']=='2024-02')==41760
    with pytest.raises(ValueError): ns['allowed_source_path'](dict(symbol='BTCUSDT',month='2025-07',normalized_path='unused'),spec)
    private=ns['benchmarks']; calendar=np.array([start,start+adapter.old.MINUTE_US],dtype=np.int64)
    assert np.array_equal(private.calendar_array(calendar),calendar)
    with pytest.raises(ValueError): adapter.v2.calendar_array(calendar)
    with pytest.raises(ValueError): private.calendar_array(calendar.astype(float))
    with pytest.raises(ValueError): private.calendar_array(np.array([end,end+adapter.old.MINUTE_US],dtype=np.int64))
    boundary=pl.DataFrame(dict(close_us=[end],available_us=[end]),schema={'close_us':pl.Int64,'available_us':pl.Int64})
    private._integer_timestamp_columns(boundary,('close_us','available_us'),allow_end=True)
    with pytest.raises(ValueError): private._integer_timestamp_columns(boundary,('close_us','available_us'))
    assert len(ns['period_aggregate']([],strategies))==3
    assert {r['spread_bps'] for r in ns['period_aggregate']([],strategies)}=={8}
    config=ns['comparison_config'](start,end,8)
    assert (config.initial_cash,config.fee_bps,config.half_spread_bps,config.slippage_bps)==(10000,10,4,4)
    assert (config.max_weight,config.max_gross,config.target_annual_vol,config.vol_window_days,config.min_vol_days)==(.3,.6,.10,30,20)
    assert ns['public_strategy'].common is private and ns['public_strategy'].original is private._v1
    assert ns['PERIOD_HYBRID'].public is ns['public_strategy'] and ns['PERIOD_HYBRID'].common is private
    assert ns['PERIOD_HYBRID'].original is private._v1 and ns['bulk_fixed_targets'].common is private
    assert ns['bulk_fixed_targets'].original is private._v1
    # Spy only the reused native wrapper's date route; financial kernel is not rerun.
    route=ns['PERIOD_NATIVE'].run_backtest; called=[]; globals_=route.__globals__
    globals_['_compiled']=lambda:(lambda bars,minutes,targets,config:called.append(minutes['open_us'].to_list()) or SimpleNamespace(summary={'gross_pnl_before_costs':0.}),None,None,[])
    globals_['derivation_receipt']=lambda:dict(derived_AST_SHA256='SYNTHETIC_ROUTE_SPY_NOT_FINANCIAL_PROOF')
    minutes=pl.DataFrame(dict(symbol=['BTCUSDT'],open_us=[start]),schema={'symbol':pl.String,'open_us':pl.Int64})
    targets=pl.DataFrame(dict(available_us=[start]),schema={'available_us':pl.Int64})
    route(None,minutes,targets,config); assert called==[[start]]
    with pytest.raises(ValueError): route(None,minutes.with_columns(pl.lit(end).cast(pl.Int64).alias('open_us')),targets,config)
    assert called==[[start]]
    assert before==(adapter.old.START,adapter.old.LOCKED,adapter.timeguard.BEGIN,adapter.timeguard.END,
        adapter.native.BEGIN_US,adapter.native.END_US,adapter.public.common,adapter.hybrid.public)
    bad={**spec,'costs':{**spec['costs'],'spread_bps':[2,4,8]}}
    with pytest.raises(ValueError): adapter.context(bad)
