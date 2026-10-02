"""One actual fault and stop/restart check of the bounded, local viewer only."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen

from quant.resources import status

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state/v7-task-window-bounded-restoration-20261002-v1')
UNIT = 'coin-task-progress-window-v7-v3.service'
WRAPPER = ROOT / '.cache/serve_task_progress_v2.py'
EXPECTED_CMD = f'/usr/bin/python3 {WRAPPER} '


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(*args):
    result = subprocess.run(['systemctl', '--user', *args], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, (args, result.stderr)
    return result.stdout.strip()


def unit_state():
    fields = ['MainPID', 'NRestarts', 'ActiveState', 'SubState', 'Slice', 'KillMode', 'Restart', 'MemorySwapMax', 'UnitFileState']
    output = command('show', UNIT, *[f'--property={name}' for name in fields])
    return dict(line.split('=', 1) for line in output.splitlines())


def process(pid):
    base = Path('/proc') / str(pid)
    return {'pid': pid, 'start_ticks': int((base/'stat').read_text().split(') ', 1)[1].split()[19]),
            'command': (base/'cmdline').read_bytes().replace(b'\0', b' ').decode(),
            'cgroup': (base/'cgroup').read_text().strip()}


def api(name):
    with urlopen('http://localhost:8765/api/status', timeout=3) as response:
        assert response.status == 200
        body = response.read(2_000_000)
    value = json.loads(body)
    assert time.time() - value['generated_at'] < 8
    assert value['resources']['ram_limit_bytes'] <= 5_000_000_000
    path = STATE/name
    path.write_bytes(body)
    return {'path': str(path), 'sha256': digest(path), 'bytes': len(body), 'generated_at': value['generated_at']}


def healthy(name, different_from=None):
    deadline = time.monotonic()+35
    while time.monotonic()<deadline:
        state = unit_state()
        pid = int(state['MainPID'])
        try:
            info = process(pid)
            if state['ActiveState']=='active' and pid!=different_from and info['command']==EXPECTED_CMD:
                assert 'coin-quant.slice/run-' in info['cgroup'] and info['cgroup'].endswith('.scope')
                return {'unit': state, 'process': info, 'api': api(name)}
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(.5)
    raise RuntimeError('Bounded viewer failed to become healthy')


accepted = json.loads((ROOT/'reports/fast_research/TASK_PROGRESS_FR69_V2_ROOT_ACCEPTANCE_20261002.json').read_text())
verified = {}
for name in ['scripts/task_progress_window.py', 'scripts/task_progress_run.py', 'tools/task_progress/index.html', 'docs/archive/TASK_PROGRESS_RESTART_WRAPPER_20261002_V2.py']:
    assert digest(ROOT/name)==accepted['source_hashes'][name]
    verified[name]=digest(ROOT/name)
assert digest(WRAPPER)==verified['docs/archive/TASK_PROGRESS_RESTART_WRAPPER_20261002_V2.py']
old_recovery = json.loads((ROOT/'reports/fast_research/V6_EXISTING_RUNTIME_RECOVERY_20261001_V2.json').read_text())
for name in ['scripts/bounded.sh', 'scripts/env.sh', 'src/quant/resources.py']:
    assert digest(ROOT/name)==old_recovery['public_v3']['contract']['sources'][name]
    verified[name]=digest(ROOT/name)
source = ROOT/'scripts/systemd'/UNIT
installed = Path('/home/xflops/.config/systemd/user')/UNIT
assert source.read_bytes()==installed.read_bytes()
collectors_before={pid:process(pid) for pid in [746,776]}
before=healthy('API_BEFORE_FAULT.json')
oldpid=before['process']['pid']
fault_start=time.monotonic()
command('kill','--kill-whom=main','--signal=SIGKILL',UNIT)
after_fault=healthy('API_AFTER_AUTO_RESTART.json',different_from=oldpid)
fault_elapsed=time.monotonic()-fault_start
assert int(after_fault['unit']['NRestarts'])==int(before['unit']['NRestarts'])+1
assert not Path('/proc',str(oldpid)).exists()
stop_pid=after_fault['process']['pid']
command('stop',UNIT)
assert unit_state()['ActiveState']=='inactive'
assert not Path('/proc',str(stop_pid)).exists()
try:
    with urlopen('http://localhost:8765/api/status',timeout=2):
        raise AssertionError('A window process survived the owned service stop')
except OSError:
    pass
command('start',UNIT)
after_stop=healthy('API_AFTER_EXPLICIT_STOP_START.json',different_from=stop_pid)
assert after_stop['unit']['UnitFileState']=='enabled'
assert after_stop['unit']['Slice']=='coin-quant.slice'
assert after_stop['unit']['KillMode']=='mixed' and after_stop['unit']['MemorySwapMax']=='0'
collectors_after={pid:process(pid) for pid in collectors_before}
assert collectors_before==collectors_after
verified[str(WRAPPER.relative_to(ROOT))]=digest(WRAPPER)
verified[str(source.relative_to(ROOT))]=digest(source)
verified[str(Path(__file__).relative_to(ROOT))]=digest(Path(__file__))
initial_error=Path('/home/xflops/coin-state/v7-task-window-restoration-20261002-v1/STDERR.log')
assert 'RuntimeError: Use the D-hosted hpc_linux distro' in initial_error.read_text()
report={'status':'BOUNDED_LOCAL_WINDOW_SERVICE_ACTUAL_FAULT_RECOVERY_ACCEPTED',
        'created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'unit':UNIT,'installed_unit':str(installed),
        'source_hashes':verified,'before_fault':before,'after_actual_viewer_SIGKILL':after_fault,
        'fault_to_healthy_seconds':fault_elapsed,'explicit_stop_left_no_viewer_or_port_listener':True,
        'after_explicit_stop_start':after_stop,'collectors_before':collectors_before,'collectors_after':collectors_after,
        'collector_PIDs_start_ticks_commands_unchanged':True,'resources':status(),
        'initial_missing_WSL_environment_failure_preserved':{'path':str(initial_error),'sha256':digest(initial_error)},
        'logs':str(STATE),'viewer_source_unchanged':True,'bounded_source_unchanged':True,
        'WSL_restart_test_performed':False,'qualification_or_alpha_claim':False}
output=ROOT/'reports/fast_research/V7_TASK_WINDOW_BOUNDED_SERVICE_ACCEPTANCE_20261002_V1.json'
with output.open('x') as stream:
    json.dump(report,stream,indent=2,ensure_ascii=False,allow_nan=False)
print(json.dumps({'status':report['status'],'report':str(output),'sha256':digest(output),'MainPID':after_stop['process']['pid'],'fault_to_healthy_seconds':fault_elapsed}),flush=True)
