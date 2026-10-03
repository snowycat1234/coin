"""ONE new213 period/source/namespace wiring case; no old finance tests or data."""
import ast
import calendar
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from quant.paths import ROOT


def adapter_module():
    path = Path(os.environ['COIN_213_WIRING_ADAPTER']).resolve()
    spec = importlib.util.spec_from_file_location('_d043_new213_wiring_adapter', path)
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.base.sha(path) == os.environ['COIN_213_WIRING_ADAPTER_SHA256']
    return module


def test_new213_source_clock_private_namespace_and_future_prefix(tmp_path):
    a = adapter_module(); minute, day, bar = a.base.MINUTE, a.base.DAY, a.benchmark.BAR
    first, end = a.stamp(a.START), a.stamp(a.END)
    layout = {
        'trade_1m': ('trade:1m:', 'USD_M_PERPETUAL_TRADE_KLINES', '2024-01', '2024-07', 'minute'),
        'mark_1m': ('markPriceKlines:', 'USD_M_PERPETUAL_markPriceKlines', '2024-01', '2024-07', 'minute'),
        'funding': ('fundingRate:', 'USD_M_PERPETUAL_fundingRate', '2024-01', '2024-07', 'event'),
        'trade_1d_warmup': ('trade:1d:', 'USD_M_PERPETUAL_TRADE_KLINES', '2023-06', '2023-12', 'day'),
        'trade_1d_score': ('trade:1d:', 'USD_M_PERPETUAL_TRADE_KLINES', '2024-01', '2024-07', 'day'),
        'signal_warmup_2h': ('trade:2h:', 'USD_M_PERPETUAL_TRADE_KLINES', '2023-12', '2023-12', 'twohour'),
    }
    files, roles, funding_counts = {}, {}, {}
    for symbol in a.base.SYMBOLS:
        roles[symbol] = {}; funding_counts[symbol] = 0
        for role, (prefix, product, lower, upper, kind) in layout.items():
            roles[symbol][role] = []
            for index, month in enumerate(a.months(lower, upper)):
                days = calendar.monthrange(*map(int, month.split('-')))[1]
                count = days * 1440 if kind == 'minute' else days * 12 if kind == 'twohour' else days
                if kind == 'event':
                    count = index + 2  # Deliberately not a fixed8h/event-count assumption.
                    funding_counts[symbol] += count
                identity = prefix + symbol + ':' + month
                roles[symbol][role].append(identity)
                files[identity] = dict(symbol=symbol, month=month, product=product, rows=count)
    window = dict(id='213D', start=a.START, end_exclusive=a.END, days=213,
        minutes_per_symbol=306720, source_ids=roles)
    manifest = dict(status=a.MANIFEST_STATUS, funding_rate_unit='UNCONFIRMED',
        funding_unit_certified=False, locked_consumed=False, source_files=files, windows=[window])
    normalized = a.metadata_view(manifest)
    assert len(files) == 72 and (end-first)//day == 213
    for symbol in a.base.SYMBOLS:
        mapped = normalized['windows'][0]['symbols'][symbol]
        assert mapped['source_ids'] == roles[symbol]
        assert mapped['rows_inherited_from_receipts']['funding'] == funding_counts[symbol] == 35
    missing = json.loads(json.dumps(manifest)); missing['windows'][0]['source_ids']['BTCUSDT']['mark_1m'].pop()
    with pytest.raises(ValueError, match='Exact symbol/product/month'):
        a.metadata_view(missing)
    extra = json.loads(json.dumps(manifest)); extra['source_files']['markPriceKlines:BTCUSDT:2024-08'] = dict(
        symbol='BTCUSDT', month='2024-08', product='USD_M_PERPETUAL_markPriceKlines', rows=44640)
    with pytest.raises(ValueError, match='Exact72'):
        a.metadata_view(extra)
    spec = dict(contract_id=a.CONTRACT, rules=a.RULES, period_ids=['213D'],
        cost_scenarios=a.base.COSTS, unit_scenarios=a.base.UNITS, input_manifest={'path':a.INPUT},
        preceding_failed_source=a.PRECEDING_FAILURE, frozen_sources=dict(a.PINS))
    wired = a.context(spec)  # All exact AST anchors compile before any source array IO.
    globals_main = wired['main'].__globals__
    assert globals_main['strategy'].MODES == ('LONG_ONLY', 'SHORT_ONLY', 'LONG_SHORT', 'CASH', 'DONCHIAN_LONG_ONLY')
    assert len(globals_main['strategy'].MODES) * len(a.base.COSTS) * len(a.base.UNITS) == 20
    assert a.RULES['planned_trading_account_simulations'] == 16 and a.RULES['planned_constant_cash_baselines'] == 1
    signal_receipt = next(row for row in wired['derivation'] if row['function'] == 'simulate')
    assert [item['matches'] for item in signal_receipt['changes']] == [1,1,1,1]
    private_globals = wired['target2h'].__globals__
    assert private_globals['_contexts'].__globals__ is private_globals
    assert private_globals['SOURCE_BEGIN_US'] == a.stamp('2023-12-01T00:00:00+00:00')
    assert private_globals['DAILY_BEGIN_US'] == a.stamp('2023-06-01T00:00:00+00:00')
    assert private_globals['SCORE_BEGIN_US'] == first and private_globals['LOCKED_US'] == a.donchian.LOCKED_US
    parent = ast.parse(Path(a.base.__file__).read_text())
    parent_main = next(n for n in parent.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    # The complete constant-cash branch is reused, including three shared aliases.
    parent_cash = [ast.dump(n, include_attributes=False) for n in ast.walk(parent_main)
        if isinstance(n, ast.If) and any(isinstance(k, ast.Constant) and k.value == 'CASH' for k in ast.walk(n.test))]
    main_receipt = next(row for row in wired['derivation'] if row['function'] == 'main')
    assert [row['change'] for row in main_receipt['changes']] == [
        'ONE_FIXED_PERIOD_CLI', 'ONE_FIXED_PERIOD_METADATA', 'SIXTEEN_PHYSICAL_TRADING_ACCOUNTS',
        'RECORD_PRIVATE_METADATA_AND_SIGNAL_DERIVATION', 'CANONICAL_DIRECTION_AND_EXPLICIT_STRATEGY_ID',
        'HONEST_FIVE_SELECTOR_FEATURE_METADATA', 'PREDECLARED_LONGER_WINDOW_REASON']
    assert all(row['matches'] == 1 for row in main_receipt['changes'])
    assert len(parent_cash) >= 3

    def frame(stamps, btc, eth, interval, duration):
        return pl.DataFrame([dict(symbol=symbol, interval=interval, open_us=int(t-duration),
            close_us=int(t), available_us=int(t), open=float(price), close=float(price),
            high=float(price+.1), low=float(price-.1), volume=1000.)
            for symbol, values in zip(a.base.SYMBOLS, (btc,eth), strict=True)
            for t,price in zip(stamps,values,strict=True)])
    daily_times = first + (np.arange(217,dtype=np.int64)-213)*day
    daily = frame(daily_times,100.+np.arange(217)*.025,120.-np.arange(217)*.025,'1d',day)
    two_times = first + (np.arange(376,dtype=np.int64)-371)*bar
    btc = np.r_[np.full(371,100.),np.arange(102.,107.)]
    signal = frame(two_times,btc,np.full(376,100.),'2h',bar)
    daily_decisions = np.array([first,first+day,first+2*day],dtype=np.int64)
    two_decisions = np.array([first,first+bar,first+2*bar],dtype=np.int64)
    def poison(source,factor):
        return source.with_columns(*[pl.when(pl.col('close_us')>first).then(pl.col(key)*factor)
            .otherwise(pl.col(key)).alias(key) for key in ('open','high','low','close')])
    sma_evidence = {}
    for mode in a.sma.MODES:
        targets, receipt = a.sma.fixed_targets(daily,daily_decisions,mode)
        future, future_receipt = a.sma.fixed_targets(poison(daily,7),daily_decisions,mode)
        assert targets.filter(pl.col('available_us')==first).equals(future.filter(pl.col('available_us')==first))
        assert receipt['risk'][0] == future_receipt['risk'][0]
        sma_evidence[mode] = targets.to_dicts()
    assert sma_evidence['LONG_SHORT'][0]['raw_signed_target'] == .3
    assert sma_evidence['LONG_SHORT'][1]['raw_signed_target'] == -.3
    assert all(row['target_weight']==0 for row in sma_evidence['CASH'])
    target2h, proof2h = wired['target2h'](signal,two_decisions,risk_daily_bars=daily)
    future2h, future_proof = wired['target2h'](poison(signal,.2),two_decisions,risk_daily_bars=poison(daily,7))
    assert target2h.filter(pl.col('available_us')==first).equals(future2h.filter(pl.col('available_us')==first))
    assert proof2h['risk'][0] == future_proof['risk'][0]
    assert target2h.filter(pl.col('available_us')>first).equals(future2h.filter(pl.col('available_us')>first)) is False
    assert all(not row['held_before'] for row in proof2h['risk'][0]['signal_witnesses'])
    with pytest.raises(ValueError):
        a.sma.fixed_targets(daily.filter(pl.col('close_us')!=first-day),daily_decisions,'LONG_SHORT')
    with pytest.raises(ValueError):
        wired['target2h'](signal.filter(pl.col('close_us')!=first-bar),two_decisions,risk_daily_bars=daily)
    late = signal.with_columns(pl.when(pl.col('close_us')==first-bar).then(first+1)
        .otherwise(pl.col('available_us')).alias('available_us'))
    with pytest.raises(ValueError):
        wired['target2h'](late,two_decisions,risk_daily_bars=daily)
    late_daily = daily.with_columns(pl.when(pl.col('close_us')==first-day).then(first+1)
        .otherwise(pl.col('available_us')).alias('available_us'))
    with pytest.raises(ValueError):
        a.sma.fixed_targets(late_daily,daily_decisions,'LONG_SHORT')
    assert max(range(first,end,day)) == end-day and max(range(first,end,bar)) == end-bar
    assert end-minute+minute == end  # Last legal minute closesAug1; no newAug1 decision.
    evidence = dict(scope='ONE_NEW213_WIRING_SYNTHETIC_ONLY_NOT_ECONOMICS',source_records=72,
        selector_records=20,physical_trading_accounts=16,physical_constant_cash_accounts=1,
        derivation=wired['derivation'],funding_counts=funding_counts,SMA=sma_evidence,
        Donchian=target2h.to_dicts(),initial_signal_receipt=proof2h['risk'][0],
        frozen_financial_body_preserved=True,actual_market_arrays_read=False)
    (tmp_path/'wiring_evidence.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
