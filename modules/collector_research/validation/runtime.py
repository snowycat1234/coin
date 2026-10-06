"""Explicit execution site and external artifact paths; no host credentials."""
import hashlib,json,os,platform,shutil,sys,time
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]
DAY=86_400_000_000;MINUTE=60_000_000
CONFIG={}

def load_settings():
    global CONFIG,ROOT,WORK,SOURCE,RUN,STATE
    CONFIG=json.loads(os.environ.get('COIN_VALIDATION_SETTINGS','{}'))
    ROOT=Path(CONFIG.get('collector_root',REPO/'modules/collector_research')).resolve()
    WORK=Path(CONFIG.get('collector_work',ROOT/'work')).resolve()
    SOURCE=Path(CONFIG.get('source_run',WORK/'automation/source')).resolve()
    RUN=Path(CONFIG.get('run_dir',WORK/'automation/validation')).resolve();STATE=RUN.parent
    os.environ['QUANT_ROOT']=str(REPO)
    os.environ['QUANT_STATE']=str(CONFIG.get('state_dir',STATE))
    os.environ['WORK_DIR']=str(WORK)
    os.environ['CONFIG_FILE']=str(ROOT/'config.env')
    sys.path[:0]=[str(ROOT),str(REPO/'src'),str(REPO)]

def configure(args):
    settings={k:str(Path(getattr(args,k)).expanduser().resolve()) for k in
              ('collector_root','collector_work','source_run','run_dir')}
    settings.update(resource_policy=args.resource_policy,workers=args.workers,minimum_days=args.minimum_days,
                    publish_source_report=args.publish_source_report,audit_device=args.audit_device)
    for key in ('collector_work','source_run','run_dir'):
        if Path(settings[key]).is_relative_to(REPO):
            raise ValueError(f'{key} must be outside the checkout; market/model/ledger bytes stay in external STATE')
    if Path(settings['run_dir'])==Path(settings['source_run']):raise ValueError('New validation directory must differ from original evidence')
    os.environ['COIN_VALIDATION_SETTINGS']=json.dumps(settings);load_settings();kernel_guard()
    RUN.mkdir(parents=True,exist_ok=True)
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS'):
        os.environ.setdefault(key,'1')

def kernel_guard():
    if platform.system()!='Linux':raise RuntimeError('Scientific execution requires Linux; Windows may only edit/inspect source')
    policy=CONFIG.get('resource_policy','local')
    wsl=bool(os.environ.get('WSL_DISTRO_NAME')) or 'microsoft' in platform.release().lower()
    total=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemTotal:')))*1024
    rel=Path('/proc/self/cgroup').read_text().split('::',1)[1].strip();group=Path('/sys/fs/cgroup'+rel)
    coin=next((p for p in (group,*group.parents) if p.name=='coin.slice'),None)
    if policy=='server':
        if wsl:raise RuntimeError('Server policy cannot bypass local WSL limits')
        observed=group;limit=(observed/'memory.max').read_text().strip()
    else:
        if os.environ.get('WSL_DISTRO_NAME')!='hpc_linux' or coin is None:
            raise RuntimeError('Local execution requires hpc_linux through with_task_progress.sh -> bounded.sh')
        observed=coin;limit=(coin/'memory.max').read_text().strip()
        if limit=='max' or not 0<int(limit)<=8_000_000_000:raise RuntimeError('Local shared RAM limit must remain at most 8 GB')
        if (coin/'memory.swap.max').read_text().strip()!='0':raise RuntimeError('Local project swap must remain disabled')
        if CONFIG.get('audit_device')=='cuda':raise RuntimeError('Local policy does not authorize GPU use')
    disk_target=WORK
    while not disk_target.exists():disk_target=disk_target.parent
    free=shutil.disk_usage(disk_target).free
    if free<15*2**30:raise RuntimeError('Less than 15 GiB free; preserve artifacts and stop')
    cpu=len(os.sched_getaffinity(0))
    return dict(memory_current=int((observed/'memory.current').read_text()),memory_max=None if limit=='max' else int(limit),
        memory_total_bytes=total,resource_policy=policy,cpu_count=cpu,free_bytes=free)

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):digest.update(block)
    return digest.hexdigest()

def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False,default=str)+'\n');tmp.replace(path)

def progress(path,module,current=None,total=None,detail='',**extra):
    atomic(path,dict(module=module,current=current,total=total,detail=detail,pid=os.getpid(),updated_at=time.time(),**extra))

load_settings()
