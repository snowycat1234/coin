"""Finite FIRST6 source/target-only entry. Requires fresh external review/GO."""
import os
import encodings.cp437  # Exact ASCII ZIP member-name decoder, before guard.
import encodings.utf_8_sig  # Exact original CSV payload decoder, before guard.
THREAD_ENV = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'POLARS_MAX_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS')
for key in THREAD_ENV:
    os.environ[key] = '1'

import argparse
import json
from pathlib import Path
import resource
import re
import signal
import time


def main():
    parser = argparse.ArgumentParser()
    for name in ('output', 'source-go', 'source-go-sha', 'source-review', 'source-review-sha'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--cpu', required=True, type=int)
    args = parser.parse_args()
    if args.cpu not in os.sched_getaffinity(0):
        raise ValueError('ACTUALLY_ALLOWED_ASSIGNED_SOURCE_CPU_REQUIRED')
    os.sched_setaffinity(0, {args.cpu})
    resource.setrlimit(resource.RLIMIT_CPU, (900, 900))
    resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('SOURCE_STAGE_WALL_CAP')))
    signal.alarm(1800)
    import cs_common as c
    import cs_entry as entry
    import cs_source as source
    import cs_source_bridge  # Pure graph preloaded before filename loaders close.
    import cs_quality
    import cs_signal
    from cs_source_guard import SourceOnlyGuard
    go = Path(args.source_go).read_bytes(); review = Path(args.source_review).read_bytes()
    authority = entry.validate_source_authority_metadata(go, args.source_go_sha, review, args.source_review_sha)
    cs_signal.originals(); cs_signal.common_grid(); cs_quality.original_quality()
    code = c.exact_object((c.HERE / 'CODE_MANIFEST.json').read_bytes())
    reads = [c.HERE / name for name in code['files']] + [c.ROOT / name for name in code['dependencies']]
    reads += [c.HERE / 'CODE_MANIFEST.json', Path(args.source_go).absolute(), Path(args.source_review).absolute()]
    for year in entry.tranche_years(authority['policy']['tranche']):
        reads += [c.ROOT / name for name in entry.contracts()['years'][str(year)]['read_files']]
    output = Path(args.output).absolute()
    if (output.parent != c.HERE / 'source_attempts'
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', output.name)
            or output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents)):
        raise ValueError('EXCLUSIVE_EXACT_NEW_CS_ATTEMPT_OUTPUT_REQUIRED')
    guard = SourceOnlyGuard(write_roots=(c.HERE / 'source_attempts',), read_paths=reads)
    began, cpu = time.monotonic(), time.process_time()
    try:
        with guard:
            guard.checkpoint('ENTER_FRESH_FIRST6_CS_SOURCE_ONLY_PROCESS')
            preparation = source.prepare_source_only(output, source_go_raw=go,
                expected_source_go_sha256=args.source_go_sha, review_raw=review,
                expected_review_sha256=args.source_review_sha)
            recorded = entry.record_metadata_bindings(preparation, lambda scope: scope.validate_current())
            guard.checkpoint('FIRST6_RECORDING_SCOPES_REVOKED_NO_FINANCE')
            with (output / 'RECORDING_ONLY_METADATA_RECEIPT.json').open('x') as stream:
                json.dump(recorded, stream, indent=2); stream.write('\n')
        elapsed = time.monotonic() - began
        size = sum(path.stat().st_size for path in output.rglob('*') if path.is_file())
        if elapsed > 1800 or time.process_time() - cpu > 900 or size > 1073741824:
            raise ValueError('SOURCE_STAGE_RESOURCE_CAP')
        receipt = guard.receipt('PASS_SOURCE_TARGET_ONLY_NO_FINANCIAL_ADMISSION')
        receipt.update(source_scopes_revoked=not entry._ACTIVE_SOURCE,
            recording_scopes_revoked=not entry._ACTIVE_RECORDING, elapsed_wall_seconds=elapsed,
            elapsed_CPU_seconds=time.process_time() - cpu, output_bytes=size,
            actual_CPU_affinity=sorted(os.sched_getaffinity(0)),
            all_TID_affinities=[sorted(os.sched_getaffinity(int(t))) for t in os.listdir('/proc/self/task')])
        with (output / 'OBSERVED_SOURCE_TARGET_GUARD_RECEIPT.json').open('x') as stream:
            json.dump(receipt, stream, indent=2); stream.write('\n')
        print(json.dumps(dict(status=receipt['status'], forbidden_attempts=receipt['forbidden_attempts'])))
    except BaseException as exc:
        stopped = guard.receipt('STOP_SOURCE_TARGET_ONLY_NO_FINANCIAL_ADMISSION', type(exc).__name__ + ':' + str(exc))
        stopped.update(source_scopes_revoked=not entry._ACTIVE_SOURCE,
            recording_scopes_revoked=not entry._ACTIVE_RECORDING,
            elapsed_wall_seconds=time.monotonic() - began,
            elapsed_CPU_seconds=time.process_time() - cpu)
        try:
            if output.is_symlink() or any(p.is_symlink() for p in output.parents):
                raise ValueError('STOP_RECEIPT_OUTPUT_SYMLINK_FORBIDDEN')
            output.mkdir(parents=True, exist_ok=True)
            with (output / 'STOP_SOURCE_TARGET_PREPARATION.json').open('x') as stream:
                json.dump(stopped, stream, indent=2); stream.write('\n')
        except BaseException as receipt_error:
            # Preserve the original failure; external launch logs still retain
            # the full observed boundary report if receipt persistence fails.
            print(json.dumps(dict(status='STOP_RECEIPT_PERSISTENCE_FAILED',
                receipt_error=type(receipt_error).__name__, observed_stop=stopped)))
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
