import hashlib, json, subprocess
from datetime import UTC, datetime
from pathlib import Path
root = Path('/mnt/d/codex/coin')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
sources = {
 'scripts/research_v8/funding_price_source_v2.py':'2f39c9803051373654094ee990474b3ebe9b241ef85fa9eb586b9bde92bb4cdb',
 'scripts/research_v8/audit_funding_price_source.py':'edf2b7e8f7f74e392c422a126ae11d3755f915d11984b50014aa44df54dcd79c',
 'protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json':'2b3ef722ba3276c95d4a658d63ecdae12d92ae7a4f95a88de2918a4fd775d38a'}
proofs = {
 'V8_FUNDING_MARK_INDEX_SOURCE_20261002_V1.json':'f4970c14797dfeed367d8ba0d0a08c4649bc89e3adfa2d73ebd0ab76c5ff758a',
 'V8_FUNDING_MARK_INDEX_INDEPENDENT_QA_20261002_V1.json':'2f2b13b6be120a2db7e09abc24943f33b0892e53bfcc6b474f1bf3a53055ac74',
 'V8_FUNDING_MARK_INDEX_SOURCE_ACCEPTANCE_20261002_V1.json':'318622721ed9733d84ae66082f750e8b7d4ed960d7812c9e899c94b3cb5188aa',
 'V8_FUNDING_MARK_INDEX_HEADER_CORRECTION_20261002_V1.json':'9d529a13208b7bdd0fa31c9386dfe19d62d3947e9fd7789ca0281cff060726d9',
 'V8_FUNDING_SOURCE_HELPER_ARCHIVE_20261002_V1.json':'169e6ade2ede47953d982d0dcd7252b830f099e107c16fa0e91d82a8be79929b',
 'V8_EXISTING_FROZEN_SPOT_MINUTE_SOURCE_REUSE_20261002_V1.json':'a8b5389eced2ae4d9742d3e212e88562ca7bcc879990f3fa2b9632ebfdf1552e',
 'V8_EXISTING_FROZEN_SPOT_MINUTE_REUSE_ARCHIVE_20261002_V1.json':'aadf310322d510ad369bec77c10423426536afceb539ada8a5efaa28e8ff2792'}
proofs = {'reports/fast_research/'+k:v for k,v in proofs.items()}
for path, expected in {**sources, **proofs}.items(): assert sha(root/path) == expected, path
acceptance = json.loads((root/'reports/fast_research/V8_FUNDING_MARK_INDEX_SOURCE_ACCEPTANCE_20261002_V1.json').read_text())
assert acceptance['accepted_format']['archives'] == 24 and acceptance['accepted_format']['actual_rows'] == 703452
assert acceptance['capabilities_preserved']['locked_consumed'] is False and acceptance['capabilities_preserved']['fits'] == 0
assert acceptance['remaining_requirements']['carry_economic_state'] == 'NOT_EVALUABLE'
tasks = []
for title in ('V8 资金费和标记指数月档 · 固定24文件来源QA','V8 24月档独立QA · 原ZIP与Parquet逐行核对'):
    found = [p for p in Path('/home/xflops/coin-state/task-progress').glob('*.json') if json.loads(p.read_text()).get('title') == title]
    assert len(found) == 1
    value = json.loads(found[0].read_text())
    assert value['status'] == 'completed' and value['exit_code'] == 0
    tasks.append(dict(path=str(found[0]),sha256=sha(found[0]),task=value))
receipt = dict(status='ROOT_ACCEPTED_OFFICIAL_INPUT_FORMAT_AND_PRIOR_MINUTE_SOURCE_REUSE_ONLY',
    created_utc=datetime.now(UTC).isoformat(),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
    source_hashes=sources,verified_prior_files=proofs,actual_task_bindings=tasks,
    actual_sessions=dict(source=68971,independent_qa=98615),no_prior_QA_rerun=True,
    header_correction='Original synopsis wrongly says no header; appended correction confirms actual16/16 official12-column headers. Original QA/raw reports remain unchanged.',
    economic_candidate='NONE',carry_economics='NOT_EVALUATED',mark_or_index_as_fill=False,
    locked_consumed=False,orders_sent=0,fits=0,GPU_hours=0,
    project_disk_scan=acceptance['execution']['initial_actual_disk_scan'],no_new_scan=True)
out=root/'reports/fast_research/OFFICIAL_INPUT_SOURCE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json'
with out.open('x') as f: json.dump(receipt,f,indent=2,ensure_ascii=False); f.write('\n')
print(json.dumps(dict(status=receipt['status'],sha256=sha(out))))
