"""Only closed-task metadata and the new synthetic witness; no market replay."""
import hashlib,importlib.util,json,os
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
guard=ROOT/'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
assert hashlib.sha256(guard.read_bytes()).hexdigest()=='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
sp=importlib.util.spec_from_file_location('d040_guard_reuse',guard);g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
parent=ROOT/'docs/archive/PERPETUAL_CAPABILITY_USED_ACTUAL_METADATA_20261003_V1';assert not parent.exists();parent.mkdir()
roles={
 'SIGNAL':('reports/fast_research/PERPETUAL_PUBLIC_SIGNAL_TEST_ACTUAL_20261003_V1.json','656c2d2ed739c80771bd77d4f166d8b8c6c48252af0a7e232a13e8f178114828'),
 'ACCOUNT':('reports/fast_research/PERPETUAL_ACCOUNT_TEST_ACTUAL_20261003_V1.json','3a77167fdc74c867da8d1c5330e511d442fd08c6635789fd8de09884f2571360'),
 'CHAIN':('reports/fast_research/PERPETUAL_PUBLIC_CHAIN_TEST_ACTUAL_20261003_V1.json','b24c6ad341f3f3e3a41e25940a99619e4ce0207d78365a89fa4ea825c7b4ef10'),
 'SOURCE_ROOT':('reports/fast_research/PERPETUAL_TRADE_SOURCE_ROOT_ACCEPTANCE_20261003_V4.json','f8f6d2e49c320ecc5f61506ffd291ac1c94af0b80803baa6b8e4210741a1f95d'),
}
copied={};tasks={};reports={}
def copy(origin,name,expected=None):
 data=Path(origin).read_bytes();digest=hashlib.sha256(data).hexdigest();assert len(data)<2_000_000 and (expected is None or digest==expected)
 target=parent/name
 with target.open('xb') as f:f.write(data)
 copied[target.relative_to(ROOT).as_posix()]=digest
for role,(name,digest) in roles.items():
 r,_=g.small(ROOT/name,digest);reports[role]=r;tasks[role]=g.closed(r['binding']['task_id'])
 copy(tasks[role]['path'],role+'_ACTUAL_TASK.json',tasks[role]['sha256'])
 run=Path(r['run_dir']);copy(run/'RUN_BINDING.json',role+'_RUN_BINDING.json',r['run_binding_sha256'])
 if role!='SOURCE_ROOT':
  assert r['status']=='PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT' and r['test_exit_code']==0
  copy(run/'junit.xml',role+'_JUNIT.xml',r['junit_sha256'])
failed={}
for identity in ('e64dfb1e39554637ae1bd3ce611dff92','c21415e892fb4c76a14163ad57d99822','da1cbdd62bb243e095157dc14fe35662'):
 task=g.closed(identity,1);failed[identity]=task;copy(task['path'],'SOURCE_ROOT_FAILED_'+identity+'.json',task['sha256'])
work=Path(reports['CHAIN']['run_dir']);found=list((work/'pytest').rglob('chain_evidence.json'))
assert len(found)==1 and not found[0].is_symlink()
value,witness_sha=g.small(found[0]);assert set(value['modes'])=={'LONG_ONLY','SHORT_ONLY','LONG_SHORT','CASH'}
assert value['scope'].startswith('SYNTHETIC_') and value['modes']['SHORT_ONLY']['trades'][0]['quantity_after']<0
assert value['modes']['SHORT_ONLY']['trades'][-1]['side']=='BUY'
assert value['modes']['CASH']['summary']['NAV']==10000
target=ROOT/'reports/fast_research/PERPETUAL_PUBLIC_CHAIN_WITNESS_20261003_V1.json'
with target.open('xb') as f:f.write(found[0].read_bytes())
g.write(ROOT/'reports/fast_research/PERPETUAL_CAPABILITY_ACTUAL_METADATA_20261003_V1.json',dict(
 status='CAPABILITY_CLOSED_SYNTHETIC_SIGNED_FILLS_WALLET_AND_REFERENCE_NOT_MARKET_RETURN',
 task_id=os.environ['COIN_TASK_ID'],roles=roles,closed_tasks=tasks,archived_metadata=copied,
 witness=dict(path=target.relative_to(ROOT).as_posix(),sha256=witness_sha,original_path=str(found[0])),
 preserved_root_initialization_failures=failed,failure_market_arrays_read=False,old_green_tests_replayed=False,
 no_economic_or_APR_claim=True,locked_consumed=False,orders_sent=0))
print(json.dumps(dict(witness_sha256=witness_sha,short_simulated_fills=len(value['modes']['SHORT_ONLY']['trades']),
 net_results_SYNTHETIC_ONLY={mode:row['summary']['net_PnL'] for mode,row in value['modes'].items()},old_market_QA_replayed=False)))
