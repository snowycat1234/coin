"""Portable offline adapter around the byte-exact frozen native financial engine.

check verifies data, sources and saved target journals without creating wallets.
run is a separate, explicit command for later authorized fresh-account research.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
from decimal import Decimal
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import shutil
import time

REPO = Path(__file__).resolve().parents[2]
os.environ["QUANT_ROOT"] = str(REPO)
sys.path[:0] = [str(REPO / "src"), str(REPO)]

import numpy as np
import polars as pl
from scripts.investment import public_sma_perpetual, vol_managed_perpetual_target
from scripts.investment import donchian_daily_pool_target, perpetual_directional
from scripts.investment.frozen_expert_mixture import combine
from scripts.investment.regime_ranking_screen import bounded_path
from scripts.research.public_cross_section_momentum import public_targets, ANCHOR_US

DAY = 86_400_000_000
MINUTE = 60_000_000
START = 1784073600000000
END = 1791504000000000
INSTRUMENTS = ("BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "XRP-USDT-SWAP", "DOGE-USDT-SWAP")
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
EXPERTS = ("CASH", "VOL_MANAGED_HOLD", "PUBLIC_SMA50_200_SIGNED", "DONCHIAN_EXIT10", "CSMOM21")
REQUESTS = {"FIXED_VOL_HOLD": [0, 1, 0, 0, 0], "FIXED_CSMOM21": [0, 0, 0, 0, 1],
            "STATIC50": [0, .5, 0, 0, .5]}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def lines(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_check():
    manifest = read(Path(__file__).with_name("RECOVERY_MANIFEST.json"))
    for path, expected in manifest["source_sha256"].items():
        require(sha(REPO / path) == expected, "Frozen source identity differs: " + path)
    require(manifest["engine_sha256"] == sha(REPO / manifest["engine_path"]), "Exact frozen engine required")
    require(sha(Path(__file__).with_name("FINANCIAL_CONFIG.json")) == manifest["financial_config_sha256"],
            "Frozen financial configuration differs")
    require(sha(Path(__file__)) == manifest["adapter_sha256"], "Portable adapter source differs")
    require(ANCHOR_US == 1704067200000000, "Original weekly rank anchor required")
    return dict(engine_sha256=manifest["engine_sha256"], verified_source_files=len(manifest["source_sha256"]))


def daily_inputs(root):
    rows, closes, clocks, events = [], [], None, []
    for instrument, symbol in zip(INSTRUMENTS, SYMBOLS, strict=True):
        daily = lines(root / instrument / "daily.jsonl")
        actual = np.array([r["close_ms_exclusive"] * 1000 for r in daily], np.int64)
        require(len(daily) == 646 and np.all(np.diff(actual) == DAY), "Complete published daily history required")
        if clocks is None:
            clocks = actual
        require(np.array_equal(actual, clocks), "Ordered common daily clock required")
        closes.append([float(r["close"]) for r in daily])
        for r in daily:
            require(r["instrument_id"] == instrument and r["historical_available_ms"] is None,
                    "Retain explicit uncertified publication clocks")
            rows.append(dict(symbol=symbol, open_us=r["open_ms"] * 1000,
                close_us=r["close_ms_exclusive"] * 1000,
                available_us=r["close_ms_exclusive"] * 1000,  # declared historical close proxy
                **{k: float(r[k]) for k in ("open", "high", "low", "close")},
                volume=float(r["native_volume_fields"][1])))  # actual base volume
        funding = lines(root / instrument / "funding.jsonl")
        require(len(funding) == 258 and [r["funding_time_ms"] * 1000 for r in funding]
                == list(range(START, END, DAY // 3)), "Exact observed signed funding calendar required")
        for r in funding:
            require(r["realizedRate"] == r["native_record"]["realizedRate"], "Actual signed funding field required")
            events.append(dict(symbol=symbol, event_us=r["funding_time_ms"] * 1000,
                               raw_rate=float(r["realizedRate"]), reported_interval_hours=8.))
    return pl.DataFrame(rows).sort(["symbol", "close_us"]), np.asarray(closes).T, clocks, sorted(events, key=lambda r: (r["event_us"], r["symbol"]))


def shard_index(root):
    coverage = read(root / "minute-intake/COVERAGE.json")
    require(coverage["full_window_ready"] and len(coverage["shards"]) == 430, "Resolved 430-day coverage required")
    index = {(r["instrument_id"], r["date"]): r for r in coverage["shards"]}
    require(len(index) == 430, "Unique instrument/date identities required")
    require(index["SOL-USDT-SWAP", "2026-08-28"]["bars_files"]["trade"].startswith("gap-resolution/"),
            "Published archive precedence must be selected explicitly")
    return index


def load_day(root, index, stamp, *, verify=True):
    date = datetime.fromtimestamp(stamp / 1_000_000, UTC).date().isoformat()
    times = np.arange(stamp, stamp + DAY, MINUTE, dtype=np.int64)
    market = {}
    for instrument, symbol in zip(INSTRUMENTS, SYMBOLS, strict=True):
        entry = index[instrument, date]
        require(entry["status"] == "COMPLETE", "Incomplete input is never filled or dropped")
        if verify:
            require(sha(root / "minute-intake" / entry["manifest"]) == entry["manifest_sha256"], "Shard manifest identity differs")
        data = {}
        for kind in ("trade", "mark"):
            path = root / "minute-intake" / entry["bars_files"][kind]
            if verify:
                require(sha(path) == entry["bars_sha256"][kind], "Exact original compressed shard required")
            records = lines(path)
            require(len(records) == 1440 and [r["open_ms"] * 1000 for r in records] == times.tolist(), "Complete minute grid required")
            require(all(r["close_ms_exclusive"] * 1000 == int(t) + MINUTE
                        and r["source_confirm"] == "1" and r["completed"]
                        and r["received_ms"] == r["available_ms"]
                        and r["historical_available_ms"] is None
                        and r["instrument_id"] == instrument for r, t in zip(records, times, strict=True)),
                    "Preserved real records, confirmation and retrieval clocks required")
            require(all(Decimal(r["open"]) > 0 and Decimal(r["close"]) > 0 for r in records), "Positive actual prices required")
            if kind == "trade":
                require(all(r["quote_turnover_USDT"] == r["volCcyQuote"]
                            and Decimal(r["quote_turnover_USDT"]) >= 0 for r in records), "Actual quote-USDT capacity required")
                data.update(open=np.array([float(r["open"]) for r in records]),
                            close=np.array([float(r["close"]) for r in records]),
                            quote_volume=np.array([float(r["quote_turnover_USDT"]) for r in records]))
            else:
                require(all(r["quote_turnover_USDT"] is None for r in records), "Mark cannot supply traded capacity")
                data["mark"] = np.array([float(r["close"]) for r in records])
        if verify:
            require(sha(root / "minute-intake" / entry["responses_file"]) == entry["responses_sha256"], "Original response evidence differs")
        market[symbol] = data
    return dict(times=times, market=market)


def targets(root, start, end, policy):
    bars, close, available, _ = daily_inputs(root)
    decisions = np.arange(start, end, DAY, dtype=np.int64)
    frames = {}
    def frame(weights, raw):
        return pl.DataFrame([dict(available_us=int(t), symbol=s, target_weight=float(weights[i, j]),
            raw_signed_target=float(raw[i, j]), mode="LONG_SHORT", eligibility_reason="ELIGIBLE")
            for i, t in enumerate(decisions) for j, s in enumerate(SYMBOLS)])
    zero = np.zeros((len(decisions), len(SYMBOLS)))
    frames[EXPERTS[0]] = frame(zero, zero)
    frames[EXPERTS[1]], _ = vol_managed_perpetual_target.fixed_targets(bars, decisions, symbols=SYMBOLS)
    frames[EXPERTS[2]], _ = public_sma_perpetual.fixed_targets(bars, decisions, "LONG_SHORT", symbols=SYMBOLS)
    frames[EXPERTS[3]], _ = donchian_daily_pool_target.fixed_targets(bars, decisions, symbols=SYMBOLS, exit_period=10)
    weight, diagnostic = public_targets(close, available, decisions, SYMBOLS, SYMBOLS, anchor_us=ANCHOR_US)
    require(np.asarray(diagnostic["current_eligible"]).all(), "All five original experts must be available")
    ranks = {r["rank_us"]: np.asarray(r["raw_weights"]) for r in diagnostic["rank_events"]}
    frames[EXPERTS[4]] = frame(weight, np.asarray([ranks[t] for t in diagnostic["rank_us"]]))
    budgets = bounded_path(np.tile(REQUESTS[policy], (len(decisions), 1)), [1, 0, 0, 0, 0], .1)
    target = combine(frames, list(EXPERTS), decisions, SYMBOLS, budgets)
    # The original global final-day cash convention applies to the entire
    # interval. It does not reset or close accounts at intermediate dates.
    target = target.with_columns(pl.when(pl.col("available_us") == int(decisions[-1]))
                                 .then(0.).otherwise(pl.col("target_weight")).alias("target_weight"))
    return target, budgets, bars


def check(state):
    report = source_check()
    root = state / "okx86/selected"
    index = shard_index(root)
    bars, _, _, events = daily_inputs(root)
    for day, stamp in enumerate(range(START, END, DAY), 1):
        load_day(root, index, stamp)
        if day % 20 == 0 or day == 86:
            print(json.dumps(dict(stage="input_verification", days=day, total_days=86)), flush=True)
    comparisons = []
    for days in (44, 41):
        ref = state / f"reference{days}"
        config = read(ref / "FINANCIAL_CONFIG.json")
        for policy in REQUESTS:
            built, budgets, _ = targets(root, config["calendar"]["start"], config["calendar"]["end"], policy)
            saved = pl.read_parquet(ref / "results" / policy / "account/targets.parquet")
            left = built.sort(["available_us", "symbol"]).select("available_us", "symbol", "target_weight")
            right = saved.sort(["available_us", "symbol"]).select("available_us", "symbol", "target_weight")
            difference = float(np.max(np.abs(left["target_weight"].to_numpy() - right["target_weight"].to_numpy())))
            require(left.equals(right), f"Exact saved target mismatch: {days} {policy} max={difference}")
            comparisons.append(dict(days=days, policy=policy, rows=left.height,
                                    maximum_target_error=difference, equality="EXACT_VALUES_AND_KEYS"))
            print(json.dumps(comparisons[-1]), flush=True)
    report.update(complete_asset_days=430, minute_rows=1238400, daily_rows=bars.height,
                  funding_events=len(events), targets=comparisons, wallets_run=0, fits=0,
                  provider_downloads=0, engine_bytes="EXACT", runner_adapter="NEW_PORTABLE_ADAPTER",
                  continuous86_result="NOT_RUN", historical_rules_certified=False)
    return report


def run(state, policy, output, *, limit_seconds=600, reserve_bytes=15 * 1024**3):
    # This command must only be invoked after the user's continuation.
    source_check()
    root = state / "okx86/selected"
    index = shard_index(root)
    target, budgets, bars = targets(root, START, END, policy)
    _, _, _, events = daily_inputs(root)
    def blocks():
        for stamp in range(START, END, DAY):
            yield load_day(root, index, stamp)
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    cost = read(Path(__file__).with_name("FINANCIAL_CONFIG.json"))["cost"]
    window = dict(symbols=SYMBOLS, start=START, end=END, daily=bars, events=events, minute_blocks=blocks)
    sim = NativeDailySimulator(window, "LONG_SHORT", cost, dict(id="RAW_AS_FRACTION", scale=1.),
        account_factory=BybitIsolatedAccount, persist_cash_close=True, final_day_target_zero=True)
    output.mkdir(parents=True, exist_ok=False)
    sim.budget = [1., 0., 0., 0., 0.]
    status, error = "RUNNING", None
    started = time.monotonic()
    try:
        for i, stamp in enumerate(range(START, END, DAY)):
            require(time.monotonic() - started < limit_seconds, "Per-wallet time budget exhausted")
            require(shutil.disk_usage(output).free >= reserve_bytes, "15 GiB disk reserve required")
            sim.budget = budgets[i].tolist()
            rows = target.filter(pl.col("available_us") == stamp)
            actual = sim.advance_day(dict(zip(rows["symbol"], rows["target_weight"], strict=True)))
            require(actual["completed"], "Incomplete account must stop")
            print(json.dumps(dict(stage=policy, days=i + 1, total_days=86, NAV=float(sim.account.nav()))), flush=True)
        require(sim.rows_written == 123840 and all(p.quantity == 0 for p in sim.account.positions.values()),
                "Full paid terminal-flat account required")
        status = "COMPLETE_CONDITIONAL_ACCOUNT"
    except BaseException as exc:
        status, error = "FAILED_PREFIX_RETAINED", dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        saved = perpetual_directional.save_case(sim.result(), output / "account")
        # Original save_case returns its summary; persist it even after a stop.
        with (output / "account/summary.json").open("x") as stream:
            json.dump(saved["summary"], stream, indent=2)
            stream.write("\n")
        with (output / "RUN.json").open("x") as stream:
            json.dump(dict(status=status, error=error, policy=policy,
                completed_minutes=sim.rows_written, required_minutes=123840,
                initial_capital_USDT=10000, guard_enabled=False,
                financial_config_sha256=sha(Path(__file__).with_name("FINANCIAL_CONFIG.json")),
                source_identity=source_check(), baseline_targets_only=False,
                independent_financial_audit="NOT_RUN", exchange_rules_certified=False), stream, indent=2)
            stream.write("\n")
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "run"))
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", choices=tuple(REQUESTS))
    args = parser.parse_args()
    if args.command == "check":
        report = check(args.state)
        with args.output.open("x") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    else:
        require(args.policy is not None, "Explicit single fresh-wallet policy required")
        print(json.dumps(run(args.state, args.policy, args.output), default=str))


if __name__ == "__main__":
    main()
