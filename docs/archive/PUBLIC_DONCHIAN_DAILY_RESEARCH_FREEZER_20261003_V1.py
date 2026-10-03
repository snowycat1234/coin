"""Freeze three fixed daily accounts after actual closed official source; metadata only."""
import hashlib,json,os,sys
from pathlib import Path
from datetime import UTC,datetime
from quant import resources
from scripts.investment import public_donchian_daily_runner as base
from scripts.investment import public_donchian_daily_runner_v2 as runner
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/PUBLIC_DONCHIAN_DAILY_RESEARCH_FREEZER_20261003_V1.py'
SOURCE='reports/fast_research/PUBLIC_DONCHIAN_DAILY_SOURCE_ACTUAL_20261003_V2.json'
ACCEPT='reports/fast_research/PUBLIC_DONCHIAN_DAILY_SOURCE_ROOT_BINDING_20261003_V1.json'
TINY='reports/fast_research/PUBLIC_DONCHIAN_DAILY_BOUNDARY_TINY_20261003_V1.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):
    with (ROOT/name).open('x') as w:json.dump(value,w,indent=2,ensure_ascii=False);w.write('\n')
def check(ok,msg):
    if not ok:raise ValueError(msg)
check(os.environ.get('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2','Actual bounded metadata task')
check(Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes(),'Frozen factory archive')
v=json.loads((ROOT/SOURCE).read_bytes())
check(v['status']==base.DAILY_STATUS and v['source_files']==66 and v['actual_daily_rows']==2008
    and v['days_per_symbol']==1004 and v['full_common_calendar'] and v['source_bytes_unchanged'],'Actual complete official source')
check(v['old_database_written'] is False and v['locked_consumed'] is False and v['models_fit']==v['orders_sent']==v['GPU']==0,'Source-only boundary')
task_path=STATE/'task-progress'/('task-'+v['binding']['task_id']+'.json')
task=json.loads(task_path.read_bytes())
check(task['status']=='completed' and task['exit_code']==0 and task['id']==v['binding']['task_id'],'Actual source closed0')
for p,h in v['binding']['source_hashes'].items():check(sha(ROOT/p)==h,'Source byte changed: '+p)
for item in v['binding']['official_files']:check(sha(item['path'])==item['sha256'],'Official utility bytes changed')
check(v['owned_bytes']<10_000_000 and v['peak_RSS_bytes']<=1_000_000_000,'Fixed source budget')
r=resources.status();check(r['ram_limit_bytes']<=5_000_000_000 and r['swap_bytes']==0 and not r['gpu_used'],'Shared resource boundary')
accepted=dict(status='PASS_ROOT_D037_CLOSED_OFFICIAL_DAILY_SOURCE_METADATA_FOR_SCREENING_ONLY',
    created_utc=datetime.now(UTC).isoformat(),factory_sha256=sha(__file__),task_id=os.environ['COIN_TASK_ID'],
    source_report=SOURCE,source_sha256=sha(ROOT/SOURCE),actual_source_task=dict(path=str(task_path),sha256=sha(task_path),task=task),
    source_hashes=v['binding']['source_hashes'],source_files=66,daily_rows=2008,days_per_symbol=1004,
    format_QA_scope='Actual producer original-parser plus new exact monthly/full UTC calendar; no duplicate old1mQA',
    source_only=True,market_arrays_read_by_root=False,publication_or_native_execution_certified=False,
    long_term_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE')
write(ACCEPT,accepted)
names=set(base.parent.PINS)|set(v['binding']['source_hashes'])
names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'src/quant').glob('*.py'))
names.update(['scripts/investment/public_long_development_adapter.py',
    'scripts/investment/public_donchian_daily.py','scripts/investment/public_donchian_daily_runner.py',
    'scripts/investment/public_donchian_daily_runner_v2.py',
    'tests/test_public_donchian_daily.py','tests/test_investment_bybit_pipeline.py',
    'scripts/research_v8/registry.py','scripts/research_v8/labels.py','scripts/research_v8/labels_v2.py',
    'protocols/BENCHMARK_CONTRACT_V1.json','protocols/EXECUTION_COST_SCENARIOS_V8.json','protocols/LABEL_CONTRACT_V8.json',
    'protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json','protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json',
    'third_party/jesse_example_donchian/donchian_original.py','third_party/jesse_example_donchian/donchian_indicator_original.py',
    'third_party/jesse_example_donchian/LICENSE','third_party/jesse_example_donchian/JESSE_LICENSE',
    'third_party/jesse_example_donchian/UPSTREAM.md','environments/v8/uv.lock',
    'scripts/research_v7/oracle_flow_ceiling.py','state/dataset_lock.json',SOURCE,ACCEPT,ARCHIVE,
    'protocols/PUBLIC_DONCHIAN_DAILY_SOURCE_20261003_V1.json','protocols/PUBLIC_DONCHIAN_DAILY_SOURCE_20261003_V2.json',
    'protocols/PUBLIC_DONCHIAN_DAILY_SOURCE_20261003_V3.json',
    'reports/fast_research/PUBLIC_DAILY_OFFICIAL_SOURCE_SELECTOR_SMOKE_20261003_V1.json',
    'reports/fast_research/PUBLIC_DAILY_OFFICIAL_SOURCE_SELECTOR_SMOKE_20261003_V2.json',
    'reports/fast_research/PUBLIC_DAILY_OFFICIAL_SOURCE_SELECTOR_SMOKE_20261003_V3.json'])
for profile in runner.PROFILES.values():
    names.update([profile['protocol'],profile['report']]);old=json.loads((ROOT/profile['protocol']).read_bytes())
    names.add(old['source_receipt'])
shared={p:sha(ROOT/p) for p in sorted(names)}
fixed={ 'scripts/investment/public_donchian_daily.py':'82796e9dac68089a24a6d4bd61c561672043e446c806cbe87a6737a459d35c4a',
    'scripts/investment/public_donchian_daily_runner.py':'5459b231c340a705c4c136cd3923ecc0b510205f7f81c8c36a4ea021b97b41d9',
    'scripts/investment/public_donchian_daily_runner_v2.py':'7b3ad9c67e993f9065ec83b9bcfab3aeb2c23af88c497d2f3328146f97b784c6',
    'tests/test_public_donchian_daily.py':'d0e6c99770ac106b65284280bff1e4bc9f06dfbf7080dc7f115e67c7df2ec497',
    'state/dataset_lock.json':'29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'}
check(all(shared[k]==h for k,h in fixed.items()),'Final strategy/test/private-lock bytes')
outputs=[]
for key,budget in [('CONT547',280_000_000),('CONT122',70_000_000),('CONT90',60_000_000)]:
    spec=runner.protocol_template(key,SOURCE,sha(ROOT/SOURCE),TINY)
    spec.update(frozen_sources=shared,maximum_new_owned_bytes=budget,maximum_wall_seconds=1800,
        daily_source_root_binding={'path':ACCEPT,'sha256':sha(ROOT/ACCEPT)},
        total_new_research_and_independent_budget_bytes=450_000_000,
        economics_question='One fixed daily horizon vs accepted saved public/VM controls under identical Bybit VIP0/capital/risk; no HPO',
        primary_reference=runner.STRATEGY)
    runner.context(spec) # Exact metadata/date/AST admission; no market-array hash/read.
    name=f'protocols/PUBLIC_DONCHIAN_DAILY_{key}_20261003_V1.json'
    write(name,spec);outputs.append({'path':name,'sha256':sha(ROOT/name),'maximum_new_owned_bytes':budget})
print(json.dumps(dict(status='FROZEN_D037_THREE_SINGLE_DAILY_ACCOUNTS_METADATA_ONLY',source_root_binding_sha256=sha(ROOT/ACCEPT),
    task_id=os.environ['COIN_TASK_ID'],protocols=outputs,shared_source_count=len(shared),market_arrays_read=False)))
