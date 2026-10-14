"""Bounded source-bound acceptance after the producer explicitly freezes.

Only generated tapes run. Original executable closure files are hashed to
verify identity; saved target artifacts in that closure are never parsed or
advanced as historical arrays. Prior helper review is reused at exact hashes.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CANDIDATE = ROOT / 'coin_bot_native_adapter_synthetic_20261014'
LAUNCHER = ROOT / 'native_pair_replacement_review_20261014/loader_identity_patch'
DEPENDENCIES = ROOT / 'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d'
HELPER_REVIEW = ROOT / 'coin_bot_independent_review_20261014'
FROZEN_SHA256 = 'c24974783e50ec8b83b199e1c6b271e75fe87d58951c4d581ce53dd46ddf1a0b'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def candidate_hashes():
    return {str(p.relative_to(CANDIDATE)): sha(p) for p in sorted(CANDIDATE.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def verify_manifest(path):
    if sha(path) != FROZEN_SHA256:
        raise ValueError('PRODUCER_CONFIRMED_FREEZE_HASH_MISMATCH')
    manifest = json.loads(path.read_text())
    if (manifest['schema'] != 'GENERATED_NATIVE_GRID_ADAPTER_SOURCE_FREEZE_V1'
        or manifest['status'] != 'FROZEN_FOR_INDEPENDENT_SYNTHETIC_REVIEW'
        or manifest['runtime'] != '519b17f6ce94cb4b5955174d8e520765edaacfee'
        or manifest['historical_GO'] is not False or manifest['risk_parity_certified'] is not False):
        raise ValueError('FROZEN_SCOPE_MISMATCH')
    for name, record in manifest['files'].items():
        candidate = CANDIDATE / name
        if candidate.is_symlink() or not candidate.resolve().is_relative_to(CANDIDATE.resolve()):
            raise ValueError('UNSAFE_FROZEN_LOCATOR:' + name)
        if sha(candidate) != record['SHA256'] or candidate.stat().st_size != record['bytes']:
            raise ValueError('FROZEN_FILE_MISMATCH:' + name)
    return manifest


def original_hashes():
    closure = json.loads((LAUNCHER / 'EXECUTABLE_CLOSURE.json').read_text())
    roots = json.loads((DEPENDENCIES / 'SYNTHETIC_ROOTS.json').read_text())
    records = {}
    for group, root in [('repo_files', roots['repo']), ('fine_files', roots['fine'])]:
        for name, record in closure[group].items():
            path = Path(root) / name
            actual = sha(path)
            if actual != record['SHA256']:
                raise ValueError('ORIGINAL_CLOSURE_DRIFT:' + name)
            records[str(path.relative_to(ROOT))] = actual
    terminal = LAUNCHER / 'terminal_adapter.py'
    if sha(terminal) != closure['terminal_adapter_SHA256']:
        raise ValueError('ORIGINAL_TERMINAL_DRIFT')
    records[str(terminal.relative_to(ROOT))] = sha(terminal)
    return records


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024 ** 3, 4 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def main():
    if len(sys.argv) != 2:
        raise ValueError('Pass the producer-confirmed frozen manifest filename.')
    freeze = CANDIDATE / sys.argv[1]
    if not freeze.is_file() or freeze.parent != CANDIDATE:
        raise ValueError('FROZEN_MANIFEST_REQUIRED')
    freeze_hash = sha(freeze)
    manifest = verify_manifest(freeze)
    helper = json.loads((HELPER_REVIEW / 'REVIEW_CHECK_RECEIPT_0001.json').read_text())
    for name in ('grid_policy.py', 'risk_gate.py'):
        if sha(ROOT / 'coin_bot_risk_matched_synthetic_20261014' / name) != helper['source_after_SHA256'][name]:
            raise ValueError('PREVIOUS_HELPER_REVIEW_SOURCE_CHANGED:' + name)
    before = candidate_hashes()
    originals_before = original_hashes()
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
               MKL_NUM_THREADS='1', POLARS_MAX_THREADS='1')
    commands = [
        ('designer_generated_tests', CANDIDATE, ['-m', 'unittest', '-v', 'test_native_adapter']),
        ('independent_generated_tests', HERE, ['-m', 'unittest', '-v', 'test_native_adversarial']),
        ('verified_financial_runtime_identity', CANDIDATE,
         ['-c', 'import native_adapter; print(native_adapter.PORT.verify()); print("ORIGINAL_FINANCIAL_RUNTIME_CLOSURE_VERIFIED")']),
        ('independent_exported_journal_audit', HERE, ['audit_exported_journals.py']),
    ]
    results = []
    for label, directory, arguments in commands:
        start = time.monotonic()
        try:
            outcome = subprocess.run([sys.executable, *arguments], cwd=directory, env=env,
                                     text=True, capture_output=True, timeout=180, preexec_fn=limits)
            record = dict(step=label, returncode=outcome.returncode,
                          wall_seconds=time.monotonic() - start,
                          stdout=outcome.stdout, stderr=outcome.stderr)
        except subprocess.TimeoutExpired as error:
            record = dict(step=label, returncode='TIMEOUT', wall_seconds=time.monotonic() - start,
                          stdout=str(error.stdout), stderr=str(error.stderr))
        results.append(record)
        (HERE / (label.upper() + '.txt')).write_text(record['stdout'] + record['stderr'])
    after = candidate_hashes()
    originals_after = original_hashes()
    verify_manifest(freeze)
    unchanged = before == after and originals_before == originals_after and sha(freeze) == freeze_hash
    passed = unchanged and all(result['returncode'] == 0 for result in results)
    receipt = dict(
        schema='INDEPENDENT_NATIVE_GRID_ADAPTER_GENERATED_REVIEW_V1',
        status='PASS_GENERATED_MECHANICS_ONLY_NO_HISTORY' if passed else 'FAIL_OR_SOURCE_CHANGED',
        reviewed_UTC=datetime.now(timezone.utc).isoformat(),
        candidate='CSH_BTC_GRID_REPLACE10', producer_freeze_file=freeze.name,
        producer_freeze_SHA256=freeze_hash, candidate_before_SHA256=before,
        producer_freeze_all_entries_verified=len(manifest['files']),
        candidate_after_SHA256=after, original_before_SHA256=originals_before,
        original_after_SHA256=originals_after, candidate_and_original_sources_unchanged=unchanged,
        previous_helper_review_receipt_SHA256=sha(HELPER_REVIEW / 'REVIEW_CHECK_RECEIPT_0001.json'),
        previous_helper_review_tests_reused=81, previous_helper_publication_commit='8d8a26a375607dfdb5f97bbaabf047a18125fd13',
        independent_suite_SHA256=sha(HERE / 'test_native_adversarial.py'),
        review_runner_SHA256=sha(__file__), commands=results,
        limits=dict(cpu_affinity_count=1, address_space_GiB=4, CPU_seconds_per_child=120,
                    wall_seconds_per_child=180), peak_child_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        market_arrays_loaded=0, historical_wallets=0, downloads=0, external_mutations=0,
        producer_sources_edited_by_reviewer=False, original_financial_patch=None,
        split_restore_parity='NOT_ADVERTISED_EXPLICITLY_UNSUPPORTED',
        realized_risk_parity_certified=False, future_risk_guaranteed=False, historical_GO=False,
        next_stage='SEPARATE_SOURCE_LINEAGE_PREFLIGHT_INDEPENDENT_REVIEW_AND_EXPLICIT_ROOT_GO_REQUIRED',
    )
    number = 1
    while (HERE / f'REVIEW_RECEIPT_{number:04d}.json').exists():
        number += 1
    destination = HERE / f'REVIEW_RECEIPT_{number:04d}.json'
    with destination.open('x') as output:
        json.dump(receipt, output, indent=2, allow_nan=False)
        output.write('\n')
    print(json.dumps(dict(status=receipt['status'], receipt=destination.name,
                          candidate_unchanged=unchanged, historical_GO=False), indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
