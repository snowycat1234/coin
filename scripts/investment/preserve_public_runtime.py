"""Preserve the stopped original collectors before any authorized restart."""
import argparse,hashlib,json,os,shutil,sqlite3,subprocess,time
from datetime import UTC,datetime
from pathlib import Path
from quant import disk,resources
from quant.paths import ROOT,STATE
from quant import collector_public_v3 as public
from quant.microstructure import read_microstructure_status
ap=argparse.ArgumentParser()
for name in ('out','prior-preservation','prior-launch','prior-sample'):ap.add_argument('--'+name,required=True)
args=ap.parse_args();OUT=Path(args.out)
assert OUT.resolve().is_relative_to(STATE) and not OUT.exists()
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def save(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
def active():
 found=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdecimal():continue
  try:
   argv=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x]
   if '-m' in argv and argv[argv.index('-m')+1] in ('quant.collector_public_v3','quant.microstructure','quant.microstructure_v2'):found.append(dict(pid=int(p.name),argv=argv))
  except (OSError,UnicodeError,IndexError):pass
 return found
assert not active(),active()
OUT.mkdir(exist_ok=True);raw=OUT/'raw-preserved';raw.mkdir();work=OUT/'derivative-working';work.mkdir();closed=OUT/'closed-derivatives';closed.mkdir()
prior=read(args.prior_preservation)
for n,h in prior['source_hashes'].items():assert sha(ROOT/n)==h,n
assert sha(ROOT/'src/quant/microstructure.py')==prior['microstructure']['binding']['implementation_sha256']
assert public.source_contract(STATE/'collector_public_v3.sqlite3',engineering=False)==prior['public']['contract']
paths=[STATE/(n+s) for n in ('collector_public_v3.sqlite3','microstructure.sqlite3') for s in ('','-wal','-shm')]
launch=read(args.prior_launch)
paths += [Path(item[k]) for item in launch['launches'] for k in ('stdout','stderr')]
paths += [Path(item['path']) for item in read(args.prior_sample)['actual_task_receipts']]
paths += [ROOT/'state/collector-public-v3-host.json',ROOT/'state/microstructure-host.json']
missing=[str(p) for p in paths if not p.is_file()]
existing=[p for p in paths if p.is_file()]
assert all(not p.is_symlink() for p in existing)
reserve=3*sum(p.stat().st_size for p in existing)+1_000_000_000
before=time.monotonic();capacity=disk.check(reserve);capacity['measured_utc']=datetime.now(UTC).isoformat()
assert capacity['total_bytes']+reserve<32_000_000_000
assert not active(),active()
saved=[]
for i,p in enumerate(existing):
 dest=raw/f'{i:02d}-{p.name}';digest=sha(p)
 with p.open('rb') as src,dest.open('xb') as dst:shutil.copyfileobj(src,dst)
 assert sha(dest)==sha(p)==digest
 saved.append(dict(source=str(p),saved=str(dest),bytes=p.stat().st_size,sha256=digest))
backups=[]
for name in ('collector_public_v3.sqlite3','microstructure.sqlite3'):
 for suffix in ('','-wal','-shm'):
  source=next((r for r in saved if r['source']==str(STATE/(name+suffix))),None)
  if source:shutil.copyfile(source['saved'],work/(name+suffix))
 assert (work/name).is_file()
 a=sqlite3.connect(f'file:{work/name}?mode=ro',uri=True);b=sqlite3.connect(closed/name)
 try:
  a.backup(b,pages=256);b.commit();assert b.execute('PRAGMA quick_check').fetchall()==[('ok',)]
  assert b.execute('PRAGMA journal_mode=DELETE').fetchone()[0]=='delete'
 finally:b.close();a.close()
 backups.append(dict(path=str(closed/name),bytes=(closed/name).stat().st_size,sha256=sha(closed/name),quick_check='ok'))
c=sqlite3.connect(f'file:{closed/"collector_public_v3.sqlite3"}?mode=ro&immutable=1',uri=True);c.row_factory=sqlite3.Row
try:
 contract,head=public.verify_registry(c)
 session=dict(c.execute('SELECT * FROM sessions ORDER BY id DESC LIMIT 1').fetchone())
 bars=[dict(r) for r in c.execute('SELECT symbol,COUNT(*) bars,MAX(open_ms) last_open_ms,MAX(websocket_received_ms) last_websocket_received_ms FROM closed_bars GROUP BY symbol')]
 lifecycle=[dict(r) for r in c.execute('SELECT * FROM public_lifecycle ORDER BY seq DESC LIMIT 6')]
finally:c.close()
assert contract==prior['public']['contract']
micro=read_microstructure_status(closed/'microstructure.sqlite3')
assert micro['binding']==prior['microstructure']['binding']
c=sqlite3.connect(f'file:{closed/"microstructure.sqlite3"}?mode=ro&immutable=1',uri=True);c.row_factory=sqlite3.Row
try:
 manifests=[dict(r) for r in c.execute('SELECT * FROM manifests ORDER BY path')]
 audit=[dict(r) for r in c.execute('SELECT * FROM audit ORDER BY seq DESC LIMIT 8')]
finally:c.close()
save(OUT/'MICRO_MANIFESTS_BEFORE.json',manifests);save(OUT/'MICRO_CHECKPOINT_BEFORE.json',micro['checkpoint'])
for r in saved:assert sha(r['source'])==r['sha256']==sha(r['saved'])
assert not active(),active()
receipt=dict(status='STOPPED_ORIGINAL_COLLECTORS_PRESERVED_NOT_RESTARTED',created_utc=datetime.now(UTC).isoformat(),
 task_id=os.environ['COIN_TASK_ID'],saved_files=saved,missing_before_preservation=missing,closed_backups=backups,
 public=dict(contract=contract,lifecycle_head=head,session=session,bars=bars,lifecycle_tail=lifecycle),microstructure=micro,
 micro_audit_tail=audit,manifest_count=len(manifests),source_hashes=prior['source_hashes'],capacity=capacity,
 resources=resources.status(),elapsed_seconds=time.monotonic()-before,uptime=subprocess.check_output(['uptime'],text=True),
 boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),exit_code='UNKNOWN',exit_reason='UNKNOWN',
 original_SQL_opened=False,originals_preserved_stable=True,restarted=False,healthy_gap_splicing=False,
 store_payload_hashes_checked=False,helper_sha256=sha(__file__),owned_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()))
save(OUT/'PRESERVATION.json',receipt)
publication=dict(ledger=capacity,measured_at=datetime.fromisoformat(capacity['measured_utc']).timestamp(),source='Existing physical guard before stopped-source backup')
tmp=OUT/'last-disk.tmp';tmp.write_text(json.dumps(publication));tmp.replace(STATE/'task-progress/last-disk.json')
print(json.dumps(dict(status=receipt['status'],out=str(OUT),disk=capacity['total_bytes'],reserved=reserve,owned=receipt['owned_bytes'],manifests=len(manifests))))
