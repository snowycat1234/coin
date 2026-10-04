"""Bind the finite cost correction to actual closed jobs, never replay accounts."""
import hashlib,json,os,shutil,subprocess
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
PARENT='f895f4b32e3c2e6e61b15b022ce46736982e9865'
assert os.environ['COIN_TASK_ID']
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==PARENT
prior=ROOT/'reports/GITHUB_MULTI_ASSET_SPRING_SYNC_VERIFIED_20261004_V1.json'
assert sha(prior)=='b5c818e0ce6e314300593a9ca8659e532205dc78982175e85da9129686140207'
assert read(prior)['local_HEAD']==read(prior)['remote_main']==PARENT
for name in ['COST_PROVENANCE_ACCOUNT_SYNTHETIC_20261004_V2','COST_PROVENANCE_CLOSING_SYNTHETIC_20261004_V1']:
    p=ROOT/'protocols'/(name+'.json')
    for key,value in read(p)['frozen_sources'].items():assert sha(ROOT/key)==value,key
    r=read(ROOT/'reports/fast_research'/(name+'.json'));assert r['test_exit_code']==0 and not r['junit_counts']['failures']
accept=read(ROOT/'reports/fast_research/COST_PROVENANCE_ACCOUNT_ACCEPTANCE_20261004_V1.json')
assert accept['market_replays']==accept['new_API_requests']==accept['orders_sent']==0
for run in accept['existing_test_runs']:
    r=read(ROOT/run['path']);assert sha(ROOT/run['path'])==run['sha256']
    assert r['test_exit_code']==run['exit_code']
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
dest=ROOT/'docs/archive/COST_PROVENANCE_TASK_METADATA_20261004_V1';dest.mkdir()
roles={}
for p in (STATE/'task-progress').glob('task-*.json'):
    t=read(p)
    if t['id']==os.environ['COIN_TASK_ID'] or not t['title'].startswith('D063'):continue
    assert t['ended_at'] and t['exit_code'] in (0,1) and t['status'] in ('completed','failed')
    assert t['status']==('completed' if t['exit_code']==0 else 'failed')
    copied=dest/p.name;shutil.copyfile(p,copied)
    roles[t['id']]=dict(title=t['title'],status=t['status'],actual_exit_code=t['exit_code'],task_archive=copied.relative_to(ROOT).as_posix(),task_archive_sha256=sha(copied))
for owner in ['d063-cost-provenance-synthetic-20261004-v1','d063-cost-provenance-synthetic-20261004-v2','d063-cost-closing-synthetic-20261004-v1']:
    for n in ['RUN_BINDING.json','junit.xml']:
        shutil.copyfile(STATE/owner/n,dest/(owner+'-'+n))
selected=set(subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines())
for folder in ['protocols','reports/fast_research','reports','docs/archive']:
    selected.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).glob('COST_PROVENANCE_*') if p.is_file())
selected.update(p.relative_to(ROOT).as_posix() for p in dest.iterdir())
selected.update(['scripts/investment/bybit_cost_inputs.py','tests/test_cost_provenance_account.py','tests/test_closing_cost_provenance.py',prior.relative_to(ROOT).as_posix()])
owned=sum(p.stat().st_size for d in STATE.glob('d063-*') if d.is_dir() for p in d.rglob('*') if p.is_file())
assert owned<5000000
verified={r['path']:sha(ROOT/r['path']) for r in accept['preserved_access_limit_evidence']}
report=dict(status='COST_CORRECTION_CLOSED_SOURCE_AND_SAVED_SYNTHETIC_ACCEPTANCE_NOT_NEW_REPLAY',created_utc=datetime.now(UTC).isoformat(),parent_commit=PARENT,source_hashes={n:sha(ROOT/n) for n in sorted(selected)},selected_module_paths=sorted(selected),verified_prior_files=verified,closed_actual_roles=roles,owned_d063_STATE_bytes=owned,final_disk_receipt='reports/COST_PROVENANCE_FINAL_RESOURCE_20261004_V1.json',market_replays=0,market_model_fits=0,orders_sent=0,new_API_requests=0,locked_body_read=False,private_SHA_only='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d',independent_static_review=accept['independent_static_review'],main_cases=0,synthetic_runner_cases_per_primary_attempt=2,primary_test_attempts=2,primary_cases_executed=13,closing_cases=1,models_adopted=0,candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE',task_id=os.environ['COIN_TASK_ID'])
out=ROOT/'reports/GITHUB_COST_PROVENANCE_SOURCE_BINDING_20261004_V1.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(output=str(out),sha256=sha(out),paths=len(selected),owned_STATE_bytes=owned)))