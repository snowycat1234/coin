"""Independent cost arithmetic plus the actual target->fill->NAV->report path.

Synthetic fixtures only: optimistic cost cases do not estimate historical fills.
"""
from copy import deepcopy
from decimal import Decimal as D
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import polars as pl
import pytest

from quant.paths import ROOT
from quant.perpetual_account import PerpetualConfig, USDTLinearPerpetualAccount as Account
from scripts.investment.bybit_cost_inputs import snapshot_cost, scenario_config, cash_cost_summary
from scripts.investment import perpetual_directional as runner

SOURCE = ROOT / 'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json'
ZONE = 'DERIVATIVES_CRYPTO_STANDARD'
MINUTE = 60_000_000
DAY = 1440 * MINUTE


def cost(spread=2, slip=1, zone=ZONE, symbols=('BTCUSDT',)):
    return snapshot_cost(SOURCE, symbols=symbols, fee_zone_by_symbol=dict.fromkeys(symbols, zone),
        scenario_id='SYNTHETIC_EXPLICIT_COST', half_spread_bps=spread, slippage_bps=slip,
        execution_source_ref='SYNTHETIC_HAND_2_PLUS_1_BP_NOT_CALIBRATED',
        execution_status='UNVERIFIED_SYNTHETIC_ONLY_NOT_HISTORICAL_BBO')


def mark(account, t, price='100'):
    account.update_marks(t, {s:dict(price=price, close_us=t, available_us=t) for s in account.symbols})


def fill(account, side, q, t, identity, **kwargs):
    return account.execute_fill('BTCUSDT', side, q, t, t-MINUTE-1, identity,
        execution_mid_price='100', quote_available_us=t, **kwargs)


def test_user_snapshot_to_actual_taker_fee_and_unequal_friction_hand_account(tmp_path):
    c = cost()
    config = PerpetualConfig(**{**scenario_config(c).__dict__, 'initial_cash':D('100000')})
    account = Account(config, symbols=('BTCUSDT',), cost_context=c['provenance'])
    mark(account, 0)
    assert fill(account, 'BUY', '100', MINUTE+1, 'open')['status'] == 'FILLED'
    assert account.positions['BTCUSDT'].entry_price == D('100.03')
    assert account.fees == D('5.50165')
    mark(account, 2*MINUTE)
    assert fill(account, 'SELL', '100', 3*MINUTE+1, 'close', reduce_only=True)['status'] == 'FILLED'
    assert account.trades[-1]['decimal_strings']['fill_price'] == '99.9700'
    assert account.fees == D('11') and account.execution_cost == D('6')
    assert account.nav() == D('99983')
    assert account.summary()['configured_nominal_roundtrip_bps'] == 17
    assert account.summary()['contract']['nominal_roundtrip_bps'] == 17
    assert account.cost_context['liquidity_role'] == 'TAKER'
    assert Account.from_snapshot(account.snapshot(), expected_cost_context=c['provenance']).snapshot() == account.snapshot()
    (tmp_path/'exact_cost_ledger.json').write_text(json.dumps(account.snapshot(), indent=2))


def test_zero_extra_friction_reversal_partial_and_reduce_only_are_not_free():
    c = cost(0, 0)
    account = Account(scenario_config(c), symbols=('BTCUSDT',), cost_context=c['provenance'])
    mark(account, 0)
    fill(account, 'BUY', '20', MINUTE+1, 'open')
    mark(account, 2*MINUTE)
    reverse = fill(account, 'SELL', '40', 3*MINUTE+1, 'reverse', available_quantity='30')
    assert reverse['status'] == 'PARTIAL'
    assert [D(r['decimal_strings']['quantity']) for r in reverse['fills']] == [D(20), D(10)]
    assert account.positions['BTCUSDT'].quantity == -10
    mark(account, 4*MINUTE)
    close = fill(account, 'BUY', '100', 5*MINUTE+1, 'reduce', reduce_only=True)
    assert D(close['decimal_strings']['executed_quantity']) == 10
    assert account.positions['BTCUSDT'].quantity == 0
    # 20 buy + 20 close long + 10 open short + 10 close short, each 100 USDT.
    assert account.fees == D('3.30') and account.execution_cost == 0
    assert account.nav() == D('9996.70')
    assert account.summary()['configured_nominal_roundtrip_bps'] == 11
    assert Account.from_snapshot(account.snapshot()).nav() == account.nav()


def test_fee_zones_are_explicit_product_scenarios_not_symbol_or_maker_inference():
    for zone, fee in [(ZONE, D('.00055')), ('DERIVATIVES_INNOVATION', D('.0011')),
                      ('DERIVATIVES_PREMARKET', D('.001'))]:
        c = cost(zone=zone)
        account = Account(scenario_config(c), symbols=('BTCUSDT',), cost_context=c['provenance'])
        mark(account, 0)
        fill(account, 'SELL', 10, MINUTE+1, zone)
        assert account.fees == D(10)*D('99.97')*fee
        assert account.cost_context['native_fee_zone_certified'] is False
        assert account.cost_context['fee_source_sha256'] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    for zone in ('SPOT_CRYPTO_STANDARD', 'DERIVATIVES_TRADFI', 'OPTIONS_STANDARD', 'UNKNOWN'):
        with pytest.raises(ValueError):
            cost(zone=zone)
    c = cost(symbols=('BTCUSDT','ETHUSDT'))
    c['provenance']['fee_zone_by_symbol']['ETHUSDT'] = 'DERIVATIVES_INNOVATION'
    with pytest.raises(ValueError):
        Account(scenario_config(c), cost_context=c['provenance'])
    c = cost(); c['provenance']['liquidity_role'] = 'MAKER'
    with pytest.raises(ValueError):
        Account(scenario_config(c), symbols=('BTCUSDT',), cost_context=c['provenance'])


def test_invalid_costs_risk_unchanged_and_cost_snapshot_tamper_rejected():
    for args in ({'fee_rate':-1}, {'fee_rate':1}, {'fee_rate':'NaN'}, {'fee_rate':True},
                 {'half_spread_bps':-1}, {'slippage_bps':'Infinity'}, {'half_spread_bps':10000},
                 {'leverage':2}, {'max_asset_weight':'.31'}, {'max_gross_weight':'.61'}):
        with pytest.raises(ValueError):
            PerpetualConfig(**args)
    with pytest.raises(ValueError):
        Account(PerpetualConfig(half_spread_bps=2, slippage_bps=1))
    c = cost(); account = Account(scenario_config(c), symbols=('BTCUSDT',), cost_context=c['provenance'])
    mark(account, 0); fill(account,'BUY',10,MINUTE+1,'open')
    original = account.snapshot()
    corrupt = deepcopy(original)
    corrupt['config']['fee_rate'] = '.0011'
    corrupt['cost_context']['fee_rate_fraction'] = '.0011'
    corrupt['cost_context']['fee_zone_by_symbol']['BTCUSDT'] = 'DERIVATIVES_INNOVATION'
    replacement = Account(PerpetualConfig(**corrupt['config']), symbols=('BTCUSDT',), cost_context=corrupt['cost_context'])
    corrupt['contract'] = replacement.contract_metadata()
    with pytest.raises(ValueError, match='per-leg cost/config'):
        Account.from_snapshot(corrupt)
    other_context = deepcopy(original['cost_context'])
    other_context['execution_source_ref'] = 'ANOTHER_SCENARIO_SOURCE'
    with pytest.raises(ValueError, match='expected cost'):
        Account.from_snapshot(original, expected_cost_context=other_context)
    assert account.snapshot() == original


def test_legacy_base_stress_cashflows_exact_against_git_parent(tmp_path):
    raw = subprocess.check_output(['git','show','f895f4b32e3c2e6e61b15b022ce46736982e9865:src/quant/perpetual_account.py'], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == '9a4223d1115add6ed2cce5b695cf6dcd89459daa6918eb61091b188e5ec05754'
    path = tmp_path/'original_account.py'; path.write_bytes(raw)
    name = 'quant._independent_parent_cost_account'
    spec = importlib.util.spec_from_file_location(name, path)
    old = importlib.util.module_from_spec(spec); sys.modules[name] = old; spec.loader.exec_module(old)
    for friction, rt in [(4,27), (8,43)]:
        accounts = [Account(PerpetualConfig(half_spread_bps=friction,slippage_bps=friction)),
                    old.USDTLinearPerpetualAccount(old.PerpetualConfig(half_spread_bps=friction,slippage_bps=friction))]
        for account in accounts:
            mark(account,0); fill(account,'SELL',10,MINUTE+1,'short')
            mark(account,2*MINUTE, '90')
            account.apply_funding('BTCUSDT','f',2*MINUTE+1,'.001',2*MINUTE+1)
            fill(account,'BUY',15,3*MINUTE+1,'reverse')
        new, previous = accounts
        assert new.trades == previous.trades and new.funding == previous.funding
        for key in ('free_cash','fees','execution_cost','funding_cash','realized_PnL','gross_fill_turnover'):
            assert getattr(new,key) == getattr(previous,key)
        assert new.nav() == previous.nav()
        assert new.contract_metadata()['nominal_roundtrip_bps'] == rt
        # The sole old stress contract correction is metadata, not journal/NAV.
        restored = Account.from_snapshot(previous.snapshot())
        assert restored.trades == previous.trades and restored.nav() == previous.nav()
        assert restored.contract_metadata()['nominal_roundtrip_bps'] == rt
    del sys.modules[name]


def test_active_runner_signed_target_fee_and_asymmetric_month_report(tmp_path):
    start = 1735689600000000; end = start+2*DAY; n = 2880
    daily = pl.DataFrame([dict(symbol='BTCUSDT', close_us=start+i*DAY, close=100.) for i in range(3)])
    window = dict(symbols=('BTCUSDT',),start=start,end=end,daily=daily,events=[],
        market={'BTCUSDT':{k:np.full(n,v) for k,v in dict(open=100.,close=100.,mark=100.,quote_volume=5000000.).items()}})
    def targets(bars, decisions, mode):
        return pl.DataFrame([dict(symbol='BTCUSDT',available_us=int(t),target_weight=w)
            for t,w in zip(decisions,[.2,-.2],strict=True)]), {'source':'SYNTHETIC_FIXED_SIGNED_DIRECTIONS'}
    output = []
    for friction in ((2,1),(0,0)):
        c = cost(*friction)
        case = runner.simulate(window, 'LONG_SHORT', c, {'id':'SYNTHETIC_NO_EVENTS','scale':1.},target_factory=targets)
        artifacts = runner.save_case(case,tmp_path/f'case-{friction[0]}-{friction[1]}')
        summary = case['summary']
        assert summary['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT' and summary['completed_minutes'] == n
        assert any(r['side']=='SELL' and r['leg']=='OPEN' for r in case['trades'])
        assert summary['terminal_cash_realized']
        fees = sum(D(r['decimal_strings']['quantity'])*D(r['decimal_strings']['fill_price'])*D('.00055') for r in case['trades'])
        execution = sum(D(r['decimal_strings']['quantity'])*abs(D(r['decimal_strings']['fill_price'])-D(100)) for r in case['trades'])
        assert abs(D(str(summary['net_PnL']))+fees+execution) < D('1e-7')
        assert abs(summary['spread_cost_USDT']+summary['slippage_cost_USDT']-float(execution)) < 1e-10
        expected_spread = float(execution)*2/3 if friction[0] else 0.
        assert abs(summary['spread_cost_USDT']-expected_spread) < 1e-10
        assert abs(summary['months'][0]['spread_cost']-expected_spread) < 1e-10
        assert summary['contract']['cost_provenance']['fee_source_sha256'] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        output.append(dict(summary=summary,artifact_hashes=artifacts))
    (tmp_path/'actual_runner_synthetic_economics.json').write_text(json.dumps(output,indent=2))


def test_actual_cash_branch_rebinds_fee_contract_and_exact_summary():
    base = cash_cost_summary(runner.COSTS[0], ('BTCUSDT','ETHUSDT'))
    base['completed_minutes'] = 2880
    stress = cash_cost_summary(runner.COSTS[1], ('BTCUSDT','ETHUSDT'), base)
    assert stress['contract']['nominal_roundtrip_bps'] == 43
    assert D(stress['decimal_strings']['configured_nominal_roundtrip_bps']) == 43
    assert stress['NAV'] == 10000 and stress['net_PnL'] == 0 and stress['completed_minutes'] == 2880
    c = cost(0,0,symbols=('BTCUSDT','ETHUSDT'))
    optimistic = cash_cost_summary(c, ('BTCUSDT','ETHUSDT'), stress)
    assert optimistic['contract']['nominal_roundtrip_bps'] == 11
    assert optimistic['contract']['cost_provenance']['fee_source_sha256'] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert optimistic['fees_USDT'] == optimistic['execution_cost_USDT'] == 0
    bad = deepcopy(base); bad['trade_legs'] = 1
    with pytest.raises(ValueError):
        cash_cost_summary(runner.COSTS[1], ('BTCUSDT','ETHUSDT'), bad)
