#!/usr/bin/env python3
"""Offline, standard-library-only verification. Never imports the research engine."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

MAX_MEMBERS = 2000
MAX_TOTAL_BYTES = 128 * 2**20
MAX_MEMBER_BYTES = 64 * 2**20

def safe(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or not name or name.endswith('/'):
        raise RuntimeError('UNSAFE_FILE_MEMBER: ' + name)
    return p

def digest(stream):
    h = hashlib.sha256(); n = 0
    while True:
        part = stream.read(1024 * 1024)
        if not part:
            break
        h.update(part); n += len(part)
    return n, h.hexdigest()

def validate_manifest(raw, seal):
    if hashlib.sha256(raw).hexdigest() != seal.split()[0]:
        raise RuntimeError('MANIFEST_SEAL_MISMATCH')
    m = json.loads(raw)
    rows = m['members']
    if len(rows) > MAX_MEMBERS or sum(x['bytes'] for x in rows) > MAX_TOTAL_BYTES:
        raise RuntimeError('BOUNDS_EXCEEDED')
    names = [x['path'] for x in rows]
    if len(names) != len(set(names)):
        raise RuntimeError('DUPLICATE_MANIFEST_PATH')
    for x in rows:
        safe(x['path'])
        if x['bytes'] > MAX_MEMBER_BYTES:
            raise RuntimeError('MEMBER_BOUND_EXCEEDED')
    return m

def verify_zip(path):
    with zipfile.ZipFile(path) as z:
        infos = z.infolist(); names = [x.filename for x in infos]
        if len(names) != len(set(names)) or len(names) > MAX_MEMBERS:
            raise RuntimeError('DUPLICATE_OR_EXCESS_ZIP_MEMBERS')
        for info in infos:
            safe(info.filename)
            mode = info.external_attr >> 16
            if info.flag_bits & 1 or stat.S_ISLNK(mode) or (mode and not stat.S_ISREG(mode)):
                raise RuntimeError('NONREGULAR_OR_ENCRYPTED_MEMBER')
            if info.file_size > MAX_MEMBER_BYTES:
                raise RuntimeError('MEMBER_BOUND_EXCEEDED')
        if sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
            raise RuntimeError('TOTAL_BOUND_EXCEEDED')
        raw = z.read('MANIFEST.json'); seal = z.read('MANIFEST.sha256').decode('ascii')
        m = validate_manifest(raw, seal)
        expected = {x['path'] for x in m['members']} | {'MANIFEST.json', 'MANIFEST.sha256'}
        if set(names) != expected:
            raise RuntimeError('MISSING_OR_UNLISTED_ZIP_MEMBER')
        for row in m['members']:
            info = z.getinfo(row['path'])
            if info.file_size != row['bytes']:
                raise RuntimeError('ZIP_LENGTH_MISMATCH: ' + row['path'])
            with z.open(info) as f:
                n, h = digest(f)
            if (n, h) != (row['bytes'], row['sha256']):
                raise RuntimeError('ZIP_HASH_MISMATCH: ' + row['path'])
        return {'status': 'PASS_ALL_MEMBERS_STREAMED', 'members': len(infos),
                'uncompressed_bytes': sum(i.file_size for i in infos),
                'engine_imports': 0, 'financial_runs': 0, 'network_requests': 0,
                'extraction_performed': False}

def verify_tree(root):
    root = root.resolve()
    m = validate_manifest((root / 'MANIFEST.json').read_bytes(),
                          (root / 'MANIFEST.sha256').read_text('ascii'))
    for row in m['members']:
        p = root.joinpath(*safe(row['path']).parts)
        current = p
        while current != root:
            if current.is_symlink():
                raise RuntimeError('SYMLINK_IN_TREE: ' + row['path'])
            current = current.parent
        if not p.is_file():
            raise RuntimeError('MISSING_FILE: ' + row['path'])
        with p.open('rb') as f:
            n, h = digest(f)
        if (n, h) != (row['bytes'], row['sha256']):
            raise RuntimeError('TREE_HASH_MISMATCH: ' + row['path'])
    return {'status': 'PASS_ALL_LISTED_FILES', 'members': len(m['members']) + 2,
            'engine_imports': 0, 'financial_runs': 0, 'network_requests': 0}

def main():
    a = argparse.ArgumentParser(description=__doc__)
    group = a.add_mutually_exclusive_group()
    group.add_argument('--zip', type=Path)
    group.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = a.parse_args()
    print(json.dumps(verify_zip(args.zip) if args.zip else verify_tree(args.root), indent=2))

if __name__ == '__main__':
    main()
