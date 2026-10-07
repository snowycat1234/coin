import hashlib,json,os,platform,shutil,time
from pathlib import Path

DAY=86_400_000_000
MINUTE=60_000_000

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def atomic(path,value):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.tmp-'+str(os.getpid()))
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    os.replace(tmp,p)

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def guard(state):
    if platform.system()!='Linux' or not Path('/home/ubuntu/coin').is_dir():
        raise RuntimeError('Scientific execution is authorized only on the Ubuntu research server')
    if shutil.disk_usage(state).free<15*1024**3:raise RuntimeError('15 GiB actual free disk reserve breached')

def stamp():return time.strftime('%Y-%m-%d %H:%M:%S')
