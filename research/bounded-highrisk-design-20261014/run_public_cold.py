"""Immutable H090 V2 transport identities and bounded generated-only cold checks."""
from __future__ import annotations
import argparse
import gzip
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
DESIGN = HERE / 'coin_bounded_highrisk_design_20261014'
REVIEW = HERE / 'coin_bounded_highrisk_review_20261014'
FREEZE = 'af840b51613335a83d5badd8454e0861863e6fb20dda136d2054457ffeb1cdf5'
AS_LIMIT = 4 * 1024 ** 3
RSS_STOP = 2 * 1024 ** 3


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != name:
        raise ValueError('Unsafe public member locator')
    return path


def verify(expected):
    if not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError('Exact public manifest SHA-256 required')
    manifest_path = HERE / 'PUBLIC_PAYLOAD_MANIFEST.json'
    if digest(manifest_path) != expected:
        raise ValueError('Public manifest identity mismatch')
    manifest = json.loads(manifest_path.read_text())
    for name, row in manifest['files'].items():
        data = (HERE / relative(name)).read_bytes()
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['SHA256']:
            raise ValueError('Public member changed: ' + name)
    if digest(DESIGN / 'SOURCE_FREEZE.json') != FREEZE:
        raise ValueError('Exact reviewed V2 science freeze required')
    freeze = json.loads((DESIGN / 'SOURCE_FREEZE.json').read_text())
    for name, expected_source in freeze['source_files_SHA256'].items():
        if digest(DESIGN / relative(name)) != expected_source:
            raise ValueError('Frozen science changed: ' + name)
    snapshot = json.loads((REVIEW / 'SOURCE_SNAPSHOT.json').read_text())
    for name, expected_source in snapshot['files'].items():
        if digest(DESIGN / relative(name)) != expected_source:
            raise ValueError('Independent source snapshot changed: ' + name)
    pins = json.loads((DESIGN / 'SOURCE_PINS.json').read_text())
    catalog = json.loads((HERE / 'ORIGINAL_CODE_CARRIER.json').read_text())
    observed = {}
    for row in catalog['files']:
        name = row['public_relative_path']
        if row['repository'] != 'snowycat1234/coin' or not re.fullmatch(r'[0-9a-f]{40}', row['commit']):
            raise ValueError('Immutable original-code reference required')
        if name in observed or digest(HERE / relative(name)) != row['SHA256']:
            raise ValueError('Original code carrier identity mismatch')
        observed[name] = row['SHA256']
    if observed != {pin['source_path']: pin['original_sha256'] for pin in pins.values()}:
        raise ValueError('Original code carrier does not exactly cover two source pins')
    projection = json.loads((HERE / 'PUBLIC_PROJECTION_MAP.json').read_text())
    toy = projection['lossless_saved_toy']
    compressed = (HERE / relative(toy['gzip_path'])).read_bytes()
    if len(compressed) != toy['gzip_bytes'] or hashlib.sha256(compressed).hexdigest() != toy['gzip_SHA256']:
        raise ValueError('Lossless toy gzip identity mismatch')
    body = gzip.decompress(compressed)
    if len(body) != toy['native_body_bytes'] or hashlib.sha256(body).hexdigest() != toy['native_body_SHA256']:
        raise ValueError('Lossless toy native body mismatch')
    json.loads(body)
    reviewer_files = json.loads((REVIEW / 'PAYLOAD_SHA256.json').read_text())
    for name, expected_review in reviewer_files.items():
        actual = toy['native_body_SHA256'] if name == 'fixed_toy.json' else digest(REVIEW / relative(name))
        if actual != expected_review:
            raise ValueError('Independent reviewer payload identity mismatch')
    return {'status': 'PASS_PUBLIC_V2_SCIENCE_ORIGINAL_CODE_AND_LOSSLESS_OUTPUT_IDENTITIES',
            'public_manifest_SHA256': expected, 'source_freeze_SHA256': FREEZE,
            'public_members_verified': len(manifest['files']),
            'original_code_only_bodies_verified': len(observed),
            'saved_toy_native_body_SHA256': toy['native_body_SHA256'],
            'saved_toy_native_body_bytes': len(body), 'historical_go': False}


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (AS_LIMIT, AS_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


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
        parser.error('Require Python3.12 on Linux with resource limits and CPU affinity')
    identity = verify(args.expected_manifest_sha256)
    output = HERE / 'cold_synthetic_receipts'
    output.mkdir(exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1',
               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    env.pop('PYTHONOPTIMIZE', None)
    env.pop('PYTHONPATH', None)
    commands = [('runtime_identity', HERE, ['-c', "import numpy\nif numpy.__version__!='2.3.5':raise SystemExit('NumPy identity mismatch')\nprint('PASS Python3.12 NumPy2.3.5')"]),
                ('original_source_preflight', DESIGN, ['source_preflight.py']),
                ('designer_34_tests', DESIGN, ['-m', 'unittest', '-v', 'test_bounded_highrisk']),
                ('independent_43_tests', REVIEW, ['-m', 'unittest', '-v', 'test_adversarial']),
                ('fixed_generated_toys', DESIGN, ['run_toy.py'])]
    records = []
    for stage, cwd, command in commands:
        start, peak, stop = time.monotonic(), 0, None
        with (output / (stage + '.txt')).open('x') as log:
            process = subprocess.Popen([sys.executable, '-B', *command], cwd=cwd,
                                       env=env, preexec_fn=limits, stdout=log,
                                       stderr=subprocess.STDOUT)
            while process.poll() is None:
                peak = max(peak, rss(process.pid))
                if peak > RSS_STOP:
                    stop = 'RSS_LIMIT'
                elif time.monotonic() - start > 120:
                    stop = 'WALL_LIMIT'
                if stop:
                    process.kill()
                    break
                time.sleep(.02)
            code = process.wait()
        records.append({'stage': stage, 'exit_code': code, 'stop_reason': stop,
                        'elapsed_seconds': time.monotonic() - start,
                        'sampled_peak_RSS_bytes': peak, 'AS_limit_bytes': AS_LIMIT,
                        'RSS_stop_bytes': RSS_STOP, 'CPU_limit_seconds': 60,
                        'wall_limit_seconds': 120, 'output_limit_bytes': 10 * 1024 * 1024,
                        'CPU_affinity_count': 1, 'threads': 1})
        if code or stop:
            break
    unchanged = verify(args.expected_manifest_sha256) == identity
    exact_toy = len(records) == 5 and digest(output / 'fixed_generated_toys.txt') == identity['saved_toy_native_body_SHA256']
    passed = len(records) == 5 and unchanged and exact_toy and all(row['exit_code'] == 0 and row['stop_reason'] is None for row in records)
    receipt = {'status': 'PASS_BOUNDED_PUBLIC_COLD_SYNTHETIC' if passed else 'FAIL_PUBLIC_COLD',
               'identity_gate': identity, 'source_bytes_unchanged': unchanged,
               'fresh_toy_equals_lossless_saved_native_body': exact_toy, 'records': records,
               'historical_wallets': 0, 'market_reads': 0, 'downloads': 0,
               'historical_financial_advances': 0, 'synthetic_account_methods_exercised': True,
               'fits': 0, 'historical_go': False, 'economic_certification': False}
    (output / 'PUBLIC_SAFE_COLD_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
