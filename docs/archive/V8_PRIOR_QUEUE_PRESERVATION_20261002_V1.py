"""Preserve the running V7 queue before the user's V8 causality gate pause."""
import hashlib
import json
import os
import signal
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
run = STATE / 'v7-family-screen-20261002-v4'
out = STATE / 'v8-prior-family-pause-20261002-v1'
out.mkdir(exist_ok=False)
processes = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit() or int(proc.name) == os.getpid():
        continue
    try:
        argv = (proc / 'cmdline').read_bytes().split(b'\0')
        command = b' '.join(argv).decode(errors='replace')
        is_queue = any(x.endswith(b'/v7_family_screen_queue_20261002_v4.sh') or
                       x == b'.cache/v7_family_screen_queue_20261002_v4.sh' for x in argv)
        is_worker = any(x.endswith(b'/screen_family_models.py') or
                        x == b'scripts/research_v7/screen_family_models.py' for x in argv)
        if not (is_queue or (is_worker and str(run) in command)):
            continue
        start = (proc / 'stat').read_text().rsplit(')', 1)[1].split()[19]
        processes.append({'pid': int(proc.name), 'start_ticks': int(start),
                          'command': command, 'cgroup': (proc / 'cgroup').read_text().strip()})
    except FileNotFoundError:
        pass
for p in processes:
    os.kill(p['pid'], signal.SIGSTOP)

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

artifacts = []
for path in sorted(run.rglob('*')):
    if path.is_file():
        artifacts.append({'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)})
for path in sorted(ROOT.glob('reports/fast_research/V7_UNSEEN_FAMILY_SCREEN_*_20261002_V2.json')):
    artifacts.append({'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)})
log = run / 'queue.log'
if log.exists():
    (out / 'queue.log').write_bytes(log.read_bytes())
receipt = {'status': 'V7_QUEUE_PAUSED_FOR_USER_V8_P1_GATE',
           'created_utc': datetime.now(UTC).isoformat(),
           'reason': 'User V8 prohibits further formal depth research until P1 non-overlap gate.',
           'research_state': 'NO_QUALIFIED_CANDIDATE', 'classification': 'SCREENING',
           'paused_processes': processes, 'preserved_artifacts': artifacts,
           'frozen_sources_modified': False, 'artifacts_deleted': 0,
           'new_oos_results_inspected_by_this_operation': False}
with (out / 'PRESERVATION.json').open('x') as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2)
    f.flush()
    os.fsync(f.fileno())
# Kill only the identified, stopped queue and its model/progress processes.
# Stopping every selected process first prevents the shell from launching the next fold.
for p in processes:
    try:
        live_start = int((Path('/proc') / str(p['pid']) / 'stat').read_text().rsplit(')', 1)[1].split()[19])
        assert live_start == p['start_ticks'], 'PID reuse: refuse to stop'
        os.kill(p['pid'], signal.SIGKILL)
    except FileNotFoundError:
        pass
receipt['stop_signal'] = 'SIGSTOP before preservation; SIGKILL only identified model queue after receipt fsync'
receipt['preservation_path'] = str(out / 'PRESERVATION.json')
receipt['preservation_sha256'] = sha(out / 'PRESERVATION.json')
dest = ROOT / 'reports/fast_research/V8_PRIOR_FAMILY_QUEUE_PAUSE_20261002_V1.json'
with dest.open('x') as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2)
print(json.dumps({'report': str(dest), 'stopped': [p['pid'] for p in processes],
                  'preserved_file_count': len(artifacts)}, ensure_ascii=False), flush=True)
