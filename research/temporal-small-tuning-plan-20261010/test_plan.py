"""Readiness and chronology checks; no model, optimizer, or economic rollout."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location("audit_plan", ROOT / "AUDIT_AND_PLAN.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def fixture():
    times = audit.clock("2024-01-01") + np.arange(5, dtype=np.int64) * audit.DAY
    data = dict(
        decision_us=times,
        episode_id=np.zeros(5, dtype=int),
        start_execution_us=times + 60000001,
        end_execution_us=times + audit.DAY + 60000001,
        past_returns30=np.zeros((5, 30, 5)),
        expert_eligible=np.ones((5, 3), dtype=bool),
        expert_asset_eligible=np.ones((5, 3, 5), dtype=bool),
    )
    short = dict(
        expert_eligible=np.ones((5, 1), dtype=bool),
        expert_asset_eligible=np.ones((5, 1, 5), dtype=bool),
    )
    calendar = np.arange(times[0] - 63 * audit.DAY, times[-1] + audit.DAY, audit.DAY)
    features = dict(
        completed_day_available_us=calendar,
        close_observed_mask=np.ones((len(calendar), 5), dtype=bool),
        feature_observed_mask=np.ones((len(calendar), 5, 24), dtype=bool),
    )
    return data, short, features


def test_maturity_and_terminal_do_not_count_as_active_dates():
    data, short, features = fixture()
    cutoff = audit.clock("2024-01-06")
    result = audit.eligible_prefix(data, short, features, cutoff)
    assert result["decision_rows"] == 5
    assert result["actual_distinct_eligible_active_training_dates"] == 4
    assert result["paid_close_rows"] == 1
    with pytest.raises(ValueError, match=">=600"):
        audit.require_training_dates(result)
    data["end_execution_us"][3] = cutoff
    with pytest.raises(ValueError, match="strictly before"):
        audit.eligible_prefix(data, short, features, cutoff)


def test_missing_calendar_cannot_be_spliced_and_masks_reduce_eligibility():
    data, short, features = fixture()
    features["close_observed_mask"][64] = False
    result = audit.eligible_prefix(data, short, features, audit.clock("2024-01-06"))
    assert result["actual_distinct_eligible_active_training_dates"] == 3
    assert result["all64_steps_all5_assets_observed_windows"] == 1
    data["decision_us"] = data["decision_us"].copy()
    data["decision_us"][2] += audit.DAY
    with pytest.raises(ValueError, match="Never splice"):
        audit.eligible_prefix(data, short, features, audit.clock("2024-01-06"))


def test_published_plan_has_six_bounded_source_verified_tasks():
    plan = json.loads((ROOT / "PLAN.json").read_text())
    assert len(plan["actual_fit_tasks"]) == plan["planned_initial_fits"] == 6
    assert {r["eligible_dates"] for r in plan["actual_fit_tasks"]} == {653, 744}
    assert plan["original_training_packet"]["actual_distinct_eligible_active_training_dates"] == 773
    assert plan["original_training_packet"]["decision_rows"] == 778
    assert plan["original_training_packet"]["unique_prefix_normalization_feature_rows"] == 907
    assert plan["common"]["max_completed_full_path_updates"] == 1024
    assert plan["source_coverage_audit"]["first600_active_dates"] == 600
    assert plan["reserved_final"]["accepted_monthly_source_inventory"]["monthly_records"] == 45
    assert not plan["reserved_final"]["reserve_results_read"]
    assert not plan["reserved_final"]["reserve_market_returns_computed"]
    for name in ("performed_fits", "model_inferences", "economic_wallets", "provider_downloads"):
        assert plan[name] == 0
    for task in plan["actual_fit_tasks"]:
        audit.require_training_dates(
            dict(actual_distinct_eligible_active_training_dates=task["eligible_dates"])
        )
    assert len(plan["candidate_settings"]) == 3
    baseline = plan["candidate_settings"]["BASE_DATE_LR1E3"]
    low = plan["candidate_settings"]["LOW_LR3E4"]
    mixed = plan["candidate_settings"]["MIXED_WALLET_HALF"]
    assert baseline["lr"] == mixed["lr"] == 0.001
    assert baseline["wallet_equal_mix"] == low["wallet_equal_mix"] == 0.0
    assert low["lr"] == 0.0003
    assert mixed["wallet_equal_mix"] == 0.5
