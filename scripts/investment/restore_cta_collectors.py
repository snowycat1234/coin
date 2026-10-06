"""Restore only the two already authorized stopped public collectors."""
import hashlib,json,os,sqlite3,subprocess
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from quant import collector_public_v3 as public
from quant.microstructure import read_microstructure_status

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False)
def active():
    for p in Path('/proc').iterdir():
        try:
            argv=(p/'cmdline').read_bytes().split(b'\0')
            if any(x in argv for x in (b'quant.collector_public_v3',b'quant.microstructure')):return True
        except OSError:pass
    return False

assert os.environ.get('COIN_TASK_ID') and not active()
pres=ROOT/'reports/CTA_CYCLE_INTERRUPTION_PRESERVED_20261006_V1.json';r=json.loads(pres.read_bytes())
pt=json.loads((STATE/'task-progress'/('task-'+r['task_id']+'.json')).read_bytes())
assert pt['status']=='completed' and pt['exit_code']==0 and not public.STOP_FILE.exists()
assert subprocess.check_output(['systemctl','--user','show','coin-quant.slice','-p','MemoryMax','--value'],text=True).strip()=='5000000000'
db=STATE/'collector_public_v3_20261006.sqlite3';out=STATE/'d099-interruption-preserved-20261006-v1'
for row in r['saved_files']:
    if row['source'].endswith(('.sqlite3','.sqlite3-wal','.sqlite3-shm')):assert sha(row['source'])==row['sha256']==sha(row['saved'])
for row in r['closed_backups']:assert sha(row['path'])==row['sha256']
conn=sqlite3.connect(f'file:{out/"closed-collector_public_v3_20261006.sqlite3"}?mode=ro&immutable=1',uri=True)
try:contract,head=public.verify_registry(conn)
finally:conn.close()
assert contract==public.source_contract(db),'Do not mutate an incompatible collector binding'
micro=read_microstructure_status(out/'closed-microstructure.sqlite3')
assert micro['binding']['implementation_sha256']==sha(ROOT/'src/quant/microstructure.py')
save(out/'AUDIT_BEFORE_RESTART.json',dict(public_contract=contract,public_audit_head=head,microstructure=micro))
starts=[]
for name,module in [('public','quant.collector_public_v3'),('micro','quant.microstructure')]:
    command=['bash',str(ROOT/'scripts/with_task_progress.sh'),'--title','D099断档恢复 '+name+' ·公开只读新会话','--',
        'systemd-run','--user','--scope','--quiet','--slice=coin-quant.slice','-p','MemorySwapMax=0','env',
        'OMP_NUM_THREADS=2','OPENBLAS_NUM_THREADS=2','POLARS_MAX_THREADS=2',str(ROOT/'.venv/bin/python'),'-u','-m',module,'--run']
    if name=='public':command+=['--db',str(db)]
    stdout=out/(name+'-restored.stdout.log');stderr=out/(name+'-restored.stderr.log')
    with stdout.open('xb') as o,stderr.open('xb') as e:
        process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=o,stderr=e,start_new_session=True)
    starts.append(dict(module=module,wrapper_pid=process.pid,command=command,stdout=str(stdout),stderr=str(stderr)))
save(ROOT/'reports/CTA_COLLECTORS_RESTORED_20261006_V2.json',dict(status='LAUNCHED_ORIGINAL_PUBLIC_SCOPE_NOT_CONTINUITY_OR_CONNECTIVITY_PROOF',
    task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),preservation_sha256=sha(pres),launches=starts,
    audit_before_restart_sha256=sha(out/'AUDIT_BEFORE_RESTART.json'),created_utc=datetime.now(UTC).isoformat(),
    healthy_gap_splicing=False,qualification=False,credentials_used=False,orders_sent=0))
print(json.dumps(dict(status='LAUNCHED_TWO_ORIGINAL_COLLECTORS_NEW_SESSION_GAPS_REQUIRED',launches=2)))
