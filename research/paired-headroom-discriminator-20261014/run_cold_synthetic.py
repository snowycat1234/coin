"""Bounded portable synthetic validation, with public-safe operational receipts."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
AS_LIMIT = 4_000_000_000
RSS_STOP = 2_000_000_000
CPU_SECONDS = 60
WALL_SECONDS = 120


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (AS_LIMIT, AS_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def rss(pid):
    try:
        lines = Path(f'/proc/{pid}/status').read_text().splitlines()
    except FileNotFoundError:
        return 0
    for line in lines:
        if line.startswith('VmRSS:'):
            return int(line.split()[1]) * 1024
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--receipt-dir', default='cold_synthetic_receipts')
    args = parser.parse_args()
    if not re.fullmatch(r'cold_synthetic_receipts(?:_attempt[0-9]{3})?', args.receipt_dir):
        parser.error('Receipt directory must be a new owned cold-synthetic basename')
    if not sys.platform.startswith('linux') or not hasattr(os, 'sched_setaffinity'):
        parser.error('Bounded wrapper requires Linux CPU-affinity and process resource limits')
    # Hash and AST verification finishes before any candidate or NumPy execution.
    from verify_public_payload import verify
    gate = verify(args.expected_manifest_sha256)
    output = HERE / args.receipt_dir
    output.mkdir(exist_ok=False)
    commands = [
        ('runtime_identity', [sys.executable, '-B', '-c', "import sys,numpy\nif sys.version_info[:2]!=(3,12) or numpy.__version__!='2.3.5': raise SystemExit('Runtime identity mismatch')\nprint('PASS Python3.12 NumPy2.3.5')"]),
        ('candidate_21_tests', [sys.executable, '-B', '-m', 'unittest', '-v', 'test_paired_buffer']),
        ('generated_toy', [sys.executable, '-B', 'run_toy.py']),
        ('fixed_synthetic_scaling', [sys.executable, '-B', 'benchmark_toy.py']),
    ]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1',
               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    # Preserve the frozen preflight/test assertions even if the caller optimized Python.
    env.pop('PYTHONOPTIMIZE', None)
    records = []
    for stage, command in commands:
        began = time.monotonic()
        peak = 0
        stop = None
        with (output / (stage + '.txt')).open('x') as log:
            process = subprocess.Popen(command, cwd=HERE, env=env, stdout=log,
                                       stderr=subprocess.STDOUT, preexec_fn=limits)
            while process.poll() is None:
                peak = max(peak, rss(process.pid))
                if peak > RSS_STOP:
                    stop = 'RSS_LIMIT'
                elif time.monotonic() - began > WALL_SECONDS:
                    stop = 'WALL_LIMIT'
                if stop:
                    process.kill()
                    break
                time.sleep(.02)
            code = process.wait()
        record = {'stage': stage, 'exit_code': code, 'stop_reason': stop,
                  'elapsed_seconds': time.monotonic() - began, 'sampled_peak_RSS_bytes': peak,
                  'AS_limit_bytes': AS_LIMIT, 'RSS_stop_bytes': RSS_STOP,
                  'CPU_limit_seconds': CPU_SECONDS, 'wall_limit_seconds': WALL_SECONDS,
                  'CPU_affinity_count': 1, 'threads': 1}
        records.append(record)
        print(json.dumps(record, sort_keys=True))
        if code or stop:
            break
    passed = len(records) == 4 and all(r['exit_code'] == 0 and r['stop_reason'] is None for r in records)
    receipt = {'status': 'PASS_BOUNDED_COLD_SYNTHETIC' if passed else 'FAIL_BOUNDED_COLD_SYNTHETIC',
               'identity_gate': gate, 'records': records, 'historical_array_reads': 0,
               'wallets': 0, 'financial_advances': 0, 'market_requests': 0,
               'fits': 0, 'historical_GO': False}
    (output / 'PUBLIC_SAFE_RESOURCE_RECEIPT.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
