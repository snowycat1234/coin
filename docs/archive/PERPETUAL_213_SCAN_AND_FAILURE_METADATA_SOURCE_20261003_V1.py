"""Publish an actual completed scan and export only closed D043 failed-task metadata."""
import hashlib,json,os
from datetime import datetime
from pathlib import Path
r=Path('/mnt/d/codex/coin');s=Path('/home/xflops/coin-state/task-progress')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
archive='docs/archive/PERPETUAL_213_SCAN_AND_FAILURE_METADATA_SOURCE_20261003_V1.py'
assert Path(__file__).read_bytes()==(r/archive).read_bytes()
p=r/'reports/fast_research/PERPETUAL_213_RESEARCH_ACTUAL_20261003_V1.json'
assert sha(p)=='d0e3488de09f89fa78aed06539fd1b77c32df3d4d1af8db9a1aab245d665a105'
v=json.loads(p.read_bytes());t=json.loads((s/('task-'+v['binding']['task_id']+'.json')).read_bytes())
assert t['status']=='completed' and t['exit_code']==0
d=v['disk'];assert d['status']=='OK' and d['total_bytes']==d['project_bytes']+d['wsl_vhd_bytes']
target=s/'last-disk.json';measured=datetime.fromisoformat(d['scan_finished_utc']).timestamp()
assert measured>json.loads(target.read_bytes())['measured_at']
(s/'last-disk-before-d043-213-20261003.json').write_bytes(target.read_bytes())
temp=s/'last-disk-d043-213-20261003.tmp'
with temp.open('x') as f:json.dump(dict(ledger=d,measured_at=measured),f)
os.replace(temp,target)
folder=r/'docs/archive/PERPETUAL_213_USED_ACTUAL_METADATA_20261003_V1';folder.mkdir(exist_ok=True)
failures={}
for path in s.glob('task-*.json'):
    task=json.loads(path.read_bytes())
    if task.get('title','').startswith('D043') and task.get('status')=='failed':
        assert task['exit_code']==1
        dest=folder/('FAILED_TASK_'+task['id']+'.json')
        with dest.open('xb') as f:f.write(path.read_bytes())
        failures[task['id']]=dict(path=dest.relative_to(r).as_posix(),sha256=sha(dest),title=task['title'])
out=r/'reports/fast_research/PERPETUAL_213_METADATA_FAILURES_AND_SCAN_20261003_V1.json'
value=dict(status='ACTUAL_D043_SAVED_SCAN_AND_FAILED_METADATA_NOT_RESEARCH',failures=failures,
    actual_scan=d,measurement_before_subsequent_outputs=True,new_scan=False,market_report_sha256=sha(p),
    helper_sha256=sha(__file__),created_utc=datetime.now().astimezone().isoformat())
with out.open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps(value,ensure_ascii=False))
