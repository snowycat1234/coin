"""Single-worker durable continuation. Frozen finance and original STOP untouched."""
from __future__ import annotations
import argparse,gc,hashlib,importlib.util,json,os,resource,secrets,shutil,subprocess,sys,time
from pathlib import Path
from freeze_resume import verify,require_publication
from resume_limits import choose_cpu,require_live_cpu,require_combined_state,terminal_status
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'coin_earlier_terminal_exit_20261013'))
import run_cases as original
preflight=original.preflight;guard=original.guard;resource_gate=original.resource_gate
REVIEWED_FREEZE=original.REVIEWED_FREEZE
DAY=86_400_000_000
sha=original.sha;write_new=original.write_new

def resume_plan():
    verify();plan=json.loads((HERE/'RESUME_PLAN.json').read_text())
    state=ROOT/plan['original_state_locator']
    if plan['max_parallel']!=1 or plan['new_wallets']!=0 or len(plan['cases'])!=2:raise ValueError('Exact serial continuation plan')
    if sha(state/'RESOURCE_RECEIPTS.json')!=plan['original_STOP_receipt_SHA256'] or sha(state/'RUN_BINDING.json')!=plan['original_RUN_BINDING_SHA256']:raise ValueError('Original STOP/RUN changed')
    if sha(ROOT/plan['original_module_locator']/'FROZEN_CODE.json')!=plan['original_freeze_SHA256']:raise ValueError('Original financial freeze changed')
    for case in plan['cases']:
        p=ROOT/case['source_state_locator']
        if sha(p/'recovery/POINTER.json')!=case['source_pointer_SHA256'] or sha(p/'BINDING.json')!=case['source_binding_SHA256']:raise ValueError('Original durable anchor changed')
        if case['resume_wall_seconds']>1200-__import__('math').ceil(case['original_elapsed_seconds']) or case['resume_CPU_seconds']!=case['resume_wall_seconds']:raise ValueError('Cumulative1200 budget expansion')
    return plan

def verify_restored(sim,snapshot,pointer,case,weights,clocks):
    import numpy as np
    if (sim.state_hash()!=case['source_state_hash'] or sim.state_hash()!=pointer['state_hash']
        or sim.cursor!=case['source_cursor_us'] or sim.rows_written!=case['durable_completed_minutes']
        or sim.stop is not None or sim.account.status not in ('ACTIVE','BOUND_BREACH_REDUCTION_REQUIRED')
        or sim.account.snapshot()!=snapshot['account']):raise ValueError('Exact original durable finance differs')
    for key in ('event_cursor','previous_quote','terminal','sequence','funding_journal','rejections','breaches','extrema','target_rows'):
        if getattr(sim,key)!=snapshot['state'][key]:raise ValueError('Durable scheduling field differs: '+key)
    pending={s:{**o,'target':str(o['target'])} for s,o in sim.pending.items()}
    if pending!=snapshot['state']['pending']:raise ValueError('Durable pending intents differ')
    for live,saved in zip(sim.minute_chunks,snapshot['minute_chunks']):np.testing.assert_array_equal(live,saved)
    np.testing.assert_array_equal(sim.targets['target_weight'].to_numpy().reshape(-1,5),weights)
    np.testing.assert_array_equal(sorted(sim.weights),clocks)
    for i,t in enumerate(clocks):np.testing.assert_array_equal([sim.weights[int(t)][s] for s in sim.symbols],weights[i])
    return dict(state_hash=sim.state_hash(),rows=sim.rows_written,cursor=sim.cursor,financial_advances=0)

def require_worker(state_root,case,manifest):
    plan=resume_plan();publication=require_publication()
    if state_root.resolve()!=(ROOT/plan['destination_state_locator']).resolve():raise ValueError('Only exact authorized resumed root')
    run=json.loads((state_root/'RECOVERY_RUN_BINDING.json').read_text())
    if (run['nonce']!=os.environ.get('COIN_TERMINAL_RESUME_NONCE') or not run['parent_GO']
        or run['recovery_manifest_SHA256']!=sha(HERE/'FROZEN_RECOVERY.json')
        or run['review_receipt_SHA256']!=sha(HERE/'REVIEW_RECEIPT.json')
        or run['recovery_publication_receipt_SHA256']!=publication['receipt_SHA256']
        or os.environ.get('COIN_TERMINAL_RESUME_BOUNDED')!='1'):raise RuntimeError('New exact resume GO/controller binding missing')
    if (len(os.sched_getaffinity(0))!=1 or any(not 0<n<=guard.WORKER_AS_LIMIT for n in resource.getrlimit(resource.RLIMIT_AS))
        or any(not 0<n<=case['resume_CPU_seconds'] for n in resource.getrlimit(resource.RLIMIT_CPU))):raise RuntimeError('Finite original remaining CPU/AS/oneCPU bounds required')

def worker(case: dict, mode: str, state_root: Path) -> None:
    manifest=verify(require_review=True)
    plan=resume_plan();rc=next(c for c in plan['cases'] if c['case_id']==case['case_id'])
    require_worker(state_root,rc,manifest)
    run_binding=json.loads((state_root/'RUN_BINDING.json').read_text())
    identity=rc['identity']
    import numpy as np
    port, source, _unused_guard_class = guard.load_port(case["year"])
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
    original_state=ROOT/rc['source_state_locator']
    binding=json.loads((original_state/'BINDING.json').read_text())
    state=state_root/identity;state.mkdir()
    (state/'BINDING.json').write_bytes((original_state/'BINDING.json').read_bytes())
    if sha(state/'BINDING.json')!=rc['source_binding_SHA256']:raise ValueError('Original binding bytes changed')
    write_new(state/'RECOVERY_BINDING.json',dict(original_pointer_SHA256=rc['source_pointer_SHA256'],
        original_snapshot_SHA256=rc['source_snapshot_SHA256'],original_state_hash=rc['source_state_hash'],
        original_durable_cursor=rc['source_cursor_us'],recovery_code_manifest_SHA256=sha(HERE/'FROZEN_RECOVERY.json'),
        recovery_run_binding_SHA256=sha(state_root/'RECOVERY_RUN_BINDING.json'),new_wallets=0,new_variants=0))

    def target_factory(_daily, decision_us, target_mode):
        np.testing.assert_array_equal(decision_us, clocks)
        if target_mode != "LONG_SHORT":
            raise ValueError("Target mode changed")
        frame = port.native.pl.DataFrame([{
            "available_us": int(stamp), "symbol": symbol,
            "target_weight": float(weights[i, j])}
            for i, stamp in enumerate(clocks) for j, symbol in enumerate(source["symbols"])])
        return frame, {"kind": "EXACT_FROZEN_ORIGINAL_TARGET_TERMINAL60", "binding": binding}

    from terminal_adapter import EarlierTerminalSimulator
    Simulator = EarlierTerminalSimulator
    snapshot,pointer=port.restore_snapshot(original_state/'recovery',binding)
    original_advance=Simulator.advance_day
    def forbidden(*_a,**_kw):raise RuntimeError('Durable restoration cannot advance finance')
    Simulator.advance_day=forbidden
    try:sim=Simulator.from_snapshot(snapshot,source,account_class=FineGridAccount)
    finally:Simulator.advance_day=original_advance
    verify_restored(sim,snapshot,pointer,rc,weights,clocks)
    begun = time.monotonic()
    port.checkpoint(state / "recovery", sim, binding)
    print("TERMINAL60_RESUME_WALLET_STARTED", identity, flush=True)
    while sim.cursor < source["end"] and sim.stop is None:
        sim.advance_day()
        days = len(sim.minute_chunks)
        if days % 30 == 0 or sim.stop is not None or sim.cursor == source["end"]:
            port.checkpoint(state / "recovery", sim, binding)
            if require_combined_state(guard.case_state_bytes(original_state),guard.case_state_bytes(state)) > guard.CASE_LIMIT:
                raise RuntimeError("250MB state cap; genuine partial state retained")
            print("TERMINAL60_RESUME_WALLET_PROGRESS", identity, days, float(sim.account.nav()),
                  sim.account.status, flush=True)
        if time.monotonic() - begun > rc['resume_wall_seconds'] - 45:
            port.checkpoint(state / "recovery", sim, binding)
            raise RuntimeError("Cumulative1200-second wallet cap; genuine partial retained")
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
    if require_combined_state(guard.case_state_bytes(original_state),guard.case_state_bytes(state)) > guard.CASE_LIMIT:
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
               "terminal_opens": 60, "terminal_signal_us": sim.terminal_signal_us,
               "daily_observed_days": len(nav) - 1,
               "status": "COMPLETE_PAID_FLAT" if paid else "FULL_NOT_PAID_OR_NOT_EVALUABLE" if full else "STOP_PARTIAL"}
    write_new(state / "RESULT.json", compact)
    write_new(state / "TIMING.json", {"resume_financial_seconds": time.monotonic() - begun, "original_elapsed_seconds": rc["original_elapsed_seconds"], "remaining_worker_wall_and_CPU_seconds": rc["resume_wall_seconds"], "new_wallets": 0})
    print("TERMINAL60_RESUME_WALLET_RESULT", identity, compact["status"], compact["marked_PnL_USDT"], flush=True)
    del sim, result, minute, daily
    gc.collect()


def controller():
    verify(require_review=True);publication=require_publication();plan=resume_plan();preflight.check();preflight.require_publication()
    state=ROOT/plan['destination_state_locator']
    if state.exists() or (HERE/'RECOVERY_STARTED.json').exists():raise RuntimeError('Exactly one interrupted-case continuation; no duplicate resume')
    admission=resource_gate.admission(state.parent,0,guard)
    # Original financial identity is preserved. New operational authorization
    # and completion live in separate sidecars, never in the original STOP.
    state.mkdir();(state/'RUN_BINDING.json').write_bytes((ROOT/plan['original_state_locator']/'RUN_BINDING.json').read_bytes())
    nonce=secrets.token_hex(16)
    write_new(state/'RECOVERY_RUN_BINDING.json',dict(parent_GO=True,nonce=nonce,
        recovery_manifest_SHA256=sha(HERE/'FROZEN_RECOVERY.json'),review_receipt_SHA256=sha(HERE/'REVIEW_RECEIPT.json'),
        recovery_publication_receipt_SHA256=publication['receipt_SHA256'],
        original_STOP_receipt_SHA256=plan['original_STOP_receipt_SHA256'],original_RUN_BINDING_SHA256=plan['original_RUN_BINDING_SHA256'],
        source_anchor_hashes={c['identity']:c['source_pointer_SHA256'] for c in plan['cases']},max_parallel=1,
        original_complete_RESUME_case_ids=[c['identity'] for c in plan['cases']],new_wallets=0,new_variants=0,initial_resource_admission=admission))
    write_new(HERE/'RECOVERY_STARTED.json',dict(destination_state=plan['destination_state_locator'],recovery_run_binding_SHA256=sha(state/'RECOVERY_RUN_BINDING.json')))
    receipts={};failed=False;remaining=list(plan['cases']);cpus=admission['allowed_cpus'];cpu=cpus[0]
    try:
        for rc in plan['cases']:
            if failed:break
            current=resource_gate.admission(state,0,guard);cpu=choose_cpu(current)
            log=(state/(rc['identity']+'.log')).open('x')
            env=dict(os.environ,COIN_TERMINAL_RESUME_BOUNDED='1',COIN_TERMINAL_RESUME_NONCE=nonce,
                CUDA_VISIBLE_DEVICES='',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
                POLARS_MAX_THREADS='1',NUMEXPR_NUM_THREADS='1',RAYON_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',PYTHONOPTIMIZE='0')
            def limits():
                guard.child_limits(cpu)
                resource.setrlimit(resource.RLIMIT_CPU,(rc['resume_CPU_seconds'],rc['resume_CPU_seconds']))
            begun=time.monotonic();peak=0;reason=None
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker-case',rc['case_id']],
                stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,preexec_fn=limits)
            remaining.pop(0);print('RESUME_CASE_STARTED',rc['identity'],proc.pid,cpu,rc['source_cursor_us'],rc['resume_wall_seconds'],flush=True)
            try:
                while proc.poll() is None:
                    peak=max(peak,guard.process_rss(proc.pid));mem=guard.memory_observation();free=shutil.disk_usage(state).free
                    reason=('HOST_USED' if mem['host_used']>guard.HOST_USED_LIMIT else 'SWAP' if mem['SwapTotal'] or mem['active_swaps'] else
                        'CGROUP_SWAP' if mem.get('cgroup_swap_current',0) else 'WORKER_RSS' if peak>guard.WORKER_RSS_LIMIT else
                        'DISK_RESERVE' if free<guard.DISK_RESERVE else 'CUMULATIVE_WALL_1200' if time.monotonic()-begun>rc['resume_wall_seconds'] else None)
                    if reason is None:
                        try:
                            external=resource_gate.external_observation()
                            resource_gate.check_external({'memory':mem,'allowed_cpus':sorted(os.sched_getaffinity(0))},external,0,guard)
                            require_live_cpu(cpu,external)
                            original_state=ROOT/rc['source_state_locator'];destination_state=state/rc['identity']
                            require_combined_state(guard.case_state_bytes(original_state),guard.case_state_bytes(destination_state))
                        except RuntimeError as err:reason='SHARED_RESOURCE_CONFLICT:'+str(err)
                    if reason:guard.terminate(proc);break
                    time.sleep(.1)
            finally:
                if proc.poll() is None:guard.terminate(proc)
                log.close()
                elapsed=time.monotonic()-begun
                receipts[rc['identity']]=dict(exit_code=proc.returncode,stop_reason=reason,peak_RSS=peak,cpu=cpu,
                    resume_elapsed_seconds=elapsed,original_elapsed_seconds=rc['original_elapsed_seconds'],
                    cumulative_case_elapsed_seconds=elapsed+rc['original_elapsed_seconds'],remaining_CPU_limit=rc['resume_CPU_seconds'],
                    peak_is_sampled_not_kernel_peak=True,new_wallets=0)
            print('RESUME_CASE_DONE',rc['identity'],proc.returncode,reason,flush=True)
            if proc.returncode or reason:failed=True
    except BaseException:
        failed=True
        raise
    finally:
        write_new(state/'RESOURCE_RECEIPTS.json',dict(status=terminal_status(failed,remaining),
            completion_scope='RECOVERY_OF_TWO_ORIGINAL_INTERRUPTED_CASES_NOT_NEW_BATCH',max_parallel=1,
            original_STOP_preserved=True,original_STOP_receipt_SHA256=plan['original_STOP_receipt_SHA256'],
            original_STATE_untouched=True,per_case=receipts,unstarted_case_ids=[c['identity'] for c in remaining]))
    if failed or remaining:raise RuntimeError('Recovery stopped; original and recovery genuine checkpoints preserved')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');parser.add_argument('--parent-go',action='store_true');parser.add_argument('--worker-case');args=parser.parse_args()
    if args.check_only:
        if args.parent_go or args.worker_case:parser.error('Check-only cannot advance finance')
        plan=resume_plan();print(json.dumps(dict(status='PASS_EXACT_INTERRUPTED_CASE_PLAN_ZERO_ADVANCE',cases=plan['cases'],resource=resource_gate.admission(ROOT,0,guard),source=preflight.check()),indent=2));return
    if args.worker_case:
        plan=resume_plan();case=next((c for c in preflight.bindings()['cases'] if c['case_id']==args.worker_case),None)
        if case is None:parser.error('Case outside original two-arm experiment')
        worker(case,'ORIGINAL',ROOT/plan['destination_state_locator']);return
    if not args.parent_go:parser.error('Separate exact-byte parent GO required for durable continuation')
    with resource_gate.controller_lock():controller()
if __name__=='__main__':main()
