"""Synthetic report engineering only; no market, account replay, or economic evidence.

These fixtures exercise the report schema and its treatment of an incomplete
calendar.  The numbers are invented, and the zero audit errors below are test
stubs, never receipts from an independently audited trading wallet.
"""
from importlib.util import find_spec
import json
from pathlib import Path

import numpy as np
import polars as pl

from modules.expert_aggregation.common import DAY, atomic, read
from modules.expert_aggregation.report import build


SYNTHETIC = "SYNTHETIC_ENGINEERING_FIXTURE_NOT_MARKET_OR_WALLET_EVIDENCE"


def _fixture(tmp_path, *, incomplete):
    """Create the 28 registered combinations without simulating any wallet."""
    source_repo = Path(__file__).resolve().parents[1]
    protocol = read(source_repo / "modules/expert_aggregation/protocol.json")
    protocol = {**protocol, "fixture_role": SYNTHETIC}
    repo = tmp_path / "synthetic-repo"
    state = tmp_path / "synthetic-state"
    atomic(repo / "modules/expert_aggregation/protocol.json", protocol)
    atomic(state / "RUN_BINDING.json", {"fixture_role": SYNTHETIC, "real_accounts_executed": 0})
    atomic(state / "cache/INPUT_BINDING.json", {"fixture_role": SYNTHETIC, "actual_market_inputs": False})
    atomic(state / "PATHS.json", {"fixture_role": SYNTHETIC, "diagnostics": []})

    # 366 closes delimit the complete 365-day evaluation; beta has a finite,
    # nonzero market denominator.  This is an invented oscillating price path.
    market_return = 0.002 * np.sin(np.arange(365, dtype=np.float64) / 13)
    prices = np.r_[100.0, 100 * np.cumprod(1 + market_return)]
    pl.DataFrame({
        "close_us": protocol["evaluation_start_us"] + np.arange(366, dtype=np.int64) * DAY,
        "close": prices,
    }).write_parquet(state / "cache/daily.parquet")

    receipts = []
    for scenario in protocol["scenarios"]:
        algorithms = (protocol["dynamic_wallets"] + protocol["base_controls"]
                      if scenario == "BASE27" else protocol["pressure_wallets"])
        for unit in protocol["units"]:
            for algorithm in algorithms:
                key = (algorithm, unit, scenario)
                partial = incomplete and key == ("STATIC_TRAIN_FROZEN", "RAW_AS_FRACTION", "BASE27")
                days = 45 if partial else 365
                dynamic = algorithm in protocol["dynamic_wallets"]
                cash = algorithm == "CASH"
                daily_return = (np.zeros(365) if cash else
                                0.0005 + 0.03 * market_return if dynamic else
                                0.00005 + 0.10 * market_return)
                nav = (10000 * np.cumprod(1 + daily_return))[:days]
                directory = state / "accounts" / ("synthetic-" + "-".join(key))
                directory.mkdir(parents=True)
                pl.DataFrame({
                    "day_end_us": protocol["evaluation_start_us"] + np.arange(1, days + 1, dtype=np.int64) * DAY,
                    "nav": nav,
                }).write_parquet(directory / "daily_nav.parquet")
                full_nav = np.r_[10000.0, nav]
                mdd = float(np.max(1 - full_nav / np.maximum.accumulate(full_nav)))
                net = float(nav[-1] - 10000)
                fees, execution, funding = ((0.0, 0.0, 0.0) if cash else (5.5, 8.0, -1.0))
                gross = net + fees + execution - funding
                long = dict(gross=gross, fees=fees, execution_cost=execution,
                            funding=funding, net_contribution=net)
                short = dict(gross=0.0, fees=0.0, execution_cost=0.0,
                             funding=0.0, net_contribution=0.0)
                summary = dict(
                    fixture_role=SYNTHETIC,
                    completion="SYNTHETIC_PREFIX_NOT_EVALUABLE" if partial else "SYNTHETIC_COMPLETE_SCHEMA",
                    completed_minutes=days * 1440,
                    required_minutes=525600,
                    terminal_cash_realized=not partial,
                    NAV=float(nav[-1]), net_PnL=net,
                    gross_PnL_same_quantities=gross,
                    minute_max_drawdown=None if partial else mdd,
                    all_observation_max_drawdown=mdd,
                    daily_metrics=None if partial else {
                        "annual_volatility": float(np.std(daily_return, ddof=1) * np.sqrt(365)),
                    },
                    realized_exposure=None if partial else {
                        "minute_mean_gross_weight": 0.0 if cash else 0.03 if dynamic else 0.10,
                        "minute_mean_net_signed_weight": 0.0 if cash else 0.03 if dynamic else 0.10,
                    },
                    fees_USDT=fees, execution_cost_USDT=execution,
                    funding_USDT=funding,
                    gross_fill_turnover_USDT=0.0 if cash else 10000.0,
                    liquidation_count=0, risk_reduction_signal_count=0,
                    long_short_marked_contribution={"LONG": long, "SHORT": short},
                    months=[], spread_cost_USDT=execution / 2,
                    slippage_cost_USDT=execution / 2,
                    funding_original_events=0 if cash else 1095,
                    funding_observed_events=0 if cash else days * 3,
                )
                # Real save_case omits realized_exposure on partial calendars.
                if partial:
                    summary.pop("realized_exposure")
                receipts.append(dict(
                    task=dict(id="synthetic-" + "-".join(key), algorithm=algorithm,
                              unit=unit, scenario=scenario, fixture_role=SYNTHETIC),
                    directory=str(directory), saved={"summary": summary, "artifacts": {}},
                    independent={"fixture_role": SYNTHETIC,
                                 "maximum_NAV_error_USDT": 0.0,
                                 "maximum_wallet_error_USDT": 0.0},
                    native_complete=not partial, elapsed_seconds=0.0,
                ))
    assert len(receipts) == protocol["budget"]["round_1_native_accounts"] == 28
    return state, repo, receipts


def test_incomplete_static_prefix_is_never_a_full_calendar_comparator(tmp_path):
    # The otherwise-positive control fixture is deliberate: an incomplete pair
    # must fail because of missing evidence, rather than incidental poor PnL.
    complete_state, repo, complete_receipts = _fixture(tmp_path / "complete", incomplete=False)
    positive = build(complete_state, repo, complete_receipts)
    assert positive["classification"] == "DYNAMIC_CAPTURE_PRELIMINARY"
    assert all(g["passes_registered_gate"] for g in positive["gates"])

    state, repo, receipts = _fixture(tmp_path / "incomplete", incomplete=True)
    result = build(state, repo, receipts)
    assert result["classification"] == "INSUFFICIENT_EVIDENCE"
    assert all(not g["passes_registered_gate"] for g in result["gates"])
    for gate in result["gates"]:
        assert any("incomplete comparison vs STATIC_TRAIN_FROZEN" in why
                   for why in gate["failed_conditions"])
    pairs = [c for c in result["comparisons"] if
             (c["control"], c["unit"], c["scenario"]) ==
             ("STATIC_TRAIN_FROZEN", "RAW_AS_FRACTION", "BASE27")]
    assert {c["candidate"] for c in pairs} == {"HEDGE", "FIXED_SHARE"}
    assert all(c["net_delta_USDT"] is None for c in pairs)
    assert all(c["comparison_status"] == "N/E_INCOMPLETE_CALENDAR_OR_TERMINAL" for c in pairs)
    assert all("quarter_delta_USDT" not in c and "paired_mean_daily_excess_ci_95" not in c for c in pairs)

    row = next(r for r in result["accounts"] if
               (r["algorithm"], r["unit"], r["scenario"]) ==
               ("STATIC_TRAIN_FROZEN", "RAW_AS_FRACTION", "BASE27"))
    assert not row["complete"] and not row["terminal_cash"]
    assert row["full_calendar_days"] == 45 and row["completed_minutes"] < row["required_minutes"]
    assert row["BTC_beta"] is None and row["daily_volatility"] is None
    assert row["minute_MDD"] is None and row["realized_mean_gross"] is None
    assert row["net_PnL_USDT"] > 0  # Its profitable prefix is retained, not used as a full-period return.

    delivery = state / "delivery"
    serialized = json.loads((delivery / "RESULTS.json").read_text())
    assert serialized["classification"] == "INSUFFICIENT_EVIDENCE"
    assert serialized["run_binding"]["fixture_role"] == SYNTHETIC
    assert (delivery / "RESULTS.csv").is_file() and (delivery / "REPORT.md").is_file()
    if find_spec("matplotlib") is not None:
        assert (delivery / "NAV.png").stat().st_size > 0
    assert (delivery / "DELIVERY_INDEX.json").is_file()
