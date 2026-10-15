"""Finite ordered, fresh-genesis-only D matrix pool with saved-only validation.

Importing this module launches nothing. Historical CLI requires exact external
GO/review/preparation. Generated profiling is a separate explicitly named route.
Snapshots are evidence only; existing unfinished work always pauses the queue.
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
MANIFEST_SHA256 = '03b8016fd98fc2bc5c60db5800672a05a558351b4cfef760dfa34014aa5be85c'
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


def validate_scope(args):
    import partial_entry as entry
    if Path(entry.__file__).resolve()!=HERE/'partial_entry.py':raise ValueError('EXACT_LOCAL_PARTIAL2021_ENTRY_REQUIRED')
    prep = (Path(args.preparation)/'PREPARATION.json').read_bytes()
    go, review = Path(args.go).read_bytes(), Path(args.review).read_bytes()
    parsed = json.loads(go)
    if parsed.get('permitted_cells') != list(entry.tranche_cells(parsed.get('tranche',entry.FIRST_TRANCHE))):
        raise ValueError('ONLY_EXACT_ORDERED_NINE_PARTIAL2021_CELLS_ALLOWED')
    for cell in parsed['permitted_cells']:
        admitted = entry.validate_root_go(prep, go, args.go_sha, cell_id=cell)
        entry._validate_independent_review(prep, admitted, review, args.review_sha, go)
    choose_worker_count(parsed['requested_worker_count'], parsed['worker_CPUs'], host_observation())
    return prep, go, review


def held_risk_report(values, columns, decisions, covariance, targets, tier, receipts):
    import numpy as np
    import partial_d as integration
    if Path(integration.__file__).resolve()!=HERE/'partial_d.py':raise ValueError('EXACT_LOCAL_PARTIAL2021_D_REQUIRED')
    import annual_reporting
    arr = np.asarray(values);names = list(columns)
    if not len(arr):
        return dict(status='NOT_EVALUABLE_NO_COMPLETED_NATIVE_MINUTES', observation_count=0,
            nominal_tier_equality_is_not_exact_realized_risk_matching=True)
    nav = arr[:, names.index('nav')]
    positive = np.flatnonzero(nav <= 0)
    count = int(positive[0]) if len(positive) else len(arr)
    if count == 0:
        return dict(status='NOT_EVALUABLE_NONPOSITIVE_NAV', observation_count=0,
            omitted_nonpositive_or_later_minutes=len(arr), nominal_tier_equality_is_not_exact_realized_risk_matching=True)
    report = annual_reporting.risk_diagnostics(arr[:count], names, decisions, covariance, targets, tier, receipts)
    weights = np.column_stack([arr[:count,names.index(s+'_signed_weight')] for s in integration.S])
    net = weights.sum(axis=1)
    report.update(status='ACTUAL_HELD_MINUTE_OBSERVATIONS' if count == len(arr) else 'POSITIVE_NAV_PREFIX_ONLY',
        omitted_nonpositive_or_later_minutes=len(arr)-count, actual_net_signed_weight_min=float(net.min()),
        actual_net_signed_weight_max=float(net.max()), actual_net_signed_weight_mean=float(net.mean()),
        actual_absolute_weight_max_by_symbol=dict(zip(integration.S,np.abs(weights).max(axis=0).tolist())),
        actual_signed_weight_min_by_symbol=dict(zip(integration.S,weights.min(axis=0).tolist())),
        actual_signed_weight_max_by_symbol=dict(zip(integration.S,weights.max(axis=0).tolist())),
        adaptive_DEV_only=True, nominal_tier_equality_is_not_exact_realized_risk_matching=True,
        reporting_code_SHA256=sha(Path(annual_reporting.__file__).read_bytes()),
        funding_publication_certified=False, native_exchange_execution_certified=False)
    return report


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


def case(args):
    apply_limits(args.cpu)
    import numpy as np
    import partial_d as integration
    if Path(integration.__file__).resolve()!=HERE/'partial_d.py':raise ValueError('EXACT_LOCAL_PARTIAL2021_D_REQUIRED')
    import partial_entry as entry
    if Path(entry.__file__).resolve()!=HERE/'partial_entry.py':raise ValueError('EXACT_LOCAL_PARTIAL2021_ENTRY_REQUIRED')
    from saved_native_reconciliation import reconcile_saved_native, checker_sha256
    import saved_native_reconciliation as checker_module
    if Path(checker_module.__file__).resolve()!=CHECKER_ROOT/'saved_native_reconciliation.py':raise ValueError('EXACT_FROZEN_SAVED_NATIVE_CHECKER_REQUIRED')
    prep_raw, go, review = validate_scope_worker(args)
    claim_raw = validate_worker_claim(args,preparation_raw=prep_raw,go_raw=go,review_raw=review)
    write_bytes(Path(args.case_output)/'LAUNCH_CLAIM.json',claim_raw)
    prep = json.loads(prep_raw);cell = entry.cell_descriptor(args.cell_id)
    directory = Path(args.case_output)
    began = time.monotonic();started = utc()
    try:
        sim, guard = entry.make_case({2021:args.source_2021}, args.preparation,
            go, args.go_sha, cell_id=args.cell_id, review_raw=review, expected_review_sha256=args.review_sha)
        construction = time.monotonic()-began
        while sim.cursor < sim.end and sim.stop is None:
            sim.advance_day()
            print(json.dumps(dict(event='NATIVE_DAY_COMPLETE', cell_id=args.cell_id,
                completed_minutes=sim.rows_written, stop_us=sim.stop, UTC=utc())), flush=True)
        result = integration.case_result(sim, guard)
        minute = result.pop('minute');values = minute.to_numpy();columns = minute.columns
        result['targets'] = result['targets'].to_dicts()
        audit = integration.V2.OWNED.export_tree(sim.account.snapshot())
        result = integration.V2.OWNED.export_tree(result)
        legacy = result['primary_financial_reconciliation']
        proof = reconcile_saved_native(audit,result,expected_continuation_version=integration.VERSION)
        result['authoritative_primary_financial_reconciliation'] = proof
        classification = classify_terminal(audit,result,calendar=cell['calendar'],completed_minutes=sim.rows_written,stop_us=sim.stop)
        with np.load(BytesIO((Path(args.preparation)/f"{cell['year']}/TARGETS.npz").read_bytes()),allow_pickle=False) as z:
            risk = held_risk_report(values,columns,z['decision_us'],z['annual_covariance'],z[cell['config']],cell['tier'],guard.receipts)
        np.savez_compressed(directory/'MINUTE.npz',values=values,columns=np.asarray(columns))
        with (directory/'MINUTE.npz').open('rb') as stream:os.fsync(stream.fileno())
        quality = guard.causal_mark_quality_guard
        evidence = {'ACCOUNT_FINANCIAL_AUDIT.json':audit,'NATIVE_RESULT.json':result,
            'LEGACY_PRIMARY_FINANCIAL_RECONCILIATION.json':legacy,'PRIMARY_FINANCIAL_RECONCILIATION.json':proof,
            'NATIVE40_RECONSTRUCTION_PROOF.json':proof,'ACTUAL_HELD_RISK_REPORT.json':risk,
            'GUARD_RECEIPTS.json':integration.V2.OWNED.export_tree(guard.receipts),
            'CAUSAL_MARK_QUALITY.json':dict(identity=quality.identity,policy_SHA256=quality.policy_sha256,
                receipts=integration.V2.OWNED.export_tree(quality.receipts),original_interpolated_marks_execution_admitted=False)}
        # The proof binds the input result without its derived self-reference.
        result.pop('authoritative_primary_financial_reconciliation')
        for name,value in evidence.items():save(directory/name,value)
        write_bytes(directory/'ADMISSION_GO.json',go);write_bytes(directory/'ADMISSION_REVIEW.json',review)
        if entry.code_identity() != prep['code_identity']:raise ValueError('CODE_CHANGED_DURING_CASE')
        receipt = dict(schema='FINITE_ORIGINAL_D_PARTIAL2021_CASE_V1',cell_id=args.cell_id,year=cell['year'],
            strategy=cell['strategy'],tier=cell['tier'],config=cell['config'],calendar=cell['calendar'],
            cost=entry.COST,policy_variant=integration.POLICY_VARIANT,status=classification,adaptive_DEV_only=True,
            root_GO_SHA256=args.go_sha,independent_review_SHA256=args.review_sha,preparation_SHA256=sha(prep_raw),
            manifest_SHA256=entry.MANIFEST_SHA256,source_identity=prep['years'][str(cell['year'])]['source_identity'],
            code_identity=prep['code_identity'],policy_identity=prep['policy_identity'],checker_SHA256=checker_sha256(),
            reconstruction_proof_SHA256=sha((directory/'NATIVE40_RECONSTRUCTION_PROOF.json').read_bytes()),
            completed_minutes=sim.rows_written,required_minutes=cell['required_minutes'],account_stop_us=sim.stop,
            started_UTC=started,ended_UTC=utc(),construction_seconds=construction,total_wall_seconds=time.monotonic()-began,
            max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
            PID=os.getpid(),requested_CPU=args.cpu,actual_CPU_affinity=sorted(os.sched_getaffinity(0)),
            thread_environment={key:os.environ[key] for key in THREAD_ENV},limits=LIMITS,
            no_halt_reset=True,snapshot_restart_certified=False,automatic_retry=False,
            native_exchange_or_funding_publication_certified=False,locked_source_reads=0,publication_actions=0)
        save(directory/'CASE_RECEIPT.json',receipt)
        if own_bytes(directory) > LIMITS['per_case_output_bytes']:raise RuntimeError('OUTPUT_LIMIT')
        save(directory/'TERMINAL_CHECKPOINT.json',dict(schema='IMMUTABLE_MATRIX_TERMINAL_CHECKPOINT_V1',
            cell_id=args.cell_id,files={name:sha((directory/name).read_bytes()) for name in TERMINAL_FILES},
            checker_SHA256=checker_sha256(),reconstruction_proof_SHA256=receipt['reconstruction_proof_SHA256'],
            all_evidence_fsynced=True,restart_financial_snapshot_permission=False))
    except BaseException as error:
        if 'sim' in locals():
            try:save(directory/'FAILED_ACCOUNT_FINANCIAL_AUDIT.json',integration.V2.OWNED.export_tree(sim.account.snapshot()))
            except BaseException:pass
        save(directory/'FAILURE.json',dict(kind='EXECUTION_RESOURCE_DATA_OR_VALIDATION_INTERRUPTION',
            error=repr(error),traceback=traceback.format_exc(),UTC=utc(),automatic_retry=False))
        raise


def validate_scope_worker(args):
    # Worker is deliberately restricted to its one CPU, so only the coordinator
    # checks the complete GO CPU set against coordinator affinity.
    import partial_entry as entry
    if Path(entry.__file__).resolve()!=HERE/'partial_entry.py':raise ValueError('EXACT_LOCAL_PARTIAL2021_ENTRY_REQUIRED')
    prep = (Path(args.preparation)/'PREPARATION.json').read_bytes()
    go, review = Path(args.go).read_bytes(), Path(args.review).read_bytes()
    parsed = json.loads(go)
    admitted = entry.validate_root_go(prep,go,args.go_sha,cell_id=args.cell_id)
    entry._validate_independent_review(prep,admitted,review,args.review_sha,go)
    if args.cpu not in parsed['worker_CPUs'] or sorted(os.sched_getaffinity(0)) != [args.cpu]:
        raise ValueError('EXACT_GO_WORKER_SINGLE_CPU_REQUIRED')
    return prep,go,review


def validate_worker_claim(args, *, preparation_raw, go_raw, review_raw, registry_root=None, handshake_seconds=2):
    """Read-only bounded parent/worker handshake before account construction."""
    registry_root=Path(registry_root) if registry_root is not None else HERE/'EXECUTION_CLAIMS'
    claim_path=registry_root/MANIFEST_SHA256/(args.cell_id+'.json')
    if not claim_path.is_file() or claim_path.is_symlink():raise ValueError('EXACT_CANONICAL_PRELAUNCH_CLAIM_REQUIRED')
    raw=claim_path.read_bytes();claim=json.loads(raw);prep=json.loads(preparation_raw)
    manifest=json.loads((HERE/'FROZEN_NINE_CELL_MANIFEST.json').read_bytes())
    cells=[c for c in manifest['cells'] if c['cell_id']==args.cell_id]
    if len(cells)!=1:raise ValueError('EXACT_NEW_MANIFEST_CELL_CLAIM_REQUIRED')
    cell=cells[0]
    expected=dict(schema='CANONICAL_IMMUTABLE_MANIFEST_CELL_LAUNCH_CLAIM_V1',manifest_SHA256=MANIFEST_SHA256,
        cell_id=args.cell_id,year=cell['year'],config=cell['config'],source_identity=prep['years'][str(cell['year'])]['source_identity'],
        selected_target_raw_SHA256=cell['selected_target_raw_SHA256'],preparation_SHA256=sha(preparation_raw),
        code_identity=prep['code_identity'],root_GO_SHA256=sha(go_raw),independent_review_SHA256=sha(review_raw),
        requested_CPU=args.cpu,case_output=str(Path(args.case_output).resolve()),
        status='RESERVED_BEFORE_PROCESS_SPAWN',automatic_clear_or_retry=False,financial_snapshot_resume=False)
    if any(body(claim.get(k))!=body(v) for k,v in expected.items()):raise ValueError('EXACT_WORKER_LAUNCH_CLAIM_SCOPE_REQUIRED')
    if registry_root.resolve()==(HERE/'EXECUTION_CLAIMS').resolve():
        bootstrap=json.loads((Path(args.case_output)/'BOOTSTRAP_READY.json').read_bytes())
        expected_limits={name:list(resource.getrlimit(which)) for name,which in (('AS',resource.RLIMIT_AS),('CPU',resource.RLIMIT_CPU),('RSS',resource.RLIMIT_RSS))}
        if (bootstrap.get('PID')!=os.getpid() or bootstrap.get('requested_CPU')!=args.cpu
                or bootstrap.get('actual_affinity')!=[args.cpu] or bootstrap.get('limits')!=expected_limits
                or bootstrap.get('thread_environment')!={key:'1' for key in THREAD_ENV}):
            raise ValueError('EXACT_PRE_NUMERICAL_RESOURCE_BOOTSTRAP_REQUIRED')
        fd_text=os.environ.get('MATRIX_CONTROLLER_LEASE_FD','')
        if not fd_text.isdigit():raise ValueError('INHERITED_CANONICAL_CONTROLLER_LEASE_FD_REQUIRED')
        try:
            descriptor=int(fd_text);held=os.fstat(descriptor);canonical=(registry_root/MANIFEST_SHA256/'CONTROLLER_LEASE.lock').stat()
        except (OSError,ValueError):raise ValueError('INHERITED_CANONICAL_CONTROLLER_LEASE_FD_REQUIRED')
        if (held.st_dev,held.st_ino)!=(canonical.st_dev,canonical.st_ino):raise ValueError('EXACT_CANONICAL_CONTROLLER_LEASE_INODE_REQUIRED')
        if claim.get('global_controller_lease_key')!=MANIFEST_SHA256+'/CONTROLLER_LEASE.lock':raise ValueError('EXACT_CANONICAL_CONTROLLER_LEASE_CLAIM_REQUIRED')
    ownership_path=Path(args.case_output)/'PROCESS_OWNERSHIP.json'
    deadline=time.monotonic()+handshake_seconds
    while not ownership_path.is_file() and time.monotonic()<deadline:time.sleep(.01)
    if not ownership_path.is_file() or ownership_path.is_symlink():raise ValueError('EXACT_WORKER_PROCESS_OWNERSHIP_REQUIRED')
    owner=json.loads(ownership_path.read_bytes());actual=process_observation(os.getpid())
    if (owner.get('cell_id')!=args.cell_id or owner.get('PID')!=os.getpid() or owner.get('CPU')!=args.cpu
            or owner.get('controller_PID')!=os.getppid() or claim.get('controller_PID')!=os.getppid()
            or actual is None or owner.get('process_start_ticks')!=actual['process_start_ticks']
            or actual['CPU_affinity']!=[args.cpu] or any(t['CPU_affinity']!=[args.cpu] for t in actual['tasks'])):
        raise ValueError('EXACT_LIVE_WORKER_PID_START_CPU_AND_PARENT_OWNERSHIP_REQUIRED')
    return raw


def validate_saved_risk_report(directory, *, preparation_directory, preparation_raw, cell, receipt, result):
    """Saved-only exact minute calendar/projection and held-risk recomputation."""
    import numpy as np
    import partial_entry as entry
    if Path(entry.__file__).resolve()!=HERE/'partial_entry.py':raise ValueError('EXACT_LOCAL_PARTIAL2021_ENTRY_REQUIRED')
    directory=Path(directory)
    with np.load(BytesIO((directory/'MINUTE.npz').read_bytes()),allow_pickle=False) as z:
        if set(z.files)!={'values','columns'}:raise ValueError('EXACT_SAVED_MINUTE_ARCHIVE_REQUIRED')
        values=z['values'];columns=z['columns'].tolist()
    if (values.ndim!=2 or len(values)!=receipt['completed_minutes'] or len(columns)!=values.shape[1]
            or len(set(columns))!=len(columns) or not np.isfinite(values).all()):
        raise ValueError('FINITE_EXACT_COMPLETED_MINUTE_MATRIX_REQUIRED')
    required=['close_us','nav','free_cash','isolated_balance','gross_weight']+[s+'_signed_weight' for s in entry.s.S]
    if any(name not in columns for name in required):raise ValueError('EXACT_MINUTE_EXPOSURE_SYMBOL_COLUMNS_REQUIRED')
    clocks=values[:,columns.index('close_us')]
    expected=cell['calendar'][0]+np.arange(1,len(values)+1,dtype=np.int64)*60_000_000
    if not np.array_equal(clocks,expected):raise ValueError('EXACT_CONTIGUOUS_SAVED_MINUTE_CALENDAR_REQUIRED')
    if len(values) and receipt.get('account_stop_us') is None:
        summary=result['summary']
        for column,key in (('nav','NAV'),('free_cash','free_cash'),('isolated_balance','isolated_balance'),('gross_weight','gross_weight')):
            if float(values[-1,columns.index(column)])!=summary[key]:raise ValueError('EXACT_SAVED_MINUTE_FINAL_PROJECTION_REQUIRED:'+column)
    prepdir=Path(preparation_directory)
    if (prepdir/'PREPARATION.json').read_bytes()!=preparation_raw:raise ValueError('EXACT_EXTERNAL_PREPARATION_BYTES_FOR_RISK_REPORT_REQUIRED')
    prep=json.loads(preparation_raw)
    name=f"{cell['year']}/TARGETS.npz";raw=(prepdir/name).read_bytes()
    if sha(raw)!=prep['artifacts'][name]['SHA256']:raise ValueError('EXACT_SAVED_RISK_TARGET_COVARIANCE_BYTES_REQUIRED')
    receipts=json.loads((directory/'GUARD_RECEIPTS.json').read_bytes())
    with np.load(BytesIO(raw),allow_pickle=False) as z:
        report=held_risk_report(values,columns,z['decision_us'],z['annual_covariance'],z[cell['config']],cell['tier'],receipts)
    if body(report)!=(directory/'ACTUAL_HELD_RISK_REPORT.json').read_bytes():raise ValueError('EXACT_ACTUAL_HELD_RISK_REPORT_RECOMPUTATION_REQUIRED')
    return report


def validate_saved_terminal(directory, *, preparation_raw, preparation_directory, cell_id, expected_go_sha256, expected_review_sha256):
    import partial_entry as entry
    if Path(entry.__file__).resolve()!=HERE/'partial_entry.py':raise ValueError('EXACT_LOCAL_PARTIAL2021_ENTRY_REQUIRED')
    import partial_d as integration
    if Path(integration.__file__).resolve()!=HERE/'partial_d.py':raise ValueError('EXACT_LOCAL_PARTIAL2021_D_REQUIRED')
    from saved_native_reconciliation import reconcile_saved_native, checker_sha256
    import saved_native_reconciliation as checker_module
    if Path(checker_module.__file__).resolve()!=CHECKER_ROOT/'saved_native_reconciliation.py':raise ValueError('EXACT_FROZEN_SAVED_NATIVE_CHECKER_REQUIRED')
    directory = Path(directory);prep = json.loads(preparation_raw)
    cp = json.loads((directory/'TERMINAL_CHECKPOINT.json').read_bytes())
    if (cp.get('cell_id') != cell_id or cp.get('all_evidence_fsynced') is not True
            or cp.get('restart_financial_snapshot_permission') is not False or set(cp.get('files',{})) != set(TERMINAL_FILES)
            or any(sha((directory/name).read_bytes()) != cp['files'][name] for name in TERMINAL_FILES)
            or cp.get('checker_SHA256') != checker_sha256()):
        raise ValueError('EXACT_ALL_TERMINAL_BYTES_CHECKER_REQUIRED')
    go, review = (directory/'ADMISSION_GO.json').read_bytes(),(directory/'ADMISSION_REVIEW.json').read_bytes()
    admitted = entry.validate_root_go(preparation_raw,go,expected_go_sha256,cell_id=cell_id)
    entry._validate_independent_review(preparation_raw,admitted,review,expected_review_sha256,go)
    receipt = json.loads((directory/'CASE_RECEIPT.json').read_bytes());cell = entry.cell_descriptor(cell_id)
    canonical_claim=HERE/'EXECUTION_CLAIMS'/MANIFEST_SHA256/(cell_id+'.json')
    if not canonical_claim.is_file() or canonical_claim.read_bytes()!=(directory/'LAUNCH_CLAIM.json').read_bytes():
        raise ValueError('SAVED_TERMINAL_CANONICAL_LAUNCH_CLAIM_REQUIRED')
    expected = dict(schema='FINITE_ORIGINAL_D_PARTIAL2021_CASE_V1',cell_id=cell_id,year=cell['year'],strategy=cell['strategy'],
        tier=cell['tier'],config=cell['config'],calendar=cell['calendar'],cost=entry.COST,policy_variant=integration.POLICY_VARIANT,
        adaptive_DEV_only=True,root_GO_SHA256=sha(go),independent_review_SHA256=sha(review),preparation_SHA256=sha(preparation_raw),
        manifest_SHA256=entry.MANIFEST_SHA256,source_identity=prep['years'][str(cell['year'])]['source_identity'],
        code_identity=prep['code_identity'],policy_identity=prep['policy_identity'],checker_SHA256=checker_sha256(),
        required_minutes=cell['required_minutes'],limits=LIMITS,no_halt_reset=True,snapshot_restart_certified=False,
        automatic_retry=False,native_exchange_or_funding_publication_certified=False,locked_source_reads=0,publication_actions=0)
    if any(body(receipt.get(k)) != body(v) for k,v in expected.items()):raise ValueError('EXACT_SAVED_CASE_SCOPE_REQUIRED')
    audit = json.loads((directory/'ACCOUNT_FINANCIAL_AUDIT.json').read_bytes())
    result = json.loads((directory/'NATIVE_RESULT.json').read_bytes())
    proof = reconcile_saved_native(audit,result,expected_continuation_version=integration.VERSION)
    if (body(proof) != (directory/'NATIVE40_RECONSTRUCTION_PROOF.json').read_bytes()
            or body(proof) != (directory/'PRIMARY_FINANCIAL_RECONCILIATION.json').read_bytes()
            or sha(body(proof)) != receipt['reconstruction_proof_SHA256']
            or cp['reconstruction_proof_SHA256'] != receipt['reconstruction_proof_SHA256']
            or result['primary_financial_reconciliation'] != json.loads((directory/'LEGACY_PRIMARY_FINANCIAL_RECONCILIATION.json').read_bytes())):
        raise ValueError('EXACT_RECONSTRUCTION_PROOF_BINDING_REQUIRED')
    if receipt['status'] != classify_terminal(audit,result,calendar=cell['calendar'],
            completed_minutes=receipt['completed_minutes'],stop_us=receipt['account_stop_us']):raise ValueError('EXACT_TERMINAL_STATUS_REQUIRED')
    validate_saved_risk_report(directory,preparation_directory=preparation_directory,preparation_raw=preparation_raw,cell=cell,receipt=receipt,result=result)
    binding = audit['historical_execution_scope']
    for key in ('cell_id','year','strategy','config','preparation_SHA256','source_identity','root_GO_SHA256',
                'independent_review_SHA256','policy_identity','policy_variant'):
        if binding.get(key) != receipt[key]:raise ValueError('EXACT_AUDIT_EXECUTION_SCOPE_REQUIRED:'+key)
    if (receipt['actual_CPU_affinity'] != [receipt['requested_CPU']] or receipt['requested_CPU'] not in json.loads(go)['worker_CPUs']
            or receipt['thread_environment'] != {key:'1' for key in THREAD_ENV}
            or receipt['total_wall_seconds'] > 600 or receipt['CPU_seconds'] > 600
            or receipt['max_RSS_bytes'] > LIMITS['per_case_RSS_stop_bytes'] or own_bytes(directory) > LIMITS['per_case_output_bytes']):
        raise ValueError('SAVED_CASE_RESOURCE_LIMIT_MISMATCH')
    return receipt


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
                command=[sys.executable,'-B',str(HERE/'run_partial.py'),'--bootstrap',str(cpu),str(directory.resolve()),'--']+builder(directory,cpu)
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
    manifest_raw=(HERE/'FROZEN_NINE_CELL_MANIFEST.json').read_bytes()
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


def controller(args):
    if Path(args.output).exists():raise ValueError('EXISTING_CONTROLLER_OUTPUT_REFUSED_SCHEDULING_RESUME_NOT_SUPPORTED')
    # Hash and stdlib resource preflight precede entry/numerical imports.
    raw_go=Path(args.go).read_bytes()
    if sha(raw_go)!=args.go_sha:raise ValueError('EXACT_EXTERNAL_GO_BYTES_REQUIRED')
    initial_go=json.loads(raw_go)
    choose_worker_count(initial_go.get('requested_worker_count'),initial_go.get('worker_CPUs'),host_observation())
    for key in THREAD_ENV:os.environ[key]='1'
    confine_existing_threads(initial_go['worker_CPUs'])
    prep,go,review=validate_scope(args);admission=json.loads(go)
    import partial_entry as entry
    if Path(entry.__file__).resolve()!=HERE/'partial_entry.py':raise ValueError('EXACT_LOCAL_PARTIAL2021_ENTRY_REQUIRED')
    parsed_prep=json.loads(prep)
    # Verify every selected source/target projection before any claim or spawn.
    for cell in admission['permitted_cells']:
        checked=entry.validate_case_inputs({2021:args.source_2021},args.preparation,go,args.go_sha,cell_id=cell)
        del checked
    output=Path(args.output)
    if output.exists():raise ValueError('EXISTING_CONTROLLER_OUTPUT_REFUSED_SCHEDULING_RESUME_NOT_SUPPORTED')
    output.mkdir(exist_ok=False)
    write_bytes(output/('ADMISSION_'+args.go_sha+'.json'),go)
    jobs=[]
    for cell in admission['permitted_cells']:
        def builder(directory,cpu,cell=cell):
            return [sys.executable,'-B',str(HERE/'run_partial.py'),'--case','--cell-id',cell,'--cpu',str(cpu),
                '--source-2021',str(Path(args.source_2021).resolve()),
                '--preparation',str(Path(args.preparation).resolve()),'--go',str(Path(args.go).resolve()),'--go-sha',args.go_sha,
                '--review',str(Path(args.review).resolve()),'--review-sha',args.review_sha,'--case-output',str(directory.resolve())]
        jobs.append((cell,builder))
    def before_launch(cell_id,directory,cpu):
        cell=entry.cell_descriptor(cell_id)
        # Recheck code and observed coordinator pressure immediately before
        # reserving. The child repeats full fresh source admission.
        if entry.code_identity()!=parsed_prep['code_identity']:raise ValueError('CODE_CHANGED_BEFORE_LAUNCH_CLAIM')
        choose_worker_count(admission['requested_worker_count'],admission['worker_CPUs'],host_observation())
        claim_launch(HERE/'EXECUTION_CLAIMS',cell_id=cell_id,manifest_sha256=MANIFEST_SHA256,metadata=dict(
            year=cell['year'],config=cell['config'],source_identity=parsed_prep['years'][str(cell['year'])]['source_identity'],
            selected_target_raw_SHA256=cell['selected_target_raw_SHA256'],preparation_SHA256=sha(prep),
            code_identity=parsed_prep['code_identity'],root_GO_SHA256=args.go_sha,independent_review_SHA256=args.review_sha,
            case_output=str(directory.resolve()),controller_output=str(output.resolve()),requested_CPU=cpu,
            global_controller_lease_key=MANIFEST_SHA256+'/CONTROLLER_LEASE.lock'))
    try:
        with controller_lease(HERE/'EXECUTION_CLAIMS'):
            report=run_pool(jobs,output,requested_workers=admission['requested_worker_count'],cpus=admission['worker_CPUs'],
            validator=lambda directory,cell:validate_saved_terminal(directory,preparation_raw=prep,preparation_directory=args.preparation,cell_id=cell,
                expected_go_sha256=args.go_sha,expected_review_sha256=args.review_sha),before_launch=before_launch)
        report.update(root_GO_SHA256=args.go_sha,tranche=admission['tranche'],manifest_SHA256=MANIFEST_SHA256,adaptive_DEV_only=True,publication_actions=0)
        save(output/('CONTROLLER_RECEIPT_'+args.go_sha+'.json'),report)
    except BaseException as error:
        save(output/('CONTROLLER_PAUSE_'+args.go_sha+'.json'),dict(status='EXECUTION_RESOURCE_DATA_OR_VALIDATION_PAUSE',
            error=repr(error),UTC=utc(),automatic_retry=False,economic_halt_relabelled=False));raise


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--bootstrap':
        if len(sys.argv)<6 or sys.argv[4]!='--':raise SystemExit('EXACT_STDLIB_BOOTSTRAP_ARGUMENTS_REQUIRED')
        cpu=int(sys.argv[2]);directory=Path(sys.argv[3]);command=sys.argv[5:]
        apply_limits(cpu)
        save(directory/'BOOTSTRAP_READY.json',dict(schema='STDLIB_PRE_NUMERICAL_IMPORT_RESOURCE_BOOTSTRAP_V1',
            PID=os.getpid(),requested_CPU=cpu,actual_affinity=sorted(os.sched_getaffinity(0)),
            thread_environment={key:os.environ[key] for key in THREAD_ENV},
            limits={name:list(resource.getrlimit(which)) for name,which in (('AS',resource.RLIMIT_AS),('CPU',resource.RLIMIT_CPU),('RSS',resource.RLIMIT_RSS))}))
        os.execvpe(command[0],command,environment())
    parser=argparse.ArgumentParser();parser.add_argument('--case',action='store_true')
    for name in ('source-2021','preparation','go','go-sha','review','review-sha'):parser.add_argument('--'+name,required=True)
    for name in ('cell-id','case-output','output'):parser.add_argument('--'+name)
    parser.add_argument('--cpu',type=int)
    args=parser.parse_args();case(args) if args.case else controller(args)
