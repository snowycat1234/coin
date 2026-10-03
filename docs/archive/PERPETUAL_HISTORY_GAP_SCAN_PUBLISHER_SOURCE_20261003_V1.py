import hashlib,json,os
from datetime import datetime
from pathlib import Path
r=Path('/mnt/d/codex/coin');s=Path('/home/xflops/coin-state/task-progress')
p=r/'reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='82cae26a2313417c59e6a63af8458d775851e7c1e341d51bc9e7fa9a2cf6c427'
v=json.loads(p.read_bytes());t=json.loads((s/('task-'+v['binding']['task_id']+'.json')).read_bytes())
assert t['status']=='failed' and t['exit_code']==1 and v['status']=='FAIL_D042_HISTORY_SOURCE'
d=v['disk'];assert d['status']=='OK' and d['total_bytes']==d['project_bytes']+d['wsl_vhd_bytes']
measured=datetime.fromisoformat(d['scan_finished_utc']).timestamp();target=s/'last-disk.json'
assert measured>json.loads(target.read_bytes())['measured_at']
(s/'last-disk-before-d042-gap-20261003.json').write_bytes(target.read_bytes())
temp=s/'last-disk-d042-gap-20261003.tmp'
with temp.open('x') as f:json.dump(dict(ledger=d,measured_at=measured),f)
os.replace(temp,target)
print(json.dumps(dict(total_bytes=d['total_bytes'],actual_scan_finished=d['scan_finished_utc'],
    measurement_before_subsequent_source_outputs=True,new_scan=False,source_qualification=False)))
