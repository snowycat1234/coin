"""Recover one pinned source member; never acquire strategy results or whole ZIP."""
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request,urlopen
import zipfile

COMMIT='d69e9ac94478c5be54cb46c622afec7aaf3c61f7'
URL=f'https://raw.githubusercontent.com/snowycat1234/coin/{COMMIT}/research_artifacts/native_20261008/coin_native_history_diagnostics_20261008.zip'
MEMBER='source/scripts/research/conditional_selector_inputs.py'
EXPECTED='9c6658cd7682b6c5470585cbe927c20893e98a3e071cd52e56c5de280e86f207'
ROOT=Path('/workspace/coin-2021-data/protocol')

class Remote(io.RawIOBase):
    def __init__(self):self.position=0;self.transferred=0;self.requests=[]
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.position
    def seek(self,n,whence=0):
        self.position=n if whence==0 else self.position+n if whence==1 else 12283650+n
        return self.position
    def read(self,n=-1):
        n=12283650-self.position if n<0 else min(n,12283650-self.position)
        if n==0:return b''
        assert 0<=self.position<12283650 and self.transferred+n<=250000
        left,right=self.position,self.position+n-1
        with urlopen(Request(URL,headers={'Range':f'bytes={left}-{right}'}),timeout=30) as r:
            assert r.status==206 and r.headers['Content-Range']==f'bytes {left}-{right}/12283650'
            b=r.read(n+1)
            assert len(b)==n
        self.position+=n;self.transferred+=n
        self.requests.append(dict(start=left,end=right,bytes=n))
        return b

remote=Remote()
with zipfile.ZipFile(remote) as z:
    body=z.read(MEMBER)
assert hashlib.sha256(body).hexdigest()==EXPECTED
(ROOT/'conditional_selector_inputs.py').write_bytes(body)
receipt=dict(source_commit=COMMIT,source_archive_URL=URL,whole_archive_SHA256_NOT_REVERIFIED=True,
    selected_member=MEMBER,selected_member_SHA256=EXPECTED,member_CRC_checked=True,
    actual_range_body_bytes=remote.transferred,requests=remote.requests)
(ROOT/'RECIPE_SOURCE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='requests'}))
