"""Verify local code-only packet bytes; never run finance or accept a GO."""
from hashlib import sha256
import json
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
manifest=json.loads((root/'FILES.json').read_bytes())
for name,record in manifest.items():
    relative=Path(name)
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('SAFE_RELATIVE_PACKAGE_MEMBER_REQUIRED')
    path=root/relative
    if path.is_symlink() or not path.is_file():raise ValueError('ORDINARY_CODE_PACKAGE_FILE_REQUIRED:'+name)
    raw=path.read_bytes()
    if len(raw)!=record['bytes'] or sha256(raw).hexdigest()!=record['SHA256']:
        raise ValueError('CODE_PACKAGE_BYTES_CHANGED:'+name)
    if path.suffix.lower() in {'.npz','.npy','.parquet','.csv','.bin'}:
        raise ValueError('NO_MARKET_OR_FINANCIAL_ARRAYS_IN_CODE_ONLY_PACKET:'+name)
print(json.dumps(dict(passed=True,files_verified=len(manifest),accounts_constructed=0,history_advanced=0)))
