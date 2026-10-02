"""Archive existing synthetic output; never import/run target code or pytest."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
from datetime import UTC, datetime
from xml.etree import ElementTree

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
OUT = ROOT / 'reports/fast_research/PUBLIC_DONCHIAN_HYBRID_TARGET_TINY_20261002_V1.json'
ARCHIVE = ROOT / 'docs/archive/PUBLIC_DONCHIAN_HYBRID_TARGET_TINY_RECEIPT_SOURCE_20261002_V1.py'
TASK = STATE / 'task-progress/task-369681b4d20d4a3eb6219421adc45faa.json'
JUNIT = STATE / 'test-public-donchian-hybrid-20261002-v1/junit.xml'
EXPECTED = {
    'scripts/investment/public_donchian_hybrid.py': '80e4b24319becacefb0d6c9551473e3d4214cf3167ae45f5ac8ff7f559c27d68',
    'tests/test_public_donchian_hybrid.py': '43f75ddce8301962638a4b215b00486e1e79b1925423af47643b5e5ac82ffdc5',
    'scripts/research_v8/public_donchian_adapter.py': '169d7ba6ebde24be5ce4730c5e741ed281a0155e4cadc22f1bb2bedccb4093c2',
    'scripts/research_v8/benchmark_targets.py': 'cb3158116494c41b6649f80dc4013b3c1ff9e495773b3ae298d9d5b6e9d46652',
    'scripts/research_v8/benchmark_targets_v2.py': '72235137633847101af57e658f8a50ea50494e1a63de663784754d72fef81a82',
    'environments/v8/uv.lock': '97335dc3dbb04d7dbc67425f91d4e941a0cfd2c84e5f2adcd852514ec4600de6',
    'third_party/jesse_example_donchian/donchian_original.py': 'fc635b257ad1e12951dc140dae46a63bd37e9abfa5f2d681ef1e754d8ce393fe',
    'third_party/jesse_example_donchian/donchian_indicator_original.py': 'b7e96ebe3ba476c771a65b353c269a84d02e04587f0d76166c5f322bbbb3a401',
    'third_party/jesse_example_donchian/LICENSE': '80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d',
    'third_party/jesse_example_donchian/JESSE_LICENSE': '8985ca8447e233f34397a52fe77989c02e27b8145d43bd8c715ae9c7a96056d4',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not ARCHIVE.exists(), 'Refuse to overwrite prior evidence'
    for name, expected in EXPECTED.items():
        assert sha(ROOT / name) == expected, f'Source bytes changed: {name}'
    assert sha(TASK) == 'c052fc7740f482e23e5148499ebf0752df752b085fa9ee9095795df7f07aba6f'
    assert sha(JUNIT) == 'ad7d488e8f5581a85926991be2c8f06bd259b139c0c75ee4df90bd47510bfe8b'
    task = json.loads(TASK.read_text())
    assert task['id'] == '369681b4d20d4a3eb6219421adc45faa'
    assert task['status'] == 'completed' and task['exit_code'] == 0
    assert task['pid'] == 20228 and task['start_ticks'] == 2652834
    suite = ElementTree.parse(JUNIT).getroot().find('testsuite')
    counts = {key: int(suite.attrib[key]) for key in ('tests', 'failures', 'errors', 'skipped')}
    assert counts == dict(tests=7, failures=0, errors=0, skipped=0)
    cases = [item.attrib['name'] for item in suite.findall('testcase')]
    assert len(cases) == 7
    self_path = Path(__file__).resolve()
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with ARCHIVE.open('xb') as writer:
        writer.write(self_path.read_bytes())
    assert sha(ARCHIVE) == sha(self_path)
    command = ('/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -m pytest '
        '/mnt/d/codex/coin/tests/test_public_donchian_hybrid.py '
        '--basetemp=/home/xflops/coin-state/test-public-donchian-hybrid-20261002-v1/pytest '
        '--junitxml=/home/xflops/coin-state/test-public-donchian-hybrid-20261002-v1/junit.xml '
        '-q -p no:cacheprovider')
    result = {
        'version': 'PUBLIC_DONCHIAN_HYBRID_TARGET_TINY_20261002_V1',
        'status': 'PASS_PUBLIC_DONCHIAN_HYBRID_TARGET_SYNTHETIC_NOT_MARKET_RESULT',
        'created_utc': datetime.now(UTC).isoformat(),
        'scope': 'Existing seven synthetic target-intent cases only; output/source metadata archive, no rerun',
        'strategy_id': 'COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER',
        'git_commit_at_original_test': 'd7aaeb4b1ec5e04908c341a8ab6a569ff81bfde1',
        'git_commit_at_metadata_archive': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'actual_host_session_id': 92586, 'test_exit_code': 0,
        'outer_exit_observation': 'Original unified-exec session92586 completion; task independently matches completed/exit0',
        'test_source_path': 'tests/test_public_donchian_hybrid.py',
        'source_sha256': EXPECTED['scripts/investment/public_donchian_hybrid.py'],
        'test_source_sha256': EXPECTED['tests/test_public_donchian_hybrid.py'],
        'source_hashes': EXPECTED, 'source_bytes_unchanged': True,
        'junit_path': str(JUNIT), 'junit_sha256': sha(JUNIT), 'junit_counts': counts,
        'existing_test_cases': cases, 'pytest_reported_seconds': float(suite.attrib['time']),
        'task_path': str(TASK), 'task_sha256': sha(TASK), 'actual_task': task,
        'outer_elapsed_seconds': task['ended_at'] - task['started_at'],
        'exact_test_command': command,
        'progress_wrapper': 'scripts/with_task_progress.sh -> scripts/bounded.sh; original task title unchanged',
        'test_environment': {'python': '/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python',
            'threads': 1, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONPATH': '/mnt/d/codex/coin/src:/mnt/d/codex/coin',
            'shared_RAM_policy_limit_bytes': 5000000000, 'swap_policy_bytes': 0},
        'original_test_peak_RSS_bytes': None,
        'resource_limit': 'Original test process RSS not captured; not fabricated from shared cgroup lifetime peak',
        'market_inputs_read': False, 'market_models_fit': 0, 'source_QA_rerun': False,
        'pytest_rerun': False, 'locked_consumed': False, 'orders_sent': 0,
        'GPU_used': False, 'economic_metrics': None, 'candidate_status': 'NO_QUALIFIED_CANDIDATE',
        'semantics': {'entry': 'New closed2h prior20 upper + original SMA200 filter',
            'exit': 'Held at new closed1h uses original prior20 lower hook',
            'same_stamp': 'Held exit first; no same-stamp reentry',
            'reentry': 'Next new closed2h event; no additional cooldown',
            'warmup': '200 contiguous available bars in each timeframe',
            'missing': 'Whole paired fold not evaluable; earlier causal intents retained',
            'terminal': 'Lastweight0 intent; feasible costed fill still required',
            'interpretation': 'Joint exit frequency/40h-to-20h lookback; not pure latency causality'},
        'metadata_archive_operation': {'python': sys.executable, 'source_path': str(self_path),
            'source_sha256': sha(self_path), 'archive_path': str(ARCHIVE), 'archive_sha256': sha(ARCHIVE),
            'progress_task_id': os.environ.get('COIN_TASK_ID', 'UNKNOWN'),
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024},
        'registry_appended': False,
    }
    with OUT.open('x') as writer:
        json.dump(result, writer, ensure_ascii=False, indent=2)
        writer.write('\n')
    print(json.dumps({'status': result['status'], 'receipt': str(OUT), 'sha256': sha(OUT),
                      'archive': str(ARCHIVE), 'archive_sha256': sha(ARCHIVE)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
