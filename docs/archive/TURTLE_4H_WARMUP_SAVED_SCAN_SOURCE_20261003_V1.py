"""Publish only the completed producer's real disk scan, without rescanning."""
import hashlib,json,os
from datetime import datetime
from pathlib import Path
r=Path('/mnt/d/codex/coin');s=Path('/home/xflops/coin-state/task-progress')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
archive='docs/archive/TURTLE_4H_WARMUP_SAVED_SCAN_SOURCE_20261003_V1.py'
assert Path(__file__).read_bytes()==(r/archive).read_bytes()
p=r/'reports/fast_research/TURTLE_4H_WARMUP_SOURCE_ACTUAL_20261003_V1.json'
v=json.loads(p.read_bytes());t=json.loads((s/('task-'+v['binding']['task_id']+'.json')).read_bytes())
assert v['status']=='PASS_D047_OFFICIAL_PERPETUAL_4H_WARMUP_FORMAT_CALENDAR_PENDING_INDEPENDENT_QA'
assert t['status']=='completed' and t['exit_code']==0
d=v['disk'];assert d['status']=='OK' and d['total_bytes']==d['project_bytes']+d['wsl_vhd_bytes']
target=s/'last-disk.json';measured=datetime.fromisoformat(d['scan_finished_utc']).timestamp()
assert measured>json.loads(target.read_bytes())['measured_at']
with (s/'last-disk-before-d047-warmup-20261003.json').open('xb') as f:f.write(target.read_bytes())
temp=s/'last-disk-d047-warmup-20261003.tmp'
with temp.open('x') as f:json.dump(dict(ledger=d,measured_at=measured),f)
os.replace(temp,target)
value=dict(status='ACTUAL_D047_WARMUP_SAVED_SCAN_NOT_NEW_SCAN_OR_ECONOMIC_ACCEPTANCE',
    actual_scan=d,measurement_before_subsequent_outputs=True,new_scan=False,
    market_report_sha256=sha(p),market_task_id=t['id'],helper_sha256=sha(__file__),
    created_utc=datetime.now().astimezone().isoformat())
out=r/'reports/fast_research/TURTLE_4H_WARMUP_SAVED_SCAN_20261003_V1.json'
with out.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
print(json.dumps(dict(status=value['status'],scan=d['total_bytes'],scan_finished_utc=d['scan_finished_utc'])))
