import hashlib,json,os
from datetime import datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state/task-progress')
p=root/'reports/fast_research/PERPETUAL_2H_WARMUP_SOURCE_ACTUAL_20261003_V1.json'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='bca7be979b1548583a31138b49732cc6fcdccb692ea340c585e85038b33dadfd'
r=json.loads(p.read_bytes());d=r['disk'];t=json.loads((state/('task-'+r['binding']['task_id']+'.json')).read_bytes())
assert t['status']=='completed' and t['exit_code']==0 and r['actual_files']==r['required_files']==2
assert d['status']=='OK' and d['total_bytes']==d['project_bytes']+d['wsl_vhd_bytes']
measured=datetime.fromisoformat(d['scan_finished_utc']).timestamp();target=state/'last-disk.json'
assert measured>json.loads(target.read_bytes())['measured_at']
with (state/'last-disk-before-d041-july-source-20261003.json').open('xb') as f:f.write(target.read_bytes())
temp=state/'last-disk-d041-july-source-20261003.tmp'
with temp.open('x') as f:json.dump(dict(ledger=d,measured_at=measured),f)
os.replace(temp,target)
print(json.dumps(dict(total_bytes=d['total_bytes'],actual_scan_finished=d['scan_finished_utc'],subsequent_outputs_not_in_scan=True,new_scan=False)))
