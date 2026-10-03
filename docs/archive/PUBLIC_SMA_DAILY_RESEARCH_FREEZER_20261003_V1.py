"""D038 protocol-only freeze; reuse accepted D037 inputs, no market-array IO."""
import hashlib,json,os,sys
from datetime import UTC,datetime
from pathlib import Path
from quant import resources
from scripts.investment import public_sma_daily_runner as runner
from scripts.investment import public_sma_daily as target
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/PUBLIC_SMA_DAILY_RESEARCH_FREEZER_20261003_V1.py'
PRIOR='protocols/PUBLIC_DONCHIAN_DAILY_CONT547_20261003_V1.json'
VENDOR='reports/fast_research/SMACROSSOVER_OFFICIAL_SOURCE_PROVENANCE_20261003_V1.json'
TINY='reports/fast_research/PUBLIC_SMA_DAILY_BOUNDARY_TINY_20261003_V1.json'
SOURCE_ROOT='reports/fast_research/PUBLIC_DONCHIAN_DAILY_SOURCE_ROOT_BINDING_20261003_V1.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,reason):
    if not ok:raise ValueError(reason)
def write(path,value):
    with (ROOT/path).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
need(os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and sha(__file__)==sha(ROOT/ARCHIVE),'Exact bounded frozen metadata helper')
prior=json.loads((ROOT/PRIOR).read_bytes());need(sha(ROOT/PRIOR)=='dc90c0522df9eecdd0c06810bd767efa158c327bfc8d41945365d97153cd604b','Accepted D037 original source union')
shared=dict(prior['frozen_sources'])
for name,digest in shared.items():need(sha(ROOT/name)==digest,'Prior exact source '+name)
v=json.loads((ROOT/VENDOR).read_bytes());need(v['status']=='PASS_D038_PINNED_SMA_SOURCE_BYTES_AND_MIT_PROVENANCE_ONLY'
    and not v['market_inputs_read'] and not v['locked_consumed'] and v['models_fit']==v['orders_sent']==v['GPU']==0,'Actually obtained pinned MIT source only')
task_path=STATE/'task-progress'/('task-'+v['binding']['task_id']+'.json');task=json.loads(task_path.read_bytes())
need(task['id']==v['binding']['task_id'] and task['status']=='completed' and task['exit_code']==0,'Actual source task closed0')
need(v['source_sha256']==target.PINNED_HASHES['smacrossover_original.py']=='453440d7b934c494934a1c56b3826d94638594f79ad4e4c7faaff36b96d33fae'
    and v['license_sha256']==target.PINNED_HASHES['LICENSE']=='80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d','Original hook/license identity')
for name,digest in v['source_hashes'].items():need(sha(ROOT/name)==digest,'Exact vendor provenance dependency');shared[name]=digest
names=[ARCHIVE,PRIOR,VENDOR,SOURCE_ROOT,'scripts/investment/public_sma_daily.py','scripts/investment/public_sma_daily_runner.py',
 'tests/test_public_sma_daily.py','docs/archive/SMACROSSOVER_OFFICIAL_SOURCE_FETCH_20261003_V1.py','docs/OPEN_SOURCE_REGISTRY.md',
 'reports/fast_research/PUBLIC_DONCHIAN_DAILY_ROOT_ACCEPTANCE_20261003_V2.json',
 'reports/GITHUB_PUBLIC_DONCHIAN_DAILY_SYNC_VERIFIED_20261003_V1.json']
for name in names:shared[name]=sha(ROOT/name)
need(shared[SOURCE_ROOT]=='58c0f265c6d22ca7dc9d85f8c3047ecd989e9fdc23a95ff58af2a08f363c1a62','Same previously accepted daily source; no new QA')
record_dir=ROOT/'docs/archive/PUBLIC_SMA_DAILY_USED_SOURCE_METADATA_20261003_V1';record_dir.mkdir()
destination=record_dir/'VENDOR_CLOSED_TASK.json';destination.write_bytes(task_path.read_bytes());shared[destination.relative_to(ROOT).as_posix()]=sha(destination)
r=resources.status();need(r['ram_limit_bytes']<=5_000_000_000 and r['swap_bytes']==0 and not r['gpu_used'],'Unchanged shared resource boundary')
outputs=[]
for period,budget in [('CONT547',280_000_000),('CONT122',70_000_000),('CONT90',60_000_000)]:
    spec=runner.protocol_template(period,TINY)
    spec.update(frozen_sources=shared,maximum_new_owned_bytes=budget,maximum_wall_seconds=1800,
        daily_source_root_binding=dict(path=SOURCE_ROOT,sha256=shared[SOURCE_ROOT]),
        total_new_research_and_independent_budget_bytes=450_000_000,
        economics_question='One fixed public SMA50/200 daily state vs accepted saved public/VM/CASH controls; same10k/BybitSpot36bp/risk; zeroHPO',
        vendor_provenance=dict(path=VENDOR,sha256=shared[VENDOR]),primary_reference=runner.STRATEGY,
        no_epsilon_or_parameter_search=True)
    runner.context(spec)
    name=f'protocols/PUBLIC_SMA_DAILY_{period}_20261003_V1.json';write(name,spec)
    outputs.append(dict(path=name,sha256=sha(ROOT/name),maximum_new_owned_bytes=budget))
print(json.dumps(dict(status='FROZEN_D038_THREE_SINGLE_SMA_ACCOUNTS_METADATA_ONLY',created_utc=datetime.now(UTC).isoformat(),
    task_id=os.environ['COIN_TASK_ID'],protocols=outputs,shared_source_count=len(shared),market_arrays_read=False,old_source_QA_replayed=False)))
