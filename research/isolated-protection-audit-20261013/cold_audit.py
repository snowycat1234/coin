"""Read-only, zero-advance audit of the preregistered 11 guard wallets.

Each invocation audits exactly one completed case, independently reopening every
lossless day chunk and the final state snapshot. It writes its receipt only into
this separate audit directory; original wallet states are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent
RUNNER = WORKSPACE / "coin_margin_protective_runner_20261013/run_guard_cases.py"
STATE = WORKSPACE / "coin_margin_protective_runner_20261013/state_20261013"
BASELINES = WORKSPACE / "new_coin_guard_baseline_identity_20261013/BASELINE_IDENTITY.json"
EXPECTED_RUNNER_SHA = "b5e8a6ebd54e790066861da5c05d0c193175d965ceb75995779d70b2fe8c27a6"
EXPECTED_BASELINES_SHA = "407973d261dc441360f86acd70b162d83190487082009030726587e7bc44f794"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def same(a, b, label):
    if a != b:
        raise ValueError(f"Cold audit mismatch: {label}")


def main(case_id: str):
    if sys.flags.optimize:
        raise RuntimeError("Python assertions must remain enabled for frozen restoration")
    same(sha(RUNNER), EXPECTED_RUNNER_SHA, "reviewed runner bytes")
    same(sha(BASELINES), EXPECTED_BASELINES_SHA, "baseline identity appendix bytes")
    spec = importlib.util.spec_from_file_location("reviewed_guard_runner", RUNNER)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    manifest = runner.verify_published_policy()
    case = next((c for c in manifest["cases"] if c["case_id"] == case_id), None)
    if case is None:
        raise ValueError("Case not in frozen eleven-case manifest")
    baseline = next(c for c in json.loads(BASELINES.read_text())["cases"]
                    if c["case_id"] == case_id)
    state = STATE / case_id
    binding = json.loads((state / "BINDING.json").read_text())
    saved = json.loads((state / "ACCOUNT.json").read_text())
    result = json.loads((state / "RESULT.json").read_text())
    minute_numeric = json.loads((state / "MINUTE_NUMERIC.json").read_text())
    same(binding["case_id"], case_id, "binding case")
    for key, case_key in (("source_index_SHA256", "source_index_SHA256"),
                          ("target_archive_SHA256", "target_archive_SHA256"),
                          ("target_array_SHA256", "target_array_SHA256")):
        same(binding[key], case[case_key], f"binding {key}")
        baseline_key = key if key == "source_index_SHA256" else "guard_" + key
        same(binding[key], baseline[baseline_key], f"baseline {key}")
    same(binding["calendar"], case["calendar"], "manifest calendar")
    same(binding["calendar"], baseline["calendar_us"], "baseline calendar")
    same(result["case_id"], case_id, "result case")
    port, source, Simulator = runner.load_port(case["year"])
    same([source["start"], source["end"]], case["calendar"], "source calendar")
    same(binding["account_class"], port.Closing.VERSION, "account class")
    same(binding["quantity_profile_SHA256"], port.profile_sha(), "quantity profile")

    # The original lossless codec verifies snapshot SHA and every day-NPZ SHA,
    # shape, dtype, finiteness, row count, and exact frozen binding.
    snapshot, pointer = port.restore_snapshot(state / "recovery", binding)
    same(pointer["binding"], binding, "checkpoint binding")
    same(sha(state / "recovery" / pointer["snapshot_path"]), pointer["snapshot_SHA256"],
         "snapshot digest")
    same(sum(row["rows"] for row in pointer["chunks"]), pointer["completed_minutes"],
         "checkpoint rows")

    # Explicitly forbid any new financial advances, even indirectly. A
    # restored simulator may inspect its already-advanced tape to cursor.
    original_advance = Simulator.advance_day
    def forbidden_advance(*args, **kwargs):
        raise RuntimeError("Cold audit must not advance financial history")
    Simulator.advance_day = forbidden_advance
    try:
        sim = Simulator.from_snapshot(snapshot, source, account_class=port.Closing)
        same(sim.state_hash(), pointer["state_hash"], "restored state hash")
        same(sim.state_hash(), result["genuine_state_hash"], "result state hash")
        same(sim.cursor, pointer["cursor"], "restored cursor")
        same(sim.stop, pointer["stop"], "restored stop")
        same(sim.rows_written, pointer["completed_minutes"], "restored minutes")
        output = sim.result()
    finally:
        Simulator.advance_day = original_advance
    same(output["summary"], saved["summary"], "account summary")
    same(output["summary"], result["summary"], "result summary")
    same(output["protective_policy"], saved["protective_policy"], "account guard journal")
    same(output["protective_policy"], result["protective_policy"], "result guard journal")
    for key in ("trades", "funding", "rejections", "breaches", "extrema", "target_meta"):
        same(output[key], saved[key], f"account {key}")
    same(output["targets"].to_dicts(), saved["targets"], "actual executed targets")
    same(output.get("liquidations", []), saved["liquidations"], "liquidation journal")
    same(port.fingerprint(output["minute"]), minute_numeric["columns"],
         "all numeric minute column bytes")
    same(output["minute"].height, result["summary"]["completed_minutes"], "minute rows")
    expected_minutes = (source["end"] - source["start"]) // 60_000_000
    status, full, paid = runner.classify_result(output["summary"], expected_minutes)
    same(result["status"], status, "result status classification")
    same(result["full_calendar"], full, "full calendar classification")
    same(result["paid_flat"], paid, "paid flat classification")
    same(result["paid_cash_PnL_USDT"], output["summary"]["net_PnL"] if paid else None,
         "paid net only if full and flat")

    receipt = {
        "case_id": case_id, "cold_restored": True, "financial_advances": 0,
        "day_chunks_sha_verified": len(pointer["chunks"]),
        "minute_rows_sha_verified": output["minute"].height,
        "minute_columns_sha_verified": len(minute_numeric["columns"]),
        "all_journals_equal": True, "all_targets_equal": True,
        "state_hash": sim.state_hash(),
        "result_SHA256": sha(state / "RESULT.json"),
        "account_SHA256": sha(state / "ACCOUNT.json"),
        "minute_numeric_SHA256": sha(state / "MINUTE_NUMERIC.json"),
        "binding_SHA256": sha(state / "BINDING.json"),
        "pointer_SHA256": sha(state / "recovery/POINTER.json"),
        "runner_SHA256": sha(RUNNER),
        "baseline_identity_SHA256": sha(BASELINES),
        "status": "PASS_COLD_RESTORE_ZERO_ADVANCE"
    }
    path = HERE / "receipts" / f"{case_id}.json"
    path.parent.mkdir(exist_ok=True)
    with path.open("x") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(receipt["status"], case_id, "minutes", receipt["minute_rows_sha_verified"],
          "chunks", receipt["day_chunks_sha_verified"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id")
    main(parser.parse_args().case_id)
