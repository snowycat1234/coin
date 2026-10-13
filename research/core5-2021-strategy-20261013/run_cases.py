"""GO-gated four-wallet full2021 original strategy comparison; zero preparation history.

Uses the published guarded runner's source transport, checkpoint, and resource
admission primitives. Only account profile and selected guard mode vary.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import secrets
import shutil
import signal
import subprocess
import sys
import time

from freeze_2021 import verify as verify_reviewed_freeze

# This stdlib-only byte check precedes imports of the financial account,
# frozen transport, scheduler and protective policy. Workers repeat it.
REVIEWED_FREEZE = verify_reviewed_freeze()

import preflight_2021 as preflight
import resource_gate
from run_budget import ensure_single_unstarted_batch, stop_on_worker_failure
from worker_bounds import require_worker_bounds

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GUARD_RUNNER = ROOT / "coin_margin_protective_runner_20261013/run_guard_cases.py"
spec = importlib.util.spec_from_file_location("frozen_guard_transport", GUARD_RUNNER)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
DAY = 86_400_000_000
CONTROLLER_WALL_LIMIT = 2400


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, obj) -> None:
    with path.open("x", encoding="utf-8") as file:
        json.dump(obj, file, indent=2, sort_keys=True, allow_nan=False)
        file.write("\n")


def state_root_ok(path: Path) -> None:
    if path.parent.resolve() != HERE.resolve() or not path.name.startswith("state") or path.is_symlink():
        raise ValueError("New state* root must be directly under this module")


def worker(case: dict, mode: str, state_root: Path) -> None:
    state_root_ok(state_root)
    run_binding = json.loads((state_root / "RUN_BINDING.json").read_text())
    identity = f"{case['case_id']}_FINE_{mode}"
    if (not run_binding.get("parent_GO") or identity not in run_binding["fine_case_ids"]
            or run_binding["nonce"] != os.environ.get("COIN_FULL2021_NONCE")
            or run_binding["runner_SHA256"] != sha(Path(__file__))
            or run_binding["bindings_SHA256"] != preflight.BINDINGS_SHA256
            or run_binding["freeze_manifest_SHA256"] != REVIEWED_FREEZE["freeze_manifest_SHA256"]
            or run_binding["fine_account_SHA256"] != sha(ROOT / "coin_quantity_resolution_20261013/fine_account.py")
            or run_binding.get("review_receipt_SHA256") != sha(HERE / "REVIEW_RECEIPT.json")
            or run_binding.get("publication_receipt_SHA256") != preflight.require_publication()["publication_receipt_SHA256"]
            or os.environ.get("COIN_FULL2021_BOUNDED") != "1"):
        raise RuntimeError("Parent GO/controller worker binding missing")
    require_worker_bounds(os.sched_getaffinity(0),
                          resource.getrlimit(resource.RLIMIT_AS),
                          resource.getrlimit(resource.RLIMIT_CPU))
    verify_reviewed_freeze(require_review=True)
    if mode != "ORIGINAL" or case["protective_enabled"] is not False:
        raise ValueError("Protective disabled ORIGINAL mode is frozen")
    import numpy as np
    from window_2021 import load_port_and_source
    port, source = load_port_and_source()
    sys.path.insert(0, str(ROOT / "coin_quantity_resolution_20261013"))
    from fine_account import FineGridAccount, profile_sha
    if profile_sha() != run_binding["fine_profile_SHA256"]:
        raise ValueError("Fine profile identity changed")
    if (sha(ROOT / case["source_index_local_locator"]) != case["source_index_SHA256"]
            or sha(ROOT / case["target_archive_local_locator"]) != case["target_archive_SHA256"]):
        raise ValueError("Source/target archive changed")
    with np.load(ROOT / case["target_archive_local_locator"], allow_pickle=False) as archive:
        clocks, weights = archive["decision_us"].copy(), archive[case["arm"]].copy()
    np.testing.assert_array_equal(clocks, np.arange(source["start"], source["end"], DAY))
    if hashlib.sha256(weights.tobytes(order="C")).hexdigest() != case["target_array_SHA256"]:
        raise ValueError("Frozen target array changed")
    if tuple(source["symbols"]) != tuple(case["symbols"]):
        raise ValueError("Source symbol order changed")
    state = state_root / identity
    state.mkdir()  # cannot overwrite or resume an old wallet
    binding = {"case_id": identity, "year": case["year"], "arm": case["arm"],
               "mode": mode, "calendar": case["calendar"], "capital_USDT": 10000,
               "source_index_SHA256": case["source_index_SHA256"],
               "target_archive_SHA256": case["target_archive_SHA256"],
               "target_array_SHA256": case["target_array_SHA256"],
               "fine_profile_SHA256": profile_sha(), "fine_account_class": FineGridAccount.VERSION,
               "fine_account_SHA256": sha(ROOT / "coin_quantity_resolution_20261013/fine_account.py"),
               "freeze_manifest_SHA256": REVIEWED_FREEZE["freeze_manifest_SHA256"],
               "scheduler_SHA256": sha(guard.REPO / "scripts/investment/resumable_perpetual.py"),
               "account_SHA256": sha(guard.REPO / "src/quant/perpetual_account.py"),
               "run_binding_SHA256": sha(state_root / "RUN_BINDING.json"),
               "terminal_quote_gate_SHA256": preflight.bindings()["terminal_quote_gate_SHA256"],
               "protective_enabled": False,
               "original_dynamic_masks_preserved": True,
               "source_commit": preflight.bindings()["source_commit"],
               "persist_cash_close": False, "final_day_target_zero": False}
    write_new(state / "BINDING.json", binding)

    def target_factory(_daily, decision_us, target_mode):
        np.testing.assert_array_equal(decision_us, clocks)
        if target_mode != "LONG_SHORT":
            raise ValueError("Target mode changed")
        frame = port.native.pl.DataFrame([{
            "available_us": int(stamp), "symbol": symbol,
            "target_weight": float(weights[i, j])}
            for i, stamp in enumerate(clocks) for j, symbol in enumerate(source["symbols"])])
        return frame, {"kind": "EXACT_FIXED_STATIC50_COIN_FULL2021_TARGET", "binding": binding}

    Simulator = port.native.NativeDailySimulator
    sim = Simulator(source, "LONG_SHORT", port.native.COSTS[0], port.native.UNITS[0],
                    target_factory=target_factory, account_factory=FineGridAccount,
                    persist_cash_close=False, final_day_target_zero=False)
    if type(sim.account) is not FineGridAccount or sim.account.nav() != 10000:
        raise ValueError("Fresh 10,000 USDT fine-grid account differs")
    begun = time.monotonic()
    port.checkpoint(state / "recovery", sim, binding)
    print("FULL2021_WALLET_STARTED", identity, flush=True)
    while sim.cursor < source["end"] and sim.stop is None:
        sim.advance_day()
        days = len(sim.minute_chunks)
        if days % 30 == 0 or sim.stop is not None or sim.cursor == source["end"]:
            port.checkpoint(state / "recovery", sim, binding)
            if guard.case_state_bytes(state) > guard.CASE_LIMIT:
                raise RuntimeError("250MB state cap; genuine partial state retained")
            print("FULL2021_WALLET_PROGRESS", identity, days, float(sim.account.nav()),
                  sim.account.status, flush=True)
        if time.monotonic() - begun > guard.WALL_LIMIT - 45:
            port.checkpoint(state / "recovery", sim, binding)
            raise RuntimeError("1200-second wallet cap; genuine partial retained")
    result = sim.result()
    summary = result["summary"]
    pointer = json.loads((state / "recovery/POINTER.json").read_text())
    guard.verify_final_pointer(pointer, sim, summary, binding, state / "recovery")
    _, inventory = port.native.episodes(result["trades"], tuple(source["symbols"]))
    for symbol in source["symbols"]:
        if inventory[symbol] != sim.account.positions[symbol].quantity:
            raise ValueError("Independent signed-inventory journal mismatch")
    bridge = port.native.nav_bridge(result["trades"], result["funding"], inventory,
                                    summary["terminal_mark_prices"], sim.account.nav())
    minute = result["minute"]
    daily = minute.filter(port.native.pl.col("close_us") % DAY == 0)
    np.testing.assert_array_equal(result["targets"]["target_weight"].to_numpy().reshape(-1, 5), weights)
    body = {key: result[key] for key in ("trades", "funding", "rejections", "breaches", "extrema", "target_meta")}
    body.update(summary=summary, targets=result["targets"].to_dicts(),
                liquidations=result.get("liquidations", []),
                protective_policy=result.get("protective_policy"))
    write_new(state / "ACCOUNT.json", body)
    daily.write_csv(state / "DAILY.csv")
    write_new(state / "MINUTE_NUMERIC.json", {"columns": port.fingerprint(minute),
              "storage": "ALL_OBSERVED_MINUTE_NUMERIC_BITS_EXACT_CHECKPOINT_NPZ_CODEC"})
    if guard.case_state_bytes(state) > guard.CASE_LIMIT:
        raise RuntimeError("250MB state cap after audit; genuine state retained")
    expected = (source["end"] - source["start"]) // 60_000_000
    full = summary["completed_minutes"] == expected
    paid = (full and summary["completion"] == "COMPLETE_CONDITIONAL_ACCOUNT"
            and bool(summary["terminal_cash_realized"]))
    nav = np.r_[10000., daily["nav"].to_numpy()]
    returns = np.diff(nav) / nav[:-1]
    net_weights = (sum(minute[f"{s}_signed_marked_notional"].to_numpy()
                       for s in source["symbols"]) / minute["nav"].to_numpy()
                   if minute.height else np.array([]))
    compact = {"case_id": identity, "mode": mode, "year": case["year"], "arm": case["arm"],
               "full_calendar": full, "paid_flat": paid,
               "paid_cash_PnL_USDT": summary["net_PnL"] if paid else None,
               "marked_PnL_USDT": summary["net_PnL"],
               "marked_return": summary["net_PnL"] / 10000,
               "annual_daily_vol": float(returns.std(ddof=1) * np.sqrt(365)) if full and len(returns)>1 else None,
               "worst_observed_30_days": float(np.min(nav[30:]/nav[:-30]-1)) if len(nav)>30 else None,
               "gross_fill_turnover_USDT": summary["gross_fill_turnover_USDT"],
               "fees_USDT": summary["fees_USDT"],
               "execution_cost_USDT": summary["execution_cost_USDT"],
               "funding_USDT": summary["funding_USDT"],
               "risk_reduction_signal_count": summary["risk_reduction_signal_count"],
               "mean_actual_signed_net": float(net_weights.mean()) if len(net_weights) else None,
               "max_actual_abs_signed_net": float(np.abs(net_weights).max()) if len(net_weights) else None,
               "minute_drawdown": summary["all_observation_max_drawdown"],
               "mean_actual_gross": float(minute["gross_weight"].mean()) if minute.height else None,
               "max_actual_gross": float(minute["gross_weight"].max()) if minute.height else None,
               "trade_legs": summary["trade_legs"],
               "rejection_counts": port.native.rejection_counts(result["rejections"]),
               "terminal_residual_quantity": {s: str(sim.account.positions[s].quantity) for s in source["symbols"]},
               "terminal_residual_marked_notional_USDT": summary["terminal_signed_marked_notional"],
               "terminal_residual_gross_notional_USDT": summary["terminal_marked_notional"],
               "halt_count": int(summary["account_status"] in ("BANKRUPT_HALT", "LIQUIDATION_REQUIRED_HALT")),
               "liquidation_event_count": len(result.get("liquidations", [])),
               "completion": summary["completion"], "account_status": summary["account_status"],
               "completed_minutes": summary["completed_minutes"], "required_minutes": expected,
               "stop_us": summary["stop_us"], "protective_policy": result.get("protective_policy"),
               "independent_decimal_NAV_bridge": bridge,
               "genuine_state_hash": pointer["state_hash"],
               "daily_observed_days": len(nav) - 1,
               "status": "COMPLETE_PAID_FLAT" if paid else "FULL_NOT_PAID_OR_NOT_EVALUABLE" if full else "STOP_PARTIAL"}
    write_new(state / "RESULT.json", compact)
    write_new(state / "TIMING.json", {"wallet_seconds": time.monotonic() - begun})
    print("FULL2021_WALLET_RESULT", identity, compact["status"], compact["marked_PnL_USDT"], flush=True)
    del sim, result, minute, daily
    gc.collect()


def controller(state_root: Path, plan: dict) -> None:
    state_root_ok(state_root)
    # Called while holding the shared controller lock, before resource admission
    # or writing any state. A different state-root cannot grant another batch.
    ensure_single_unstarted_batch(HERE, state_root)
    publication = preflight.require_publication()
    admission = resource_gate.admission(HERE, 0, guard)
    state_root.mkdir()
    nonce = secrets.token_hex(16)
    ordered = [(case, mode) for case in plan["cases"] for mode in plan["modes"]]
    write_new(state_root / "RUN_BINDING.json", {"parent_GO": True, "nonce": nonce,
              "runner_SHA256": sha(Path(__file__)), "bindings_SHA256": preflight.BINDINGS_SHA256,
              "fine_account_SHA256": sha(ROOT / "coin_quantity_resolution_20261013/fine_account.py"),
              "freeze_manifest_SHA256": REVIEWED_FREEZE["freeze_manifest_SHA256"],
              "fine_profile_SHA256": plan["fine_profile_SHA256"],
              "fine_case_ids": [f"{case['case_id']}_FINE_{mode}" for case, mode in ordered],
              "publication_receipt_SHA256": publication["publication_receipt_SHA256"],
              "review_receipt_SHA256": sha(HERE / "REVIEW_RECEIPT.json"),
              "initial_resource_admission": admission})
    waiting = list(ordered)
    running = {}
    receipts = {}
    failed = False
    experiment_began = time.monotonic()
    external_checked = 0.
    cpus = admission["allowed_cpus"][:2]
    try:
        while waiting or running:
            while waiting and len(running) < 2 and not failed:
                current = resource_gate.admission(state_root, len(running), guard)
                cpu = next((c for c in cpus if c in current["allowed_cpus"]
                            and c not in {v["cpu"] for v in running.values()}), None)
                if cpu is None:
                    raise RuntimeError("Distinct allowed worker CPU missing")
                case, mode = waiting.pop(0)
                identity = f"{case['case_id']}_FINE_{mode}"
                log = (state_root / f"{identity}.log").open("x")
                env = dict(os.environ, COIN_FULL2021_BOUNDED="1", COIN_FULL2021_NONCE=nonce,
                           CUDA_VISIBLE_DEVICES="", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
                           MKL_NUM_THREADS="1", POLARS_MAX_THREADS="1", NUMEXPR_NUM_THREADS="1",
                           RAYON_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1", PYTHONOPTIMIZE="0")
                try:
                    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                        "--worker-case", case["case_id"], "--worker-mode", mode,
                        "--state-root", str(state_root)], env=env, stdout=log,
                        stderr=subprocess.STDOUT, start_new_session=True,
                        preexec_fn=lambda chosen=cpu: guard.child_limits(chosen))
                except BaseException:
                    log.close()
                    waiting.insert(0, (case, mode))
                    raise
                running[identity] = {"process": proc, "cpu": cpu, "log": log,
                                     "began": time.monotonic(), "peak_RSS": 0}
                print("FULL2021_CASE_STARTED", identity, proc.pid, cpu, flush=True)
            if not running:
                break
            mem = guard.memory_observation()
            free = shutil.disk_usage(state_root).free
            stop = ("CONTROLLER_WALL_2400_SECONDS" if time.monotonic() - experiment_began > CONTROLLER_WALL_LIMIT else
                    "HOST_USED" if mem["host_used"] > guard.HOST_USED_LIMIT else
                    "SWAP" if mem["SwapTotal"] or mem["active_swaps"] else
                    "CGROUP_SWAP" if mem.get("cgroup_swap_current", 0) else
                    "CGROUP_MEMORY" if mem.get("cgroup_limit_verified") and
                      mem["cgroup_memory_current"] > mem["cgroup_memory_max"] else
                    "DISK_RESERVE" if free < guard.DISK_RESERVE else None)
            if stop is None and time.monotonic() - external_checked >= 1.:
                external_checked = time.monotonic()
                external = resource_gate.external_observation()
                try:
                    resource_gate.check_external({'memory': mem,
                        'allowed_cpus': sorted(os.sched_getaffinity(0))}, external,
                        max(0, len(running)-1), guard)
                    if any(job['cpu'] in external['external_busy_cpus'] for job in running.values()):
                        raise RuntimeError('External pack CPU now overlaps financial worker')
                except RuntimeError as error:
                    stop = 'SHARED_RESOURCE_CONFLICT:' + str(error)
            for identity, job in list(running.items()):
                proc = job["process"]
                job["peak_RSS"] = max(job["peak_RSS"], guard.process_rss(proc.pid))
                reason = (stop or "WORKER_RSS" if job["peak_RSS"] > guard.WORKER_RSS_LIMIT
                          else stop)
                if reason is None and time.monotonic() - job["began"] > guard.WALL_LIMIT:
                    reason = "WALL_SECONDS"
                if reason is not None:
                    receipts[identity] = {"stop_reason": reason, "peak_RSS": job["peak_RSS"]}
                    failed = True
                    guard.terminate(proc)
                code = proc.poll()
                if code is not None:
                    receipts.setdefault(identity, {"stop_reason": None, "peak_RSS": job["peak_RSS"]})
                    receipts[identity].update(exit_code=code, cpu=job["cpu"],
                        elapsed_seconds=time.monotonic() - job["began"],
                        peak_is_sampled_not_kernel_peak=True)
                    job["log"].close()
                    del running[identity]
                    if stop_on_worker_failure(code):
                        failed = True
                    print("FULL2021_CASE_DONE", identity, code, receipts[identity]["stop_reason"], flush=True)
            if failed:
                for identity, job in list(running.items()):
                    guard.terminate(job["process"])
                    job["log"].close()
                    receipts[identity] = {"stop_reason": "PEER_STOP",
                        "exit_code": job["process"].returncode, "cpu": job["cpu"],
                        "peak_RSS": job["peak_RSS"]}
                    del running[identity]
            else:
                time.sleep(.1)
    except BaseException:
        failed = True
        raise
    finally:
        for identity, job in running.items():
            guard.terminate(job["process"])
            job["log"].close()
            receipts[identity] = {"stop_reason": "CONTROLLER_EXCEPTION",
                "exit_code": job["process"].returncode, "cpu": job["cpu"],
                "peak_RSS": job["peak_RSS"]}
        write_new(state_root / "RESOURCE_RECEIPTS.json", {"per_case": receipts,
                  "unstarted_case_ids": [f"{c['case_id']}_FINE_{m}" for c, m in waiting],
                  "status": "STOP_PARTIAL" if failed else "ALL_CASES_FINISHED"})
    if failed or waiting:
        raise RuntimeError("Fine-grid run stopped; genuine partial state retained")


def main() -> None:
    guard.require_assertions_enabled()
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--parent-go", action="store_true")
    parser.add_argument("--state-root", type=Path)
    parser.add_argument("--worker-case")
    parser.add_argument("--worker-mode", choices=["ORIGINAL"])
    args = parser.parse_args()
    if args.check_only:
        if args.parent_go or args.worker_case or args.state_root:
            parser.error("Check-only cannot launch or write a wallet")
        print(json.dumps(preflight.check(), indent=2))
        return
    plan = preflight.bindings()
    if args.worker_case:
        if not args.worker_mode or args.state_root is None:
            parser.error("Bound worker needs mode and state root")
        case = next((c for c in plan["cases"] if c["case_id"] == args.worker_case), None)
        if case is None:
            parser.error("Worker case outside frozen plan")
        worker(case, args.worker_mode, args.state_root)
    else:
        if not args.parent_go or args.state_root is None or args.worker_mode:
            parser.error("Historical wallets require reviewed --parent-go and new --state-root")
        verify_reviewed_freeze(require_review=True)
        preflight.check()
        with resource_gate.controller_lock():
            controller(args.state_root, plan)


if __name__ == "__main__":
    main()
