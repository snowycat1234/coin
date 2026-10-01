"""Small synthetic evidence, no model fit, market history or acceptance writes."""

import copy
import importlib.util
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from quant.alpha_rules_v2 import r2_gates
from quant.backtest import BacktestConfig
from quant.execution_contract import ExecutionContractV2
from quant.features_v2 import feature_schema_v2
from quant.operations import date_us
from quant.predictor import contracts_from_execution, make_predictor_manifest

SPEC = importlib.util.spec_from_file_location(
    "audit_nonlinear_v2", Path(__file__).parents[1] / "scripts/audit_nonlinear_v2.py"
)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def write_json(path, value):
    path.write_text(json.dumps(value, allow_nan=False))


def financial_fixture(tmp_path):
    """A purchase, a rejected attempt, then a full close: one financial cycle."""
    start, minute, day = date_us("2024-01-01"), audit.MINUTE_US, audit.DAY_US
    first, second = start + minute, start + day + minute
    prices = audit.MinutePrices(
        pl.DataFrame(
            {
                "symbol": ["BTCUSDT"] * 6,
                "open_us": [
                    first - minute,
                    first,
                    start + day - minute,
                    second - minute,
                    second,
                    start + 2 * day - minute,
                ],
                "open": [100.0, 100.0, 100.0, 105.0, 105.0, 105.0],
                "close": [100.0, 100.0, 100.0, 105.0, 105.0, 105.0],
                "quote_volume": [1_000_000.0] * 6,
            }
        )
    )
    config = asdict(BacktestConfig(start_us=start, end_us=date_us("2026-03-01")))
    cash, trades, daily, orders = 10000.0, [], [], []
    fees = []
    for index, (now, mid, side) in enumerate(((first, 100.0, "buy"), (second, 105.0, "sell"))):
        sign = 1 if side == "buy" else -1
        fill = mid * (1 + sign * 0.0005)
        fee, cost = fill * 0.001, abs(fill - mid)
        cash -= sign * fill + fee
        nav = cash + (mid if side == "buy" else 0.0)
        fees.append(fee)
        trade = {
            "execution_us": now + 1,
            "signal_us": now - minute,
            "capacity_open_us": now - minute,
            "symbol": "BTCUSDT",
            "side": side,
            "quantity": 1.0,
            "mid_price": mid,
            "fill_price": fill,
            "notional": fill,
            "fee": fee,
            "execution_cost": cost,
            "cash_after": cash,
            "nav_after": nav,
            "asset_weight_after": mid / nav if sign == 1 else 0.0,
            "gross_weight_after": mid / nav if sign == 1 else 0.0,
            "capacity": 1000.0,
        }
        trades.append(trade)
        orders.append(
            {
                "open_us": now,
                "signal_us": now - minute,
                "symbol": "BTCUSDT",
                "side": side,
                "filled_notional": fill,
                "status": "filled",
            }
        )
        prior_nav = 10000.0 if index == 0 else daily[-1]["nav"]
        daily.append(
            {
                "date": date(2024, 1, index + 1),
                "nav": nav,
                "return": nav / prior_nav - 1,
                "cash": cash,
                "fees": fee,
                "execution_costs": cost,
                "turnover": fill / prior_nav,
                "gross_weight": mid / nav if sign == 1 else 0.0,
                "stale_prices": False,
                "stale_exposure": False,
            }
        )
    orders.insert(
        1,
        {
            "open_us": first + minute,
            "signal_us": first - minute,
            "symbol": "BTCUSDT",
            "side": "buy",
            "filled_notional": 0.0,
            "status": "capacity_zero",
        },
    )
    values = np.array([item["nav"] for item in daily])
    returns = values / np.r_[10000.0, values[:-1]] - 1
    volatility = float(np.std(returns, ddof=1) * np.sqrt(365))
    full = np.r_[10000.0, values]
    summary = {
        "days": 2,
        "initial_nav": 10000.0,
        "final_nav": float(values[-1]),
        "total_return": float(values[-1] / 10000.0 - 1),
        "annual_return": float((values[-1] / 10000.0) ** (365 / 2) - 1),
        "annual_volatility": volatility,
        "sharpe": float(np.mean(returns) * 365 / volatility),
        "max_drawdown": float(-np.min(full / np.maximum.accumulate(full) - 1)),
        "fees": sum(fees),
        "execution_costs": sum(item["execution_costs"] for item in daily),
        "turnover": sum(item["turnover"] for item in daily),
        "trade_count": 2,
        "round_trip_count": 1,
        "valuation_gap_days": 0,
        "exposed_valuation_gap_days": 0,
        "daily_risk_observable": True,
        "gross_pnl_before_costs": 5.0,
        "start_utc": "2024-01-01T00:00:00+00:00",
        "end_utc": "2026-03-01T00:00:00+00:00",
        "execution_contract_version": "execution_v2",
        "execution_contract_sha256": ExecutionContractV2().digest(),
        "canonical_latency": True,
        "open_positions": {"BTCUSDT": 0.0},
    }
    frames = {
        "daily_nav": pl.DataFrame(daily),
        "trades": pl.DataFrame(trades),
        "orders": pl.DataFrame(orders),
        "round_trips": pl.DataFrame(
            [
                {
                    "symbol": "BTCUSDT",
                    "entry_us": first + 1,
                    "exit_us": second + 1,
                    "pnl": cash - 10000.0,
                    "fees": sum(fees),
                }
            ]
        ),
    }
    for label, frame in frames.items():
        frame.write_parquet(tmp_path / f"base_{label}.parquet")
    write_json(tmp_path / "base.json", {"config": config, "summary": summary})
    return summary, prices


def test_synthetic_financial_cycle_and_costs_are_independently_reconciled(tmp_path):
    summary, prices = financial_fixture(tmp_path)
    result = audit.audit_financial_report(
        tmp_path, "base", summary, "base", prices, expected_days=2
    )
    assert result["closed_cycles"] == 1 and result["actual_trade_count"] == 2
    assert result["gross_pnl_before_costs"] == pytest.approx(5.0)
    assert result["net_pnl"] < 5.0


@pytest.mark.parametrize("mutation", ["fees", "cycle", "future_capacity", "unfilled", "days"])
def test_financial_tampering_is_rejected_even_if_json_claims_match(tmp_path, mutation):
    summary, prices = financial_fixture(tmp_path)
    if mutation == "fees":
        summary["fees"] += 1.0
        payload = audit.read_json(tmp_path / "base.json")
        payload["summary"] = summary
        write_json(tmp_path / "base.json", payload)
    elif mutation == "cycle":
        file = tmp_path / "base_round_trips.parquet"
        pl.read_parquet(file).with_columns(pl.lit(123.0).alias("pnl")).write_parquet(file)
    elif mutation == "future_capacity":
        file = tmp_path / "base_trades.parquet"
        pl.read_parquet(file).with_columns(
            (pl.col("capacity_open_us") + audit.MINUTE_US).alias("capacity_open_us")
        ).write_parquet(file)
    elif mutation == "unfilled":
        file = tmp_path / "base_orders.parquet"
        pl.read_parquet(file).with_columns(
            pl.when(pl.col("status") == "capacity_zero")
            .then(1.0)
            .otherwise(pl.col("filled_notional"))
            .alias("filled_notional")
        ).write_parquet(file)
    else:
        file = tmp_path / "base_daily_nav.parquet"
        pl.read_parquet(file).with_columns(pl.lit(date(2024, 1, 2)).alias("date")).write_parquet(
            file
        )
    with pytest.raises(audit.AuditRejected):
        audit.audit_financial_report(tmp_path, "base", summary, "base", prices, expected_days=2)


def r2_fixture():
    metric = {
        "gross_pnl_before_costs": -1.0,
        "fees": 1.0,
        "total_return": -0.01,
        "sharpe": -0.1,
        "max_drawdown": 0.1,
        "daily_risk_observable": True,
        "round_trip_count": 0,
    }
    baseline = {name: copy.deepcopy(metric) for name in audit.BASELINES}
    report = {
        "status": "STOP_v2",
        "final_fit_count": 0,
        "frozen_candidate": None,
        "baselines": baseline,
        "results": {},
    }
    for name in audit.CONFIG_IDS:
        metrics = {scenario: copy.deepcopy(metric) for scenario in audit.SCENARIOS}
        report["results"][name] = {
            "metrics": metrics,
            "R2": r2_gates(
                metrics["base"],
                {key: metrics[key] for key in ("fee_x2", "slippage_x2")},
                {key: baseline[key] for key in ("B2", "B3", "B4")},
            ),
        }
    return {"status": "STOP_v2", "final_fit_count": 0}, report


def test_failed_metrics_stop_without_final_fit_and_false_gate_claim_is_rejected():
    state, report = r2_fixture()
    assert audit.audit_r2_summary(state, report)["unique_selected_configuration"] is None
    report["results"]["LGB_A"]["R2"]["passed"] = True
    with pytest.raises(audit.AuditRejected, match="R2 recomputation"):
        audit.audit_r2_summary(state, report)


def test_actual_cycle_minimum_and_missing_stress_cannot_be_waived():
    state, report = r2_fixture()
    report["results"]["LGB_A"]["metrics"].pop("fee_x2")
    with pytest.raises(audit.AuditRejected, match="Both cost stress"):
        audit.audit_r2_summary(state, report)
    state, report = r2_fixture()
    report["final_fit_count"] = state["final_fit_count"] = 1
    with pytest.raises(audit.AuditRejected, match="one final fit"):
        audit.audit_r2_summary(state, report)


def test_unique_winner_uses_sharpe_then_fees_then_id_and_not_boolean_claim():
    state, report = r2_fixture()
    for name in ("LGB_A", "LGB_B", "XGB_C"):
        for scenario in audit.SCENARIOS:
            report["results"][name]["metrics"][scenario].update(
                gross_pnl_before_costs=200.0,
                fees=20.0 if name != "XGB_C" else 30.0,
                total_return=0.02,
                sharpe=0.8,
                round_trip_count=30,
            )
        item = report["results"][name]
        item["R2"] = r2_gates(
            item["metrics"]["base"],
            {key: item["metrics"][key] for key in ("fee_x2", "slippage_x2")},
            {key: report["baselines"][key] for key in ("B2", "B3", "B4")},
        )
    state.update(status="ALPHA_CANDIDATE", final_fit_count=1)
    report.update(
        status="ALPHA_CANDIDATE", final_fit_count=1, frozen_candidate={"configuration": "LGB_A"}
    )
    assert audit.audit_r2_summary(state, report)["unique_selected_configuration"] == "LGB_A"
    report["frozen_candidate"]["configuration"] = "LGB_B"
    with pytest.raises(audit.AuditRejected, match="unique selection"):
        audit.audit_r2_summary(state, report)


def test_artifact_hashes_or_path_escape_and_orphan_outputs_are_rejected(tmp_path):
    member = tmp_path / "model.txt"
    member.write_text("synthetic fixture, not a real model")
    hashes = {"model.txt": audit.digest(member)}
    audit.audit_hashes(tmp_path, hashes, exact=True)
    member.write_text("changed synthetic bytes")
    with pytest.raises(audit.AuditRejected, match="SHA256"):
        audit.audit_hashes(tmp_path, hashes)
    with pytest.raises(audit.AuditRejected, match="escaped"):
        audit.audit_hashes(tmp_path, {"../unrelated.txt": "0" * 64})
    hashes["model.txt"] = audit.digest(member)
    (tmp_path / "unregistered.txt").write_text("extra attempt")
    with pytest.raises(audit.AuditRejected, match="Unregistered"):
        audit.audit_hashes(tmp_path, hashes, exact=True)


def test_duplicate_json_and_nonfinite_values_fail_closed(tmp_path):
    file = tmp_path / "result.json"
    file.write_text('{"passed":false,"passed":true}')
    with pytest.raises(audit.AuditRejected, match="Duplicate"):
        audit.read_json(file)
    file.write_text('{"sharpe":NaN}')
    with pytest.raises(audit.AuditRejected, match="Nonfinite"):
        audit.read_json(file)


def test_fixed_54_commits_and_purge_calendar_cannot_be_shortened_or_duplicated():
    report = {"fit_count": 54, "folds": audit.expected_folds(), "cv_days": 790}
    state = {
        "fit_count": 54,
        "inflight_fit": None,
        "completed_fits": {
            f"{name}:fold{index}": {} for name in audit.CONFIG_IDS for index in range(9)
        },
        "audit": [{"event": "registered_before_any_fit", "created_us": 1}],
    }
    audit.audit_fit_budget(state, report)
    assert report["folds"][-1]["test_end"] == "2026-03-01"
    state["completed_fits"].pop("LGB_A:fold0")
    with pytest.raises(audit.AuditRejected, match="54 independently"):
        audit.audit_fit_budget(state, report)
    state["completed_fits"]["LGB_A:fold0"] = {}
    report["folds"][0]["train_start"] = "2022-02-01"
    with pytest.raises(audit.AuditRejected, match="Nine folds"):
        audit.audit_fit_budget(state, report)


def test_exact_label_embargo_boundary_is_excluded():
    cutoff = date_us("2024-01-01") - audit.HOUR_US
    frame = pl.DataFrame(
        {
            "available_us": [date_us("2023-12-30")] * 3,
            "label_valid": [True] * 3,
            "label_end_us": [cutoff - 1, cutoff, cutoff + 1],
            "symbol": ["BTCUSDT"] * 3,
            "gross_return": [0.01] * 3,
            **{name: [0.0] * 3 for name in audit.FEATURE_NAMES_V2},
        }
    )
    result = audit._training_rows(frame, audit.expected_folds()[0])
    assert result["label_end_us"].to_list() == [cutoff - 1]


def fit_fixture(tmp_path):
    # Explicit ENGINEERING bytes: structural audit only, no model loader or fit.
    folder = tmp_path / "LGB_A/fold0"
    folder.mkdir(parents=True)
    times = date_us("2022-01-01") + np.arange(5000) * audit.HOUR_US
    train = pl.DataFrame(
        {
            "available_us": times,
            "symbol": ["BTCUSDT"] * 5000,
            "label_end_us": times + 4 * audit.HOUR_US,
            "gross_return": [0.01] * 5000,
            **{name: [0.0] * 5000 for name in audit.FEATURE_NAMES_V2},
        }
    )
    test = train.head(20).with_columns(
        pl.Series("available_us", date_us("2024-01-01") + np.arange(20) * audit.HOUR_US)
    )
    blob = b"ENGINEERING_ONLY_NOT_A_NATIVE_MODEL"
    (folder / "model.txt").write_bytes(blob)
    cost, risk = contracts_from_execution(ExecutionContractV2())
    columns = ["available_us", "symbol", *audit.FEATURE_NAMES_V2, "gross_return", "label_end_us"]
    manifest = make_predictor_manifest(
        blob,
        model_type="lightgbm",
        feature_schema=feature_schema_v2(),
        execution_contract=ExecutionContractV2(),
        cost_contract=cost,
        risk_contract=risk,
        training_cutoff="2024-01-01T00:00:00Z",
        training_last_available_us=int(times[-1]),
        training_last_label_end_us=int(times[-1] + 4 * audit.HOUR_US),
        training_data_sha256=audit.frame_digest(train.select(columns)),
    )
    write_json(folder / "manifest.json", manifest)
    test.select("symbol", "available_us").with_columns(
        pl.lit(0.01).alias("expected_return")
    ).write_parquet(folder / "predictions.parquet")
    receipt = {
        "fold": audit.expected_folds()[0],
        "rows": 5000,
        "test_rows": 20,
        "max_train_label_end_us": int(train["label_end_us"].max()),
        "native_parity_max_error": 0.0,
        "training_sha256": manifest["training_data_sha256"],
        "artifacts": {
            str(path.relative_to(tmp_path)): audit.digest(path) for path in folder.iterdir()
        },
    }
    return receipt, {"id": "LGB_A", "model_type": "lightgbm"}, train, test


def test_synthetic_fit_provenance_has_no_native_or_alpha_qualification(tmp_path):
    receipt, config, train, test = fit_fixture(tmp_path)
    result = audit.audit_fit(
        tmp_path, receipt, config, audit.expected_folds()[0], train, test, native_parity=False
    )
    assert result["native_vectors_verified"] == 0 and result["rows"] == 5000
    assert result["native_max_error"] is None


@pytest.mark.parametrize(
    "mutation", ["label_boundary", "training_values", "model_bytes", "future_keys"]
)
def test_committed_fit_actual_matrix_purge_and_artifact_tampering_are_rejected(tmp_path, mutation):
    receipt, config, train, test = fit_fixture(tmp_path)
    if mutation == "label_boundary":
        train = train.with_columns(
            pl.lit(date_us("2024-01-01") - audit.HOUR_US).alias("label_end_us")
        )
    elif mutation == "training_values":
        train = train.with_columns(pl.lit(123.0).alias(audit.FEATURE_NAMES_V2[0]))
    elif mutation == "model_bytes":
        (tmp_path / "LGB_A/fold0/model.txt").write_text("changed bytes")
    else:
        file = tmp_path / "LGB_A/fold0/predictions.parquet"
        pl.read_parquet(file).with_columns(
            (pl.col("available_us") + audit.HOUR_US).alias("available_us")
        ).write_parquet(file)
        receipt["artifacts"][str(file.relative_to(tmp_path))] = audit.digest(file)
    with pytest.raises(audit.AuditRejected):
        audit.audit_fit(
            tmp_path, receipt, config, audit.expected_folds()[0], train, test, native_parity=False
        )


def resource_fixture():
    memory = {
        "aggregate_cgroup": "/sys/fs/cgroup/coin-quant.slice",
        "ram_limit_bytes": 4_999_999_488,
        "ram_current_bytes": 1_000_000,
        "ram_peak_bytes": 2_000_000,
        "swap_bytes": 0,
        "gpu_used": False,
        "memory_events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0",
    }
    return {
        "resource_start": copy.deepcopy(memory),
        "resources": copy.deepcopy(memory),
        "disk": {
            "hard_limit_bytes": 40_000_000_000,
            "total_bytes": 8_000_000_000,
            "project_bytes": 2_000_000_000,
            "wsl_vhd_bytes": 6_000_000_000,
            "reserved_bytes": 0,
            "d_free_bytes": 100_000_000_000,
            "status": "OK",
        },
    }


@pytest.mark.parametrize("mutation", ["oom", "ram", "swap", "disk", "missing_start"])
def test_resource_snapshot_is_not_accepted_without_real_limits_and_continuity(mutation):
    report = resource_fixture()
    audit.audit_resources(report)
    if mutation == "oom":
        report["resources"]["memory_events"] = report["resources"]["memory_events"].replace(
            "oom 0", "oom 1"
        )
    elif mutation == "ram":
        report["resources"]["ram_peak_bytes"] = 5_000_000_001
    elif mutation == "swap":
        report["resources"]["swap_bytes"] = 1
    elif mutation == "disk":
        report["disk"].update(total_bytes=36_000_000_000, project_bytes=30_000_000_000)
    else:
        report.pop("resource_start")
    with pytest.raises(audit.AuditRejected):
        audit.audit_resources(report)


def test_actual_audit_refuses_synthetic_root_before_any_data_or_acceptance_write(tmp_path):
    with pytest.raises(audit.AuditRejected, match="canonical D project"):
        audit.audit_results(tmp_path)
    assert not list(tmp_path.iterdir())
