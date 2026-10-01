from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import polars as pl
import pytest

from quant import baselines_v2
from quant.backtest import BacktestConfig
from quant.baselines_v2 import (
    HOUR_US,
    LOCKED_HISTORICAL_START_US,
    BaselineAdmissionError,
    baseline_targets_v2,
    run_baseline_suite,
    strong_baseline_signals,
)
from quant.paths import ROOT

BASE = 1_704_067_200_000_000


def bars(prices, *, symbol="BTCUSDT", high=None, low=None, skip=None):
    rows = []
    for index, price in enumerate(prices):
        if index == skip:
            continue
        opened = BASE + index * HOUR_US
        rows.append({
            "symbol": symbol, "interval": "1h", "open_us": opened,
            "close_us": opened + HOUR_US, "available_us": opened + HOUR_US,
            "open": float(price), "close": float(price),
            "high": float(high[index] if high else price + 1),
            "low": float(low[index] if low else price - 1),
        })
    return pl.DataFrame(rows)


def test_donchian_uses_previous_channels_not_current_extrema_and_never_intrabar_touch():
    prices = [95] * 55 + [101, 89, 101]
    highs = [100] * 55 + [150, 110, 200]
    lows = [90] * 55 + [91, 80, 90]
    result = strong_baseline_signals(bars(prices, high=highs, low=lows), "B3")
    assert not any(result["is_long"][:55])
    assert result.row(55, named=True)["entry_channel"] == 100
    assert result["is_long"][55]
    assert result.row(56, named=True)["exit_channel"] == 90
    assert not result["is_long"][56]  # own low=80 must not suppress exit against past low=90
    assert not result["is_long"][57]  # high touches 200, but close doesn't break previous 150


def test_donchian_strict_threshold_and_position_persistence():
    prices = [95] * 55 + [100, 101, 90, 89]
    highs = [100] * 55 + [100, 101, 100, 100]
    lows = [90] * 55 + [90, 90, 90, 89]
    result = strong_baseline_signals(bars(prices, high=highs, low=lows), "B3")
    assert result["is_long"][-4:].to_list() == [False, True, True, False]
    assert result["target_weight"][-4:].to_list() == [0.0, 0.3, 0.3, 0.0]


def test_slow_momentum_requires_full_lag168_and_causal_ema168_independent_formula():
    prices = [100] * 168 + [110, 90, 110]
    result = strong_baseline_signals(bars(prices), "B4")
    expected_ema = pl.Series(prices).cast(pl.Float64).ewm_mean(span=168, adjust=False)
    assert result["warmup_complete"][:168].to_list() == [False] * 168
    assert result["is_long"][-3:].to_list() == [True, False, True]
    assert result["return_168h"][168] == pytest.approx(0.1)
    np.testing.assert_allclose(result["ema168"][167:].to_numpy(), expected_ema[167:].to_numpy())
    # Positive seven-day return alone is insufficient when current price is below EMA.
    result = strong_baseline_signals(bars([90] + [120] * 167 + [100]), "B4")
    assert result["return_168h"][-1] > 0
    assert result["close"][-1] < result["ema168"][-1]
    assert not result["is_long"][-1]


@pytest.mark.parametrize("name,window", [("B3", 55), ("B4", 168)])
def test_missing_hour_resets_warmup_and_does_not_forward_fill(name, window):
    values = [100 + index * 0.1 for index in range(400)]
    data = bars(values, skip=200)
    result = strong_baseline_signals(data, name)
    segment = result.filter(pl.col("open_us") >= BASE + 201 * HOUR_US)
    assert segment["warmup_complete"][:window].to_list() == [False] * window
    assert segment["target_weight"][:window].to_list() == [0.0] * window
    assert segment["warmup_complete"][window]


@pytest.mark.parametrize("name", ["B3", "B4"])
def test_future_changes_cannot_alter_historical_signals_and_symbols_stay_independent(name):
    prices = [100 + np.sin(index / 9) + index * 0.02 for index in range(350)]
    original = bars(prices)
    changed = bars(prices[:250] + [500.0] * 100)
    before = strong_baseline_signals(original, name).head(250)
    after = strong_baseline_signals(changed, name).head(250)
    assert before.equals(after)
    both = pl.concat([original, bars([200] * 350, symbol="ETHUSDT")]).reverse()
    combined = strong_baseline_signals(both, name)
    assert combined.filter(pl.col("symbol") == "BTCUSDT").equals(
        strong_baseline_signals(original, name)
    )


def test_incomplete_duplicate_or_unavailable_hour_is_rejected():
    data = bars([100, 100, 100])
    with pytest.raises(ValueError, match="Duplicate"):
        baseline_targets_v2(pl.concat([data, data.head(1)]), "B3")
    with pytest.raises(ValueError, match="complete"):
        baseline_targets_v2(data.with_columns(pl.lit("15m").alias("interval")), "B4")
    with pytest.raises(ValueError, match="complete"):
        baseline_targets_v2(
            data.with_columns((pl.col("close_us") - 1).alias("available_us")), "B3"
        )
    with pytest.raises(ValueError, match="Availability"):
        baseline_targets_v2(
            data.with_columns(pl.lit(BASE + 100 * HOUR_US).alias("available_us")), "B3"
        )


def test_A01_missing_rejects_before_any_signal_or_backtest(monkeypatch):
    monkeypatch.setattr(baselines_v2, "baseline_targets_v2", lambda *_: pytest.fail("signal ran"))
    with pytest.raises(BaselineAdmissionError, match="not available"):
        run_baseline_suite(
            pl.DataFrame(), pl.DataFrame(), BacktestConfig(),
            parity_receipt=ROOT / "reports/ABSENT_A01_TEST_ONLY.json",
        )


@pytest.mark.parametrize("change", [
    {"execution_contract_version": "legacy_execution_v1"},
    {"cross_engine_parity": {"pass": False}},
    {"canonical_baselines": {"status": "PENDING"}},
    {"source_hashes": {}},
    {"source_hashes": {"../backtest.py": "0" * 64}},
    {"source_hashes": {"backtest.py": "0" * 64}},
])
def test_self_declared_A01_PASS_without_current_evidence_is_rejected(change):
    receipt = {
        "status": "PASS", "execution_contract_version": "execution_v2",
        "cross_engine_parity": {"pass": True},
        "canonical_baselines": {"status": "PASS"},
        "source_hashes": {},
        **change,
    }
    with pytest.raises(BaselineAdmissionError):
        baselines_v2._verify_parity_receipt(receipt)


@pytest.mark.parametrize("change", [
    {"latency_minutes": 0}, {"max_order_wait_minutes": 10},
    {"target_annual_vol": None}, {"participation_rate": 0.0001},
    {"fee_bps": 5}, {"vol_window_days": 31},
    {"end_us": LOCKED_HISTORICAL_START_US + HOUR_US},
])
def test_formal_V2_config_cannot_change_contract_or_reach_locked_history(change):
    config = BacktestConfig(latency_minutes=1, start_us=BASE, end_us=BASE + 200 * HOUR_US)
    with pytest.raises(BaselineAdmissionError):
        baselines_v2._verify_v2_config(replace(config, **change))


def test_suite_mock_only_preserves_fixed_all_baselines_costs_and_active_median(monkeypatch):
    # No historical performance is evaluated before A01. The wrapper is exercised
    # against an injected stub, explicitly confined to this synthetic unit test.
    monkeypatch.setattr(baselines_v2, "_v2_preflight", lambda *_: {"status": "TEST_STUB_ONLY"})
    from quant import disk

    reserves, seen = [], []
    monkeypatch.setattr(disk, "check", lambda reserve: reserves.append(reserve))

    def fake_run(hourly, minutes, targets, settings):
        seen.append((targets, settings))
        index = (len(seen) - 1) % 5
        return SimpleNamespace(summary={"total_return": index, "sharpe": index})

    monkeypatch.setattr(baselines_v2, "run_backtest", fake_run)
    config = BacktestConfig(latency_minutes=1, start_us=BASE, end_us=BASE + 200 * HOUR_US)
    result = run_baseline_suite(bars([100] * 200), pl.DataFrame(), config)
    assert len(seen) == 15
    assert reserves == [752_000_000]
    assert result["active_baselines"] == ["B2", "B3", "B4"]
    assert result["scenarios"]["base"]["active_median_net_return"] == 3
    assert result["alpha_candidate"] is False and result["true_forward_days"] == 0
    for index, (_, settings) in enumerate(seen):
        expected = [(1.0, 1.0), (2.0, 1.0), (1.0, 2.0)][index // 5]
        assert (settings.fee_multiplier, settings.slippage_multiplier) == expected
        assert settings.latency_minutes == 1 and settings.participation_rate == 0.001
        assert settings.max_weight == 0.30 and settings.max_gross == 0.60
        assert settings.target_annual_vol == 0.10
    with pytest.raises(BaselineAdmissionError, match="locked historical"):
        run_baseline_suite(
            bars([100]).with_columns(pl.lit(LOCKED_HISTORICAL_START_US).alias("available_us")),
            pl.DataFrame(), replace(config, end_us=LOCKED_HISTORICAL_START_US),
        )
    assert len(seen) == 15
