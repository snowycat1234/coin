"""Reuse the actual finished D035 capacity scan for the existing window."""
import hashlib,json,os
from datetime import datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state/task-progress')
source=root/'reports/fast_research/VOL_MANAGED_HOLD_90D_ACTUAL_20261003_V1.json'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='0bf3fbf2d1145506fed5ab8c3d95d7a7235a176ec0aa975629235b504dc98ca5'
r=json.loads(source.read_bytes());d=r['disk'];task=json.loads((state/('task-'+r['binding']['task_id']+'.json')).read_bytes())
assert r['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and task['status']=='completed' and task['exit_code']==0
assert d['status']=='OK' and d['total_bytes']==d['project_bytes']+d['wsl_vhd_bytes']
measured=datetime.fromisoformat(d['scan_finished_utc']).timestamp();target=state/'last-disk.json';old=target.read_bytes()
assert measured>json.loads(old)['measured_at']
with (state/'last-disk-before-d035-20261003-v1.json').open('xb') as f:f.write(old)
tmp=state/'last-disk-d035-actual-20261003-v1.tmp'
with tmp.open('x') as f:json.dump(dict(ledger=d,measured_at=measured),f)
os.replace(tmp,target)
proof=dict(status='PUBLISHED_ACTUAL_D035_COMPLETED_SCAN_WITH_ORIGINAL_TIME',source_receipt=str(source.relative_to(root)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),measured_at=measured,ledger=d,new_scan_executed=False,disk_guard_changed=False,subsequent_outputs_not_in_this_prior_scan=True)
with (root/'reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_PROGRESS_SCAN_PUBLISHED_20261003_V1.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(proof))
