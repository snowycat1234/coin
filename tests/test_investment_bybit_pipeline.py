"""New received-asset settlement through the actual common research ledger."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from quant.backtest import BacktestConfig
from scripts.investment import compare_simple_strategies as common
from scripts.investment import bybit_spot_adapter


def fixture_minutes():
    start = common.day_us(date(2025, 11, 1))
    frames = []
    for symbol, price in zip(common.SYMBOLS, (100., 50.)):
        times = np.arange(start, start + common.DAY_US, common.MINUTE_US, dtype=np.int64)
        frames.append(pl.DataFrame(dict(symbol=[symbol] * len(times), open_us=times,
            close_us=times + common.MINUTE_US, available_us=times + common.MINUTE_US,
            open=np.full(len(times), price), high=np.full(len(times), price + 1),
            low=np.full(len(times), price - 1), close=np.full(len(times), price),
            quote_volume=np.full(len(times), 100_000_000.), valid_day=[True] * len(times),
            minute_valid=[True] * len(times), missing_reason=[None] * len(times))))
    return start, pl.concat(frames).sort(['open_us', 'symbol'])


def test_received_asset_entry_to_common_minute_nav(tmp_path):
    start, minutes = fixture_minutes()
    targets = pl.DataFrame(dict(symbol=['BTCUSDT', 'ETHUSDT', 'BTCUSDT', 'ETHUSDT'],
        available_us=[start + common.MINUTE_US] * 2 + [start + 60 * common.MINUTE_US] * 2,
        target_weight=[.30, .20, 0., 0.]))
    cfg = BacktestConfig(start_us=start, end_us=start + common.DAY_US,
        target_annual_vol=None, liquidate_at_end=True)
    result = bybit_spot_adapter.run_backtest(minutes.select('symbol', 'close_us', 'available_us'), minutes, targets, cfg)
    ledger = common.write_ledger(tmp_path / 'new-native-ledger', result, minutes)
    inventory = pl.read_parquet(Path(ledger['directory']) / 'minute_nav_inventory.parquet')
    cash = Decimal(str(cfg.initial_cash))
    balances = dict.fromkeys(common.SYMBOLS, Decimal(0))
    fee_value = execution_cost = Decimal(0)
    for fill in result.trades.iter_rows(named=True):
        symbol = fill['symbol']
        qty, price, mid = (Decimal(str(fill[key])) for key in ('quantity', 'fill_price', 'mid_price'))
        rate = Decimal('0.001')
        if fill['side'] == 'buy':
            cash -= qty * price
            balances[symbol] += qty * (1 - rate)
            fee_value += qty * rate * mid
        else:
            assert qty <= balances[symbol] + Decimal('1e-12')
            balances[symbol] -= qty
            cash += qty * price * (1 - rate)
            fee_value += qty * price * rate
        execution_cost += qty * abs(price - mid)
    expected_nav = cash + balances['BTCUSDT'] * 100 + balances['ETHUSDT'] * 50
    assert abs(float(expected_nav) - float(inventory['nav'][-1])) < 1e-7
    assert abs(float(fee_value) - ledger['summary']['fees']) < 1e-7
    assert abs(float(execution_cost) - ledger['summary']['execution_costs']) < 1e-7
    assert ledger['summary']['same_quantity_gross_minus_cost_equals_net']
    assert ledger['summary']['gross_reference_quantity_semantics'].startswith('NET_RECEIVED')
    assert result.trades.filter(pl.col('side') == 'buy')['position_delta'].lt(result.trades.filter(pl.col('side') == 'buy')['quantity']).all()
    assert balances['BTCUSDT'] >= -Decimal('1e-12') and balances['ETHUSDT'] >= -Decimal('1e-12')


def test_reused_derivative_binding_rejects_wrong_hash_and_external_path(tmp_path, monkeypatch):
    start, frame = fixture_minutes()
    root, state = tmp_path / 'repo', tmp_path / 'native-state'
    root.mkdir()
    state.mkdir()
    path = state / 'accepted.parquet'
    frame.write_parquet(path)
    monkeypatch.setattr(common, 'ROOT', root)
    monkeypatch.setattr(common, 'STATE', state)
    parent = dict(status='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING', source_bytes_unchanged=True,
        all_planned_ledgers_complete=True, source_receipt_sha256='s' * 64,
        minute_source=dict(path=str(path), sha256=common.file_sha(path), rows=len(frame)))
    common.save_json(root / 'parent.json', parent)
    reference = dict(report_path='parent.json', report_sha256=common.file_sha(root / 'parent.json'),
        path=str(path), sha256=common.file_sha(path))
    spec = dict(source_receipt_sha256='s' * 64, reused_minute_input=reference)
    assert common.reused_minute_input(spec).equals(frame)
    with pytest.raises(ValueError, match='Exact accepted nativeSTATE'):
        common.reused_minute_input({**spec, 'reused_minute_input': {**reference, 'sha256': '0' * 64}})
    with pytest.raises(ValueError, match='Exact accepted nativeSTATE'):
        common.reused_minute_input({**spec, 'reused_minute_input': {**reference, 'path': str(root / 'never-open.parquet')}})
    with pytest.raises(ValueError, match='Completed unchanged parent'):
        common.reused_minute_input({**spec, 'reused_minute_input': {**reference, 'report_sha256': '0' * 64}})


def test_reused_target_keeps_causal_intents_and_rejects_unbound_calendar(tmp_path, monkeypatch):
    root, state = tmp_path / 'repo', tmp_path / 'native-state'
    root.mkdir(); state.mkdir()
    monkeypatch.setattr(common, 'ROOT', root)
    monkeypatch.setattr(common, 'STATE', state)
    original = common.public_strategy.original
    strategy = common.public_strategy.STRATEGY_2H_ID
    calendar = np.arange(common.day_us(date(2025, 11, 1)), common.day_us(date(2025, 11, 1)) + 3 * common.MINUTE_US,
        common.MINUTE_US, dtype=np.int64)
    plan = original._plan(strategy, calendar, np.array([[.3, 0.], [.3, 0.], [0., 0.]]),
        [['fixture', 'fixture']] * 3, metadata=dict(timeframe_minutes=120,
            public_upstream_sha256=common.public_strategy.PINNED_HASHES))
    intent = plan.calendar_ledger.rename({'earliest_permissible_order_us': 'preserved_v8_intent_earliest_order_us'}).with_columns(
        (pl.col('decision_us') + common.MINUTE_US).alias('comparison_order_eligible_us'))
    plan.targets.write_parquet(state / 'targets.parquet')
    intent.write_parquet(state / 'intent_calendar.parquet')
    common.save_json(state / 'target_receipt.json', plan.receipt)
    reference = {name: dict(path=str(state / name), sha256=common.file_sha(state / name))
        for name in ('targets.parquet', 'intent_calendar.parquet', 'target_receipt.json')}
    target_bindings = {key: reference[name]['sha256'] for key, name in
        (('target_sha256', 'targets.parquet'), ('intent_sha256', 'intent_calendar.parquet'), ('receipt_sha256', 'target_receipt.json'))}
    audit = dict(status='PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE', ledgers=[
        dict(fold='FIXTURE', strategy=strategy, spread_bps=spread, target_bindings=target_bindings) for spread in (2, 4, 8)])
    common.save_json(root / 'audit.json', audit)
    reference['accepted_audit'] = dict(path='audit.json', sha256=common.file_sha(root / 'audit.json'))
    spec = dict(reused_target_inputs={'FIXTURE:' + strategy: reference})
    reused = common.reused_public_target(spec, strategy, 'FIXTURE', calendar)
    assert reused.targets.equals(plan.targets) and reused.calendar_ledger.equals(plan.calendar_ledger)
    with pytest.raises(ValueError, match='causal public2h'):
        common.reused_public_target(spec, strategy, 'FIXTURE', calendar + common.MINUTE_US)
    with pytest.raises(ValueError, match='previously accepted'):
        common.reused_public_target(dict(reused_target_inputs={'FIXTURE:' + strategy:
            {**reference, 'targets.parquet': {**reference['targets.parquet'], 'sha256': '0' * 64}}}), strategy, 'FIXTURE', calendar)


def test_shared_synthetic_acceptance_refuses_changed_code_or_cost():
    hashes = {'scripts/investment/bybit_spot_adapter.py': 'a' * 64,
        'tests/test_investment_bybit_pipeline.py': 'b' * 64, 'protocols/PERIOD122.json': 'c' * 64}
    accepted = dict(status='PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT',
        binding=dict(source_hashes=hashes), registration_start=dict(hyperparameters={'risk': .3},
            cost_assumptions={'fee': 10}, thresholds={'fixed': True}))
    spec = dict(fee_settlement='BYBIT_SPOT_RECEIVED_ASSET_V1', common_config={'risk': .3}, costs={'fee': 10}, strategy_rules={'fixed': True})
    assert common.accept_synthetic_receipt(accepted, spec, {**hashes, 'protocols/PERIOD90.json': 'd' * 64}).startswith('EXACT_SHARED')
    with pytest.raises(ValueError, match='All shared'):
        common.accept_synthetic_receipt(accepted, spec, {**hashes, 'scripts/investment/bybit_spot_adapter.py': '0' * 64})
    with pytest.raises(ValueError, match='All shared'):
        common.accept_synthetic_receipt(accepted, {**spec, 'costs': {'fee': 5.5}}, hashes)
