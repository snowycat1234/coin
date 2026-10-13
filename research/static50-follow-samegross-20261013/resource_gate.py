"""Shared conservative resource admission; accounts for the active guard pack."""
from __future__ import annotations
from contextlib import contextmanager
import fcntl
import os
import json
from pathlib import Path

PACK_RELATIVE = 'coin_margin_guard_lossless_pack_20261013/pack_minimal_guard.py'
PACK_VERIFY_RELATIVE = 'coin_margin_guard_lossless_pack_20261013/verify_restored_native.py'
RELEASE_PATH = Path(__file__).resolve().parent / 'GUARD_PACK_RELEASE.json'
PRIOR_RUNNERS = ('coin_quantity_resolution_20261013/run_cases.py',
                 'coin_daily_reentry_ablation_20261013/run_cases.py',
                 'coin_margin_protective_runner_20261013/run_guard_cases.py')
PACK_RESERVED_BYTES = 2_000_000_000
LOCK_PATH = Path('/tmp/coin_offline_financial_controller.lock')

def task_reservation(release_path: Path = RELEASE_PATH):
    # PID disappearance is never evidence that the whole pack/restore/audit
    # task has released its reservation. Only the parent's explicit receipt.
    if not release_path.exists():
        return {'pack_task_released': False, 'task_reserved_bytes': PACK_RESERVED_BYTES,
                'task_busy_cpus': [8], 'release_receipt_SHA256': None}
    release = json.loads(release_path.read_text())
    if (release.get('status') != 'VERIFIED_GUARD_PACK_TASK_RELEASED_BY_PARENT'
            or release.get('pack_complete') is not True
            or release.get('restored_files_verified') != 4053
            or release.get('native_zero_advance_wallets_verified') != 11
            or release.get('heavy_work_released') is not True):
        raise RuntimeError('Guard-pack task release receipt is invalid')
    import hashlib
    return {'pack_task_released': True, 'task_reserved_bytes': 0, 'task_busy_cpus': [],
            'release_receipt_SHA256': hashlib.sha256(release_path.read_bytes()).hexdigest()}

def external_observation(proc_root: Path = Path('/proc')):
    packs, histories = [], []
    for directory in proc_root.iterdir():
        if not directory.name.isdigit():
            continue
        try:
            args = (directory / 'cmdline').read_bytes().decode().split('\0')
            if any(arg.endswith(PACK_RELATIVE) or arg.endswith(PACK_VERIFY_RELATIVE) for arg in args):
                pid = int(directory.name)
                packs.append({'pid': pid, 'reserved_bytes': PACK_RESERVED_BYTES,
                              'allowed_cpus': sorted(os.sched_getaffinity(pid))})
            elif any(any(arg.endswith(marker) for marker in PRIOR_RUNNERS) for arg in args):
                histories.append(int(directory.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError, UnicodeError):
            continue
    task = task_reservation()
    return {**task, 'guard_pack_processes': packs, 'prior_historical_processes': histories,
            'external_reserved_bytes': max(task['task_reserved_bytes'], len(packs) * PACK_RESERVED_BYTES),
            'external_busy_cpus': sorted(set(task['task_busy_cpus']) |
                {cpu for row in packs for cpu in row['allowed_cpus']})}

def check_external(base: dict, external: dict, active: int, guard):
    if external['prior_historical_processes']:
        raise RuntimeError('Prior financial controllers/workers still active; shared admission blocked')
    reserved = external['external_reserved_bytes']
    committed = (active + 1) * guard.WORKER_RSS_LIMIT
    mem = base['memory']
    if mem['host_used'] + reserved + committed > guard.HOST_USED_LIMIT:
        raise RuntimeError('Host cap cannot reserve guard-pack plus financial workers')
    if (mem.get('cgroup_limit_verified') and mem['cgroup_memory_current'] + reserved + committed
            > mem['cgroup_memory_max']):
        raise RuntimeError('Cgroup cap cannot reserve guard-pack plus financial workers')
    cpus = sorted(set(base['allowed_cpus']) - set(external['external_busy_cpus']))
    if len(cpus) < 2:
        raise RuntimeError('Two unoccupied distinct CPUs required after guard-pack exclusion')
    return {**base, **external, 'allowed_cpus': cpus,
            'new_financial_committed_bytes': committed,
            'memory_accounting': 'CONSERVATIVE_CURRENT_RSS_PLUS_FULL_EXTERNAL_AND_WORKER_RESERVATIONS'}

def admission(state_root: Path, active: int, guard):
    return check_external(guard.resource_admission(state_root, active), external_observation(), active, guard)

@contextmanager
def controller_lock():
    # Participating future financial controllers share this host-wide lock.
    # Existing guard-pack is separately observed/reserved; it does not pretend
    # to participate in a lock added after that pack was launched.
    with LOCK_PATH.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Another coin financial controller holds shared resource gate') from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
