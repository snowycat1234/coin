"""GO-gated three fixed headroom wallets, one worker per executor; no preflight history.

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

from freeze_candidate import verify as verify_reviewed_freeze

# This stdlib-only byte check precedes imports of the financial account,
# frozen transport, scheduler and protective policy. Workers repeat it.
REVIEWED_FREEZE = None

import preflight
import resource_gate
from run_budget import ensure_single_unstarted_batch
from worker_bounds import require_worker_bounds

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
guard = None
DAY = 86_400_000_000


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, obj) -> None:
    with path.open("x", encoding="utf-8") as file:
        json.dump(obj, file, indent=2, sort_keys=True, allow_nan=False)
        file.write("\n")


def state_root_ok(path: Path) -> None:
    if not path.is_absolute() or not path.name.startswith('state') or path.is_symlink() or not path.parent.is_dir():
        raise ValueError('Explicit absolute fresh state* output with existing parent required')


def worker(case: dict, mode: str, state_root: Path, workspace: Path, source_root=None, target_archive=None, feature_archive=None) -> None:
    global REVIEWED_FREEZE
    REVIEWED_FREEZE = verify_reviewed_freeze(workspace, require_review=True)
    state_root_ok(state_root)
    run_binding = json.loads((state_root / "RUN_BINDING.json").read_text())
    identity = f"{case['case_id']}_FINE_{mode}"
    if (not run_binding.get("parent_GO") or identity not in run_binding["fine_case_ids"]
            or run_binding["nonce"] != os.environ.get("COIN_HEADROOM_NONCE")
            or run_binding["runner_SHA256"] != sha(Path(__file__))
            or run_binding["bindings_SHA256"] != sha(HERE / "CASE_BINDINGS.json")
            or run_binding["freeze_manifest_SHA256"] != REVIEWED_FREEZE["freeze_manifest_SHA256"]
            or run_binding["fine_account_SHA256"] != sha(workspace / "coin_quantity_resolution_20261013/fine_account.py")
            or run_binding['review_receipt_SHA256'] != sha(HERE/'REVIEW_RECEIPT.json')
            or run_binding['publication_receipt_SHA256'] != preflight.require_publication()['publication_receipt_SHA256']
            or os.environ.get("COIN_HEADROOM_BOUNDED") != "1"):
        raise RuntimeError("Parent GO/controller worker binding missing")
    require_worker_bounds(os.sched_getaffinity(0),resource.getrlimit(resource.RLIMIT_AS),resource.getrlimit(resource.RLIMIT_CPU))
    if mode != "HEADROOM": raise ValueError("Only fixed HEADROOM mode allowed")
    preflight.require_publication()
    import numpy as np
    from source_adapter import load_port, source_window
    from feature_tape import FeatureTape
    source_path,target_path,feature_path = preflight.paths(case,workspace,source_root,target_archive,feature_archive)
    port = load_port(workspace)
    source = source_window(case, source_path, port, workspace)
    feature_manifest=json.loads((HERE/"features"/f"Y{case['year']}.json").read_text())
    source["headroom_features"]=FeatureTape.load(feature_path,feature_manifest)
    from fine_account import FineGridAccount, profile_sha
    if profile_sha() != run_binding["fine_profile_SHA256"]:
        raise ValueError("Fine profile identity changed")
    if (sha(source_path / "SOURCE_INDEX.json") != case["source_index_SHA256"]
            or sha(target_path) != case["target_archive_SHA256"]):
        raise ValueError("Source/target archive changed")
    with np.load(target_path, allow_pickle=False) as archive:
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
               "fine_account_SHA256": sha(workspace / "coin_quantity_resolution_20261013/fine_account.py"),
               "freeze_manifest_SHA256": REVIEWED_FREEZE["freeze_manifest_SHA256"],
               "feature_binding": source["headroom_features"].binding,
               "source_root":str(source_path.resolve()),"target_archive":str(target_path.resolve()),
               "terminal_opens":5, "terminal_signal_us":source["end"]-6*60_000_000,
               "headroom_adapter_SHA256":sha(HERE/"headroom_policy.py"),
               "guard_policy_SHA256": sha(workspace / "coin_margin_protective_policy_20261013/protective_policy.py"),
               "scheduler_SHA256": sha(workspace / "coin_native_half_mix_20261013/repo/scripts/investment/resumable_perpetual.py"),
               "account_SHA256": sha(workspace / "coin_native_half_mix_20261013/repo/src/quant/perpetual_account.py"),
               "run_binding_SHA256": sha(state_root / "RUN_BINDING.json"),
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
        return frame, {"kind": "EXACT_ORIGINAL_STATIC50_CSH_HEADROOM_ONLY", "binding": binding}

    from headroom_policy import HeadroomFullExitSimulator
    Simulator = HeadroomFullExitSimulator
    sim = Simulator(source, "LONG_SHORT", port.native.COSTS[0], port.native.UNITS[0],
                    target_factory=target_factory, account_factory=FineGridAccount,
                    persist_cash_close=False, final_day_target_zero=False)
    if type(sim.account) is not FineGridAccount or sim.account.nav() != 10000:
        raise ValueError("Fresh 10,000 USDT fine-grid account differs")
    begun = time.monotonic()
    port.checkpoint(state / "recovery", sim, binding)
    print("HEADROOM_WALLET_STARTED", identity, flush=True)
    while sim.cursor < source["end"] and sim.stop is None:
        sim.advance_day()
        days = len(sim.minute_chunks)
        if days % 30 == 0 or sim.stop is not None or sim.cursor == source["end"]:
            port.checkpoint(state / "recovery", sim, binding)
            if guard.case_state_bytes(state) > guard.CASE_LIMIT:
                raise RuntimeError("250MB state cap; genuine partial state retained")
            print("HEADROOM_WALLET_PROGRESS", identity, days, float(sim.account.nav()),
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
    compact = {"case_id": identity, "mode": mode, "year": case["year"], "arm": case["arm"],
               "full_calendar": full, "paid_flat": paid,
               "paid_cash_PnL_USDT": summary["net_PnL"] if paid else None,
               "marked_PnL_USDT": summary["net_PnL"],
               "marked_return": summary["net_PnL"] / 10000,
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
    print("HEADROOM_WALLET_RESULT", identity, compact["status"], compact["marked_PnL_USDT"], flush=True)
    del sim, result, minute, daily
    gc.collect()


def controller(args, plan):
    """One bounded worker at a time, using the reviewed existing resource primitives."""
    workspace=args.workspace_root.resolve();state=args.state_root.resolve()
    state_root_ok(state)
    if state.exists() or (HERE/'HISTORICAL_LAUNCH.json').exists():
        raise RuntimeError('Fixed executor batch already reserved; no duplicate historical wallet')
    selected=[c for c in plan['cases'] if c['year'] in args.years]
    verify_reviewed_freeze(workspace,require_review=True)
    publication=preflight.require_publication()
    inputs=preflight.check(workspace,args.years,args.source_root,args.target_archive,args.feature_archive)
    admission=resource_gate.admission(state.parent,0,guard)
    state.mkdir();nonce=secrets.token_hex(16)
    freeze=verify_reviewed_freeze(workspace,require_review=True)
    write_new(state/'RUN_BINDING.json',{'parent_GO':True,'nonce':nonce,'max_parallel':1,
        'runner_SHA256':sha(Path(__file__)),'bindings_SHA256':sha(HERE/'CASE_BINDINGS.json'),
        'freeze_manifest_SHA256':freeze['freeze_manifest_SHA256'],
        'fine_account_SHA256':sha(workspace/'coin_quantity_resolution_20261013/fine_account.py'),
        'fine_profile_SHA256':plan['fine_profile_SHA256'],
        'fine_case_ids':[c['case_id']+'_FINE_HEADROOM' for c in selected],
        'review_receipt_SHA256':sha(HERE/'REVIEW_RECEIPT.json'),**publication,
        'workspace_root':str(workspace),'input_paths':inputs['selected_cases'],'initial_resource_admission':admission})
    write_new(HERE/'HISTORICAL_LAUNCH.json',{'state_root':str(state),'run_binding_SHA256':sha(state/'RUN_BINDING.json'),
        'selected_years':args.years,'reserved_candidate_wallets':len(selected)})
    receipts={};remaining=list(selected);failed=False
    try:
        for case in selected:
            if failed:break
            current=resource_gate.admission(state,0,guard);cpu=current['allowed_cpus'][0]
            identity=case['case_id']+'_FINE_HEADROOM';log=(state/(identity+'.log')).open('x')
            env=dict(os.environ,COIN_HEADROOM_BOUNDED='1',COIN_HEADROOM_NONCE=nonce,COIN_HEADROOM_WORKSPACE=str(workspace),
                CUDA_VISIBLE_DEVICES='',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
                POLARS_MAX_THREADS='1',NUMEXPR_NUM_THREADS='1',RAYON_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',PYTHONOPTIMIZE='0')
            command=[sys.executable,str(Path(__file__).resolve()),'--worker-case',case['case_id'],
                '--state-root',str(state),'--workspace-root',str(workspace)]
            for flag,value in (('--source-root',args.source_root),('--target-archive',args.target_archive),('--feature-archive',args.feature_archive)):
                if value:command += [flag,str(value.resolve())]
            begun=time.monotonic();peak=0;reason=None
            proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,
                preexec_fn=lambda:guard.child_limits(cpu))
            remaining.pop(0);print('HEADROOM_CASE_STARTED',identity,proc.pid,cpu,flush=True)
            try:
                while proc.poll() is None:
                    rss=guard.process_rss(proc.pid);peak=max(peak,rss);mem=guard.memory_observation()
                    external=resource_gate.external_observation();reserve=max(0,guard.WORKER_RSS_LIMIT-rss)
                    # Current worker RSS is already in host_used. Reserve only
                    # its unused allowance, not a duplicate second full2GB.
                    reason=('HOST_USED_PLUS_REMAINING_RESERVE' if mem['host_used']+external['external_reserved_bytes']+reserve>guard.HOST_USED_LIMIT else
                        'SWAP' if mem['SwapTotal'] or mem['active_swaps'] or mem.get('cgroup_swap_current',0) else
                        'WORKER_RSS' if peak>guard.WORKER_RSS_LIMIT else
                        'CGROUP_MEMORY' if mem.get('cgroup_limit_verified') and mem['cgroup_memory_current']>mem['cgroup_memory_max'] else
                        'DISK_RESERVE' if shutil.disk_usage(state).free<guard.DISK_RESERVE else
                        'WALL_1200' if time.monotonic()-begun>guard.WALL_LIMIT else
                        'EXTERNAL_HISTORY' if external['prior_historical_processes'] else
                        'EXTERNAL_CPU' if cpu in external['external_busy_cpus'] else
                        'STATE250MB' if guard.case_state_bytes(state/identity)>guard.CASE_LIMIT else None)
                    if reason:guard.terminate(proc);break
                    time.sleep(.1)
            finally:
                if proc.poll() is None:guard.terminate(proc)
                log.close();receipts[identity]={'exit_code':proc.returncode,'stop_reason':reason,'peak_RSS':peak,
                    'cpu':cpu,'elapsed_seconds':time.monotonic()-begun,'peak_is_sampled_not_kernel_peak':True}
            failed=bool(proc.returncode or reason)
            print('HEADROOM_CASE_DONE',identity,proc.returncode,reason,flush=True)
    except BaseException:
        failed=True;raise
    finally:
        write_new(state/'RESOURCE_RECEIPTS.json',{'status':'STOP_PARTIAL' if failed or remaining else 'ALL_CASES_FINISHED',
            'max_parallel':1,'per_case':receipts,'unstarted_case_ids':[c['case_id']+'_FINE_HEADROOM' for c in remaining]})
    if failed or remaining:raise RuntimeError('Retained genuine partial state; no automatic new wallet or variant')


def main():
    global guard
    parser=argparse.ArgumentParser()
    parser.add_argument('--check-only',action='store_true');parser.add_argument('--parent-go',action='store_true')
    parser.add_argument('--years',type=int,nargs='+',default=[2021,2023,2024],choices=[2021,2023,2024])
    parser.add_argument('--workspace-root',type=Path,default=ROOT)
    parser.add_argument('--source-root',type=Path);parser.add_argument('--target-archive',type=Path)
    parser.add_argument('--feature-archive',type=Path);parser.add_argument('--state-root',type=Path)
    parser.add_argument('--worker-case');parser.add_argument('--rebuild-features',type=Path);parser.add_argument('--derived-csv',type=Path)
    args=parser.parse_args();workspace=args.workspace_root.resolve();os.environ['COIN_HEADROOM_WORKSPACE']=str(workspace)
    verify_reviewed_freeze(workspace)
    path=workspace/'coin_margin_protective_runner_20261013/run_guard_cases.py'
    spec=importlib.util.spec_from_file_location('candidate_guard_resource_primitives',path)
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.require_assertions_enabled()
    plan=preflight.bindings()
    if args.rebuild_features:
        if args.parent_go or args.worker_case or args.state_root or len(args.years)!=1 or args.source_root is None:
            parser.error('Source-only rebuild selects one year, source-root and fresh output, never parent-go/state')
        from source_adapter import rebuild_features
        case=next(c for c in plan['cases'] if c['year']==args.years[0])
        print(json.dumps(rebuild_features(case,args.source_root,args.rebuild_features,args.derived_csv),indent=2));return
    if args.check_only:
        if args.parent_go or args.worker_case or args.state_root:parser.error('Check-only cannot launch a wallet')
        print(json.dumps(preflight.check(workspace,args.years,args.source_root,args.target_archive,args.feature_archive),indent=2));return
    if args.worker_case:
        if args.parent_go or args.state_root is None:parser.error('Worker needs existing controller-bound state')
        case=next((c for c in plan['cases'] if c['case_id']==args.worker_case),None)
        if case is None:parser.error('Worker outside exactly3 fixed cases')
        worker(case,'HEADROOM',args.state_root.resolve(),workspace,args.source_root,args.target_archive,args.feature_archive);return
    if not args.parent_go or args.state_root is None:parser.error('Historical execution requires separate parent-go and fresh explicit output')
    with resource_gate.controller_lock():controller(args,plan)

if __name__=='__main__':main()

