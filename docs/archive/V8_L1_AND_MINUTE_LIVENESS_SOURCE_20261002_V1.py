"""Read-only lifecycle snapshot; no collector restart or quality qualification."""
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from quant.paths import ROOT, STATE
from quant.microstructure import read_microstructure_status
from quant.collector_public_v3 import read_public_v3_status

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def process(pid):
    base = Path('/proc') / str(pid)
    if not base.exists():
        return {'pid': pid, 'live': False}
    fields = (base/'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': pid, 'live': True, 'state': fields[0], 'start_ticks': int(fields[19]),
            'command': (base/'cmdline').read_bytes().replace(b'\0', b' ').decode(),
            'cgroup': (base/'cgroup').read_text()}

task_path = STATE/'task-progress/task-7ed0a9c3456b4d90a947a217d1dd4906.json'
stderr = STATE/'v8-l1-clock-preservation-20261002-v2/microstructure-recovery.stderr.log'
micro = read_microstructure_status()
minute = read_public_v3_status()
db = sqlite3.connect(f'file:{STATE / "microstructure.sqlite3"}?mode=ro', uri=True)
try:
    db.execute('BEGIN')
    db.row_factory = sqlite3.Row
    tail = [dict(row) for row in db.execute('SELECT * FROM audit ORDER BY seq DESC LIMIT 6')]
finally:
    db.close()
task = json.loads(task_path.read_text())
processes = {str(pid): process(pid) for pid in (2453, 540, 384)}
conditions = {
    'original_l1_process_identity': processes['2453']['live'] and processes['2453']['start_ticks'] == 395718,
    'original_l1_task_running': task['status'] == 'running' and task['pid'] == 2453 and task['start_ticks'] == 395718,
    'original_l1_new_session_connected': micro['state'] == 'CONNECTED' and micro['checkpoint']['session'] == '6ba28c2935bc4c858f988ac62cd5a6da',
    'original_l1_source_bytes': sha(ROOT/'src/quant/microstructure.py') == micro['binding']['implementation_sha256'] == '649a69c924cdcfc4e85dca37a2a6c4958993f3f3365e04b3f10372f8875ddbb4',
    'minute_running_source_matches': processes['540']['live'] and minute['state'] == 'RUNNING' and minute['stored_source_matches_current'],
    'restart_stderr_empty': stderr.stat().st_size == 0,
}
report = {'status': 'PASS_READ_ONLY_L1_AND_MINUTE_LIVENESS_SNAPSHOT' if all(conditions.values()) else 'INVESTIGATE_READ_ONLY_LIVENESS_SNAPSHOT',
          'measured_utc': datetime.now(UTC).isoformat(), 'conditions': conditions,
          'processes': processes, 'l1_task_snapshot': task, 'l1_status': micro,
          'l1_audit_tail_snapshot': tail, 'minute_status': minute,
          'script_sha256': sha(Path(__file__)), 'read_only_collector_access': True,
          'collector_restarted': False, 'clock_modified': False, 'healthy_time_spliced': False,
          'qualification': 'NOT_CERTIFIED_BY_THIS_SNAPSHOT', 'alpha_eligible': False,
          'real_time_days_certified': 0, 'model_fits': 0, 'orders_sent': 0}
output = ROOT/'reports/fast_research/V8_L1_AND_MINUTE_LIVENESS_20261002_V1.json'
with output.open('x') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
print(json.dumps({'status': report['status'], 'measured_utc': report['measured_utc'],
                  'l1_session': micro['checkpoint']['session'], 'l1_audit_head': micro['audit_head'],
                  'minute_state': minute['state'], 'conditions': conditions, 'report_sha256': sha(output)}), flush=True)
