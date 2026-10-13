"""One small observer, using existing shared admission and resource primitives."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RSS = 2_000_000_000
AS = 4_000_000_000
CPU = 300
WALL = 360


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def save(path, value):
    with path.open('x') as file:
        json.dump(value, file, indent=2, sort_keys=True, allow_nan=False)
        file.write('\n')


def main(args):
    from cold_audit import sha
    if sys.flags.optimize or not args.controller_released:
        raise RuntimeError('Assertions and explicit terminal controller release required')
    if sha(HERE/'cold_audit.py') != args.observer_sha256:
        raise ValueError('Expected reviewed observer SHA differs')
    guard = load('headroom_audit_resource_primitives', ROOT/'coin_margin_protective_runner_20261013/run_guard_cases.py')
    shared = load('headroom_audit_shared_admission', ROOT/'coin_headroom_risk_candidate_20261013/resource_gate.py')
    label = f'Y{args.year}_STATIC50_FINE_HEADROOM_{args.attempt}'
    log_path, resource_path = HERE/(label+'.log'), HERE/(label+'_RESOURCE.json')
    if log_path.exists() or resource_path.exists():
        raise FileExistsError('Retain prior audit attempt; choose a fresh attempt label')
    state_root = args.state_root.resolve()
    if not (state_root/'RESOURCE_RECEIPTS.json').is_file():
        raise RuntimeError('Terminal historical resource receipt absent')
    with shared.controller_lock():
        admission = shared.admission(HERE, 0, guard)
        cpu = admission['allowed_cpus'][0]
        def limits():
            os.sched_setaffinity(0, {cpu})
            resource.setrlimit(resource.RLIMIT_AS, (AS, AS))
            resource.setrlimit(resource.RLIMIT_CPU, (CPU, CPU))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONOPTIMIZE='0',
                   OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
                   POLARS_MAX_THREADS='1', NUMEXPR_NUM_THREADS='1', RAYON_NUM_THREADS='1', CUDA_VISIBLE_DEVICES='')
        command = [sys.executable, str(HERE/'cold_audit.py'), '--state-root', str(state_root), '--year', str(args.year), '--controller-released']
        began, peak, reason, proc = time.monotonic(), 0, None, None
        with log_path.open('x') as log:
            try:
                proc = subprocess.Popen(command, env=env, preexec_fn=limits, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                while proc.poll() is None:
                    mem, external = guard.memory_observation(), shared.external_observation()
                    rss = guard.process_rss(proc.pid); peak = max(peak, rss)
                    reason = ('HISTORICAL_PROCESS_REAPPEARED' if external['prior_historical_processes'] else
                        'WORKER_RSS' if peak > RSS else
                        'HOST_COMMITTED' if mem['host_used']+external['external_reserved_bytes']+max(0, RSS-rss) > guard.HOST_USED_LIMIT else
                        'SWAP' if mem['SwapTotal'] or mem['active_swaps'] or mem.get('cgroup_swap_current', 0) else
                        'CGROUP_MEMORY' if mem.get('cgroup_limit_verified') and mem['cgroup_memory_current'] > mem['cgroup_memory_max'] else
                        'DISK_RESERVE' if shutil.disk_usage(HERE).free < guard.DISK_RESERVE else
                        'EXTERNAL_CPU_CONFLICT' if cpu in external['external_busy_cpus'] else
                        'WALL_SECONDS' if time.monotonic()-began > WALL else None)
                    if reason:
                        guard.terminate(proc)
                        break
                    time.sleep(.1)
                proc.wait(timeout=10)
            finally:
                if proc is not None and proc.poll() is None:
                    guard.terminate(proc)
                save(resource_path, {'exit_code': proc.returncode if proc else None, 'stop_reason': reason,
                    'elapsed_seconds': time.monotonic()-began, 'sampled_peak_RSS': peak,
                    'peak_is_sampled_not_kernel_peak': True, 'one_CPU': cpu, 'RLIMIT_AS_bytes': AS,
                    'RLIMIT_CPU_seconds': CPU, 'RSS_ceiling_bytes': RSS, 'wall_limit_seconds': WALL,
                    'admission': admission, 'observer_code_SHA256': args.observer_sha256,
                    'financial_advances': 0, 'historical_wallets_opened': 0})
    print(log_path.read_text(), end='', flush=True)
    if proc.returncode or reason:
        raise RuntimeError('Retained failed read-only audit: ' + label)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-root', type=Path, required=True)
    parser.add_argument('--year', type=int, choices=(2021, 2023), required=True)
    parser.add_argument('--controller-released', action='store_true')
    parser.add_argument('--observer-sha256', required=True)
    parser.add_argument('--attempt', default='attempt001')
    main(parser.parse_args())
