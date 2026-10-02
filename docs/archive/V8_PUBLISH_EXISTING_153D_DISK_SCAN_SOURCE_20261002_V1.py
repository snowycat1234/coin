"""Publish the accepted existing source scan; no disk walk or observer change."""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

root = Path('/mnt/d/codex/coin')
state = Path('/home/xflops/coin-state/task-progress')
source = root/'reports/fast_research/V8_SHARED_SOURCE_VIEW_153D_20261002_V1.json'
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_sha == 'dd931ce79f7f78e7e2c070f553077ffeca4ed73d7c0c0a1c744e4288d68f05cf'
receipt = json.loads(source.read_text())
ledger = receipt['disk']
assert receipt['status'] == 'PASS_SHARED_V8_SOURCE_VIEW_153D' and ledger['status'] == 'OK'
assert ledger['total_bytes'] == ledger['project_bytes'] + ledger['wsl_vhd_bytes'] == 19_355_135_811
assert ledger['measured_utc'] == '2026-10-02T09:40:54.517503+00:00'
measured = datetime.fromisoformat(ledger['measured_utc']).timestamp()
target = state/'last-disk.json'
old = target.read_bytes()
previous = json.loads(old)
assert measured > previous['measured_at'], 'Do not replace a newer disk scan'
archive = state/'last-disk-before-153d-source-scan-v8-20261002-v1.json'
with archive.open('xb') as stream:
    stream.write(old)
temporary = state/'last-disk-from-accepted-153d-source-scan-v8-v1.tmp'
with temporary.open('x') as stream:
    json.dump({'ledger': ledger, 'measured_at': measured}, stream)
os.replace(temporary, target)
proof = {'status': 'PUBLISHED_PREEXISTING_ACCEPTED_153D_SOURCE_DISK_SCAN',
         'source_receipt_path': str(source.relative_to(root)), 'source_receipt_sha256': source_sha,
         'measured_utc': ledger['measured_utc'], 'total_bytes': ledger['total_bytes'],
         'new_scan_executed': False, 'measurement_timestamp_not_publication_timestamp': True,
         'disk_guard_changed': False, 'observer_changed': False,
         'prior_display_record_path': str(archive), 'prior_display_record_sha256': hashlib.sha256(old).hexdigest(),
         'published_record_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
         'publisher_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
with (root/'reports/fast_research/V8_PROGRESS_DISK_RECORD_UPDATE_153D_20261002_V1.json').open('x') as stream:
    json.dump(proof, stream, indent=2)
    stream.write('\n')
print(json.dumps(proof), flush=True)
