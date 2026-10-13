"""One-at-a-time bounded observer after terminal receipt, release, review and GO."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import resource
import re
import shutil
import subprocess
import sys
import time
from provenance import HERE, ROOT, MODULE, STATE, CASE_IDS, read, sha, verify_terminal_run, case_availability
from gate import verify_observer_go

AS_LIMIT = 4_000_000_000  # VAS limit; separate sampled RSS ceiling is 2GB.
CPU_LIMIT = 300
WALL_LIMIT = 360
RSS_LIMIT = 2_000_000_000
HOST_LIMIT = 8_000_000_000
DISK_RESERVE = 16_106_127_360
DISK_MARGIN = 250_000_000
HISTORICAL_MARKERS = ('coin_daily_reentry_ablation_20261013/run_cases.py',
    'coin_quantity_resolution_20261013/run_cases.py',
    'coin_margin_protective_runner_20261013/run_guard_cases.py')


def is_historical_python_command(args: list[str]) -> bool:
    if not args or not re.fullmatch(r'python(?:\d+(?:\.\d+)*)?', Path(args[0]).name):
        return False
    index = 1
    while index < len(args) and args[index].startswith('-'):
        flag = args[index]
        if flag in ('-c', '-m'):
            return False
        index += 2 if flag in ('-W', '-X') else 1
    return index < len(args) and any(args[index].endswith(marker) for marker in HISTORICAL_MARKERS)


def active_historical_processes(proc_root: Path = Path('/proc')) -> list[int]:
    pids = []
    for directory in proc_root.iterdir():
        if not directory.name.isdigit():
            continue
        try:
            args = (directory / 'cmdline').read_bytes().decode().split('\0')
            if is_historical_python_command(args):
                pids.append(int(directory.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError, UnicodeError):
            continue
    return sorted(pids)


def admission_check(mem: dict, external: dict, active_history: list[int], free: int,
                    allowed_cpus: list[int]) -> dict:
    if active_history:
        raise RuntimeError('Historical processes have not released: ' + str(active_history))
    if mem['SwapTotal'] or mem['active_swaps'] or mem.get('cgroup_swap_current'):
        raise RuntimeError('Postrun requires zero swap')
    reserved = external.get('external_reserved_bytes', 0)
    if mem['host_used'] + reserved + RSS_LIMIT > HOST_LIMIT:
        raise RuntimeError('No shared 2GB observer reservation under 8GB host cap')
    if (mem.get('cgroup_limit_verified') and
            mem['cgroup_memory_current'] + reserved + RSS_LIMIT > mem['cgroup_memory_max']):
        raise RuntimeError('Observer cgroup reservation unavailable')
    if free < DISK_RESERVE + DISK_MARGIN:
        raise RuntimeError('Observer 15GiB reserve plus output margin unavailable')
    cpus = sorted(set(allowed_cpus) - set(external.get('external_busy_cpus', [])))
    if not cpus:
        raise RuntimeError('No unoccupied allowed observer CPU')
    return {'memory': mem, 'external': external, 'historical_processes': [],
            'cpu': cpus[0], 'observer_RSS_commitment_bytes': RSS_LIMIT,
            'host_limit_bytes': HOST_LIMIT, 'disk_free_bytes': free,
            'disk_reserve_bytes': DISK_RESERVE, 'disk_margin_bytes': DISK_MARGIN,
            'cgroup_enforcement_claim': 'VERIFIED_LIMIT_OBSERVED' if mem.get('cgroup_limit_verified')
                else 'UNAVAILABLE_AND_UNVERIFIED_NO_CGROUP_ENFORCEMENT_CLAIM'}


def load_resource_helpers():
    path = ROOT / 'coin_margin_protective_runner_20261013/run_guard_cases.py'
    spec = importlib.util.spec_from_file_location('reentry_postrun_resource_transport', path)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    spec2 = importlib.util.spec_from_file_location('reentry_postrun_shared_resource_gate', MODULE / 'resource_gate.py')
    shared = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(shared)
    return guard, shared


def resource_admission(guard, shared):
    return admission_check(guard.memory_observation(), shared.external_observation(),
        active_historical_processes(), shutil.disk_usage(HERE).free, sorted(os.sched_getaffinity(0)))


def child_limits(cpu):
    resource.setrlimit(resource.RLIMIT_AS, (AS_LIMIT, AS_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT, CPU_LIMIT))
    os.sched_setaffinity(0, {cpu})


def runtime_stop(mem, peak, free, elapsed, active_history):
    return ('HISTORICAL_PROCESS_REAPPEARED' if active_history else
        'WORKER_RSS' if peak > RSS_LIMIT else 'HOST_USED' if mem['host_used'] > HOST_LIMIT else
        'SWAP' if mem['SwapTotal'] or mem['active_swaps'] else
        'CGROUP_SWAP' if mem.get('cgroup_swap_current') else
        'CGROUP_MEMORY' if mem.get('cgroup_limit_verified') and
            mem['cgroup_memory_current'] > mem['cgroup_memory_max'] else
        'DISK_RESERVE' if free < DISK_RESERVE else 'WALL_SECONDS' if elapsed > WALL_LIMIT else None)


def run_bounded(command, guard, shared):
    admission = resource_admission(guard, shared)
    cpu = admission['cpu']
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONOPTIMIZE='0',
        DAILY_REENTRY_POSTRUN_BOUNDED='1',
        DAILY_REENTRY_POSTRUN_GO_SHA256=sha(HERE / 'POSTRUN_GO.json'),
        OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
        POLARS_MAX_THREADS='1', NUMEXPR_NUM_THREADS='1', RAYON_NUM_THREADS='1', CUDA_VISIBLE_DEVICES='')
    proc = subprocess.Popen(command, env=env, preexec_fn=lambda: child_limits(cpu),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    began, peak, reason = time.monotonic(), 0, None
    last = admission['memory']
    try:
        while proc.poll() is None:
            last = guard.memory_observation()
            peak = max(peak, guard.process_rss(proc.pid))
            reason = runtime_stop(last, peak, shutil.disk_usage(HERE).free,
                                   time.monotonic() - began, active_historical_processes())
            external = shared.external_observation()
            if reason is None and (last['host_used'] + external['external_reserved_bytes']
                                   + RSS_LIMIT > HOST_LIMIT):
                reason = 'SHARED_EXTERNAL_RESOURCE_RESERVATION'
            if reason is None and cpu in external['external_busy_cpus']:
                reason = 'SHARED_EXTERNAL_CPU_CONFLICT'
            if reason:
                guard.terminate(proc)
                break
            time.sleep(.1)
        output, _ = proc.communicate(timeout=10)
    except BaseException:
        guard.terminate(proc)
        raise
    print(output, end='', flush=True)
    return {'exit_code': proc.returncode, 'stop_reason': reason, 'sampled_peak_RSS': peak,
        'peak_is_sampled_not_kernel_peak': True, 'elapsed_seconds': time.monotonic() - began,
        'admission': admission, 'last_memory_observation': last, 'one_CPU': cpu,
        'RLIMIT_AS_bytes': AS_LIMIT, 'RSS_ceiling_bytes': RSS_LIMIT,
        'RLIMIT_CPU_seconds': CPU_LIMIT, 'wall_limit_seconds': WALL_LIMIT}


def write_new(path, value):
    with path.open('x') as file:
        json.dump(value, file, indent=2, sort_keys=True, allow_nan=False)
        file.write('\n')


def main(stage: str):
    if sys.flags.optimize:
        raise RuntimeError('Frozen source assertions must be enabled')
    go = verify_observer_go(stage)
    go_text = (HERE / 'POSTRUN_GO.json').read_text()
    go_sha = sha(HERE / 'POSTRUN_GO.json')
    if __import__('hashlib').sha256(go_text.encode()).hexdigest() != go_sha:
        raise RuntimeError('Postrun GO changed while capturing authorization')
    if go.get('historical_controller_released') is not True:
        raise RuntimeError('Parent terminal resource release attestation required')
    verify_terminal_run()
    controller = read(STATE / 'RESOURCE_RECEIPTS.json')
    output_path = HERE / (stage + '_RESOURCE_RECEIPTS.json')
    if output_path.exists():
        raise FileExistsError('Never silently overwrite a postrun resource receipt')
    guard, shared = load_resource_helpers()
    receipts, remaining, failed = {}, [], False
    work = list(CASE_IDS) if stage == 'AUDIT' else ['FULL_THREE_CASE_REPORT']
    with shared.controller_lock():
        resource_admission(guard, shared)
        try:
            for index, identity in enumerate(work):
                remaining = work[index + 1:]
                if sha(HERE / 'POSTRUN_GO.json') != go_sha:
                    raise RuntimeError('Postrun GO changed during observer stage')
                if stage == 'AUDIT':
                    availability = case_availability(STATE, identity, controller)
                    if availability in ('UNSTARTED_NO_WALLET', 'STARTED_NO_RECOVERABLE_CHECKPOINT'):
                        unavailable = {'case_id': identity, 'status': availability,
                            'availability': availability, 'financial_advances': 0,
                            'historical_wallets_opened': 0, 'controls_rerun': 0,
                            'cold_restore_possible': False, 'observed_summary': None,
                            'observer_manifest_SHA256': sha(HERE / 'REVIEWED_POSTRUN_CODE.json'),
                            'postrun_GO_SHA256': sha(HERE / 'POSTRUN_GO.json'),
                            'input_files_SHA256': {
                                str((STATE / name).relative_to(ROOT)): sha(STATE / name)
                                for name in ('RUN_BINDING.json', 'RESOURCE_RECEIPTS.json')}}
                        (HERE / 'receipts').mkdir(exist_ok=True)
                        write_new(HERE / 'receipts' / (identity + '.json'), unavailable)
                        receipts[identity] = {**unavailable,
                            'cold_receipt_SHA256': sha(HERE / 'receipts' / (identity + '.json'))}
                        continue
                    if (HERE / 'receipts' / (identity + '.json')).exists():
                        raise FileExistsError('Never rerun or overwrite an existing cold receipt')
                    command = [sys.executable, str(HERE / 'cold_audit.py'), identity]
                else:
                    command = [sys.executable, str(HERE / 'build_report.py')]
                receipts[identity] = run_bounded(command, guard, shared)
                if sha(HERE / 'POSTRUN_GO.json') != go_sha:
                    raise RuntimeError('Postrun GO changed during observer stage')
                if receipts[identity]['exit_code'] != 0 or receipts[identity]['stop_reason'] is not None:
                    failed = True
                    raise RuntimeError('Bounded postrun observer failed: ' + identity)
                if stage == 'AUDIT':
                    receipts[identity]['cold_receipt_SHA256'] = sha(HERE / 'receipts' / (identity + '.json'))
        except BaseException:
            failed = True
            raise
        finally:
            write_new(output_path, {'status': 'STOP_PARTIAL' if failed else 'ALL_OBSERVERS_FINISHED',
                'stage': stage, 'case_ids': list(CASE_IDS), 'per_observer': receipts,
                'unstarted_observer_ids': remaining, 'financial_advances': 0,
                'historical_wallets_opened': 0, 'observer_manifest_SHA256': sha(HERE / 'REVIEWED_POSTRUN_CODE.json'),
                'postrun_GO_SHA256': go_sha, 'postrun_GO_text': go_text})
    print('POSTRUN_' + stage + '_FINISHED', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--parent-go', action='store_true')
    parser.add_argument('--stage', choices=('AUDIT', 'REPORT'), required=True)
    args = parser.parse_args()
    if not args.parent_go:
        parser.error('Separate reviewed postrun --parent-go is required')
    main(args.stage)
