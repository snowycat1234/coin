"""One consumed ticket per sealed holdout; a failed development run cannot open it."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import polars as pl

from .paths import ROOT, STATE, utc_now_us
from .research import (
    INTERVAL_US,
    _flat_targets,
    build_features,
    canonical_hash,
    date_us,
    evaluate_gates,
    excess_bootstrap,
    predict_exported_model,
    quarter_profit_fraction,
)


class HoldoutDenied(ValueError):
    pass


@dataclass(frozen=True)
class HoldoutGrant:
    model_sha256: str
    protocol_sha256: str
    dataset_id: str
    authorized_by: str
    reason: str
    confirmation: str = "one_frozen_candidate_once"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _native(path: str | Path) -> Path:
    result = Path(path).resolve()
    if not result.is_relative_to(STATE.resolve()):
        raise HoldoutDenied("留出消费账本必须使用D盘WSL native STATE")
    return result


def _development_gate(report: dict) -> None:
    # Deliberately precedes model/protocol/data reads and native database creation.
    if report.get("status") != "HOLDOUT_REQUIRED" or report.get("holdout_revealed") is not False:
        raise HoldoutDenied("开发研究没有通过或留出已揭晓；禁止读取留出")
    interval = report.get("selected_interval")
    if interval not in INTERVAL_US or not report.get("frozen_model_sha256"):
        raise HoldoutDenied("尚未冻结唯一候选模型")
    if (
        report.get("candidates", {}).get(interval, {}).get("gates", {}).get("development_passed")
        is not True
    ):
        raise HoldoutDenied("所选候选未通过预登记开发门槛")
    sealed_v1 = ROOT / "reports/generated/P04/summary.json"
    if sealed_v1.exists():
        known = json.loads(sealed_v1.read_text())
        if known.get("status") == "STOP" and report.get("protocol_sha256") == known.get(
            "protocol_sha256"
        ):
            raise HoldoutDenied("已封存v1为STOP，不能用另一个summary改写准入")


def _open_journal(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS attempts (
            dataset_id TEXT PRIMARY KEY, ticket_sha TEXT UNIQUE NOT NULL,
            received_us INTEGER NOT NULL, ticket TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS receipts (
            ticket_sha TEXT PRIMARY KEY, received_us INTEGER NOT NULL,
            receipt_sha TEXT UNIQUE NOT NULL, receipt TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS attempts_no_update BEFORE UPDATE ON attempts
            BEGIN SELECT RAISE(ABORT,'immutable holdout ticket'); END;
        CREATE TRIGGER IF NOT EXISTS attempts_no_delete BEFORE DELETE ON attempts
            BEGIN SELECT RAISE(ABORT,'immutable holdout ticket'); END;
        CREATE TRIGGER IF NOT EXISTS receipts_no_update BEFORE UPDATE ON receipts
            BEGIN SELECT RAISE(ABORT,'immutable release receipt'); END;
        CREATE TRIGGER IF NOT EXISTS receipts_no_delete BEFORE DELETE ON receipts
            BEGIN SELECT RAISE(ABORT,'immutable release receipt'); END;
    """)
    db.commit()
    return db


def _load_locked_data(protocol: dict, lock: dict) -> tuple[pl.DataFrame, pl.DataFrame]:
    from .data import load_bars

    start, end = date_us(protocol["holdout_start"]), date_us(protocol["holdout_end"])
    intervals = tuple(sorted({"1h", protocol["selected_interval"]}))
    bars = load_bars(intervals).filter(pl.col("open_us") < end)
    files = [ROOT / name for name in lock["minute_files"]]
    columns = [
        "symbol",
        "interval",
        "open_us",
        "close_us",
        "available_us",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_volume",
        "trade_count",
        "taker_buy_base",
        "taker_buy_quote",
    ]
    minutes = (
        pl.scan_parquet(files)
        .filter(
            pl.col("valid_day")
            & (pl.col("open_us") >= start - 32 * 86_400_000_000)
            & (pl.col("open_us") < end)
        )
        .select(columns)
        .collect(engine="streaming")
    )
    return bars, minutes


def _evaluate(model: dict, protocol: dict, data: tuple[pl.DataFrame, pl.DataFrame]) -> dict:
    from .backtest import BacktestConfig, baseline_targets, run_backtest

    bars, minutes = data
    start, end = date_us(protocol["holdout_start"]), date_us(protocol["holdout_end"])
    interval = model["interval"]
    features = build_features(bars.filter(pl.col("interval") == interval)).filter(
        (pl.col("available_us") >= start + protocol["embargo_bars"] * INTERVAL_US[interval])
        & (
            pl.col("available_us")
            < end
            - protocol["label_horizon_minutes"] * 60_000_000
            - protocol["embargo_bars"] * INTERVAL_US[interval]
        )
        & pl.all_horizontal([pl.col(name).is_not_null() for name in model["features"]])
    )
    if not features.height:
        raise ValueError("留出无完整因果特征")
    targets = predict_exported_model(model, features).select(
        "available_us", "symbol", "target_weight", "probability"
    )
    targets = pl.concat(
        [
            targets,
            _flat_targets(start, protocol["symbols"]),
            _flat_targets(end - INTERVAL_US["1h"], protocol["symbols"]),
        ]
    )
    base_config = BacktestConfig(start_us=start, end_us=end, liquidate_at_end=True)
    base = run_backtest(bars, minutes, targets, base_config)
    baseline_bars = bars.filter(pl.col("interval") == "1h")
    baseline_signals = baseline_targets(baseline_bars, "B2")
    resets = pl.concat(
        [
            _flat_targets(when, protocol["symbols"]).select(
                "available_us", "symbol", "target_weight"
            )
            for when in (start, end - INTERVAL_US["1h"])
        ]
    )
    baseline_signals = pl.concat(
        [
            baseline_signals.join(
                resets.select("available_us", "symbol"), on=["available_us", "symbol"], how="anti"
            ),
            resets,
        ]
    ).sort("available_us", "symbol")
    baseline = run_backtest(baseline_bars, minutes, baseline_signals, base_config)
    stress = {}
    for name, kwargs in (
        ("fee_x2", {"fee_multiplier": 2}),
        ("slippage_x2", {"slippage_multiplier": 2}),
    ):
        stress[name] = run_backtest(
            bars,
            minutes,
            targets,
            BacktestConfig(start_us=start, end_us=end, liquidate_at_end=True, **kwargs),
        ).summary
    fraction = quarter_profit_fraction(base.daily_nav, base_config.initial_cash)
    gates = evaluate_gates(base.summary, baseline.summary, stress, fraction, protocol["gates"])
    return {
        "summary": base.summary,
        "B2": baseline.summary,
        "stress": stress,
        "quarter_profit_fraction": fraction,
        "gates": gates,
        "excess_confidence": excess_bootstrap(
            base.daily_nav, baseline.daily_nav, **protocol["bootstrap"]
        ),
    }


def evaluate_holdout_once(
    development_report_path: str | Path,
    model_path: str | Path,
    protocol_path: str | Path,
    *,
    grant: HoldoutGrant,
    state_db: str | Path | None = None,
    engineering: bool = False,
    dataset_verifier: Callable | None = None,
    loader: Callable | None = None,
    evaluator: Callable | None = None,
) -> dict:
    """Consume before reading prices; no retry after crash/error/failed holdout.

    Custom data/evaluator injection is permitted only for engineering tests. This
    function is not an authorization source: a grant documents an explicit prior
    human/root instruction, whose validity remains the caller's responsibility.
    """
    report = json.loads(Path(development_report_path).read_text())
    _development_gate(report)
    if engineering and (
        state_db is None or any(item is None for item in (dataset_verifier, loader, evaluator))
    ):
        raise HoldoutDenied("工程验收必须显式注入合成数据、评估器和独立消费账本")
    if not engineering and any(item is not None for item in (dataset_verifier, loader, evaluator)):
        raise HoldoutDenied("真实留出不能注入模拟数据或替代评估器")
    model = json.loads(Path(model_path).read_text())
    protocol = json.loads(Path(protocol_path).read_text())
    model_sha, protocol_sha = canonical_hash(model), canonical_hash(protocol)
    if (
        model_sha != report["frozen_model_sha256"]
        or protocol_sha != report["protocol_sha256"]
        or model.get("protocol_sha256") != protocol_sha
        or model.get("interval") != report["selected_interval"]
    ):
        raise HoldoutDenied("冻结模型或协议与开发结果不符")
    if model.get("holdout_revealed") is not False:
        raise HoldoutDenied("模型已使用留出")
    start = date_us(protocol["holdout_start"])
    if any(
        model.get(name, start) >= start
        for name in ("training_last_available_us", "training_last_label_end_us")
    ):
        raise HoldoutDenied("训练时点或标签已跨入留出")
    if model.get("validation_end_us") != start:
        raise HoldoutDenied("冻结验证边界与留出边界不符")
    if (
        grant.model_sha256 != model_sha
        or grant.protocol_sha256 != protocol_sha
        or grant.dataset_id != report["dataset_id"]
        or not grant.authorized_by
        or not grant.reason
        or grant.confirmation != "one_frozen_candidate_once"
    ):
        raise HoldoutDenied("必须明确授权同一模型、协议和数据的单次揭晓")
    from .data import verify_dataset_lock

    lock = (dataset_verifier or verify_dataset_lock)()
    if engineering and not lock["dataset_id"].startswith(("synthetic-", "engineering-")):
        raise HoldoutDenied("工程验收不能消费真实锁定数据集")
    if lock["dataset_id"] != report["dataset_id"]:
        raise HoldoutDenied("锁定数据身份改变")
    if not engineering and (
        lock["holdout_start_utc"][:10] != protocol["holdout_start"]
        or lock["holdout_end_exclusive_utc"][:10] != protocol["holdout_end"]
    ):
        raise HoldoutDenied("冻结数据的留出边界改变")
    path = _native(state_db or STATE / "holdout.sqlite3")
    if not engineering and path != (STATE / "holdout.sqlite3").resolve():
        raise HoldoutDenied("真实留出仅能使用固定STATE/holdout.sqlite3消费真源")
    if engineering and path == (STATE / "holdout.sqlite3").resolve():
        raise HoldoutDenied("工程消费账本必须与真实留出账本隔离")
    from . import disk

    if not engineering:
        disk.check(reserve=100_000_000)
    ticket = {
        "grant": asdict(grant),
        "development_sha256": canonical_hash(report),
        "model_sha256": model_sha,
        "protocol_sha256": protocol_sha,
        "dataset_id": lock["dataset_id"],
        "engineering": engineering,
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    ticket_sha = canonical_hash(ticket)
    db = _open_journal(path)
    try:
        try:
            with db:
                db.execute(
                    "INSERT INTO attempts VALUES(?,?,?,?)",
                    (lock["dataset_id"], ticket_sha, utc_now_us(), _json(ticket)),
                )
        except sqlite3.IntegrityError:
            raise HoldoutDenied("同一锁定留出已消费；失败、未知或崩溃也不允许再揭晓") from None
        try:
            selected_protocol = {**protocol, "selected_interval": model["interval"]}
            data = (loader or _load_locked_data)(selected_protocol, lock)
            result = (evaluator or _evaluate)(model, protocol, data)
            passed = result["gates"]["development_passed"] is True
            status = "ENGINEERING_ONLY" if engineering else "PAPER_ELIGIBLE" if passed else "STOP"
            receipt = {
                "status": status,
                "ticket_sha256": ticket_sha,
                "model_sha256": model_sha,
                "protocol_sha256": protocol_sha,
                "dataset_id": lock["dataset_id"],
                "development_sha256": canonical_hash(report),
                "engineering": engineering,
                "holdout_revealed": True,
                "real_money_authorized": False,
                "result": result,
            }
        except Exception as error:
            receipt = {
                "status": "INVALID_RUN_CONSUMED",
                "ticket_sha256": ticket_sha,
                "model_sha256": model_sha,
                "protocol_sha256": protocol_sha,
                "dataset_id": lock["dataset_id"],
                "development_sha256": canonical_hash(report),
                "engineering": engineering,
                "holdout_revealed": True,
                "real_money_authorized": False,
                "error": f"{type(error).__name__}: {error}",
            }
        digest = canonical_hash(receipt)
        with db:
            db.execute(
                "INSERT INTO receipts VALUES(?,?,?,?)",
                (ticket_sha, utc_now_us(), digest, _json(receipt)),
            )
        return {**receipt, "receipt_sha256": digest, "state_db": str(path)}
    finally:
        db.close()


def verify_paper_release(receipt: dict, model: dict) -> None:
    """Verify a local immutable release receipt; no external signature is claimed."""
    if (
        receipt.get("status") != "PAPER_ELIGIBLE"
        or receipt.get("engineering") is not False
        or receipt.get("model_sha256") != canonical_hash(model)
        or receipt.get("protocol_sha256") != model.get("protocol_sha256")
    ):
        raise HoldoutDenied("没有同一冻结模型的真实单次留出通过凭证")
    path = _native(receipt["state_db"])
    if path != (STATE / "holdout.sqlite3").resolve():
        raise HoldoutDenied("真实准入只能来自固定留出消费账本，工程子库不能授权")
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        row = db.execute(
            "SELECT receipt_sha,receipt FROM receipts WHERE ticket_sha=?",
            (receipt["ticket_sha256"],),
        ).fetchone()
        if not row or row[0] != receipt["receipt_sha256"]:
            raise HoldoutDenied("准入凭证不存在或摘要不符")
        stored = json.loads(row[1])
        if canonical_hash(stored) != row[0] or stored != {
            name: value
            for name, value in receipt.items()
            if name not in {"receipt_sha256", "state_db"}
        }:
            raise HoldoutDenied("准入凭证被改变")
        attempt = db.execute(
            "SELECT dataset_id,ticket FROM attempts WHERE ticket_sha=?", (receipt["ticket_sha256"],)
        ).fetchone()
        if not attempt:
            raise HoldoutDenied("准入凭证没有原始消费票")
        ticket = json.loads(attempt[1])
        if (
            canonical_hash(ticket) != receipt["ticket_sha256"]
            or ticket.get("engineering") is not False
        ):
            raise HoldoutDenied("消费票被改变或来自工程模拟")
        for name in ("model_sha256", "protocol_sha256", "dataset_id", "development_sha256"):
            if ticket.get(name) != stored.get(name):
                raise HoldoutDenied("消费票与准入的数据/模型/协议/开发结果绑定不符")
        if attempt[0] != stored["dataset_id"]:
            raise HoldoutDenied("原始dataset唯一票身份不符")
        grant = ticket.get("grant", {})
        if (
            any(
                grant.get(name) != stored.get(name)
                for name in ("model_sha256", "protocol_sha256", "dataset_id")
            )
            or not grant.get("authorized_by")
            or not grant.get("reason")
            or grant.get("confirmation") != "one_frozen_candidate_once"
        ):
            raise HoldoutDenied("原始单次授权绑定不符")
        gates = stored.get("result", {}).get("gates", {})
        checks = gates.get("checks", {})
        if (
            gates.get("development_passed") is not True
            or gates.get("status") != "HOLDOUT_REQUIRED"
            or not checks
            or any(value is not True for value in checks.values())
        ):
            raise HoldoutDenied("原始留出绩效门槛并未全部通过")
        triggers = {
            name: sql
            for name, sql in db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")
        }
        for table in ("attempts", "receipts"):
            for action in ("update", "delete"):
                sql = triggers.get(f"{table}_no_{action}", "")
                if f"BEFORE {action.upper()} ON {table}" not in sql or "RAISE(ABORT" not in sql:
                    raise HoldoutDenied("准入账本缺少不可改写触发器")
    finally:
        db.close()
