"""Fixed, bounded code-preflight and generated tests only."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import hashlib
HERE = Path(__file__).resolve().parent


def verify_manifest(expected):
    raw = (HERE / 'RUNNER_MANIFEST.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('TRUSTED_RUNNER_MANIFEST_MISMATCH')
    manifest = json.loads(raw)
    for name, digest in manifest['files_SHA256'].items():
        p = Path(name)
        if p.is_absolute() or '..' in p.parts or (HERE / p).is_symlink():
            raise ValueError('RUNNER_FILE_PATH_REFUSED')
        if hashlib.sha256((HERE / p).read_bytes()).hexdigest() != digest:
            raise ValueError('RUNNER_SOURCE_IDENTITY_MISMATCH')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--roots', required=True)
    p.add_argument('--runner-manifest-sha', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    verify_manifest(a.runner_manifest_sha)
    output = Path(a.output)
    output.mkdir(exist_ok=False)
    env = dict(os.environ, PAIRED_TEST_CODE_ROOTS=str(Path(a.roots).resolve()),
        PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
        MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    env.pop('PYTHONOPTIMIZE', None)
    def limits():
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        resource.setrlimit(resource.RLIMIT_AS, (4_000_000_000, 4_000_000_000))
        resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    commands = [('code_metadata_preflight', [sys.executable, '-B', 'source_cli.py', 'preflight',
            '--runner-manifest-sha', a.runner_manifest_sha, '--roots', str(Path(a.roots).resolve())]),
        ('synthetic_tests', [sys.executable, '-B', 'source_cli.py', 'synthetic-tests',
            '--runner-manifest-sha', a.runner_manifest_sha, '--roots', str(Path(a.roots).resolve())])]
    records = []
    for stage, command in commands:
        began, peak, stop = time.monotonic(), 0, None
        with (output / (stage + '.log')).open('x') as log:
            child = subprocess.Popen(command, cwd=HERE, env=env, preexec_fn=limits,
                stdout=log, stderr=subprocess.STDOUT)
            while child.poll() is None:
                try:
                    lines = Path(f'/proc/{child.pid}/status').read_text().splitlines()
                    peak = max(peak, next((int(x.split()[1]) * 1024 for x in lines if x.startswith('VmRSS:')), 0))
                except FileNotFoundError:
                    pass
                if peak > 2_000_000_000: stop = 'RSS_LIMIT'
                elif time.monotonic() - began > 120: stop = 'WALL_LIMIT'
                if stop:
                    child.kill()
                    break
                time.sleep(.02)
            code = child.wait()
        records.append({'stage': stage, 'exit_code': code, 'stop_reason': stop,
            'elapsed_seconds': time.monotonic() - began, 'peak_RSS_bytes': peak,
            'AS_limit_bytes': 4_000_000_000, 'RSS_stop_bytes': 2_000_000_000,
            'CPU_seconds': 60, 'wall_seconds': 120, 'CPUs': 1, 'math_threads': 1})
        if code or stop: break
    passed = len(records) == 2 and all(r['exit_code'] == 0 and r['stop_reason'] is None for r in records)
    receipt = {'status': 'PASS_BOUNDED_CODE_AND_SYNTHETIC' if passed else 'FAIL_BOUNDED_CODE_AND_SYNTHETIC',
        'runner_manifest_SHA256': a.runner_manifest_sha, 'records': records,
        'historical_array_reads': 0, 'wallets': 0, 'fits': 0, 'new_market_downloads': 0}
    (output / 'RESOURCE_RECEIPT.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, sort_keys=True))
    if not passed: raise SystemExit(1)


if __name__ == '__main__':
    main()
