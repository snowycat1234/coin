"""Export exact already-accepted metadata/code; no financial or QA recomputation."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

root = Path('/mnt/d/codex/coin')
state = Path('/home/xflops/coin-state')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
own_archive = 'docs/archive/FUNDING_INCOME_THIN_SOURCE_EXPORT_20261003_V1.py'
assert Path(__file__).read_bytes() == (root/own_archive).read_bytes()
hashes = {own_archive: sha(root/own_archive)}
receipts = {}
tasks = {}
names = {
    'protocols/FUNDING_INCOME_DIAGNOSTIC_122D_20261003_V1.json': ('306749e93b82e70c4597be75dd1f0e548ba63b4937a2094d9d677ede34755db4', None, None),
    'protocols/FUNDING_SEMANTICS_PROBE_20261003_V1.json': ('4c28d4d677afb071efb15dc1a814f893a95f7ec5c2d091645654307cd7259033', None, None),
    'protocols/FUNDING_SEMANTICS_PROBE_20261003_V2.json': ('4cf49418fc6106670a6d60bb60df7d3164aa28398e8fab269440694cd2278b58', None, None),
    'reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V1.json': ('595acfac68508b6bac16c89271d2a40b7821cfbd8fd927efed8f495a800dff6c', 1, '46323'),
    'reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V2.json': ('54febc06b7815e521715c8d70c3e930929a489c7e2a84d1ddae9507a03e4da4d', 1, '65859'),
    'reports/fast_research/FUNDING_INCOME_DIAGNOSTIC_TINY_20261003_V1.json': ('b260943395e4ba3b5ebd6af02f73b8963b54766488fe6716af08306cfcda4f6c', 0, '52655'),
    'reports/fast_research/FUNDING_INCOME_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json': ('8dc6eb125dfdb5358ba64b4600dfc38025bb08eae40b80469e6247e34442b5e2', 0, '38761'),
    'reports/fast_research/FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json': ('643ac6a536e0cd3d5d495019f9245341de18a05b15f9ce7d91e6c29f1633bc2f', 1, 'chunk:121be0'),
    'reports/fast_research/FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json': ('a943e7dadc42bf4ae1742745307a04fdd5ff8e64f30602f3e7009fddc1eb5b1f', 0, 'chunk:438966'),
    'reports/fast_research/FUNDING_INCOME_ROOT_MODULE_ACCEPTANCE_20261003_V1.json': ('af9399c66e9c50308d27c3359810914ba501ec95ff77b751887f6c414a922d7f', 0, 'chunk:877d0a'),
}
def add(name, digest):
    assert not Path(name).is_absolute() and '..' not in Path(name).parts and '\\' not in name
    path = root/name
    assert path.is_file() and not path.is_symlink() and path.stat().st_size < 2_000_000
    assert sha(path) == digest and (name not in hashes or hashes[name] == digest)
    hashes[name] = digest
for name, (digest, exit_code, host) in names.items():
    add(name, digest)
    value = json.loads((root/name).read_bytes())
    receipts[name] = dict(sha256=digest, status=value.get('status', 'FROZEN_PROTOCOL'))
    for mapping in (value.get('frozen_sources', {}), value.get('binding', {}).get('source_hashes', {}), value.get('verified_source_hashes', {})):
        for dependency, bound in mapping.items(): add(dependency, bound)
    if exit_code is not None:
        identity = value.get('task_id') or value['binding']['task_id']
        path = state/'task-progress'/('task-'+identity+'.json')
        task = json.loads(path.read_bytes())
        assert task['id'] == identity and task['exit_code'] == exit_code and task['status'] == ('failed' if exit_code else 'completed')
        tasks[name] = dict(path=str(path), sha256=sha(path), host_result=host, task=task)
archives = []
for relative, destination, digest in (
    ('test-funding-income-independent-audit-20261003-v1/audit.py', 'docs/archive/FUNDING_INCOME_DECIMAL_CHECKER_20261003_V1.py', '3fd24b4be93b192c146434590ea3bf63ad149a0e394442f4b721b0bf8af98bc1'),
    ('test-funding-income-independent-audit-20261003-v2/prefix_recovery.py', 'docs/archive/FUNDING_INCOME_PREFIX_RECOVERY_20261003_V2.py', 'a75d980d692110cfa8aaf97761b1e31778ed3d5b3c57a91bc9bdab083e46f3cd'),
    ('test-funding-income-independent-audit-20261003-v1/root_accept.py', 'docs/archive/FUNDING_INCOME_ROOT_ACCEPTANCE_HELPER_20261003_V2.py', 'ff11ae17209fe12fd6306d2c318d49462fddfe00b317d93cfedb411e715d1a85')):
    source = state/relative
    assert source.is_file() and not source.is_symlink() and sha(source) == digest
    with (root/destination).open('xb') as writer: writer.write(source.read_bytes())
    add(destination, digest)
    archives.append(dict(original_path=str(source), archive_path=destination, sha256=digest))
for name in ('docs/archive/FUNDING_INCOME_PUSH_VERIFICATION_SOURCE_20261003_V1.py',
             'docs/archive/FUNDING_INCOME_REMOTE_HEAD_SOURCE_20261003_V1.ps1',
             'docs/archive/FUNDING_MODULE_OUTCOME_REGISTRATION_SOURCE_20261003_V1.py',
             'docs/archive/FUNDING_SEMANTICS_PROTOCOL_FREEZER_20261003_V2.py'):
    add(name, sha(root/name))
actual = json.loads((root/'reports/fast_research/FUNDING_INCOME_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json').read_bytes())
assert actual['income_unit_certification'] == 'UNCONFIRMED_NOT_AN_INVESTMENT_GATE_PASS'
assert actual['completed_events'] == 732 and actual['capital_net_APR'] == 'NOT_EVALUABLE'
result = dict(status='PASS_EXACT_ACCEPTED_METADATA_AND_CODE_EXPORT_CONDITIONAL_MATH_ONLY',
    created_utc=datetime.now(UTC).isoformat(), source_hashes=hashes, original_receipts=receipts,
    actual_task_evidence=tasks, exact_STATE_code_archives=archives,
    market_data_QA_or_statistics_or_tests_repeated=False, frozen_receipts_overwritten=False,
    source_hashes_contain_STATE_paths=False, income_unit_certified=False, NAV_or_APR_computed=False,
    candidate_status='NO_QUALIFIED_CANDIDATE', resource_metadata={key:actual[key] for key in ('disk','resources','peak_RSS_bytes','owned_bytes')})
output = root/'reports/GITHUB_FUNDING_INCOME_SOURCE_BINDING_20261003_V1.json'
with output.open('x') as writer: json.dump(result, writer, indent=2, ensure_ascii=False); writer.write('\n')
print(json.dumps(dict(output=str(output), sha256=sha(output), source_files=len(hashes), statistical_replays=0)))
