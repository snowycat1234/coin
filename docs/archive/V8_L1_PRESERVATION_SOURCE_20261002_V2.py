"""Preserve a terminated L1 clock incident before unchanged-source restart."""
import json
import shutil
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path

from quant import disk, resources
from quant.paths import ROOT, STATE
from quant.microstructure import read_microstructure_status
from quant.research_fast.dataset import file_sha

OUT = STATE / 'v8-l1-clock-preservation-20261002-v2'
OLD = STATE / 'v7-runtime-preservation-20261002-v3'

def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)

def identity(pid):
    path = Path('/proc') / str(pid)
    return {'pid': pid, 'command': (path/'cmdline').read_bytes().replace(b'\0', b' ').decode(),
            'start_ticks': int((path/'stat').read_text().split(') ', 1)[1].split()[19]),
            'cgroup': (path/'cgroup').read_text().strip()}

assert not Path('/proc/523').exists(), 'Original L1 PID still exists'
other = [identity(540), identity(384)]
assert 'quant.collector_public_v3 --run' in other[0]['command']
assert 'serve_task_progress_v2.py' in other[1]['command']
for path in Path('/proc').iterdir():
    if not path.name.isdecimal():
        continue
    try:
        command = (path/'cmdline').read_bytes().replace(b'\0', b' ').decode()
    except (OSError, UnicodeError):
        continue
    assert ' -m quant.microstructure --run' not in command, f'Another L1 process exists: {path.name}'

OUT.mkdir()
failed_tasks = [json.loads(path.read_text()) for path in (STATE/'task-progress').glob('task-*.json')]
failed_tasks = [value for value in failed_tasks if value.get('title') == 'V8 L1时钟停止留证与独立闭合备份']
assert len(failed_tasks) == 1 and failed_tasks[0]['status'] == 'failed' and failed_tasks[0]['exit_code'] == 1
first_failure = {'status': 'FIRST_ATTEMPT_FAILED_PRESERVED',
                 'error': 'FileExistsError: copied old PRESERVATION.json collided with exclusive new receipt filename.',
                 'directory': str(STATE/'v8-l1-clock-preservation-20261002-v1'),
                 'task': failed_tasks[0],
                 'source_path': str(ROOT/'.cache/v8_preserve_l1_clock_20261002_v1.py'),
                 'source_sha256': file_sha(ROOT/'.cache/v8_preserve_l1_clock_20261002_v1.py'),
                 'old_same_name_receipt_does_not_authorize_restart': True}
save(OUT/'FIRST_ATTEMPT_FAILURE.json', first_failure)
saved = []
task = STATE/'task-progress/task-e3873ec320e641c38dd7b33129046c34.json'
old_task = json.loads(task.read_text())
assert old_task['pid'] == 523 and old_task['exit_code'] == 1 and old_task['status'] == 'failed'
for path in [task, OLD/'microstructure-new.stderr.log', OLD/'microstructure-new.stdout.log',
             OLD/'PRESERVATION.json']:
    target = OUT/('previous-PRESERVATION.json' if path.name == 'PRESERVATION.json' else path.name)
    with target.open('xb') as stream:
        stream.write(path.read_bytes())
    assert file_sha(path) == file_sha(target)
    saved.append({'source': str(path), 'saved': str(target), 'sha256': file_sha(target),
                  'bytes': target.stat().st_size})
assert 'Receipt clock incident requires restart' in (OUT/'microstructure-new.stderr.log').read_text()

source = sqlite3.connect(f'file:{STATE/"microstructure.sqlite3"}?mode=ro', uri=True)
target = OUT/'microstructure.sqlite3'
assert not target.exists()
destination = sqlite3.connect(target)
try:
    source.backup(destination, pages=256)
    destination.commit()
    assert destination.execute('PRAGMA quick_check').fetchall() == [('ok',)]
    assert destination.execute('PRAGMA journal_mode=DELETE').fetchone()[0] == 'delete'
finally:
    source.close()
    destination.close()

micro = read_microstructure_status(target)
expected = json.loads((ROOT/'reports/fast_research/V7_PUBLIC_COLLECTOR_RECOVERY_20261002_V1.json').read_text())
assert micro['state'] == 'STOPPED' and micro['last_audit']['payload']['fatal'] == 'CLOCK_INCIDENT'
assert micro['binding'] == expected['microstructure']['binding']
assert micro['binding']['implementation_sha256'] == file_sha(ROOT/'src/quant/microstructure.py')
db = sqlite3.connect(f'file:{target}?mode=ro&immutable=1', uri=True)
db.row_factory = sqlite3.Row
try:
    head = dict(db.execute('SELECT seq,received_us,kind,sha256 FROM audit ORDER BY seq DESC LIMIT 1').fetchone())
    checkpoint_raw = db.execute("SELECT value FROM state WHERE key='checkpoint'").fetchone()[0]
    incidents = [dict(row) for row in db.execute("SELECT * FROM audit WHERE kind='CLOCK_INCIDENT' ORDER BY seq DESC LIMIT 2")]
    tail = [dict(row) for row in db.execute('SELECT * FROM audit ORDER BY seq DESC LIMIT 6')]
    manifests = [dict(row) for row in db.execute('SELECT * FROM manifests ORDER BY path')]
    sessions = [dict(row) for row in db.execute("SELECT * FROM audit WHERE kind='SESSION' ORDER BY seq DESC LIMIT 2")]
    for rows in (incidents, tail, sessions):
        for row in rows:
            row['payload'] = json.loads(row['payload'])
finally:
    db.close()
assert incidents and incidents[0]['seq'] < head['seq']
assert head['sha256'] == micro['audit_head']
for row in manifests:
    path = Path(micro['binding']['store']) / row['path']
    assert path.stat().st_size == row['bytes'] and file_sha(path) == row['sha256'], str(path)
save(OUT/'MANIFESTS_BEFORE.json', manifests)
save(OUT/'CHECKPOINT_BEFORE.json', json.loads(checkpoint_raw))

scan_start = time.monotonic()
ledger = disk.check(1_000_000_000)
ledger.update(measured_utc=datetime.now(UTC).isoformat(), elapsed_seconds=time.monotonic()-scan_start)
assert ledger['total_bytes'] + 1_000_000_000 < 36_000_000_000
assert other == [identity(540), identity(384)]
receipt = {'status': 'L1_CLOCK_INCIDENT_PRESERVED_BEFORE_RESTART',
           'created_utc': datetime.now(UTC).isoformat(),
           'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
           'original_task': old_task, 'saved_files': saved,
           'first_attempt_failure': first_failure,
           'helper_path': str(Path(__file__).resolve()), 'helper_sha256': file_sha(Path(__file__)),
           'closed_backup': {'path': str(target), 'sha256': file_sha(target), 'bytes': target.stat().st_size,
                             'closed': True, 'journal_mode': 'delete', 'quick_check': 'ok', 'audit_chain': 'verified'},
           'microstructure_before': micro, 'audit_head_before': head, 'recent_clock_incidents': incidents,
           'audit_tail_before': tail, 'recent_sessions': sessions,
           'manifest_count': len(manifests), 'manifest_actual_files_verified': True,
           'manifest_prefix_path': str(OUT/'MANIFESTS_BEFORE.json'),
           'manifest_prefix_sha256': file_sha(OUT/'MANIFESTS_BEFORE.json'),
           'checkpoint_path': str(OUT/'CHECKPOINT_BEFORE.json'),
           'checkpoint_sha256': file_sha(OUT/'CHECKPOINT_BEFORE.json'),
           'unchanged_other_processes': other, 'disk': ledger, 'resources': resources.status(),
           'exit_cause': 'Actual exit 1; CLOCK_INCIDENT audit and Receipt clock incident requires restart traceback.',
           'clock_guard': 'Absolute wall/monotonic increment divergence exceeded 1 second; monotonic increment was not persisted, magnitude unknown.',
           'collector_source_changed': False, 'source_version_switch': False,
           'healthy_gap_splicing': False, 'locked_consumed': False, 'orders_sent': 0, 'gpu_hours': 0}
save(OUT/'PRESERVATION.json', receipt)
save(ROOT/'reports/fast_research/V8_L1_CLOCK_INCIDENT_PRESERVATION_20261002_V2.json',
     {**receipt, 'preservation_path': str(OUT/'PRESERVATION.json'),
      'preservation_sha256': file_sha(OUT/'PRESERVATION.json')})
print(json.dumps({'status': receipt['status'], 'head': head, 'disk_total_bytes': ledger['total_bytes'],
                  'checkpoint': micro['checkpoint']['asof_us'], 'latest_incident': incidents[0]}, ensure_ascii=False), flush=True)
