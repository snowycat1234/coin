"""Recover immutable public GitHub parts and verify every original member."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from bisect import bisect_right
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
from urllib.request import Request, urlopen
import zipfile
import zlib

PREFIX = 'research/core5-q4-2024-native-data'


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


def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name:
        raise ValueError('Unsafe member path')
    return path


def reference_body(pack, member, base):
    starts = [0]
    for part in pack['parts']:
        starts.append(starts[-1] + part['bytes'])
    if starts[-1] != pack['original_bytes']:
        raise ValueError('Invalid source pack lengths')
    transferred = requests = 0

    def fetch(offset, count):
        nonlocal transferred, requests
        if offset < 0 or count < 1 or offset + count > starts[-1]:
            raise ValueError('Source member range outside declared pack')
        bodies = []
        while count:
            index = bisect_right(starts, offset) - 1
            part = pack['parts'][index]
            local = offset - starts[index]
            size = min(count, part['bytes'] - local)
            name = part['file_name']
            if re.fullmatch(r'coin_public_tail_archives_20261008_part0[123]\.zip\.bytepart[0-9]{3}', name) is None:
                raise ValueError('Invalid immutable source part name')
            request = Request(base + name, headers={'Range': f'bytes={local}-{local+size-1}'})
            with urlopen(request, timeout=30) as response:
                if response.status != 206 or response.headers.get('Content-Range') != f"bytes {local}-{local+size-1}/{part['bytes']}":
                    raise ValueError('Exact source byte range was not served')
                body = response.read(size + 1)
                if len(body) != size:
                    raise ValueError('Source range length mismatch')
            bodies.append(body)
            transferred += size
            requests += 1
            offset += size
            count -= size
        return b''.join(bodies)

    if member['compression'] != zipfile.ZIP_STORED or member['compressed_bytes'] != member['bytes']:
        raise ValueError('Source wrapper member must be stored unchanged')
    offset = member['local_header_offset']
    fields = struct.unpack('<4s5H3I2H', fetch(offset, 30))
    if fields[0] != b'PK\x03\x04' or fields[2] & 1 or fields[3] != zipfile.ZIP_STORED:
        raise ValueError('Source local header identity failed')
    name_length, extra_length = fields[-2:]
    if not 0 < name_length < 1024 or extra_length >= 4096:
        raise ValueError('Invalid source header metadata lengths')
    metadata = fetch(offset + 30, name_length + extra_length)
    if metadata[:name_length].decode('utf-8') != member['name']:
        raise ValueError('Source member identity mismatch')
    body = fetch(offset + 30 + name_length + extra_length, member['bytes'])
    if f'{zlib.crc32(body):08x}' != member['CRC32']:
        raise ValueError('Source outer member CRC failed')
    return body, transferred, requests


def recover(commit, fold, output, cache_root=None):
    if re.fullmatch('[0-9a-f]{40}', commit) is None:
        raise ValueError('Use a full immutable 40-character Git commit')
    if shutil.disk_usage(output.parent).free < 15 * 1024**3 + 200 * 1024**2:
        raise ValueError('Keep a 15 GiB free-space reserve')
    output.mkdir(parents=True, exist_ok=False)
    base = f'https://raw.githubusercontent.com/snowycat1234/coin/{commit}/{PREFIX}/{fold}/'
    index_bytes = remote(base + 'INDEX.json', 250000)
    index = json.loads(index_bytes)
    if index['schema'] != 'CORE5_NATIVE_MINUTE_REFERENCE_AND_DELTA_PARTS_V1' or index['fold'] != fold:
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
            name = safe_path(record['name'])
            body = archive.read(str(name))
            if len(body) != record['bytes'] or hashlib.sha256(body).hexdigest() != record['SHA256']:
                raise ValueError('Recovered original member SHA/size failed')
            path = target / str(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
    raw = json.loads((target / 'RAW_MANIFEST.json').read_text())
    refs = json.loads((target / 'PUBLIC_REFERENCES.json').read_text())
    source_commit = refs['source_commit']
    if source_commit != 'd69e9ac94478c5be54cb46c622afec7aaf3c61f7' or len(refs['records']) != 45:
        raise ValueError('Unexpected original public source identity/count')
    source_base = f'https://raw.githubusercontent.com/snowycat1234/coin/{source_commit}/research_artifacts/native_20261008/byteparts/'
    by_path = {r['relative_raw_path']: r for r in raw['records']}
    packs = {p['original_file']: p for p in refs['packs']}
    copied = source_bytes = source_requests = fetched = 0
    for record in refs['records']:
        relative = str(safe_path(record['relative_raw_path']))
        original = by_path[relative]
        if record['SHA256'] != original['SHA256'] or record['bytes'] != original['size']:
            raise ValueError('Source reference differs from fresh official identity')
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        cached = cache_root / relative if cache_root is not None else None
        if cached is not None and cached.is_file():
            if cached.stat().st_size != record['bytes'] or sha(cached) != record['SHA256']:
                raise ValueError('Cached reference source SHA/size mismatch')
            shutil.copyfile(cached, path)
            copied += 1
        else:
            body, transferred, requests = reference_body(packs[record['source_pack']], record['member'], source_base)
            if len(body) != record['bytes'] or hashlib.sha256(body).hexdigest() != record['SHA256']:
                raise ValueError('Remote referenced archive official SHA/size mismatch')
            path.write_bytes(body)
            source_bytes += transferred
            source_requests += requests
            fetched += 1
        Path(str(path) + '.CHECKSUM').write_text(original['checksum_text'])
    if raw['archive_count'] != 55 or len(raw['records']) != 55 or copied + fetched != 45:
        raise ValueError('Unexpected complete source archive count')
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
        every_original_official_SHA_and_ZIP_CRC_verified=True, concurrency=4,
        remote_delta_original_archives=10, referenced_original_archives_copied_from_SHA_verified_cache=copied,
        referenced_original_archives_fetched_by_exact_public_range=fetched,
        referenced_public_range_body_bytes=source_bytes, referenced_public_range_requests=source_requests,
        reference_source_commit=source_commit, provider_archive_download_bytes=0,
        whole_referenced_outer_pack_or_parts_SHA256_verified=False,
        referenced_integrity_scope='Selected original archive SHA256 and inner ZIP CRC verified; fetched outer stored member CRC checked; full old source packs/parts not fetched')
    (output / 'REMOTE_RECOVERY.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commit', required=True)
    p.add_argument('--fold', choices=['Q42024'], required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cache-root', type=Path, help='Optional SHA-verified existing Q42024 root containing raw/...')
    args = p.parse_args()
    recover(args.commit, args.fold, args.output, args.cache_root)
