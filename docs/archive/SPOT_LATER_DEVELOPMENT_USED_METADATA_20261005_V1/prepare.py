import hashlib,json,subprocess
from pathlib import Path
from datetime import UTC,datetime
from quant.paths import ROOT,STATE
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
def ref(n):return dict(path=str(ROOT/n),sha256=sha(ROOT/n))
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert head=='f6cdf43186a4f3aa9ea62a3eb738d9225ea4a36b'
sources=[('reports/fast_research/PUBLIC_LONG_547D_SOURCE_REUSE_20261003_V1.json','PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_578D_CALENDAR'),
 ('reports/fast_research/V8_EXISTING_FROZEN_SPOT_MINUTE_SOURCE_REUSE_20261002_V1.json','PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_153D_CALENDAR'),
 ('reports/fast_research/PUBLIC_STRATEGY_CHRONOLOGY_SOURCE_REUSE_20261002_V1.json','PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_151D_CALENDAR')]
window=dict(symbols=['BTCUSDT','ETHUSDT'],source_start_month='2025-05',source_end_month='2026-02',
 accepted_source_receipts=[dict(**ref(n),expected_status=s) for n,s in sources],
 prior_use_protocols=[ref(n) for n in ['protocols/PUBLIC_LONG_547D_SOURCE_REUSE_20261003_V1.json','protocols/PUBLIC_LONG_547D_FIXED_THREE_ACCOUNTS_20261003_V1.json','protocols/PUBLIC_STRATEGY_CONTINUOUS_90D_V2.json']],
 prior_registry_sha256=sha(ROOT/'reports/experiment_registry.jsonl'),private_SHA_only=sha(ROOT/'state/dataset_lock.json'))
save(ROOT/'protocols/SPOT_LATER_SOURCE_WINDOW_20261005_V1.json',window)
base=json.loads((ROOT/'protocols/SPOT_DEFENSIVE_BLEND_20261005_V1.json').read_bytes())
for k in ['spot_control','economic_reference','perpetual_report']:base.pop(k,None)
base.update(parent_commit=head,experiment_id='D082_LATER_DEVELOPMENT_FIXED_RECIPES',module='D082',
 data_role='SEEN_DEVELOPMENT_CHRONOLOGY_NOT_UNSEEN',start_us=int(datetime(2025,12,1,tzinfo=UTC).timestamp())*1000000,
 end_us=int(datetime(2026,3,1,tzinfo=UTC).timestamp())*1000000,warmup_start='2025-05',last_source_month='2026-02',execution_start_month='2025-11',
 annual_vol_target=.08,recipe='HOLD8',budget=dict(wall_seconds=1200,owned_bytes=100000000,actual_spot_wallets=2,fits=0,downloads=0,API=0,HPO=0),
 hypothesis='Test two already fixed research recipes on later already-seen chronology; no parameter/cost/risk/asset changes. This cannot establish independent alpha.',
 comparison='Same new90-day Spot account period, complete10k, previous-only200 daily warmup and risk, received-asset fees and full minute wallet. Not risk matched.',
 success_decision='Before results: retain defense if it offers a net/risk tradeoff or dominates HOLD8 in both costs; pause it for this later-window evidence if HOLD8 dominates net, vol and minuteDD in both. CASH remains a reference, no investment adoption or period-grid.',
 stop_rule='Four real wallets only, same finite recipes and two original cost scenarios. Source, target, cash, fee or observed caps failure stops acceptance; preserve residue and all negative results.')
base['source_hashes']={n:sha(ROOT/n) for n in base['source_hashes']}
for n in ['scripts/task_progress_api.py','scripts/investment/accepted_spot_window.py','scripts/investment/audit_daily_spot_targets.py','scripts/investment/spot_saved_economic_diagnostics.py','scripts/investment/accept_spot_research.py']:
    base['source_hashes'][n]=sha(ROOT/n)
source_out='reports/fast_research/SPOT_LATER_SOURCE_WINDOW_20261005_V1.json'
save(ROOT/'protocols/SPOT_LATER_DEVELOPMENT_20261005_V1.json',dict(parent_commit=head,problem=base['hypothesis'],window_protocol=ref('protocols/SPOT_LATER_SOURCE_WINDOW_20261005_V1.json'),
 common=base,fixed_recipes=['HOLD8','HALF_HOLD10_EXIT10'],success_decision=base['success_decision'],total_wallets=4,total_fits=0,total_downloads=0,
 source_output=source_out,source_bytes_budget=1000000,total_replay_owned_budget=200000000,locked_body_read=False,orders_sent=0))
print('PRE_RESULT_FIXED_TWO_RECIPES_LATER_SEEN_WINDOW_READY')
