"""One bounded immutable public Git archive read, only after parent GO."""
import argparse
import hashlib
import json
import time
import urllib.request
import io
import zipfile
from pathlib import Path

URL = ('https://raw.githubusercontent.com/snowycat1234/coin/'
       '4a661765dc476d314ec4002e8cc706877a11bcda/'
       'research/jump-share-risk-20261012/public/INPUTS/PACKET.zip')
EXPECTED = '285528c6c0e204e5d69632a4fdc7dd5ee5f17aeeeaffc2292a5fcea90e10a9ac'
SIZE = 16_834_324
q = argparse.ArgumentParser(); q.add_argument('--output', type=Path, required=True)
args = q.parse_args()
if args.output.exists():
    raise FileExistsError('Existing source cache must be verified/reused, never downloaded again')
began = time.monotonic()
with urllib.request.urlopen(URL, timeout=45) as response:
    raw = response.read(SIZE + 1)
if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != EXPECTED:
    raise ValueError('Exact immutable public source archive hash/size failure')
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    names = archive.namelist()
    if len(names) != len(set(names)) or any(name.startswith('/') or '..' in Path(name).parts for name in names):
        raise ValueError('Unsafe or duplicate source archive paths')
    if len(names) != 15 or sum(info.file_size for info in archive.infolist()) > 20_000_000:
        raise ValueError('Unexpected source archive member count/expanded size')
    if archive.testzip() is not None:
        raise ValueError('Source archive CRC failure')
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open('xb') as stream:
    stream.write(raw)
with args.output.with_suffix('.RECEIPT.json').open('x') as stream:
    json.dump(dict(URL=URL, SHA256=EXPECTED, bytes=SIZE, seconds=time.monotonic()-began,
                   request_count=1, provider_requests=0, scientific_arrays_parsed=0,
                   safe_zip_member_count=len(names), archive_paths_safe=True, CRC_pass=True,
                   automatic_retries=0, fits=0, wallets=0), stream, indent=2)
print('SAVED_SOURCE_PACKET_HASH_VERIFIED', EXPECTED)
