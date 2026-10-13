"""Read-only exact-pair observer; publishes no annual delta from a halt."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from provenance import verify_completed_run

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODULE = ROOT / "coin_quantity_resolution_20261013"
STATE = MODULE / "state_20261013"
BRANCH_SNAPSHOT = ROOT / "coin_recovery_state/BRANCH_HEADS_20261013_1048.txt"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path: Path, obj) -> None:
    with path.open("x") as file:
        json.dump(obj, file, indent=2, sort_keys=True, allow_nan=False)
        file.write("\n")


def previous_original(case: dict) -> dict:
    row = case["coarse_original"]
    identity = row["published_identity"]
    full = identity["baseline_completed_minutes"] == identity["baseline_required_minutes"]
    paid = (full and identity["baseline_completion"] == "COMPLETE_CONDITIONAL_ACCOUNT"
            and identity["baseline_terminal_cash_realized"])
    local = None
    if row["local_result_locator"]:
        path = ROOT / row["local_result_locator"]
        if sha(path) != row["local_result_SHA256"]:
            raise ValueError("Local published coarse original result changed")
        local = json.loads(path.read_text())
        if (abs(local["summary"]["net_PnL"] - identity["baseline_net_marked_USDT"]) > 1e-8
                or local["summary"]["completed_minutes"] != identity["baseline_completed_minutes"]):
            raise ValueError("Published baseline and local original differ")
    elif case["arm"] == "STATIC50" and case["year"] in (2023, 2025):
        path = HERE / "prior_refs" / f"Y{case['year']}_STATIC50_RESULT.json"
        expected = {2023: "adfd514adbb976c2c3a548a97ddcd1265e6a023a87b8631ce5c8fa997be0d66f",
                    2025: "34884a9c3921694e941bc9e512e28a29583a25725c2f919c3b5883d052c4879e"}[case["year"]]
        if sha(path) != expected:
            raise ValueError("Published coarse STATIC50 result bytes changed")
        local = json.loads(path.read_text())
        if (abs(local["summary"]["net_PnL"] - identity["baseline_net_marked_USDT"]) > 1e-8
                or local["summary"]["completed_minutes"] != identity["baseline_completed_minutes"]):
            raise ValueError("Published remote coarse baseline differs")
    financial = local["summary"] if local else {}
    return {"source_url": identity["baseline_source_url"],
            "completed_minutes": identity["baseline_completed_minutes"],
            "required_minutes": identity["baseline_required_minutes"],
            "full_calendar": full, "paid_flat": paid,
            "marked_PnL_USDT": identity["baseline_net_marked_USDT"],
            "paid_cash_PnL_USDT": identity["baseline_net_marked_USDT"] if paid else None,
            "minute_drawdown": identity["baseline_minute_max_drawdown"],
            "account_status": identity["baseline_account_status"],
            "completion": identity["baseline_completion"],
            "stop_us": financial.get("stop_us"),
            "halt_count": int(identity["baseline_account_status"] in (
                "LIQUIDATION_REQUIRED_HALT", "BANKRUPT_HALT")),
            "terminal_residual_gross_notional_USDT":
                financial.get("terminal_marked_notional"),
            "mean_actual_gross": local["metrics"]["mean_actual_gross"] if local else None,
            "trade_legs": financial.get("trade_legs"),
            "gross_fill_turnover_USDT": financial.get("gross_fill_turnover_USDT"),
            "fees_USDT": financial.get("fees_USDT"),
            "execution_cost_USDT": financial.get("execution_cost_USDT"),
            "funding_USDT": financial.get("funding_USDT"),
            "rejection_counts": local.get("rejection_counts") if local else None,
            "published_result_detail_available": local is not None}


def previous_guard(case: dict) -> dict:
    ref = case["coarse_guard"]
    path = ROOT / ref["result_local_locator"]
    if sha(path) != ref["result_SHA256"]:
        raise ValueError("Local published coarse guard result changed")
    row = json.loads(path.read_text())
    s = row["summary"]
    return {"completed_minutes": s["completed_minutes"],
            "required_minutes": s["required_minutes"],
            "full_calendar": row["full_calendar"], "paid_flat": row["paid_flat"],
            "marked_PnL_USDT": row["marked_PnL_USDT"],
            "paid_cash_PnL_USDT": row["paid_cash_PnL_USDT"],
            "minute_drawdown": row["metrics"]["minute_drawdown"],
            "account_status": s["account_status"], "completion": s["completion"],
            "stop_us": s.get("stop_us"),
            "halt_count": int(s["account_status"] in (
                "LIQUIDATION_REQUIRED_HALT", "BANKRUPT_HALT")),
            "terminal_residual_gross_notional_USDT": s["terminal_marked_notional"],
            "mean_actual_gross": row["metrics"]["mean_actual_gross"],
            "trade_legs": s["trade_legs"],
            "gross_fill_turnover_USDT": s["gross_fill_turnover_USDT"],
            "fees_USDT": s["fees_USDT"],
            "execution_cost_USDT": s["execution_cost_USDT"],
            "funding_USDT": s["funding_USDT"],
            "rejection_counts": row["rejection_counts"],
            "protective_trigger_count": s["protective_trigger_count"],
            "protective_full_exit_count": s["protective_full_exit_count"]}


def current(case: dict, mode: str) -> dict:
    identity = f"{case['case_id']}_FINE_{mode}"
    state = STATE / identity
    row = json.loads((state / "RESULT.json").read_text())
    account = json.loads((state / "ACCOUNT.json").read_text())
    summary = account["summary"]
    if (row["case_id"] != identity or row["completed_minutes"] != summary["completed_minutes"]
            or row["required_minutes"] != summary["required_minutes"]
            or row["marked_PnL_USDT"] != summary["net_PnL"]):
        raise ValueError("Fine result/account identity differs")
    return {"completed_minutes": row["completed_minutes"],
            "required_minutes": row["required_minutes"],
            "full_calendar": row["full_calendar"], "paid_flat": row["paid_flat"],
            "marked_PnL_USDT": row["marked_PnL_USDT"],
            "paid_cash_PnL_USDT": row["paid_cash_PnL_USDT"],
            "minute_drawdown": row["minute_drawdown"],
            "account_status": row["account_status"], "completion": row["completion"],
            "stop_us": row["stop_us"],
            "halt_count": row["halt_count"],
            "terminal_residual_gross_notional_USDT": row["terminal_residual_gross_notional_USDT"],
            "mean_actual_gross": row["mean_actual_gross"],
            "trade_legs": row["trade_legs"],
            "gross_fill_turnover_USDT": summary["gross_fill_turnover_USDT"],
            "fees_USDT": summary["fees_USDT"],
            "execution_cost_USDT": summary["execution_cost_USDT"],
            "funding_USDT": summary["funding_USDT"],
            "rejection_counts": row["rejection_counts"],
            "protective_trigger_count": summary.get("protective_trigger_count", 0),
            "protective_full_exit_count": summary.get("protective_full_exit_count", 0),
            "result_SHA256": sha(state / "RESULT.json")}


def contrast(a: dict, b: dict) -> dict:
    """Return b minus a, only where their financial horizons really match."""
    same_full = (a["full_calendar"] and b["full_calendar"]
                 and a["completed_minutes"] == b["completed_minutes"])
    both_paid = same_full and a["paid_flat"] and b["paid_flat"]
    def diff(key):
        return b[key] - a[key] if same_full and a[key] is not None and b[key] is not None else None
    def relative(key):
        return ((b[key] - a[key]) / a[key] if same_full and a[key] not in (None, 0)
                and b[key] is not None else None)
    ar, br = a.get("rejection_counts"), b.get("rejection_counts")
    return {"same_full_calendar": same_full,
            "both_paid_flat": both_paid,
            "paid_cash_PnL_delta_USDT": b["paid_cash_PnL_USDT"] - a["paid_cash_PnL_USDT"]
                if both_paid else None,
            "marked_PnL_delta_same_full_calendar_USDT": diff("marked_PnL_USDT"),
            "minute_drawdown_delta_same_full_calendar": diff("minute_drawdown"),
            "mean_actual_gross_delta_same_full_calendar": diff("mean_actual_gross"),
            "mean_l1_target_weight_gap_delta_same_full_calendar": diff("mean_l1_target_weight_gap"),
            "terminal_residual_gross_notional_delta_USDT": diff(
                "terminal_residual_gross_notional_USDT"),
            "trade_legs_delta": diff("trade_legs"),
            "trade_legs_relative_change": relative("trade_legs"),
            "gross_fill_turnover_delta_USDT": diff("gross_fill_turnover_USDT"),
            "fees_delta_USDT": diff("fees_USDT"),
            "execution_cost_delta_USDT": diff("execution_cost_USDT"),
            "funding_delta_USDT": diff("funding_USDT"),
            "rejection_count_deltas": ({key: br.get(key, 0) - ar.get(key, 0)
                    for key in sorted(set(ar) | set(br))} if same_full and ar is not None and br is not None
                    else None),
            "rejection_count_relative_changes": ({
                key: ((br.get(key, 0) - ar.get(key, 0)) / ar[key]
                      if ar.get(key, 0) else None)
                for key in sorted(set(ar) | set(br))}
                if same_full and ar is not None and br is not None else None),
            "halt_count_delta": b["halt_count"] - a["halt_count"],
            "unequal_or_partial_horizon_needs_common_prefix": not same_full}


def target_gap(recovery: Path | None, weights: np.ndarray,
               minutes: int | None = None) -> float | None:
    """Minute-weighted sum of 5 absolute actual-minus-daily-target weights."""
    if recovery is None:
        return None
    pointer = json.loads((recovery / "POINTER.json").read_text())
    total, count = 0., 0
    if len(pointer["chunks"]) > len(weights):
        raise ValueError("Target-gap recovery exceeds target calendar")
    if minutes is not None and (minutes < 0 or minutes > pointer["completed_minutes"]):
        raise ValueError("Requested target-gap prefix is outside saved minutes")
    for day, row in enumerate(pointer["chunks"]):
        if minutes is not None and count >= minutes:
            break
        path = recovery / row["path"]
        if sha(path) != row["SHA256"]:
            raise ValueError("Target-gap checkpoint chunk SHA differs")
        with np.load(path, allow_pickle=False) as archive:
            chunk = archive["minute_chunk"]
        # Checkpoint stores 36 numeric fields; result() adds close_us as column 37.
        if chunk.dtype != np.float64 or chunk.ndim != 2 or chunk.shape[1] != 36:
            raise ValueError("Target-gap minute geometry differs")
        n = len(chunk) if minutes is None else min(len(chunk), minutes - count)
        actual = chunk[:n, 29:34]
        if not np.isfinite(actual).all():
            raise ValueError("Nonfinite realized target weights")
        total += float(np.abs(actual - weights[day]).sum())
        count += n
    if count != (pointer["completed_minutes"] if minutes is None else minutes):
        raise ValueError("Target-gap minute count differs")
    return total / count if count else None


def prefix_nav(recovery: Path, minutes: int) -> dict:
    pointer = json.loads((recovery / "POINTER.json").read_text())
    if sum(row["rows"] for row in pointer["chunks"]) < minutes:
        raise ValueError("Common prefix exceeds saved recovery minutes")
    left, peak, mdd, last = minutes, 10000., 0., 10000.
    gross_sum, gross_max = 0., 0.
    for row in pointer["chunks"]:
        if left == 0:
            break
        path = recovery / row["path"]
        if sha(path) != row["SHA256"]:
            raise ValueError("Common-prefix chunk SHA differs")
        with np.load(path, allow_pickle=False) as archive:
            chunk = archive["minute_chunk"]
        if (chunk.dtype != np.float64 or chunk.ndim != 2
                or chunk.shape != (row["rows"], 36)):
            raise ValueError("Common-prefix chunk geometry differs")
        used = chunk[:left]
        if not np.isfinite(used[:, 34]).all() or np.any(used[:, 34] < 0):
            raise ValueError("Invalid gross exposure in common-prefix recovery")
        gross_sum += float(used[:, 34].sum())
        gross_max = max(gross_max, float(used[:, 34].max()))
        for nav in used[:, 0]:
            if not np.isfinite(nav) or nav <= 0:
                raise ValueError("Nonpositive/nonfinite common-prefix NAV")
            last = float(nav)
            peak = max(peak, last)
            mdd = max(mdd, 1 - last / peak)
        left -= min(left, len(chunk))
    if left:
        raise ValueError("Truncated common-prefix recovery")
    return {"common_completed_minutes": minutes, "last_completed_minute_NAV_USDT": last,
            "last_completed_minute_marked_PnL_USDT": last - 10000.,
            "max_drawdown_of_completed_minute_prefix": mdd,
            "mean_minute_close_gross_weight_of_prefix": gross_sum / minutes,
            "max_minute_close_gross_weight_of_prefix": gross_max,
            "excludes_halt_mark_after_last_completed_minute": True}


def common_prefix_2024_static(case: dict, coarse_original: dict, coarse_guard: dict,
                              fine_original: dict, fine_guard: dict,
                              weights: np.ndarray) -> dict:
    if case["year"] != 2024 or case["arm"] != "STATIC50":
        raise ValueError("Only predeclared 2024 STATIC50 halt gets prefix analysis")
    minutes = min(row["completed_minutes"] for row in
                  (coarse_original, coarse_guard, fine_original, fine_guard))
    paths = {
        "coarse_original": ROOT / "coin_expanded_coverage_20261013/wallets/STATIC50/recovery",
        "coarse_guard": ROOT / "coin_margin_protective_runner_20261013/state_20261013/Y2024_STATIC50/recovery",
        "fine_original": STATE / "Y2024_STATIC50_FINE_ORIGINAL/recovery",
        "fine_guard": STATE / "Y2024_STATIC50_FINE_GUARD50/recovery",
    }
    rows = {key: prefix_nav(path, minutes) for key, path in paths.items()}
    gaps = {key: target_gap(path, weights, minutes) for key, path in paths.items()}
    same_stop = (coarse_original["completed_minutes"] == fine_original["completed_minutes"]
                 and coarse_original["stop_us"] == fine_original["stop_us"]
                 and coarse_original["account_status"] == "LIQUIDATION_REQUIRED_HALT"
                 and fine_original["account_status"] == "LIQUIDATION_REQUIRED_HALT")
    stop_deltas = {key: fine_original[key] - coarse_original[key] for key in (
        "trade_legs", "gross_fill_turnover_USDT", "fees_USDT", "execution_cost_USDT",
        "funding_USDT", "terminal_residual_gross_notional_USDT")} if same_stop else None
    matched_rejections = None
    if same_stop and coarse_original["rejection_counts"] is not None:
        ar, br = coarse_original["rejection_counts"], fine_original["rejection_counts"]
        matched_rejections = {
            "absolute_count_deltas": {key: br.get(key, 0) - ar.get(key, 0)
                                      for key in sorted(set(ar) | set(br))},
            "relative_count_changes": {
                key: ((br.get(key, 0) - ar.get(key, 0)) / ar[key]
                      if ar.get(key, 0) else None)
                for key in sorted(set(ar) | set(br))}}
    return {"comparison_scope": "SAME_COMPLETED_MINUTE_PREFIX_EXCLUDES_ORIGINAL_HALT_MARK",
            "common_completed_minutes": minutes,
            "last_completed_minute_close_us": case["calendar"][0] + minutes * 60_000_000,
            "paths": rows,
            "mean_l1_target_weight_gap_same_prefix": gaps,
            "fine_minus_coarse_original_prefix_mean_l1_target_weight_gap":
                gaps["fine_original"] - gaps["coarse_original"],
            "fine_minus_coarse_guard_prefix_mean_l1_target_weight_gap":
                gaps["fine_guard"] - gaps["coarse_guard"],
            "original_endpoints": {
                "coarse": {key: coarse_original[key] for key in (
                    "completed_minutes", "account_status", "stop_us", "marked_PnL_USDT")},
                "fine": {key: fine_original[key] for key in (
                    "completed_minutes", "account_status", "stop_us", "marked_PnL_USDT")}},
            "matched_original_halt_endpoint": same_stop,
            "matched_halt_endpoint_original_execution_deltas": stop_deltas,
            "matched_halt_endpoint_original_trade_legs_relative_change": (
                stop_deltas["trade_legs"] / coarse_original["trade_legs"]
                if same_stop and coarse_original["trade_legs"] else None),
            "matched_halt_endpoint_original_rejection_changes": matched_rejections,
            "fine_minus_coarse_original_prefix_PnL_USDT":
                rows["fine_original"]["last_completed_minute_marked_PnL_USDT"]
                - rows["coarse_original"]["last_completed_minute_marked_PnL_USDT"],
            "fine_minus_coarse_guard_prefix_PnL_USDT":
                rows["fine_guard"]["last_completed_minute_marked_PnL_USDT"]
                - rows["coarse_guard"]["last_completed_minute_marked_PnL_USDT"],
            "annual_return_delta": None}


def main() -> None:
    import sys
    sys.path.insert(0, str(MODULE))
    import preflight
    plan = preflight.bindings()
    cases = verify_completed_run(STATE, MODULE, plan)
    receipts = HERE / "receipts"
    if {path.stem for path in receipts.glob("*.json")} != set(cases):
        raise ValueError("Cold-audit receipt set differs from exactly twelve fixed cases")
    for identity in cases:
        receipt = json.loads((receipts / f"{identity}.json").read_text())
        if (receipt["status"] != "PASS_COLD_RESTORE_ZERO_ADVANCE"
                or receipt["case_id"] != identity or receipt["financial_advances"] != 0):
            raise ValueError(f"Cold-audit verdict differs: {identity}")
        state = STATE / identity
        for field, path in (("result_SHA256", state / "RESULT.json"),
                            ("account_SHA256", state / "ACCOUNT.json"),
                            ("binding_SHA256", state / "BINDING.json"),
                            ("pointer_SHA256", state / "recovery/POINTER.json"),
                            ("runner_SHA256", MODULE / "run_cases.py"),
                            ("fine_account_SHA256", MODULE / "fine_account.py")):
            if receipt[field] != sha(path):
                raise ValueError(f"Post-cold-audit file drift: {identity} {field}")
    output = []
    attempts = []
    for case in plan["cases"]:
        co = previous_original(case)
        cg = previous_guard(case)
        fo = current(case, "ORIGINAL")
        fg = current(case, "GUARD50")
        target_path = ROOT / case["target_archive_local_locator"]
        if sha(target_path) != case["target_archive_SHA256"]:
            raise ValueError("Frozen target archive changed during observer audit")
        with np.load(target_path, allow_pickle=False) as archive:
            weights = archive[case["arm"]].copy()
        if hashlib.sha256(weights.tobytes(order="C")).hexdigest() != case["target_array_SHA256"]:
            raise ValueError("Frozen target array changed during observer audit")
        original_recovery = (
            ROOT / f"coin_native_half_mix_20261013/STATE_Y{case['year']}/recovery"
            if case["arm"] == "COMBINED" else
            ROOT / f"coin_expanded_coverage_20261013/wallets/{case['arm']}/recovery"
            if case["year"] == 2024 else None)
        co["mean_l1_target_weight_gap"] = target_gap(original_recovery, weights)
        cg["mean_l1_target_weight_gap"] = target_gap(
            ROOT / "coin_margin_protective_runner_20261013/state_20261013"
            / case["case_id"] / "recovery", weights)
        fo["mean_l1_target_weight_gap"] = target_gap(
            STATE / f"{case['case_id']}_FINE_ORIGINAL/recovery", weights)
        fg["mean_l1_target_weight_gap"] = target_gap(
            STATE / f"{case['case_id']}_FINE_GUARD50/recovery", weights)
        record = {"case_id": case["case_id"], "year": case["year"], "arm": case["arm"],
                  "target_array_SHA256": case["target_array_SHA256"],
                  "source_index_SHA256": case["source_index_SHA256"],
                  "coarse_original": co, "coarse_guard": cg,
                  "fine_original": fo, "fine_guard": fg,
                  "fine_minus_coarse_original": contrast(co, fo),
                  "fine_minus_coarse_guard": contrast(cg, fg),
                  "coarse_guard_minus_original": contrast(co, cg),
                  "fine_guard_minus_original": contrast(fo, fg)}
        if case["year"] == 2024 and case["arm"] == "STATIC50":
            record["common_prefix_2024_halt"] = common_prefix_2024_static(
                case, co, cg, fo, fg, weights)
        output.append(record)
        for mode, fine in (("ORIGINAL", fo), ("GUARD50", fg)):
            identity = f"{case['case_id']}_FINE_{mode}"
            attempts.append({"case_id": identity, "target_array_SHA256": case["target_array_SHA256"],
                             "status": fine["completion"], "full_calendar": fine["full_calendar"],
                             "paid_flat": fine["paid_flat"], "marked_PnL_USDT": fine["marked_PnL_USDT"],
                             "result_SHA256": fine["result_SHA256"],
                             "cold_audit_SHA256": sha(receipts / f"{identity}.json")})
    if len(output) != 6 or len(attempts) != 12:
        raise ValueError("Fixed complete attempt population differs")
    report = {"status": "COMPLETE_TWELVE_FINE_GRID_CONDITIONAL_OFFLINE_SENSITIVITY",
              "no_native_or_historical_venue_filter_certification": True,
              "initial_capital_USDT_per_independent_wallet": 10000,
              "coarse_wallets_rerun": 0, "fine_wallets_run": 12,
              "source_target_identity_manifest_SHA256": sha(MODULE / "CASE_BINDINGS.json"),
              "reviewed_freeze_manifest_SHA256": sha(MODULE / "FROZEN_CODE.json"),
              "published_code_branch": "research/quantity-resolution-sensitivity-20261013",
              "published_code_commit": "63b0ab7c9c11da40dbfc0df1ec4ae7ea108dee4d",
              "branch_heads_snapshot_SHA256": sha(BRANCH_SNAPSHOT),
              "branch_heads_snapshot_observed_UTC": "2026-10-13T10:48:00Z",
              "cases": output,
              "target_gap_definition": "Time-weighted mean of sum over CORE5 symbols of absolute realized minute-close signed weight minus that UTC day's exact frozen target weight; includes price drift and guard-intent exits, so it is a tracking measure, not a pure lot-rejection count. Published coarse 2023/25 STATIC50 lacks local minute recovery and is null.",
              "interpretation": "Paired paid profit only for both complete/flat; marked full-calendar differences retain residual exposure; halted 2024 original is compared only on the common completed-minute prefix, never as an annual return. These are conditional Binance-observation/assumed-Bybit-cost simulations, not venue-certified executions."}
    save_new(HERE / "RESULTS_COMPACT.json", report)
    save_new(HERE / "ATTEMPTS.json", {"planned_and_executed_cases": attempts,
             "all_predeclared_cases_retained": True, "no_result_based_omission": True,
             "historical_wallets_run": 12, "coarse_wallets_rerun": 0,
             "branch_heads_snapshot_SHA256": sha(BRANCH_SNAPSHOT)})
    print("FINE_PAIR_AUDIT_COMPLETE", len(output), len(attempts))


if __name__ == "__main__":
    main()
