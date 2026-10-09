"""Recover the exact official PyPI wheel into an explicit external directory."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.parse
import urllib.request
import zipfile

REGISTRY='https://pypi.org/pypi/jesse-rust/1.3.0/json'
WHEEL_SHA='65c0e9edd3af5397642ca417da2ef7c23f311d6fa2bf6a2d46c729f656528cee'
EXTENSION_SHA='4ca1bc482f53650842817901ce8a1199d302db93242949fdaeffcb9384c8b2eb'
HERE=Path(__file__).resolve().parent


def recover(root):
    root.mkdir(parents=True,exist_ok=True);p=root/'PYPI_1_3_0.json'
    if not p.exists():p.write_bytes(urllib.request.urlopen(REGISTRY,timeout=30).read())
    m=json.loads(p.read_bytes());matches=[r for r in m['urls'] if r['digests']['sha256']==WHEEL_SHA]
    if len(matches)!=1:raise ValueError('Exact pinned official wheel not available')
    r=matches[0]
    if urllib.parse.urlparse(r['url']).hostname!='files.pythonhosted.org' or 'cp312' not in r['filename']:raise ValueError('Official CPython3.12 wheel required')
    wheel=root/r['filename']
    if not wheel.exists():wheel.write_bytes(urllib.request.urlopen(r['url'],timeout=60).read())
    if wheel.stat().st_size!=r['size'] or hashlib.sha256(wheel.read_bytes()).hexdigest()!=WHEEL_SHA:raise ValueError('Pinned wheel bytes differ')
    out=root/'installed';out.mkdir(exist_ok=True)
    with zipfile.ZipFile(wheel) as z:
        if z.testzip() is not None:raise ValueError('Wheel CRC failed')
        for n in z.namelist():
            name=PurePosixPath(n)
            if name.is_absolute() or '..' in name.parts:raise ValueError('Unsafe wheel path')
            if n.endswith('/'):continue
            dest=out.joinpath(*name.parts);dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():dest.write_bytes(z.read(n))
            if dest.read_bytes()!=z.read(n):raise ValueError('Preserved installed file differs')
    binding=json.loads((HERE.parents[1]/'third_party/jesse_example_rsi2/INSTALLED_KERNEL_BINDING_20261002_V1.json').read_bytes())
    for n in ('jesse_rust/__init__.py',binding['extension_relative_path'],'jesse_rust-1.3.0.dist-info/METADATA'):
        if hashlib.sha256((out/n).read_bytes()).hexdigest()!=binding['installed_files'][n]['sha256']:raise ValueError('Pinned installed byte identity differs')
    if binding['extension_sha256']!=EXTENSION_SHA:raise ValueError('Pinned extension binding differs')
    receipt=dict(status='PASS_EXACT_OFFICIAL_WHEEL_EXTENSION_AND_METADATA',registry=REGISTRY,url=r['url'],filename=r['filename'],bytes=r['size'],wheel_sha256=WHEEL_SHA,extension_sha256=EXTENSION_SHA,installed_relative='installed',wheel_redistributed=False)
    (root/'RECOVERY.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',type=Path,required=True);a=p.parse_args();print(json.dumps(recover(a.destination)))
