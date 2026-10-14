"""Hash-bound, stdlib-only public synthetic cold checks. No history interface."""
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
SOURCE_MANIFEST_SHA256 = 'ddea8797f02722f39c779fc548d0e3471f13907f04d94f9f9c3fe8b4be605bd8'
CANDIDATE = HERE / 'coin_bot_risk_matched_synthetic_20261014'
REVIEW = HERE / 'coin_bot_independent_review_20261014'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(expected):
    if not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError('Expected manifest must be an exact SHA-256')
    manifest_path = HERE / 'PUBLIC_PAYLOAD_MANIFEST.json'
    if digest(manifest_path) != expected:
        raise ValueError('Public manifest identity mismatch')
    manifest = json.loads(manifest_path.read_text())
    for name, row in manifest['files'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or path.as_posix() != name:
            raise ValueError('Unsafe manifest member')
        data = (HERE / path).read_bytes()
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['SHA256']:
            raise ValueError('Public member identity mismatch: ' + name)
    if digest(CANDIDATE / 'FINAL_MANIFEST.json') != SOURCE_MANIFEST_SHA256:
        raise ValueError('Original scientific freeze identity mismatch')
    original = json.loads((CANDIDATE / 'FINAL_MANIFEST.json').read_text())
    mapping = json.loads((CANDIDATE / 'PUBLIC_PROJECTION_MAP.json').read_text())
    projections = {row['original_filename']: row for row in mapping['receipt_projections']}
    for name, expected_source in original['files_SHA256'].items():
        if name.startswith('CHECK_RECEIPT'):
            row = projections[name]
            if row['original_SHA256'] != expected_source or digest(CANDIDATE / row['public_filename']) != row['public_SHA256']:
                raise ValueError('Receipt projection provenance mismatch')
        elif digest(CANDIDATE / name) != expected_source:
            raise ValueError('Original source changed: ' + name)
    review = json.loads((REVIEW / 'REVIEW_MANIFEST.json').read_text())
    for name, expected_review in review['files_SHA256'].items():
        if digest(REVIEW / name) != expected_review:
            raise ValueError('Independent review source changed')
    return {'status': 'PASS_PUBLIC_HASH_AND_SCIENTIFIC_IDENTITY',
            'public_manifest_SHA256': expected,
            'source_manifest_SHA256': SOURCE_MANIFEST_SHA256,
            'public_members_verified': len(manifest['files']),
            'private_raw_receipt_projections': len(projections),
            'external_native_source_bodies_verified': 0}


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-manifest-sha256', required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12) or not sys.platform.startswith('linux'):
        parser.error('Require Python3.12 on Linux with resource limits and CPU affinity')
    identity = verify(args.expected_manifest_sha256)
    output = HERE / 'cold_synthetic_receipts'
    output.mkdir(exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    env.pop('PYTHONOPTIMIZE', None)
    env.pop('PYTHONPATH', None)
    commands = [('designer_40_tests', CANDIDATE, ['-m', 'unittest', '-v', 'test_synthetic']),
                ('independent_41_tests', REVIEW, ['-m', 'unittest', '-v', 'test_adversarial']),
                ('generated_toy', CANDIDATE, ['toy_demo.py'])]
    records = []
    for stage, cwd, command in commands:
        start = time.monotonic()
        with (output / (stage + '.txt')).open('x') as log:
            try:
                process = subprocess.run([sys.executable, '-B', *command], cwd=cwd,
                                         env=env, preexec_fn=limits, stdout=log,
                                         stderr=subprocess.STDOUT, timeout=60)
                code, stop = process.returncode, None
            except subprocess.TimeoutExpired:
                code, stop = None, 'WALL_LIMIT'
        records.append({'stage': stage, 'exit_code': code, 'stop_reason': stop,
                        'elapsed_seconds': time.monotonic() - start,
                        'CPU_limit_seconds': 60, 'wall_limit_seconds': 60,
                        'AS_limit_bytes': 512 * 1024 * 1024,
                        'output_limit_bytes': 10 * 1024 * 1024,
                        'CPU_affinity_count': 1, 'threads': 1})
        if code != 0 or stop:
            break
    unchanged = verify(args.expected_manifest_sha256) == identity
    passed = len(records) == 3 and unchanged and all(r['exit_code'] == 0 for r in records)
    receipt = {'status': 'PASS_BOUNDED_PUBLIC_COLD_SYNTHETIC' if passed else 'FAIL_PUBLIC_COLD',
               'identity_gate': identity, 'source_bytes_unchanged': unchanged,
               'records': records, 'historical_wallets': 0, 'market_reads': 0,
               'downloads': 0, 'native_financial_advances': 0, 'fits': 0,
               'historical_go': False, 'investment_certification': False}
    (output / 'PUBLIC_SAFE_COLD_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
