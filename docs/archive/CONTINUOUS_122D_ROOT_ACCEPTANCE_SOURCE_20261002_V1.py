import hashlib,json,subprocess
from datetime import UTC,datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
prefix='reports/fast_research/'
proofs={
 'SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_20261002_V1.json':'62cb5604580e3af8de3bcf7d1db5f76343581ef44f656ba89f927ba4bdb24e94',
 'SIMPLE_STRATEGY_CONTINUOUS_122D_TINY_20261002_V1.json':'3cb1b46b66a9ae50148eaeaf8a0e18a63c3d3ca61ca1cf2f171179c3c2084e12',
 'SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_EXIT_MONTHS_20261002_V1.json':'601356b8a47dc046683fe446bea70af9552eb52aaf6bd8da0eceeff6ac0aa599',
 'SIMPLE_STRATEGY_CONTINUOUS_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json':'f4046253f6349e0a23d9150a02a0b157d4b546a9a752261e2b950c456bd5391d',
 'SIMPLE_STRATEGY_CONTINUOUS_122D_AUDIT_ACTUAL_EXIT_20261002_V1.json':'8e2688505b34444001cde3de1c2989113a7169d1f603cd31f67653dfc01f95e7'}
proofs={prefix+k:v for k,v in proofs.items()}
for path,expected in proofs.items():assert sha(root/path)==expected,path
read=lambda name:json.loads((root/(prefix+name)).read_text())
actual=read('SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_20261002_V1.json')
audit=read('SIMPLE_STRATEGY_CONTINUOUS_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json')
execution=read('SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_EXIT_MONTHS_20261002_V1.json')
audit_exit=read('SIMPLE_STRATEGY_CONTINUOUS_122D_AUDIT_ACTUAL_EXIT_20261002_V1.json')
assert actual['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and actual['completed_ledgers']==actual['planned_ledgers']==12
assert actual['all_planned_ledgers_complete'] and actual['source_bytes_unchanged']
assert execution['actual_outer_exit']==0 and execution['actual_outer_session']==33281
assert audit['status']=='PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE' and audit['completed_ledgers_verified']==12
assert audit_exit['independent_actual_tool_exit']['exit_code']==0
assert len(actual['folds'])==1 and actual['folds'][0]['days']==122
assert actual['account_continuity']=='SINGLE_CONTINUOUS_PERIOD_BY_STRATEGY_AND_COST'
assert actual['market_models_fit']==actual['orders_sent']==0 and not actual['locked_consumed']
assert not actual['resources']['gpu_used'] and actual['resources']['swap_bytes']==0
sources=actual['binding']['source_hashes']
for path,expected in sources.items():assert sha(root/path)==expected,path
assert sources['src/quant/backtest.py']=='ee333d4e5cbadb489e5d467619d0872f78ccb2d86d8b5f46eacc69cb63f9829a'
expected=['CASH','SPOT_BUY_AND_HOLD','VOL_MANAGED_BUY_AND_HOLD','COIN_JESSE_DONCHIAN_1H_SPOT_ADAPTER']
assert actual['binding']['strategies']==expected
tasks=[]
for item in audit_exit['tasks'].values():
    p=Path(item['path']);v=json.loads(p.read_text())
    assert sha(p)==item['sha256'] and v['status']=='completed' and v['exit_code']==0
    tasks.append(dict(path=str(p),sha256=sha(p),id=v['id'],exit_code=0))
receipt=dict(status='ROOT_ACCEPTED_CONTINUOUS122DAY_PROXY_ECONOMIC_COMPARISON_ONLY',created_utc=datetime.now(UTC).isoformat(),
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 source_hashes=sources,verified_prior_files=proofs,actual_task_bindings=tasks,
 actual_session=33281,actual_exit=0,independent_exit=0,completed_accounts=12,continuous_days=122,
 economic_qualification='NO_QUALIFIED_CANDIDATE',main_profitable_strategy=None,
 public_port_retained_as='DEFENSIVE_RESEARCH_REFERENCE_NOT_PROFITABLE_MAIN',
 decision='D012: public1h negative net versus cash despite positive same-qty gross. Next exactly one preregistered2h turnover/horizon probe, unchanged fees/risk/sources; no HPO.',
 period_aggregates=actual['aggregate'],source_bytes_unchanged=True,earlier_green_or72_ledger_reruns=0,
 monthly_continuity_and_PnL_reconciliation=True,unseen=False,long_term_net_APR_proven=False,real_BBO=False,
 locked_consumed=False,models_fit=0,orders_sent=0,GPU_hours=0,
 peak_orchestrator_RSS_bytes=actual['orchestrator_peak_RSS_bytes'],owned_bytes=actual['owned_bytes'],
 latest_actual_disk_scan=actual['disk'],resources=actual['resources'])
out=root/(prefix+'CONTINUOUS_122D_ROOT_MODULE_ACCEPTANCE_20261002_V1.json')
with out.open('x') as f:json.dump(receipt,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
git_sources=dict(sources);runtime={'state/dataset_lock.json':git_sources.pop('state/dataset_lock.json')}
binding=dict(status='GIT_SOURCE_BINDING_EXCLUDES_IGNORED_RUNTIME_LOCK',source_hashes=git_sources,
 verified_prior_files={str(out.relative_to(root)):sha(out),**proofs},verified_runtime_not_for_upload=runtime,
 scope='Root full binding verifies runtime lock; Git review only committed sources, no market rerun.')
with (root/'reports/GITHUB_CONTINUOUS_122D_SOURCE_BINDING_20261002_V1.json').open('x') as f:
    json.dump(binding,f,indent=2);f.write('\n')
print(json.dumps(dict(status=receipt['status'],sha256=sha(out))))
