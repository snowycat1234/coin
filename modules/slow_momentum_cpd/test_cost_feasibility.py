"""Financial counterexamples; no training or native wallet runs."""
from decimal import Decimal as D

import numpy as np
import pytest

from .cost_feasibility import arithmetic, FEE, SPREAD, SLIP


def test_constant_target_rebalances_price_drift_and_pays_exit():
    summary, daily = arithmetic([[.1], [.1]], [[.1], [0]])
    assert summary["drift_trade_turnover"] == pytest.approx(.21)
    assert summary["descriptive_target_turnover"] == pytest.approx(.2)
    assert daily[1]["drift_trade_turnover"] == pytest.approx(.01)


def test_ineligible_exit_charges_old_holding_and_cash_nan_is_safe():
    s, daily = arithmetic([[.1], [0]], [[.1], [np.nan]])
    assert s["drift_trade_turnover"] == pytest.approx(.21)
    assert daily[1]["drift_trade_turnover"] == pytest.approx(.11)
    assert s["terminal_cost"] == 0


def test_crossing_zero_charges_full_trade():
    s, daily = arithmetic([[.1], [-.1]], [[0], [0]])
    assert daily[1]["drift_trade_turnover"] == pytest.approx(.2)
    assert s["drift_trade_turnover"] == pytest.approx(.4)


def test_terminal_after_last_realized_return_and_fee_on_adverse_fill():
    s, _ = arithmetic([[.1]], [[.1]])
    expected_fee = D('.00055') * (D('.1') * D('1.0008') + D('.11') * D('.9992'))
    expected_exit = D('.11') * (D('.0008') + D('.00055') * D('.9992'))
    assert s["fee"] == pytest.approx(float(expected_fee))
    assert s["terminal_cost"] == pytest.approx(float(expected_exit))
    assert s["fixed_cost_total"] == pytest.approx(float(expected_fee + D('.21') * D('.0008')))


def test_missing_held_return_is_invalid():
    with pytest.raises(ValueError, match="held return"):
        arithmetic([[.1]], [[np.nan]])
    with pytest.raises(ValueError, match="held return"):
        arithmetic([[.1]], [[-1]])


def test_ensemble_before_turnover_is_not_mean_seed_cost():
    a, _ = arithmetic([[.1]], [[0]])
    b, _ = arithmetic([[-.1]], [[0]])
    ensemble, _ = arithmetic([[0]], [[0]])
    assert ensemble["fixed_cost_total"] == 0
    assert (a["fixed_cost_total"] + b["fixed_cost_total"]) / 2 > 0


def test_flat_cash_break_even_undefined_negative_gross_signed():
    cash, _ = arithmetic([[0]], [[np.nan]])
    assert cash["break_even_nominal_per_side_bps"] is None
    assert cash["break_even_status"] == "UNDEFINED_ZERO_TURNOVER"
    losing, _ = arithmetic([[.1]], [[-.1]])
    assert losing["break_even_nominal_per_side_bps"] < 0
    assert losing["cost_to_positive_gross_ratio"] is None


def test_independent_blocks_have_paid_entries_and_exits():
    a, _ = arithmetic([[.1]], [[0]])
    b, _ = arithmetic([[.1]], [[0]])
    bridged, _ = arithmetic([[.1], [.1]], [[0], [0]])
    assert a["fixed_cost_total"] + b["fixed_cost_total"] == pytest.approx(2 * bridged["fixed_cost_total"])


def test_short_fee_cross_term_and_signed_trade_conservation():
    s, _ = arithmetic([[-.1], [.07], [-.03]], [[.1], [-.2], [.5]])
    assert s["fee"] == pytest.approx(FEE * s["drift_trade_turnover"] - FEE * (SPREAD + SLIP) * s["gross_price_proxy"])
