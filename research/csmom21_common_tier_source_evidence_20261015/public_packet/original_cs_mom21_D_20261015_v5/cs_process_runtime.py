"""Copied original-D finite process safety and native terminal taxonomy.

Only sibling launcher and frozen-scope filename substitutions; no launch on import.
"""
from __future__ import annotations
import argparse
import fcntl
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT=HERE.parent
CHECKER_ROOT=ROOT/'bounded_native_continuation_guard50_exit_expansion_20261015'
if str(CHECKER_ROOT) not in sys.path:sys.path.insert(0,str(CHECKER_ROOT))
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
MANIFEST_SHA256 = '9a5ef547d61272d5eb0bfb1b61fef8005a752d82f4e0007d18cbe65f06445a8a'
LIMITS = dict(maximum_live_workers=2, threads_per_worker=1, per_case_wall_seconds=600,
    per_case_CPU_seconds=600, per_case_RSS_stop_bytes=2_000_000_000,
    per_case_AS_bytes=4_000_000_000, per_case_output_bytes=250_000_000,
    aggregate_live_worker_RSS_stop_bytes=3_500_000_000)
_CONTROLLER_LEASE_FD = None
THREAD_ENV = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'POLARS_MAX_THREADS', 'VECLIB_MAXIMUM_THREADS')
TERMINAL_FILES = ('CASE_RECEIPT.json', 'ACCOUNT_FINANCIAL_AUDIT.json', 'NATIVE_RESULT.json',
    'LEGACY_PRIMARY_FINANCIAL_RECONCILIATION.json', 'PRIMARY_FINANCIAL_RECONCILIATION.json',
    'NATIVE40_RECONSTRUCTION_PROOF.json', 'ACTUAL_HELD_RISK_REPORT.json', 'MINUTE.npz',
    'GUARD_RECEIPTS.json', 'CAUSAL_MARK_QUALITY.json', 'ADMISSION_GO.json', 'ADMISSION_REVIEW.json',
    'LAUNCH_CLAIM.json', 'PROCESS_OWNERSHIP.json', 'BOOTSTRAP_READY.json')



def utc():return datetime.now(timezone.utc).isoformat()


def sha(raw):return sha256(raw).hexdigest()


def body(value):return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()


def write_bytes(path, raw):
    # Publish only fully written/fsynced immutable bytes, without replacing an
    # existing artifact. Hard-link publication is atomic on this filesystem.
    path=Path(path);temporary=path.with_name('.'+path.name+'.'+str(os.getpid())+'.'+str(time.time_ns())+'.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.link(temporary,path)
        fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if temporary.exists():temporary.unlink()


def save(path, value):write_bytes(path,body(value))


def own_bytes(path):
    total=0;seen=set()
    for item in Path(path).rglob('*'):
        try:info=item.stat()
        except (FileNotFoundError,ProcessLookupError):continue
        identity=(info.st_dev,info.st_ino)
        if stat.S_ISREG(info.st_mode) and identity not in seen:
            total+=info.st_size;seen.add(identity)
    return total


def environment():
    return dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **{key:'1' for key in THREAD_ENV})


def apply_limits(cpu):
    if type(cpu) is not int or cpu not in os.sched_getaffinity(0):
        raise ValueError('REQUESTED_WORKER_CPU_MUST_BE_ACTUALLY_ALLOWED')
    os.sched_setaffinity(0, {cpu})
    for key, value in ((resource.RLIMIT_AS, LIMITS['per_case_AS_bytes']),
            (resource.RLIMIT_CPU, LIMITS['per_case_CPU_seconds']),
            (resource.RLIMIT_RSS, LIMITS['per_case_RSS_stop_bytes'])):
        resource.setrlimit(key, (value, value))
    for key in THREAD_ENV:os.environ[key] = '1'


def process_observation(pid):
    try:
        raw = Path(f'/proc/{pid}/status').read_text()
        fields = dict(line.split(':', 1) for line in raw.splitlines() if ':' in line)
        tasks = []
        for task in Path(f'/proc/{pid}/task').iterdir():
            try:tasks.append(dict(TID=int(task.name), name=(task/'comm').read_text().strip(), CPU_affinity=sorted(os.sched_getaffinity(int(task.name)))))
            except (FileNotFoundError, ProcessLookupError):pass
        return dict(tasks=tasks, PID=pid, RSS_bytes=int(fields.get('VmRSS', '0 kB').split()[0])*1024,
            threads=int(fields['Threads']), CPU_affinity=sorted(os.sched_getaffinity(pid)),
            process_start_ticks=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19])
    except (FileNotFoundError, ProcessLookupError):return None


def host_observation():
    mem = dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
    quota = {}
    for name in ('/sys/fs/cgroup/cpu.max', '/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory.current'):
        try:quota[name] = Path(name).read_text().strip()
        except (FileNotFoundError, PermissionError):quota[name] = 'UNAVAILABLE'
    return dict(UTC=utc(), allowed_CPUs=sorted(os.sched_getaffinity(0)),
        MemAvailable_bytes=int(mem['MemAvailable'].split()[0])*1024, cgroup_observations=quota,
        quota_visibility='UNVERIFIED_HOST_OBSERVATIONS_ONLY', host_quota_guaranteed=False)


def choose_worker_count(requested, cpus, observation):
    if type(requested) is not int or requested not in (1,2) or type(cpus) is not list or len(cpus) != requested:
        raise ValueError('EXACT_ONE_OR_TWO_WORKERS_REQUIRED')
    if any(type(cpu) is not int or cpu not in observation['allowed_CPUs'] for cpu in cpus) or len(set(cpus)) != len(cpus):
        raise ValueError('DISTINCT_ACTUALLY_ALLOWED_WORKER_CPUS_REQUIRED')
    # Conservative headroom, reobserved before every new launch. Host readings
    # are observations, never evidence of an enforceable host resource quota.
    available = observation['MemAvailable_bytes']
    quota = observation.get('cgroup_observations', {})
    maximum, current = quota.get('/sys/fs/cgroup/memory.max'), quota.get('/sys/fs/cgroup/memory.current')
    if str(maximum).isdigit() and str(current).isdigit():available = min(available, int(maximum)-int(current))
    if available < 2_300_000_000:raise RuntimeError('INSUFFICIENT_OBSERVED_MEMORY_PAUSE_BEFORE_LAUNCH')
    count = requested if available >= 4_500_000_000 else 1
    cpu_max = quota.get('/sys/fs/cgroup/cpu.max', '').split()
    if len(cpu_max) == 2 and cpu_max[0].isdigit() and int(cpu_max[0]) < 2*int(cpu_max[1]):count = 1
    return min(requested, count)


def classify_terminal(audit, result, *, calendar, completed_minutes, stop_us):
    from decimal import Decimal as D, localcontext
    from saved_native_reconciliation import HALTS
    summary, economics = result['summary'], result['economics']
    full = completed_minutes == (calendar[1]-calendar[0])//60_000_000 and stop_us is None
    flat = all(D(p['quantity']) == 0 for p in audit['positions'].values())
    healthy = audit['status'] not in HALTS and D(audit['unpaid_liability']) == 0
    paid = bool(full and flat and healthy and not audit['settlement_journal'])
    conditional = bool(full and flat and healthy and audit['settlement_journal'])
    if not full:
        witness = audit.get('halt_witness')
        if (audit['status'] not in HALTS or not isinstance(witness,dict) or not witness
                or type(stop_us) is not int or witness.get('event_us') != stop_us or audit['clock_us'] != stop_us
                or not calendar[0] <= stop_us <= calendar[1]
                or completed_minutes != (stop_us-calendar[0]-1)//60_000_000):
            raise ValueError('INCOMPLETE_EXECUTION_IS_NOT_ECONOMIC_HALT_PAUSE_QUEUE')
        def wd(key):return D(str(witness.get('decimal_strings',{}).get(key,witness.get(key))))
        nav, debt = D(summary['decimal_strings']['NAV']), D(audit['unpaid_liability'])
        if wd('NAV') != nav or wd('unpaid_liability') != debt or debt < 0:
            raise ValueError('EXACT_NATIVE_HALT_NAV_DEBT_REQUIRED')
        with localcontext() as ctx:
            ctx.prec = 40
            if 'symbol' in witness:
                s = witness['symbol'];p = audit['positions'][s];q = D(p['quantity']);mark = D(audit['marks'][s][-1]['price'])
                equity = D(p['isolated_balance'])+q*(mark-D(p['entry_price']));mm=abs(q)*mark*D('.005')
                if (q == 0 or mark <= 0 or wd('quantity') != q or wd('mark_price') != mark
                        or wd('isolated_equity') != equity or wd('maintenance_margin') != mm
                        or audit['status'] == 'LIQUIDATION_REQUIRED_HALT' and not (0 < equity <= mm and nav > 0 and debt == 0)
                        or audit['status'] == 'BANKRUPT_HALT' and not (equity <= 0 or nav <= 0 or debt > 0)):
                    raise ValueError('EXACT_NATIVE_HALT_PREDICATE_REQUIRED')
            elif audit['status'] != 'BANKRUPT_HALT' or not (nav <= 0 or debt > 0):
                raise ValueError('EXACT_NATIVE_GLOBAL_BANKRUPTCY_PREDICATE_REQUIRED')
    classification = ('FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT' if paid else
        'FULL_CALENDAR_CONDITIONAL_SETTLED_FLAT' if conditional else
        'FULL_CALENDAR_RESIDUAL_OR_UNSETTLED_UNPAID' if full else 'NATIVE_HALT_PARTIAL_CALENDAR')
    expected_return = float(D(summary['decimal_strings']['NAV'])/D(10000)-1) if paid or conditional else None
    for key,value in dict(full_calendar=full, paid_flat=paid, actual_paid_market_flat=paid, conditional_settled_flat=conditional).items():
        if type(economics.get(key)) is not bool or economics[key] != value:raise ValueError('HONEST_SAVED_TERMINAL_TAXONOMY_REQUIRED')
    if (economics['comparable_full_calendar_return'] != expected_return
            or economics['paid_net_return'] != (expected_return if paid else None)
            or economics['conditional_model_net_return'] != (expected_return if conditional else None)
            or summary['completed_minutes'] != completed_minutes or summary['stop_us'] != stop_us):
        raise ValueError('HONEST_SAVED_TERMINAL_RETURN_CALENDAR_REQUIRED')
    if full and not (paid or conditional):raise ValueError('UNSETTLED_OR_RESIDUAL_CASE_PAUSES_FINITE_QUEUE')
    return classification


def confine_existing_threads(cpus):
    cpus=set(cpus)
    for task in Path('/proc/self/task').iterdir():
        try:os.sched_setaffinity(int(task.name),cpus)
        except ProcessLookupError:pass


@contextmanager
def cpu_envelope(cpus):
    allowed=set(os.sched_getaffinity(0))
    if any(type(cpu) is not int or cpu not in allowed for cpu in cpus):raise ValueError('ACTUALLY_ALLOWED_COORDINATOR_CPUS_REQUIRED')
    old={int(t.name):set(os.sched_getaffinity(int(t.name))) for t in Path('/proc/self/task').iterdir()}
    confine_existing_threads(cpus)
    try:yield
    finally:
        for task in Path('/proc/self/task').iterdir():
            try:os.sched_setaffinity(int(task.name),old.get(int(task.name),allowed))
            except ProcessLookupError:pass


def run_pool(jobs, output, *, requested_workers, cpus, validator, observation_callback=host_observation, before_launch=None):
    # Coordinator helpers and validation share the same at-most-two-CPU union.
    with cpu_envelope(cpus):
        return _run_pool(jobs,output,requested_workers=requested_workers,cpus=cpus,validator=validator,
            observation_callback=observation_callback,before_launch=before_launch)


def _run_pool(jobs, output, *, requested_workers, cpus, validator, observation_callback=host_observation, before_launch=None):
    """Generic bounded scheduler; jobs are ordered (cell_id, command_builder).

    Generic use is for generated tests. Historical controller builds jobs only
    after full-tranche external admission. Never automatically retries a case.
    """
    output = Path(output);output.mkdir(exist_ok=True)
    ids = [cell for cell,_ in jobs]
    if len(set(ids)) != len(ids) or any(not cell or Path(cell).name != cell for cell in ids):raise ValueError('UNIQUE_SAFE_CASE_IDS_REQUIRED')
    observations = [];completed = [];pending = [];active = {};started = utc()
    for cell, command in jobs:
        directory = output/cell
        if directory.exists():
            if not (directory/'TERMINAL_CHECKPOINT.json').is_file():
                launch = json.loads((directory/'PROCESS_OWNERSHIP.json').read_bytes()) if (directory/'PROCESS_OWNERSHIP.json').is_file() else {}
                live = process_observation(launch.get('PID',-1)) if type(launch.get('PID')) is int else None
                state = 'LIVE_OWNED' if live and live.get('process_start_ticks') == launch.get('process_start_ticks') else 'AMBIGUOUS_OR_INTERRUPTED'
                raise RuntimeError('EXISTING_UNFINISHED_CASE_PAUSE_NO_RETRY:'+cell+':'+state)
            receipt = validator(directory,cell)
            completed.append(dict(cell_id=cell,status=receipt['status'],checkpoint_SHA256=sha((directory/'TERMINAL_CHECKPOINT.json').read_bytes()),reused_saved_terminal=True))
        else:pending.append((cell,command))
    try:
        while pending or active:
            host = observation_callback()
            capacity = choose_worker_count(requested_workers,cpus,host)
            live_rows = [row for pid in active if (row:=process_observation(pid)) is not None]
            rss = sum(r['RSS_bytes'] for r in live_rows)
            observations.append(dict(UTC=utc(),aggregate_live_RSS_bytes=rss,workers=live_rows,observed_capacity=capacity))
            reason = None
            if rss > LIMITS['aggregate_live_worker_RSS_stop_bytes']:reason = 'AGGREGATE_LIVE_RSS_LIMIT'
            for pid,state in active.items():
                row = next((r for r in live_rows if r['PID']==pid),None)
                if row and row['RSS_bytes'] > LIMITS['per_case_RSS_stop_bytes']:reason='WORKER_RSS_LIMIT'
                ready=(state['directory']/'BOOTSTRAP_READY.json').is_file()
                if ready and row and (row['CPU_affinity'] != [state['cpu']] or any(t['CPU_affinity'] != [state['cpu']] for t in row['tasks'])):reason='WORKER_AFFINITY_LIMIT'
                if not ready and time.monotonic()-state['began']>5:reason='WORKER_BOOTSTRAP_STARTUP_LIMIT'
                if time.monotonic()-state['began'] > 600:reason='WORKER_WALL_LIMIT'
                if own_bytes(state['directory']) + state['log_path'].stat().st_size > LIMITS['per_case_output_bytes']:reason='WORKER_OUTPUT_LIMIT'
            if reason:raise RuntimeError(reason)
            for pid,state in list(active.items()):
                code = state['process'].poll()
                if code is None:continue
                state['log'].close();del active[pid]
                if code:raise RuntimeError('WORKER_FAILED_EXECUTION_NOT_ECONOMIC_HALT:'+state['cell']+':'+str(code))
                receipt = validator(state['directory'],state['cell'])
                completed.append(dict(cell_id=state['cell'],status=receipt['status'],PID=pid,CPU=state['cpu'],
                    checkpoint_SHA256=sha((state['directory']/'TERMINAL_CHECKPOINT.json').read_bytes()),reused_saved_terminal=False))
            # Pressure fallback changes only future launch concurrency. Existing
            # worker state is never restored, duplicated or migrated.
            while pending and len(active) < capacity:
                # Capacity can fall after the previous child was launched.
                # Reobserve and honor serial fallback before consuming a job
                # or reserving its permanent launch claim.
                fresh_capacity=choose_worker_count(requested_workers,cpus,observation_callback())
                if len(active)>=fresh_capacity:break
                used = {state['cpu'] for state in active.values()};cpu = next(c for c in cpus if c not in used)
                cell, builder = pending.pop(0);directory=output/cell;directory.mkdir(exist_ok=False)
                if before_launch is not None:before_launch(cell,directory,cpu)
                log_path=output/(cell+'.log');log=log_path.open('xb')
                began=time.monotonic()
                command=[sys.executable,'-B',str(HERE/'run_cs.py'),'--bootstrap',str(cpu),str(directory.resolve()),'--']+builder(directory,cpu)
                try:
                    child_env=environment()
                    if _CONTROLLER_LEASE_FD is not None:child_env['MATRIX_CONTROLLER_LEASE_FD']=str(_CONTROLLER_LEASE_FD)
                    process=subprocess.Popen(command,cwd=HERE,env=child_env,stdout=log,stderr=subprocess.STDOUT,
                        start_new_session=True,pass_fds=(() if _CONTROLLER_LEASE_FD is None else (_CONTROLLER_LEASE_FD,)))
                except BaseException:
                    log.close()
                    raise
                state=dict(cell=cell,cpu=cpu,directory=directory,process=process,began=began,log=log,log_path=log_path)
                active[process.pid]=state
                actual=process_observation(process.pid)
                save(directory/'PROCESS_OWNERSHIP.json',dict(cell_id=cell,PID=process.pid,CPU=cpu,
                    process_start_ticks=actual['process_start_ticks'] if actual else None,controller_PID=os.getpid(),UTC=utc()))
            if active:time.sleep(.1)
        report=dict(status='ALL_ADMITTED_ORDERED_CELLS_TERMINAL',started_UTC=started,ended_UTC=utc(),cases=completed,
            observations=observations,limits=LIMITS,host_quota_guaranteed=False,quota_visibility='UNVERIFIED_HOST_OBSERVATIONS_ONLY',
            coordinator_CPU_affinity=sorted(os.sched_getaffinity(0)),coordinator_thread_observation=process_observation(os.getpid()),
            compute_thread_pools_maximum=1,helper_threads_allowed_but_all_affinities_confined=True,
            no_automatic_retry=True,no_financial_snapshot_resume=True)
        return report
    except BaseException:
        for state in active.values():
            try:os.killpg(state['process'].pid,signal.SIGKILL)
            except ProcessLookupError:pass
            state['process'].wait();state['log'].close()
        raise


def claim_launch(registry_root, *, cell_id, manifest_sha256, metadata):
    """Permanent exclusive launch reservation, not a financial checkpoint.

    The historical caller has already validated external approval and inputs.
    Failed spawn and interrupted execution keep this claim permanently blocked.
    Tests pass only temporary registry roots; no claim is made on import.
    """
    if manifest_sha256 != MANIFEST_SHA256 or Path(cell_id).name != cell_id or cell_id == '2024_STATIC50_MID':
        raise ValueError('EXACT_NEW_MANIFEST_CELL_CLAIM_REQUIRED')
    manifest_raw=(HERE/'FROZEN_FIFTEEN_CELL_MANIFEST.json').read_bytes()
    if sha(manifest_raw)!=MANIFEST_SHA256 or cell_id not in {c['cell_id'] for c in json.loads(manifest_raw)['cells']}:
        raise ValueError('EXACT_NEW_MANIFEST_CELL_CLAIM_REQUIRED')
    registry=Path(registry_root)/manifest_sha256;registry.mkdir(parents=True,exist_ok=True)
    path=registry/(cell_id+'.json')
    value=dict(schema='CANONICAL_IMMUTABLE_MANIFEST_CELL_LAUNCH_CLAIM_V1',manifest_SHA256=manifest_sha256,
        cell_id=cell_id,claim_UTC=utc(),controller_PID=os.getpid(),status='RESERVED_BEFORE_PROCESS_SPAWN',
        automatic_clear_or_retry=False,financial_snapshot_resume=False,**metadata)
    try:save(path,value)
    except FileExistsError:raise RuntimeError('PERMANENT_CANONICAL_CELL_CLAIM_EXISTS_NO_DUPLICATE_LAUNCH:'+cell_id)
    fd=os.open(registry,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return path


@contextmanager
def controller_lease(registry_root):
    """One cross-tranche controller; inherited open-file description holds it.

    Close this process's descriptor without explicit LOCK_UN: surviving worker
    duplicates must retain exclusion even if the coordinator exits or dies.
    """
    global _CONTROLLER_LEASE_FD
    directory=Path(registry_root)/MANIFEST_SHA256;directory.mkdir(parents=True,exist_ok=True)
    descriptor=os.open(directory/'CONTROLLER_LEASE.lock',os.O_CREAT|os.O_RDWR,0o600)
    try:
        try:fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('CANONICAL_GLOBAL_CONTROLLER_LEASE_HELD_REFUSE_OVERLAP')
        previous=_CONTROLLER_LEASE_FD;_CONTROLLER_LEASE_FD=descriptor
        try:yield descriptor
        finally:_CONTROLLER_LEASE_FD=previous
    finally:os.close(descriptor)
