"""Preserve stopped original public collectors; SQL opens copies only."""
from pathlib import Path
from datetime import UTC, datetime
import hashlib, json, os, shutil, sqlite3, time
from quant import disk, resources
from quant.paths import ROOT, STATE
from quant import collector_public_v3 as public
from quant.microstructure import read_microstructure_status
OUT=STATE/'d066-public-collector-preservation-20261004-v1'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False)
def active():
    result=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()
            if any(x in cmd for x in (' -m quant.collector_public_v3',' -m quant.microstructure')):
                result.append(dict(pid=int(p.name),command=cmd))
        except (OSError,UnicodeError):pass
    return result
assert OUT.is_dir() and OUT.resolve().is_relative_to(STATE.resolve())
assert not active(),active()
originals=[STATE/(name+suffix) for name in ('collector_public_v3.sqlite3','microstructure.sqlite3') for suffix in ('','-wal','-shm')]
originals += [STATE/'v7-runtime-preservation-20261002-v3'/('public-v3-new.'+s+'.log') for s in ('stdout','stderr')]
originals += [STATE/'v8-l1-clock-preservation-20261002-v2'/('microstructure-recovery.'+s+'.log') for s in ('stdout','stderr')]
originals += [STATE/'task-progress/task-16050f18b5584e98a1e5ff61fb3bc2e5.json',STATE/'task-progress/task-7ed0a9c3456b4d90a947a217d1dd4906.json']
originals += [ROOT/'state/collector-public-v3-host.json',ROOT/'state/microstructure-host.json']
originals += [ROOT/'.cache/v7_restart_public_20261002_v3.sh',ROOT/'.cache/v8_restart_l1_20261002_v2.sh',ROOT/'reports/fast_research/V7_PUBLIC_COLLECTOR_RECOVERY_20261002_V1.json',ROOT/'reports/fast_research/V8_L1_CLOCK_INCIDENT_PRESERVATION_20261002_V2.json']
assert all(p.is_file() and not p.is_symlink() for p in originals)
reserve=3*sum(p.stat().st_size for p in originals)+1_000_000_000
before=time.monotonic();capacity=disk.check(reserve)
capacity.update(measured_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-before)
assert capacity['total_bytes']+reserve<32_000_000_000
assert not active(),active()
raw=OUT/'raw-preserved';raw.mkdir()
working=OUT/'derivative-working';working.mkdir()
closed=OUT/'closed-derivatives';closed.mkdir()
saved=[]
for i,p in enumerate(originals):
    item=dict(source=str(p),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns,sha256=sha(p))
    target=raw/f'{i:02d}-{p.name}'
    with target.open('xb') as f:
        with p.open('rb') as source:shutil.copyfileobj(source,f)
    assert sha(p)==item['sha256']==sha(target)
    item['saved']=str(target);saved.append(item)
assert not active(),active()
backups=[]
for index,name in enumerate(('collector_public_v3.sqlite3','microstructure.sqlite3')):
    for offset,suffix in enumerate(('','-wal','-shm')):
        item=saved[index*3+offset]
        shutil.copyfile(item['saved'],working/(name+suffix))
    source=sqlite3.connect(f'file:{working/name}?mode=ro',uri=True)
    target=closed/name;destination=sqlite3.connect(target)
    try:
        source.backup(destination,pages=256)
        destination.commit()
        assert destination.execute('PRAGMA quick_check').fetchall()==[('ok',)]
        assert destination.execute('PRAGMA journal_mode=DELETE').fetchone()[0]=='delete'
    finally:destination.close();source.close()
    backups.append(dict(path=str(target),bytes=target.stat().st_size,sha256=sha(target),closed=True,quick_check='ok',source_original_SQL_opened=False))
old=json.loads((raw/'16-V7_PUBLIC_COLLECTOR_RECOVERY_20261002_V1.json').read_text())
public_db=sqlite3.connect(f'file:{closed/"collector_public_v3.sqlite3"}?mode=ro&immutable=1',uri=True)
try:
    contract,head=public.verify_registry(public_db)
    public_db.row_factory=sqlite3.Row
    session=public_db.execute('SELECT * FROM sessions ORDER BY id DESC LIMIT 1').fetchone()
    lifecycle=[dict(r) for r in public_db.execute('SELECT * FROM public_lifecycle ORDER BY seq DESC LIMIT 6')]
    for row in lifecycle:row['payload']=json.loads(row['payload'])
    columns=[r[1] for r in public_db.execute('PRAGMA table_info(closed_bars)')]
    bars=[dict(r) for r in public_db.execute('SELECT symbol,COUNT(*) bars,MAX(open_ms) last_open_ms,MAX(websocket_received_ms) last_websocket_received_ms FROM closed_bars GROUP BY symbol')]
    public_state=dict(contract=contract,lifecycle_head=head,session=dict(session) if session else None,lifecycle_tail=lifecycle,bars=bars,closed_bars_columns=columns)
finally:public_db.close()
current_contract=public.source_contract(STATE/'collector_public_v3.sqlite3',engineering=False)
assert contract==old['public_v3']['contract']==current_contract
micro=read_microstructure_status(closed/'microstructure.sqlite3')
assert micro['binding']==old['microstructure']['binding']
assert micro['binding']['implementation_sha256']==sha(ROOT/'src/quant/microstructure.py')
micro_db=sqlite3.connect(f'file:{closed/"microstructure.sqlite3"}?mode=ro&immutable=1',uri=True)
micro_db.row_factory=sqlite3.Row
try:
    audit=[dict(r) for r in micro_db.execute('SELECT * FROM audit ORDER BY seq DESC LIMIT 8')]
    for row in audit:row['payload']=json.loads(row['payload'])
    manifests=[dict(r) for r in micro_db.execute('SELECT * FROM manifests ORDER BY path')]
finally:micro_db.close()
save(OUT/'MICRO_CHECKPOINT_BEFORE.json',micro['checkpoint'])
save(OUT/'MICRO_MANIFESTS_BEFORE.json',manifests)
assert not active(),active()
for item in saved:assert sha(item['source'])==item['sha256']==sha(item['saved'])
report=dict(status='STOPPED_ORIGINAL_PUBLIC_COLLECTORS_PRESERVED_COPIES_AND_SOURCE_BINDINGS_VERIFIED_NOT_RESTARTED',created_utc=datetime.now(UTC).isoformat(),
    task_id=os.environ.get('COIN_TASK_ID'),source_helper_path=str(Path(__file__).resolve()),source_helper_sha256=sha(Path(__file__)),
    all_process_absence_verified=True,processes_current=active(),exit_code='UNKNOWN',exit_reason='UNKNOWN',
    saved_files=saved,closed_backups=backups,public=public_state,microstructure=micro,micro_audit_tail=audit,
    resources=resources.status(),capacity_before_copy=capacity,source_hashes=contract['sources'],
    original_source_bindings_match_prior=True,original_databases_never_opened_by_SQL=True,original_source_files_stable_after_derivative_queries=True,
    database_names=['collector_public_v3.sqlite3','microstructure.sqlite3'],microstructure_version='microstructure_l1_v1',
    manifest_count=len(manifests),manifest_catalog_preserved=True,manifest_store_payload_SHA_verification='NOT_PERFORMED',
    original_start_commands=[dict(shell=str(ROOT/'.cache/v7_restart_public_20261002_v3.sh'),command='.venv/bin/python -u -m quant.collector_public_v3 --run'),dict(shell=str(ROOT/'.cache/v8_restart_l1_20261002_v2.sh'),command='.venv/bin/python -u -m quant.microstructure --run')],
    stopped_tasks=[json.loads((raw/f'{i:02d}-{originals[i].name}').read_text()) for i in (10,11)],
    public_stop_file_present=(ROOT/'state/collector_public_v3.stop').exists(),
    restart_prerequisites=['Root inspect preserved audit/checkpoints/termination evidence','Verify original manifest file identities if required','Fresh capacity/resource/absence check','Use unchanged existing .venv and original default DB/store, new exclusive stdout/stderr and task; no v2 switch','Actual new sessions must record gap; no healthy-time splicing'],
    market_downloads=0,keys_read=False,orders_sent=0,locked_consumed=False,gpu_hours=0,restarted=False,live_data_qualification='NOT_CERTIFIED',
    original_to_check_time=dict(public_last_websocket_ms=max(r['last_websocket_received_ms'] or 0 for r in bars),micro_checkpoint_asof_us=micro['checkpoint'].get('asof_us'),checked_us=time.time_ns()//1000),
    new_owned_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()))
save(OUT/'PUBLIC_COLLECTOR_PRESERVATION_20261004_V1.json',report)
print(json.dumps(dict(status=report['status'],task_id=report['task_id'],report=str(OUT/'PUBLIC_COLLECTOR_PRESERVATION_20261004_V1.json'),public_last=public_state['lifecycle_tail'][0],micro_last=micro['last_audit'],capacity_total=capacity['total_bytes'],owned_bytes=report['new_owned_bytes']),ensure_ascii=False),flush=True)