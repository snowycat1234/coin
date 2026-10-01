from dataclasses import replace

import pytest

from quant.backtest import BacktestConfig
from quant.execution_contract import MINUTE_US, ExecutionContractV2
from quant.execution_parity import cross_engine_parity


def test_canonical_default_and_boundary_receipt_semantics():
    contract = ExecutionContractV2()
    assert BacktestConfig().latency_minutes == 1
    boundary = 3_600_000_000
    assert contract.earliest_execution_us(boundary) == boundary + MINUTE_US
    assert contract.earliest_execution_us(boundary + 1) == boundary + 2 * MINUTE_US
    order = contract.order_times_ms(boundary, boundary // 1000 + 500)
    assert order["not_before_ms"] == (boundary + MINUTE_US) // 1000
    assert order["signal_received_ms"] == boundary // 1000 + 500
    assert order["expires_ms"] == (boundary + 6 * MINUTE_US) // 1000
    assert contract.capacity_minute_us(boundary + MINUTE_US + 123) == boundary
    assert contract.earliest_execution_us(boundary, extra_delay_minutes=1) == (
        boundary + 2 * MINUTE_US)


@pytest.mark.parametrize("bad", [-1, True, 1.5])
def test_no_invalid_decision_or_config_delay(bad):
    with pytest.raises(ValueError):
        ExecutionContractV2().earliest_execution_us(bad)
    with pytest.raises(ValueError):
        BacktestConfig(latency_minutes=bad)


def test_no_early_receipt_or_changed_canonical_parameters():
    contract = ExecutionContractV2()
    with pytest.raises(ValueError, match="before"):
        contract.order_times_ms(3_600_000_000, 3_599_999)
    with pytest.raises(ValueError, match="frozen"):
        replace(contract, latency_minutes=0)
    assert contract.rebalance_buffer(0.0005, 0.001, 0.6) == pytest.approx(0.9981994)
    assert len(contract.digest()) == 64


@pytest.mark.parametrize("params", [{}, {"partial": True}, {"fee_multiplier": 2},
                                    {"slippage_multiplier": 2}])
def test_actual_cross_engine_price_capacity_quantity_cash_and_expiry(params):
    report = cross_engine_parity(**params)
    assert report["pass"] and report["fills"] >= 4
    assert report["first_execution_minute_us"] == report["signal_us"] + MINUTE_US
    assert report["capacity_source_minute_us"] == report["signal_us"]
    assert report["historical_expired"] == report["live_expired"]
    if params.get("partial"):
        assert report["historical_expired"] == 2
