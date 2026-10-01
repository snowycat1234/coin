"""Independent short congestion diagnostic; never substitutes for full acceptance."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from measure_candidate_adapter_v3 import attempt_probe, digest, load_fixture, runtime_snapshot

from quant import disk
from quant.paths import ROOT, STATE
from quant.resources import status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source, folder, output = (value.resolve() for value in (
        args.source, args.directory, args.output
    ))
    if (not source.is_relative_to(STATE.resolve())
            or not source.parent.name.startswith("a03-capacity-")
            or not folder.is_relative_to(STATE.resolve())
            or not folder.name.startswith("a03-capacity-")
            or folder.exists() or output.exists()
            or not output.is_relative_to((ROOT / "reports").resolve())):
        raise ValueError("Use independent engineering paths; preserve previous evidence")
    started = time.monotonic()
    paths = (Path(__file__), ROOT / "scripts/measure_candidate_adapter_v3.py",
             ROOT / "tests/test_candidate_adapter.py", ROOT / "src/quant/candidate_paper.py",
             ROOT / "src/quant/candidate_strategy.py")
    before = {str(path.relative_to(ROOT)): digest(path) for path in paths}
    runtime = runtime_snapshot()
    ledger = disk.check(reserve=50_000_000)
    try:
        result = attempt_probe(load_fixture(), source, folder, ledger)
    except Exception as exc:
        failure = {
            "status": "CONGESTION_FIXTURE_FAILED_NOT_ACCEPTED",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "error_type": type(exc).__name__,
            "failure": exc.args[0] if isinstance(exc, AssertionError) else str(exc),
            "source_hashes": before, "native_runtime_snapshot": runtime,
            "resources": status(), "baseline_disk": ledger,
            "capacity_accepted": False, "production_authorized": False,
        }
        with output.open("x", encoding="utf-8") as writer:
            writer.write(json.dumps(failure, indent=2, allow_nan=False) + "\n")
        raise
    if before != {str(path.relative_to(ROOT)): digest(path) for path in paths}:
        raise RuntimeError("Sources changed while measuring")
    if runtime != runtime_snapshot():
        raise RuntimeError("Runtime changed while measuring")
    document = {
        "status": "SHORT_CONGESTION_ENGINEERING_DIAGNOSTIC_ONLY",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "probe": result, "source_hashes": before, "native_runtime_snapshot": runtime,
        "resources": status(), "baseline_disk": ledger,
        "elapsed_seconds": time.monotonic() - started,
        "capacity_accepted": False, "production_authorized": False,
        "training_fits": 0, "network_requests": 0, "actual_qualification_days": 0,
    }
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(document, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": document["status"],
                      "attempts": result["attempts"],
                      "increment_bytes": result["increment_bytes"],
                      "elapsed_seconds": document["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
