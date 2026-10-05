"""Finite D095 recovery; preserve old public binding and record new session gaps."""
import argparse,hashlib,json,os,sqlite3,subprocess
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from quant import collector_public_v3 as public,resources
from quant.microstructure import read_microstructure_status
OUT=STATE/'d095-stopped-collector-recovery-20261005-v1'
DB=STATE/'collector_public_v3_20261006.sqlite3'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(n,v):
 with (OUT/n).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False)
def live():
 result=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdecimal():continue
  try:
   argv=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x]
   if argv and argv[0]==str(ROOT/'.venv/bin/python') and '-m' in argv and argv[argv.index('-m')+1] in ('quant.collector_public_v3','quant.microstructure'):
    result.append(dict(pid=int(p.name),argv=argv,start_ticks=int((p/'stat').read_text().split(') ',1)[1].split()[19]),cgroup=(p/'cgroup').read_text().strip()))
  except (OSError,UnicodeError,IndexError):pass
 return sorted(result,key=lambda x:x['pid'])
ap=argparse.ArgumentParser();ap.add_argument('action',choices=['launch','sample1','sample2']);a=ap.parse_args()
pres=json.loads((OUT/'PRESERVATION.json').read_bytes())
for p,h in pres['source_hashes'].items():
 if p!='src/quant/collector_public_v3.py':assert sha(ROOT/p)==h,p
assert sha(ROOT/'src/quant/microstructure.py')==pres['microstructure']['binding']['implementation_sha256']
if a.action=='launch':
 assert not live() and not DB.exists() and not public.STOP_FILE.exists()
 for v in pres['saved']:assert sha(v['source'])==v['sha256']
 # Strictly scoped new source contract. No old frozen row is rewritten.
 contract=public.source_contract(DB)
 old=pres['public']['contract']
 for key in set(contract)-{'database','disk_hard_bytes','ram_shared_max_bytes','sources'}:assert contract[key]==old[key],key
 assert contract['disk_hard_bytes']==150000000000 and contract['ram_shared_max_bytes']==8000000000
 for key,h in old['sources'].items():
  if key not in ('src/quant/collector_public_v3.py','src/quant/disk.py','src/quant/resources.py','scripts/env.sh','scripts/bounded.sh'):assert contract['sources'][key]==h,key
 starts=[]
 for name,module in [('public','quant.collector_public_v3'),('micro','quant.microstructure')]:
  command=['bash',str(ROOT/'scripts/with_task_progress.sh'),'--title','D095断档恢复 '+name+' ·只读新会话','--','env','OMP_NUM_THREADS=2','OPENBLAS_NUM_THREADS=2','POLARS_MAX_THREADS=2',str(ROOT/'.venv/bin/python'),'-u','-m',module,'--run']
  if name=='public':command+=['--db',str(DB)]
  out=OUT/(name+'-new.stdout.log');err=OUT/(name+'-new.stderr.log')
  with out.open('xb') as o,err.open('xb') as e:p=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=o,stderr=e,start_new_session=True)
  starts.append(dict(module=module,wrapper_pid=p.pid,command=command,stdout=str(out),stderr=str(err)))
 save('NEW_LAUNCH.json',dict(status='LAUNCHED_NEW_PUBLIC_BINDING_AND_SAME_MICRO_STORE_NOT_HEALTH_PROOF',launches=starts,public_contract=contract,old_public_contract=old,old_public_db_retained=True,created_utc=datetime.now(UTC).isoformat(),task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),orders_sent=0,credentials_used=False))
else:
 procs=live();assert len(procs)==2 and all('coin.slice' in v['cgroup'] for v in procs)
 pub=public.read_public_v3_status(DB);micro=read_microstructure_status()
 assert pub['stored_source_matches_current'] and pub['state']=='RUNNING'
 assert micro['binding']==pres['microstructure']['binding'] and micro['state']=='CONNECTED'
 assert micro['checkpoint']['session']!=pres['microstructure']['checkpoint']['session']
 c=sqlite3.connect(f'file:{STATE/"microstructure.sqlite3"}?mode=ro',uri=True);c.row_factory=sqlite3.Row
 gaps=[dict(v) for v in c.execute("SELECT * FROM audit WHERE kind IN ('RESTART_GAP','SESSION') ORDER BY seq DESC LIMIT 6")];c.close()
 # Old public database remains byte-for-byte untouched, including its WAL/SHM.
 for v in pres['saved']:
  if Path(v['source']).name.startswith('collector_public_v3.sqlite3'):assert sha(v['source'])==v['sha256']
 snap=dict(status='SAMPLED_NEW_SESSIONS_NOT_CONTINUOUS_HEALTH',processes=procs,public=pub,microstructure=micro,micro_restart_gaps=gaps,old_public_last_heartbeat_ms=pres['public']['session']['heartbeat_ms'],resources=resources.status(),created_utc=datetime.now(UTC).isoformat(),task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),qualified_days=0,exit_cause='UNKNOWN',healthy_gap_splicing=False)
 if a.action=='sample2':
  prev=json.loads((OUT/'NEW_SAMPLE1.json').read_bytes())
  assert [(p['pid'],p['start_ticks']) for p in procs]==[(p['pid'],p['start_ticks']) for p in prev['processes']]
  assert pub['session']['heartbeat_ms']>prev['public']['session']['heartbeat_ms']
  assert all(pub['symbols'][s]['last_websocket_received_ms']>prev['public']['symbols'][s]['last_websocket_received_ms'] for s in pub['symbols'])
  assert micro['checkpoint']['asof_us']>prev['microstructure']['checkpoint']['asof_us'] and micro['checkpoint']['accepted_events']>prev['microstructure']['checkpoint']['accepted_events']
 save('NEW_'+a.action.upper()+'.json',snap)
print(json.dumps(dict(action=a.action,status='PASS_FINITE_STAGE',public_database=str(DB),task_id=os.environ['COIN_TASK_ID'])))
