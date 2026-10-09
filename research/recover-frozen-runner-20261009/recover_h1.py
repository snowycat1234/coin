"""Recover pinned public H1 bytes and normalize original caches offline."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import socket
import subprocess
import sys
import zipfile

COMMIT = 'd69e9ac94478c5be54cb46c622afec7aaf3c61f7'
BASE = 'research_artifacts/'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('Different existing recovery bytes: ' + path.name)
    else:
        path.write_bytes(data)


def archive(repo, state, family):
    base = BASE + family + '_20261008'
    def git(name):
        return subprocess.check_output(['git', '-C', str(repo), 'show', COMMIT + ':' + base + '/' + name])
    raw = git('INDEX.json')
    index = json.loads(raw)
    save(state / 'INDEX.json', raw)
    path = state / index['original_file']
    if not path.exists():
        parts = []
        for i, p in enumerate(index['parts']):
            if p['index'] != i:
                raise ValueError('Original part order required')
            b = git(p['file_name'])
            if len(b) != p['bytes'] or sha(b) != p['sha256']:
                raise ValueError('Public part differs')
            if hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() != p['git_blob_sha1']:
                raise ValueError('Public git blob differs')
            parts.append(b)
        save(path, b''.join(parts))
    b = path.read_bytes()
    if len(b) != index['original_bytes'] or sha(b) != index['original_sha256']:
        raise ValueError('Original concatenated archive differs')
    return path


def extract(path, destination, selected=None):
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError('Public archive CRC differs')
        manifest = json.loads(z.read('MANIFEST_SHA256.json'))
        for member in manifest['members']:
            name = member.get('name', member.get('path'))
            p = Path(name)
            if p.is_absolute() or '..' in p.parts:
                raise ValueError('Relative original archive paths required')
            b = z.read(name)
            if len(b) != member['bytes'] or sha(b) != member['sha256']:
                raise ValueError('Original member differs: ' + name)
            if selected is None or name in selected:
                save(destination / p, b)
        if selected is None:
            save(destination / 'MANIFEST_SHA256.json', z.read('MANIFEST_SHA256.json'))
    return len(manifest['members'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--normalize', action='store_true')
    a = p.parse_args()
    h1 = a.state / 'h1_validation'
    n = extract(archive(a.repo, h1, 'e5_h1_tail_coverage_pair'), h1 / 'original')
    bear = a.state / 'e5-bear-original'
    extract(archive(a.repo, bear, 'e5_bear_recovery'), bear,
            {'source_increment/modules/native_action/e5_teacher.py'})
    print(json.dumps(dict(status='PASS_ORIGINAL_ARCHIVES_AND_MEMBERS', H1_members=n,
        provider_downloads=0, wallets=0, fits=0)), flush=True)
    if a.normalize:
        def blocked(*args, **kwargs):
            raise RuntimeError('Offline normalization forbids network connections')
        socket.create_connection = blocked
        socket.socket.connect = blocked
        sys.argv = ['normalize_e5_cached_archives.py', '--root', str(a.repo.resolve()),
                    '--work', str((h1 / 'original/h1_market').resolve())]
        runpy.run_path(h1 / 'original/offline_importer/normalize_e5_cached_archives.py', run_name='__main__')


if __name__ == '__main__':
    main()
