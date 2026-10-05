"""Verify stopped original L1 immutable manifest file identities, no data QA."""
import hashlib,json,os,resource,time
from pathlib import Path
from datetime import UTC,datetime
from quant import resources
from task_progress_sample import write_snapshot
OUT=Path('/home/xflops/coin-state/d075-runtime-restoration-20261005-v1')
STORE=Path('/mnt/d/codex/coin/data/microstructure_v1')
CATALOG=OUT/'MICRO_MANIFESTS_BEFORE.json'
CATALOG_SHA=hashlib.sha256(CATALOG.read_bytes()).hexdigest()
PRES=OUT/'PRESERVATION.json'
PRES_SHA=hashlib.sha256(PRES.read_bytes()).hexdigest()

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def active():
    result=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            command=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()
            if any(x in command for x in (' -m quant.collector_public_v3',' -m quant.microstructure')):result.append(dict(pid=int(p.name),command=command))
        except (OSError,UnicodeError):pass
    return result
assert not active(),active()
assert sha(CATALOG)==CATALOG_SHA and sha(PRES)==PRES_SHA
pres=json.loads(PRES.read_text());rows=json.loads(CATALOG.read_text())
assert len(rows)==pres['manifest_count'] and len({r['path'] for r in rows})==len(rows)
assert Path(pres['microstructure']['binding']['store'])==STORE
assert not STORE.is_symlink() and STORE.resolve()==STORE
start=time.monotonic();results=[];errors=[];volume=0
for index,row in enumerate(rows):
    path=STORE/row['path'];item=dict(path=row['path'],expected_bytes=row['bytes'],expected_sha256=row['sha256'])
    try:
        assert not Path(row['path']).is_absolute() and path.resolve().is_relative_to(STORE)
        assert not any(p.is_symlink() for p in (path,*path.parents)), 'Symlink in manifest path'
        before=path.stat();assert path.is_file(), 'Not an ordinary file'
        item.update(actual_bytes=before.st_size,actual_sha256=sha(path),mtime_ns=before.st_mtime_ns)
        after=path.stat()
        assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino), 'Input changed during streaming SHA'
        assert item['actual_bytes']==row['bytes'], 'Size mismatch'
        assert item['actual_sha256']==row['sha256'], 'SHA mismatch'
        item['status']='EXACT';volume+=before.st_size
    except Exception as error:
        item.update(status='ERROR',error_type=type(error).__name__,error=str(error));errors.append(item)
    results.append(item)
    if (index+1)%20==0 or index+1==len(rows):
        state=resources.status()
        assert time.monotonic()-start<900 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<750_000_000
        write_snapshot(dict(pid=os.getpid(),task_id=os.environ['COIN_TASK_ID'],updated_at=time.time(),phase='原L1冻结清单文件身份核验',completed=index+1,total=len(rows),unit='文件',metrics={'已核验字节':volume,'错误数':len(errors)},detail='只读流式SHA；不回放或重新运行数据QA'))
assert not active(),active()
assert sha(CATALOG)==CATALOG_SHA and sha(PRES)==PRES_SHA
report=dict(status='ALL_ORIGINAL_L1_MANIFEST_PAYLOAD_IDENTITIES_EXACT_NOT_DATA_QUALIFICATION' if not errors else 'FAILED_ORIGINAL_L1_MANIFEST_PAYLOAD_IDENTITIES',task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),
    helper_path=str(Path(__file__).resolve()),helper_sha256=sha(Path(__file__)),preservation_sha256=PRES_SHA,catalogue_path=str(CATALOG),catalogue_sha256=CATALOG_SHA,
    store=str(STORE),required_files=len(rows),checked_files=len(results),exact_files=len(results)-len(errors),total_exact_payload_bytes=volume,elapsed_seconds=time.monotonic()-start,
    process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,shared_resources=resources.status(),results=results,errors=errors,
    original_files_read_only=True,symlinks_allowed=False,original_database_SQL_opened=False,new_QA_runs=0,model_fits=0,downloads=0,locked_consumed=False,orders_sent=0,restarted=False,
    scope='Copied closed DB catalogue membership/bytes/SHA identity only; no validity-day or alpha qualification claim')
target=OUT/'MANIFEST_IDENTITIES.json'
with target.open('x') as f:json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
print(json.dumps({k:report[k] for k in ('status','task_id','checked_files','exact_files','total_exact_payload_bytes','elapsed_seconds','process_peak_RSS_bytes')},ensure_ascii=False),flush=True)
if errors:raise SystemExit(1)