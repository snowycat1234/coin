"""Metadata-only actual auditor exit and pure code archives; no ledger reads."""
from pathlib import Path
from datetime import UTC,datetime
import hashlib,json,os,shutil,sys
ROOT=Path('/mnt/d/codex/coin');STATE=Path(__file__).parent.resolve()
REPORT=ROOT/'reports/fast_research/PUBLIC_RSI2_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json'
OUT=ROOT/'reports/fast_research/PUBLIC_RSI2_NATIVE_SIX_LEDGER_AUDIT_EXIT_AND_CODE_BINDING_20261002_V1.json'
CHECKER=ROOT/'docs/archive/PUBLIC_RSI2_NATIVE_SIX_LEDGER_AUDIT_CHECKER_20261002_V1.py'
EXPORT=ROOT/'docs/archive/PUBLIC_RSI2_NATIVE_SIX_LEDGER_EXIT_EXPORT_20261002_V1.py'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def need(ok,message):
    if not ok:raise ValueError(message)
def task(task_id):
    path=Path('/home/xflops/coin-state/task-progress')/('task-'+task_id+'.json');value=read(path)
    need(value['id']==task_id and value['status']=='completed' and value['exit_code']==0 and value['pid']>0 and value['start_ticks']>0,'Real completed0 task binding')
    return {'path':str(path),'sha256':sha(path),'task':value}
need(os.environ.get('COIN_TASK_ID') and not OUT.exists() and not EXPORT.exists(),'Exclusive metadata export')
need(sha(REPORT)=='36ae8d6deb965e93d618d61b537f05587caf185ca33342fe50bc63e21a4e6b07','Frozen independent audit report')
audit=read(REPORT);binding=read(STATE/'RUN_BINDING.json')
need(audit['status']=='PASS_RSI2_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_AND_CAUSAL_SCOPE' and audit['completed_ledgers_verified']==len(audit['ledgers'])==6,'Six new verified RSI2 blocks')
need(binding==audit['binding'] and sha(STATE/'RUN_BINDING.json')==audit['run_binding_sha256'] and binding['checker_sha256']==audit['independent_source_sha256']==sha(STATE/'audit.py')=='9da9581635ae73bda0926fb3f53904ff190a556569b1d83a50cbd88e55aa55bb','Frozen actual auditor code and RUN_BINDING')
need(binding['financial_block_bytes_identical'] and binding['financial_block_sha256']=='4b6e0514898676ea2fc1a75881917b2cb480e5f2f0501621008e13617924d04f','Original native financial block exact')
actual_auditor=task(binding['task_id']);parents=[]
for period in audit['period_bindings']:
    report_path=Path(period['report_path']);parent=read(report_path)
    need(sha(report_path)==period['report_sha256'] and parent['completed_ledgers']==3 and parent['all_planned_ledgers_complete'],'Parent three completed report bytes')
    actual_parent=task(parent['binding']['task_id'])
    need(actual_parent==period['actual_task'],'Parent task matches independent audit receipt')
    need(all(sha(ROOT/p)==d for p,d in parent['binding']['source_hashes'].items()),'Current declared source bytes preserved')
    parents.append({'period':period['label'],'report_path':str(report_path),'report_sha256':sha(report_path),'actual_host_session_id':period['actual_host_session_id'],'actual_task':actual_parent,'protocol_sha256':period['protocol_sha256']})
need(len(parents)==2 and {p['period'] for p in parents}=={'122','90'},'Two explicit parent periods')
if CHECKER.exists():need(sha(CHECKER)==audit['independent_source_sha256'],'Existing root checker archive exact byte identity')
else:shutil.copyfile(STATE/'audit.py',CHECKER)
shutil.copyfile(__file__,EXPORT)
need(sha(CHECKER)==audit['independent_source_sha256'] and sha(EXPORT)==sha(__file__),'Pure code original bytes archived')
result={'version':'PUBLIC_RSI2_NATIVE_SIX_LEDGER_AUDIT_EXIT_AND_CODE_BINDING_20261002_V1','status':'PASS_ACTUAL_EXIT0_AND_PURE_CODE_BYTE_BINDING','scope':'Only report/task/source metadata and pure-code archive; zero new market/test/ledger/math runs','audit_report_path':str(REPORT.relative_to(ROOT)),'audit_report_sha256':sha(REPORT),'audit_status':audit['status'],'completed_ledgers_verified':6,'actual_auditor_host_session_id':48782,'actual_auditor_task':actual_auditor,'run_binding_path':str(STATE/'RUN_BINDING.json'),'run_binding_sha256':sha(STATE/'RUN_BINDING.json'),'checker_archive_path':str(CHECKER.relative_to(ROOT)),'checker_archive_sha256':sha(CHECKER),'checker_archive_bytes':CHECKER.stat().st_size,'metadata_export_archive_path':str(EXPORT.relative_to(ROOT)),'metadata_export_sha256':sha(EXPORT),'metadata_export_task_id':os.environ['COIN_TASK_ID'],'metadata_export_exact_command':' '.join(sys.argv),'financial_block_bytes_identical':True,'financial_block_sha256':binding['financial_block_sha256'],'actual_manifest_sha256':binding['actual_manifest_sha256'],'parent_actual_tasks':parents,'peak_RSS_bytes':audit['peak_RSS_bytes'],'candidate_status':'NO_QUALIFIED_CANDIDATE','native_Bybit_market_or_filters_proven':False,'registry_written':False,'additional_market_test_ledger_replays':0,'created_utc':datetime.now(UTC).isoformat()}
source_paths=('scripts/investment/compare_simple_strategies.py','scripts/investment/public_rsi2_adapter.py','scripts/investment/public_rsi2_indicator.py','scripts/investment/bybit_spot_adapter.py','src/quant/backtest.py','src/quant/execution_contract.py','docs/archive/COMPARE_SIMPLE_STRATEGIES_PRE_RSI2_20261002_V1.py',str(CHECKER.relative_to(ROOT)),str(EXPORT.relative_to(ROOT)),'third_party/jesse_example_rsi2/INSTALLED_KERNEL_BINDING_20261002_V1.json','third_party/jesse_example_rsi2/rsi_kernel_original.rs','third_party/jesse_example_rsi2/rsi2_original.py','environments/v8/uv.lock','protocols/PUBLIC_RSI2_BYBIT_122D_V1.json','protocols/PUBLIC_RSI2_BYBIT_90D_V1.json',str(REPORT.relative_to(ROOT)))
source_hashes={p:sha(ROOT/p) for p in source_paths}
need(source_hashes['scripts/investment/compare_simple_strategies.py']=='3dfa0e3176791980de51e5bc990b1998f93eb24c02bdc1261a074eab92fb52f1' and source_hashes['docs/archive/COMPARE_SIMPLE_STRATEGIES_PRE_RSI2_20261002_V1.py']=='bff0fe43a4a46406668a8a7bbe1d298397437a31d6ec623480abff2b2006131e','Current and prior common use distinct frozen paths')
need(all(not Path(p).is_absolute() and (ROOT/p).resolve().is_relative_to(ROOT.resolve()) and (ROOT/p).stat().st_size<2_000_000 for p in source_hashes),'Only project-relative small code/metadata source proof')
result['source_hashes']=source_hashes
result['actual_manifest_proof']={'path':binding['actual_manifest_path'],'sha256':binding['actual_manifest_sha256']}
need(sha(binding['actual_manifest_path'])==binding['actual_manifest_sha256'],'Original ACTUAL_BINDING bytes preserved')
result['official_kernel_metadata']=audit['official_kernel_metadata']
with OUT.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)
print(json.dumps({'status':result['status'],'report':str(OUT),'sha256':sha(OUT),'checker_archive_sha256':sha(CHECKER),'export_archive_sha256':sha(EXPORT),'metadata_task_id':os.environ['COIN_TASK_ID']}))