"""GO-gated, read-only, full-population observer of the three reentry cases.

Imports are stdlib-only. No runner, account, scheduler or historical simulator is
imported here. The only numerical work aggregates already saved observations.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import gate
import provenance

HERE, ROOT, MODULE, STATE = provenance.HERE, provenance.ROOT, provenance.MODULE, provenance.STATE
CASE_IDS, sha = provenance.CASE_IDS, provenance.sha
MINUTE, DAY, CAPITAL = 60_000_000, 86_400_000_000, 10000.0
PREFIX_PASS = "PASS_ALL_FINANCIAL_MINUTE_TRADE_FUNDING_PREFIX_BITS"
FULL_COLD = "PASS_COLD_RESTORE_ZERO_ADVANCE"
PARTIAL_COLD = "PASS_PARTIAL_COLD_RESTORE_ZERO_ADVANCE"
PREEXECUTION_COMMIT = "e1f42b8ed4fbdfcd2870799bd4b375a3873743cb"
PRE_GO_REVIEW_SHA256 = "0d383cbeba76da51f8ce1edc715ca7f689c30bd4c10a617c93298bfa76dbf296"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, obj) -> None:
    with path.open("x", encoding="utf-8") as file:
        json.dump(obj, file, indent=2, sort_keys=True, allow_nan=False)
        file.write("\n")


def safe_path(root: Path, locator: str) -> Path:
    relative = Path(locator)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("Absolute/traversing observer locator")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Observer locator escapes root")
    return path


def _integer(value, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError("Invalid observer integer: " + label)
    return value


def _decimal(row: dict, key: str) -> Decimal:
    value = Decimal(str(row.get("decimal_strings", {}).get(key, row[key])))
    if not value.is_finite():
        raise ValueError("Nonfinite journal quantity")
    return value


def reentry_entry_evidence(trades: list, daily_policy: dict | None,
                           protective_policy: dict | None) -> dict:
    """Match permissions to paid OPEN fills by exact symbol and daily signal.

    A permission is never counted as an entry unless the matching journal starts
    exactly flat and reaches a nonzero, target-sign-consistent actual position.
    Later protective cycles are counted before that symbol's next permission.
    This function executes no financial operation and infers no hypothetical fill.
    """
    events = list((daily_policy or {}).get("events", []))
    protection = list((protective_policy or {}).get("events", []))
    by_signal = defaultdict(list)
    for trade in trades:
        if trade.get("leg") == "OPEN":
            by_signal[(trade["symbol"], trade["signal_us"])].append(trade)
    seen = set()
    output = []
    for event in events:
        key = (event["symbol"], event["signal_us"])
        if key in seen:
            raise ValueError("Duplicate reentry permission")
        seen.add(key)
        kind = event["kind"]
        if kind not in ("SAME_DIRECTION_REENTRY_ALLOWED", "FRESH_DAILY_RESET"):
            raise ValueError("Unknown reentry permission kind")
        if (event["event_us"] != event["signal_us"]
                or not event["trigger_us"] <= event["flat_us"] < event["signal_us"]
                or event["signal_us"] % DAY != 0
                or Decimal(str(event["actual_quantity"])) != 0
                or event["account_status"] != "ACTIVE"
                or event["stopped_sign"] not in (-1, 1)):
            raise ValueError("Invalid fresh-daily reentry causality")
        target = Decimal(str(event["target_quantity"]))
        if not target.is_finite():
            raise ValueError("Nonfinite reentry target")
        sign = (target > 0) - (target < 0)
        if (sign != event["new_sign"] or
                (kind == "SAME_DIRECTION_REENTRY_ALLOWED") != (sign == event["stopped_sign"])):
            raise ValueError("Reentry direction classification differs")
        fills = sorted(by_signal.get(key, []), key=lambda r: (r["event_us"], r["fill_id"]))
        first = None
        for fill in fills:
            before, after = _decimal(fill, "quantity_before"), _decimal(fill, "quantity_after")
            if fill["event_us"] <= event["signal_us"]:
                raise ValueError("Reentry fill is not causally after its signal")
            if after == 0 or (after > 0) - (after < 0) != sign:
                raise ValueError("Reentry OPEN fill disagrees with actual target direction")
            if first is None and before == 0:
                first = fill
        if fills and (first is None or first is not fills[0]):
            raise ValueError("Reentry OPEN journal lacks its exact-flat first entry")
        next_signal = min((e["signal_us"] for e in events
                           if e["symbol"] == event["symbol"]
                           and e["signal_us"] > event["signal_us"]), default=None)
        later = [p for p in protection if first is not None
                 and p["symbol"] == event["symbol"] and p["event_us"] > first["event_us"]
                 and (next_signal is None or p["event_us"] < next_signal)]
        row = {k: event[k] for k in ("kind", "symbol", "trigger_us", "flat_us", "signal_us",
                                    "stopped_sign", "new_sign")}
        row.update(permission_only=first is None,
                   entry_us=first["event_us"] if first else None,
                   executed_opening_fill_legs=len(fills),
                   first_open_fill_id=first["fill_id"] if first else None,
                   later_full_exit_signal_count=sum(p["kind"] == "FULL_EXIT_SIGNAL" for p in later),
                   later_paid_flat_count=sum(p["kind"] == "FULL_EXIT_FLAT" for p in later))
        output.append(row)
    same = [r for r in output if r["kind"] == "SAME_DIRECTION_REENTRY_ALLOWED"]
    actual = [r for r in same if r["entry_us"] is not None]
    return {"events": output, "total_permission_count": len(output),
            "same_direction_permission_count": len(same),
            "fresh_daily_reset_permission_count": len(output) - len(same),
            "same_direction_executed_entry_count": len(actual),
            "all_direction_executed_entry_count": sum(r["entry_us"] is not None for r in output),
            "permissions_without_actual_entry_count": sum(r["permission_only"] for r in output),
            "first_actual_same_direction_entry_us": min((r["entry_us"] for r in actual), default=None),
            "actual_opening_fill_legs_for_permissions": sum(r["executed_opening_fill_legs"] for r in output),
            "entry_definition": "Exact symbol and signal_us OPEN journal, first quantity_before exactly zero, nonzero quantity_after of target sign; permission alone is not a fill."}


def terminal_attempt_evidence(policy: dict | None, *, observed: bool) -> dict:
    if not observed:
        return {"availability": "UNAVAILABLE_IN_FROZEN_FINE_CONTROL",
                "actual_attempt_count": None, "actual_attempts_by_kind": None,
                "observations": None,
                "caveat": "Close fills and rejection journals do not prove every actual eligible terminal-phase attempt."}
    records = (policy or {}).get("terminal_attempt_observations")
    if not isinstance(records, dict):
        raise ValueError("New reentry wallet terminal observations missing")
    by_kind = Counter()
    for key, row in records.items():
        count = _integer(row["actual_attempts"], "terminal attempts", 1)
        if (key != row["symbol"] + ":" + row["kind"]
                or row["first_attempt_us"] > row["last_attempt_us"]):
            raise ValueError("Actual terminal attempt identity differs")
        by_kind[row["kind"]] += count
    return {"availability": "EXPLICIT_FROZEN_OBSERVER", "actual_attempt_count": sum(by_kind.values()),
            "actual_attempts_by_kind": dict(sorted(by_kind.items())),
            "observations": records,
            "counter_definition": "Observed increments of the frozen scheduler order['attempts'] counter in terminal mode, by inherited order kind; eligible scheduler-counted attempts/minutes, not executed fill legs.",
            "caveat": "A zero-delta order can increment the counter before being marked reached without execute_fill. Counters do not imply accepted fills or rejected execution calls. Ongoing PROTECTIVE_STOP is not relabeled TERMINAL; below-lot deferred minutes are excluded."}


def subsequent_halt_evidence(summary: dict, entry_evidence: dict | None) -> dict:
    halted = summary["account_status"] in ("BANKRUPT_HALT", "LIQUIDATION_REQUIRED_HALT")
    entries = [row["entry_us"] for row in (entry_evidence or {}).get("events", [])
               if row.get("entry_us") is not None]
    first = min(entries, default=None)
    same = (entry_evidence or {}).get("first_actual_same_direction_entry_us")
    halt_us = summary.get("stop_us") if halted else None
    if type(halt_us) is not int:
        witness = summary.get("halt_witness") or {}
        halt_us = witness.get("event_us") if halted and type(witness.get("event_us")) is int else None
    def after(entry):
        if not halted:
            return False
        return entry is not None and halt_us > entry if halt_us is not None else None
    return {"account_halted": halted, "exact_halt_us": halt_us,
            "observed_account_clock_us": summary.get("clock_us"),
            "first_actual_reentry_us": first, "first_actual_same_direction_entry_us": same,
            "halt_after_any_actual_reentry": after(first),
            "halt_after_actual_same_direction_entry": after(same),
            "unknown_exact_halt_timestamp_is_not_inferred_from_observed_clock": True}


def _pointer(recovery: Path) -> dict:
    pointer = read_json(recovery / "POINTER.json")
    completed = _integer(pointer["completed_minutes"], "completed minutes")
    rows = 0
    paths = set()
    for index, chunk in enumerate(pointer["chunks"]):
        n = _integer(chunk["rows"], "chunk rows", 1)
        if n > 1440 or chunk["columns"] != 36 or chunk["path"] in paths:
            raise ValueError("Checkpoint minute chunk metadata/geometry differs")
        if index < len(pointer["chunks"]) - 1 and n != 1440:
            raise ValueError("Non-final checkpoint day is incomplete")
        safe_path(recovery, chunk["path"])
        paths.add(chunk["path"])
        rows += n
    if rows != completed:
        raise ValueError("Checkpoint minute count differs")
    return pointer


def stream_prefix(recovery: Path, minutes: int, weights=None) -> dict:
    """Aggregate one saved day at a time with exact chunk SHA and float64 geometry.

    No account finance is run. The endpoint is the last completed minute and
    excludes a halt mark/funding observation after that minute. Every referenced
    chunk is checked, even when only an earlier prefix contributes to aggregates.
    """
    import numpy as np
    pointer = _pointer(recovery)
    minutes = _integer(minutes, "requested prefix")
    if minutes > pointer["completed_minutes"]:
        raise ValueError("Requested common prefix exceeds checkpoint")
    if weights is not None:
        weights = np.asarray(weights)
        if (weights.dtype != np.float64 or weights.ndim != 2 or weights.shape[1] != 5
                or not np.isfinite(weights).all() or len(pointer["chunks"]) > len(weights)):
            raise ValueError("Frozen target weight geometry differs")
    count, peak, drawdown, last = 0, CAPITAL, 0.0, None
    cumulative = {"fees_USDT": None, "execution_cost_USDT": None,
                  "funding_USDT": None, "gross_fill_turnover_USDT": None}
    gross_sum, gross_max, gap_sum = 0.0, None, 0.0
    raw_hash = hashlib.sha256()
    for day, meta in enumerate(pointer["chunks"]):
        path = safe_path(recovery, meta["path"])
        if sha(path) != meta["SHA256"]:
            raise ValueError("Saved minute chunk SHA differs")
        with np.load(path, allow_pickle=False) as archive:
            if archive.files != ["minute_chunk"]:
                raise ValueError("Checkpoint minute archive schema differs")
            chunk = archive["minute_chunk"]
        if chunk.dtype != np.float64 or chunk.shape != (meta["rows"], 36):
            raise ValueError("Saved minute chunk float64 geometry differs")
        used = chunk[:max(0, min(len(chunk), minutes - count))]
        if not len(used):
            continue
        if (not np.isfinite(used[:, 0]).all() or not np.isfinite(used[:, 5:9]).all()
                or not np.isfinite(used[:, 29:35]).all()
                or np.any(used[:, 34] < 0)):
            raise ValueError("Nonfinite minute NAV/weights or negative gross exposure")
        raw_hash.update(used.tobytes(order="C"))
        for nav in used[:, 0]:
            last = float(nav)
            peak = max(peak, last)
            drawdown = max(drawdown, 1.0 - last / peak)
        gross_sum += float(used[:, 34].sum())
        maximum = float(used[:, 34].max())
        gross_max = maximum if gross_max is None else max(gross_max, maximum)
        if weights is not None:
            gap_sum += float(np.abs(used[:, 29:34] - weights[day]).sum())
        for column, key in enumerate(cumulative, start=5):
            cumulative[key] = float(used[-1, column])
        count += len(used)
    if count != minutes:
        raise ValueError("Truncated saved common prefix")
    return {"common_completed_minutes": count,
            "last_completed_minute_NAV_USDT": last,
            "last_completed_minute_marked_PnL_USDT": last - CAPITAL if last is not None else None,
            "max_drawdown_of_completed_minute_prefix": drawdown if count else None,
            "mean_minute_close_gross_weight_of_prefix": gross_sum / count if count else None,
            "max_minute_close_gross_weight_of_prefix": gross_max,
            "mean_l1_target_weight_gap_of_prefix": gap_sum / count if count and weights is not None else None,
            "minute_prefix_raw_SHA256": raw_hash.hexdigest(),
            "chunks_sha_and_geometry_verified": len(pointer["chunks"]),
            "saved_cumulative_at_last_completed_minute": cumulative,
            "excludes_halt_mark_after_last_completed_minute": True,
            "financial_advances": 0}


def censoring(summary: dict, required_minutes: int, *, official_result: bool) -> dict:
    completed = _integer(summary["completed_minutes"], "completed minutes")
    required = _integer(required_minutes, "required minutes", 1)
    if completed > required:
        raise ValueError("Observed horizon exceeds fixed calendar")
    full = official_result and completed == required
    quantities = summary.get("positions", {})
    exact_flat = bool(quantities) and all(_decimal(row, "quantity") == 0 for row in quantities.values())
    paid = (full and summary["completion"] == "COMPLETE_CONDITIONAL_ACCOUNT"
            and summary.get("terminal_cash_realized") is True and exact_flat)
    halted = summary["account_status"] in ("BANKRUPT_HALT", "LIQUIDATION_REQUIRED_HALT")
    return {"completed_minutes": completed, "required_minutes": required,
            "full_calendar": full, "paid_flat": paid, "exact_terminal_flat": exact_flat,
            "observation_class": "FULL_PAID_FLAT" if paid else "FULL_MARKED" if full else
                "PARTIAL_HALTED" if halted else "PARTIAL_RESOURCE_OR_CONTROLLER_CENSORED",
            "official_runner_result_present": official_result,
            "annual_paid_return": summary["net_PnL"] / CAPITAL if paid else None,
            "paid_cash_PnL_USDT": summary["net_PnL"] if paid else None}


def contrast(control: dict, reentry: dict) -> dict:
    """Reentry minus frozen control. Annual paid deltas need both full-flat."""
    same_full = (control.get("available") and reentry.get("available")
                 and control["full_calendar"] and reentry["full_calendar"]
                 and control["completed_minutes"] == reentry["completed_minutes"]
                 and control["required_minutes"] == reentry["required_minutes"])
    both_paid = bool(same_full and control["paid_flat"] and reentry["paid_flat"])
    keys = ("marked_PnL_USDT", "minute_drawdown", "mean_actual_gross", "max_actual_gross",
            "mean_l1_target_weight_gap", "trade_legs", "gross_fill_turnover_USDT", "fees_USDT",
            "execution_cost_USDT", "funding_USDT", "terminal_residual_gross_notional_USDT")
    deltas = {key: (reentry[key] - control[key] if same_full and control.get(key) is not None
                    and reentry.get(key) is not None else None) for key in keys}
    return {"same_full_calendar": bool(same_full), "both_paid_flat": both_paid,
            "paid_cash_PnL_delta_USDT": reentry["paid_cash_PnL_USDT"] - control["paid_cash_PnL_USDT"]
                if both_paid else None,
            "annual_paid_return_delta": reentry["annual_paid_return"] - control["annual_paid_return"]
                if both_paid else None,
            "same_full_calendar_observed_deltas": deltas,
            "unequal_or_partial_horizon_needs_common_prefix": not bool(same_full),
            "marked_full_calendar_delta_is_not_paid_profit": bool(same_full and not both_paid)}


def common_prefix(control: dict, reentry: dict, control_recovery: Path,
                  reentry_recovery: Path, weights, *, start_us: int) -> dict:
    minutes = min(control["completed_minutes"], reentry["completed_minutes"])
    a, b = stream_prefix(control_recovery, minutes, weights), stream_prefix(reentry_recovery, minutes, weights)
    fields = ("last_completed_minute_marked_PnL_USDT", "max_drawdown_of_completed_minute_prefix",
              "mean_minute_close_gross_weight_of_prefix", "max_minute_close_gross_weight_of_prefix",
              "mean_l1_target_weight_gap_of_prefix")
    return {"scope": "SAME_COMPLETED_MINUTE_PREFIX_EXCLUDES_POST_MINUTE_HALT_MARK",
            "common_completed_minutes": minutes,
            "last_completed_minute_close_us": start_us + minutes * MINUTE if minutes else None,
            "control": a, "reentry": b,
            "reentry_minus_control_observed_prefix": {
                key: b[key] - a[key] if a[key] is not None and b[key] is not None else None for key in fields},
            "reentry_minus_control_saved_cumulative_prefix": {
                key: (b["saved_cumulative_at_last_completed_minute"][key] - value
                      if value is not None and b["saved_cumulative_at_last_completed_minute"][key] is not None else None)
                for key, value in a["saved_cumulative_at_last_completed_minute"].items()},
            "annual_return_delta": None,
            "no_full_year_or_paid_profit_claim": True}


def verify_audit_stage(audit: dict, *, manifest_sha: str, run_binding_sha: str,
                       controller_sha: str, state_locator: str) -> None:
    """Bind cold receipts to a finished bounded AUDIT and its original GO bytes."""
    if (audit.get("stage") != "AUDIT" or audit.get("status") != "ALL_OBSERVERS_FINISHED"
            or audit.get("case_ids") != list(CASE_IDS)
            or set(audit.get("per_observer", {})) != set(CASE_IDS)
            or audit.get("unstarted_observer_ids") != [] or audit.get("financial_advances") != 0
            or audit.get("historical_wallets_opened") != 0
            or audit.get("observer_manifest_SHA256") != manifest_sha):
        raise ValueError("Successful full-population bounded AUDIT receipt missing")
    original_go = audit.get("postrun_GO_text")
    if (not isinstance(original_go, str) or
            hashlib.sha256(original_go.encode("utf-8")).hexdigest() != audit.get("postrun_GO_SHA256")):
        raise ValueError("Original AUDIT GO exact bytes/hash missing")
    go = json.loads(original_go)
    if (go.get("parent_GO") is not True or "AUDIT" not in go.get("approved_stages", [])
            or not set(go.get("approved_stages", [])) <= {"AUDIT", "REPORT"}
            or go.get("manifest_SHA256") != manifest_sha or go.get("state_locator") != state_locator
            or go.get("run_binding_SHA256") != run_binding_sha
            or go.get("controller_receipt_SHA256") != controller_sha
            or go.get("historical_controller_released") is not True):
        raise ValueError("Original AUDIT GO does not authorize these frozen inputs")


def verify_receipt(case_id: str, receipt: dict, audit: dict) -> None:
    if receipt.get("case_id") != case_id or receipt.get("financial_advances") != 0:
        raise ValueError("Cold receipt identity/zero-advance verdict differs")
    status = receipt.get("status", "")
    files = receipt.get("input_files_SHA256")
    if not isinstance(files, dict):
        raise ValueError("Cold receipt pinned input-file map missing")
    if (receipt.get("observer_manifest_SHA256") != audit["observer_manifest_SHA256"]
            or receipt.get("postrun_GO_SHA256") != audit["postrun_GO_SHA256"]):
        raise ValueError("Cold receipt reviewed observer/GO identity differs")
    observer = audit["per_observer"][case_id]
    if observer.get("cold_receipt_SHA256") != sha(HERE / "receipts" / (case_id + ".json")):
        raise ValueError("Cold receipt is not the exact bounded AUDIT output")
    for locator, expected in files.items():
        if sha(safe_path(ROOT, locator)) != expected:
            raise ValueError("Post-cold-audit file drift: " + locator)
    for name in ("RUN_BINDING.json", "RESOURCE_RECEIPTS.json"):
        path = STATE / name
        if files.get(str(path.relative_to(ROOT))) != sha(path):
            raise ValueError("Required cold-audit run/controller pin missing")
    if status not in (FULL_COLD, PARTIAL_COLD):
        if status not in ("UNSTARTED_NO_WALLET", "STARTED_NO_RECOVERABLE_CHECKPOINT") or receipt.get("observed_summary") is not None:
            raise ValueError("Cold receipt is neither restored nor explicitly unavailable")
        if {k: v for k, v in observer.items() if k != "cold_receipt_SHA256"} != receipt:
            raise ValueError("Unavailable receipt differs from exact AUDIT unavailable record")
        if provenance.case_availability(STATE, case_id, read_json(STATE / "RESOURCE_RECEIPTS.json")) != status:
            raise ValueError("Unavailable receipt differs from terminal controller case")
        return
    if (observer.get("exit_code") != 0 or observer.get("stop_reason") is not None
            or type(observer.get("sampled_peak_RSS")) is not int
            or not 0 <= observer["sampled_peak_RSS"] <= 2_000_000_000
            or observer.get("RSS_ceiling_bytes") != 2_000_000_000
            or receipt.get("simulator_class") != "native_half_equity_full_exit_fresh_daily_reentry_v1"
            or receipt.get("account_class") != "conditional_shared_default_fine_grid_sensitivity_v1"
            or receipt.get("runner_SHA256") != sha(MODULE / "run_cases.py")
            or receipt.get("fine_account_SHA256") != sha(ROOT / "coin_quantity_resolution_20261013/fine_account.py")
            or any(receipt.get(key) is not True for key in ("all_snapshot_state_equal", "all_journals_equal", "all_targets_equal"))):
        raise ValueError("Cold receipt lacks successful bounded worker/code/class/state evidence")
    state = STATE / case_id
    pointer = _pointer(state / "recovery")
    if receipt.get("state_hash") != pointer["state_hash"]:
        raise ValueError("Cold restored state hash differs from pinned checkpoint")
    mandatory = [state / "BINDING.json", state / "recovery/POINTER.json",
                 safe_path(state / "recovery", pointer["snapshot_path"])]
    for name in ("RESULT.json", "ACCOUNT.json", "MINUTE_NUMERIC.json", "PREFIX_ACCEPTANCE.json"):
        if (state / name).exists():
            mandatory.append(state / name)
    for path in mandatory:
        if files.get(str(path.relative_to(ROOT))) != sha(path):
            raise ValueError("Required cold-audit input pin missing: " + str(path.relative_to(ROOT)))
    if sha(safe_path(state / "recovery", pointer["snapshot_path"])) != pointer["snapshot_SHA256"]:
        raise ValueError("Checkpoint snapshot SHA differs")
    if pointer["completed_minutes"] != receipt["observed_summary"]["completed_minutes"]:
        raise ValueError("Cold receipt/checkpoint observed horizon differs")
    result_present = (state / "RESULT.json").exists()
    if (status == FULL_COLD) != result_present:
        raise ValueError("Cold receipt finished/partial status differs from result availability")
    proof = receipt.get("prefix_financial_proof")
    if not isinstance(proof, dict) or proof.get("status") != PREFIX_PASS:
        raise ValueError("Verified financial guard prefix proof missing")
    if result_present:
        persisted = read_json(state / "PREFIX_ACCEPTANCE.json")
        if proof != persisted or read_json(state / "RESULT.json").get("guard_prefix_acceptance") != persisted:
            raise ValueError("Persisted official runner prefix proof differs from cold verification")
    if (receipt.get("prefix_financial_proof_verified") is not True or
            receipt.get("prefix_verification_status") not in (
                "VERIFIED_RUNNER_ACCEPTANCE_EXACT",
                "VERIFIED_PARTIAL_PREFIX_THROUGH_FIRST_SIGNAL_NO_RESULT_ACCEPTANCE",
                "VERIFIED_SAVED_PARTIAL_PREFIX_NO_SAME_SIGNAL_NO_RESULT_ACCEPTANCE")):
        raise ValueError("Cold financial prefix verification did not pass")
    if (proof.get("comparator_case_id") != case_id.replace("_REENTRY50", "_GUARD50")
            or proof.get("guard_wallets_rerun") != 0
            or type(proof.get("minute_rows")) is not int
            or not 0 <= proof["minute_rows"] <= pointer["completed_minutes"]):
        raise ValueError("Financial guard prefix population/horizon differs")


def load_weights(case: dict):
    import numpy as np
    path = safe_path(ROOT, case["target_archive_local_locator"])
    if sha(path) != case["target_archive_SHA256"]:
        raise ValueError("Frozen target archive SHA differs")
    with np.load(path, allow_pickle=False) as archive:
        weights = archive[case["arm"]].copy()
        clocks = archive["decision_us"].copy()
    if (list(weights.shape) != case["target_shape"] or weights.dtype.str != case["target_dtype"]
            or hashlib.sha256(weights.tobytes(order="C")).hexdigest() != case["target_array_SHA256"]
            or not np.array_equal(clocks, np.arange(*case["calendar"], DAY))):
        raise ValueError("Frozen target/calendar numerical identity differs")
    return weights


def observed_row(case: dict, *, case_id: str, summary: dict, result: dict | None,
                 policy: dict | None, protection: dict | None, metrics: dict,
                 quantities: dict | None, entry_evidence: dict | None,
                 rejection_counts: dict | None, is_reentry: bool) -> dict:
    required = (case["calendar"][1] - case["calendar"][0]) // MINUTE
    row = {"case_id": case_id, "available": True, **censoring(summary, required, official_result=result is not None),
           "marked_PnL_USDT": summary["net_PnL"],
           "minute_drawdown": summary["all_observation_max_drawdown"],
           "mean_actual_gross": metrics.get("mean_actual_gross"),
           "max_actual_gross": metrics.get("max_actual_gross"),
           "completion": summary["completion"], "account_status": summary["account_status"],
           "stop_us": summary.get("stop_us"), "observed_clock_us": summary.get("clock_us"),
           "halt_count": int(summary["account_status"] in ("BANKRUPT_HALT", "LIQUIDATION_REQUIRED_HALT")),
           "halt_witness": summary.get("halt_witness"),
           "terminal_residual_quantity": quantities,
           "terminal_residual_signed_marked_notional_USDT": summary.get("terminal_signed_marked_notional"),
           "terminal_residual_gross_notional_USDT": summary.get("terminal_marked_notional"),
           "rejection_counts": rejection_counts,
           "protective_trigger_count": summary.get("protective_trigger_count", 0),
           "protective_full_exit_count": summary.get("protective_full_exit_count", 0),
           "protective_event_kind_counts": dict(Counter(e["kind"] for e in (protection or {}).get("events", []))),
           "open_protective_locks": (protection or {}).get("open_locks"),
           "reentry_entry_evidence": entry_evidence,
           "subsequent_halt_evidence": subsequent_halt_evidence(summary, entry_evidence) if is_reentry else None,
           "terminal_attempt_evidence": terminal_attempt_evidence(policy, observed=is_reentry)}
    for key in ("trade_legs", "gross_fill_turnover_USDT", "fees_USDT", "execution_cost_USDT", "funding_USDT"):
        row[key] = summary.get(key)
    if result is not None:
        checks = ("completed_minutes", "required_minutes", "full_calendar", "paid_flat", "paid_cash_PnL_USDT",
                  "marked_PnL_USDT", "completion", "account_status", "minute_drawdown", "trade_legs")
        if result.get("case_id") != case_id or any(result.get(key) != row[key] for key in checks):
            raise ValueError("Saved result/account/cold observation classification differs")
    return row


def fine_control(case: dict, mode: str, weights) -> tuple[dict, Path]:
    ref = case["fine_comparators"][mode]
    for record in ref["files"].values():
        if sha(safe_path(ROOT, record["locator"])) != record["SHA256"]:
            raise ValueError("Hash-bound frozen fine comparator changed")
    state = safe_path(ROOT, ref["state_locator"])
    result, account = read_json(state / "RESULT.json"), read_json(state / "ACCOUNT.json")
    binding = read_json(state / "BINDING.json")
    receipt = read_json(safe_path(ROOT, ref["files"]["cold_receipt"]["locator"]))
    pointer = _pointer(state / "recovery")
    if (receipt.get("status") != FULL_COLD or receipt.get("financial_advances") != 0
            or receipt.get("case_id") != ref["case_id"] or binding.get("case_id") != ref["case_id"]
            or pointer.get("binding") != binding or binding.get("calendar") != case["calendar"]
            or binding.get("target_array_SHA256") != case["target_array_SHA256"]
            or binding.get("source_index_SHA256") != case["source_index_SHA256"]
            or sha(safe_path(state / "recovery", pointer["snapshot_path"])) != pointer["snapshot_SHA256"]):
        raise ValueError("Frozen comparator cold/binding/snapshot identity differs")
    metrics = stream_prefix(state / "recovery", pointer["completed_minutes"], weights)
    row = observed_row(case, case_id=ref["case_id"], summary=account["summary"], result=result,
                       policy=None, protection=account.get("protective_policy"),
                       metrics=result, quantities=result.get("terminal_residual_quantity"),
                       entry_evidence=None, rejection_counts=result.get("rejection_counts"), is_reentry=False)
    row.update(mean_l1_target_weight_gap=metrics["mean_l1_target_weight_gap_of_prefix"],
               completed_minute_prefix_metrics=metrics,
               input_files_SHA256={r["locator"]: r["SHA256"] for r in ref["files"].values()},
               journal_evidence={"close_fill_leg_count": sum(t.get("leg") == "CLOSE" for t in account["trades"]),
                                 "pending_orders_at_stop": account["summary"].get("pending_orders_at_stop"),
                                 "actual_terminal_attempt_counts_unavailable": True})
    return row, state / "recovery"


def reentry_case(case: dict, receipt: dict, weights) -> tuple[dict, Path | None]:
    case_id = case["case_id"] + "_FINE_REENTRY50"
    state = STATE / case_id
    if receipt["status"] not in (FULL_COLD, PARTIAL_COLD):
        return {"case_id": case_id, "available": False, "observation_class": "UNAVAILABLE",
                "reason": receipt.get("reason", receipt.get("unavailable_reason", receipt["status"])),
                "full_calendar": False, "paid_flat": False, "annual_paid_return": None,
                "paid_cash_PnL_USDT": None, "marked_PnL_USDT": None,
                "official_runner_result_present": False}, None
    result = read_json(state / "RESULT.json") if (state / "RESULT.json").exists() else None
    summary = receipt["observed_summary"]
    if result is not None and read_json(state / "ACCOUNT.json")["summary"] != summary:
        raise ValueError("Cold receipt/account summary differs")
    policy, protection = receipt["observed_daily_reentry_policy"], receipt["observed_protective_policy"]
    evidence = receipt.get("observed_reentry_entry_evidence")
    if evidence is None:
        raise ValueError("Cold reentry actual-entry journal evidence missing")
    if result is not None:
        account = read_json(state / "ACCOUNT.json")
        if (account.get("daily_reentry_policy") != policy or account.get("protective_policy") != protection
                or reentry_entry_evidence(account["trades"], policy, protection) != evidence):
            raise ValueError("Cold reentry entry/protection evidence differs from account journal")
    metrics = stream_prefix(state / "recovery", summary["completed_minutes"], weights)
    proof = receipt["prefix_financial_proof"]
    if (proof.get("comparator_pointer_SHA256") !=
            case["fine_comparators"]["GUARD50"]["files"]["pointer"]["SHA256"]
            or stream_prefix(state / "recovery", proof["minute_rows"])["minute_prefix_raw_SHA256"] !=
                proof["minute_raw_SHA256"]):
        raise ValueError("Cold financial proof does not match saved guard/new minute prefix identity")
    row = observed_row(case, case_id=case_id, summary=summary, result=result, policy=policy,
                       protection=protection, metrics=receipt["observed_minute_metrics"],
                       quantities=receipt.get("observed_terminal_residual_quantity"),
                       entry_evidence=evidence, rejection_counts=receipt.get("observed_rejection_counts"), is_reentry=True)
    row.update(mean_l1_target_weight_gap=metrics["mean_l1_target_weight_gap_of_prefix"],
               completed_minute_prefix_metrics=metrics,
               observed_journal_counts=receipt.get("observed_journal_counts"),
               first_same_direction_permission_us=policy.get("first_same_direction_signal_us"),
               prefix_financial_proof=receipt["prefix_financial_proof"],
               prefix_verification_status=receipt["prefix_verification_status"],
               official_runner_prefix_acceptance_present=result is not None,
               input_files_SHA256=receipt["input_files_SHA256"])
    return row, state / "recovery"


def main() -> None:
    gate.verify_observer_go("REPORT")
    gate.require_bounded_worker("REPORT")
    plan = read_json(MODULE / "CASE_BINDINGS.json")
    cases = provenance.verify_terminal_run(state=STATE, module=MODULE, plan=plan)
    expected = tuple(CASE_IDS)
    if tuple(cases) != expected or len(expected) != 3:
        raise ValueError("Terminal run differs from fixed ordered three-case population")
    receipts_dir = HERE / "receipts"
    audit = read_json(HERE / "AUDIT_RESOURCE_RECEIPTS.json")
    verify_audit_stage(audit, manifest_sha=sha(HERE / "REVIEWED_POSTRUN_CODE.json"),
                       run_binding_sha=sha(STATE / "RUN_BINDING.json"),
                       controller_sha=sha(STATE / "RESOURCE_RECEIPTS.json"),
                       state_locator=str(STATE.relative_to(ROOT)))
    if {path.stem for path in receipts_dir.glob("*.json")} != set(expected):
        raise ValueError("Cold receipt population differs from exactly three planned cases")
    receipts = {}
    for case_id in expected:
        receipts[case_id] = read_json(receipts_dir / (case_id + ".json"))
        verify_receipt(case_id, receipts[case_id], audit)
    if tuple(case["case_id"] + "_FINE_REENTRY50" for case in plan["cases"]) != expected:
        raise ValueError("Binding plan case population/order differs")
    output, attempts = [], []
    for case in plan["cases"]:
        case_id = case["case_id"] + "_FINE_REENTRY50"
        receipt = receipts[case_id]
        weights = load_weights(case)
        reentry, recovery = reentry_case(case, receipt, weights)
        controls, comparisons = {}, {}
        for mode in ("ORIGINAL", "GUARD50"):
            control, control_recovery = fine_control(case, mode, weights)
            controls[mode] = control
            comparison = contrast(control, reentry)
            if comparison["unequal_or_partial_horizon_needs_common_prefix"] and recovery is not None:
                comparison["common_observed_minute_prefix"] = common_prefix(
                    control, reentry, control_recovery, recovery, weights, start_us=case["calendar"][0])
            elif recovery is None:
                comparison["common_observed_minute_prefix"] = None
                comparison["reason"] = "Reentry checkpoint unavailable; no path or annual claims"
            comparisons[mode] = comparison
        output.append({"case_id": case["case_id"], "reentry_case_id": case_id,
                       "year": case["year"], "arm": case["arm"], "calendar_us": case["calendar"],
                       "target_array_SHA256": case["target_array_SHA256"],
                       "source_index_SHA256": case["source_index_SHA256"],
                       "fine_controls": controls, "reentry": reentry,
                       "reentry_minus_frozen_fine_control": comparisons})
        attempts.append({"case_id": case_id, "cold_status": receipt["status"],
                         "available": reentry["available"], "observation_class": reentry["observation_class"],
                         "completed_minutes": reentry.get("completed_minutes"),
                         "required_minutes": (case["calendar"][1] - case["calendar"][0]) // MINUTE,
                         "full_calendar": reentry["full_calendar"], "paid_flat": reentry["paid_flat"],
                         "official_runner_result_present": reentry["official_runner_result_present"],
                         "target_array_SHA256": case["target_array_SHA256"],
                         "cold_audit_SHA256": sha(receipts_dir / (case_id + ".json"))})
    if len(output) != 3 or len(attempts) != 3:
        raise ValueError("Full predeclared report population differs")
    controller = read_json(STATE / "RESOURCE_RECEIPTS.json")
    report = {"status": "THREE_CASE_FRESH_DAILY_REENTRY_READ_ONLY_OBSERVER",
              "controller_terminal_status": controller["status"], "cases": output,
              "fixed_three_case_ids": list(expected), "historical_wallets_advanced_by_observer": 0,
              "frozen_fine_control_wallets_reused": 6, "fine_control_wallets_rerun": 0,
              "initial_capital_USDT_per_independent_wallet": CAPITAL,
              "source_target_identity_manifest_SHA256": sha(MODULE / "CASE_BINDINGS.json"),
              "reviewed_execution_freeze_manifest_SHA256": sha(MODULE / "FROZEN_CODE.json"),
              "pinned_pre_execution_commit": PREEXECUTION_COMMIT,
              "independent_pre_GO_review_receipt_SHA256": PRE_GO_REVIEW_SHA256,
              "bounded_AUDIT_resource_receipt_SHA256": sha(HERE / "AUDIT_RESOURCE_RECEIPTS.json"),
              "target_gap_definition": "Minute-weighted mean sum over five symbols of absolute realized minute-close signed weight minus that UTC day's exact frozen target weight. Includes price drift and protective exits; not a pure lot-rejection count.",
              "interpretation": "All three cases retained against both existing fine controls. Only both full-calendar exact-flat cases permit annual paid deltas. Full-marked endpoints retain signed/gross residue. Partial/halted cases are censored and use matched saved-minute prefixes, excluding post-minute halt marks. Permissions are distinguished from actual paid entry fills. Conditional Binance observations and assumed Bybit costs/fine grid are not venue-certified fills or live-tradability evidence."}
    attempts_report = {"planned_cases": attempts, "all_predeclared_cases_retained": True,
                       "no_result_based_omission": True, "fine_control_wallets_rerun": 0,
                       "historical_financial_advances_by_observer": 0,
                       "controller_terminal_status": controller["status"],
                       "controller_result_SHA256": sha(STATE / "RESOURCE_RECEIPTS.json")}
    # Both destinations must be unused before either is written. Creation remains
    # exclusive, so a concurrent or accidental repeat cannot silently overwrite.
    destinations = (HERE / "RESULTS_COMPACT.json", HERE / "ATTEMPTS.json")
    if any(path.exists() for path in destinations):
        raise FileExistsError("Observer outputs already exist; no overwrite permitted")
    save_new(destinations[0], report)
    save_new(destinations[1], attempts_report)
    print("THREE_CASE_REENTRY_REPORT_COMPLETE", len(output), len(attempts), flush=True)


if __name__ == "__main__":
    main()
