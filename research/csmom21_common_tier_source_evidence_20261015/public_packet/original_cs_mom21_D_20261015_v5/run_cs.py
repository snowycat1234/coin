"""Finite FIRST6 fresh-wallet controller. Importing this file starts nothing.

Original-D process safety is reused in cs_process_runtime. Source recapture is
guarded before any financial class import; saved CS targets are never rebuilt.
"""
import os
THREAD_ENV = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'POLARS_MAX_THREADS', 'VECLIB_MAXIMUM_THREADS')
for key in THREAD_ENV:
    os.environ[key] = '1'

import argparse
from io import BytesIO
import json
from pathlib import Path
import re
import resource
import sys
import time
import traceback

import cs_process_runtime as r
import cs_supersession as supersession

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCOPE_SHA = '9a5ef547d61272d5eb0bfb1b61fef8005a752d82f4e0007d18cbe65f06445a8a'
WIRE_NAMES = ('go', 'review', 'prepared-review', 'native-review', 'source-go', 'source-review')
EXTRA_TERMINAL = ('SOURCE_RECAPTURE_GUARD_RECEIPT.json', 'PREPARED_TARGET_REVIEW.json',
                  'NATIVE_GENERATED_REVIEW.json', 'WORKER_AUTHORITY_VERIFIED.json',
                  'WORKER_SOURCE_ACCEPTED_BEFORE_ACCOUNT.json')
TERMINAL_FILES = r.TERMINAL_FILES + EXTRA_TERMINAL


def ordinary(path):
    path = Path(path).absolute()
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('ORDINARY_NO_SYMLINK_PATH_REQUIRED')
    return path


def wires(args):
    import cs_common as c
    import cs_entry as e
    import cs_finance_gate as gate
    if c.HERE != HERE or Path(e.__file__).resolve() != HERE / 'cs_entry.py':
        raise ValueError('EXACT_NEW_CS_SOURCE_MODULES_REQUIRED')
    prep_root = ordinary(args.preparation)
    raw = c.exact(prep_root / 'PREPARATION.json', args.preparation_sha)
    blobs = {name: c.exact(ordinary(getattr(args, name.replace('-', '_'))),
                          getattr(args, name.replace('-', '_') + '_sha')) for name in WIRE_NAMES}
    e.validate_source_authority_metadata(blobs['source-go'], args.source_go_sha,
                                        blobs['source-review'], args.source_review_sha)
    gate.validate(raw, blobs['go'], args.go_sha, blobs['review'], args.review_sha,
                  blobs['prepared-review'], args.prepared_review_sha, blobs['native-review'], args.native_review_sha)
    import cs_verified_wires
    prep = cs_verified_wires.exact_preparation_shape(raw)
    if (prep['source_stage_GO_SHA256'] != args.source_go_sha
            or prep['source_review_SHA256'] != args.source_review_sha):
        raise ValueError('EXACT_PREPARED_NEW_CS_SOURCE_LINEAGE_REQUIRED')
    return raw, prep, blobs


def read_paths(args, prep):
    import cs_common as c
    import cs_entry as e
    paths = []
    for name in ('CODE_MANIFEST.json', 'FINANCIAL_CODE_MANIFEST.json'):
        record = c.exact_object((HERE / name).read_bytes())
        paths += [HERE / key for key in record['files']]
        paths += [ROOT / key for key in record['dependencies']]
        paths.append(HERE / name)
    paths += [ordinary(getattr(args, name.replace('-', '_'))) for name in WIRE_NAMES]
    paths += [ordinary(args.preparation) / 'PREPARATION.json']
    paths += [ordinary(args.preparation) / c.relative(name) for name in prep['artifacts']]
    for year in e.tranche_years(e.FIRST6):
        paths += [ROOT / key for key in e.contracts()['years'][str(year)]['read_files']]
    return paths


def load_saved_year(args, prep, verified_binding):
    # Exact frozen CLI imports only its two finite stdlib codec dependencies.
    import prepare_cs_source
    import cs_source_bridge
    import cs_signal
    import cs_quality
    import cs_loader
    from cs_source_guard import SourceOnlyGuard
    cs_signal.originals(); cs_signal.common_grid(); cs_quality.original_quality()
    year = int(args.cell_id[:4])
    guard = SourceOnlyGuard(read_paths=read_paths(args, prep), write_roots=())
    loaded = None
    try:
        with guard:
            guard.checkpoint('FRESH_WORKER_CS_SOURCE_RECAPTURE_BEFORE_FINANCE_IMPORT')
            loaded = cs_loader.load_year(args.preparation, expected_preparation_sha256=args.preparation_sha,
                year=year, source_go_raw=Path(args.source_go).read_bytes(),
                expected_source_go_sha256=args.source_go_sha, source_review_raw=Path(args.source_review).read_bytes(),
                expected_source_review_sha256=args.source_review_sha, financial_go_raw=Path(args.go).read_bytes(),
                expected_financial_go_sha256=args.go_sha, financial_review_raw=Path(args.review).read_bytes(),
                expected_financial_review_sha256=args.review_sha,
                prepared_review_raw=Path(args.prepared_review).read_bytes(),
                expected_prepared_review_sha256=args.prepared_review_sha,
                native_review_raw=Path(args.native_review).read_bytes(),
                expected_native_review_sha256=args.native_review_sha, verified_binding=verified_binding)
            guard.checkpoint('EXACT_SAVED_CS_TARGETS_LOADED_WITHOUT_REGENERATION')
        import cs_entry
        receipt = guard.receipt('PASS_FINANCIAL_WORKER_SOURCE_ONLY_RECAPTURE')
        receipt.update(source_scopes_revoked=not cs_entry._ACTIVE_SOURCE,
                       saved_targets_and_covariance_rebuilt=False)
        return loaded, receipt
    except BaseException:
        if loaded is not None:
            cs_loader.revoke(loaded)
        r.save(Path(args.case_output) / 'FAILED_SOURCE_RECAPTURE_GUARD_RECEIPT.json',
               guard.receipt('STOP_FINANCIAL_WORKER_SOURCE_ONLY_RECAPTURE'))
        raise


def expected_claim(args, prep_raw, prep):
    import cs_config as config
    import cs_finance_gate as gate
    cell = config.cell_named(args.cell_id)
    value = dict(schema='CANONICAL_IMMUTABLE_MANIFEST_CELL_LAUNCH_CLAIM_V1', manifest_SHA256=SCOPE_SHA,
        cell_id=args.cell_id, year=cell['year'], config=config.STRATEGY + '_' + cell['tier'],
        source_identity=prep['years'][str(cell['year'])]['source_identity'],
        selected_target_raw_SHA256=prep['cells'][args.cell_id]['input_binding']['selected_target_raw_SHA256'],
        preparation_SHA256=r.sha(prep_raw), code_identity=gate.code_identity(),
        root_GO_SHA256=args.go_sha, independent_review_SHA256=args.review_sha,
        prepared_source_target_review_SHA256=args.prepared_review_sha,
        native_generated_review_SHA256=args.native_review_sha, requested_CPU=args.cpu,
        case_output=str(ordinary(args.case_output)), status='RESERVED_BEFORE_PROCESS_SPAWN',
        automatic_clear_or_retry=False, financial_snapshot_resume=False,
        global_controller_lease_key=SCOPE_SHA + '/CONTROLLER_LEASE.lock',
        stable_cross_version_claim_registry=supersession.STABLE_REGISTRY_REL,
        failed_claim_supersession_packet_SHA256=supersession.PACKET_SHA)
    if args.cell_id in supersession.FAILED_CELLS:
        value.update(superseded_claim_SHA256=supersession.packet()['failed_claims'][args.cell_id]['SHA256'],
                     one_use_consumption_permanent=True, original_claim_unchanged=True)
    return value



def worker_claim(args, prep_raw, prep):
    import cs_common as c
    claim_path = ordinary(supersession.claim_path(args.cell_id))
    raw = claim_path.read_bytes(); claim = c.exact_object(raw)
    if any(c.canonical(claim.get(k)) != c.canonical(v) for k, v in expected_claim(args, prep_raw, prep).items()):
        raise ValueError('EXACT_NEW_CS_CANONICAL_WORKER_CLAIM_REQUIRED')
    directory = ordinary(args.case_output)
    bootstrap = c.exact_object((directory / 'BOOTSTRAP_READY.json').read_bytes())
    limits = {name: list(resource.getrlimit(which)) for name, which in
              (('AS', resource.RLIMIT_AS), ('CPU', resource.RLIMIT_CPU), ('RSS', resource.RLIMIT_RSS))}
    if (bootstrap.get('PID') != os.getpid() or bootstrap.get('requested_CPU') != args.cpu
            or bootstrap.get('actual_affinity') != [args.cpu] or bootstrap.get('limits') != limits
            or bootstrap.get('thread_environment') != {key: '1' for key in THREAD_ENV}):
        raise ValueError('EXACT_PRE_NUMERICAL_BOOTSTRAP_REQUIRED')
    fd = os.environ.get('MATRIX_CONTROLLER_LEASE_FD', '')
    if not fd.isdigit():
        raise ValueError('INHERITED_CANONICAL_CONTROLLER_LEASE_FD_REQUIRED')
    held = os.fstat(int(fd)); canonical = (supersession.registry_root() / SCOPE_SHA / 'CONTROLLER_LEASE.lock').stat()
    if (held.st_dev, held.st_ino) != (canonical.st_dev, canonical.st_ino):
        raise ValueError('EXACT_CANONICAL_LEASE_INODE_REQUIRED')
    deadline = time.monotonic() + 2
    owner_path = directory / 'PROCESS_OWNERSHIP.json'
    while not owner_path.is_file() and time.monotonic() < deadline:
        time.sleep(.01)
    owner = c.exact_object(ordinary(owner_path).read_bytes()); actual = r.process_observation(os.getpid())
    if (owner.get('cell_id') != args.cell_id or owner.get('PID') != os.getpid() or owner.get('CPU') != args.cpu
            or owner.get('controller_PID') != os.getppid() or claim.get('controller_PID') != os.getppid()
            or actual is None or owner.get('process_start_ticks') != actual['process_start_ticks']
            or actual['CPU_affinity'] != [args.cpu]
            or any(t['CPU_affinity'] != [args.cpu] for t in actual['tasks'])):
        raise ValueError('EXACT_LIVE_PARENT_WORKER_PID_START_AND_CPU_REQUIRED')
    return raw


def held_risk(values, columns, loaded, tier, receipts):
    import numpy as np
    import cs_native as native
    import annual_reporting
    arr = np.asarray(values); names = list(columns)
    if not len(arr):
        return dict(status='NOT_EVALUABLE_NO_COMPLETED_NATIVE_MINUTES', observation_count=0,
                    nominal_tier_equality_is_not_exact_realized_risk_matching=True)
    bad = np.flatnonzero(arr[:, names.index('nav')] <= 0)
    count = int(bad[0]) if len(bad) else len(arr)
    if count == 0:
        return dict(status='NOT_EVALUABLE_NONPOSITIVE_NAV', observation_count=0,
                    omitted_nonpositive_or_later_minutes=len(arr), nominal_tier_equality_is_not_exact_realized_risk_matching=True)
    targets = loaded.arrays['CSMOM21_COMMON_TIER_' + tier]
    report = annual_reporting.risk_diagnostics(arr[:count], names, loaded.arrays['decision_us'],
        loaded.arrays['annual_covariance'], targets, tier, receipts)
    weights = np.column_stack([arr[:count, names.index(s + '_signed_weight')] for s in native.S]); net = weights.sum(axis=1)
    report.update(status='ACTUAL_HELD_MINUTE_OBSERVATIONS' if count == len(arr) else 'POSITIVE_NAV_PREFIX_ONLY',
        omitted_nonpositive_or_later_minutes=len(arr)-count, actual_net_signed_weight_min=float(net.min()),
        actual_net_signed_weight_max=float(net.max()), actual_net_signed_weight_mean=float(net.mean()),
        actual_absolute_weight_max_by_symbol=dict(zip(native.S, np.abs(weights).max(axis=0).tolist())),
        actual_signed_weight_min_by_symbol=dict(zip(native.S, weights.min(axis=0).tolist())),
        actual_signed_weight_max_by_symbol=dict(zip(native.S, weights.max(axis=0).tolist())),
        adaptive_DEV_only=True, nominal_tier_equality_is_not_exact_realized_risk_matching=True,
        reporting_code_SHA256=r.sha(Path(annual_reporting.__file__).read_bytes()),
        funding_publication_certified=False, native_exchange_execution_certified=False)
    return report


def case(args):
    r.apply_limits(args.cpu)
    prep_raw, prep, blobs = wires(args)
    import cs_config as config
    if args.cell_id not in json.loads(blobs['go'])['ordered_cells']:
        raise ValueError('EXACT_ADMITTED_FIRST6_CELL_REQUIRED')
    claim = worker_claim(args, prep_raw, prep)
    directory = ordinary(args.case_output); r.write_bytes(directory / 'LAUNCH_CLAIM.json', claim)
    began, started = time.monotonic(), r.utc(); loaded = None
    try:
        import cs_verified_wires
        hashes = {name: getattr(args, name.replace('-', '_') + '_sha') for name in WIRE_NAMES}
        with cs_verified_wires.verify(preparation_raw=prep_raw, cell_id=args.cell_id, raw=blobs, hashes=hashes, claim_raw=claim) as binding:
            r.save(directory / 'WORKER_AUTHORITY_VERIFIED.json', dict(schema='CS_WORKER_PREFINANCE_PHASE_V1',
                phase='EXACT_EXECUTABLE_GO_VERIFIED_OUTSIDE_UNCHANGED_SOURCE_GUARD', cell_id=args.cell_id,
                root_GO_SHA256=args.go_sha, preparation_SHA256=r.sha(prep_raw), financial_code_manifest_SHA256=binding.code_sha,
                claim_SHA256=r.sha(claim), PID=os.getpid(), UTC=r.utc(), source_capture_started=False,
                historical_scopes_constructed=0, providers_constructed=0, accounts_constructed=0))
            loaded, source_receipt = load_saved_year(args, prep, binding)
        if cs_verified_wires._LIVE:
            raise ValueError('PREFLIGHT_BINDING_NOT_REVOKED')
        r.save(directory / 'SOURCE_RECAPTURE_GUARD_RECEIPT.json', source_receipt)
        r.save(directory / 'WORKER_SOURCE_ACCEPTED_BEFORE_ACCOUNT.json', dict(schema='CS_WORKER_PREFINANCE_PHASE_V1',
            phase='SOURCE_RECAPTURE_AND_SAVED_TARGET_BINDING_ACCEPTED_GUARD_EXITED', cell_id=args.cell_id,
            root_GO_SHA256=args.go_sha, preparation_SHA256=r.sha(prep_raw),
            source_guard_receipt_SHA256=r.sha((directory / 'SOURCE_RECAPTURE_GUARD_RECEIPT.json').read_bytes()),
            PID=os.getpid(), UTC=r.utc(), verified_wires_revoked=True, historical_scopes_constructed=0,
            providers_constructed=0, accounts_constructed=0))
        # Financial classes enter only after the clean source-only guard exits.
        import cs_admission
        import cs_native as native
        from saved_native_reconciliation import reconcile_saved_native, checker_sha256
        import numpy as np
        cell = config.cell_named(args.cell_id)
        calendar = [cell['start_us'], cell['end_exclusive_us']]
        with cs_admission.admit_case(loaded, cell_id=args.cell_id, go_raw=blobs['go'],
            expected_go_sha256=args.go_sha, review_raw=blobs['review'], expected_review_sha256=args.review_sha,
            prepared_review_raw=blobs['prepared-review'], expected_prepared_review_sha256=args.prepared_review_sha,
            native_review_raw=blobs['native-review'], expected_native_review_sha256=args.native_review_sha) as (sim, guard, scope):
            construction = time.monotonic() - began
            while sim.cursor < sim.end and sim.stop is None:
                sim.advance_day()
                print(json.dumps(dict(event='NATIVE_DAY_COMPLETE', cell_id=args.cell_id,
                    completed_minutes=sim.rows_written, stop_us=sim.stop, UTC=r.utc())), flush=True)
            result = native.case_result(sim, guard); minute = result.pop('minute')
            values, columns = minute.to_numpy(), minute.columns
            result['targets'] = result['targets'].to_dicts()
            audit = native.V2.OWNED.export_tree(sim.account.snapshot())
            result = native.V2.OWNED.export_tree(result)
            legacy = result['primary_financial_reconciliation']
            proof = reconcile_saved_native(audit, result, expected_continuation_version=native.VERSION)
            classification = r.classify_terminal(audit, result, calendar=calendar,
                                                 completed_minutes=sim.rows_written, stop_us=sim.stop)
            risk = held_risk(values, columns, loaded, cell['tier'], guard.receipts)
            np.savez_compressed(directory / 'MINUTE.npz', values=values, columns=np.asarray(columns))
            with (directory / 'MINUTE.npz').open('rb') as stream:
                os.fsync(stream.fileno())
            quality = guard.causal_mark_quality_guard
            evidence = {'ACCOUNT_FINANCIAL_AUDIT.json': audit, 'NATIVE_RESULT.json': result,
                'LEGACY_PRIMARY_FINANCIAL_RECONCILIATION.json': legacy,
                'PRIMARY_FINANCIAL_RECONCILIATION.json': proof, 'NATIVE40_RECONSTRUCTION_PROOF.json': proof,
                'ACTUAL_HELD_RISK_REPORT.json': risk,
                'GUARD_RECEIPTS.json': native.V2.OWNED.export_tree(guard.receipts),
                'CAUSAL_MARK_QUALITY.json': dict(identity=quality.identity, policy_SHA256=quality.policy_sha256,
                    receipts=native.V2.OWNED.export_tree(quality.receipts), original_interpolated_marks_execution_admitted=False,
                    actual_CS_event_and_position_impacts='REQUIRE_SEPARATE_SAVED_AUDIT_NOT_INHERITED_FROM_D')}
            for name, value in evidence.items(): r.save(directory / name, value)
            for name, key in (('ADMISSION_GO.json', 'go'), ('ADMISSION_REVIEW.json', 'review'),
                              ('PREPARED_TARGET_REVIEW.json', 'prepared-review'), ('NATIVE_GENERATED_REVIEW.json', 'native-review')):
                r.write_bytes(directory / name, blobs[key])
            scope.validate_current()
            receipt = dict(schema='FINITE_CSMOM21_FIRST6_ORIGINAL_D_CASE_V2', cell_id=args.cell_id,
                year=cell['year'], strategy=config.STRATEGY, tier=cell['tier'], config=scope.config, calendar=calendar,
                cost='BASE27', policy_variant=native.POLICY_VARIANT, status=classification, adaptive_DEV_only=True,
                root_GO_SHA256=args.go_sha, independent_review_SHA256=args.review_sha,
                prepared_source_target_review_SHA256=args.prepared_review_sha, native_generated_review_SHA256=args.native_review_sha,
                preparation_SHA256=r.sha(prep_raw), scope_manifest_SHA256=SCOPE_SHA,
                source_identity=prep['years'][str(cell['year'])]['source_identity'],
                source_code_manifest_SHA256=scope.metadata['source_code_manifest_SHA256'],
                financial_code_manifest_SHA256=scope.metadata['financial_code_manifest_SHA256'],
                input_binding_SHA256=prep['cells'][args.cell_id]['input_binding_SHA256'], checker_SHA256=checker_sha256(),
                reconstruction_proof_SHA256=r.sha((directory / 'NATIVE40_RECONSTRUCTION_PROOF.json').read_bytes()),
                completed_minutes=sim.rows_written, required_minutes=cell['calendar_days'] * 1440, account_stop_us=sim.stop,
                started_UTC=started, ended_UTC=r.utc(), construction_seconds=construction,
                total_wall_seconds=time.monotonic()-began, max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                CPU_seconds=time.process_time(), PID=os.getpid(), requested_CPU=args.cpu,
                controller_PID=os.getppid(), process_start_ticks=r.process_observation(os.getpid())['process_start_ticks'],
                controller_lease_inode=os.fstat(int(os.environ['MATRIX_CONTROLLER_LEASE_FD'])).st_ino,
                actual_CPU_affinity=sorted(os.sched_getaffinity(0)),
                all_TID_affinities=[sorted(os.sched_getaffinity(int(t))) for t in os.listdir('/proc/self/task')],
                thread_environment={key: os.environ[key] for key in THREAD_ENV}, limits=r.LIMITS,
                no_halt_reset=True, snapshot_restart_certified=False, automatic_retry=False,
                native_exchange_or_funding_publication_certified=False, locked_source_reads=0, publication_actions=0)
            r.save(directory / 'CASE_RECEIPT.json', receipt)
        if cs_admission._LIVE:
            raise ValueError('CS_FINANCIAL_SCOPES_NOT_REVOKED')
        if r.own_bytes(directory) > r.LIMITS['per_case_output_bytes']:
            raise RuntimeError('OUTPUT_LIMIT')
        r.save(directory / 'TERMINAL_CHECKPOINT.json', dict(schema='IMMUTABLE_MATRIX_TERMINAL_CHECKPOINT_V1',
            cell_id=args.cell_id, files={name: r.sha((directory / name).read_bytes()) for name in TERMINAL_FILES},
            checker_SHA256=checker_sha256(), reconstruction_proof_SHA256=receipt['reconstruction_proof_SHA256'],
            all_evidence_fsynced=True, restart_financial_snapshot_permission=False, fresh_scope_revoked=True))
    except BaseException as error:
        if 'sim' in locals():
            try: r.save(directory / 'FAILED_ACCOUNT_FINANCIAL_AUDIT.json', native.V2.OWNED.export_tree(sim.account.snapshot()))
            except BaseException: pass
        r.save(directory / 'FAILURE.json', dict(kind='EXECUTION_RESOURCE_DATA_OR_VALIDATION_INTERRUPTION',
            error=repr(error), traceback=traceback.format_exc(), UTC=r.utc(), automatic_retry=False))
        raise
    finally:
        if loaded is not None:
            import cs_loader
            cs_loader.revoke(loaded)


def command(args, *, cell_id, directory, cpu):
    result = [sys.executable, '-B', str(HERE / 'run_cs.py'), '--case', '--cell-id', cell_id,
              '--cpu', str(cpu), '--case-output', str(directory.resolve()),
              '--preparation', str(ordinary(args.preparation)), '--preparation-sha', args.preparation_sha]
    for name in WIRE_NAMES:
        result += ['--' + name, str(ordinary(getattr(args, name.replace('-', '_')))),
                   '--' + name + '-sha', getattr(args, name.replace('-', '_') + '_sha')]
    return result


def controller(args):
    # Validate all new authority and immutable prepared bytes before leases,
    # permanent claims, output creation, or spawning any worker.
    prep_raw, prep, blobs = wires(args)
    import cs_common as c
    import cs_entry as e
    import cs_finance_gate as gate
    from types import SimpleNamespace
    go = c.exact_object(blobs['go']); cpus = go['worker_CPUs']
    r.choose_worker_count(go['requested_worker_count'], cpus, r.host_observation())
    output = ordinary(args.output)
    if (output.parent != HERE / 'financial_attempts' or output.exists()
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', output.name)):
        raise ValueError('EXCLUSIVE_NEW_CS_FINANCIAL_ATTEMPT_REQUIRED_NO_RESUME')
    ordinary(supersession.registry_root() / SCOPE_SHA)
    supersession.validate_evidence()
    for name, pin in prep['artifacts'].items():
        c.exact(ordinary(args.preparation) / c.relative(name), pin['SHA256'], pin['bytes'])
    output.parent.mkdir(exist_ok=True)
    output.mkdir(exist_ok=False)
    r.write_bytes(output / ('ADMISSION_' + args.go_sha + '.json'), blobs['go'])
    jobs = [(cell, lambda directory, cpu, cell=cell: command(args, cell_id=cell, directory=directory, cpu=cpu))
            for cell in e.tranche_cells(e.FIRST6)]
    def before_launch(cell, directory, cpu):
        wires(args)  # Current exact source, native, prepared, reviews and GO.
        r.choose_worker_count(go['requested_worker_count'], cpus, r.host_observation())
        clone = SimpleNamespace(**vars(args)); clone.cell_id = cell; clone.case_output = str(directory); clone.cpu = cpu
        metadata = expected_claim(clone, prep_raw, prep)
        for key in ('schema', 'manifest_SHA256', 'cell_id', 'status', 'automatic_clear_or_retry', 'financial_snapshot_resume'):
            metadata.pop(key)
        metadata['controller_output'] = str(output)
        supersession.reserve(cell_id=cell, metadata=metadata, go=go)
    try:
        from cs_saved import validate_saved_terminal
        with r.controller_lease(supersession.registry_root()):
            report = r.run_pool(jobs, output, requested_workers=go['requested_worker_count'], cpus=cpus,
                validator=lambda directory, cell: validate_saved_terminal(directory, args=args, cell_id=cell),
                before_launch=before_launch)
        report.update(root_GO_SHA256=args.go_sha, tranche=e.FIRST6, scope_manifest_SHA256=SCOPE_SHA,
                      source_code_manifest_SHA256=gate.SOURCE_CODE_SHA256, publication_actions=0)
        r.save(output / ('CONTROLLER_RECEIPT_' + args.go_sha + '.json'), report)
    except BaseException as error:
        r.save(output / ('CONTROLLER_PAUSE_' + args.go_sha + '.json'), dict(status='EXECUTION_RESOURCE_DATA_OR_VALIDATION_PAUSE',
            error=repr(error), UTC=r.utc(), automatic_retry=False, economic_halt_relabelled=False))
        raise


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--bootstrap':
        if len(sys.argv) < 6 or sys.argv[4] != '--':
            raise SystemExit('EXACT_STDLIB_BOOTSTRAP_ARGUMENTS_REQUIRED')
        cpu = int(sys.argv[2]); directory = ordinary(sys.argv[3]); child = sys.argv[5:]
        r.apply_limits(cpu)
        r.save(directory / 'BOOTSTRAP_READY.json', dict(schema='STDLIB_PRE_NUMERICAL_IMPORT_RESOURCE_BOOTSTRAP_V1',
            PID=os.getpid(), requested_CPU=cpu, actual_affinity=sorted(os.sched_getaffinity(0)),
            thread_environment={key: os.environ[key] for key in THREAD_ENV},
            limits={name: list(resource.getrlimit(which)) for name, which in
                    (('AS', resource.RLIMIT_AS), ('CPU', resource.RLIMIT_CPU), ('RSS', resource.RLIMIT_RSS))}))
        os.execvpe(child[0], child, r.environment())
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', action='store_true')
    for name in WIRE_NAMES:
        parser.add_argument('--' + name, required=True); parser.add_argument('--' + name + '-sha', required=True)
    for name in ('preparation', 'preparation-sha'):
        parser.add_argument('--' + name, required=True)
    for name in ('output', 'cell-id', 'case-output'):
        parser.add_argument('--' + name)
    parser.add_argument('--cpu', type=int)
    args = parser.parse_args()
    case(args) if args.case else controller(args)


if __name__ == '__main__':
    main()
