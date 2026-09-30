"""Read-only P06 evidence checks. Historical/synthetic records never earn elapsed days."""

from __future__ import annotations

import calendar
import hashlib
import json
import math
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from .metrics import block_bootstrap_mean_ci, daily_metrics

DAY_US = 86_400_000_000
ZERO_HASH = "0" * 64
SCENARIOS = ("candidate", "B2", "fee_x2", "slippage_x2")


class EvidenceIntegrityError(ValueError):
    """Signed evidence is malformed, changed, or internally contradictory."""


def record_digest(record: dict[str, Any]) -> str:
    body = {name: record[name] for name in (
        "seq", "received_us", "version", "kind", "payload", "prev_hash")}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_record_chain(records: list[dict[str, Any]], head_hash: str | None) -> str:
    previous = ZERO_HASH
    for expected_seq, record in enumerate(records, start=1):
        try:
            if record["seq"] != expected_seq or record["prev_hash"] != previous:
                raise EvidenceIntegrityError("链序号或前序哈希断裂")
            if not isinstance(record["received_us"], int) or record["received_us"] < 0:
                raise EvidenceIntegrityError("真实收到时刻无效")
            if record_digest(record) != record["hash"]:
                raise EvidenceIntegrityError("记录内容与哈希不符，证据可能已改写")
            previous = record["hash"]
        except (KeyError, TypeError, OverflowError) as error:
            raise EvidenceIntegrityError(f"链记录合同错误：{error}") from error
    if head_hash is not None and previous != head_hash:
        raise EvidenceIntegrityError("记录尾哈希与保存锚不符")
    return previous


def _base_report(version: str | None) -> dict[str, Any]:
    return {"module": "P06", "version": version, "status": "INSUFFICIENT_EVIDENCE",
            "champion": False, "real_money_authorized": False,
            "reasons": [], "failed_checks": [], "metrics": {},
            "minimum_real_elapsed_days": 180,
            "testnet": "未由本报告验证；独立的真实30天测试环境与凭证门槛仍适用",
            "integrity_scope": "本地append-only触发器和SHA-256链审计；没有外部签名认证"}


def _utc_date(timestamp: int) -> date:
    return datetime.fromtimestamp(timestamp / 1_000_000, UTC).date()


def _day_end_us(day: date) -> int:
    return int(datetime.combine(day + timedelta(days=1), datetime.min.time(), UTC)
               .timestamp() * 1_000_000)


def _nav_frames(records: list[dict], first_us: int,
                allowed_source: str = "live") -> tuple[dict[str, pl.DataFrame], list[str], dict]:
    rows: dict[str, list[dict]] = {scenario: [] for scenario in SCENARIOS}
    opening_nav = {}
    rejected = []
    for record in records:
        if record["kind"] != "nav":
            continue
        payload = record["payload"]
        scenario = payload.get("scenario")
        if scenario not in rows:
            continue
        if payload.get("source") != allowed_source:
            rejected.append(f"{scenario} 存在非live日记录，不能累计前向证据")
            continue
        try:
            day = date.fromisoformat(payload["date"])
            end = _day_end_us(day)
            # Late reconstructions and history imports cannot create daily observations.
            if day < _utc_date(first_us) or not end <= record["received_us"] <= end + 300_000_000:
                rejected.append(f"{scenario}/{day} 日记录不是及时真实前向观察")
                continue
            if payload.get("timely_recorded") is False or payload.get("observation_status") == \
                    "MISSED_WHILE_STOPPED":
                rejected.append(f"{scenario}/{day} 明确记录为停机后迟到重构")
                continue
            numbers = {name: float(payload[name]) for name in
                       ("nav", "fees", "execution_costs", "turnover")}
            if not all(math.isfinite(value) for value in numbers.values()):
                raise EvidenceIntegrityError("日NAV或成本含非有限数")
            if numbers["nav"] <= 0 or any(numbers[name] < 0 for name in
                                          ("fees", "execution_costs", "turnover")):
                raise EvidenceIntegrityError("日NAV或成本无效")
            if "stale_exposure" not in payload or "daily_risk_observable" not in payload:
                rejected.append(f"{scenario}/{day} 缺少持仓估值可观察性")
                continue
            if payload.get("complete_utc_day") is not True:
                partial_start = day == _utc_date(first_us) and first_us % DAY_US != 0
                if payload.get("complete_utc_day") is False and partial_start:
                    if payload["stale_exposure"] or not payload["daily_risk_observable"]:
                        rejected.append(f"{scenario}/{day} 首个部分日的窗口起始NAV不可观察")
                    else:
                        opening_nav[scenario] = numbers["nav"]
                    continue
                rejected.append(f"{scenario}/{day} 不是可验证的完整UTC日")
                continue
            rows[scenario].append({"date": day, **numbers,
                                   "stale_exposure": bool(payload["stale_exposure"]),
                                   "daily_risk_observable": bool(payload["daily_risk_observable"]),
                                   "received_us": record["received_us"]})
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, EvidenceIntegrityError):
                raise
            raise EvidenceIntegrityError(f"日记录合同错误：{error}") from error
    frames = {}
    for scenario, observations in rows.items():
        if not observations:
            continue
        frame = pl.DataFrame(observations).sort("date")
        if frame["date"].n_unique() != frame.height:
            raise EvidenceIntegrityError(f"{scenario} 同一UTC日存在重复或重写NAV")
        frames[scenario] = frame
    return frames, sorted(set(rejected)), opening_nav


def _complete_positive_months(frame: pl.DataFrame, initial_nav: float,
                              first_us: int) -> tuple[int, list[dict]]:
    periods: dict[str, dict] = {}
    previous = initial_nav
    for day, nav in frame.select("date", "nav").iter_rows():
        key = day.isoformat()[:7]
        month = periods.setdefault(key, {"month": key, "start_nav": previous,
                                         "end_nav": nav, "days": 0})
        month["end_nav"] = nav
        month["days"] += 1
        previous = nav
    result = []
    first_day = _utc_date(first_us)
    for key, month in periods.items():
        year, number = map(int, key.split("-"))
        full = month["days"] == calendar.monthrange(year, number)[1]
        # A partial first live UTC day cannot qualify a completed calendar month.
        if first_day.year == year and first_day.month == number:
            full = full and first_us == int(datetime(year, number, 1, tzinfo=UTC)
                                            .timestamp() * 1_000_000)
        result.append({**month, "return": month["end_nav"] / month["start_nav"] - 1,
                       "complete_calendar_month": full})
    return sum(row["complete_calendar_month"] and row["return"] > 0
               for row in result), result


def evaluate_forward_records(records: list[dict[str, Any]], *, head_hash: str | None,
                             triggers_verified: bool,
                             expected_version: str | None = None) -> dict[str, Any]:
    """Evaluate an immutable snapshot, not runtime counters or a replay backtest."""
    report = _base_report(expected_version)
    try:
        report["head_hash"] = verify_record_chain(records, head_hash)
    except (EvidenceIntegrityError, ValueError) as error:
        report.update(status="FAIL", reasons=[str(error)], failed_checks=["record_integrity"])
        return report
    if not records:
        report["reasons"] = ["没有冻结候选的真实前向记录"]
        return report
    if not triggers_verified or head_hash is None:
        report["reasons"].append("缺少append-only触发器或尾哈希审计证据")
    candidate_starts = [record for record in records if record["kind"] == "start" and
                        record["payload"].get("role") == "candidate" and
                        (expected_version is None or record["version"] == expected_version)]
    versions = {record["version"] for record in candidate_starts}
    if not candidate_starts:
        report["reasons"].append("只有行情或B0/B2参考记录，未找到冻结盈利候选")
        return report
    if len(versions) != 1:
        report["reasons"].append("存在多个候选版本，必须明确指定同一冻结版本")
        return report
    version = candidate_starts[0]["version"]
    report["version"] = version
    selected = [record for record in records if record["version"] == version]
    start = candidate_starts[0]
    payload = start["payload"]
    if len(candidate_starts) != 1:
        report.update(status="FAIL", reasons=["同一冻结候选重复启动起算，证据合同不明确"],
                      failed_checks=["frozen_version_start"])
        return report
    engineering = payload.get("mode") != "live_paper" or payload.get("source") != "live"
    report["evidence_mode"] = payload.get("mode")
    if engineering:
        report["reasons"].append("合成、回放或回补资料不能计入真实180天")
    incidents = [record for record in selected if record["kind"] == "incident"]
    report["incident_count"] = len(incidents)
    if incidents:
        report.update(status="FAIL", reasons=["冻结版本出现事故，事故数必须为0"],
                      failed_checks=["zero_incidents"])
        return report
    if payload.get("qualified_72h_at_start") is not True:
        report["reasons"].append("没有开始前真实72小时采集资格凭证")
    try:
        initial_nav = float(payload["initial_cash"])
        if not math.isfinite(initial_nav) or initial_nav <= 0:
            raise EvidenceIntegrityError("初始NAV无效")
        frames, rejected, opening_nav = _nav_frames(
            selected, start["received_us"],
            allowed_source="synthetic" if engineering else "live")
    except (EvidenceIntegrityError, KeyError, TypeError, ValueError) as error:
        report.update(status="FAIL", reasons=[str(error)], failed_checks=["nav_integrity"])
        return report
    report["reasons"].extend(rejected)
    missing = [scenario for scenario in SCENARIOS if scenario not in frames]
    report["missing_scenarios"] = missing
    if missing:
        report["reasons"].append("缺少真实同版本日NAV：" + ", ".join(missing))
    candidate = frames.get("candidate")
    if candidate is None:
        return report
    first_us = start["received_us"]
    last_us = int(candidate["received_us"].max())
    elapsed_days = (last_us - first_us) / DAY_US if not engineering else 0.0
    report.update(first_received_us=first_us, last_received_us=last_us,
                  actual_elapsed_days=elapsed_days, daily_observations=candidate.height)
    if engineering:
        report["engineering_span_days"] = (last_us - first_us) / DAY_US
    if elapsed_days < 180:
        report["reasons"].append(f"真实同版本首尾仅{elapsed_days:.4f}天，尚不足180天")
    if candidate.height < 180:
        report["reasons"].append("完整UTC日NAV不足180条，部分首日不计完整日")
    window_first = _utc_date(first_us) + timedelta(days=int(first_us % DAY_US != 0))
    expected_dates = {day for day in (
        window_first + timedelta(days=index)
        for index in range((candidate["date"][-1] - window_first).days + 1))}
    candidate_dates = set(candidate["date"].to_list())
    if candidate_dates != expected_dates:
        report["reasons"].append("候选日度记录不连续，缺失日期不能补造")
    for scenario, frame in frames.items():
        if set(frame["date"].to_list()) != candidate_dates:
            report["reasons"].append(f"{scenario} 与候选并非相同完整UTC日期区间")
        if first_us % DAY_US and scenario not in opening_nav:
            report["reasons"].append(f"{scenario} 缺少首个完整日窗口的已观察起始NAV")
    report["reasons"] = list(dict.fromkeys(report["reasons"]))
    if report["reasons"]:
        return report
    # Only a fully evidenced 180-day experiment is evaluated against performance gates.
    initial_by_scenario = {scenario: opening_nav.get(scenario, initial_nav) for scenario in frames}
    summaries = {scenario: daily_metrics(frame, initial_by_scenario[scenario])
                 for scenario, frame in frames.items()}
    positive_months, monthly = _complete_positive_months(
        candidate, initial_by_scenario["candidate"], first_us)
    cycles = [record["payload"].get("cycle_id") for record in selected
              if record["kind"] == "round_trip" and
              record["payload"].get("scenario") == "candidate"]
    if any(cycle is None for cycle in cycles) or len(cycles) != len(set(cycles)):
        report.update(status="FAIL", reasons=["已闭合周期标识缺失或重复"],
                      failed_checks=["round_trip_integrity"])
        return report
    nav = candidate["nav"].to_numpy()
    baseline_nav = frames["B2"]["nav"].to_numpy()
    candidate_returns = nav / np.r_[initial_by_scenario["candidate"], nav[:-1]] - 1
    baseline_returns = baseline_nav / np.r_[initial_by_scenario["B2"], baseline_nav[:-1]] - 1
    low, high = block_bootstrap_mean_ci(candidate_returns - baseline_returns)
    checks = {
        "positive_net_return": summaries["candidate"]["total_return"] > 0,
        "daily_sharpe_at_least_1": summaries["candidate"]["sharpe"] >= 1,
        "daily_drawdown_at_most_12pct": summaries["candidate"]["max_drawdown"] <= .12,
        "daily_risk_observable": all(frame["daily_risk_observable"].all() and
                                     not frame["stale_exposure"].any()
                                     for frame in frames.values()),
        "four_complete_positive_months": positive_months >= 4,
        "fee_x2_nonnegative": summaries["fee_x2"]["total_return"] >= 0,
        "slippage_x2_nonnegative": summaries["slippage_x2"]["total_return"] >= 0,
        "exceed_same_period_B2": summaries["candidate"]["total_return"] >
        summaries["B2"]["total_return"],
        "thirty_closed_independent_cycles": len(cycles) >= 30,
        "paired_excess_CI_lower_positive": low > 0,
        "zero_incidents": True,
    }
    report.update(checks=checks, metrics=summaries, monthly=monthly,
                  complete_positive_months=positive_months, round_trip_count=len(cycles),
                  excess_CI_95_daily_mean=[low, high],
                  excess_CI_95_annual_mean=[low * 365, high * 365],
                  CI_method="paired circular 7-day block bootstrap, 2000 samples, seed 20260930",
                  failed_checks=[name for name, passed in checks.items() if not passed])
    report["status"] = "PASS" if all(checks.values()) else "FAIL"
    report["champion"] = report["status"] == "PASS"
    if report["failed_checks"]:
        report["reasons"] = ["完整证据下未通过门槛：" + ", ".join(report["failed_checks"])]
    return report


def evaluate_forward_snapshot(snapshot: dict[str, Any],
                              expected_version: str | None = None) -> dict[str, Any]:
    """Consume the paper module's independently closed, read-only SQLite snapshot."""
    return evaluate_forward_records(snapshot.get("records", []),
                                    head_hash=snapshot.get("head_hash"),
                                    triggers_verified=snapshot.get("triggers_verified", False),
                                    expected_version=expected_version)


def read_forward_report(db_path: str | Path,
                        expected_version: str | None = None) -> dict[str, Any]:
    """Read the whole shadow chain before selecting a version; never open a writer."""
    from .shadow import read_forward_evidence

    db_path = Path(db_path)
    if not db_path.exists():
        report = _base_report(expected_version)
        report["reasons"] = ["前向策略账本尚不存在，不能用行情库或回测替代"]
        return report
    try:
        snapshot = read_forward_evidence(db_path)
    except RuntimeError as error:
        report = _base_report(expected_version)
        report.update(status="FAIL", reasons=[f"前向账本审计失败：{error}"],
                      failed_checks=["record_integrity"])
        return report
    return evaluate_forward_snapshot(snapshot, expected_version)


def format_forward_report(report: dict[str, Any]) -> str:
    lines = ["# P06 前向竞争性记录验收", "",
             f"状态：**{report['status']}**；版本：{report.get('version') or '无候选'}。", "",
             "B0/B2 仅为参考记录，采集时长、回补和工程回放不能成为盈利候选资格。",
             "本报告不授权真钱；独立真实30天测试环境及用户批准仍为后续门槛。", ""]
    if "actual_elapsed_days" in report:
        lines.append(f"真实同版本首尾 {report['actual_elapsed_days']:.4f} 天；"
                     f"UTC 日记录 {report['daily_observations']} 条。")
        lines.append("")
    for reason in report["reasons"]:
        lines.append(f"- {reason}")
    if report["metrics"]:
        lines.extend(["", "| 情景 | 净收益 | 日度 Sharpe | 观察日度最大回撤 |",
                      "|---|---:|---:|---:|"])
        for scenario, metrics in report["metrics"].items():
            lines.append(f"| {scenario} | {metrics['total_return']:.4%} | "
                         f"{metrics['sharpe']:.4f} | {metrics['max_drawdown']:.4%} |")
        lines.extend(["", f"已闭合独立周期：{report['round_trip_count']}；"
                      f"完整正收益月：{report['complete_positive_months']}。",
                      f"超额年化日均收益95%区间：{report['excess_CI_95_annual_mean']}。"])
    lines.extend(["", "资料缺失保持证据不足，不以0替代压力收益，不缩短180天。",
                  "统计以UTC日度NAV和365日年化为依据，不证明日内风险或未来盈利。", ""])
    return "\n".join(lines)


def write_forward_report(report: dict[str, Any], output_dir: str | Path) -> Path:
    """Write an artifact; the evidence database is never opened for writing."""
    from .disk import check

    output_dir = Path(output_dir).resolve()
    if not str(output_dir).startswith("/mnt/d/"):
        raise ValueError("Forward reports must stay on D: via /mnt/d")
    payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    markdown = format_forward_report(report)
    check(reserve=len(payload.encode()) + len(markdown.encode()) + 16_384)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(payload + "\n")
    path = output_dir / "REPORT.md"
    path.write_text(markdown)
    return path
