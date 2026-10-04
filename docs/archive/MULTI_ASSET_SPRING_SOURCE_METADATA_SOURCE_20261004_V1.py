"""Freeze a finite source-only third window, reusing accepted capabilities."""
import argparse,hashlib,json,os,subprocess
from datetime import UTC,datetime
from pathlib import Path
from scripts.investment import multi_asset_data as data
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def small(p,h=None):
    p=Path(p);assert p.is_file() and not p.is_symlink() and p.stat().st_size<2_000_000
    if h:assert sha(p)==h
    return json.loads(p.read_bytes())
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
parser=argparse.ArgumentParser();parser.add_argument('--expected-data',required=True);parser.add_argument('--expected-transport',required=True)
args=parser.parse_args();assert os.environ['COIN_TASK_ID']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='a98ceb45178d445b78a2cac113956f0408ac07fe'
old=small(ROOT/'protocols/MULTI_ASSET_WINTER_MARKET_SOURCE_20261004_V1.json')
changes={'scripts/investment/multi_asset_data.py':args.expected_data,
         'scripts/investment/multi_asset_official_transport.ps1':args.expected_transport}
pins={}
for p,h in old['source_hashes'].items():
    if 'STARTUP_FAILURE' in p:continue
    expected=changes.get(p,h);assert sha(ROOT/p)==expected,p;pins[p]=expected
for p in ('docs/archive/MULTI_ASSET_SPRING_SOURCE_METADATA_SOURCE_20261004_V1.py',
          'docs/archive/MULTI_ASSET_SPRING_COVERAGE_SOURCE_20261004_V1.py',
          'reports/fast_research/MULTI_ASSET_SPRING_COVERAGE_20261004_V1.json',
          'reports/fast_research/MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_20261004_V2.json'):
    pins[p]=sha(ROOT/p)
warm_ref=dict(path=str(STATE/'d056-multiasset-winter-source-acceptance-20261004-v2/INPUT_MANIFEST.json'),
    sha256='56f1eb1b768e14d4c67198156732c1d4a22e6a901e980c24ebee9f20bbf86193',
    required_status='PASS_D056_SELECTED_PORTFOLIO_WINTER_SOURCE_BINDING_NOT_ECONOMICS')
warm=small(warm_ref['path'],warm_ref['sha256'])
cap_ref=warm['source_acceptance'];cap_path=Path(cap_ref['path']);cap_path=cap_path if cap_path.is_absolute() else ROOT/cap_path
cap=small(cap_path,cap_ref['sha256'])
assert cap_ref['sha256']=='5f904de403070d9397fa00ef338e6cda38f642aaa85bb6620a68e5e935b3476c'
assert cap['status']==data.WINTER_ACCEPTANCE_STATUS and cap['actual_exit_code']==0 and cap['source_only']
t=small(STATE/'task-progress'/('task-'+cap['binding']['task_id']+'.json'))
assert t['status']=='completed' and t['exit_code']==0
pool=small(ROOT/old['pool_receipt']['path'],old['pool_receipt']['sha256'])
assert pool['symbols']==warm['selected_symbols'] and len(pool['symbols'])==10
refs=[*warm['warmup_source_acceptances'],cap_ref]
for ref in refs:
    p=Path(ref['path']);p=p if p.is_absolute() else ROOT/p
    r=small(p,ref['sha256']);assert r['status']==ref['required_status'] and r['actual_exit_code']==0
spec=dict(contract_id=data.SPRING_CONTRACT,experiment_id='D062-FIXED-POOL-SPRING-SOURCE-20261004-V1',
    phase='SPRING_SOURCE',ready_for_execution=True,capacity_registered=True,
    start_us=1740787200000000,end_us=1751328000000000,days=122,
    score_months=['2025-03','2025-04','2025-05','2025-06'],rules=data.SPRING_RULES,budgets=data.SPRING_BUDGETS,
    run_dir=str(STATE/'d062-multiasset-spring-source-20261004-v1'),
    output_path='reports/fast_research/MULTI_ASSET_SPRING_MARKET_SOURCE_20261004_V1.json',
    source_hashes=pins,reuse_manifest=old['reuse_manifest'],pool_receipt=old['pool_receipt'],
    pool_receipt_sha256=old['pool_receipt_sha256'],symbols=sorted(pool['symbols']),
    warmup_manifest=warm_ref,warmup_source_acceptance=cap_ref,warmup_source_acceptances=refs,
    pool_reselected=False,new_market_files=96,reused_market_files=24,
    transport='DEFAULT_WINDOWS_HTTPS_SAME_OFFICIAL_URLS_WSL_PARSE',child_environment=old['child_environment'],
    compatibility_reason='FINITE_FOUR_MONTH_THIRD_DEVELOPMENT_WINDOW_NORMAL_INTERFACE',
    joint_disk_reservation_bytes=1500000000,
    capacity_registration=dict(latest_actual_scan_bytes=25596421780,actual_scan_utc='2026-10-04T10:40:44.119435Z',
        module_joint_reserve_bytes=1500000000,expected_total_upper_bytes=27096421780,warn=32000000000,
        stop_new=36000000000,hard=40000000000,scan_scope='New existing disk.check before network mandatory'),
    funding_unit_certified=False,native_Bybit_certified=False,publication_certified=False,
    locked_consumed=False,GPU=0,model_fits=0,orders_sent=0,
    decision='Fixed same July pool; source-only; preserve all absences and source failures',created_utc=datetime.now(UTC).isoformat())
assert spec['budgets']['market_owned_bytes']==400000000 and spec['budgets']['source_wall_seconds']==1800
p=ROOT/'protocols/MULTI_ASSET_SPRING_MARKET_SOURCE_20261004_V1.json';write(p,spec)
out=ROOT/'reports/fast_research/MULTI_ASSET_SPRING_SOURCE_METADATA_20261004_V1.json'
write(out,dict(status='READY_FIXED_SPRING_SOURCE_PROTOCOL_NOT_DOWNLOADED_OR_ACCEPTED',
    task_id=os.environ['COIN_TASK_ID'],protocol=dict(path=str(p.relative_to(ROOT)),sha256=sha(p)),source_hashes=pins,
    new_source_files=96,reused_accepted_score_files=24,prior_warm_aliases=130,
    market_accounts=0,financial_calls=0,price_payloads_read=0,new_QA_calls=0,metadata_source_sha256=sha(Path(__file__))))
print(json.dumps(dict(status='READY_FIXED_SPRING_SOURCE_PROTOCOL_NOT_DOWNLOADED_OR_ACCEPTED',protocol=str(p),sha256=sha(p))),flush=True)
