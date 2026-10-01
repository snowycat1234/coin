"""A thin stdlib copy of byte-bound shards to a bounded D-WSL working snapshot."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

from quant import disk
from quant.paths import STATE

from .trade_flow_v2 import checksum, require, validate_request


def native_shard_snapshot(shards, directory):
    """Keep immutable original receipts; use at most 1 GB temporary fold inputs."""
    directory = Path(directory).resolve()
    require(
        directory.is_relative_to(STATE.resolve()) and not directory.exists(),
        "Exclusive task-owned native STATE snapshot required",
    )
    for source in shards:
        validate_request(source.market, source.symbol, source.day)
    total = sum(source.path.stat().st_size for source in shards)
    require(0 < total <= 1_000_000_000, "Native working-input budget exceeded")
    ledger = disk.check(reserve=total + 25_000_000)
    directory.mkdir()
    result, bindings = [], []
    for source in shards:
        path = directory / f"{source.market}-{source.symbol}-{source.day}.parquet"
        require(
            not path.exists() and checksum(source.path) == source.sha256,
            "Original immutable shard changed or duplicate copy target",
        )
        shutil.copy2(source.path, path)
        require(checksum(path) == source.sha256, "Native input SHA differs")
        result.append(replace(source, path=path))
        bindings.append(
            {
                "original": str(source.path),
                "native": str(path),
                "sha256": source.sha256,
                "bytes": path.stat().st_size,
            }
        )
    with (directory / "SOURCE_SNAPSHOT.json").open("x") as writer:
        writer.write(
            json.dumps(
                {
                    "status": "BYTE_EXACT_NATIVE_WORKING_INPUT_SNAPSHOT",
                    "bytes": total,
                    "temporary_working_budget_bytes": 1_000_000_000,
                    "ledger_before_copy": ledger,
                    "files": bindings,
                },
                indent=2,
            )
            + "\n"
        )
    return result
