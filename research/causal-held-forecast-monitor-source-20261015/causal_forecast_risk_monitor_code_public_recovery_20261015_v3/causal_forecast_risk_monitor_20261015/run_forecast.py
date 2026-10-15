"""Finite four-cell driver over the unchanged bounded native worker pool.

There is no launch on import. Exact new preparation, external root GO and review
are required before source admission, canonical claims, lease or process launch.
"""
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
import traceback
from types import FunctionType

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OLD_ROOT=ROOT/'bounded_native_continuation_guard50_exit_expansion_20261015'
spec=importlib.util.spec_from_file_location('_forecast_exact_bounded_pool',OLD_ROOT/'run_expansion.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
MANIFEST_SHA256='1069e5a46b5197ce1195aaa7db1569cac3573800e526fff55039c7206f35081b'
LIMITS,THREAD_ENV,TERMINAL_FILES=R.LIMITS,R.THREAD_ENV,R.TERMINAL_FILES
sha,body,save,write_bytes=R.sha,R.body,R.save,R.write_bytes
apply_limits,own_bytes,utc=R.apply_limits,R.own_bytes,R.utc
choose_worker_count,host_observation=R.choose_worker_count,R.host_observation
process_observation=R.process_observation
# One explicit globals dictionary retains the exact inherited lease FD across
# the exact contextmanager and exact pool functions. No R module is patched.
_POOL_GLOBALS=dict(R.__dict__,MANIFEST_SHA256=MANIFEST_SHA256)


def _pool_bind(function):
    result=FunctionType(function.__code__,_POOL_GLOBALS,function.__name__,function.__defaults__,function.__closure__)
    result.__kwdefaults__=function.__kwdefaults__
    return result


controller_lease=contextmanager(_pool_bind(R.controller_lease.__wrapped__))
_POOL_GLOBALS['_run_pool']=_pool_bind(R._run_pool)
run_pool=_pool_bind(R.run_pool)


def _entry():
    import forecast_entry
    if Path(forecast_entry.__file__).resolve()!=HERE/'forecast_entry.py':
        raise ValueError('EXACT_LOCAL_FORECAST_ENTRY_REQUIRED')
    return forecast_entry


def _checker():
    if str(OLD_ROOT) not in sys.path:sys.path.insert(0,str(OLD_ROOT))
    import saved_native_reconciliation
    if Path(saved_native_reconciliation.__file__).resolve()!=OLD_ROOT/'saved_native_reconciliation.py':
        raise ValueError('EXACT_PINNED_NATIVE40_CHECKER_REQUIRED')
    return saved_native_reconciliation


def validate_scope(args,*,worker=False):
    e=_entry()
    prep=(Path(args.preparation)/'PREPARATION.json').read_bytes()
    go,review=Path(args.go).read_bytes(),Path(args.review).read_bytes()
    parsed=json.loads(go)
    if parsed.get('permitted_cells')!=list(e.tranche_cells()):
        raise ValueError('ONLY_EXACT_ORDERED_FOUR_FORECAST_CELLS_ALLOWED')
    cells=(args.cell_id,) if worker else e.tranche_cells()
    for cell in cells:
        admitted=e.validate_root_go(prep,go,args.go_sha,cell_id=cell)
        e._validate_independent_review(prep,admitted,review,args.review_sha,go)
    if json.loads(prep)['code_identity']!=e.code_identity():
        raise ValueError('FORECAST_CODE_CHANGED_SINCE_PREPARATION')
    if worker:
        if args.cpu not in parsed['worker_CPUs'] or sorted(os.sched_getaffinity(0))!=[args.cpu]:
            raise ValueError('EXACT_NEW_GO_SINGLE_WORKER_CPU_REQUIRED')
    else:
        choose_worker_count(parsed['requested_worker_count'],parsed['worker_CPUs'],host_observation())
    return prep,go,review


def claim_launch(registry_root,*,cell_id,manifest_sha256,metadata):
    e=_entry();e.cell_descriptor(cell_id)
    if manifest_sha256!=MANIFEST_SHA256 or e.MANIFEST_SHA256!=MANIFEST_SHA256:
        raise ValueError('EXACT_NEW_FOUR_CELL_MANIFEST_CLAIM_REQUIRED')
    directory=Path(registry_root)/MANIFEST_SHA256;directory.mkdir(parents=True,exist_ok=True)
    path=directory/(cell_id+'.json')
    value=dict(schema='CANONICAL_IMMUTABLE_MANIFEST_CELL_LAUNCH_CLAIM_V1',
        manifest_SHA256=MANIFEST_SHA256,cell_id=cell_id,claim_UTC=utc(),controller_PID=os.getpid(),
        status='RESERVED_BEFORE_PROCESS_SPAWN',automatic_clear_or_retry=False,
        financial_snapshot_resume=False,**metadata)
    try:save(path,value)
    except FileExistsError:raise RuntimeError('PERMANENT_CANONICAL_CELL_CLAIM_EXISTS_NO_DUPLICATE_LAUNCH:'+cell_id)
    descriptor=os.open(directory,os.O_RDONLY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)
    return path


def validate_worker_claim(args,*,preparation_raw,go_raw,review_raw,registry_root=None,handshake_seconds=2):
    e=_entry();cell=e.cell_descriptor(args.cell_id);prep=json.loads(preparation_raw)
    registry=Path(registry_root) if registry_root is not None else HERE/'EXECUTION_CLAIMS'
    path=registry/MANIFEST_SHA256/(args.cell_id+'.json')
    if not path.is_file() or path.is_symlink():raise ValueError('EXACT_CANONICAL_PRELAUNCH_CLAIM_REQUIRED')
    raw=path.read_bytes();claim=json.loads(raw)
    expected=dict(schema='CANONICAL_IMMUTABLE_MANIFEST_CELL_LAUNCH_CLAIM_V1',manifest_SHA256=MANIFEST_SHA256,
        cell_id=args.cell_id,year=cell['year'],config=cell['config'],source_identity=prep['years'][str(cell['year'])]['source_identity'],
        selected_target_raw_SHA256=cell['selected_target_raw_SHA256'],preparation_SHA256=sha(preparation_raw),
        code_identity=prep['code_identity'],root_GO_SHA256=sha(go_raw),independent_review_SHA256=sha(review_raw),
        requested_CPU=args.cpu,case_output=str(Path(args.case_output).resolve()),status='RESERVED_BEFORE_PROCESS_SPAWN',
        automatic_clear_or_retry=False,financial_snapshot_resume=False,
        global_controller_lease_key=MANIFEST_SHA256+'/CONTROLLER_LEASE.lock')
    if any(body(claim.get(k))!=body(v) for k,v in expected.items()):raise ValueError('EXACT_FOUR_CELL_WORKER_CLAIM_SCOPE_REQUIRED')
    if registry.resolve()==(HERE/'EXECUTION_CLAIMS').resolve():
        boot=json.loads((Path(args.case_output)/'BOOTSTRAP_READY.json').read_bytes())
        limits={name:list(resource.getrlimit(which)) for name,which in (('AS',resource.RLIMIT_AS),('CPU',resource.RLIMIT_CPU),('RSS',resource.RLIMIT_RSS))}
        if (boot.get('PID')!=os.getpid() or boot.get('requested_CPU')!=args.cpu or boot.get('actual_affinity')!=[args.cpu]
                or boot.get('limits')!=limits or boot.get('thread_environment')!={k:'1' for k in THREAD_ENV}):
            raise ValueError('EXACT_PRE_NUMERICAL_RESOURCE_BOOTSTRAP_REQUIRED')
        fd=os.environ.get('MATRIX_CONTROLLER_LEASE_FD','')
        if not fd.isdigit():raise ValueError('INHERITED_CANONICAL_CONTROLLER_LEASE_FD_REQUIRED')
        try:
            held=os.fstat(int(fd));canonical=(registry/MANIFEST_SHA256/'CONTROLLER_LEASE.lock').stat()
        except (OSError,ValueError):raise ValueError('INHERITED_CANONICAL_CONTROLLER_LEASE_FD_REQUIRED')
        if (held.st_dev,held.st_ino)!=(canonical.st_dev,canonical.st_ino):
            raise ValueError('EXACT_CANONICAL_CONTROLLER_LEASE_INODE_REQUIRED')
    ownership=Path(args.case_output)/'PROCESS_OWNERSHIP.json';deadline=time.monotonic()+handshake_seconds
    while not ownership.is_file() and time.monotonic()<deadline:time.sleep(.01)
    if not ownership.is_file() or ownership.is_symlink():raise ValueError('EXACT_WORKER_PROCESS_OWNERSHIP_REQUIRED')
    owner=json.loads(ownership.read_bytes());actual=process_observation(os.getpid())
    if (owner.get('cell_id')!=args.cell_id or owner.get('PID')!=os.getpid() or owner.get('CPU')!=args.cpu
            or owner.get('controller_PID')!=os.getppid() or claim.get('controller_PID')!=os.getppid()
            or actual is None or owner.get('process_start_ticks')!=actual['process_start_ticks']
            or actual['CPU_affinity']!=[args.cpu] or any(t['CPU_affinity']!=[args.cpu] for t in actual['tasks'])):
        raise ValueError('EXACT_LIVE_WORKER_PID_START_CPU_PARENT_REQUIRED')
    return raw


def case(args):
    apply_limits(args.cpu)
    e=_entry()
    prep_raw,go,review=validate_scope(args,worker=True)
    claim=validate_worker_claim(args,preparation_raw=prep_raw,go_raw=go,review_raw=review)
    import numpy as np
    import forecast_historical as integration
    if Path(integration.__file__).resolve()!=HERE/'forecast_historical.py':
        raise ValueError('EXACT_LOCAL_FORECAST_HISTORICAL_INTEGRATION_REQUIRED')
    checker=_checker()
    directory=Path(args.case_output);write_bytes(directory/'LAUNCH_CLAIM.json',claim)
    prep=json.loads(prep_raw);cell=e.cell_descriptor(args.cell_id)
    began=time.monotonic();started=utc()
    try:
        sim,guard=e.make_case({2023:args.source_2023,2024:args.source_2024},args.preparation,
            go,args.go_sha,cell_id=args.cell_id,review_raw=review,expected_review_sha256=args.review_sha)
        construction=time.monotonic()-began
        while sim.cursor<sim.end and sim.stop is None:
            sim.advance_day()
            print(json.dumps(dict(event='NATIVE_DAY_COMPLETE',cell_id=args.cell_id,
                completed_minutes=sim.rows_written,stop_us=sim.stop,UTC=utc())),flush=True)
        result=integration.case_result(sim,guard)
        minute=result.pop('minute');values=minute.to_numpy();columns=minute.columns
        result['targets']=result['targets'].to_dicts()
        audit=integration.V2.OWNED.export_tree(sim.account.snapshot())
        result=integration.V2.OWNED.export_tree(result)
        legacy=result['primary_financial_reconciliation']
        proof=checker.reconcile_saved_native(audit,result,expected_continuation_version=integration.VERSION)
        validate_policy_evidence(audit,result,historical=True)
        classification=R.classify_terminal(audit,result,calendar=cell['calendar'],completed_minutes=sim.rows_written,stop_us=sim.stop)
        with np.load(BytesIO((Path(args.preparation)/f"{cell['year']}/TARGETS.npz").read_bytes()),allow_pickle=False) as z:
            risk=R.held_risk_report(values,columns,z['decision_us'],z['annual_covariance'],z[cell['config']],cell['tier'],guard.receipts)
        np.savez_compressed(directory/'MINUTE.npz',values=values,columns=np.asarray(columns))
        with (directory/'MINUTE.npz').open('rb') as stream:os.fsync(stream.fileno())
        quality=guard.causal_mark_quality_guard
        evidence={'ACCOUNT_FINANCIAL_AUDIT.json':audit,'NATIVE_RESULT.json':result,
            'LEGACY_PRIMARY_FINANCIAL_RECONCILIATION.json':legacy,'PRIMARY_FINANCIAL_RECONCILIATION.json':proof,
            'NATIVE40_RECONSTRUCTION_PROOF.json':proof,'ACTUAL_HELD_RISK_REPORT.json':risk,
            'GUARD_RECEIPTS.json':integration.V2.OWNED.export_tree(guard.receipts),
            'CAUSAL_MARK_QUALITY.json':dict(identity=quality.identity,policy_SHA256=quality.policy_sha256,
                receipts=integration.V2.OWNED.export_tree(quality.receipts),original_interpolated_marks_execution_admitted=False)}
        for name,value in evidence.items():save(directory/name,value)
        write_bytes(directory/'ADMISSION_GO.json',go);write_bytes(directory/'ADMISSION_REVIEW.json',review)
        if e.code_identity()!=prep['code_identity']:raise ValueError('CODE_CHANGED_DURING_CASE')
        receipt=dict(schema='FINITE_CAUSAL_FORECAST_FOUR_CELL_CASE_V1',cell_id=args.cell_id,year=cell['year'],
            strategy=cell['strategy'],tier=cell['tier'],config=cell['config'],calendar=cell['calendar'],cost=e.COST,
            policy_variant=integration.POLICY_VARIANT,status=classification,adaptive_DEV_only=True,
            root_GO_SHA256=args.go_sha,independent_review_SHA256=args.review_sha,preparation_SHA256=sha(prep_raw),
            manifest_SHA256=e.MANIFEST_SHA256,source_identity=prep['years'][str(cell['year'])]['source_identity'],
            code_identity=prep['code_identity'],policy_identity=prep['policy_identity'],checker_SHA256=checker.checker_sha256(),
            reconstruction_proof_SHA256=sha((directory/'NATIVE40_RECONSTRUCTION_PROOF.json').read_bytes()),
            completed_minutes=sim.rows_written,required_minutes=cell['required_minutes'],account_stop_us=sim.stop,
            started_UTC=started,ended_UTC=utc(),construction_seconds=construction,total_wall_seconds=time.monotonic()-began,
            max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
            PID=os.getpid(),requested_CPU=args.cpu,actual_CPU_affinity=sorted(os.sched_getaffinity(0)),
            thread_environment={k:os.environ[k] for k in THREAD_ENV},limits=LIMITS,no_halt_reset=True,
            snapshot_restart_certified=False,automatic_retry=False,native_exchange_or_funding_publication_certified=False,
            locked_source_reads=0,publication_actions=0)
        save(directory/'CASE_RECEIPT.json',receipt)
        if own_bytes(directory)>LIMITS['per_case_output_bytes']:raise RuntimeError('OUTPUT_LIMIT')
        save(directory/'TERMINAL_CHECKPOINT.json',dict(schema='IMMUTABLE_MATRIX_TERMINAL_CHECKPOINT_V1',
            cell_id=args.cell_id,files={name:sha((directory/name).read_bytes()) for name in TERMINAL_FILES},
            checker_SHA256=checker.checker_sha256(),reconstruction_proof_SHA256=receipt['reconstruction_proof_SHA256'],
            all_evidence_fsynced=True,restart_financial_snapshot_permission=False))
    except BaseException as error:
        if 'sim' in locals():
            try:save(directory/'FAILED_ACCOUNT_FINANCIAL_AUDIT.json',integration.V2.OWNED.export_tree(sim.account.snapshot()))
            except BaseException:pass
        save(directory/'FAILURE.json',dict(kind='EXECUTION_RESOURCE_DATA_OR_VALIDATION_INTERRUPTION',
            error=repr(error),traceback=traceback.format_exc(),UTC=utc(),automatic_retry=False))
        raise


def validate_policy_evidence(audit,result,*,historical=True):
    """Narrow saved policy invariants in addition to unchanged native finance."""
    import forecast_monitor as f
    if Path(f.__file__).resolve()!=HERE/'forecast_monitor.py':
        raise ValueError('EXACT_LOCAL_FORECAST_MONITOR_REQUIRED')
    contract=audit.get('contract',{})
    common=result.get('common_execution_policy',{})
    forecast=result.get('forecast_risk_monitor',{})
    summary=result.get('summary',{})
    economic=result.get('continuation_economic_report',{})
    expected_contract=dict(version=f.VERSION,integration_version=f.VERSION,continuation_policy=f.VERSION,
        bound_nominal_tier='MID',original_mid_forecast_budget=.10,topup_enabled=False,
        automatic_topup=False,no_autonomous_rerisking=True,historical_execution_admitted=historical,
        generated_only=not historical,policy_variant=f.E.POLICY_VARIANT,
        frozen_D_rule_SHA256=f.E.FROZEN_D_PINS['guard50_exit.py'],
        free_cash_floor='1000',total_isolated_ceiling='8500',leverage=1,
        paid_partial_fills_atomic=False,per_fill_variance_monotonicity_guaranteed=False)
    expected_common=dict(version=f.VERSION,tier='MID',original_mid_forecast_budget=.10,
        annual_covariance_volatility_ceiling=.10,automatic_topup=False,no_autonomous_rerisking=True,
        historical_execution_admitted=historical,policy_variant=f.E.POLICY_VARIANT,
        free_cash_increase_floor='1000',actual_isolated_margin_ceiling='8500',
        initial_cash='10000',leverage=1,forecast_risk_monitor=True)
    expected_forecast=dict(version=f.VERSION,original_mid_budget=.10,automatic_topup=False,
        no_autonomous_rerisking=True,historical_execution_admitted=historical,
        partial_fills_atomic=False,per_fill_variance_monotonicity_guaranteed=False,
        completed_projection_strict_variance_reduction_required=True,historical_control_reruns=0)
    for value,expected in ((contract,expected_contract),(common,expected_common),(forecast,expected_forecast)):
        if any(body(value.get(k))!=body(v) for k,v in expected.items()):
            raise ValueError('EXACT_SAVED_FORECAST_POLICY_METADATA_REQUIRED')
    if (audit.get('continuation_policy')!=f.VERSION or audit.get('bound_nominal_tier')!='MID'
            or audit.get('historical_execution_admitted') is not historical
            or summary.get('version')!=f.VERSION or economic.get('version')!=f.VERSION
            or body(summary.get('contract'))!=body(contract) or body(economic.get('contract'))!=body(contract)
            or audit.get('transfer_journal')!=[] or audit.get('transfer_ids')!={}
            or economic.get('transfers')!=[]
            or forecast.get('journal')!=audit.get('forecast_journal')
            or forecast.get('paid_fill_variance_journal')!=audit.get('forecast_fill_journal')
            or forecast.get('pending_cohort')!=audit.get('forecast_active')
            or type(audit.get('deferred_ordinary_reduction_close_count')) is not int
            or audit['deferred_ordinary_reduction_close_count']<0
            or type(forecast.get('deferred_ordinary_reduction_close_count')) is not int
            or forecast.get('deferred_ordinary_reduction_close_count')!=audit['deferred_ordinary_reduction_close_count']):
        raise ValueError('SAVED_FORECAST_NO_TRANSFER_IDENTITY_JOURNAL_REQUIRED')
    for row in audit['forecast_journal']:
        if row.get('kind')=='COHORT_CREATED':
            sigma=row.get('sigma');alpha=row.get('alpha')
            current=row.get('current_variance');projected=row.get('projected_variance')
            values=(sigma,alpha,current,projected)
            valid=all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in values)
            if (not valid or not sigma>.10 or not 0<alpha<=1
                    or alpha!=min(1.,.10/sigma) or not projected<current):
                raise ValueError('SAVED_FORECAST_STRICT_MINIMUM_PROJECTION_REQUIRED')
    return True


def validate_saved_terminal(directory,*,preparation_raw,preparation_directory,cell_id,expected_go_sha256,expected_review_sha256):
    e=_entry();checker=_checker()
    import forecast_historical as integration
    if Path(integration.__file__).resolve()!=HERE/'forecast_historical.py':
        raise ValueError('EXACT_LOCAL_FORECAST_HISTORICAL_INTEGRATION_REQUIRED')
    directory=Path(directory);prep=json.loads(preparation_raw)
    if prep.get('code_identity')!=e.code_identity():
        raise ValueError('SAVED_FORECAST_PREPARATION_CURRENT_CODE_MISMATCH')
    cp=json.loads((directory/'TERMINAL_CHECKPOINT.json').read_bytes())
    if (cp.get('cell_id')!=cell_id or cp.get('all_evidence_fsynced') is not True
            or cp.get('restart_financial_snapshot_permission') is not False
            or set(cp.get('files',{}))!=set(TERMINAL_FILES)
            or any(sha((directory/name).read_bytes())!=cp['files'][name] for name in TERMINAL_FILES)
            or cp.get('checker_SHA256')!=checker.checker_sha256()):
        raise ValueError('EXACT_ALL_TERMINAL_BYTES_CHECKER_REQUIRED')
    go,review=(directory/'ADMISSION_GO.json').read_bytes(),(directory/'ADMISSION_REVIEW.json').read_bytes()
    admitted=e.validate_root_go(preparation_raw,go,expected_go_sha256,cell_id=cell_id)
    e._validate_independent_review(preparation_raw,admitted,review,expected_review_sha256,go)
    receipt=json.loads((directory/'CASE_RECEIPT.json').read_bytes());cell=e.cell_descriptor(cell_id)
    claim=HERE/'EXECUTION_CLAIMS'/MANIFEST_SHA256/(cell_id+'.json')
    if not claim.is_file() or claim.read_bytes()!=(directory/'LAUNCH_CLAIM.json').read_bytes():
        raise ValueError('SAVED_TERMINAL_CANONICAL_LAUNCH_CLAIM_REQUIRED')
    expected=dict(schema='FINITE_CAUSAL_FORECAST_FOUR_CELL_CASE_V1',cell_id=cell_id,year=cell['year'],
        strategy=cell['strategy'],tier=cell['tier'],config=cell['config'],calendar=cell['calendar'],cost=e.COST,
        policy_variant=integration.POLICY_VARIANT,adaptive_DEV_only=True,root_GO_SHA256=expected_go_sha256,
        independent_review_SHA256=expected_review_sha256,preparation_SHA256=sha(preparation_raw),
        manifest_SHA256=e.MANIFEST_SHA256,source_identity=prep['years'][str(cell['year'])]['source_identity'],
        code_identity=prep['code_identity'],policy_identity=prep['policy_identity'],checker_SHA256=checker.checker_sha256(),
        required_minutes=cell['required_minutes'],limits=LIMITS,no_halt_reset=True,snapshot_restart_certified=False,
        automatic_retry=False,native_exchange_or_funding_publication_certified=False,locked_source_reads=0,publication_actions=0)
    if any(body(receipt.get(k))!=body(v) for k,v in expected.items()):raise ValueError('EXACT_SAVED_FORECAST_SCOPE_REQUIRED')
    audit=json.loads((directory/'ACCOUNT_FINANCIAL_AUDIT.json').read_bytes())
    result=json.loads((directory/'NATIVE_RESULT.json').read_bytes())
    proof=checker.reconcile_saved_native(audit,result,expected_continuation_version=integration.VERSION)
    validate_policy_evidence(audit,result,historical=True)
    if (body(proof)!=(directory/'NATIVE40_RECONSTRUCTION_PROOF.json').read_bytes()
            or body(proof)!=(directory/'PRIMARY_FINANCIAL_RECONCILIATION.json').read_bytes()
            or sha(body(proof))!=receipt['reconstruction_proof_SHA256']
            or cp['reconstruction_proof_SHA256']!=receipt['reconstruction_proof_SHA256']
            or result['primary_financial_reconciliation']!=json.loads((directory/'LEGACY_PRIMARY_FINANCIAL_RECONCILIATION.json').read_bytes())):
        raise ValueError('EXACT_NATIVE40_RAW100_PROOF_BINDING_REQUIRED')
    if receipt['status']!=R.classify_terminal(audit,result,calendar=cell['calendar'],completed_minutes=receipt['completed_minutes'],stop_us=receipt['account_stop_us']):
        raise ValueError('EXACT_TERMINAL_STATUS_REQUIRED')
    R.validate_saved_risk_report(directory,preparation_directory=preparation_directory,preparation_raw=preparation_raw,cell=cell,receipt=receipt,result=result)
    for key in ('cell_id','year','strategy','config','preparation_SHA256','source_identity','root_GO_SHA256','independent_review_SHA256','policy_identity','policy_variant'):
        if audit['historical_execution_scope'].get(key)!=receipt[key]:raise ValueError('EXACT_AUDIT_EXECUTION_SCOPE_REQUIRED:'+key)
    if (receipt['actual_CPU_affinity']!=[receipt['requested_CPU']] or receipt['requested_CPU'] not in json.loads(go)['worker_CPUs']
            or receipt['thread_environment']!={k:'1' for k in THREAD_ENV}
            or receipt['total_wall_seconds']>600 or receipt['CPU_seconds']>600
            or receipt['max_RSS_bytes']>LIMITS['per_case_RSS_stop_bytes'] or own_bytes(directory)>LIMITS['per_case_output_bytes']):
        raise ValueError('SAVED_CASE_RESOURCE_LIMIT_MISMATCH')
    return receipt


def controller(args):
    if Path(args.output).exists():raise ValueError('EXISTING_OUTPUT_REFUSED_NO_SCHEDULING_RESUME')
    raw_go=Path(args.go).read_bytes()
    if sha(raw_go)!=args.go_sha:raise ValueError('EXACT_EXTERNAL_GO_BYTES_REQUIRED')
    initial=json.loads(raw_go)
    choose_worker_count(initial.get('requested_worker_count'),initial.get('worker_CPUs'),host_observation())
    for key in THREAD_ENV:os.environ[key]='1'
    R.confine_existing_threads(initial['worker_CPUs'])
    prep,go,review=validate_scope(args);admission=json.loads(go);parsed=json.loads(prep);e=_entry()
    for cell in admission['permitted_cells']:
        checked=e.validate_case_inputs({2023:args.source_2023,2024:args.source_2024},args.preparation,go,args.go_sha,cell_id=cell)
        del checked
    output=Path(args.output)
    if output.exists():raise ValueError('EXISTING_OUTPUT_REFUSED_NO_SCHEDULING_RESUME')
    output.mkdir(exist_ok=False);write_bytes(output/('ADMISSION_'+args.go_sha+'.json'),go)
    jobs=[]
    for cell in admission['permitted_cells']:
        def builder(directory,cpu,cell=cell):
            return [sys.executable,'-B',str(Path(__file__).resolve()),'--case','--cell-id',cell,'--cpu',str(cpu),
                '--source-2023',str(Path(args.source_2023).resolve()),'--source-2024',str(Path(args.source_2024).resolve()),
                '--preparation',str(Path(args.preparation).resolve()),'--go',str(Path(args.go).resolve()),'--go-sha',args.go_sha,
                '--review',str(Path(args.review).resolve()),'--review-sha',args.review_sha,'--case-output',str(directory.resolve())]
        jobs.append((cell,builder))
    def before_launch(cell_id,directory,cpu):
        cell=e.cell_descriptor(cell_id)
        if e.code_identity()!=parsed['code_identity']:raise ValueError('CODE_CHANGED_BEFORE_LAUNCH_CLAIM')
        choose_worker_count(admission['requested_worker_count'],admission['worker_CPUs'],host_observation())
        claim_launch(HERE/'EXECUTION_CLAIMS',cell_id=cell_id,manifest_sha256=MANIFEST_SHA256,metadata=dict(
            year=cell['year'],config=cell['config'],source_identity=parsed['years'][str(cell['year'])]['source_identity'],
            selected_target_raw_SHA256=cell['selected_target_raw_SHA256'],preparation_SHA256=sha(prep),code_identity=parsed['code_identity'],
            root_GO_SHA256=args.go_sha,independent_review_SHA256=args.review_sha,requested_CPU=cpu,
            case_output=str(directory.resolve()),controller_output=str(output.resolve()),
            global_controller_lease_key=MANIFEST_SHA256+'/CONTROLLER_LEASE.lock'))
    try:
        with controller_lease(HERE/'EXECUTION_CLAIMS'):
            report=run_pool(jobs,output,requested_workers=admission['requested_worker_count'],cpus=admission['worker_CPUs'],
                validator=lambda directory,cell:validate_saved_terminal(directory,preparation_raw=prep,preparation_directory=args.preparation,
                    cell_id=cell,expected_go_sha256=args.go_sha,expected_review_sha256=args.review_sha),before_launch=before_launch)
        report.update(root_GO_SHA256=args.go_sha,manifest_SHA256=MANIFEST_SHA256,tranche=admission['tranche'],adaptive_DEV_only=True,publication_actions=0)
        save(output/('CONTROLLER_RECEIPT_'+args.go_sha+'.json'),report)
    except BaseException as error:
        save(output/('CONTROLLER_PAUSE_'+args.go_sha+'.json'),dict(status='EXECUTION_RESOURCE_DATA_OR_VALIDATION_PAUSE',
            error=repr(error),UTC=utc(),automatic_retry=False,economic_halt_relabelled=False));raise


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--case',action='store_true')
    for name in ('source-2023','source-2024','preparation','go','go-sha','review','review-sha'):p.add_argument('--'+name,required=True)
    for name in ('cell-id','case-output','output'):p.add_argument('--'+name)
    p.add_argument('--cpu',type=int);args=p.parse_args()
    case(args) if args.case else controller(args)


if __name__=='__main__':main()
