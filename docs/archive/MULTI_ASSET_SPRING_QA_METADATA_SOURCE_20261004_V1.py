"""Bind a completed new source task to the normal independent format gate."""
import hashlib,json,os,subprocess
from pathlib import Path
from datetime import UTC,datetime
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def small(p,h=None):
    p=Path(p);assert p.is_file() and not p.is_symlink() and p.stat().st_size<4_000_000
    if h:assert sha(p)==h
    return json.loads(p.read_bytes())
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
assert os.environ['COIN_TASK_ID']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='a98ceb45178d445b78a2cac113956f0408ac07fe'
source_path=ROOT/'reports/fast_research/MULTI_ASSET_SPRING_MARKET_SOURCE_20261004_V1.json'
source=small(source_path);proto_path=ROOT/'protocols/MULTI_ASSET_SPRING_MARKET_SOURCE_20261004_V1.json'
proto=small(proto_path,'d06566fbf0a3c6331d2aff63fd06465ad7677259a4ae95c126b64d04e7c12350')
assert source['status']=='COMPLETE_D062_FIXED_POOL_SPRING_SOURCE_FORMAT_PENDING_ACCEPTANCE'
assert source['actual_exit_code']==0 and source['source_bytes_unchanged'] and len(source['market_records'])==120
assert source['new_market_files']==96 and source['reused_market_files']==24 and len(source['warmup_minute_records'])==60
ident=source['binding']['task_id'];task=small(STATE/'task-progress'/('task-'+ident+'.json'))
assert task['status']=='completed' and task['exit_code']==0 and task['ended_at']
rb=small(Path(source['run_dir'])/'RUN_BINDING.json',source['run_binding_sha256'])
assert rb==source['binding'] and rb['source_hashes']==proto['source_hashes'] and rb['protocol_sha256']==sha(proto_path)
pins=dict(proto['source_hashes'])
extra=('scripts/investment/multi_asset_source_acceptance.py',
    'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py',
    'scripts/research_v8/audit_funding_price_source.py','scripts/investment/audit_perpetual_trade_source.py',
    'docs/archive/MULTI_ASSET_SPRING_QA_METADATA_SOURCE_20261004_V1.py')
for p in extra:pins[p]=sha(ROOT/p)
assert pins['scripts/investment/multi_asset_source_acceptance.py']=='861b9126102abb302db1ba815d37912f73714025040f58c3c1b9aa5f2a97dd09'
assert pins['docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py']=='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
assert pins['scripts/research_v8/audit_funding_price_source.py']=='edf2b7e8f7f74e392c422a126ae11d3755f915d11984b50014aa44df54dcd79c'
assert pins['scripts/investment/audit_perpetual_trade_source.py']=='7770342534d216b121d42da3c541874bb7c175fcd3b10c9939337417760e8e92'
warm_ref=proto['warmup_manifest'];warm=small(warm_ref['path'],warm_ref['sha256'])
cap_ref=proto['warmup_source_acceptance']
for ref in [cap_ref,*warm['warmup_source_acceptances']]:
    p=Path(ref['path']);p=p if p.is_absolute() else ROOT/p
    cap=small(p,ref['sha256']);assert cap['status']==ref['required_status'] and cap['actual_exit_code']==0
    name=str(p.relative_to(ROOT));pins[name]=ref['sha256']
    t=small(STATE/'task-progress'/('task-'+cap['binding']['task_id']+'.json'))
    assert t['status']=='completed' and t['exit_code']==0
old=small(ROOT/proto['reuse_manifest']['path'],proto['reuse_manifest']['sha256'])
for row in old['source_files'].values():
    if row['symbol'] in ('BTCUSDT','ETHUSDT') and row['month'] in proto['score_months']:
        p=row['independent_QA_report_path'];h=row['independent_QA_report_sha256']
        assert sha(ROOT/p)==h;pins[p]=h
pins[str(source_path.relative_to(ROOT))]=sha(source_path);pins[str(proto_path.relative_to(ROOT))]=sha(proto_path)
for p,h in pins.items():assert sha(ROOT/p)==h,p
run=STATE/'d062-multiasset-spring-source-acceptance-20261004-v1'
spec=dict(contract_id='D062_FIXED_POOL_SPRING_SOURCE_FORMAT_ACCEPTANCE_V1',
    experiment_id='D062_FIXED_POOL_SPRING_SOURCE_ACCEPTANCE_20261004_V1',ready_to_execute=True,
    source_month='2025-03_2025-06',score_months=proto['score_months'],start_us=proto['start_us'],end_us=proto['end_us'],
    run_dir=str(run),output_path='reports/fast_research/MULTI_ASSET_SPRING_SOURCE_ACCEPTANCE_20261004_V1.json',
    manifest_path=str(run/'INPUT_MANIFEST.json'),frozen_sources=pins,
    market_receipt=dict(path=str(source_path.relative_to(ROOT)),sha256=sha(source_path),required_status=source['status']),
    pool_receipt=proto['pool_receipt'],reuse_manifest=proto['reuse_manifest'],prior_manifest=warm_ref,
    prior_acceptance=cap_ref,prior_acceptances=warm['warmup_source_acceptances'],
    budgets=dict(new_owned_bytes=5000000,peak_RSS_bytes=1000000000,wall_seconds=1200),
    source_only=True,economics='NOT_EVALUATED',funding_unit_certified=False,native_Bybit_certified=False,
    created_utc=datetime.now(UTC).isoformat(),metadata_task_id=os.environ['COIN_TASK_ID'])
p=ROOT/'protocols/MULTI_ASSET_SPRING_SOURCE_ACCEPTANCE_20261004_V1.json';write(p,spec)
out=ROOT/'reports/fast_research/MULTI_ASSET_SPRING_QA_METADATA_20261004_V1.json'
write(out,dict(status='READY_COMPLETED_SOURCE_BOUND_INDEPENDENT_QA_NOT_YET_ACCEPTED',
    task_id=os.environ['COIN_TASK_ID'],protocol=dict(path=str(p.relative_to(ROOT)),sha256=sha(p)),
    producer_task_id=ident,producer_actual_exit_code=0,source_hashes=pins,source_payload_rows_read=0,
    old_source_QA_calls=0,new_QA_calls=0,market_accounts=0,metadata_source_sha256=sha(Path(__file__))))
print(json.dumps(dict(protocol=str(p),sha256=sha(p),producer_task=ident)),flush=True)
