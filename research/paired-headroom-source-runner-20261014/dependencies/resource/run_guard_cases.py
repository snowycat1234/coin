"""Bounded, fresh-state runner for the preregistered 11 protective wallets.

This is a transport/observer harness. Financial math stays in the frozen account
and scheduler plus the separately published protective_policy.py adapter. No
historical execution occurs without an explicit parent GO CLI argument.
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

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent
POLICY = WORKSPACE / "coin_margin_protective_policy_20261013"
REPO = WORKSPACE / "coin_native_half_mix_20261013/repo"
CASE_LIMIT = 250_000_000
DISK_RESERVE = 16_106_127_360
HOST_USED_LIMIT = 8_000_000_000
WORKER_RSS_LIMIT = 2_000_000_000
WORKER_AS_LIMIT = 4_000_000_000
WALL_LIMIT = 1200
CPU_LIMIT = 1200
DAY = 86_400_000_000
POLICY_COMMIT = "7564139f27d0963d6cec34b72bc0e7b0a80bffa7"
POLICY_FREEZE_SHA256 = "1a447073dc204ae0dc11ee93a712f0a3a66fa2d8ec20cd12772148846d250881"
PORT_ORIGINAL_SHA256 = "c290175e490ac982b37f60e5b45793068169629fbeb70dc1625d49f7cfb4cb22"
PORT_2025_SCHEMA_SHA256 = "22882ac609574b964699e15545786ce9906f8ab73962d5466da0cccd41e1bca2"
WINDOW_2024_SHA256 = "23c48651ca4b1d767835bd6a371dd3046bfed46de478d60924389c05a0dda500"
PORT_MANIFEST_ORIGINAL_SHA256 = "c4fdb69b3ec8398bcc8bf7ce28f299144e95451a7d95a5defd74d1f2dcf55c56"
PORT_MANIFEST_2025_SHA256 = "c821cba7fa8e5a83e1cd2661938957d7eef01951ca113b1778991c5a2e84623c"
CASE_SET = {
    "Y2023_STATIC50", "Y2023_SMA200_10PCT", "Y2023_COMBINED",
    "Y2024_CS_MATCHED", "Y2024_VOL_MATCHED", "Y2024_STATIC50",
    "Y2024_SMA200_10PCT", "Y2024_EXACTHALF",
    "Y2025_STATIC50", "Y2025_SMA200_10PCT", "Y2025_COMBINED",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_assertions_enabled(optimize: int | None = None) -> None:
    # Frozen transport ports and source-month callbacks contain hash asserts.
    # They are part of input integrity and must not be stripped by python -O.
    level = sys.flags.optimize if optimize is None else optimize
    if level != 0:
        raise RuntimeError("Python optimization disables frozen source SHA assertions")


def exclusive_json(path: Path, obj) -> None:
    with path.open("x", encoding="utf-8") as out:
        json.dump(obj, out, indent=2, sort_keys=True, allow_nan=False)
        out.write("\n")


def verify_published_policy() -> dict:
    if sha(POLICY / "FREEZE.json") != POLICY_FREEZE_SHA256:
        raise ValueError("Published protective policy freeze bytes changed")
    freeze = json.loads((POLICY / "FREEZE.json").read_text())
    manifest = json.loads((POLICY / "RUN_MANIFEST.json").read_text())
    expected = {
        "adapter": POLICY / "protective_policy.py",
        "protocol": POLICY / "PROTOCOL.json",
        "synthetic_tests": POLICY / "test_policy_synthetic.py",
        "run_manifest": POLICY / "RUN_MANIFEST.json",
        "read_only_preflight": POLICY / "preflight_run_plan.py",
        "scheduler": REPO / "scripts/investment/resumable_perpetual.py",
        "account": REPO / "src/quant/perpetual_account.py",
        "quantity_adapter": REPO / "research/quantity-grid-sensitivity-20261012/grid_account.py",
        "quantity_profile": REPO / "research/quantity-grid-sensitivity-20261012/QUANTITY_PROFILE.json",
    }
    if set(freeze["SHA256"]) != set(expected):
        raise ValueError("Protective policy freeze has unexpected keys")
    for key, path in expected.items():
        if sha(path) != freeze["SHA256"][key]:
            raise ValueError(f"Frozen {key} bytes changed")
    transport = REPO / "research/static50-sma-20261013"
    if (sha(transport / "local_native_apis.py") != PORT_ORIGINAL_SHA256 or
        sha(transport / "local_native_apis_2025.py") != PORT_2025_SCHEMA_SHA256 or
        sha(transport / "LOCAL_CODE_MANIFEST.json") != PORT_MANIFEST_ORIGINAL_SHA256 or
        sha(transport / "LOCAL_CODE_MANIFEST_2025.json") != PORT_MANIFEST_2025_SHA256 or
        sha(WORKSPACE / "coin_expanded_coverage_20261013/window_2024.py") != WINDOW_2024_SHA256):
        raise ValueError("Verified original transport/window adapter bytes changed")
    if len(manifest["cases"]) != 11 or {c["case_id"] for c in manifest["cases"]} != CASE_SET:
        raise ValueError("Eleven-case plan differs")
    return manifest


def require_input_preflight(report: dict) -> None:
    if (report.get("status") != "INPUTS_BOUND_RESOURCE_RECHECK_REQUIRED_BEFORE_GO" or
            set(report.get("case_ids", [])) != CASE_SET or
            report.get("disk_preflight_pass") is not True or
            report.get("wallets_started") != 0):
        raise RuntimeError("Eleven-case input or conservative disk preflight did not pass")


def classify_result(summary: dict, expected_minutes: int) -> tuple[str, bool, bool]:
    full = summary["completed_minutes"] == expected_minutes
    paid = (full and summary["completion"] == "COMPLETE_CONDITIONAL_ACCOUNT"
            and bool(summary["terminal_cash_realized"]))
    status = ("COMPLETE_PAID_FLAT_GUARD_SHARED_NATIVE" if paid else
              "FULL_CALENDAR_NOT_PAID_OR_NOT_EVALUABLE_GUARD" if full else
              "STOP_PARTIAL_GUARD_SHARED_NATIVE")
    return status, full, paid


def verify_final_pointer(pointer: dict, sim, summary: dict, binding: dict,
                         recovery: Path) -> None:
    if (pointer.get("binding") != binding or
            pointer.get("completed_minutes") != sim.rows_written or
            pointer.get("completed_minutes") != summary["completed_minutes"] or
            pointer.get("cursor") != sim.cursor or
            pointer.get("stop") != sim.stop or
            pointer.get("stop") != summary["stop_us"] or
            pointer.get("state_hash") != sim.state_hash() or
            sum(row["rows"] for row in pointer.get("chunks", [])) != sim.rows_written or
            sha(recovery / pointer["snapshot_path"]) != pointer["snapshot_SHA256"]):
        raise ValueError("Final lossless checkpoint pointer differs from live account")


def memory_observation() -> dict:
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        name, _, rest = line.partition(":")
        if name in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
            values[name] = int(rest.split()[0]) * 1024
    if not {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"} <= set(values):
        raise RuntimeError("Host memory counters unavailable")
    values["host_used"] = values["MemTotal"] - values["MemAvailable"]
    values["active_swaps"] = max(0, len(Path("/proc/swaps").read_text().splitlines()) - 1)
    def limit(path: str):
        try:
            raw = Path(path).read_text().strip()
            number = int(raw) if raw != "max" else None
            # cgroup v1 can advertise a huge sentinel instead of a limit.
            return number if number is not None and number < values["MemTotal"] * 100 else None
        except (FileNotFoundError, ValueError):
            return None
    values["cgroup_memory_max"] = (limit("/sys/fs/cgroup/memory.max") or
                                   limit("/sys/fs/cgroup/memory/memory.limit_in_bytes"))
    values["cgroup_memory_current"] = (limit("/sys/fs/cgroup/memory.current") or
                                       limit("/sys/fs/cgroup/memory/memory.usage_in_bytes"))
    values["cgroup_swap_current"] = limit("/sys/fs/cgroup/memory.swap.current")
    values["cgroup_limit_verified"] = (values["cgroup_memory_max"] is not None and
                                        values["cgroup_memory_current"] is not None)
    return values


def resource_admission(state_root: Path, active: int, *, parallel: int = 2) -> dict:
    if active < 0 or active >= parallel or parallel != 2:
        raise ValueError("At most two distinct one-CPU workers")
    mem = memory_observation()
    if mem["active_swaps"] or mem["SwapTotal"] != 0:
        raise RuntimeError("Zero-swap resource contract violated")
    if mem.get("cgroup_swap_current", 0):
        raise RuntimeError("cgroup reports active swap")
    committed = (active + 1) * WORKER_RSS_LIMIT
    if mem["host_used"] + committed > HOST_USED_LIMIT:
        raise RuntimeError("Insufficient two-worker commitment under shared 8GB host cap")
    if (mem.get("cgroup_limit_verified") and
            mem["cgroup_memory_current"] + committed > mem["cgroup_memory_max"]):
        raise RuntimeError("Insufficient two-worker commitment under actual cgroup limit")
    free = shutil.disk_usage(state_root).free
    # Count all active and newly admitted cases at full 250 MB, even before
    # the existing child has allocated its future bytes (conservative double
    # count of bytes already reflected in current free disk).
    required = DISK_RESERVE + (active + 1) * (CASE_LIMIT + 2 * 63_204_609) + 1_048_576
    if free < required:
        raise RuntimeError("15 GiB disk reserve plus case/checkpoint margin unavailable")
    cpus = sorted(os.sched_getaffinity(0))
    if len(cpus) < parallel:
        raise RuntimeError("Two distinct allowed CPUs unavailable")
    return {"memory": mem, "disk_free_bytes": free,
            "disk_required_bytes": required, "allowed_cpus": cpus}


def process_rss(pid: int) -> int:
    pending, seen, total = [pid], set(), 0
    while pending:
        item = pending.pop()
        if item in seen:
            continue
        seen.add(item)
        try:
            status = Path(f"/proc/{item}/status").read_text()
            total += next((int(x.split()[1]) * 1024 for x in status.splitlines()
                           if x.startswith("VmRSS:")), 0)
            pending.extend(map(int, Path(f"/proc/{item}/task/{item}/children").read_text().split()))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return total


def load_port(year: int):
    """Use the same verified transport ports as the frozen native drivers."""
    require_assertions_enabled()
    import numpy as np
    base = REPO / "research/static50-sma-20261013"
    if year == 2025:
        path = base / "local_native_apis_2025.py"
        port_sha = PORT_2025_SCHEMA_SHA256
        port_manifest = base / "LOCAL_CODE_MANIFEST_2025.json"
        manifest_sha = PORT_MANIFEST_2025_SHA256
    else:
        path = base / "local_native_apis.py"
        port_sha = PORT_ORIGINAL_SHA256
        port_manifest = base / "LOCAL_CODE_MANIFEST.json"
        manifest_sha = PORT_MANIFEST_ORIGINAL_SHA256
    if sha(path) != port_sha:
        raise ValueError("Original native port bytes differ before import")
    if sha(port_manifest) != manifest_sha:
        raise ValueError("Original native port manifest bytes differ before import")
    if year == 2024 and sha(WORKSPACE / "coin_expanded_coverage_20261013/window_2024.py") != WINDOW_2024_SHA256:
        raise ValueError("Original 2024 window bytes differ before import")
    sys.path[:0] = [str(REPO), str(REPO / "src"), str(POLICY)]
    os.environ["QUANT_ROOT"] = str(REPO)
    os.environ["QUANT_STATE"] = str(WORKSPACE / "coin_expanded_coverage_20261013"
                                    if year == 2024 else REPO.parent)
    os.environ["CONFIG_FILE"] = "/dev/null"
    spec = importlib.util.spec_from_file_location(f"guard_native_port_{year}", path)
    port = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(port)
    port.verify()
    if year == 2024:
        window_path = WORKSPACE / "coin_expanded_coverage_20261013/window_2024.py"
        spec2 = importlib.util.spec_from_file_location("guard_window_2024", window_path)
        window_module = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(window_module)
        source = window_module.window(WORKSPACE / "coin_expanded_coverage_20261013/prepared_2024_cold")
    else:
        source = port.window(f"Y{year}")
    from protective_policy import ProtectiveFullExitSimulator, verified_freeze
    verified_freeze()
    return port, source, ProtectiveFullExitSimulator


def case_state_bytes(path: Path) -> int:
    seen, total = set(), 0
    for item in path.rglob("*"):
        if item.is_file():
            stat = item.stat()
            inode = (stat.st_dev, stat.st_ino)
            if inode not in seen:
                seen.add(inode)
                total += stat.st_size
    return total


def validate_state_root(path: Path) -> None:
    """Constrain every new run to this module's own fresh state namespace."""
    if (path.parent.resolve() != HERE.resolve() or not path.name.startswith("state")
            or path.is_symlink()):
        raise ValueError("State root must be a new state* directory under this runner")


def verify_worker_authorization(state_root: Path, case: dict) -> None:
    validate_state_root(state_root)
    path = state_root / "RUN_BINDING.json"
    if not path.is_file():
        raise RuntimeError("Controller GO binding missing before worker source load")
    binding = json.loads(path.read_text())
    if (binding.get("parent_go") is not True or
            set(binding.get("case_ids", [])) != CASE_SET or
            len(binding.get("case_ids", [])) != 11 or
            case.get("case_id") not in binding["case_ids"] or
            binding.get("policy_commit") != POLICY_COMMIT or
            binding.get("policy_freeze_SHA256") != POLICY_FREEZE_SHA256 or
            binding.get("run_manifest_SHA256") != sha(POLICY / "RUN_MANIFEST.json") or
            binding.get("runner_SHA256") != sha(Path(__file__)) or
            not binding.get("run_nonce") or
            binding["run_nonce"] != os.environ.get("COIN_GUARD_RUN_NONCE")):
        raise RuntimeError("Controller GO binding or run nonce differs")


def worker(case: dict, state_root: Path) -> None:
    verify_worker_authorization(state_root, case)
    if os.environ.get("COIN_GUARD_BOUNDED") != "1":
        raise RuntimeError("Worker must be launched by bounded controller")
    if len(os.sched_getaffinity(0)) != 1 or resource.getrlimit(resource.RLIMIT_AS)[0] > WORKER_AS_LIMIT:
        raise RuntimeError("One CPU and 4GB address-space bound required")
    import numpy as np
    port, source, Simulator = load_port(case["year"])
    if (sha(WORKSPACE / case["source_index_local_locator"]) != case["source_index_SHA256"]
            or sha(WORKSPACE / case["target_archive_local_locator"]) != case["target_archive_SHA256"]):
        raise ValueError("Case source or target bytes changed after admission")
    with np.load(WORKSPACE / case["target_archive_local_locator"], allow_pickle=False) as archive:
        clocks, weights = archive["decision_us"].copy(), archive[case["arm"]].copy()
    np.testing.assert_array_equal(clocks, np.arange(source["start"], source["end"], DAY))
    if hashlib.sha256(weights.tobytes(order="C")).hexdigest() != case["target_array_SHA256"]:
        raise ValueError("Bound target matrix differs")
    symbols = tuple(source["symbols"])
    if symbols != tuple(case["symbols"]):
        raise ValueError("CORE5 source order differs")
    state = state_root / case["case_id"]
    state.mkdir()  # exclusive fresh case; never resume or overwrite here
    binding = {"case_id": case["case_id"], "year": case["year"], "arm": case["arm"],
               "policy_commit": POLICY_COMMIT, "policy_freeze_SHA256": sha(POLICY / "FREEZE.json"),
               "policy_adapter_SHA256": sha(POLICY / "protective_policy.py"),
               "protocol_SHA256": sha(POLICY / "PROTOCOL.json"),
               "run_manifest_SHA256": sha(POLICY / "RUN_MANIFEST.json"),
               "runner_SHA256": sha(Path(__file__)),
               "local_native_port_SHA256": sha(REPO / "research/static50-sma-20261013" /
                   ("local_native_apis_2025.py" if case["year"] == 2025 else "local_native_apis.py")),
               "window_2024_SHA256": sha(WORKSPACE / "coin_expanded_coverage_20261013/window_2024.py")
                   if case["year"] == 2024 else None,
               "source_index_SHA256": case["source_index_SHA256"],
               "target_archive_SHA256": case["target_archive_SHA256"],
               "target_array_SHA256": case["target_array_SHA256"],
               "account_class": port.Closing.VERSION,
               "quantity_profile_SHA256": port.profile_sha(),
               "capital_USDT": 10000, "persist_cash_close": False,
               "final_day_target_zero": False, "calendar": case["calendar"]}
    exclusive_json(state / "BINDING.json", binding)

    def target_factory(_daily, decision_us, mode):
        np.testing.assert_array_equal(decision_us, clocks)
        if mode != "LONG_SHORT":
            raise ValueError("Unexpected mode")
        frame = port.native.pl.DataFrame([{
            "available_us": int(at), "symbol": symbol,
            "target_weight": float(weights[i, j])}
            for i, at in enumerate(clocks) for j, symbol in enumerate(symbols)])
        return frame, {"kind": "EXACT_SAVED_PREREGISTERED_ARM", "binding": binding}

    sim = Simulator(source, "LONG_SHORT", port.native.COSTS[0], port.native.UNITS[0],
                    target_factory=target_factory, account_factory=port.Closing,
                    persist_cash_close=False, final_day_target_zero=False)
    if type(sim.account) is not port.Closing or sim.account.nav() != 10000:
        raise ValueError("Unchanged fresh-capital account contract differs")
    begun = time.monotonic()
    port.checkpoint(state / "recovery", sim, binding)
    print("GUARD_WALLET_STARTED", case["case_id"], flush=True)
    while sim.cursor < source["end"] and sim.stop is None:
        sim.advance_day()
        days = len(sim.minute_chunks)
        if days % 30 == 0 or sim.stop is not None or sim.cursor == source["end"]:
            port.checkpoint(state / "recovery", sim, binding)
            if case_state_bytes(state) > CASE_LIMIT:
                exclusive_json(state / "BUDGET_STOP.json", {"reason": "CASE_BYTES",
                    "used": case_state_bytes(state), "limit": CASE_LIMIT})
                raise RuntimeError("250MB per-case state cap exceeded; partial retained")
            print("GUARD_WALLET_PROGRESS", case["case_id"], days,
                  float(sim.account.nav()), sim.account.status, flush=True)
        if time.monotonic() - begun > WALL_LIMIT - 45:
            port.checkpoint(state / "recovery", sim, binding)
            exclusive_json(state / "BUDGET_STOP.json", {"reason": "WALL_SECONDS",
                "elapsed": time.monotonic() - begun, "limit": WALL_LIMIT})
            raise RuntimeError("1200-second wallet cap; genuine partial retained")
    case_out = sim.result()
    summary = case_out["summary"]
    pointer = json.loads((state / "recovery/POINTER.json").read_text())
    verify_final_pointer(pointer, sim, summary, binding, state / "recovery")
    _, inventory = port.native.episodes(case_out["trades"], symbols)
    for symbol in symbols:
        if inventory[symbol] != sim.account.positions[symbol].quantity:
            raise ValueError("Independent signed inventory journal mismatch")
    bridge = port.native.nav_bridge(case_out["trades"], case_out["funding"], inventory,
                                    summary["terminal_mark_prices"], sim.account.nav())
    minute = case_out["minute"]
    daily = minute.filter(port.native.pl.col("close_us") % DAY == 0)
    np.testing.assert_array_equal(case_out["targets"]["target_weight"].to_numpy().reshape(-1, 5), weights)
    body = {key: case_out[key] for key in
            ("trades", "funding", "rejections", "breaches", "extrema", "target_meta")}
    body.update(summary=summary, targets=case_out["targets"].to_dicts(),
                liquidations=case_out.get("liquidations", []),
                protective_policy=case_out["protective_policy"])
    exclusive_json(state / "ACCOUNT.json", body)
    daily.write_csv(state / "DAILY.csv")
    exclusive_json(state / "MINUTE_NUMERIC.json", {"columns": port.fingerprint(minute),
                    "storage": "ALL_OBSERVED_MINUTE_NUMERIC_BITS_EXACT_CHECKPOINT_NPZ_CODEC"})
    used = case_state_bytes(state)
    if used > CASE_LIMIT:
        exclusive_json(state / "BUDGET_STOP.json", {"reason": "CASE_BYTES_AFTER_AUDIT",
            "used": used, "limit": CASE_LIMIT})
        raise RuntimeError("250MB per-case state cap exceeded after audit; state retained")
    nav = np.r_[10000., daily["nav"].to_numpy()]
    returns = np.diff(nav) / nav[:-1]
    rolling = nav[30:] / nav[:-30] - 1 if len(nav) > 30 else np.asarray([])
    status, full, paid = classify_result(summary,
        (source["end"] - source["start"]) // 60_000_000)
    result = {"case_id": case["case_id"], "year": case["year"], "arm": case["arm"],
              "status": status,
              "summary": summary, "protective_policy": case_out["protective_policy"],
              "metrics": {"days": len(returns), "annual_daily_vol":
                  float(returns.std(ddof=1) * np.sqrt(365)) if len(returns) > 1 else None,
                  "worst30": float(rolling.min()) if len(rolling) else None,
                  "mean_actual_gross": float(minute["gross_weight"].mean()) if minute.height else None,
                  "max_actual_gross": float(minute["gross_weight"].max()) if minute.height else None,
                  "minute_drawdown": summary["all_observation_max_drawdown"]},
              "full_calendar": full,
              "terminal_cash_realized": bool(summary["terminal_cash_realized"]),
              "paid_flat": paid,
              "paid_cash_PnL_USDT": summary["net_PnL"] if paid else None,
              "paid_cash_return": summary["net_PnL"] / 10000 if paid else None,
              "marked_PnL_USDT": summary["net_PnL"],
              "marked_return": summary["net_PnL"] / 10000,
              "independent_decimal_NAV_bridge": bridge,
              "genuine_state_hash": pointer["state_hash"],
              "rejection_counts": port.native.rejection_counts(case_out["rejections"]),
              "new_wallets": 1, "new_fits": 0, "downloads": 0,
              "policy_commit": POLICY_COMMIT}
    exclusive_json(state / "RESULT.json", result)
    exclusive_json(state / "TIMING.json", {"wallet_seconds": time.monotonic() - begun})
    print("GUARD_WALLET_RESULT", case["case_id"], result["status"],
          summary["net_PnL"], result["paid_flat"], flush=True)
    del sim, case_out, minute, daily
    gc.collect()


def child_limits(cpu: int) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (WORKER_AS_LIMIT, WORKER_AS_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT, CPU_LIMIT))
    os.sched_setaffinity(0, {cpu})


def terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


def controller(state_root: Path, manifest: dict, *, go: bool) -> None:
    if not go:
        raise RuntimeError("Explicit parent GO required before any historical wallet")
    validate_state_root(state_root)
    if state_root.exists() or not state_root.parent.is_dir():
        raise ValueError("Fresh state root and existing parent required")
    admission = resource_admission(state_root.parent, 0)
    cases = manifest["cases"]
    state_root.mkdir()
    run_nonce = secrets.token_hex(16)
    exclusive_json(state_root / "RUN_BINDING.json", {"policy_commit": POLICY_COMMIT,
        "parent_go": True, "run_nonce": run_nonce,
        "policy_freeze_SHA256": sha(POLICY / "FREEZE.json"),
        "run_manifest_SHA256": sha(POLICY / "RUN_MANIFEST.json"),
        "runner_SHA256": sha(Path(__file__)),
        "case_ids": [c["case_id"] for c in cases], "initial_resource_admission": admission})
    cpus = admission["allowed_cpus"][:2]
    waiting = list(cases)
    running = {}
    receipts = {}
    failed = False
    try:
        while waiting or running:
            while waiting and len(running) < 2 and not failed:
                current_admission = resource_admission(state_root, len(running))
                cpu = next((item for item in cpus if item in current_admission["allowed_cpus"]
                    and item not in {v["cpu"] for v in running.values()}), None)
                if cpu is None:
                    raise RuntimeError("No distinct allowed CPU remains for next worker")
                case = waiting.pop(0)
                log = (state_root / f'{case["case_id"]}.log').open("x")
                env = dict(os.environ, COIN_GUARD_BOUNDED="1", COIN_GUARD_RUN_NONCE=run_nonce,
                    CUDA_VISIBLE_DEVICES="",
                    OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                    POLARS_MAX_THREADS="1", NUMEXPR_NUM_THREADS="1", RAYON_NUM_THREADS="1",
                    PYTHONDONTWRITEBYTECODE="1", PYTHONOPTIMIZE="0")
                try:
                    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                        "--worker-case", case["case_id"], "--state-root", str(state_root),
                        "--parent-go"],
                        env=env, stdout=log, stderr=subprocess.STDOUT,
                        start_new_session=True, preexec_fn=lambda chosen=cpu: child_limits(chosen))
                except BaseException:
                    log.close()
                    waiting.insert(0, case)
                    raise
                running[case["case_id"]] = {"process": proc, "cpu": cpu,
                    "log": log, "began": time.monotonic(), "peak_RSS": 0}
                print("BOUNDED_GUARD_CASE_STARTED", case["case_id"], proc.pid, cpu, flush=True)
            if not running:
                break
            mem = memory_observation()
            free = shutil.disk_usage(state_root).free
            stop_reason = ("HOST_USED" if mem["host_used"] > HOST_USED_LIMIT else
                "SWAP" if mem["SwapTotal"] or mem["active_swaps"] else
                "CGROUP_SWAP" if mem.get("cgroup_swap_current", 0) else
                "CGROUP_MEMORY" if mem.get("cgroup_limit_verified") and
                    mem["cgroup_memory_current"] > mem["cgroup_memory_max"] else
                "DISK_RESERVE" if free < DISK_RESERVE else None)
            for key, job in list(running.items()):
                proc = job["process"]
                job["peak_RSS"] = max(job["peak_RSS"], process_rss(proc.pid))
                reason = stop_reason
                if reason is None and job["peak_RSS"] > WORKER_RSS_LIMIT:
                    reason = "WORKER_RSS"
                if reason is None and time.monotonic() - job["began"] > WALL_LIMIT:
                    reason = "WALL_SECONDS"
                if reason is not None:
                    receipts[key] = {"stop_reason": reason, "peak_RSS": job["peak_RSS"]}
                    failed = True
                    terminate(proc)
                code = proc.poll()
                if code is not None:
                    receipts.setdefault(key, {"stop_reason": None, "peak_RSS": job["peak_RSS"]})
                    receipts[key].update(exit_code=code, cpu=job["cpu"],
                        elapsed_seconds=time.monotonic() - job["began"],
                        peak_is_sampled_not_kernel_peak=True)
                    job["log"].close()
                    del running[key]
                    print("BOUNDED_GUARD_CASE_DONE", key, code, receipts[key]["stop_reason"], flush=True)
                    if code != 0:
                        failed = True
            if failed:
                for key, job in list(running.items()):
                    terminate(job["process"])
                    job["log"].close()
                    receipts[key] = {"stop_reason": "PEER_STOP", "exit_code": job["process"].returncode,
                        "cpu": job["cpu"], "peak_RSS": job["peak_RSS"]}
                    del running[key]
            else:
                time.sleep(.1)
    except BaseException:
        failed = True
        raise
    finally:
        for key, job in running.items():
            terminate(job["process"])
            job["log"].close()
            receipts[key] = {"stop_reason": "CONTROLLER_EXCEPTION",
                "exit_code": job["process"].returncode, "cpu": job["cpu"],
                "peak_RSS": job["peak_RSS"]}
        exclusive_json(state_root / "RESOURCE_RECEIPTS.json", {"per_case": receipts,
            "unstarted_case_ids": [c["case_id"] for c in waiting],
            "host_cap_bytes": HOST_USED_LIMIT, "worker_RSS_cap_bytes": WORKER_RSS_LIMIT,
            "worker_AS_cap_bytes": WORKER_AS_LIMIT, "worker_wall_seconds": WALL_LIMIT,
            "disk_reserve_bytes": DISK_RESERVE, "swap_allowed": False,
            "two_distinct_one_CPU_workers": True,
            "status": "STOP_PARTIAL" if failed else "ALL_STARTED_CASES_FINISHED"})
    if failed or waiting:
        raise RuntimeError("Bounded guard run stopped; retained genuine partial cases")


def main() -> None:
    require_assertions_enabled()
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path)
    parser.add_argument("--parent-go", action="store_true")
    parser.add_argument("--worker-case", choices=sorted(CASE_SET))
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.worker_case and (args.check_only or not args.parent_go):
        parser.error("Worker requires controller GO and cannot be check-only")
    if args.check_only and args.parent_go:
        parser.error("Check-only and parent GO are incompatible")
    manifest = verify_published_policy()
    sys.path.insert(0, str(POLICY))
    if args.worker_case:
        if args.state_root is None:
            parser.error("Worker requires state root")
        case = next(c for c in manifest["cases"] if c["case_id"] == args.worker_case)
        worker(case, args.state_root)
    elif args.check_only:
        from preflight_run_plan import check
        print(json.dumps({"preflight": check(POLICY / "RUN_MANIFEST.json", WORKSPACE),
            "resource": resource_admission(WORKSPACE, 0),
            "historical_wallets_started": 0}, indent=2))
    else:
        if args.state_root is None:
            parser.error("Controller requires state root")
        from preflight_run_plan import check
        require_input_preflight(check(POLICY / "RUN_MANIFEST.json", WORKSPACE))
        controller(args.state_root, manifest, go=args.parent_go)


if __name__ == "__main__":
    main()
