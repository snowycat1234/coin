"""Read-only binding of a completed fine run before any cold/report claim."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_completed_run(state: Path, module: Path, plan: dict) -> list[str]:
    ids = [f"{case['case_id']}_FINE_{mode}"
           for case in plan["cases"] for mode in plan["modes"]]
    if len(ids) != 12 or len(set(ids)) != 12:
        raise ValueError("Expected exactly twelve distinct predeclared fine cases")
    binding = json.loads((state / "RUN_BINDING.json").read_text())
    expected = {
        "parent_GO": True,
        "runner_SHA256": sha(module / "run_cases.py"),
        "bindings_SHA256": sha(module / "CASE_BINDINGS.json"),
        "fine_account_SHA256": sha(module / "fine_account.py"),
        "freeze_manifest_SHA256": sha(module / "FROZEN_CODE.json"),
        "fine_profile_SHA256": plan["fine_profile_SHA256"],
        "coarse_profile_SHA256": plan["coarse_profile_SHA256"],
        "fine_case_ids": ids,
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            raise ValueError(f"Fine RUN_BINDING differs: {key}")
    nonce = binding.get("nonce")
    if not isinstance(nonce, str) or len(nonce) != 32:
        raise ValueError("Fine RUN_BINDING nonce absent")
    controller = json.loads((state / "RESOURCE_RECEIPTS.json").read_text())
    if (controller.get("status") != "ALL_CASES_FINISHED"
            or controller.get("unstarted_case_ids") != []
            or set(controller.get("per_case", {})) != set(ids)):
        raise ValueError("Fine controller does not attest all twelve fixed cases")
    for identity, row in controller["per_case"].items():
        if (row.get("exit_code") != 0 or row.get("stop_reason") is not None
                or not isinstance(row.get("peak_RSS"), int)
                or row["peak_RSS"] < 0 or row["peak_RSS"] > 2_000_000_000):
            raise ValueError(f"Fine worker lacks clean bounded completion: {identity}")
    return ids
