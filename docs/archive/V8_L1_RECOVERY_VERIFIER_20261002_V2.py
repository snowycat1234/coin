"""Read-only acceptance of the original public L1 collector's new session."""
import json
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path

from quant import resources
from quant.paths import ROOT, STATE
from quant.microstructure import MicrostructureCollector, read_microstructure_status
from quant.research_fast.dataset import file_sha

OUT = STATE/'v8-l1-clock-preservation-20261002-v2'
before = json.loads((OUT/'PRESERVATION.json').read_text())
assert before['status'] == 'L1_CLOCK_INCIDENT_PRESERVED_BEFORE_RESTART'
deadline = time.monotonic()+240
while True:
    tasks = [json.loads(path.read_text()) for path in (STATE/'task-progress').glob('task-*.json')]
    task = [value for value in tasks if value.get('title') == 'V8原源码L1公开采集恢复 · 时钟断档新会话V2']
    assert len(task) == 1
    task = task[0]
    assert task['status'] == 'running', task
    micro = read_microstructure_status()
    if micro['state'] == 'CONNECTED' and micro['checkpoint'].get('session') != before['microstructure_before']['checkpoint']['session']:
        break
    assert time.monotonic() < deadline, micro
    time.sleep(2)

def identity(pid):
    path = Path('/proc')/str(pid)
    return {'pid': pid, 'command': (path/'cmdline').read_bytes().replace(b'\0', b' ').decode(),
            'start_ticks': int((path/'stat').read_text().split(') ', 1)[1].split()[19]),
            'cgroup': (path/'cgroup').read_text().strip()}

process = identity(task['pid'])
assert process['command'].strip() == '.venv/bin/python -u -m quant.microstructure --run'
assert process['start_ticks'] == task['start_ticks']
assert 'coin-quant.slice' in process['cgroup']
assert micro['binding'] == before['microstructure_before']['binding']
assert file_sha(ROOT/'src/quant/microstructure.py') == micro['binding']['implementation_sha256']
assert [identity(value['pid']) for value in before['unchanged_other_processes']] == before['unchanged_other_processes']
assert file_sha(Path(before['closed_backup']['path'])) == before['closed_backup']['sha256']

old = sqlite3.connect(f'file:{before["closed_backup"]["path"]}?mode=ro&immutable=1', uri=True)
db = sqlite3.connect(f'file:{STATE/"microstructure.sqlite3"}?mode=ro', uri=True)
db.row_factory = sqlite3.Row
try:
    db.execute('BEGIN')
    reader = object.__new__(MicrostructureCollector)
    reader.db = db
    head_sha = reader.verify_audit()
    old_audit = old.execute('SELECT * FROM audit ORDER BY seq').fetchall()
    current_prefix = db.execute('SELECT * FROM audit WHERE seq<=? ORDER BY seq', (before['audit_head_before']['seq'],)).fetchall()
    assert old_audit == [tuple(row) for row in current_prefix]
    old_manifests = old.execute('SELECT * FROM manifests ORDER BY path').fetchall()
    for row in old_manifests:
        actual = db.execute('SELECT * FROM manifests WHERE path=?', (row[0],)).fetchone()
        assert tuple(actual) == row
    new_audit = [dict(row) for row in db.execute('SELECT * FROM audit WHERE seq>? ORDER BY seq', (before['audit_head_before']['seq'],))]
    for row in new_audit:
        row['payload'] = json.loads(row['payload'])
    sessions = [row for row in new_audit if row['kind'] == 'SESSION']
    gaps = [row for row in new_audit if row['kind'] == 'RESTART_GAP']
    assert len(sessions) == 1 and len(gaps) == 1
    assert sessions[0]['payload']['session'] == micro['checkpoint']['session']
    assert sessions[0]['payload']['source_sha256'] == micro['binding']['implementation_sha256']
    assert gaps[0]['payload']['start_us'] == before['microstructure_before']['checkpoint']['asof_us']
    assert gaps[0]['payload']['uncommitted_tail_unknown'] is True
    assert not any(row['kind'] in ('CLOCK_INCIDENT', 'STOP') for row in new_audit)
    assert micro['checkpoint']['asof_us'] > gaps[0]['payload']['end_us']
    assert micro['checkpoint']['accepted_events'] > 0
    snapshot_head = dict(db.execute('SELECT seq,received_us,kind,sha256 FROM audit ORDER BY seq DESC LIMIT 1').fetchone())
    assert snapshot_head['sha256'] == head_sha
finally:
    old.close()
    db.close()

manifests = json.loads((OUT/'MANIFESTS_BEFORE.json').read_text())
for row in manifests:
    path = Path(micro['binding']['store'])/row['path']
    assert path.stat().st_size == row['bytes'] and file_sha(path) == row['sha256'], str(path)
stderr = OUT/'microstructure-recovery.stderr.log'
assert stderr.stat().st_size == 0, stderr.read_text()
assert identity(task['pid']) == process
receipt = {'status': 'PUBLIC_L1_RECOVERED_NEW_SESSION_SOURCE_PREFIX_VERIFIED',
           'created_utc': datetime.now(UTC).isoformat(),
           'preservation_path': str(OUT/'PRESERVATION.json'), 'preservation_sha256': file_sha(OUT/'PRESERVATION.json'),
           'helper_path': str(Path(__file__).resolve()), 'helper_sha256': file_sha(Path(__file__)),
           'restart_wrapper_path': str(ROOT/'.cache/v8_restart_l1_20261002_v2.sh'),
           'restart_wrapper_sha256': file_sha(ROOT/'.cache/v8_restart_l1_20261002_v2.sh'),
           'process': process, 'original_exit_code': before['original_task']['exit_code'],
           'cause': before['exit_cause'], 'original_clock_incident': before['recent_clock_incidents'][0],
           'old_checkpoint': before['microstructure_before']['checkpoint'],
           'old_audit_head': before['audit_head_before'], 'snapshot_audit_head': snapshot_head,
           'exact_old_audit_prefix_rows': len(old_audit), 'exact_old_manifest_prefix_rows': len(old_manifests),
           'old_feature_actual_sha256_verified_again': True,
           'new_session_audit': sessions[0], 'restart_gap_audit': gaps[0],
           'restart_gap_seconds': (gaps[0]['payload']['end_us']-gaps[0]['payload']['start_us'])/1_000_000,
           'microstructure': micro, 'new_task': task,
           'other_processes_unchanged': before['unchanged_other_processes'],
           'prelaunch_disk': before['disk'], 'disk_measurement_is_prelaunch_not_current': True,
           'resources': resources.status(),
           'frozen_source_changed': False, 'source_version_switch': False, 'healthy_gap_splicing': False,
           'collector_restart_only': True, 'real_time_days_certified': 0,
           'alpha_eligible': False, 'qualified_candidate': 'NONE', 'locked_consumed': False,
           'orders_sent': 0, 'gpu_hours': 0}
for target in [OUT/'RECOVERY_ACCEPTANCE.json', ROOT/'reports/fast_research/V8_L1_CLOCK_INCIDENT_RECOVERY_20261002_V2.json']:
    with target.open('x') as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False, allow_nan=False)
print(json.dumps({'status': receipt['status'], 'pid': process['pid'],
                  'new_session': micro['checkpoint']['session'], 'gap_seconds': receipt['restart_gap_seconds'],
                  'old_audit_rows': len(old_audit), 'old_feature_rows': len(old_manifests),
                  'accepted_events': micro['checkpoint']['accepted_events'],
                  'checkpoint_us': micro['checkpoint']['asof_us']}, ensure_ascii=False), flush=True)
