"""Actual first-fill hold clocks are distinct from financial accounting cycles."""

import pytest

from quant.execution_parity import cross_engine_parity, hold_repair_case


@pytest.mark.parametrize("name", ["ordinary", "late_partial", "dust_reentry", "risk_reduction",
                                  "risk_clear_reentry"])
def test_actual_hold_repair_cross_engine_and_restart(name):
    result = hold_repair_case(name)
    assert result["pass"] and result["restart_verified"] and result["fills"] > 0
    if name == "dust_reentry":
        assert result["holding_anchor_ms"] > result["financial_cycle_entry_ms"]
        assert result["round_trip_count"] == 1
    elif name == "risk_reduction":
        assert result["first_sell_ms"] - result["first_buy_ms"] == 60 * 60_000
    elif name == "risk_clear_reentry":
        assert result["holding_anchor_ms"] > result["first_buy_ms"]
        assert result["round_trip_count"] == 2
    else:
        assert result["first_sell_ms"] - result["first_buy_ms"] >= 120 * 60_000


@pytest.mark.parametrize("partial", [False, True])
def test_no_hold_reference_path_preserves_execution_parity(partial):
    assert cross_engine_parity(partial=partial)["pass"]
