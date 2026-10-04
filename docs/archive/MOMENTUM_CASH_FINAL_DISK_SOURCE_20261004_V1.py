"""One final call to the existing physical-file guard; no market work."""
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import time
from quant import disk, resources

root = Path('/mnt/d/codex/coin')
state = Path('/home/xflops/coin-state')
assert os.environ.get('COIN_TASK_ID')
run = state/'d057-final-resource-scan-20261004-v1'
run.mkdir()
started = time.monotonic()
print(json.dumps(dict(phase='模块结束原磁盘守卫扫描；总量未知', completed=None,
                      total=None, unit='扫描'), ensure_ascii=False), flush=True)
before = json.loads((root/'reports/fast_research/MOMENTUM_CASH_SEPNOV91_20261004_V1.json').read_bytes())['disk_before']
value = disk.check(0)
value['measured_utc'] = datetime.now(UTC).isoformat()
report = dict(status='PASS_EXISTING_FINAL_PHYSICAL_FILE_GUARD_NOT_MARKET_REPLAY',
    task_id=os.environ['COIN_TASK_ID'], ledger=value, before_first_account=before,
    interval_total_growth_bytes=value['total_bytes']-before['total_bytes'],
    growth_scope='Whole ROOT plus entire D WSL VHD interval, includes collectors and Git; not exclusively account outputs',
    elapsed_seconds=time.monotonic()-started,
    process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    shared_resources=resources.status(), market_accounts=0, financial_calls=0,
    model_fits=0, orders_sent=0, locked_consumed=False,
    disk_source_sha256=hashlib.sha256((root/'src/quant/disk.py').read_bytes()).hexdigest())
with (run/'ACTUAL_FINAL_DISK.json').open('x') as stream:
    json.dump(report, stream, indent=2); stream.write('\n')
published = dict(ledger=value, measured_at=datetime.fromisoformat(value['measured_utc']).timestamp(),
                 source='D057 actual final existing disk.check, after eight main and financial accounts, before module Git')
temp = state/'task-progress/d057-final-disk.tmp'
temp.write_text(json.dumps(published, indent=2)+'\n')
temp.replace(state/'task-progress/last-disk.json')
print(json.dumps(dict(status=report['status'], ledger=value,
                     interval_total_growth_bytes=report['interval_total_growth_bytes'],
                     elapsed_seconds=report['elapsed_seconds'])), flush=True)
