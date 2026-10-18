#!/usr/bin/env python3
"""Strictly verify raw byte parts; optionally create one new archive. No network."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os

EXPECTED_SHA256 = 'bcf7382a8fce51ae83d18ef1a8ca70c70635126a553e89b3ca51a9e94ab98d17'
EXPECTED_BYTES = 46161099
EXPECTED_NAME = 'SMA2025_PERSISTENT_V2R1_RECOVERY_20261018.zip'

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--verify-only', action='store_true')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    if bool(a.verify_only) == bool(a.output):
        ap.error('choose exactly one of --verify-only or --output')
    root = Path(__file__).resolve().parent
    mp = root / 'ARCHIVE_PARTS.json'
    if mp.is_symlink() or mp.stat().st_size > 131072:
        raise ValueError('unsafe manifest')
    m = json.loads(mp.read_text(encoding='utf-8'))
    if (m['schema'], m['archive_name'], m['archive_bytes'], m['archive_sha256']) != ('RAW_BYTE_SPLIT_ARCHIVE_V1', EXPECTED_NAME, EXPECTED_BYTES, EXPECTED_SHA256):
        raise ValueError('unexpected archive identity')
    parts = m['parts']
    if not 1 <= len(parts) <= 128 or len(parts) != m['part_count']:
        raise ValueError('part count bound')
    whole = hashlib.sha256()
    offset = 0
    paths = []
    for i, r in enumerate(parts):
        expected = f'parts/{EXPECTED_NAME}.part{i:03d}'
        p = root / r['path']
        if r['path'] != expected or PurePosixPath(r['path']).is_absolute() or p.is_symlink() or p.parent.is_symlink():
            raise ValueError('unsafe or unordered part path')
        if r['offset'] != offset or not 0 < r['bytes'] <= 786432 or p.stat().st_size != r['bytes']:
            raise ValueError('part length/offset mismatch')
        sha = hashlib.sha256()
        git = hashlib.sha1(f"blob {r['bytes']}\0".encode())
        n = 0
        with p.open('rb') as f:
            while b := f.read(65536):
                n += len(b)
                if n > r['bytes']:
                    raise ValueError('part grew during read')
                sha.update(b); git.update(b); whole.update(b)
        if n != r['bytes'] or sha.hexdigest() != r['sha256'] or git.hexdigest() != r['git_blob_sha1']:
            raise ValueError(f'part digest mismatch: {p.name}')
        offset += n
        paths.append(p)
    if offset != EXPECTED_BYTES or whole.hexdigest() != EXPECTED_SHA256:
        raise ValueError('whole archive digest mismatch')
    if a.output:
        if a.output.is_symlink() or a.output.exists() or not a.output.parent.is_dir():
            raise ValueError('output must be absent and parent must exist')
        check = hashlib.sha256()
        n = 0
        # Exclusive creation never replaces an existing path. An interrupted write
        # remains as a visible partial file and must not be mistaken for success.
        with a.output.open('xb') as out:
            for p in paths:
                with p.open('rb') as f:
                    while b := f.read(65536):
                        n += len(b)
                        if n > EXPECTED_BYTES:
                            raise ValueError('input changed during assembly')
                        check.update(b)
                        out.write(b)
            out.flush()
            os.fsync(out.fileno())
        if n != EXPECTED_BYTES or check.hexdigest() != EXPECTED_SHA256:
            raise ValueError('assembly failed: partial output retained')
    print(json.dumps({'status':'PASS_EXACT_ARCHIVE_IDENTITY','bytes':offset,'sha256':EXPECTED_SHA256,'parts':len(parts),'output':str(a.output) if a.output else None}, sort_keys=True))

if __name__ == '__main__':
    main()
