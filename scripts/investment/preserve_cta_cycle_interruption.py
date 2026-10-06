"""Preserve stopped research and collector bytes before any finite recovery."""
import hashlib,json,os,shutil,sqlite3,subprocess
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False)
def processes():
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            argv=(p/'cmdline').read_bytes().split(b'\0')
            if any(x in argv for x in (b'quant.collector_public_v3',b'quant.microstructure')) or any(x.endswith(b'/run_cta_leaderboard.py') for x in argv):
                found.append(int(p.name))
        except OSError:pass
    return found

assert os.environ.get('COIN_TASK_ID') and not processes()
run=STATE/'d099-fixed-btc-cycle-accounts-20261006-v1'
out=STATE/'d099-interruption-preserved-20261006-v1';out.mkdir()
checkpoint=json.loads((run/'CHECKPOINT.json').read_bytes())
assert len(checkpoint['cases'])==3 and not (ROOT/'reports/fast_research/SHORT_FIXED_CYCLE_2022_2023_BASE27_20261006_V1.json').exists()
paths=[run/'CHECKPOINT.json',run/'RUN_BINDING.json',run/'frozen_signals.parquet',run/'SIGNAL_AVAILABILITY.json',
       ROOT/'scripts/investment/run_cta_leaderboard.py']
for p in (STATE/'task-progress').glob('task-*.json'):
    v=json.loads(p.read_bytes())
    if v.get('id')=='36961787058a4a4c8324836fbfcc03a9' or v.get('pid') in (1172,1173):paths.append(p)
for stem in ('collector_public_v3_20261006.sqlite3','microstructure.sqlite3'):
    paths += [STATE/(stem+s) for s in ('','-wal','-shm') if (STATE/(stem+s)).exists()]
logdir=STATE/'d095-stopped-collector-recovery-20261005-v1'
if logdir.exists():paths += list(logdir.glob('*.log'))
saved=[]
for i,p in enumerate(paths):
    assert not p.is_symlink();h=sha(p);dest=out/f'{i:03d}-{p.name}'
    shutil.copyfile(p,dest);assert sha(p)==sha(dest)==h
    saved.append(dict(source=str(p),saved=str(dest),sha256=h,bytes=dest.stat().st_size))
closed=[]
for stem in ('collector_public_v3_20261006.sqlite3','microstructure.sqlite3'):
    work=out/('working-'+stem)
    for suffix in ('','-wal','-shm'):
        row=next((r for r in saved if r['source']==str(STATE/(stem+suffix))),None)
        if row:shutil.copyfile(row['saved'],str(work)+suffix)
    source=sqlite3.connect(f'file:{work}?mode=ro',uri=True);dest=out/('closed-'+stem);target=sqlite3.connect(dest)
    try:
        source.backup(target);target.commit();assert target.execute('PRAGMA quick_check').fetchall()==[('ok',)]
        target.execute('PRAGMA journal_mode=DELETE')
    finally:target.close();source.close()
    closed.append(dict(path=str(dest),sha256=sha(dest),quick_check='ok'))
assert not processes() and all(sha(r['source'])==r['sha256'] for r in saved)
receipt=dict(status='INTERRUPTED_TASK_AND_STOPPED_COLLECTORS_PRESERVED_NOT_RESTARTED',task_id=os.environ['COIN_TASK_ID'],
    source_sha256=sha(__file__),created_utc=datetime.now(UTC).isoformat(),saved_files=saved,closed_backups=closed,
    completed_case_ids=[r['id'] for r in checkpoint['cases']],parent_task_id=checkpoint['binding']['task_id'],
    parent_exit_code='UNKNOWN',parent_exit_reason='UNKNOWN',boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    reboot_history=subprocess.check_output(['last','-x','reboot','-n','3'],text=True),
    source_SQL_opened=False,originals_unchanged=True,healthy_gap_splicing=False,restarted=False)
save(ROOT/'reports/CTA_CYCLE_INTERRUPTION_PRESERVED_20261006_V1.json',receipt)
print(json.dumps(dict(status=receipt['status'],saved_files=len(saved),cases=3)))
