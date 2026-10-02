import datetime,hashlib,json,pathlib,sqlite3,time
from quant import resources
from quant.microstructure import read_microstructure_status
from quant.collector_public_v3 import read_public_v3_status
ROOT=pathlib.Path('/mnt/d/codex/coin')
OUT=pathlib.Path('/home/xflops/coin-state/v7-runtime-preservation-20261002-v3')
before=json.loads((OUT/'PRESERVATION.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
processes=[]
for p in pathlib.Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()
        kind='microstructure' if ' -m quant.microstructure --run' in cmd else 'public_v3' if ' -m quant.collector_public_v3 --run' in cmd else None
        if not kind:continue
        ticks=int((p/'stat').read_text().split(') ',1)[1].split()[19])
        group=(p/'cgroup').read_text().strip()
        assert 'coin-quant.slice' in group
        processes.append({'kind':kind,'pid':int(p.name),'start_ticks':ticks,'command':cmd,'cgroup':group,'unified_session':31822 if kind=='microstructure' else 60666})
    except (FileNotFoundError,ProcessLookupError,PermissionError):pass
assert sorted(p['kind'] for p in processes)==['microstructure','public_v3'],processes
micro=read_microstructure_status()
public=read_public_v3_status()
assert micro['binding']==before['microstructure_before']['binding']
assert public['contract']==before['public_before']['contract'] and public['stored_source_matches_current']
assert micro['checkpoint']['session']!=before['microstructure_before']['checkpoint']['session']
assert public['session']['id']!=before['public_before']['session']['id']
assert micro['state']=='CONNECTED',micro['state']
assert public['state']=='RUNNING',public['state']
assert all(v['last_websocket_received_ms']>=public['session']['started_ms'] for v in public['symbols'].values())
preserved_prefixes={}
new_lifecycle={}
for name,table in [('microstructure.sqlite3','audit'),('collector_public_v3.sqlite3','public_lifecycle')]:
    old=sqlite3.connect(f'file:{OUT/name}?mode=ro',uri=True)
    current=sqlite3.connect(f'file:/home/xflops/coin-state/{name}?mode=ro',uri=True)
    try:
        terminal=old.execute(f'SELECT * FROM {table} ORDER BY seq DESC LIMIT 1').fetchone()
        actual=current.execute(f'SELECT * FROM {table} WHERE seq=?',(terminal[0],)).fetchone()
        assert actual==terminal
        rows=current.execute(f'SELECT * FROM {table} WHERE seq>? ORDER BY seq',(terminal[0],)).fetchall()
        items=[{'seq':r[0],'received':r[1],'kind':r[2],'payload':json.loads(r[3]),'sha256':r[5]} for r in rows if r[2] in ['SESSION','RESTART_GAP','CONNECTED','UNGRACEFUL_PREVIOUS_SESSION','RUN_REQUEST']]
        preserved_prefixes[table]={'prior_terminal_seq':terminal[0],'prior_terminal_sha256':terminal[5],'exact_prior_terminal_row_unchanged':True}
        new_lifecycle[table]=items
    finally:old.close();current.close()
assert any(r['kind']=='RESTART_GAP' for r in new_lifecycle['audit'])
assert any(r['kind']=='UNGRACEFUL_PREVIOUS_SESSION' for r in new_lifecycle['public_lifecycle'])
logs=[]
for p in OUT.glob('*new.*.log'):
    logs.append({'path':str(p),'sha256_at_snapshot':sha(p),'bytes_at_snapshot':p.stat().st_size})
report={'status':'EXISTING_PUBLIC_COLLECTORS_RECOVERED_NEW_SESSIONS','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'preservation_receipt':str(OUT/'PRESERVATION.json'),'preservation_sha256':sha(OUT/'PRESERVATION.json'),'prelaunch_disk':before['disk'],'resources':resources.status(),'processes':processes,'microstructure':micro,'public_v3':public,'old_audit_prefixes':preserved_prefixes,'new_session_and_gap_records':new_lifecycle,'new_logs':logs,'frozen_sources_unchanged':True,'source_version_switch':False,'exit_cause':'UNKNOWN; old handles missing; saved kernel init-systemd messages support hpc_linux reinitialization without proving trigger; same kernel boot ID does not prove continuous distro processes','old_healthy_seconds_not_spliced':True,'gap_credited_as_healthy':False,'real_time_days_certified':0,'qualified_72h':False,'new_resource_observer_started':False,'old_daily_downloader_restarted':False,'old_history_qa_restarted':False,'financial_accounts':False,'credentials_used':False,'orders_sent':0,'gpu_used':False,'initial_preservation_import_failure':{'script':'.cache/v7_preserve_collectors_20261002_v1.py','unified_session':64681,'exit_code':1,'stage':'import before OUT creation; incorrect status API name, v2 used existing read_public_v3_status'}}
report['exit_cause']='Verified original L1 clock incident; subsequent distro process environment interruption has unknown trigger. Closed backups and zero-fit research evidence preserved in V3.'
report['initial_preservation_import_failure']=None
report['environment_recovery_requires_new_sessions']=True
target=ROOT/'reports/fast_research/V7_PUBLIC_COLLECTOR_RECOVERY_20261002_V3.json'
with target.open('x') as f:json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
print(json.dumps({'status':report['status'],'report':str(target),'sha256':sha(target),'processes':processes,'microstructure_checkpoint_asof':micro['checkpoint']['asof_us'],'public_session':public['session']}),flush=True)
