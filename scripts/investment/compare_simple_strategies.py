"""Actual simple-strategy ledgers through the unchanged minute backtest engine.

An explicit proxy SCREENING comparison, not a V8 BBO execution gate or an alpha
qualification. Sources, signals and accounting are reused; no model is fitted.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
import polars as pl
from quant import disk, resources
from quant.paths import ROOT, STATE
from quant.backtest import BacktestConfig, run_backtest, MINUTE_US, DAY_US
from quant.execution_contract import ExecutionContractV2
from quant.research_fast.trade_flow_v2 import require

sys.path.insert(0, str(ROOT))
from scripts.research_v8 import benchmark_targets_v2 as benchmarks
from scripts.research_v8 import public_donchian_adapter as public_strategy
from scripts.investment import bulk_fixed_targets
from scripts.research_v8.registry import FIELDS, append_event
from scripts.research_v7.oracle_flow_ceiling import Progress

PROTOCOL = ROOT / "protocols/SIMPLE_STRATEGY_COMPARISON_V1.json"
SYMBOLS = ("BTCUSDT", "ETHUSDT")
STRATEGIES = ("CASH", "SPOT_BUY_AND_HOLD", "VOL_MANAGED_BUY_AND_HOLD", "FIXED_TREND", "FIXED_MEAN_REVERSION", public_strategy.STRATEGY_ID)
file_sha = benchmarks.file_sha
START, LOCKED = date(2025, 7, 1), date(2026, 3, 1)


def day_us(day):
    return int(datetime.combine(day, datetime.min.time(), UTC).timestamp()) * 1_000_000


def read_json(path):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT) and path.is_file() and path.stat().st_size < 2_000_000,
            "Explicit bounded project receipt required")
    return json.loads(path.read_text())


def save_json(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def allowed_source_path(record):
    """Reject unapproved dates/path before opening or hashing a market file."""
    require(record["symbol"] in SYMBOLS and record["month"] in ("2025-07", "2025-08", "2025-09", "2025-10", "2025-11"),
        "Only explicit accepted July-November Spot minutes; no locked IO")
    expected = (ROOT / "data/normalized/spot" / record["symbol"] / "1m" / (record["month"] + ".parquet")).resolve()
    require(Path(record["normalized_path"]).resolve() == expected and expected.is_relative_to(ROOT.resolve()),
        "Exact explicit original normalized source required")
    return expected


def minute_view(frame):
    """Keep official sealed minutes; mark invalid data, never interpolate/drop."""
    required = {"symbol", "open_us", "close_us", "available_us", "open", "high", "low", "close", "quote_volume", "valid_day"}
    require(required <= set(frame.columns), "Original normalized minute schema required")
    require(all(frame.schema[key] == pl.Int64 for key in ("open_us", "close_us", "available_us")), "Original integer timestamps")
    require(frame["symbol"].is_in(SYMBOLS).all() and frame.height == frame.unique(["symbol", "open_us"]).height, "Two symbols; no duplicate minutes")
    stamps = frame["open_us"].to_numpy()
    require(np.all((stamps >= day_us(START)) & (stamps < day_us(LOCKED)) & (stamps % MINUTE_US == 0)), "Development aligned minute source")
    valid = (pl.col("close_us") == pl.col("open_us") + MINUTE_US) & (pl.col("available_us") == pl.col("close_us")) & pl.col("valid_day")
    valid &= pl.all_horizontal([pl.col(key).is_finite() & (pl.col(key) > 0) for key in ("open", "high", "low", "close")])
    valid &= (pl.col("low") <= pl.min_horizontal("open", "close")) & (pl.col("high") >= pl.max_horizontal("open", "close"))
    valid &= pl.col("quote_volume").is_finite() & (pl.col("quote_volume") >= 0)
    return frame.select(sorted(required)).with_columns(valid.fill_null(False).alias("minute_valid")).with_columns(
        pl.when(pl.col("minute_valid")).then(None).otherwise(pl.lit("MISSING_OR_INVALID_COMPLETE_MINUTE_PRICE_SOURCE")).alias("missing_reason")).sort(["open_us", "symbol"])


def complete_fold(minutes, lower, start, end):
    expected = np.arange(lower, end, MINUTE_US, dtype=np.int64)
    return bool(minutes["minute_valid"].all() and all(np.array_equal(
        minutes.filter(pl.col("symbol") == symbol)["open_us"].to_numpy(), expected) for symbol in SYMBOLS))


def reference_daily_returns(minutes):
    """Fixed .3/.3 gross reference basket, not a recursively simulated VM book."""
    daily = minutes.with_columns((pl.col("open_us") // DAY_US).alias("day")).group_by(["symbol", "day"]).agg(
        pl.len().alias("rows"), pl.col("minute_valid").all().alias("valid"), pl.col("close").last().alias("close"),
        pl.col("available_us").max().alias("available_us")).sort(["symbol", "day"])
    returns = daily.with_columns((pl.col("close") / pl.col("close").shift(1).over("symbol") - 1).alias("ret"),
        pl.col("day").shift(1).over("symbol").alias("prior_day"),
        pl.col("valid").shift(1).over("symbol").alias("prior_valid"))
    returns = returns.filter((pl.col("rows") == 1440) & pl.col("valid") & pl.col("prior_valid")
        & (pl.col("day") - pl.col("prior_day") == 1) & pl.col("ret").is_finite())
    result = returns.group_by("day").agg(pl.len().alias("symbols"),
        (pl.col("ret").sum() * .3).alias("gross_exposure_return"), pl.col("available_us").max().alias("available_us"))
    return result.filter(pl.col("symbols") == 2).with_columns(((pl.col("day") + 1) * DAY_US).alias("day_end_us"))


def comparison_config(start, end, spread):
    require(spread in (2, 4, 8), "Fixed nominal30/32/36bp roundtrip scenarios only")
    return BacktestConfig(initial_cash=10_000., fee_bps=10., half_spread_bps=spread / 2, slippage_bps=4.,
        latency_minutes=1, start_us=int(start), end_us=int(end), max_weight=.3, max_gross=.6,
        target_annual_vol=.10, vol_window_days=30, min_vol_days=20, participation_rate=.001,
        max_order_wait_minutes=5, liquidate_at_end=True)


def account_inventory(result, minutes):
    """Independent balance/mark audit of actual fills, never another simulator."""
    cfg = result.config
    mark = minutes.filter((pl.col("open_us") >= cfg.start_us) & (pl.col("open_us") < cfg.end_us)).sort(["open_us", "symbol"])
    per = {symbol: mark.filter(pl.col("symbol") == symbol) for symbol in SYMBOLS}
    stamps = per[SYMBOLS[0]]["close_us"].to_numpy()
    require(all(np.array_equal(stamps, frame["close_us"].to_numpy()) for frame in per.values()), "Same complete marking calendar")
    fills = result.trades.sort("execution_us", maintain_order=True)
    execution = fills["execution_us"].to_numpy()
    direction = np.where(fills["side"].to_numpy() == "buy", 1., -1.)
    notional, fees, extra = (fills[name].to_numpy() for name in ("notional", "fee", "execution_cost"))
    cash_steps = cfg.initial_cash - np.cumsum(direction * notional + fees)
    require(np.allclose(cash_steps, fills["cash_after"].to_numpy(), rtol=0, atol=1e-7), "Cash ledger does not reconcile actual fills")
    counts = np.searchsorted(execution, stamps, side="right")
    def at_steps(values):
        return np.r_[0., np.cumsum(values)][counts]
    cash = cfg.initial_cash - at_steps(direction * notional + fees)
    gross_cash = cfg.initial_cash - at_steps(direction * fills["quantity"].to_numpy() * fills["mid_price"].to_numpy())
    nav, gross_nav = cash.copy(), gross_cash.copy()
    output = {"close_us": stamps, "cash": cash}
    symbol_notionals = []
    for symbol in SYMBOLS:
        is_symbol = fills["symbol"].to_numpy() == symbol
        quantity = at_steps(direction * fills["quantity"].to_numpy() * is_symbol)
        values = quantity * per[symbol]["close"].to_numpy()
        nav += values
        gross_nav += values
        output[symbol + "_quantity"] = quantity
        output[symbol + "_marked_notional"] = values
        symbol_notionals.append(values)
        require(abs(quantity[-1] - result.summary["open_positions"][symbol]) < 1e-8, "Terminal position ledger mismatch")
    require(np.allclose(gross_nav - at_steps(fees + extra), nav, rtol=0, atol=1e-6), "Same quantities gross-cost must equal net NAV")
    require(np.isfinite(nav).all() and np.all(cash >= -1e-7), "Missing mark or negative cash")
    output.update(nav=nav, gross_marked_nav_same_quantities=gross_nav, cumulative_fee=at_steps(fees), cumulative_execution_cost=at_steps(extra),
        gross_weight=np.sum(symbol_notionals, axis=0) / nav)
    frame = pl.DataFrame(output)
    daily = frame.filter(pl.col("close_us") % DAY_US == 0)
    require(np.allclose(daily["nav"].to_numpy(), result.daily_nav["nav"].to_numpy(), rtol=0, atol=1e-6), "UTC daily NAV differs from independent inventory")
    for fill in fills.iter_rows(named=True):
        require(fill["execution_us"] >= ExecutionContractV2().earliest_execution_us(fill["signal_us"]) + 1,
            "Fill precedes registered complete-minute latency")
        require(fill["capacity_open_us"] == fill["execution_us"] // MINUTE_US * MINUTE_US - MINUTE_US,
            "Capacity uses future/current rather than previous complete minute")
        require(abs(fill["fee"] - fill["notional"] * cfg.fee_rate) < 1e-8
            and abs(fill["execution_cost"] - fill["quantity"] * abs(fill["fill_price"] - fill["mid_price"])) < 1e-8,
            "Actual costs not charged exactly once")
        require(fill["notional"] <= fill["capacity"] + 1e-7 and fill["execution_us"] < cfg.end_us, "Capacity/period exceeded")
    require(abs(float(nav[-1]) - result.summary["final_nav"]) < 1e-6, "Terminal MTM missing from finalNAV")
    return frame


def write_ledger(directory, result, minutes):
    require(not directory.exists(), "New exclusive ledger; no overwrite")
    directory.mkdir()
    inventory = account_inventory(result, minutes)
    for name, frame in (("daily_nav", result.daily_nav), ("trades", result.trades), ("orders", result.orders),
                        ("round_trips", result.round_trips), ("minute_nav_inventory", inventory)):
        frame.write_parquet(directory / (name + ".parquet"), compression="zstd")
    save_json(directory / "config_and_summary.json", {"config": asdict(result.config), "summary": result.summary})
    summary = dict(result.summary)
    fee, execution_cost = summary["fees"], summary["execution_costs"]
    qty_net = summary["final_nav"] - result.config.initial_cash
    notionals = float(np.sum(result.trades["quantity"].to_numpy() * result.trades["mid_price"].to_numpy()))
    positive = np.maximum(result.daily_nav["nav"].to_numpy() - np.r_[10_000., result.daily_nav["nav"].to_numpy()[:-1]]
        + result.daily_nav["fees"].to_numpy() + result.daily_nav["execution_costs"].to_numpy(), 0)
    summary.update(net_cash_PnL=qty_net, gross_cash_PnL_same_quantities=qty_net + fee + execution_cost,
        max_observed_minute_MDD=float(-np.min(inventory["nav"].to_numpy() / np.maximum.accumulate(np.r_[result.config.initial_cash, inventory["nav"].to_numpy()])[1:] - 1)),
        spread_cost=execution_cost * result.config.half_spread_bps / (result.config.half_spread_bps + 4),
        slippage_cost=execution_cost * 4 / (result.config.half_spread_bps + 4),
        actual_two_sided_mid_notional=notionals,
        break_even_roundtrip_cost_bps=2 * (qty_net + fee + execution_cost) / notionals * 10_000 if notionals else None,
        max_minute_marked_gross_weight=float(inventory["gross_weight"].max()),
        minimum_marked_cash=float(inventory["cash"].min()),
        terminal_marked_notional=sum(float(inventory[symbol + "_marked_notional"][-1]) for symbol in SYMBOLS),
        terminal_positions_flat=all(value == 0 for value in summary["open_positions"].values()),
        max_minute_BTC_weight=float((inventory["BTCUSDT_marked_notional"] / inventory["nav"]).max()),
        max_minute_ETH_weight=float((inventory["ETHUSDT_marked_notional"] / inventory["nav"]).max()),
        top1_day_positive_gross_PnL_share=float(positive.max() / positive.sum()) if positive.sum() else None,
        evaluation_status="MINUTE_PROXY_SCREENING_MARKED_TERMINAL_RESIDUALS", real_BBO=False, capacity_proven=False,
        net_long_term_CAGR_proven=False, short_window_annualization_is_descriptive_only=True,
        same_quantity_gross_minus_cost_equals_net=True, candidate_qualification_allowed=False)
    return {"summary": summary, "directory": str(directory), "artifacts": {
        path.name: {"sha256": file_sha(path), "bytes": path.stat().st_size} for path in directory.iterdir() if path.is_file()}}


def verify_sources(spec):
    expected = spec["frozen_sources"]
    for path, digest in expected.items():
        require(file_sha(ROOT / path) == digest, "Frozen source changed: " + path)
    source = read_json(ROOT / spec["source_receipt"])
    require(file_sha(ROOT / spec["source_receipt"]) == spec["source_receipt_sha256"]
        and source["status"] == "PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_153D_CALENDAR", "Accepted original minute source receipt required")
    require(len(source["sources"]) == 10 and len({(record["symbol"], record["month"]) for record in source["sources"]}) == 10,
        "Exactly ten explicit symbol-months required")
    for record in source["sources"]:
        allowed_source_path(record)
    require(Path(sys.prefix).resolve() == Path(spec["environment"]["sys_prefix"]).resolve()
        and file_sha(ROOT / "environments/v8/uv.lock") == spec["environment"]["lock_sha256"], "Accepted clean native CPU environment")
    require(pl.thread_pool_size() <= 2, "At most2 Polars threads")
    return source


def research(spec, source, work, progress, report):
    windows, wanted = [], set()
    for fold in spec["folds"]:
        start, end = [day_us(date.fromisoformat(fold[key])) for key in ("test_start", "test_end_exclusive")]
        lower = start - 31 * DAY_US
        require(day_us(START) <= lower < start < end < day_us(LOCKED) and end - start == 7 * DAY_US, "Frozen development-only7day periods")
        cursor = datetime.fromtimestamp(lower // 1_000_000, UTC).date()
        while day_us(cursor) < end:
            wanted.add(cursor)
            cursor += timedelta(days=1)
        windows.append((fold["id"], lower, start, end))
    progress.update("复用原验收现货分钟来源", 0, 10, "文件")
    report.update(source_receipt_sha256=spec["source_receipt_sha256"], source_days_per_symbol=153, source_month_files=10)
    parts = []
    for index, record in enumerate(source["sources"]):
        path = allowed_source_path(record)
        require(file_sha(path) == record["normalized_sha256"], "Original accepted minute source bytes changed")
        frame = pl.read_parquet(path)
        require(frame.height == record["rows"] and frame["symbol"].eq(record["symbol"]).all(), "Accepted symbol/rows changed")
        parts.append(minute_view(frame))
        progress.update("复用原验收现货分钟来源", index + 1, 10, "文件")
    minutes = pl.concat(parts).sort(["open_us", "symbol"])
    lower_bound, upper_bound = min(row[1] for row in windows), max(row[3] for row in windows)
    minutes = minutes.filter(pl.col("open_us").is_between(lower_bound, upper_bound, closed="left"))
    minutes.write_parquet(work / "shared_source_minutes.parquet", compression="zstd")
    report["minute_source"] = {"path": str(work / "shared_source_minutes.parquet"), "sha256": file_sha(work / "shared_source_minutes.parquet"),
        "rows": minutes.height, "invalid_minutes": minutes.filter(~pl.col("minute_valid")).height}
    completed = 0
    for fold, lower, start, end in windows:
        fold_minutes = minutes.filter(pl.col("open_us").is_between(lower, end, closed="left"))
        calendar = np.arange(start, end, MINUTE_US, dtype=np.int64)
        fold_record = {"fold": fold, "start_us": start, "end_us": end, "days": 7, "results": [],
            "minute_input_sha256": hashlib.sha256(fold_minutes.write_ipc(None).getvalue()).hexdigest()}
        report["folds"].append(fold_record)
        if not complete_fold(fold_minutes, lower, start, end):
            fold_record.update(status="NOT_EVALUABLE_COMPLETE_MINUTE_SOURCE_MISSING", missing_minutes=fold_minutes.filter(~pl.col("minute_valid")).height)
            continue
        bars = fold_minutes.select("symbol", "close_us", "available_us")
        closes = fold_minutes.select("symbol", "close_us", "available_us", "close")
        daily_reference = reference_daily_returns(fold_minutes)
        for strategy in STRATEGIES:
            progress.update("生成固定策略意图；内部分钟轮次未知", completed, 72, "收益账本", fold=fold, strategy=strategy)
            generation_started = time.monotonic()
            plan = public_strategy.fixed_targets(fold_minutes, calendar) if strategy == public_strategy.STRATEGY_ID else bulk_fixed_targets.fixed_targets(
                strategy, closes, calendar, daily_returns=daily_reference if strategy == "VOL_MANAGED_BUY_AND_HOLD" else None)
            target_dir = work / (fold + "-" + strategy)
            target_dir.mkdir()
            plan.targets.write_parquet(target_dir / "targets.parquet")
            intent = plan.calendar_ledger.rename({"earliest_permissible_order_us": "preserved_v8_intent_earliest_order_us"}).with_columns(
                (pl.col("decision_us") + MINUTE_US).alias("comparison_order_eligible_us"))
            intent.write_parquet(target_dir / "intent_calendar.parquet")
            save_json(target_dir / "target_receipt.json", plan.receipt)
            save_json(target_dir / "target_generation_timing.json", {"elapsed_seconds": time.monotonic() - generation_started, "decision_rows": len(calendar), "model_fits": 0})
            if not plan.receipt["paired_comparison_allowed"]:
                fold_record["results"].append({"strategy": strategy, "status": "NOT_EVALUABLE_TARGET_WARMUP", "receipt": plan.receipt})
                continue
            for spread in (2, 4, 8):
                require(time.monotonic() - report["started_monotonic"] < spec["maximum_wall_seconds"], "Fixed CPU screening time budget reached; preserve partial ledgers")
                result = run_backtest(bars, fold_minutes, plan.targets, comparison_config(start, end, spread))
                ledger = write_ledger(target_dir / ("spread" + str(spread)), result, fold_minutes)
                fold_record["results"].append({"strategy": strategy, "spread_bps": spread, "nominal_roundtrip_bps": 28 + spread, **ledger})
                completed += 1
                progress.update("固定策略共同成本资金账本", completed, 72, "收益账本", fold=fold, strategy=strategy, roundtrip_bps=28 + spread)
        fold_record["status"] = "COMPLETE_PROXY_COMPARISON" if len(fold_record["results"]) == 18 else "PARTIAL_INPUT_COVERAGE"
    report.update(completed_ledgers=completed, all_planned_ledgers_complete=completed == 72)
    aggregate = []
    for strategy in STRATEGIES:
        for spread in (2, 4, 8):
            values = [result["summary"] for fold in report["folds"] for result in fold["results"]
                if result.get("strategy") == strategy and result.get("spread_bps") == spread]
            aggregate.append({"strategy": strategy, "spread_bps": spread, "complete7day_folds": len(values),
                "mean7day_net_return": float(np.mean([item["total_return"] for item in values])) if values else None,
                "worst7day_net_return": min(item["total_return"] for item in values) if values else None,
                "max_observed_daily_MDD": max(item["max_drawdown"] for item in values) if values else None,
                "fees_USDT_across_independent_accounts": sum(item["fees"] for item in values),
                "execution_cost_USDT_across_independent_accounts": sum(item["execution_costs"] for item in values),
                "trade_count": sum(item["trade_count"] for item in values),
                "annualization": "NONE_FOUR_INDEPENDENT7DAY_ACCOUNTS_NOT_CONTINUOUS_CAGR"})
    report["aggregate"] = aggregate
    require(sum(path.stat().st_size for path in work.rglob("*") if path.is_file()) <= spec["maximum_new_owned_bytes"], "Owned output disk budget exceeded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--smoke", action="store_true")
    modes.add_argument("--research", action="store_true")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    args = parser.parse_args()
    work, output = args.run_dir.resolve(), args.output.resolve()
    require(work.is_relative_to(STATE.resolve()) and not work.exists(), "Exclusive new native STATE run required")
    require(output.is_relative_to((ROOT / "reports/fast_research").resolve()) and not output.exists(), "Exclusive small report")
    require(bool(os.environ.get("COIN_TASK_ID")), "Actual bounded/progress wrapper required")
    resources.status()
    protocol_path = args.protocol.resolve()
    spec = read_json(protocol_path)
    hashes = {path: file_sha(ROOT / path) for path in spec["frozen_sources"]}
    hashes.update({str(protocol_path.relative_to(ROOT)): file_sha(protocol_path), str(Path(__file__).resolve().relative_to(ROOT)): file_sha(Path(__file__)),
        "tests/test_simple_strategy_comparison.py": file_sha(ROOT / "tests/test_simple_strategy_comparison.py")})
    command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
    test_command = [sys.executable, "-m", "pytest", "tests/test_simple_strategy_comparison.py", "-q",
        "--basetemp=" + str(work / "pytest"), "-o", "cache_dir=" + str(work / "pytest-cache"), "--junitxml=" + str(work / "junit.xml")]
    if spec.get("smoke_pytest_expression"):
        test_command.extend(["-k", spec["smoke_pytest_expression"]])
    binding = {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_hashes": hashes, "protocol_sha256": file_sha(protocol_path), "exact_command": shlex.join(command),
        "exact_test_command": shlex.join(test_command) if args.smoke else None, "environment_lock_sha256": hashes["environments/v8/uv.lock"],
        "sys_prefix": sys.prefix, "python": sys.executable, "all_folds": spec["folds"], "strategies": list(STRATEGIES),
        "data_scope": "SYNTHETIC_ONLY" if args.smoke else "ACCEPTED_DEVELOPMENT_DATES_ALREADY_INSPECTED_MECHANISM_SCREENING",
        "task_id": os.environ["COIN_TASK_ID"], "fits": 0, "seed": 20261002 if args.smoke else "NOT_APPLICABLE_DETERMINISTIC"}
    work.mkdir()
    save_json(work / "RUN_BINDING.json", binding)
    for name in hashes:
        saved = work / "source-snapshot" / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, saved)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=args.experiment_id, event_id=args.experiment_id + ":START", event_type="OPERATIONAL_START",
        git_commit=binding["git_commit"], data_manifest_hash=hashes["tests/test_simple_strategy_comparison.py"] if args.smoke else spec["source_receipt_sha256"],
        protocol_hash=binding["protocol_sha256"], feature_set="CLOSED_SPOT_MINUTE_PRICES_AND_31D_PAST_HISTORY_NO_478_CACHE",
        labels="NONE_STRATEGY_LEDGER_COMPARISON", model_family="NONE", hyperparameters=spec["common_config"], seed=binding["seed"],
        thresholds=spec["strategy_rules"], cost_assumptions=spec["costs"], all_folds=spec["folds"], success_failure="START",
        reason_for_next_experiment="Create actual fair simple-strategy net-return/risk/cost comparison before new model research",
        result_influenced_later_choice=False, source_hashes=hashes, exact_command=binding["exact_command"],
        environment_lock_sha256=binding["environment_lock_sha256"], run_binding_sha256=file_sha(work / "RUN_BINDING.json"), market_models_fit=0)
    registered = append_event(ROOT / "reports/experiment_registry.jsonl", event)
    report = {"status": "FAIL_SIMPLE_STRATEGY_COMPARISON", "registration_start": registered, "binding": binding,
        "run_dir": str(work), "run_binding_sha256": file_sha(work / "RUN_BINDING.json"), "folds": [],
        "started_monotonic": time.monotonic(), "market_inputs_read": False, "market_models_fit": 0, "locked_consumed": False,
        "orders_sent": 0, "candidate_status": "NO_QUALIFIED_CANDIDATE", "classification": "MINUTE_PROXY_SCREENING",
        "limitations": spec["limitations"], "primary_reference": spec["primary_reference"]}
    progress = Progress()
    progress.value["detail"] = "简单策略统一分钟代理账本；没有交易所订单或长期收益资格"
    try:
        source = verify_sources(spec)
        progress.update("真实扫描磁盘和账本预留", 0, None, "扫描")
        report["disk"] = {"scan_started_utc": datetime.now(UTC).isoformat(), **disk.check(10_000_000 if args.smoke else spec["maximum_new_owned_bytes"]),
            "scan_finished_utc": datetime.now(UTC).isoformat()}
        if args.smoke:
            progress.update("费用时序与账本合成验收", 0, None, "用例")
            result = subprocess.run(test_command, cwd=ROOT, check=False)
            report["test_exit_code"] = result.returncode
            if (work / "junit.xml").is_file():
                suites = ET.parse(work / "junit.xml").getroot()
                report["junit_counts"] = {key: sum(int(suite.attrib.get(key, "0")) for suite in suites.iter("testsuite")) for key in ("tests", "errors", "failures", "skipped")}
                report["junit_sha256"] = file_sha(work / "junit.xml")
            require(result.returncode == 0, "Actual comparison adapter smoke failed")
            report["status"] = "PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT"
        else:
            accepted = read_json(ROOT / spec["required_smoke_receipt"])
            require(accepted["status"] == "PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT"
                and accepted["binding"]["source_hashes"] == hashes, "Exact source must pass smoke before actual economics")
            report["accepted_smoke_sha256"] = file_sha(ROOT / spec["required_smoke_receipt"])
            report["market_inputs_read"] = True
            research(spec, source, work, progress, report)
            report["status"] = "COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING" if report["all_planned_ledgers_complete"] else "PARTIAL_ACTUAL_PROXY_STRATEGY_SCREENING_INPUT_LIMITS"
        require(hashes == {name: file_sha(ROOT / name) for name in hashes}, "Source bytes changed during execution")
        report["source_bytes_unchanged"] = True
    except Exception as error:
        report.update(status="FAIL_SIMPLE_STRATEGY_COMPARISON", error_type=type(error).__name__, reason=str(error))
        raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(), elapsed_seconds=time.monotonic() - report.pop("started_monotonic"),
            orchestrator_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            owned_bytes=sum(path.stat().st_size for path in work.rglob("*") if path.is_file()), resources=resources.status())
        save_json(output, report)
        append_event(ROOT / "reports/experiment_registry.jsonl", {**event, "event_id": args.experiment_id + ":RESULT",
            "event_type": "OPERATIONAL_RESULT", "success_failure": report["status"], "artifact_path": str(output.relative_to(ROOT)), "artifact_sha256": file_sha(output)})
        progress.stop.set()
        progress.thread.join(timeout=3)
        print(json.dumps({"status": report["status"], "output": str(output)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
