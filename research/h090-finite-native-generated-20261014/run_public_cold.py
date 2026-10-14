"""Manifest-first bounded transport of an unchanged generated finite candidate."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import resource
import signal
import subprocess
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
FREEZE = '6f915e88d0f29a1307706d25a206edac5751700687196b88c82643c45e9b2c96'
CONTROL_FREEZE = 'cf886908cb2a55537c7ddc1d7e5a73a5a09ed48eff110634cbc59242240ea40f'
VERSIONS = {'python': '3.12.14', 'numpy': '2.3.5', 'polars': '1.44.2', 'pyarrow': '23.0.1'}
AS_BYTES = 4 * 1024**3
RSS_BYTES = 2 * 1024**3
CPU_SECONDS = 60
WALL_SECONDS = 120
OUTPUT_BYTES = 8 * 1024**2
ARCHIVE_BYTES = 16 * 1024**2
FINITE_TEST_MODULES = ['test_finite_candidate', 'test_finite_atomic', 'test_finite_review_boundaries']

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()

def safe(name):
    require(isinstance(name, str) and bool(name), 'SAFE_RELATIVE_MEMBER_REQUIRED')
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and '.' not in path.parts
            and str(path) == name, 'UNSAFE_MEMBER_PATH')
    return Path(name)

def checked(name, row):
    path = HERE / safe(name)
    require(not any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(HERE)),
            'SYMLINKED_PUBLIC_MEMBER')
    require(path.is_file() and path.resolve().is_relative_to(HERE), 'PUBLIC_MEMBER_ESCAPE')
    require(path.stat().st_size == row['bytes'], 'PUBLIC_MEMBER_SIZE_MISMATCH:' + name)
    raw = path.read_bytes()
    require(sha(raw) == row['SHA256'], 'PUBLIC_MEMBER_SHA256_MISMATCH:' + name)
    require(git(raw) == row['GitBlobSHA1'], 'PUBLIC_MEMBER_GIT_BLOB_MISMATCH:' + name)
    return raw

def archive_bodies(manifest):
    catalog = json.loads(checked('retained_evidence/BODY_CATALOG.json', manifest['files']['retained_evidence/BODY_CATALOG.json']))
    archive = catalog['archive']
    raw = checked(archive['path'], archive)
    require(catalog['unique_body_count'] == 12, 'EXACT_RETAINED_BODY_COUNT_REQUIRED')
    expected = {}
    for row in catalog['entries']:
        safe(row['original_relative_path'])
        member = row['archive_member']
        require(member == 'sha256/' + row['SHA256'], 'CONTENT_ADDRESSED_ARCHIVE_MEMBER_REQUIRED')
        if member in expected:
            require(expected[member] == {k: row[k] for k in ('bytes', 'SHA256', 'GitBlobSHA1')}, 'CONFLICTING_BODY_ALIAS')
        expected[member] = {k: row[k] for k in ('bytes', 'SHA256', 'GitBlobSHA1')}
    require(len(expected) == catalog['unique_body_count'], 'ARCHIVE_ALIAS_COUNT_MISMATCH')
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:
        expanded = compressed.read(ARCHIVE_BYTES + 1)
    require(len(expanded) <= ARCHIVE_BYTES and len(expanded) == catalog['uncompressed_tar_bytes'], 'BOUNDED_EXACT_ARCHIVE_REQUIRED')
    bodies = {}
    with tarfile.open(fileobj=io.BytesIO(expanded), mode='r:') as source:
        for item in source.getmembers():
            require(item.name in expected and item.isfile() and item.name not in bodies,
                    'UNEXPECTED_OR_DUPLICATE_ARCHIVE_MEMBER')
            row = expected[item.name]
            require(item.size == row['bytes'] and item.size <= ARCHIVE_BYTES, 'ARCHIVE_MEMBER_SIZE_MISMATCH')
            body = source.extractfile(item).read(row['bytes'] + 1)
            require(len(body) == row['bytes'] and sha(body) == row['SHA256'] and git(body) == row['GitBlobSHA1'],
                    'EXACT_ARCHIVED_BODY_MISMATCH')
            bodies[item.name] = body
    require(set(bodies) == set(expected), 'ARCHIVED_BODY_SET_MISMATCH')
    return catalog, bodies

def verify(expected):
    require(re.fullmatch('[0-9a-f]{64}', expected) is not None, 'EXTERNAL_PUBLIC_MANIFEST_SHA256_REQUIRED')
    path = HERE / 'PUBLIC_PAYLOAD_MANIFEST.json'
    require(not path.is_symlink() and path.is_file(), 'REGULAR_PUBLIC_MANIFEST_REQUIRED')
    raw = path.read_bytes()
    require(sha(raw) == expected, 'EXTERNAL_PUBLIC_MANIFEST_MISMATCH')
    manifest = json.loads(raw)
    require(manifest['schema'] == 'H090_FINITE_EXACT_PUBLIC_PAYLOAD_V1', 'PUBLIC_MANIFEST_SCHEMA')
    actual = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() or p.is_symlink()}
    require(actual == set(manifest['files']) | {'PUBLIC_PAYLOAD_MANIFEST.json'}, 'EXACT_PUBLIC_FILE_SET_REQUIRED')
    for name, row in manifest['files'].items():
        checked(name, row)
    frozen_raw = checked('SOURCE_FREEZE.json', manifest['files']['SOURCE_FREEZE.json'])
    require(sha(frozen_raw) == FREEZE, 'ACCEPTED_FINITE_FREEZE_REQUIRED')
    freeze = json.loads(frozen_raw)
    require(freeze['immutable_control_freeze_SHA256'] == CONTROL_FREEZE, 'IMMUTABLE_CONTROL_FREEZE_REQUIRED')
    require(sha(checked('CONTROL_SOURCE_FREEZE.json', manifest['files']['CONTROL_SOURCE_FREEZE.json'])) == CONTROL_FREEZE,
            'EXACT_CONTROL_ALIAS_REQUIRED')
    pins = json.loads(checked('DEPENDENCY_PINS.json', manifest['files']['DEPENDENCY_PINS.json']))
    closure = dict(freeze['files_SHA256'])
    for name, digest in pins['files_SHA256'].items():
        require(name not in closure or closure[name] == digest, 'CONFLICTING_FROZEN_CLOSURE_PIN')
        closure[name] = digest
    require(len(freeze['files_SHA256']) == 29 and len(pins['files_SHA256']) == 62 and len(closure) == 91,
            'EXACT_FINITE_AND_INHERITED_CLOSURE_COUNTS_REQUIRED')
    for name, digest in closure.items():
        require(name in manifest['files'] and sha(checked(name, manifest['files'][name])) == digest,
                'FROZEN_SOURCE_CLOSURE_MISMATCH:' + name)
    require(len(manifest['reused_public_CONTROL_closure']) == 79, 'ALL_79_REUSED_CONTROL_AND_DEPENDENCY_MEMBERS_REQUIRED')
    for name, row in manifest['reused_public_CONTROL_closure'].items():
        require(name in closure and manifest['files'][name] == row, 'REUSED_PUBLIC_MEMBER_IDENTITY_MISMATCH')
    catalog, bodies = archive_bodies(manifest)
    identity = {'status': 'PASS_EXACT_PUBLIC_FINITE_SOURCE_AND_CLOSURE_IDENTITIES',
                'public_manifest_SHA256': expected, 'source_freeze_SHA256': FREEZE,
                'public_member_count': len(manifest['files']), 'finite_source_freeze_members': 29,
                'dependency_members': 62, 'exact_frozen_closure_members': 91,
                'reused_public_CONTROL_and_dependency_members': 79,
                'checksum_only_already_public_target_NPZ_files': 2, 'checksum_only_target_bytes': 50586,
                'NPZ_array_parses': 0, 'retained_exact_unique_bodies': len(bodies)}
    return identity, catalog, bodies

def explicit_sites(names):
    require(bool(names), 'EXPLICIT_RUNTIME_SITE_REQUIRED')
    sites = []
    for name in names:
        path = Path(name).resolve(strict=True)
        require(path.is_dir() and not path.is_relative_to(HERE), 'EXTERNAL_RUNTIME_SITE_DIRECTORY_REQUIRED')
        require(str(path) not in sites, 'DUPLICATE_RUNTIME_SITE')
        sites.append(str(path))
    return sites

def limits():
    resource.setrlimit(resource.RLIMIT_AS, (AS_BYTES, AS_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_BYTES, OUTPUT_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    cpus = os.sched_getaffinity(0)
    require(bool(cpus), 'AVAILABLE_CPU_REQUIRED')
    os.sched_setaffinity(0, {min(cpus)})

def group_rss(group):
    total = 0
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            if os.getpgid(int(path.name)) != group:
                continue
            for line in (path / 'status').read_text().splitlines():
                if line.startswith('VmRSS:'):
                    total += int(line.split()[1]) * 1024
                    break
        except (OSError, ValueError, ProcessLookupError):
            pass
    return total

def output_size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())

def kill_group(group):
    try:
        os.killpg(group, signal.SIGKILL)
    except ProcessLookupError:
        pass

def bounded(stage, command, env, destination):
    began = time.monotonic()
    peak = 0
    reason = None
    log = destination / (stage + '.txt')
    with log.open('xb') as output:
        child = subprocess.Popen(command, cwd=HERE, env=env, preexec_fn=limits, start_new_session=True,
                                 stdout=output, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                peak = max(peak, group_rss(child.pid))
                if peak > RSS_BYTES:
                    reason = 'PROCESS_GROUP_RSS_LIMIT'
                elif time.monotonic() - began > WALL_SECONDS:
                    reason = 'PROCESS_GROUP_WALL_LIMIT'
                elif output_size(destination) > OUTPUT_BYTES:
                    reason = 'TOTAL_OUTPUT_LIMIT'
                if reason:
                    kill_group(child.pid)
                    break
                time.sleep(.025)
            code = child.wait()
        finally:
            # Kill any descendants that outlive their main process.
            kill_group(child.pid)
    size = output_size(destination)
    if size > OUTPUT_BYTES and reason is None:
        reason = 'TOTAL_OUTPUT_LIMIT'
    return {'stage': stage, 'returncode': code, 'stop_reason': reason,
            'wall_seconds': time.monotonic() - began, 'sampled_group_peak_RSS_bytes': peak,
            'output_SHA256': sha(log.read_bytes()), 'total_output_bytes_after_stage': size}

def runtime_identity():
    import numpy, polars, pyarrow
    actual = {'python': platform.python_version(), 'numpy': numpy.__version__,
              'polars': polars.__version__, 'pyarrow': pyarrow.__version__}
    require(actual == VERSIONS and sys.flags.optimize == 0, 'EXACT_UNOPTIMIZED_RUNTIME_REQUIRED')
    return actual

def child_stage(stage, expected, sites, destination):
    # This path runs under -I -S. No inherited user sites, startup hooks, PYTHONPATH,
    # optimization flags or working-directory import path are consumed.
    identity, _, _ = verify(expected)
    require(sys.flags.optimize == 0 and sys.flags.isolated == 1 and sys.flags.no_site == 1,
            'ISOLATED_UNOPTIMIZED_NO_SITE_CHILD_REQUIRED')
    sys.dont_write_bytecode = True
    sys.path.extend(sites)
    versions = runtime_identity()
    if stage == 'exact_runtime_identity':
        print(json.dumps({'versions': versions, 'optimization_level': sys.flags.optimize,
                          'isolated': sys.flags.isolated, 'no_site': sys.flags.no_site}, sort_keys=True))
        return 0
    sys.path.insert(0, str(HERE))
    if stage == 'finite_35_tests':
        import types, unittest
        freeze = json.loads((HERE / 'SOURCE_FREEZE.json').read_bytes())
        path = HERE / 'verified_source.py'
        source = path.read_bytes()
        require(sha(source) == freeze['files_SHA256']['verified_source.py'], 'UNCHANGED_VERIFIED_BOOTSTRAP_REQUIRED')
        require('verified_source' not in sys.modules, 'COLD_VERIFIED_BOOTSTRAP_REQUIRED')
        module = types.ModuleType('verified_source')
        module.__file__ = str(path)
        sys.modules['verified_source'] = module
        exec(compile(source, str(path), 'exec', optimize=0), module.__dict__)
        runtime = module.install(FREEZE)
        suite = unittest.defaultTestLoader.loadTestsFromNames(FINITE_TEST_MODULES)
        require(suite.countTestCases() == 35, 'EXACT_35_FINITE_TESTS_REQUIRED')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        audit = runtime.audit()
        require(result.testsRun == 35, 'EXACT_35_FINITE_TESTS_EXECUTED_REQUIRED')
        print(json.dumps({'source_audit': audit, 'tests_run': result.testsRun,
                          'tests_passed': result.wasSuccessful(), 'unchanged_CONTROL_tests_rerun': 0}, sort_keys=True))
        return 0 if result.wasSuccessful() else 1
    require(stage in ('demo', 'witnesses'), 'KNOWN_GENERATED_STAGE_REQUIRED')
    # Execute the exact accepted entry bytes. It installs the unchanged bootstrap.
    entry = HERE / 'run_finite_verified.py'
    sys.argv = [str(entry), '--freeze-sha', FREEZE, stage, '--receipt-dir', destination]
    namespace = {'__name__': '__main__', '__file__': str(entry), '__package__': None}
    exec(compile(entry.read_bytes(), str(entry), 'exec', optimize=0), namespace)
    return 0

def restore_evidence(destination, catalog, bodies):
    out = Path(destination).resolve()
    require(not out.exists() and not out.is_relative_to(HERE), 'NEW_EXTERNAL_EVIDENCE_RESTORE_DIRECTORY_REQUIRED')
    out.mkdir(parents=True, exist_ok=False)
    for row in catalog['entries']:
        path = out / safe(row['original_relative_path'])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bodies[row['archive_member']])
    return {'directory_supplied_explicitly': True, 'exact_restored_alias_count': len(catalog['entries']),
            'unique_native_and_development_bodies': len(bodies), 'native_wallet_restore_implemented': False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--receipt-dir')
    parser.add_argument('--runtime-site', action='append', default=[])
    parser.add_argument('--identity-only', action='store_true')
    parser.add_argument('--restore-evidence-dir')
    args = parser.parse_args()
    identity, catalog, bodies = verify(args.expected_manifest_sha256)
    if args.restore_evidence_dir:
        identity['evidence_restore'] = restore_evidence(args.restore_evidence_dir, catalog, bodies)
    if args.identity_only:
        print(json.dumps(identity, indent=2, sort_keys=True))
        return 0
    require(sys.platform.startswith('linux') and platform.python_version() == VERSIONS['python'],
            'EXACT_PYTHON_3_12_14_LINUX_RUNTIME_REQUIRED')
    require(args.receipt_dir is not None, 'NEW_RECEIPT_DIRECTORY_REQUIRED')
    sites = explicit_sites(args.runtime_site)
    destination = Path(args.receipt_dir).resolve()
    require(not destination.exists() and not destination.is_relative_to(HERE), 'NEW_EXTERNAL_RECEIPT_DIRECTORY_REQUIRED')
    destination.mkdir(parents=True, exist_ok=False)
    env = {k: v for k, v in os.environ.items() if not k.startswith('PYTHON')
           and k not in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'VIRTUAL_ENV', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV')}
    env.update(PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
               MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', POLARS_MAX_THREADS='1', RAYON_NUM_THREADS='1',
               VECLIB_MAXIMUM_THREADS='1', BLIS_NUM_THREADS='1', PATH='/usr/bin:/bin')
    entry_body = (HERE / 'run_public_cold.py').read_bytes()
    # The outer external manifest verifies this exact transport body before spawn;
    # each fresh child then verifies the complete manifest before project imports.
    loader = ('namespace={"__name__":"finite_public_transport","__file__":' + repr(str(HERE / 'run_public_cold.py'))
              + '}; exec(compile(' + repr(entry_body) + ',namespace["__file__"],"exec",optimize=0),namespace); '
              + 'raise SystemExit(namespace["child_stage"](*' )
    records = []
    for stage, output in [('exact_runtime_identity', ''), ('finite_35_tests', ''),
                          ('demo', str(destination / 'demo')), ('witnesses', str(destination / 'owner_boundaries'))]:
        code = loader + repr((stage, args.expected_manifest_sha256, sites, output)) + '))'
        record = bounded(stage, [sys.executable, '-I', '-S', '-B', '-c', code], env, destination)
        records.append(record)
        if record['returncode'] != 0 or record['stop_reason'] is not None:
            break
    passed = len(records) == 4 and all(r['returncode'] == 0 and r['stop_reason'] is None for r in records)
    parity = []
    expected_paths = ['bounded_finite_receipts_003/demo/DEMO.json',
                      'bounded_finite_receipts_003/owner_boundaries/OWNER_BOUNDARIES.json']
    if passed:
        for name, produced in zip(expected_paths, [destination / 'demo/DEMO.json', destination / 'owner_boundaries/OWNER_BOUNDARIES.json']):
            saved = next(r for r in catalog['entries'] if r['original_relative_path'] == name)
            raw = produced.read_bytes()
            exact = raw == bodies[saved['archive_member']]
            parity.append({'saved_original_path': name, 'bytes': len(raw), 'SHA256': sha(raw),
                           'byte_exact_saved_native_body': exact})
            passed = passed and exact
    after, _, _ = verify(args.expected_manifest_sha256)
    unchanged = after == {k: v for k, v in identity.items() if k != 'evidence_restore'}
    passed = passed and unchanged
    receipt = {'schema': 'H090_FINITE_PUBLIC_BOUNDED_TRANSPORT_RECEIPT_V1',
               'status': 'PASS_35_FINITE_TESTS_EXACT_GENERATED_NATIVE_BODY_PARITY' if passed else 'FAIL_PUBLIC_FINITE_TRANSPORT',
               'identity_gate': after, 'runtime': VERSIONS, 'explicit_runtime_site_count': len(sites),
               'inherited_python_and_optimization_settings_neutralized': True,
               'child_flags': ['-I', '-S', '-B'], 'child_optimization_level': 0,
               'resources': {'CPU_affinity_count': 1, 'math_threads': 1, 'address_space_bytes': AS_BYTES,
                             'process_group_RSS_stop_bytes': RSS_BYTES, 'CPU_seconds_per_child': CPU_SECONDS,
                             'wall_seconds_per_child': WALL_SECONDS, 'total_output_limit_bytes': OUTPUT_BYTES},
               'records': records, 'finite_tests': 35 if passed else None, 'unchanged_CONTROL_tests_rerun': 0,
               'native_body_parity': parity, 'frozen_source_bytes_unchanged': unchanged,
               'scope': 'GENERATED_ONLY_WITH_CHECKSUM_ACCESS_TO_TWO_ALREADY_PUBLIC_DEVELOPMENT_TARGET_ARCHIVES',
               'historical_wallets': 0, 'historical_array_parses': 0, 'downloads': 0, 'live_finance': 0,
               'historical_GO': False, 'restore_GO': False, 'profitability': 'NOT_TESTED_NOT_CLAIMED'}
    (destination / 'PUBLIC_COLD_RECEIPT.json').write_text(json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + '\n')
    print(json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False))
    return 0 if passed else 1

if __name__ == '__main__':
    raise SystemExit(main())
