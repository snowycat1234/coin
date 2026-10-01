"""Operator entry points; real evidence is checked before looking up credentials."""

from __future__ import annotations

import asyncio
import math
import os
from pathlib import Path

from .paths import ROOT, STATE


def add_commands(sub) -> None:
    status = sub.add_parser("testnet-status", help="Read and audit the persistent Testnet ledger")
    status.add_argument("--execution-db", default=str(STATE / "testnet-execution.sqlite3"))
    for name in ("testnet-preflight", "testnet-run", "testnet-resume"):
        parser = sub.add_parser(name, help="Verified Spot Testnet only; default STOP")
        parser.add_argument("--development",
                            default=str(ROOT / "reports/generated/P04/summary.json"))
        for field in ("model", "protocol", "release", "collector-db", "paper-db", "version"):
            parser.add_argument("--" + field)
        if name != "testnet-preflight":
            parser.add_argument("--enable-testnet", action="store_true")
            parser.add_argument("--authorization", default="")
            parser.add_argument("--execution-db", default=str(STATE / "testnet-execution.sqlite3"))
            parser.add_argument("--seconds", type=float)


def _path(value: str | None) -> Path | None:
    return Path(value) if value else None


def _credentials() -> tuple[str, str]:
    # Never called during preflight or before every real prerequisite passes.
    return os.environ["QUANT_TESTNET_API_KEY"], os.environ["QUANT_TESTNET_API_SECRET"]


def run_command(args) -> dict:
    from .testnet_runtime import EvidenceBundle, EvidenceVerifier, RuntimeConfig, TestnetRuntime

    if args.command == "testnet-status":
        from .testnet_runtime import read_runtime_status

        return read_runtime_status(Path(args.execution_db))
    bundle = EvidenceBundle(
        development_path=_path(args.development), model_path=_path(args.model),
        protocol_path=_path(args.protocol), release_path=_path(args.release),
        collector_db=_path(args.collector_db), paper_db=_path(args.paper_db), version=args.version)
    if args.command == "testnet-preflight":
        return EvidenceVerifier(bundle).verify()
    if args.seconds is not None and (not math.isfinite(args.seconds) or args.seconds < 0):
        return {"state": "STOP", "reasons": ["INVALID_DURATION"], "credentials_loaded": False,
                "network_enabled": False, "real_money_authorized": False}

    async def execute() -> dict:
        runtime = TestnetRuntime(
            bundle, config=RuntimeConfig(
                enable_testnet=args.enable_testnet, authorization=args.authorization,
                db_path=Path(args.execution_db)), credential_loader=_credentials)
        try:
            operation = runtime.resume if args.command == "testnet-resume" else runtime.run
            result = await operation(run_seconds=args.seconds)
            return {**result, "command_returned": True, "runtime_active": False}
        finally:
            await runtime.close()

    return asyncio.run(execute())
