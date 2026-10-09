"""Extract retained public bear/recovery bundle and reproduce exact caches offline."""
import argparse,hashlib,json,os
from pathlib import Path,PurePosixPath
import resource,runpy,socket,sys,zipfile

def recover(state):
    archive=state/'e5-bear-original/coin_e5_bear_recovery_native_increment_20261008_v2.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()=='98e38bc3f0e6a16fd51a63be880371882d4e2b52df1d8ec5a39963721d2d2bb8'
    root=state/'e5-bear-original/original';root.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        manifest=json.loads(z.read('MANIFEST_SHA256.json'))
        for r in manifest['members']:
            b=z.read(r['name']);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
        for name in z.namelist():
            n=PurePosixPath(name);assert not n.is_absolute() and '..' not in n.parts
            if name.endswith('/'):continue
            b=z.read(name);p=root.joinpath(*n.parts);p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():assert p.read_bytes()==b
            else:p.write_bytes(b)
    repo=Path(__file__).resolve().parents[2]
    sys.argv=['normalize_e5_cached_archives.py','--root',str(repo),'--work',str(root/'bear_recovery_data')]
    runpy.run_path(str(root/'offline_importer/normalize_e5_cached_archives.py'),run_name='__main__')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000))
    def blocked(*a,**kw):raise RuntimeError('Offline recovery forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    recover(a.state)
