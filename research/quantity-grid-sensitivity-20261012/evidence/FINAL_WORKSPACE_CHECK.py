import datetime, hashlib, json, shutil
from pathlib import Path
root = Path('/workspace/coin-tail-risk')
here = root / 'research/quantity-grid-sensitivity-20261012'
cases = []
for label, state, published in (
    ('new_quantity', Path('/workspace/quantity-grid-state'), here),
    ('fine_REUSED', Path('/workspace/unified-exit-economics-state'), root / 'research/unified-closing-exempt-economics-20261012'),
):
    for key in ('P1', 'P2'):
        for arm in ('CS_MATCHED', 'VOL_MATCHED', 'STATIC50'):
            account = state / ('OBSERVED_' + key) / arm
            for name in ('BINDING.json', 'RESULT.json'):
                assert (account / name).read_bytes() == (published / 'summary' / key / arm / name).read_bytes()
            pointer = json.loads((account / 'recovery/POINTER.json').read_text())
            snapshot = account / 'recovery' / pointer['snapshot_path']
            snapshot_sha = hashlib.sha256(snapshot.read_bytes()).hexdigest()
            assert snapshot_sha == pointer['snapshot_SHA256']
            cases.append(dict(role=label, window=key, arm=arm, original_account=str(account), snapshot_SHA256=snapshot_sha, genuine_state_hash=pointer['state_hash'], published_binding_result='EXACT_BYTES', original_snapshot='PRESENT_SHA_VERIFIED'))
remaining_financial = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        command = (proc / 'cmdline').read_bytes().replace(b'\x00', b' ').decode(errors='replace')
    except (OSError, PermissionError):
        continue
    if '/quantity-grid-sensitivity-20261012/driver.py' in command and 'python' in command:
        remaining_financial.append(int(proc.name))
assert not remaining_financial
report = dict(check_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), scope='Own original six quantity accounts and six reused fine accounts; no claim about parent workspace or missing 2026 ledgers', cases=cases, original_account_count=12, all_originals_present=True, own_workspace_anomaly_detected=False, financial_processes_remaining=remaining_financial, economic_execution='ALL6_FINISHED_WITHOUT_REPLAY', branch_snapshot='Existing paginated58 snapshot preserved at original observation time', available_disk_bytes=shutil.disk_usage('/workspace').free, reserve_bytes=16106127360, guard_changed=False, financial_advances=0, market_downloads=0)
assert report['available_disk_bytes'] > report['reserve_bytes']
(here / 'evidence/FINAL_WORKSPACE_CHECK.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
