"""Explicit candidate commands; development admission precedes every later input."""

from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path

from .paths import ROOT, STATE


class CommandDenied(ValueError):
    pass


def _preflight(path: str | Path) -> None:
    from .holdout import _development_gate

    _development_gate(json.loads(Path(path).read_text()))


def _required(value: str | None, label: str) -> Path:
    if not value:
        raise CommandDenied(f"准入后仍须明确提供{label}")
    return Path(value)


def holdout_command(args) -> dict:
    """A grant records existing authorization; the CLI cannot create that authority."""
    _preflight(args.development)
    model = _required(args.model, "冻结模型")
    protocol = _required(args.protocol, "登记协议")
    grant_path = _required(args.grant, "单次揭晓授权记录")
    destination = Path(args.output).resolve()
    if not destination.is_relative_to(ROOT.resolve()):
        raise CommandDenied("准入报告必须留在D盘项目目录")
    if destination.exists():
        raise CommandDenied("禁止覆盖已有留出报告")
    from .holdout import HoldoutGrant, evaluate_holdout_once

    grant = HoldoutGrant(**json.loads(grant_path.read_text()))

    result = evaluate_holdout_once(args.development, model, protocol, grant=grant)
    # Consumption and its immutable receipt are already durable inside native STATE.
    # Report export failure cannot authorize a second reveal.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return {"status": result["status"], "receipt": str(destination),
            "ticket_sha256": result["ticket_sha256"], "real_money_authorized": False}


def candidate_command(args) -> dict:
    _preflight(args.development)
    model = _required(args.model, "冻结模型")
    release_path = _required(args.release, "真实一次留出通过凭证")
    if args.seconds is not None and (not math.isfinite(args.seconds) or args.seconds <= 0):
        raise CommandDenied("运行时长必须大于0")
    from .candidate_paper import create_candidate_pipeline

    runner = create_candidate_pipeline(
        args.development, model, release=json.loads(release_path.read_text()),
        collector_db=args.collector_db, candidate_db=args.account_db)
    try:
        return asyncio.run(runner.run(args.seconds))
    finally:
        if runner.candidate is not None:
            runner.candidate.close()
        runner.close()


def candidate_report_command(args) -> dict:
    source = Path(args.account_db).resolve()
    if not source.is_relative_to(STATE.resolve()):
        raise CommandDenied("候选评估须读取D盘WSL native STATE账本")
    from .forward_report import read_forward_report, write_forward_report

    result = read_forward_report(source, expected_version=args.version)
    write_forward_report(result, args.output)
    return result


def add_commands(sub) -> None:
    holdout = sub.add_parser("holdout", help="One authorized reveal for an admitted frozen model")
    candidate = sub.add_parser("candidate-paper", help="Admitted candidate, public data only")
    for parser in (holdout, candidate):
        parser.add_argument(
            "--development", default=str(ROOT / "reports/generated/P04/summary.json"))
        parser.add_argument("--model")
    holdout.add_argument("--protocol")
    holdout.add_argument("--grant")
    holdout.add_argument("--output", default=str(ROOT / "reports/generated/HOLDOUT/receipt.json"))
    candidate.add_argument("--release")
    candidate.add_argument("--collector-db", default=str(STATE / "candidate_live.sqlite3"))
    candidate.add_argument("--account-db", default=str(STATE / "candidate_paper.sqlite3"))
    candidate.add_argument("--seconds", type=float)
    report = sub.add_parser(
        "candidate-report", help="Read the candidate journal without writing it")
    report.add_argument("--account-db", default=str(STATE / "candidate_paper.sqlite3"))
    report.add_argument("--version")
    report.add_argument("--output", default=str(ROOT / "reports/generated/P06_CANDIDATE"))


def run_command(args) -> dict:
    from .holdout import HoldoutDenied

    try:
        if args.command == "candidate-report":
            return candidate_report_command(args)
        return holdout_command(args) if args.command == "holdout" else candidate_command(args)
    except (HoldoutDenied, CommandDenied) as error:
        return {"status": "DENIED", "command": args.command, "reason": str(error),
                "real_money_authorized": False}
