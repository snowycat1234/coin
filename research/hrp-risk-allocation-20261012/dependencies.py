"""Pinned official small wheels, separate state installation, offline cold default."""
import argparse,hashlib,json,urllib.request,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
NAMES={'PYPORTFOLIOOPT_1.5.6.json':'pyportfolioopt-1.5.6-py3-none-any.whl','CVXPY_1.7.4.json':'cvxpy-1.7.4-cp312-cp312-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl'}

def recover(state,fetch=False):
    out=state/'dependencies';out.mkdir(parents=True,exist_ok=True);proof=[]
    for meta,name in NAMES.items():
        obj=json.loads((HERE/'source'/meta).read_text());r=next(r for r in obj['urls'] if r['filename']==name);p=HERE/'source/wheels'/name
        if fetch and not p.exists():
            if r['size']>4_000_000 or not r['url'].startswith('https://files.pythonhosted.org/'):raise ValueError('Bounded official wheel only')
            with urllib.request.urlopen(r['url'],timeout=20) as f:raw=f.read(4_000_001)
            if len(raw)!=r['size'] or hashlib.sha256(raw).hexdigest()!=r['digests']['sha256']:raise ValueError('Official wheel identity')
            p.parent.mkdir(exist_ok=True);p.write_bytes(raw)
        raw=p.read_bytes()
        if len(raw)!=r['size'] or hashlib.sha256(raw).hexdigest()!=r['digests']['sha256']:raise ValueError('Pinned public wheel identity')
        with zipfile.ZipFile(p) as z:
            if z.testzip() is not None:raise ValueError('Wheel CRC')
            for member in z.namelist():
                if member.startswith('/') or '..' in Path(member).parts:raise ValueError('Wheel member traversal')
            z.extractall(out)
        proof.append(dict(filename=name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest(),version=obj['info']['version'],license=obj['info']['license']))
    return out,proof
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--fetch',action='store_true');a=p.parse_args();path,proof=recover(a.state,a.fetch);print(json.dumps(proof,indent=2))
