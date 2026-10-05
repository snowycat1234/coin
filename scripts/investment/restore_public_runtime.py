"""Restore only already authorized original public sources; no source switch."""
import argparse,hashlib,json,os,sqlite3,subprocess,time
from pathlib import Path
from datetime import UTC,datetime
from quant import disk,resources
from quant.paths import ROOT,STATE
from quant import collector_public_v3 as public
from quant.microstructure import read_microstructure_status


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False)
def processes():
    result=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():continue
        try:
            argv=(path/'cmdline').read_bytes().split(b'\0')
            args=[x.decode() for x in argv if x]
            if not args or args[0]!=str(ROOT/'.venv/bin/python'):continue
            if '-m' not in args:continue
            index=args.index('-m')
            if index+1>=len(args) or args[index+1] not in ('quant.collector_public_v3','quant.microstructure','quant.microstructure_v2'):continue
            result.append(dict(pid=int(path.name),argv=args,start_ticks=int((path/'stat').read_text().split(') ',1)[1].split()[19]),cgroup=(path/'cgroup').read_text().strip()))
        except (OSError,UnicodeError):pass
    return result
def task_for(pid):
    results=[]
    current_ticks=int((Path('/proc')/str(pid)/'stat').read_text().split(') ',1)[1].split()[19])
    for p in (STATE/'task-progress').glob('task-*.json'):
        try:
            value=json.loads(p.read_text())
            if value.get('pid')==pid and value.get('start_ticks')==current_ticks:results.append(dict(path=str(p),sha256=sha(p),metadata=value))
        except (OSError,ValueError):pass
    assert len(results)==1,(pid,results)
    return results[0]
def small_identity(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
parser=argparse.ArgumentParser();parser.add_argument('action',choices=('launch','sample1','sample2'));parser.add_argument('--out',required=True);args=parser.parse_args();OUT=Path(args.out);assert OUT.resolve().is_relative_to(STATE)
reportpath=OUT/('RESTORE_'+args.action.upper()+'.json')
assert not reportpath.exists()
prespath=OUT/'PRESERVATION.json';pres=json.loads(prespath.read_text())
proofpath=OUT/'MANIFEST_IDENTITIES.json';proof=json.loads(proofpath.read_text())
assert proof['status']=='ALL_ORIGINAL_L1_MANIFEST_PAYLOAD_IDENTITIES_EXACT_NOT_DATA_QUALIFICATION'
assert proof['exact_files']==proof['checked_files']==proof['required_files']==pres['manifest_count'] and not proof['errors']
assert sha(prespath)==proof['preservation_sha256']
assert public.source_contract(STATE/'collector_public_v3.sqlite3',engineering=False)==pres['public']['contract']
assert sha(ROOT/'src/quant/microstructure.py')==pres['microstructure']['binding']['implementation_sha256']
assert not (ROOT/'state/collector_public_v3.stop').exists()
receipt=dict(action=args.action,task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),helper=small_identity(Path(__file__)),preservation=small_identity(prespath),manifest_identity=small_identity(proofpath),resources=resources.status(),new_services=0,source_switch=False,credentials_used=False,orders_sent=0,locked_consumed=False,gpu_hours=0)
if args.action=='launch':
    assert not processes(),processes()
    for item in pres['saved_files']:assert sha(item['source'])==item['sha256'],item['source']
    stamp=time.monotonic();capacity=disk.check(1_000_000_000)
    capacity.update(measured_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-stamp)
    assert capacity['total_bytes']+capacity['reserved_bytes']<32_000_000_000
    assert not processes(),processes()
    assert public.source_contract(STATE/'collector_public_v3.sqlite3',engineering=False)==pres['public']['contract']
    assert sha(ROOT/'src/quant/microstructure.py')==pres['microstructure']['binding']['implementation_sha256']
    starts=[]
    for name,module,title in [('public-v3','quant.collector_public_v3','原公开分钟采集恢复·断档新会话'),('micro-l1-v1','quant.microstructure','原L1采集恢复·断档新会话')]:
        stdout=OUT/(name+'-restored.stdout.log');stderr=OUT/(name+'-restored.stderr.log')
        command=['bash',str(ROOT/'scripts/with_task_progress.sh'),'--title',title,'--',str(ROOT/'.venv/bin/python'),'-u','-m',module,'--run']
        with stdout.open('xb') as out,stderr.open('xb') as err:
            process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
        starts.append(dict(name=name,module=module,title=title,wrapper_pid=process.pid,command=command,stdout=str(stdout),stderr=str(stderr),start_new_session=True))
    receipt.update(status='ORIGINAL_PUBLIC_COLLECTORS_SINGLE_DETACHED_LAUNCH_NOT_HEALTH_OR_QUALIFICATION',capacity=capacity,launches=starts,collector_processes_at_launch=processes(),launch_epoch_seconds=time.time())
else:
    launch=json.loads((OUT/'RESTORE_LAUNCH.json').read_text())
    live=processes();receipt.update(processes=live,launch_epoch_seconds=launch['launch_epoch_seconds'],sampled_us=time.time_ns()//1000)
    required={'quant.collector_public_v3','quant.microstructure'}
    mapping={p['argv'][p['argv'].index('-m')+1]:p for p in live}
    errors=[]
    if set(mapping)!=required:errors.append(dict(kind='PROCESS_SET',expected=sorted(required),actual=sorted(mapping)))
    receipts=[]
    for module in required & set(mapping):
        handle=mapping[module]
        if 'coin-quant.slice' not in handle['cgroup']:errors.append(dict(kind='CGROUP',module=module,actual=handle['cgroup']))
        task=task_for(handle['pid']);receipts.append(task)
        if task['metadata'].get('status')!='running' or task['metadata'].get('start_ticks')!=handle['start_ticks']:errors.append(dict(kind='TASK_IDENTITY',module=module,task=task))
    receipt['actual_task_receipts']=receipts
    pub=public.read_public_v3_status();micro=read_microstructure_status()
    if pub.get('state')!='RUNNING':errors.append(dict(kind='PUBLIC_SESSION_NOT_FRESH_RUNNING',state=pub.get('state')))
    if micro.get('state')!='CONNECTED':errors.append(dict(kind='MICRO_CHECKPOINT_NOT_FRESH_CONNECTED',state=micro.get('state')))
    receipt.update(public=pub,microstructure=micro,errors=errors)
    assert pub['stored_source_matches_current'] and micro['binding']==pres['microstructure']['binding']
    p_db=sqlite3.connect(f'file:{STATE/"collector_public_v3.sqlite3"}?mode=ro',uri=True);p_db.row_factory=sqlite3.Row
    try:receipt['public_lifecycle_tail']=[dict(r) for r in p_db.execute('SELECT * FROM public_lifecycle ORDER BY seq DESC LIMIT 6')]
    finally:p_db.close()
    m_db=sqlite3.connect(f'file:{STATE/"microstructure.sqlite3"}?mode=ro',uri=True);m_db.row_factory=sqlite3.Row
    try:receipt['micro_restart_gap_tail']=[dict(r) for r in m_db.execute("SELECT * FROM audit WHERE kind IN ('RESTART_GAP','SESSION') ORDER BY seq DESC LIMIT 6")]
    finally:m_db.close()
    if pub.get('session',{}).get('id')<=pres['public']['session']['id']:errors.append(dict(kind='PUBLIC_NEW_SESSION_MISSING'))
    if micro['checkpoint'].get('session')==pres['microstructure']['checkpoint']['session']:errors.append(dict(kind='MICRO_NEW_SESSION_NOT_YET_CHECKPOINTED'))
    if args.action=='sample2':
        first=json.loads((OUT/'RESTORE_SAMPLE1.json').read_text())
        previous=first['public'];oldmicro=first['microstructure']['checkpoint']
        if pub['session']['heartbeat_ms']<=previous['session']['heartbeat_ms']:errors.append(dict(kind='PUBLIC_HEARTBEAT_NO_ADVANCEMENT'))
        if not all(pub['symbols'][s]['last_websocket_received_ms']>previous['symbols'][s]['last_websocket_received_ms'] for s in pub['symbols']):errors.append(dict(kind='PUBLIC_SYMBOLS_NO_NEW_CLOSED_BARS'))
        if micro['checkpoint'].get('asof_us',0)<=oldmicro.get('asof_us',0) or micro['checkpoint'].get('accepted_events',0)<=oldmicro.get('accepted_events',0):errors.append(dict(kind='MICRO_CHECKPOINT_NO_ADVANCEMENT'))
        receipt['advancement_comparison']=dict(first_report=small_identity(OUT/'RESTORE_SAMPLE1.json'),public_heartbeat_delta_ms=pub['session']['heartbeat_ms']-previous['session']['heartbeat_ms'],micro_checkpoint_delta_us=micro['checkpoint'].get('asof_us',0)-oldmicro.get('asof_us',0),micro_accepted_events_delta=micro['checkpoint'].get('accepted_events',0)-oldmicro.get('accepted_events',0))
    receipt['status']='ORIGINAL_PUBLIC_COLLECTORS_LIVE_NEW_SESSIONS_SAMPLE_NOT_QUALIFICATION' if not errors else 'ORIGINAL_PUBLIC_COLLECTOR_RESTORE_SAMPLE_NOT_YET_VERIFIED'
    receipt['log_snapshots']=[dict(path=p,bytes=Path(p).stat().st_size,sha256=sha(p),tail=Path(p).read_text(errors='replace')[-6000:]) for start in launch['launches'] for p in (start['stdout'],start['stderr'])]
receipt.update(healthy_gap_splicing=False,real_time_days_certified=0,alpha_eligible=False)
save(reportpath,receipt)
print(json.dumps(dict(status=receipt['status'],action=args.action,report=str(reportpath),processes=receipt.get('processes',receipt.get('collector_processes_at_launch')),errors=receipt.get('errors',[])),ensure_ascii=False),flush=True)
