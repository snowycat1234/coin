"""Source-bound independent portable review, generated-only and from start."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = ROOT / 'coin_bot_native_adapter_portable_synthetic_20261014'
PRIOR = ROOT / 'coin_bot_native_adapter_synthetic_20261014'
OLD_REVIEW = ROOT / 'coin_bot_native_independent_review_20261014'
FREEZE = '732c04cd365c06b487ccbaff1c5916e23e73bb6d9718c663450d0f1603f0a6f0'
PRIOR_FREEZE = 'c24974783e50ec8b83b199e1c6b271e75fe87d58951c4d581ce53dd46ddf1a0b'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(directory, filename, expected):
    path = directory / filename
    if sha(path) != expected:
        raise ValueError('FREEZE_HASH_MISMATCH:' + filename)
    manifest = json.loads(path.read_text())
    for name, record in manifest['files'].items():
        relative = Path(name)
        path = directory / relative
        if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or not path.resolve().is_relative_to(directory):
            raise ValueError('UNSAFE_FREEZE_PATH:' + name)
        if path.suffix.lower() in ('.npz', '.npy', '.parquet', '.arrow', '.feather', '.pyc'):
            raise ValueError('ARRAY_OR_CACHE_IN_FREEZE:' + name)
        if sha(path) != record['SHA256'] or path.stat().st_size != record['bytes']:
            raise ValueError('EXACT_FROZEN_FILE_MISMATCH:' + name)
    return manifest


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def main():
    portable = verify(SOURCE, 'PORTABLE_FINAL_MANIFEST.json', FREEZE)
    prior = verify(PRIOR, 'FINAL_MANIFEST.json', PRIOR_FREEZE)
    scope = json.loads((SOURCE / 'REVISION_SCOPE.json').read_text())
    for name, expected in scope['unchanged_scientific_files'].items():
        if sha(SOURCE / name) != expected or sha(PRIOR / name) != expected:
            raise ValueError('SCIENTIFIC_BODY_CHANGED:' + name)
    locators = json.loads((SOURCE / 'PUBLIC_SOURCE_LOCATORS.json').read_text())
    for name, record in locators['files'].items():
        raw = (SOURCE / name).read_bytes()
        git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if git_blob != record['GitBlobSHA1'] or hashlib.sha256(raw).hexdigest() != record['SHA256'] or len(raw) != record['bytes']:
            raise ValueError('EXACT_PUBLIC_BODY_IDENTITY:' + name)
    number = 1
    while (HERE / f'cold_run_{number:04d}').exists():
        number += 1
    cold = HERE / f'cold_run_{number:04d}'
    candidate = cold / SOURCE.name
    review = cold / 'independent_review'
    output = cold / 'fresh_output'
    candidate.mkdir(parents=True)
    review.mkdir()
    output.mkdir()
    for name in [*portable['files'], 'PORTABLE_FINAL_MANIFEST.json']:
        destination = candidate / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / name, destination)
    for name in ('cold_stage.py', 'test_portable_math.py'):
        shutil.copyfile(HERE / name, review / name)
    for name in ('test_native_adversarial.py', 'audit_exported_journals.py'):
        shutil.copyfile(OLD_REVIEW / name, review / name)
    assert not (cold / PRIOR.name).exists()
    cold_catalog_before = {str(p.relative_to(cold)): sha(p) for p in candidate.rglob('*') if p.is_file()}
    producer_receipt = json.loads((ROOT / 'coin_bot_native_portable_producer_final_20261014/PORTABLE_CHECK_RECEIPT.json').read_text())
    sites = [str(Path(record['file']).parent.parent) for record in producer_receipt['runtime'].values()]
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONOPTIMIZE', None)
    env.update(PYTHONPATH=os.pathsep.join(sites), PYTHONDONTWRITEBYTECODE='1',
               BOT_NATIVE_RUNTIME_SITES=json.dumps(sites), OPENBLAS_NUM_THREADS='1',
               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', POLARS_MAX_THREADS='1')
    results = []
    for stage in ('gate', 'math', 'native', 'independent', 'export', 'audit'):
        command = [sys.executable, '-B', str(review / 'cold_stage.py'), stage,
                   '--candidate', str(candidate), '--output', str(output),
                   '--review-sources', str(review), '--workspace', str(ROOT)]
        for site in sites:
            command.extend(('--runtime-site', site))
        start = time.monotonic()
        try:
            child = subprocess.run(command, cwd=cold, env=env, text=True,
                                   capture_output=True, timeout=180, preexec_fn=limits)
            code, log = child.returncode, child.stdout + child.stderr
        except subprocess.TimeoutExpired as error:
            code, log = 124, str(error)
        (output / (stage.upper() + '.txt')).write_text(log)
        results.append(dict(stage=stage, returncode=code, wall_seconds=time.monotonic()-start))
        print(json.dumps(results[-1]), flush=True)
        if code:
            break
    parity_path = output / 'EXACT_33_BODY_PARITY_RECEIPT.json'
    if len(results) == 6 and all(r['returncode'] == 0 for r in results):
        command = [sys.executable, '-B', str(HERE / 'compare_native_bodies.py'),
                   str(PRIOR / 'generated_journals'), str(output / 'generated_journals'), str(parity_path)]
        child = subprocess.run(command, env=env, text=True, capture_output=True,
                               timeout=180, preexec_fn=limits)
        (output / 'EXACT_BODY_PARITY.txt').write_text(child.stdout + child.stderr)
        results.append(dict(stage='exact_33_native_body_parity', returncode=child.returncode))
        print(child.stdout, flush=True)
    cold_catalog_after = {str(p.relative_to(cold)): sha(p) for p in candidate.rglob('*') if p.is_file()}
    verify(SOURCE, 'PORTABLE_FINAL_MANIFEST.json', FREEZE)
    verify(PRIOR, 'FINAL_MANIFEST.json', PRIOR_FREEZE)
    guards = [json.loads(p.read_text()) for p in sorted(output.glob('*_OPEN_GUARD.json'))]
    passed = len(results) == 7 and all(r['returncode'] == 0 for r in results)
    passed &= cold_catalog_before == cold_catalog_after and len(guards) == 6
    passed &= all(g['array_open_attempts'] == g['warm_workspace_open_attempts'] == 0 for g in guards)
    receipt = dict(schema='INDEPENDENT_PORTABLE_NATIVE_GRID_COLD_REVIEW_V1',
        status='PASS_SYNTHETIC_ONLY_COLD_SOURCE' if passed else 'FAIL',
        reviewed_UTC=datetime.now(timezone.utc).isoformat(),
        portable_freeze_SHA256=FREEZE, prior_c249_freeze_SHA256=PRIOR_FREEZE,
        source_files_verified=len(portable['files']), public_carrier_bodies_verified=len(locators['files']),
        compiled_original_code_inventory=len(scope['compiled_raw_code_files']),
        unchanged_scientific_bodies=scope['unchanged_scientific_files'],
        cold_source_catalog_before=cold_catalog_before, cold_source_catalog_after=cold_catalog_after,
        source_unchanged=cold_catalog_before == cold_catalog_after,
        original_c249_declared_files_reverified=len(prior['files']), stages=results,
        guarded_array_open_attempts=sum(g['array_open_attempts'] for g in guards),
        guarded_warm_workspace_open_attempts=sum(g['warm_workspace_open_attempts'] for g in guards),
        guarded_open_events=sum(g['guarded_open_events'] for g in guards),
        stage_open_guards=guards, exact_body_parity_receipt_SHA256=sha(parity_path) if parity_path.exists() else None,
        tests=dict(portable_binder=6, independent_math_and_transport=7, unchanged_native=20, reused_independent_native=26),
        limits=dict(cpu_affinity_count=1, address_space_GiB=4, cpu_seconds_per_child=120, wall_seconds_per_child=180),
        peak_child_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        reviewer_source_SHA256={name:sha(HERE/name) for name in ('cold_stage.py','test_portable_math.py','run_cold_review.py','compare_native_bodies.py')},
        reused_review_source_SHA256={name:sha(review/name) for name in ('test_native_adversarial.py','audit_exported_journals.py')},
        runtime_versions=dict(Python='3.12.14',NumPy='2.3.5',Polars='1.44.2',PyArrow='23.0.1'),
        cold_copy_manifest_only=True, caches_copied=0, source_arrays_copied=0,
        original26_historical_closure_verified=False, historical_admission='REFUSED',
        historical_GO=False, risk_parity_certified=False, restore_supported=False,
        financial_source_patch=None, producer_files_edited_by_reviewer=False)
    path = HERE / f'REVIEW_RECEIPT_{number:04d}.json'
    path.write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(status=receipt['status'],receipt=path.name,output=str(output.relative_to(HERE)))))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
