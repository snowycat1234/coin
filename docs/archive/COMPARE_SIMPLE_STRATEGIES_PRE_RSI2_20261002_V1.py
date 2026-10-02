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
STRATEGIES = ("CASH", "SPOT_BUY_AND_HOLD", "VOL_MANAGED_BUY_AND_HOLD", "FIXED_TREND", "FIXED_MEAN_REVERSION", public_strategy.STRATEGY_ID, public_strategy.STRATEGY_2H_ID,
    "COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER")
file_sha = benchmarks.file_sha
START, LOCKED = date(2025, 7, 1), date(2026, 3, 1)
SOURCE_SCOPES = {
    "JUL_NOV_2025": (("2025-07", "2025-08", "2025-09", "2025-10", "2025-11"), 153,
        "PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_153D_CALENDAR"),
    "OCT2025_FEB2026": (("2025-10", "2025-11", "2025-12", "2026-01", "2026-02"), 151,
        "PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_151D_CALENDAR"),
}


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


def source_scope(spec):
    """Only two accepted, explicit calendars; legacy protocols retain July-Nov."""
    key = spec.get("source_scope", "JUL_NOV_2025")
    require(key in SOURCE_SCOPES, "Only two fixed accepted source scopes")
    months, days, status = SOURCE_SCOPES[key]
    require(tuple(spec.get("source_calendar", months if key == "JUL_NOV_2025" else ())) == months,
        "Exact authorized source_calendar required")
    require(spec.get("source_days_per_symbol", days) == days, "Exact accepted source day count")
    return key, months, days, status


def allowed_source_path(record, spec=None):
    """Reject unapproved dates/path before opening or hashing a market file."""
    _, months, _, _ = source_scope(spec or {})
    require(record["symbol"] in SYMBOLS and record["month"] in months,
        "Only explicit accepted source calendar Spot minutes; no locked IO")
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


def signal_close_view(minutes, calendar):
    """Exclude closes after the last decision; keep full execution/MTM minutes."""
    calendar = benchmarks.calendar_array(calendar)
    return minutes.select("symbol", "close_us", "available_us", "close").filter(pl.col("close_us") <= int(calendar[-1]))


def comparison_plan(spec):
    """Protocol-selected sleeves and whole UTC periods; no outcome selection."""
    strategies = tuple(spec.get("strategy_ids", STRATEGIES[:6]))
    require(strategies and len(set(strategies)) == len(strategies) and set(strategies) <= set(STRATEGIES),
        "Unique subset of the already fixed strategies required")
    windows = []
    for period in spec["folds"]:
        identifier = period["id"]
        require(isinstance(identifier, str) and identifier.replace("_", "").isalnum(), "Safe unique period identifier")
        start = day_us(date.fromisoformat(period.get("period_start", period.get("test_start"))))
        end = day_us(date.fromisoformat(period.get("period_end_exclusive", period.get("test_end_exclusive"))))
        lower = start - 31 * DAY_US
        require(day_us(START) <= lower < start < end <= day_us(LOCKED) and (end - start) % DAY_US == 0,
            "Complete positive development UTC periods with31day past warmup; no locked IO")
        windows.append((identifier, lower, start, end))
    require(windows and len({row[0] for row in windows}) == len(windows), "Unique nonempty period IDs")
    planned = len(windows) * len(strategies) * 3
    require(spec.get("planned_ledgers", planned) == planned, "Planned ledger count must match fixed periods/sleeves/costs")
    return strategies, windows, planned


def period_aggregate(folds, strategies):
    aggregate = []
    for strategy in strategies:
        for spread in (2, 4, 8):
            selected = [(period["days"], result["summary"]) for period in folds for result in period["results"]
                if result.get("strategy") == strategy and result.get("spread_bps") == spread]
            values = [value for _, value in selected]
            aggregate.append({"strategy": strategy, "spread_bps": spread, "complete_periods": len(values),
                "period_lengths_days": [days for days, _ in selected],
                "period_net_return": values[0]["total_return"] if len(values) == 1 else None,
                "mean_period_net_return": float(np.mean([item["total_return"] for item in values])) if values else None,
                "worst_period_net_return": min(item["total_return"] for item in values) if values else None,
                "max_observed_daily_MDD": max(item["max_drawdown"] for item in values) if values else None,
                "max_observed_minute_MDD": max(item["max_observed_minute_MDD"] for item in values) if values else None,
                "fees_USDT_across_period_accounts": sum(item["fees"] for item in values),
                "execution_cost_USDT_across_period_accounts": sum(item["execution_costs"] for item in values),
                "trade_count": sum(item["trade_count"] for item in values),
                "annualization": "NO_POOLED_CAGR_PERIOD_ACCOUNTS_NOT_STITCHED;_ENGINE_PERIOD_CAGR_DESCRIPTIVE_ONLY"})
    return aggregate


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
    received_asset_fee = result.summary.get("fee_settlement_version") == "BYBIT_SPOT_RECEIVED_ASSET_V1"
    position_delta = fills["position_delta"].to_numpy() if received_asset_fee else direction * fills["quantity"].to_numpy()
    cash_delta = fills["cash_delta"].to_numpy() if received_asset_fee else -direction * notional - fees
    cash_steps = cfg.initial_cash + np.cumsum(cash_delta)
    require(np.allclose(cash_steps, fills["cash_after"].to_numpy(), rtol=0, atol=1e-7), "Cash ledger does not reconcile actual fills")
    counts = np.searchsorted(execution, stamps, side="right")
    def at_steps(values):
        return np.r_[0., np.cumsum(values)][counts]
    cash = cfg.initial_cash + at_steps(cash_delta)
    gross_cash = cfg.initial_cash - at_steps(position_delta * fills["mid_price"].to_numpy())
    nav, gross_nav = cash.copy(), gross_cash.copy()
    output = {"close_us": stamps, "cash": cash}
    symbol_notionals = []
    for symbol in SYMBOLS:
        is_symbol = fills["symbol"].to_numpy() == symbol
        quantity = at_steps(position_delta * is_symbol)
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
        expected_fee = fill["notional"] * cfg.fee_rate
        if received_asset_fee:
            buy = fill["side"] == "buy"
            fee_units = fill["quantity"] * cfg.fee_rate if buy else expected_fee
            fee_asset = fill["symbol"][:-4] if buy else "USDT"
            expected_fee = fee_units * fill["mid_price"] if buy else fee_units
            expected_position = fill["quantity"] * (1 - cfg.fee_rate) if buy else -fill["quantity"]
            expected_cash = -fill["notional"] if buy else fill["notional"] - expected_fee
            require(fill["fee_asset"] == fee_asset and abs(fill["fee_amount"] - fee_units) < 1e-10
                and abs(fill["position_delta"] - expected_position) < 1e-10
                and abs(fill["cash_delta"] - expected_cash) < 1e-8
                and abs(fill["fee_USDT_mid"] - expected_fee) < 1e-8,
                "Received-asset fee or cash/inventory allocation is wrong")
        require(abs(fill["fee"] - expected_fee) < 1e-8
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
        period_days=summary["days"], period_net_return=summary["total_return"],
        period_descriptive_net_CAGR=summary["annual_return"], annualized_return_is_descriptive_only=True,
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
    if result.summary.get("fee_settlement_version") == "BYBIT_SPOT_RECEIVED_ASSET_V1":
        summary.update(gross_reference_quantity_semantics="NET_RECEIVED_BUYS_AND_GROSS_SELLS_MATCH_ACTUAL_INVENTORY",
            fee_valuation="BASE_FEE_MARKED_AT_FILL_MID;_QUOTE_SELL_FEE_ALREADY_USDT",
            fee_cash_and_inventory_changes_native_rule=True, data_venue="Binance", fee_reference_venue="Bybit",
            native_Bybit_market_or_filters_proven=False)
    return {"summary": summary, "directory": str(directory), "artifacts": {
        path.name: {"sha256": file_sha(path), "bytes": path.stat().st_size} for path in directory.iterdir() if path.is_file()}}


def verify_source_calendar(spec, source):
    """Receipt metadata and interval coverage, before any market-file IO."""
    key, months, days, status = source_scope(spec)
    require(source["status"] == status, "Accepted original minute source receipt required")
    receipt_spec = source["binding"]["spec"]
    require(tuple(receipt_spec["source_calendar"]) == months
        and receipt_spec.get("source_scope", "JUL_NOV_2025") == key, "Source receipt scope/calendar mismatch")
    expected = {(symbol, month) for symbol in SYMBOLS for month in months}
    require(len(source["sources"]) == 10 and {(r["symbol"], r["month"]) for r in source["sources"]} == expected,
        "Exactly ten authorized explicit symbol-months required")
    require(source["source_files"] == 10 and source["days_per_symbol"] == days
        and source["actual_minute_rows"] == days * 1440 * 2, "Exact accepted source coverage required")
    for record in source["sources"]:
        allowed_source_path(record, spec)
        first = date.fromisoformat(record["month"] + "-01")
        last = date(first.year + first.month // 12, first.month % 12 + 1, 1)
        rows = (last - first).days * 1440
        quality = record["old_quality"]
        require(record["rows"] == rows and quality["rows"] == rows and quality["expected_rows"] == rows
            and quality["first_open_us"] == day_us(first) and quality["last_open_us"] == day_us(last) - MINUTE_US
            and all(quality[name] == 0 for name in ("missing_rows", "duplicate_rows", "bad_timestamps", "bad_values", "gaps", "quarantined_rows"))
            and not quality["incomplete_days"] and not quality["quarantined_days"], "Complete sealed monthly coverage required")
    lower = day_us(date.fromisoformat(months[0] + "-01"))
    # upper uses the authorized final month, independent of receipt row order.
    final_month = date.fromisoformat(months[-1] + "-01")
    upper = day_us(date(final_month.year + final_month.month // 12, final_month.month % 12 + 1, 1))
    require(all(lower <= window[1] < window[2] < window[3] <= upper for window in comparison_plan(spec)[1]),
        "Accepted source does not cover complete warmup and scoring interval")
    return days


def verify_sources(spec):
    expected = spec["frozen_sources"]
    for path, digest in expected.items():
        require(file_sha(ROOT / path) == digest, "Frozen source changed: " + path)
    source = read_json(ROOT / spec["source_receipt"])
    require(file_sha(ROOT / spec["source_receipt"]) == spec["source_receipt_sha256"], "Accepted original minute source receipt hash required")
    verify_source_calendar(spec, source)
    require(Path(sys.prefix).resolve() == Path(spec["environment"]["sys_prefix"]).resolve()
        and file_sha(ROOT / "environments/v8/uv.lock") == spec["environment"]["lock_sha256"], "Accepted clean native CPU environment")
    require(pl.thread_pool_size() <= 2, "At most2 Polars threads")
    require(spec.get("fee_settlement", "LEGACY_QUOTE") in ("LEGACY_QUOTE", "BYBIT_SPOT_RECEIVED_ASSET_V1"),
        "Only explicit existing quote or Bybit Spot received-asset fees")
    if spec.get("fee_settlement") == "BYBIT_SPOT_RECEIVED_ASSET_V1":
        from scripts.investment import bybit_spot_adapter
        require(spec["fee_profile_path"] == "protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json"
            and file_sha(ROOT / spec["fee_profile_path"]) == spec["fee_profile_sha256"], "Fixed ordinary Bybit Spot fee reference")
        require(spec["costs"]["fee_bps_per_side"] == 10 and spec["market_type"] == "CRYPTO_SPOT_NO_BORROW_OR_LEVERAGE",
            "Bybit Spot tenbp; no perpetual fee or margin substitution")
        bybit_spot_adapter.derivation_receipt()
    return source


def reused_minute_input(spec):
    """Exact accepted derivative input; no raw source QA or signal regeneration."""
    reference = spec["reused_minute_input"]
    parent = read_json(ROOT / reference["report_path"])
    require(file_sha(ROOT / reference["report_path"]) == reference["report_sha256"]
        and parent["status"] == "COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING"
        and parent["source_bytes_unchanged"] and parent["all_planned_ledgers_complete"], "Completed unchanged parent input report required")
    require(parent["source_receipt_sha256"] == spec["source_receipt_sha256"], "Parent minute source receipt differs")
    path = Path(reference["path"]).resolve()
    require(path.is_relative_to(STATE.resolve()) and path == Path(parent["minute_source"]["path"]).resolve()
        and reference["sha256"] == parent["minute_source"]["sha256"] and file_sha(path) == reference["sha256"],
        "Exact accepted nativeSTATE derivative Parquet required")
    frame = pl.read_parquet(path)
    require(frame.height == parent["minute_source"]["rows"] and
        {"symbol", "open_us", "available_us", "close_us", "open", "high", "low", "close", "quote_volume", "minute_valid", "valid_day", "missing_reason"} <= set(frame.columns),
        "Exact accepted derivative row count and marking/availability schema required")
    return frame


def reused_public_target(spec, strategy, fold, calendar):
    """Reuse one exact accepted2h signal plan when only settlement changes."""
    require(strategy == public_strategy.STRATEGY_2H_ID, "Only unchanged public2h targets may be reused")
    reference = spec["reused_target_inputs"][fold + ':' + strategy]
    audit_reference = reference['accepted_audit']
    audit = read_json(ROOT / audit_reference['path'])
    require(file_sha(ROOT / audit_reference['path']) == audit_reference['sha256'] and audit['status'] in
        ('PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE', 'PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE_WITH_NONPORTABLE_IPC_LIMIT'),
        "Existing accepted target audit binding required")
    prior = [row for row in audit['ledgers'] if row['fold'] == fold and row['strategy'] == strategy]
    require(len(prior) == 3 and {row['spread_bps'] for row in prior} == {2, 4, 8} and all(
        row['target_bindings'] == {key: reference[name]['sha256'] for key, name in
            (('target_sha256', 'targets.parquet'), ('intent_sha256', 'intent_calendar.parquet'), ('receipt_sha256', 'target_receipt.json'))}
        for row in prior), "Target bytes must match the previously accepted three-account audit")
    frames = {}
    for name in ('targets.parquet', 'intent_calendar.parquet', 'target_receipt.json'):
        item = reference[name]
        path = Path(item['path']).resolve()
        require(path.is_relative_to(STATE.resolve()) and path.is_file()
            and file_sha(path) == item['sha256'], "Exact accepted nativeSTATE target artifact required")
        frames[name] = json.loads(path.read_text()) if name.endswith('.json') else pl.read_parquet(path)
    receipt, targets, intent = frames['target_receipt.json'], frames['targets.parquet'], frames['intent_calendar.parquet']
    require(receipt['strategy_id'] == strategy and receipt['paired_comparison_allowed']
        and not receipt['warmup_failed'] and receipt['timeframe_minutes'] == 120
        and receipt['public_upstream_sha256'] == public_strategy.PINNED_HASHES
        and receipt['calendar_sha256'] == hashlib.sha256(calendar.tobytes()).hexdigest()
        and receipt['decision_count'] == len(calendar)
        and public_strategy.original.frame_sha(targets) == receipt['targets_sha256'], "Exact accepted causal public2h plan required")
    require(intent.height == len(calendar) * 2 and
        all(np.array_equal(intent.filter(pl.col('symbol') == symbol)['decision_us'].to_numpy(), calendar) for symbol in SYMBOLS),
        "Same complete target decision calendar required")
    original_intent = intent.drop('comparison_order_eligible_us').rename(
        {'preserved_v8_intent_earliest_order_us': 'earliest_permissible_order_us'})
    return public_strategy.original.TargetPlan(strategy, targets, original_intent, receipt)


def bind_reused_reference(spec, minute_source, report):
    if "reused_reference_report" not in spec:
        return
    path = ROOT / spec["reused_reference_report"]
    previous = read_json(path)
    require(file_sha(path) == spec["reused_reference_report_sha256"]
        and previous["status"] == "COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING" and previous["completed_ledgers"] == 12,
        "Exact accepted twelve reference accounts required; no replays")
    require(previous["minute_source"]["sha256"] == minute_source["sha256"], "New account must share byte-identical reference minute input")
    require(previous["registration_start"]["hyperparameters"] == spec["common_config"]
        and previous["registration_start"]["cost_assumptions"] == spec["costs"] and previous["binding"]["all_folds"] == spec["folds"],
        "Reference must share period, funding and risk parameters")
    for name in ("src/quant/backtest.py", "src/quant/execution_contract.py", "src/quant/decision_policy.py", "src/quant/metrics.py"):
        require(previous["binding"]["source_hashes"][name] == file_sha(ROOT / name), "Reference economic engine changed")
    report["reused_reference_binding"] = {"report_path": str(path.relative_to(ROOT)), "report_sha256": file_sha(path),
        "run_binding_sha256": previous["run_binding_sha256"], "minute_input_sha256": minute_source["sha256"],
        "reference_source_hashes": previous["binding"]["source_hashes"], "reference_run_git_commit": previous["binding"]["git_commit"],
        "reused_accounts": 12, "new_accounts": 3, "existing_reference_accounts_replayed": False,
        "same_common_config_and_period": True, "historical_screening_not_unseen": True}


def accept_synthetic_receipt(accepted, spec, hashes):
    """Native settlement tests cover shared code, independent of market period.

    Date/source receipts still pass verify_sources and exact derivative/target
    binding before economic execution. A different period does not repeat the
    same synthetic account. Legacy protocols retain the full exact binding.
    """
    require(accepted['status'] == 'PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT',
        'Accepted synthetic integration required')
    previous = accepted['binding']['source_hashes']
    if spec.get('fee_settlement') != 'BYBIT_SPOT_RECEIVED_ASSET_V1':
        require(previous == hashes, 'Exact source must pass smoke before actual economics')
        return 'EXACT_FULL_BINDING'
    def shared(binding):
        return {name: digest for name, digest in binding.items()
            if name.startswith(('src/', 'scripts/', 'tests/', 'environments/', 'third_party/'))
            or name in ('protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json',
                'protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json')}
    require(shared(previous) == shared(hashes) and
        'scripts/investment/bybit_spot_adapter.py' in shared(hashes) and
        'tests/test_investment_bybit_pipeline.py' in shared(hashes) and
        accepted['registration_start']['hyperparameters'] == spec['common_config'] and
        accepted['registration_start']['cost_assumptions'] == spec['costs'] and
        accepted['registration_start']['thresholds'] == spec['strategy_rules'],
        'All shared code, environment, fee contract and economic assumptions must match synthetic acceptance')
    return 'EXACT_SHARED_CODE_AND_ECONOMIC_RULES_PERIOD_AND_INPUTS_VERIFIED_SEPARATELY'


def research(spec, source, work, progress, report):
    strategies, windows, planned = comparison_plan(spec)
    report.update(planned_ledgers=planned, account_continuity="SINGLE_CONTINUOUS_PERIOD_BY_STRATEGY_AND_COST" if len(windows) == 1
        else "INDEPENDENT_PERIOD_ACCOUNTS_NOT_STITCHED")
    report.update(source_receipt_sha256=spec["source_receipt_sha256"], source_days_per_symbol=source_scope(spec)[2],
        source_scope=source_scope(spec)[0], source_calendar=list(source_scope(spec)[1]), source_month_files=10)
    if spec.get("reused_minute_input"):
        progress.update("复用已验收分钟Parquet；不重复来源QA", 0, 1, "文件")
        minutes = reused_minute_input(spec)
        report.update(reused_minute_input=spec["reused_minute_input"], raw_normalized_market_files_read=False)
        progress.update("复用已验收分钟Parquet；不重复来源QA", 1, 1, "文件")
    else:
        progress.update("复用原验收现货分钟来源", 0, 10, "文件")
        parts = []
        for index, record in enumerate(source["sources"]):
            path = allowed_source_path(record, spec)
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
    if spec.get("fee_settlement") == "BYBIT_SPOT_RECEIVED_ASSET_V1":
        from scripts.investment import bybit_spot_adapter
        report["fee_derivation"] = bybit_spot_adapter.export_derivation(work / "fee-derivation")
        report["fee_settlement"] = spec["fee_settlement"]
        report["fee_profile_sha256"] = spec["fee_profile_sha256"]
        execute = bybit_spot_adapter.run_backtest
    else:
        execute = run_backtest
    bind_reused_reference(spec, report["minute_source"], report)
    completed = 0
    for fold, lower, start, end in windows:
        fold_minutes = minutes.filter(pl.col("open_us").is_between(lower, end, closed="left"))
        if spec.get("fee_settlement") == "BYBIT_SPOT_RECEIVED_ASSET_V1":
            input_path = work / (fold + '-minute-input.arrow')
            fold_minutes.write_ipc(input_path)
            fold_minutes = pl.read_ipc(input_path, memory_map=False)
            input_binding = dict(minute_input_path=str(input_path), minute_input_sha256=file_sha(input_path),
                minute_input_format='IMMUTABLE_ARROW_IPC_FILE_READ_BEFORE_SIGNALS_AND_EXECUTION')
        else:
            input_binding = dict(minute_input_sha256=hashlib.sha256(fold_minutes.write_ipc(None).getvalue()).hexdigest())
        calendar = np.arange(start, end, MINUTE_US, dtype=np.int64)
        fold_record = {"fold": fold, "start_us": start, "end_us": end, "days": (end - start) // DAY_US, "results": [],
            **input_binding}
        report["folds"].append(fold_record)
        if not complete_fold(fold_minutes, lower, start, end):
            fold_record.update(status="NOT_EVALUABLE_COMPLETE_MINUTE_SOURCE_MISSING", missing_minutes=fold_minutes.filter(~pl.col("minute_valid")).height)
            continue
        bars = fold_minutes.select("symbol", "close_us", "available_us")
        closes = signal_close_view(fold_minutes, calendar)
        daily_reference = reference_daily_returns(fold_minutes)
        for strategy in strategies:
            progress.update("生成固定策略意图；内部分钟轮次未知", completed, planned, "收益账本", fold=fold, strategy=strategy)
            generation_started = time.monotonic()
            if fold + ':' + strategy in spec.get('reused_target_inputs', {}):
                plan = reused_public_target(spec, strategy, fold, calendar)
                report.setdefault('reused_target_inputs', {})[fold + ':' + strategy] = spec['reused_target_inputs'][fold + ':' + strategy]
            elif strategy == "COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER":
                from scripts.investment import public_donchian_hybrid
                plan = public_donchian_hybrid.fixed_targets(fold_minutes, calendar)
            elif strategy in (public_strategy.STRATEGY_ID, public_strategy.STRATEGY_2H_ID):
                plan = public_strategy.fixed_targets(fold_minutes, calendar, timeframe_minutes=120 if strategy == public_strategy.STRATEGY_2H_ID else 60)
            else:
                plan = bulk_fixed_targets.fixed_targets(strategy, closes, calendar,
                    daily_returns=daily_reference if strategy == "VOL_MANAGED_BUY_AND_HOLD" else None)
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
                result = execute(bars, fold_minutes, plan.targets, comparison_config(start, end, spread))
                ledger = write_ledger(target_dir / ("spread" + str(spread)), result, fold_minutes)
                fold_record["results"].append({"strategy": strategy, "spread_bps": spread, "nominal_roundtrip_bps": 28 + spread, **ledger})
                completed += 1
                progress.update("固定策略共同成本资金账本", completed, planned, "收益账本", fold=fold, strategy=strategy, roundtrip_bps=28 + spread)
        fold_record["status"] = "COMPLETE_PROXY_COMPARISON" if len(fold_record["results"]) == len(strategies) * 3 else "PARTIAL_INPUT_COVERAGE"
    report.update(completed_ledgers=completed, all_planned_ledgers_complete=completed == planned)
    report["aggregate"] = period_aggregate(report["folds"], strategies)
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
    strategies, windows, planned = comparison_plan(spec)
    hashes = {path: file_sha(ROOT / path) for path in spec["frozen_sources"]}
    smoke_test_path = spec.get("smoke_test_path", "tests/test_simple_strategy_comparison.py")
    require(smoke_test_path.startswith("tests/") and (ROOT / smoke_test_path).resolve().is_relative_to(ROOT / "tests"), "Explicit project test source")
    hashes.update({str(protocol_path.relative_to(ROOT)): file_sha(protocol_path), str(Path(__file__).resolve().relative_to(ROOT)): file_sha(Path(__file__)),
        smoke_test_path: file_sha(ROOT / smoke_test_path)})
    command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
    test_command = [sys.executable, "-m", "pytest", smoke_test_path, "-q",
        "--basetemp=" + str(work / "pytest"), "-o", "cache_dir=" + str(work / "pytest-cache"), "--junitxml=" + str(work / "junit.xml")]
    if spec.get("smoke_pytest_expression"):
        test_command.extend(["-k", spec["smoke_pytest_expression"]])
    binding = {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_hashes": hashes, "protocol_sha256": file_sha(protocol_path), "exact_command": shlex.join(command),
        "exact_test_command": shlex.join(test_command) if args.smoke else None, "environment_lock_sha256": hashes["environments/v8/uv.lock"],
        "sys_prefix": sys.prefix, "python": sys.executable, "all_folds": spec["folds"], "strategies": list(strategies), "planned_ledgers": planned,
        "data_scope": "SYNTHETIC_ONLY" if args.smoke else "ACCEPTED_DEVELOPMENT_HISTORICAL_SCREENING_NOT_UNSEEN",
        "task_id": os.environ["COIN_TASK_ID"], "fits": 0, "seed": 20261002 if args.smoke else "NOT_APPLICABLE_DETERMINISTIC"}
    work.mkdir()
    save_json(work / "RUN_BINDING.json", binding)
    for name in hashes:
        saved = work / "source-snapshot" / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, saved)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=args.experiment_id, event_id=args.experiment_id + ":START", event_type="OPERATIONAL_START",
        git_commit=binding["git_commit"], data_manifest_hash=hashes[smoke_test_path] if args.smoke else spec["source_receipt_sha256"],
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
            report['synthetic_acceptance_scope'] = accept_synthetic_receipt(accepted, spec, hashes)
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
