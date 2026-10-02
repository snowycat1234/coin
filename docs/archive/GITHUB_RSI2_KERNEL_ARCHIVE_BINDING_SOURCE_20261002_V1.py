"""Metadata-only official RSI2 source/export proof; no indicator/market execution."""
import argparse,hashlib,json,os,resource,shlex,subprocess,sys,time
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state');VENDOR=ROOT/'third_party/jesse_example_rsi2'
OUT=ROOT/'reports/GITHUB_RSI2_KERNEL_ARCHIVE_SOURCE_BINDING_20261002_V1.json'
SELF_ARCHIVE=ROOT/'docs/archive/GITHUB_RSI2_KERNEL_ARCHIVE_BINDING_SOURCE_20261002_V1.py'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(ok,message):
    if not bool(ok):raise ValueError(message)
def write(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def proof(path):
    path=Path(path);need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT),'Ordinary repository source only')
    need(path.stat().st_size<1000000 and path.suffix not in ('.whl','.so','.gz','.sqlite3','.parquet','.arrow','.zip'),'Small code/license/metadata only')
    return str(path.relative_to(ROOT)),sha(path)
p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args();work=a.run_dir.resolve()
need(not work.exists() and not OUT.exists() and work.is_relative_to(STATE),'Exclusive STATE and report required')
need(sys.prefix==str(STATE/'v8-clean-env-20261002-v2'),'Frozen clean interpreter required')
need(sha(ROOT/'environments/v8/uv.lock')=='97335dc3dbb04d7dbc67425f91d4e941a0cfd2c84e5f2adcd852514ec4600de6','Base lock unchanged')
need(sha(__file__)==sha(SELF_ARCHIVE),'Export helper exact archive required')
work.mkdir();binding=dict(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),task_id=os.environ['COIN_TASK_ID'],exact_command=shlex.join([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]),helper_source_sha256=sha(__file__),helper_archive_path=str(SELF_ARCHIVE.relative_to(ROOT)),helper_archive_sha256=sha(SELF_ARCHIVE),base_environment_lock_sha256=sha(ROOT/'environments/v8/uv.lock'),base_sys_prefix=sys.prefix,data_scope='EXISTING_CODE_LICENSE_AND_SMALL_JSON_METADATA_ONLY',seed='NOT_APPLICABLE',models_fit=0,GPU=0)
write(work/'RUN_BINDING.json',binding);write(work/'START.json',dict(binding,status='PREBOUND_START',created_utc=datetime.now(UTC).isoformat()))
report=dict(status='FAIL_METADATA_ONLY_RSI2_KERNEL_ARCHIVE_BINDING',binding=binding,run_dir=str(work),source_hashes={},market_inputs_read=False,locked_consumed=False,models_fit=0,orders_sent=0,GPU=0,kernel_called=False,old_green_tests_rerun=0)
started=time.monotonic()
try:
    pairs=[('rsi2-dependency-install-operation-20261002-v1.py','RSI2_KERNEL_DEPENDENCY_OPERATION_SOURCE_20261002_V1.py','b05184339d48c96285106a2000ba547a966e854836612d7bc0bafa4689321965'),('rsi2-dependency-install-operation-20261002-v2.py','RSI2_KERNEL_DEPENDENCY_OPERATION_SOURCE_20261002_V2.py','8608d19481499b39f4784816ce5f8c8f2e125ac74b10c039903e6f726da8f204'),('rsi2-dependency-install-operation-20261002-v3.py','RSI2_KERNEL_DEPENDENCY_OPERATION_SOURCE_20261002_V3.py','cc26054d34b9c01fdbcfa6db5f501a5a23885fa50bbc809b134521e5117cb956'),('rsi2-kernel-semantics-operation-20261002-v1.py','RSI2_KERNEL_SEMANTICS_OPERATION_SOURCE_20261002_V1.py','d46eea03597608a526639c0847cff8d245f875cc6ec47b44d820b7118e95cfca')]
    archives=[];paths=[ROOT/'scripts/investment/public_rsi2_indicator.py',ROOT/'docs/archive/PUBLIC_RSI2_PROTOCOL_FREEZE_SOURCE_20261002_V1.py',SELF_ARCHIVE]
    for original,archive,expected in pairs:
        source=STATE/original;destination=ROOT/'docs/archive'/archive;need(sha(source)==sha(destination)==expected,'Actual operation source/archive changed')
        paths.append(destination);archives.append(dict(original_actual_operation_path=str(source),archive_path=str(destination.relative_to(ROOT)),source_sha256=expected,archive_sha256=expected,byte_exact=True,bytes=destination.stat().st_size))
    freeze_original=ROOT/'.cache/freeze_public_rsi2_20261002_v1.py';freeze_archive=ROOT/'docs/archive/PUBLIC_RSI2_PROTOCOL_FREEZE_SOURCE_20261002_V1.py';need(sha(freeze_original)==sha(freeze_archive),'Protocol freeze archive changed')
    reports=[ROOT/'reports/fast_research'/name for name in ('RSI2_OFFICIAL_KERNEL_DEPENDENCY_INSTALL_20261002_V1.json','RSI2_OFFICIAL_KERNEL_DEPENDENCY_INSTALL_20261002_V2.json','RSI2_OFFICIAL_KERNEL_DEPENDENCY_INSTALL_20261002_V3.json','RSI2_OFFICIAL_KERNEL_SEMANTICS_20261002_V1.json','RSI2_OFFICIAL_KERNEL_ACTUAL_EXIT_20261002_V1.json')]
    paths.extend(reports);paths.extend(path for path in VENDOR.iterdir() if path.is_file());report['source_hashes']=dict(proof(path) for path in paths)
    actual_exit=json.loads(reports[-1].read_text());need(actual_exit['status']=='PASS_FINAL_DEPENDENCY_AND_SEMANTICS_ACTUAL_EXIT_FAILURES_PRESERVED' and len(actual_exit['runs'])==4,'Actual failure/recovery exit evidence required')
    checks=[]
    for row in actual_exit['runs']:
        receipt=ROOT/row['report_path'];need(sha(receipt)==row['report_sha256'],'Actual operation report changed')
        progress_path=STATE/'task-progress'/('task-'+row['task_id']+'.json');progress=json.loads(progress_path.read_text());need(sha(progress_path)==row['task_progress_sha256'] and progress['exit_code']==row['actual_exit_code'] and progress['status']==row['actual_progress_status'],'Actual operation task metadata changed')
        actual=json.loads(receipt.read_text());need(actual['binding']['helper_source_sha256'] in {v['source_sha256'] for v in archives},'Actual helper must be portable archived source')
        checks.append(dict(report_path=row['report_path'],report_sha256=row['report_sha256'],task_id=row['task_id'],actual_status=progress['status'],actual_exit_code=progress['exit_code']))
    need([v['actual_exit_code'] for v in checks]==[1,1,0,0],'Preserved failed installs and successful recovery/semantics expected')
    report.update(status='PASS_METADATA_ONLY_RSI2_KERNEL_ARCHIVE_BINDING_FAILURES_PRESERVED',actual_operation_archives=archives,actual_completed_operations=checks,protocol_freeze_archive=dict(path=str(freeze_archive.relative_to(ROOT)),sha256=sha(freeze_archive),original_sha256=sha(freeze_original)),source_hash_scope='ONLY_SMALL_REPOSITORY_CODE_ARCHIVES_OFFICIAL_VENDOR_AND_FIVE_EXISTING_JSON_RECEIPTS',external_runtime_binary_and_market_files_excluded=True,environment_not_modified=True)
    need(sha(ROOT/'environments/v8/uv.lock')==binding['base_environment_lock_sha256'],'Base lock changed')
except Exception as error:
    report.update(error_type=type(error).__name__,reason=str(error));raise
finally:
    report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    write(OUT,report);print(json.dumps(dict(status=report['status'],output=str(OUT),sha256=sha(OUT))))