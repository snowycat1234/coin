"""Restore only existing pinned public Git market-source bytes; never a provider."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import concurrent.futures,hashlib,json,shutil,subprocess,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'source';SRC.mkdir(exist_ok=True)
RESERVE=15*1024**3
YEAR_COMMIT='94fe13c494c82bb6e6868e6614eb7298fb15b3c3'
MARK_COMMIT='a23f8cc36bdaddce832b2305a16fda493d1cf764'
YEAR_PREFIX='research/core5-2021-economic-data/Y2021/'
REPOS=[ROOT.parent/'coin_native_lossless_pack_20261013/public_restore_git',ROOT.parent/'coin_native_lossless_2024_20261013/public_restore_git']
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save(name,data):
    p=ROOT/name;tmp=p.with_suffix(p.suffix+'.new');tmp.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n');tmp.replace(p)
def get(rec):
    path=SRC/rec['local_path'];path.parent.mkdir(parents=True,exist_ok=True)
    method='EXISTING_VERIFIED_LOCAL_FILE'
    if not (path.exists() and path.stat().st_size==rec['bytes'] and sha(path)==rec['SHA256']):
        assert shutil.disk_usage(ROOT).free>RESERVE+300_000_000
        tmp=path.with_suffix(path.suffix+'.download');found=False
        env=dict(os.environ,GIT_NO_LAZY_FETCH='1')
        for repo in REPOS:
            check=subprocess.run(['git','-C',str(repo),'cat-file','--batch-check'],input=(rec['commit']+':'+rec['git_path']+'\n').encode(),capture_output=True,env=env)
            if b' blob ' not in check.stdout:continue
            with tmp.open('wb') as f:
                r=subprocess.run(['git','-C',str(repo),'show',rec['commit']+':'+rec['git_path']],stdout=f,stderr=subprocess.PIPE,env=env)
            assert r.returncode==0,r.stderr
            method='EXISTING_LOCAL_GIT_BLOB';found=True;break
        if not found:
            url='https://raw.githubusercontent.com/snowycat1234/coin/'+rec['commit']+'/'+rec['git_path']
            r=subprocess.run(['curl','-fLsS','--max-time','120',url,'-o',str(tmp)],capture_output=True,text=True)
            if r.returncode:raise RuntimeError(f"Pinned public Git fetch stopped for {rec['git_path']}: {r.stderr}")
            method='PINNED_PUBLIC_GIT_READ'
        assert tmp.stat().st_size==rec['bytes'] and sha(tmp)==rec['SHA256'],rec
        tmp.replace(path)
    return dict(rec,transport=method)
def main():
    started=time.monotonic()
    year=json.loads((ROOT/'evidence/Y2021_INDEX.json').read_text());mark=json.loads((ROOT/'evidence/DEC2021_RECOVERY.json').read_text())
    assert len(year['parts'])==212 and year['package_bytes']==166692849
    todo=[dict(r,commit=YEAR_COMMIT,git_path=YEAR_PREFIX+r['name'],local_path='Y2021_parts/'+r['name']) for r in year['parts']]
    for record in mark['sources']:
        row=record['source']
        for part in row['parts']:todo.append(dict(part,commit=MARK_COMMIT,git_path=part['path'],local_path='DEC2021_parts/'+row['symbol']+'/'+Path(part['path']).name))
    assert len(todo)==222 and sum(r['bytes'] for r in todo)==171932044
    completed=[]
    for start in range(0,len(todo),4):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:completed.extend(pool.map(get,todo[start:start+4]))
        save('PUBLIC_GIT_RESTORE_LEDGER.json',dict(status='RESTORING' if len(completed)<len(todo) else 'ALL_PARTS_VERIFIED',parts=completed,provider_downloads=0,targets=0,wallets=0))
        print('PUBLIC2021_PARTS_VERIFIED',len(completed),len(todo),flush=True)
    wrapper=SRC/'Y2021.zip'
    if not (wrapper.exists() and wrapper.stat().st_size==year['package_bytes'] and sha(wrapper)==year['package_SHA256']):
        tmp=wrapper.with_suffix('.zip.new')
        with tmp.open('wb') as f:
            for part in year['parts']:f.write((SRC/'Y2021_parts'/part['name']).read_bytes())
        assert tmp.stat().st_size==year['package_bytes'] and sha(tmp)==year['package_SHA256'];tmp.replace(wrapper)
    with zipfile.ZipFile(wrapper) as z:assert z.testzip() is None
    for record in mark['sources']:
        row=record['source'];base=SRC/'DEC2021'/row['symbol'];base.mkdir(parents=True,exist_ok=True);path=base/(row['symbol']+'-1m-2021-12.zip')
        with path.open('wb') as f:
            for part in row['parts']:f.write((SRC/'DEC2021_parts'/row['symbol']/Path(part['path']).name).read_bytes())
        assert path.stat().st_size==row['ZIP_bytes'] and sha(path)==row['ZIP_SHA256']
        check=Path(str(path)+'.CHECKSUM');check.write_text(row['official_checksum_text']);assert sha(check)==row['CHECKSUM_member_SHA256']
        with zipfile.ZipFile(path) as z:assert z.testzip() is None
    save('PUBLIC_GIT_RESTORE_RECEIPT.json',dict(status='PASS_REAL2021_ORIGINAL_BYTES_RESTORED',year_wrapper=dict(path=str(wrapper.relative_to(ROOT)),bytes=wrapper.stat().st_size,SHA256=sha(wrapper)),year_public_commit=YEAR_COMMIT,December_mark_public_commit=MARK_COMMIT,parts=222,pinned_public_bytes=171932044,new_provider_downloads=0,targets_generated=0,wallets=0,elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,CPU_affinity=list(os.sched_getaffinity(0)),AS_limit_bytes=2*1024**3))
    print('2021_PUBLIC_SOURCE_BYTES_READY',flush=True)
if __name__=='__main__':main()
