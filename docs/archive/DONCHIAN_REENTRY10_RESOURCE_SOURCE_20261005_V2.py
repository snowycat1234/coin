"""One existing physical guard scan after D070; no resource observer."""
import hashlib,json,os,resource,time
from pathlib import Path
from datetime import UTC,datetime
from quant import disk,resources
from quant.paths import ROOT,STATE
assert os.environ['COIN_TASK_ID']
start=time.monotonic()
actual=json.loads((ROOT/'reports/fast_research/DONCHIAN_REENTRY10_20261005_V3.json').read_bytes())
ledger=disk.check(0);ledger['measured_utc']=datetime.now(UTC).isoformat()
owned=sum(p.stat().st_size for d in STATE.glob('d070-*') if d.is_dir() for p in d.rglob('*') if p.is_file())
assert owned<800000000
value=dict(status='PASS_EXISTING_PHYSICAL_DISK_GUARD_NOT_ECONOMIC_PROOF',task_id=os.environ['COIN_TASK_ID'],ledger=ledger,before_account=actual['disk_before'],
    interval_total_growth_bytes=ledger['total_bytes']-actual['disk_before']['total_bytes'],owned_d070_STATE_bytes=owned,
    growth_scope='Whole ROOT and entire D WSL VHD includes collectors/Git; not exclusive D070',elapsed_seconds=time.monotonic()-start,
    process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,shared_resources=resources.status(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),orders_sent=0,locked_consumed=False)
out=ROOT/'reports/DONCHIAN_REENTRY10_RESOURCE_20261005_V2.json'
with out.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
published=dict(ledger=ledger,measured_at=datetime.fromisoformat(ledger['measured_utc']).timestamp(),source='D070 actual existing disk.check after accounts and financial comparison before Git')
temp=STATE/'task-progress/d070-final-disk.tmp';temp.write_text(json.dumps(published,indent=2)+'\n');temp.replace(STATE/'task-progress/last-disk.json')
print(json.dumps(dict(ledger=ledger,owned_d070_STATE_bytes=owned)))
