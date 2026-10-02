"""Project one private lock out of Git-only pins; retain the exact failed guard evidence."""
from datetime import UTC, datetime
import hashlib, json, os, re, subprocess, sys
from pathlib import Path
ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
LIMIT = 100_000
ORIGINAL = 'reports/GITHUB_PUBLIC_LONG_547D_SOURCE_BINDING_20261003_V1.json'
ORIGINAL_SHA = '5c8e05ead3ebc86cb1b6c705bd3824e51a175fad8fc24c0d05de6da38a10d2ff'
ORIGINAL_STATUS = 'PASS_CLOSED_PUBLIC_LONG_547D_SOURCE_BINDING_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR'
ARCHIVE = 'docs/archive/PUBLIC_LONG_547D_PORTABLE_PREFLIGHT_PROJECTION_SOURCE_20261003_V1.py'
OUT = 'reports/GITHUB_PUBLIC_LONG_547D_PORTABLE_PREFLIGHT_BINDING_20261003_V1.json'
LOCK = 'state/dataset_lock.json'
LOCK_SHA = '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
TITLE = '547日公开策略 · 提交前字节与凭证检查'
TASK_ID = '7094803632ba42e7bd3a0c0835b668c6'
TASK_SHA = '95cb1505ded88de0595da38e625e2014b61fa381cdb771639735405d9a740d86'
TASK_ARCHIVE = 'docs/archive/PUBLIC_LONG_547D_PREFLIGHT_PRIVATE_STATE_FAILURE_TASK_20261003_V1.json'
FAILURE = 'reports/GITHUB_PUBLIC_LONG_547D_STAGED_PREFLIGHT_FAILURE_20261003_V1.json'
GUARD = 'docs/archive/PUBLIC_LONG_547D_STANDARD_GIT_PREFLIGHT_SOURCE_20261003_V1.py'
GUARD_SHA = '2f709f45b7fd6b91cf12c7ae0ea92fcfb8834b84c9bef2c7d962220d5403a6b8'
CACHE_GUARD = '.cache/github_module_preflight.py'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    path = Path(path)
    assert path.is_file() and not path.is_symlink() and path.stat().st_size <= LIMIT
    assert path.resolve().is_relative_to(ROOT) or path.resolve().is_relative_to(STATE)
    return path.read_bytes()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def main():
    assert os.environ.get('COIN_TASK_ID') and Path(sys.prefix).resolve() == STATE / 'v8-clean-env-20261002-v2'
    assert Path(__file__).resolve() == ROOT / ARCHIVE
    own = read(__file__)
    original_bytes = read(ROOT / ORIGINAL)
    assert digest(original_bytes) == ORIGINAL_SHA
    original = json.loads(original_bytes)
    assert original['status'] == ORIGINAL_STATUS and original['candidate_status'] == 'NO_QUALIFIED_CANDIDATE'
    pins = original['source_hashes']
    assert isinstance(pins, dict) and pins.get(LOCK) == LOCK_SHA
    for name, value in pins.items():
        assert isinstance(name, str) and not Path(name).is_absolute() and '\x00' not in name
        assert (ROOT / name).resolve().is_relative_to(ROOT) and re.fullmatch('[0-9a-f]{64}', value)
    # Query only the original pinned paths. No working-tree, market, or whole-disk scan.
    index = subprocess.check_output(['git', 'ls-files', '--stage', '-z', '--', *pins], cwd=ROOT)
    assert len(index) <= LIMIT
    staged = set()
    for record in index.split(b'\x00'):
        if not record:
            continue
        header, name = record.split(b'\t', 1)
        mode, object_id, stage = header.split(b' ')
        assert mode in (b'100644', b'100755') and stage == b'0' and re.fullmatch(b'[0-9a-f]{40}', object_id)
        name = name.decode('utf-8')
        assert name in pins and name not in staged
        staged.add(name)
    missing = sorted(set(pins) - staged)
    assert missing == [LOCK], missing
    assert digest(read(ROOT / LOCK)) == LOCK_SHA
    assert digest(read(ROOT / GUARD)) == digest(read(ROOT / CACHE_GUARD)) == GUARD_SHA
    task_path = STATE / 'task-progress' / ('task-' + TASK_ID + '.json')
    task_bytes = read(task_path)
    assert digest(task_bytes) == TASK_SHA
    task = json.loads(task_bytes)
    assert task['id'] == TASK_ID and task['title'] == TITLE and task['status'] == 'failed'
    assert type(task['exit_code']) is int and task['exit_code'] == 1
    titles = []
    for path in (STATE / 'task-progress').glob('task-*.json'):
        value = json.loads(read(path))
        if value.get('title') == TITLE:
            titles.append(value['id'])
    assert titles == [TASK_ID], titles
    assert not any((ROOT / name).exists() for name in (TASK_ARCHIVE, FAILURE, OUT))
    stamp = datetime.now(UTC).isoformat()
    failure = dict(status='PRESERVED_D033_STAGED_PREFLIGHT_FAILURE_PRIVATE_LOCAL_STATE_NOT_IN_GIT', created_utc=stamp,
        binding=dict(session_id=33053, chunk_id='84d8b8', host_exit_code=1, actual_task_id=TASK_ID,
            actual_task_exit_code=1, actual_task_sha256=TASK_SHA, actual_task_archive=TASK_ARCHIVE),
        original_binding=dict(path=ORIGINAL, sha256=ORIGINAL_SHA),
        exact_missing_staged_paths=missing, failure='Frozen artifact missing from staged tree',
        source_provenance=dict(standard_guard_archive=GUARD, standard_guard_sha256=GUARD_SHA,
            local_guard_operation_path=CACHE_GUARD, local_guard_operation_sha256=GUARD_SHA,
            projection_source=ARCHIVE, projection_source_sha256=digest(own)),
        local_non_git_source_hashes={LOCK: LOCK_SHA}, standard_guard_changed=False,
        original_binding_overwritten=False, source_or_financial_tests_or_market_arrays_replayed=False)
    failure_bytes = encoded(failure)
    projected = {name: value for name, value in pins.items() if name != LOCK}
    for name, value in ((ORIGINAL, ORIGINAL_SHA), (ARCHIVE, digest(own)), (GUARD, GUARD_SHA),
                        (TASK_ARCHIVE, TASK_SHA), (FAILURE, digest(failure_bytes))):
        assert name not in projected or projected[name] == value
        projected[name] = value
    value = dict(status='PASS_PORTABLE_GIT_PREFLIGHT_SOURCE_PROJECTION_NOT_ECONOMIC_REVALIDATION', created_utc=stamp,
        binding=dict(task_id=os.environ['COIN_TASK_ID'], exporter_sha256=digest(own),
            original_binding_path=ORIGINAL, original_binding_sha256=ORIGINAL_SHA),
        source_hashes=projected, local_non_git_source_hashes={LOCK: LOCK_SHA},
        explicit_Git_only_exclusions=[dict(path=LOCK, sha256=LOCK_SHA,
            reason='Intentionally local private state; byte identity remains separately bound and enforced locally')],
        original_source_hashes_preserved_except_exact_private_lock=True,
        index_metadata=dict(command='git ls-files --stage -z -- <original pinned paths>',
            bytes=len(index), sha256=digest(index), exact_missing_paths=missing, matched_original_paths=len(staged)),
        preserved_standard_preflight_failure=dict(report=FAILURE, sha256=digest(failure_bytes), task_id=TASK_ID),
        unchanged_standard_guard=dict(path=GUARD, sha256=GUARD_SHA),
        standard_guard_changed=False, frozen_guard_weakened=False, original_binding_overwritten=False,
        projection_executed_before_standard_guard_rerun=True, rerun_standard_guard='REQUIRED_NOT_YET_EXECUTED_BY_THIS_HELPER',
        market_arrays_QA_tests_or_scientific_replays=False, candidate_status='NO_QUALIFIED_CANDIDATE',
        sustainable_net_APR='NOT_ESTABLISHED', locked_consumed=False)
    output_bytes = encoded(value)
    assert len(own) + len(task_bytes) + len(failure_bytes) + len(output_bytes) <= LIMIT
    # Inputs and the frozen guard are checked again before exclusive metadata writes.
    assert digest(read(ROOT / ORIGINAL)) == ORIGINAL_SHA and digest(read(ROOT / LOCK)) == LOCK_SHA
    assert digest(read(ROOT / GUARD)) == digest(read(ROOT / CACHE_GUARD)) == GUARD_SHA
    assert digest(read(task_path)) == TASK_SHA
    for name, data in ((TASK_ARCHIVE, task_bytes), (FAILURE, failure_bytes), (OUT, output_bytes)):
        with (ROOT / name).open('xb') as stream:
            stream.write(data)
    print(json.dumps(dict(status=value['status'], output=OUT, sha256=digest(output_bytes),
        failure_report=FAILURE, failure_sha256=digest(failure_bytes), task_archive=TASK_ARCHIVE,
        task_sha256=TASK_SHA, generated_bytes=len(task_bytes)+len(failure_bytes)+len(output_bytes))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
