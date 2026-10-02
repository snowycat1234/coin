import hashlib, json, os, sys
from datetime import datetime
from pathlib import Path
root = Path('/mnt/d/codex/coin')
receipt_path = root / (sys.argv[1] if len(sys.argv)>1 else 'reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_20261002_V3.json')
receipt = json.loads(receipt_path.read_text())
assert receipt_path.resolve().is_relative_to(root/'reports/fast_research')
ledger = receipt['disk']
assert ledger['total_bytes'] == ledger['project_bytes'] + ledger['wsl_vhd_bytes']
stamp = datetime.fromisoformat(ledger['scan_finished_utc']).timestamp()
target = Path('/home/xflops/coin-state/task-progress/last-disk.json')
value = dict(ledger=ledger, measured_at=stamp, source_receipt=str(receipt_path),
    source_receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    scope='Previously completed actual scan, not a new or instantaneous scan')
if not target.exists() or json.loads(target.read_text())['measured_at'] < stamp:
    temporary = target.with_suffix('.publish-tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False))
    os.replace(temporary, target)
print(json.dumps(dict(status='PUBLISHED_COMPLETED_SCAN_TIMESTAMP',total_bytes=ledger['total_bytes'],measured_utc=ledger['scan_finished_utc'])))
