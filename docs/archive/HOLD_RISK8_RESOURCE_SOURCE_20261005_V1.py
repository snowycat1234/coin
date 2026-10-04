"""Publish one actual existing disk guard scan, with its timestamp."""
import hashlib,json,os,resource,time
from datetime import UTC,datetime
from pathlib import Path
from quant import disk,resources
from quant.paths import ROOT,STATE
assert os.environ['COIN_TASK_ID']
start=time.monotonic()
actual=json.loads((ROOT/'reports/fast_research/HOLD_RISK8_20261005_V1.json').read_bytes())
ledger=disk.check(0);ledger['measured_utc']=datetime.now(UTC).isoformat()
owned=sum(p.stat().st_size for d in STATE.glob('d071-*') if d.is_dir() for p in d.rglob('*') if p.is_file())
assert owned<400000000
value=dict(status='PASS_EXISTING_PHYSICAL_DISK_GUARD_NOT_ECONOMIC_PROOF',task_id=os.environ['COIN_TASK_ID'],ledger=ledger,before_account=actual['disk_before'],
    interval_total_growth_bytes=ledger['total_bytes']-actual['disk_before']['total_bytes'],owned_D071_STATE_bytes=owned,
    growth_scope='Whole ROOT and entire D WSL VHD includes collectors/Git; not exclusive D071',elapsed_seconds=time.monotonic()-start,
    process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,shared_resources=resources.status(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
out=ROOT/'reports/HOLD_RISK8_RESOURCE_20261005_V1.json'
with out.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
published=dict(ledger=ledger,measured_at=datetime.fromisoformat(ledger['measured_utc']).timestamp(),source='D071 existing guard after accounts/finance before Git')
temp=STATE/'task-progress/d071-final-disk.tmp';temp.write_text(json.dumps(published,indent=2)+'\n');temp.replace(STATE/'task-progress/last-disk.json')
print(json.dumps(dict(ledger=ledger,owned_D071_STATE_bytes=owned)))
