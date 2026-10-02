import hashlib, json, shutil, subprocess
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

root = Path('/mnt/d/codex/coin')
state = Path('/home/xflops/coin-state/public-donchian-tiny-20261002-v1')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
tasks = [p for p in Path('/home/xflops/coin-state/task-progress').glob('*.json')
         if json.loads(p.read_text()).get('title') == '公开Donchian规则 · 因果与缺分钟核验']
assert len(tasks) == 1
task = json.loads(tasks[0].read_text())
assert task['status'] == 'completed' and task['exit_code'] == 0
junit = state / 'junit.xml'
suites = list(ET.parse(junit).getroot().iter('testsuite'))
assert sum(int(s.attrib['tests']) for s in suites) == 3
assert all(int(s.attrib.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped'))
paths = ['scripts/research_v8/public_donchian_adapter.py', 'tests/test_public_donchian_adapter.py',
    'scripts/research_v8/benchmark_targets.py', 'scripts/research_v8/benchmark_targets_v2.py',
    'scripts/research_v8/labels_v3.py', 'third_party/jesse_example_donchian/donchian_original.py',
    'third_party/jesse_example_donchian/donchian_indicator_original.py',
    'third_party/jesse_example_donchian/LICENSE', 'third_party/jesse_example_donchian/JESSE_LICENSE',
    'third_party/jesse_example_donchian/UPSTREAM.md']
hashes = {name: sha(root / name) for name in paths}
for name in paths:
    dst = state / 'source-snapshot' / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    assert not dst.exists()
    shutil.copyfile(root / name, dst)
receipt = dict(status='PASS_PUBLIC_RULE_PORT_TINY_CAUSALITY_ONLY', created_utc=datetime.now(UTC).isoformat(),
    git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    source_sha256=hashes, upstream_local_modifications='No upstream bytes changed; explicit signal context port only',
    test_scope=['public hook entry/hold/exit and previous20 excluding current', 'future OHLC perturbation',
        'missing/delayed hour invalidates whole paired fold'], tests=3,
    actual_session=29060, actual_host_exit=0, actual_child_exit=task['exit_code'], actual_task=task,
    task_path=str(tasks[0]), task_sha256=sha(tasks[0]), junit_path=str(junit), junit_sha256=sha(junit),
    registry_start='NOT_REGISTERED_BEFORE_SYNTHETIC_RUN; no market trial or parameter fitting occurred',
    market_read=False, fits=0, locked_consumed=False, orders_sent=0, GPU_hours=0,
    economic_result='NOT_YET_RUN', qualified_candidate='NONE')
output = root / 'reports/fast_research/PUBLIC_DONCHIAN_ADAPTER_TINY_20261002_V1.json'
with output.open('x') as f: json.dump(receipt, f, indent=2, ensure_ascii=False, allow_nan=False); f.write('\n')
print(json.dumps(dict(status=receipt['status'], path=str(output), sha256=sha(output), public_source_sha256=hashes[paths[0]])))
