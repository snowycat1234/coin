"""Portable source-free code/metadata and generated-test restoration only."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
RUNNER = 'd0148be6c9e3ecd24742cd005fff93b512f11a0f59346fddd5113f04c269e297'
EXPECTED_LAYOUT = {
    'paired_module': '../paired-headroom-discriminator-20261014',
    'input_module': 'dependencies/input_module',
    'resource_guard': 'dependencies/resource/run_guard_cases.py',
    'resource_release': 'dependencies/resource/GUARD_PACK_RELEASE.json',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != name:
        raise ValueError('Unsafe manifest member')
    return path


def verify(expected):
    if not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError('Exact public manifest SHA-256 required')
    if digest(HERE / 'PUBLIC_PAYLOAD_MANIFEST.json') != expected:
        raise ValueError('Public manifest identity mismatch')
    manifest = json.loads((HERE / 'PUBLIC_PAYLOAD_MANIFEST.json').read_text())
    for name, row in manifest['files'].items():
        path = HERE / relative(name)
        if path.is_symlink() or path.stat().st_size != row['bytes'] or digest(path) != row['SHA256']:
            raise ValueError('Public member identity mismatch: ' + name)
    if digest(HERE / 'RUNNER_MANIFEST.json') != RUNNER:
        raise ValueError('Exact reviewed runner freeze required')
    runner = json.loads((HERE / 'RUNNER_MANIFEST.json').read_text())
    for name, expected_source in runner['files_SHA256'].items():
        if digest(HERE / relative(name)) != expected_source:
            raise ValueError('Frozen runner source changed')
    layout = json.loads((HERE / 'CODE_ONLY_LAYOUT.json').read_text())
    if {k: v for k, v in layout.items() if k != 'scope'} != EXPECTED_LAYOUT:
        raise ValueError('Fixed code-only layout required; historical roots forbidden')
    roots = {k: str((HERE / v).resolve()) for k, v in EXPECTED_LAYOUT.items()}
    pins = json.loads((HERE / 'DEPENDENCY_PINS.json').read_text())
    paired = Path(roots['paired_module'])
    for name, expected_source in pins['paired_publication']['files_SHA256'].items():
        if digest(paired / relative(name)) != expected_source:
            raise ValueError('Inherited exact paired module changed')
    for name, row in pins['input_publication']['files'].items():
        path = Path(roots['input_module']) / relative(name)
        if path.stat().st_size != row['bytes'] or digest(path) != row['SHA256']:
            raise ValueError('Exact original input code/metadata changed')
    for key, pin_key in [('resource_guard', 'original_resource_guard'),
                         ('resource_release', 'original_resource_release')]:
        row = pins[pin_key]
        path = Path(roots[key])
        if path.stat().st_size != row['bytes'] or digest(path) != row['SHA256']:
            raise ValueError('Exact original resource code/metadata changed')
    review = json.loads((HERE / 'independent_review/PUBLIC_REVIEW_PAYLOAD_MANIFEST.json').read_text())
    for name, expected_review in review['files_SHA256'].items():
        if digest(HERE / 'independent_review' / relative(name)) != expected_review:
            raise ValueError('Independent reviewer payload changed')
    return {'status': 'PASS_PUBLIC_RUNNER_AND_IMMUTABLE_CODE_METADATA_IDENTITIES',
            'public_manifest_SHA256': expected, 'runner_manifest_SHA256': RUNNER,
            'public_members_verified': len(manifest['files']),
            'inherited_paired_files_verified': len(pins['paired_publication']['files_SHA256']),
            'additive_original_code_metadata_files_verified': 5,
            'historical_array_reads': 0, 'wallets': 0}, roots


def limits():
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (4_000_000_000, 4_000_000_000))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))


def rss(pid):
    try:
        for line in Path('/proc/' + str(pid) + '/status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                return int(line.split()[1]) * 1024
    except (FileNotFoundError, ProcessLookupError):
        pass
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-manifest-sha256', required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12) or not sys.platform.startswith('linux'):
        parser.error('Require Python3.12/Linux CPU-affinity and process resource limits')
    identity, roots = verify(args.expected_manifest_sha256)
    output = HERE / 'cold_synthetic_receipts'
    output.mkdir(exist_ok=False)
    roots_path = output / 'CODE_ONLY_ROOTS.json'
    roots_path.write_text(json.dumps(roots, indent=2) + '\n')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1',
               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    env.pop('PYTHONOPTIMIZE', None)
    env.pop('PYTHONPATH', None)
    env.pop('PAIRED_TEST_CODE_ROOTS', None)
    env.pop('REVIEW_RUNNER_ROOT', None)
    commands = [('runtime_identity', ['-c', "import numpy\nif numpy.__version__!='2.3.5':raise SystemExit('NumPy identity mismatch')\nprint('PASS Python3.12 NumPy2.3.5')"]),
                ('canonical_27_generated_checks', ['run_synthetic_checks.py', '--roots', str(roots_path),
                  '--runner-manifest-sha', RUNNER, '--output', str(output / 'canonical')]),
                ('independent_19_active_checks', ['independent_review/run_independent_bounded.py',
                  str(HERE), str(output / 'independent'), str(roots_path)])]
    records = []
    for stage, command in commands:
        began, peak, stop = time.monotonic(), 0, None
        with (output / (stage + '.txt')).open('x') as log:
            child = subprocess.Popen([sys.executable, '-B', *command], cwd=HERE, env=env,
                                     preexec_fn=limits, stdout=log, stderr=subprocess.STDOUT)
            while child.poll() is None:
                peak = max(peak, rss(child.pid))
                if peak > 2_000_000_000:
                    stop = 'RSS_LIMIT'
                elif time.monotonic() - began > 120:
                    stop = 'WALL_LIMIT'
                if stop:
                    child.kill()
                    break
                time.sleep(.02)
            code = child.wait()
        records.append({'stage': stage, 'exit_code': code, 'stop_reason': stop,
                        'elapsed_seconds': time.monotonic() - began,
                        'sampled_parent_peak_RSS_bytes': peak, 'AS_limit_bytes': 4_000_000_000,
                        'RSS_stop_bytes': 2_000_000_000, 'CPU_seconds': 60,
                        'wall_seconds': 120, 'CPUs': 1, 'math_threads': 1})
        if code or stop:
            break
    after, _ = verify(args.expected_manifest_sha256)
    unchanged = after == identity
    passed = len(records) == 3 and unchanged and all(r['exit_code'] == 0 and r['stop_reason'] is None for r in records)
    if passed:
        canonical = json.loads((output / 'canonical/RESOURCE_RECEIPT.json').read_text())
        independent = json.loads((output / 'independent/RESOURCE_RECEIPT.json').read_text())
        passed = canonical['status'] == 'PASS_BOUNDED_CODE_AND_SYNTHETIC' and independent['status'] == 'PASS_GENERATED_REVIEW_CHECKS'
    receipt = {'status': 'PASS_BOUNDED_SOURCE_FREE_PUBLIC_COLD' if passed else 'FAIL_PUBLIC_COLD',
               'identity_gate': identity, 'records': records, 'source_bytes_unchanged': unchanged,
               'distinct_runner_tests': 27, 'active_independent_checks': 19,
               'retired_freeze_checks_intentionally_skipped': 5,
               'independent_nested_canonical_27_replay': True,
               'historical_array_reads': 0, 'wallets': 0, 'fits': 0,
               'new_market_downloads': 0, 'cached_source_GO': False, 'wallet_GO': False}
    (output / 'PUBLIC_SAFE_COLD_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
