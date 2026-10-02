import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

root = Path('/mnt/d/codex/coin')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
name = 'reports/fast_research/PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_AUDIT_EXIT_AND_CODE_BINDING_20261002_V1.json'
assert sha(root / name) == '750879fb9cea3e8c96bd3bfbdf65bd59465eb9a5091fb090403cc2841e977cc3'
v = json.loads((root / name).read_text())
assert v['actual_auditor_host_session_id'] == 95966
assert v['actual_auditor_task']['status'] == 'completed' and v['actual_auditor_task']['exit_code'] == 0
assert v['completed_ledgers_verified'] == 6 and v['financial_block_bytes_identical']
assert sha(root / v['checker_archive_path']) == v['checker_archive_sha256']
assert sha(root / v['metadata_export_archive_path']) == v['metadata_export_sha256']
previous = 'reports/GITHUB_BYBIT_NATIVE_FEE_SYNC_VERIFIED_20261002_V1.json'
assert sha(root / previous) == 'ca8058d61e7fa4b8ab72e69cac673900fdf2a0461fa2fe04ae0defa953ee8033'
registry_archive = 'docs/archive/OPEN_SOURCE_REGISTRY_PRE_HYBRID_ECONOMICS_20261002.md'
assert sha(root / registry_archive) == 'f77aec85bf0ddf442fe7f1b23c8911c43b5f2784e7fbc5f41b1638086defdb4e'
paths = [name, previous, registry_archive, v['checker_archive_path'], v['metadata_export_archive_path'],
    'docs/archive/HYBRID_BYBIT_PUSH_VERIFICATION_SOURCE_20261002_V1.py']
assert sha(root / paths[-1]) == sha(root / '.cache/hybrid_bybit_push_verification_20261002_v1.py')
failures = []
state = Path('/home/xflops/coin-state/test-hybrid-native-fee-independent-audit-20261002-v1')
for file in ('EXPORT_INVOCATION_FAILURE.json', 'EXPORT_POWERSHELL5_FAILURE.json'):
    p = state / file
    assert p.is_file() and p.stat().st_size < 1000000
    failures.append(dict(path=str(p), sha256=sha(p), original_metadata=json.loads(p.read_text())))
archive = root / 'docs/archive/HYBRID_BYBIT_EXPORT_BINDING_SOURCE_20261002_V1.py'
with archive.open('xb') as f:
    f.write(Path(__file__).read_bytes())
paths.append(str(archive.relative_to(root)))
out = root / 'reports/GITHUB_HYBRID_NATIVE_AUDIT_EXPORT_SOURCE_BINDING_20261002_V1.json'
receipt = dict(status='PASS_EXACT_METADATA_EXPORT_AND_ARCHIVED_CODE_BINDING_NO_FINANCIAL_RERUN',
    created_utc=datetime.now(UTC).isoformat(), source_hashes={p: sha(root / p) for p in paths},
    export_metadata_failures_preserved=failures, market_inputs_read=False, old_tests_or_ledgers_rerun=False,
    helper_source_sha256=sha(__file__))
with out.open('x') as f:
    json.dump(receipt, f, indent=2, ensure_ascii=False, allow_nan=False)
    f.write('\n')
print(json.dumps(dict(status=receipt['status'], output=str(out), sha256=sha(out))))
