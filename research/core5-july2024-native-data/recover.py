"""Recover immutable public GitHub parts and verify every original member."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.request import urlopen
import zipfile

PREFIX = 'research/core5-july2024-native-data'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def remote(url, limit):
    with urlopen(url, timeout=30) as response:
        if response.status != 200:
            raise ValueError(f'HTTP {response.status}: {url}')
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError('Remote file exceeded its bounded declared size')
        return body


def recover(commit, fold, output):
    if re.fullmatch('[0-9a-f]{40}', commit) is None:
        raise ValueError('Use a full immutable 40-character Git commit')
    output.mkdir(parents=True, exist_ok=False)
    base = f'https://raw.githubusercontent.com/snowycat1234/coin/{commit}/{PREFIX}/{fold}/'
    index_bytes = remote(base + 'INDEX.json', 250000)
    index = json.loads(index_bytes)
    if index['schema'] != 'CORE5_NATIVE_MINUTE_ORIGINALS_PARTS_V1' or index['fold'] != fold:
        raise ValueError('Unexpected index identity')
    if index['maximum_part_bytes'] > 768 * 1024:
        raise ValueError('Part size limit exceeded')
    (output / 'INDEX.json').write_bytes(index_bytes)
    parts = output / 'parts'
    parts.mkdir()
    def obtain(record):
        name = record['name']
        if re.fullmatch(r'originals\.zip\.part[0-9]{4}', name) is None or not 0 < record['bytes'] <= 768*1024:
            raise ValueError('Invalid part name/length')
        body = remote(base + name, record['bytes'])
        if len(body) != record['bytes'] or hashlib.sha256(body).hexdigest() != record['SHA256']:
            raise ValueError(f'Remote part SHA/size mismatch: {name}')
        (parts / name).write_bytes(body)
        return name
    with ThreadPoolExecutor(max_workers=4) as pool:
        obtained = list(pool.map(obtain, index['parts']))
    package = output / 'originals.zip'
    with package.open('xb') as out:
        for record in index['parts']:
            out.write((parts / record['name']).read_bytes())
    if package.stat().st_size != index['package_bytes'] or sha(package) != index['package_SHA256']:
        raise ValueError('Reassembled wrapper SHA/size mismatch')
    target = output / fold
    target.mkdir()
    with zipfile.ZipFile(package) as archive:
        if archive.testzip() is not None or archive.namelist() != [x['name'] for x in index['members']]:
            raise ValueError('Wrapper CRC/member identity failed')
        for record in index['members']:
            name = PurePosixPath(record['name'])
            if name.is_absolute() or '..' in name.parts or '\\' in str(name):
                raise ValueError('Unsafe member path')
            body = archive.read(str(name))
            if len(body) != record['bytes'] or hashlib.sha256(body).hexdigest() != record['SHA256']:
                raise ValueError('Recovered original member SHA/size failed')
            path = target / str(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
    raw = json.loads((target / 'RAW_MANIFEST.json').read_text())
    for record in raw['records']:
        path = target / record['relative_raw_path']
        if path.stat().st_size != record['size'] or sha(path) != record['SHA256']:
            raise ValueError('Recovered source differs from original official checksum')
        words = Path(str(path) + '.CHECKSUM').read_text().split()
        if words != [record['SHA256'], path.name]:
            raise ValueError('Recovered official CHECKSUM sidecar differs')
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError('Recovered original ZIP CRC failed')
    receipt = dict(status='REMOTE_IMMUTABLE_SHA_AND_ORIGINAL_BYTE_RECOVERY_VERIFIED',
        checked_UTC=datetime.now(timezone.utc).isoformat(), commit=commit, fold=fold,
        index_URL=base+'INDEX.json', index_SHA256=hashlib.sha256(index_bytes).hexdigest(),
        part_count=len(obtained), remote_part_bytes=sum(x['bytes'] for x in index['parts']),
        package_SHA256=sha(package), recovered_original_archive_count=raw['archive_count'],
        recovered_original_compressed_bytes=raw['total_original_compressed_bytes'],
        every_original_official_SHA_and_ZIP_CRC_verified=True, concurrency=4)
    (output / 'REMOTE_RECOVERY.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commit', required=True)
    p.add_argument('--fold', choices=['JULY2024'], required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    recover(args.commit, args.fold, args.output)
