"""Build one compact, all-arm paired report from 11 cold-audited guard wallets."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent
STATE = WORKSPACE / "coin_margin_protective_runner_20261013/state_20261013"
BASELINES = WORKSPACE / "new_coin_guard_baseline_identity_20261013/BASELINE_IDENTITY.json"
MANIFEST = WORKSPACE / "coin_margin_protective_policy_20261013/RUN_MANIFEST.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def must(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    baseline = json.loads(BASELINES.read_text())
    manifest = json.loads(MANIFEST.read_text())
    ids = [row["case_id"] for row in manifest["cases"]]
    must(len(ids) == len(set(ids)) == 11, "Frozen run plan must contain 11 unique cases")
    baselines = {row["case_id"]: row for row in baseline["cases"]}
    must(set(ids) == set(baselines), "Baseline identity appendix must cover exact plan")
    controller = json.loads((STATE / "RESOURCE_RECEIPTS.json").read_text())
    resource = controller["per_case"]
    must(set(resource) == set(ids), "Controller must report all eleven cases")
    cases = []
    for case_id in ids:
        must(resource[case_id]["exit_code"] == 0 and
             resource[case_id]["stop_reason"] is None, f"Financial runner failure: {case_id}")
        cold_path = HERE / "receipts" / f"{case_id}.json"
        cold = json.loads(cold_path.read_text())
        must(cold["status"] == "PASS_COLD_RESTORE_ZERO_ADVANCE" and
             cold["financial_advances"] == 0 and
             cold["minute_columns_sha_verified"] == 37,
             f"Cold audit incomplete: {case_id}")
        result_path = STATE / case_id / "RESULT.json"
        result = json.loads(result_path.read_text())
        original = baselines[case_id]
        must(cold["result_SHA256"] == sha(result_path), f"Cold/result mismatch: {case_id}")
        must(result["summary"]["completed_minutes"] == cold["minute_rows_sha_verified"],
             f"Minute row mismatch: {case_id}")
        guard_full = result["full_calendar"]
        base_full = original["baseline_completed_minutes"] == original["baseline_required_minutes"]
        base_paid = (base_full and original["baseline_completion"] == "COMPLETE_CONDITIONAL_ACCOUNT"
                     and original["baseline_terminal_cash_realized"])
        guard_paid = result["paid_flat"]
        no_signal = result["summary"]["protective_trigger_count"] == 0
        if no_signal and guard_full and base_full:
            must(abs(result["marked_PnL_USDT"] - original["baseline_net_marked_USDT"]) < 1e-9,
                 f"No-trigger net parity failed: {case_id}")
            must(abs(result["metrics"]["minute_drawdown"] - original["baseline_minute_max_drawdown"]) < 1e-12,
                 f"No-trigger drawdown parity failed: {case_id}")
            must(guard_paid == base_paid, f"No-trigger paid classification differs: {case_id}")
        cases.append({
            "case_id": case_id, "year": result["year"], "arm": result["arm"],
            "baseline_source_url": original["baseline_source_url"],
            "baseline_completed_minutes": original["baseline_completed_minutes"],
            "baseline_required_minutes": original["baseline_required_minutes"],
            "baseline_completion": original["baseline_completion"],
            "baseline_marked_PnL_USDT": original["baseline_net_marked_USDT"],
            "baseline_minute_max_drawdown": original["baseline_minute_max_drawdown"],
            "baseline_paid_flat": base_paid,
            "guard_status": result["status"],
            "guard_completed_minutes": result["summary"]["completed_minutes"],
            "guard_required_minutes": result["summary"]["required_minutes"],
            "guard_completion": result["summary"]["completion"],
            "guard_marked_PnL_USDT": result["marked_PnL_USDT"],
            "guard_minute_max_drawdown": result["metrics"]["minute_drawdown"],
            "guard_paid_flat": guard_paid,
            "guard_paid_cash_PnL_USDT": result["paid_cash_PnL_USDT"],
            "guard_paid_cash_return": result["paid_cash_return"],
            "protective_trigger_count": result["summary"]["protective_trigger_count"],
            "protective_full_exit_count": result["summary"]["protective_full_exit_count"],
            "paired_paid_cash_delta_USDT":
                result["paid_cash_PnL_USDT"] - original["baseline_net_marked_USDT"]
                if guard_paid and base_paid else None,
            "paired_full_calendar_marked_delta_USDT":
                result["marked_PnL_USDT"] - original["baseline_net_marked_USDT"]
                if guard_full and base_full else None,
            "paired_full_calendar_drawdown_delta_percentage_points":
                100 * (result["metrics"]["minute_drawdown"] - original["baseline_minute_max_drawdown"])
                if guard_full and base_full else None,
            "golden_no_trigger_net_DD_parity": no_signal and guard_full and base_full,
            "result_SHA256": sha(result_path),
            "cold_audit_receipt_SHA256": sha(cold_path),
            "genuine_state_hash": result["genuine_state_hash"]
        })
    summary = {
        "title": "Preregistered isolated half-equity full-exit guard, 11 matched native wallets",
        "status": "ALL_ELEVEN_FINANCIAL_EXITS_ZERO_AND_COLD_RESTORE_VERIFIED",
        "policy_id": "isolated_half_equity_full_exit_v1",
        "policy_commit": "7564139f27d0963d6cec34b72bc0e7b0a80bffa7",
        "runner_commit": "02138fb5b8690be48af2aa44261366331fbb318f",
        "baseline_identity_SHA256": sha(BASELINES),
        "run_manifest_SHA256": sha(MANIFEST),
        "resource_receipts_SHA256": sha(STATE / "RESOURCE_RECEIPTS.json"),
        "all_case_cold_restores": 11,
        "historical_wallets_in_fixed_guard_plan": 11,
        "new_fits": 0,
        "cases": cases,
        "interpretation": {
            "conditional_model": "Research-only conditional XRP/CORE5 quantity-grid isolated 1x with assumed 0.5% maintenance; not venue-certified historical exchange rules.",
            "paid_endpoint": "Only full-calendar, terminal-flat, normal-completion cases have a paid-cash annual return; otherwise null.",
            "original_2024_halts": "CS_MATCHED and STATIC50 baseline stopped 2024-11-16 10:49 UTC; baseline marked values are partial and cannot be compared to guard full-year paid returns.",
            "pairing": "All eleven same-year original source, executed target arrays and financial contracts validated by baseline identity appendix; no threshold tuning after the halt."
        }
    }
    canonical(HERE / "COMPARISON.json", summary)
    header = "| Year | Arm | Base completed | Base marked USDT | Guard completed | Guard marked USDT | Guard paid USDT | Guard DD | Signals | Paired paid delta USDT |\n|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines = ["# Isolated half-equity guard: fixed 11-wallet audit", "",
             "Research-only conditional account model. This does not establish real exchange liquidation rules or tradable returns.", "",
             "The 50% isolated-equity full-exit rule was frozen before historical replay. All 11 source/target/account bindings match the original controls. Each guard checkpoint was cold-restored without another financial advance; all day chunks, account journals, target rows and every numeric minute column passed exact checks.", "",
             header]
    def amount(x):
        return "—" if x is None else f"{x:+.2f}"
    for row in cases:
        lines.append(f"| {row['year']} | {row['arm']} | {row['baseline_completed_minutes']:,} | {amount(row['baseline_marked_PnL_USDT'])} | {row['guard_completed_minutes']:,} | {amount(row['guard_marked_PnL_USDT'])} | {amount(row['guard_paid_cash_PnL_USDT'])} | {100*row['guard_minute_max_drawdown']:.2f}% | {row['protective_trigger_count']} | {amount(row['paired_paid_cash_delta_USDT'])} |")
    lines += ["", "In the two 2024 controls that originally stopped on November 16 under the conditional account, the guard generated XRP full-exit signals on November 14 (CS 19:37 UTC, STATIC50 19:41 UTC) and completed paid closes at the next minute's open. Those guard paths reached year-end; the original partial marked values do not establish a paired annual return improvement.", "",
              "The three 2025 matched full-year cases all deteriorated on marked PnL and minute drawdown: STATIC50 −740.34 USDT / +4.30 drawdown percentage points; SMA −74.33 / +0.70; COMBINED −421.11 / +1.85. All retained residual positions, so none has a paid annual return.", "",
              "Paired paid deltas require both full-year flat endpoints. The two halted 2024 original controls have only partial marked values; their paid deltas are intentionally blank. Full-year marked and drawdown deltas are separately recorded in COMPARISON.json.", "",
              "No-trigger cases must reproduce the original full-year marked PnL, minute drawdown and paid classification. Both improved and worsened arms are retained; this is a sensitivity exercise, not an optimized strategy selection.", "",
              f"Exact baseline identity appendix SHA256: {sha(BASELINES)}", "",
              "Small audit receipts and summary are publication-safe. Full checkpoint archives remain local pending separate payload/destination review; no original 2025 backup is included.", ""]
    (HERE / "REPORT.md").write_text("\n".join(lines))
    print("BUILT_ALL_ELEVEN_COMPACT_GUARD_REPORT", len(cases))


if __name__ == "__main__":
    main()
