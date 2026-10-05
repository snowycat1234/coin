"""Actual paired fills for an explicit discretionary Spot rebalance band."""
from dataclasses import replace

import numpy as np
import polars as pl
import pytest

from quant.backtest import BacktestConfig, MINUTE_US, run_backtest

START = 1_640_995_200_000_000


def fixture(volume=10_000_000.):
    minutes = pl.DataFrame({'symbol': ['BTCUSDT'] * 90,
        'open_us': START + np.arange(90, dtype=np.int64) * MINUTE_US,
        'open': [100.] * 90, 'close': [100.] * 90,
        'quote_volume': [volume] * 90})
    bars = pl.DataFrame([{'symbol': 'BTCUSDT', 'available_us': START + t * MINUTE_US,
        'close_us': START + t * MINUTE_US} for t in (15, 30, 45, 60)])
    return bars, minutes


def targets(*rows, declared=True):
    records = []
    for minute, weight, discretionary, reason, forced in rows:
        row = {'symbol': 'BTCUSDT', 'available_us': START + minute * MINUTE_US,
            'target_weight': weight, 'risk_forced_exit': forced}
        if declared:
            row.update(discretionary_rebalance=discretionary, target_reason=reason)
        records.append(row)
    return pl.DataFrame(records)


def cfg(band=50., **changes):
    return BacktestConfig(target_annual_vol=None, min_notional=0,
        half_spread_bps=0, slippage_bps=0, lot_step_by_symbol={},
        fee_settlement='RECEIVED_ASSET', discretionary_rebalance_min_notional=band, **changes)


@pytest.mark.parametrize('second_weight,side', [(.101, 'buy'), (.099, 'sell')])
def test_small_explicit_discretionary_buy_sell_are_skipped_without_account_mutation(second_weight, side):
    bars, minutes = fixture()
    intent = targets((15, .1, False, 'INITIAL_TARGET', False),
        (30, second_weight, True, 'DISCRETIONARY_REBALANCE', False))
    old = run_backtest(bars, minutes, intent, cfg(0))
    new = run_backtest(bars, minutes, intent, cfg())
    first_only = run_backtest(bars, minutes,
        targets((15, .1, False, 'INITIAL_TARGET', False)), cfg())
    assert old.trades.height == 2 and old.trades['side'][1] == side
    assert old.trades['notional'][1] < 50
    assert new.trades.height == 1
    assert new.orders.filter(pl.col('status') == 'rebalance_band').height == 1
    assert new.daily_nav.equals(first_only.daily_nav)
    assert new.summary['open_positions'] == first_only.summary['open_positions']
    assert new.summary['fees'] == first_only.summary['fees']


@pytest.mark.parametrize('reason', ['SIGNAL_COMPONENT_CHANGE', 'VOLATILITY_RISK_REDUCTION', 'DATA_EXIT'])
def test_protected_small_target_changes_execute(reason):
    bars, minutes = fixture()
    result = run_backtest(bars, minutes,
        targets((15, .1, False, 'INITIAL_TARGET', False), (30, .099, False, reason, False)), cfg())
    assert result.trades.height == 2
    assert result.trades['side'][1] == 'sell'
    assert result.trades['notional'][1] < 50
    assert 'rebalance_band' not in result.orders['status'].to_list()


def test_explicit_forced_risk_exit_cannot_be_suppressed_by_small_discretionary_flag():
    bars, minutes = fixture()
    result = run_backtest(bars, minutes,
        targets((15, .1, False, 'INITIAL_TARGET', False),
            (30, .099, True, 'DISCRETIONARY_REBALANCE', True)), cfg())
    assert result.trades.height == 2
    assert result.trades['side'][1] == 'sell'
    assert 'rebalance_band' not in result.orders['status'].to_list()


def test_small_reduction_after_price_drift_breaches_cap_is_not_discretionary():
    bars, minutes = fixture()
    minutes = minutes.with_columns([
        pl.when(pl.col('open_us') >= START + 30 * MINUTE_US).then(101.)
        .otherwise(pl.col(c)).alias(c) for c in ('open', 'close')])
    result = run_backtest(bars, minutes,
        targets((15, .3, False, 'INITIAL_TARGET', False),
            (30, .3, True, 'DISCRETIONARY_REBALANCE', False)), cfg())
    assert result.trades.height == 2
    assert result.trades['side'][1] == 'sell'
    assert result.trades['notional'][1] < 50
    assert 'rebalance_band' not in result.orders['status'].to_list()
    assert result.trades['asset_weight_after'][1] <= .3 + 1e-9


def test_first_inventory_entry_below_band_still_executes():
    bars, minutes = fixture()
    result = run_backtest(bars, minutes,
        targets((15, .002, True, 'DISCRETIONARY_REBALANCE', False)), cfg())
    assert result.trades.height == 1
    assert 0 < result.trades['notional'][0] < 50
    assert result.summary['open_positions']['BTCUSDT'] > 0


def test_started_partial_order_completes_even_when_remaining_goal_below_band():
    bars, minutes = fixture(volume=40_000.)
    result = run_backtest(bars, minutes,
        targets((15, .013, True, 'DISCRETIONARY_REBALANCE', False)), cfg())
    assert result.trades.height == 4
    assert result.trades['notional'].to_list()[:3] == pytest.approx([40] * 3)
    assert 0 < result.trades['notional'][3] < 50
    assert result.orders['status'].to_list() == ['partial', 'partial', 'partial', 'filled']


def test_zero_and_terminal_exit_keep_all_inventory_and_fees_in_ledger():
    bars, minutes = fixture()
    signal = run_backtest(bars, minutes,
        targets((15, .002, False, 'INITIAL_TARGET', False),
            (30, 0., True, 'DISCRETIONARY_REBALANCE', False)), cfg())
    terminal = run_backtest(bars, minutes,
        targets((15, .002, True, 'DISCRETIONARY_REBALANCE', False)),
        cfg(liquidate_at_end=True, terminal_exit_minutes=5))
    for result in (signal, terminal):
        assert result.trades['side'].to_list() == ['buy', 'sell']
        assert result.summary['open_positions']['BTCUSDT'] == 0
        assert result.summary['final_nav'] == pytest.approx(10_000 - result.summary['fees'], abs=1e-8)
        assert 'rebalance_band' not in result.orders['status'].to_list()


def test_absent_discretionary_declaration_preserves_small_orders():
    bars, minutes = fixture()
    result = run_backtest(bars, minutes,
        targets((15, .1, False, 'UNKNOWN', False),
            (30, .101, False, 'UNKNOWN', False), declared=False), cfg())
    assert result.trades.height == 2
    assert result.trades['notional'][1] < 50
    assert 'rebalance_band' not in result.orders['status'].to_list()


def test_discretionary_boolean_must_not_be_unknown_or_integer():
    bars, minutes = fixture()
    normal = targets((15, .1, True, 'DISCRETIONARY_REBALANCE', False))
    for bad in (normal.with_columns(pl.lit(None, dtype=pl.Boolean).alias('discretionary_rebalance')),
                normal.with_columns(pl.lit(1).alias('discretionary_rebalance'))):
        with pytest.raises(ValueError):
            run_backtest(bars, minutes, bad, cfg())


def test_other_asset_cap_breach_protects_small_reduction():
    bars, minutes=fixture()
    bars=pl.concat([bars,bars.with_columns(pl.lit('ETHUSDT').alias('symbol'))])
    bars=bars.with_columns(pl.when(pl.col('symbol')=='BTCUSDT').then(pl.lit('ZZZUSDT')).otherwise(pl.col('symbol')).alias('symbol'))
    eth=minutes.with_columns(pl.lit('ETHUSDT').alias('symbol'))
    minutes=pl.concat([minutes.with_columns([
        pl.when(pl.col('open_us')>=START+30*MINUTE_US).then(101.)
        .otherwise(pl.col(c)).alias(c) for c in ('open','close')]).with_columns(pl.lit('ZZZUSDT').alias('symbol')),eth])
    intent=pl.concat([targets((15,.3,False,'INITIAL_TARGET',False),
        (30,.3,True,'DISCRETIONARY_REBALANCE',False)).with_columns(pl.lit('ZZZUSDT').alias('symbol')),
        targets((15,.1,False,'INITIAL_TARGET',False),
            (30,.099,True,'DISCRETIONARY_REBALANCE',False)).with_columns(pl.lit('ETHUSDT').alias('symbol'))])
    result=run_backtest(bars,minutes,intent,cfg())
    eth_sell=result.trades.filter((pl.col('symbol')=='ETHUSDT')&(pl.col('side')=='sell'))
    assert eth_sell.height==1 and eth_sell['notional'][0]<50
    assert eth_sell['rebalance_band_exempt'][0]


def test_target_flags_protect_pool_signal_and_small_component_risk_decrease():
    from scripts.investment.spot_perpetual_product_comparison import discretionary_targets
    symbols=['BTCUSDT','ETHUSDT']
    risks=[]
    for i in range(4):
        risks.append(dict(decision_us=START+i*MINUTE_US,symbol_order=symbols,
            eligibility=dict.fromkeys(symbols,'ELIGIBLE'),component_HOLD_raw=[.3,.3],
            component_EXIT10_raw=[0.,0.] if i<2 else [.3,0.],
            component_HOLD_target=[.1,.1-1e-15] if i==3 else [.1,.1],
            component_EXIT10_target=[0.,0.] if i<2 else [.1,0.]))
    frame=pl.DataFrame([dict(available_us=r['decision_us'],symbol=s,target_weight=.1,
        eligibility_reason='ELIGIBLE') for r in risks for s in symbols])
    marked=discretionary_targets(frame,dict(symbols=symbols,risk=risks))
    assert marked['target_reason'].to_list()==['INITIAL_TARGET','INITIAL_TARGET',
        'DISCRETIONARY_REBALANCE','DISCRETIONARY_REBALANCE',
        'SIGNAL_COMPONENT_CHANGE','SIGNAL_COMPONENT_CHANGE',
        'DISCRETIONARY_REBALANCE','VOLATILITY_RISK_REDUCTION']


def test_default_zero_exact_prior_wallet_behavior(tmp_path):
    import importlib.util,subprocess,sys
    oldpath=tmp_path/'prior_backtest.py'
    oldpath.write_bytes(subprocess.check_output(['git','show','6ef22565d61f0771493f2e91a8bf1bc42e00b3d6:src/quant/backtest.py']))
    spec=importlib.util.spec_from_file_location('d079_prior_normal_account',oldpath)
    old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
    bars,minutes=fixture()
    intent=targets((15,.3,False,'INITIAL_TARGET',False),(30,.299,True,'DISCRETIONARY_REBALANCE',False),
        (45,0.,False,'SIGNAL_COMPONENT_CHANGE',False))
    from dataclasses import asdict
    for settlement in ('QUOTE','RECEIVED_ASSET'):
        current_config=replace(cfg(0),fee_settlement=settlement,liquidate_at_end=True,terminal_exit_minutes=5)
        values=asdict(current_config);values.pop('discretionary_rebalance_min_notional')
        prior=old.run_backtest(bars,minutes,intent,old.BacktestConfig(**values))
        current=run_backtest(bars,minutes,intent,current_config)
        for name in ('trades','orders','daily_nav','round_trips'):
            assert getattr(prior,name).equals(getattr(current,name))
        assert prior.summary==current.summary
