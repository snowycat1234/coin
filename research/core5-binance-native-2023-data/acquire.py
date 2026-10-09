"""Bounded official CORE5 trade/mark minute inventory and raw download."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile

SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
FAMILIES = ('klines', 'markPriceKlines')
MONTHS = ('2023-07', '2023-08', '2023-09', '2023-10', '2023-11', '2023-12')
BASE = 'https://data.binance.vision/'
LIST_BASE = 'https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'
BUDGET = 150 * 2**20
WORKERS = 4


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def small_get(url, limit=250000):
    with urlopen(Request(url), timeout=30) as response:
        assert response.status == 200
        data = response.read(limit + 1)
        assert len(data) <= limit
        return data


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def inventory(root):
    listings = root / 'official-listings'
    listings.mkdir(parents=True, exist_ok=True)
    def listing(pair):
        symbol, family = pair
        prefix = f'data/futures/um/monthly/{family}/{symbol}/1m/'
        url = LIST_BASE + '?' + urlencode(dict(prefix=prefix, **{'list-type': '2', 'start-after': prefix + symbol + '-1m-2023-06.zip.CHECKSUM', 'max-keys': 12}))
        raw = small_get(url)
        (listings / (symbol + '_' + family + '.xml')).write_bytes(raw)
        tree = ET.fromstring(raw)
        ns = {'s': 'http://s3.amazonaws.com/doc/2006-03-01/'}
        result = {}
        for node in tree.findall('s:Contents', ns):
            key = node.findtext('s:Key', namespaces=ns)
            result[key] = dict(size=int(node.findtext('s:Size', namespaces=ns)),
                last_modified=node.findtext('s:LastModified', namespaces=ns),
                ETag=node.findtext('s:ETag', namespaces=ns), listing_url=url)
        records = []
        for month in MONTHS:
            key = prefix + symbol + '-1m-' + month + '.zip'
            assert key in result and key + '.CHECKSUM' in result, key
            records.append(dict(symbol=symbol, family=family, month=month, key=key,
                url=BASE + key, checksum_url=BASE + key + '.CHECKSUM', **result[key]))
        return records
    pairs = [(s, f) for s in SYMBOLS for f in FAMILIES]
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        records = [r for group in pool.map(listing, pairs) for r in group]
    def proof(record):
        raw = small_get(record['checksum_url'], 1000)
        words = raw.decode().strip().split()
        assert len(words) == 2 and words[1] == record['url'].rsplit('/', 1)[1]
        assert len(words[0]) == 64 and all(c in '0123456789abcdef' for c in words[0])
        # HEAD independently confirms the archive's declared length before any GET.
        with urlopen(Request(record['url'], method='HEAD'), timeout=30) as response:
            assert response.status == 200
            assert int(response.headers['Content-Length']) == record['size']
            headers = dict(Content_Length=int(response.headers['Content-Length']),
                Content_Type=response.headers.get('Content-Type'), Last_Modified=response.headers.get('Last-Modified'))
        return dict(record, SHA256=words[0], checksum_text=raw.decode(), HEAD=headers)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        records = list(pool.map(proof, records))
    totals = {fold: sum(r['size'] for r in records if r['month'] in months)
              for fold, months in [('JULY2023', MONTHS[:3]), ('OCTOBER2023', MONTHS[3:])]}
    result = dict(schema='OFFICIAL_BINANCE_MISSING_CORE5_MINUTE_INVENTORY_V1',
        checked_UTC=datetime.now(timezone.utc).isoformat(), symbols=list(SYMBOLS), families=list(FAMILIES),
        months=list(MONTHS), archive_count=len(records), expected_compressed_bytes=sum(totals.values()),
        fold_compressed_bytes=totals, compressed_download_budget_bytes=BUDGET,
        status='WITHIN_BUDGET' if sum(totals.values()) <= BUDGET else 'STOP_EXPECTED_TOTAL_EXCEEDS_BUDGET',
        modest_concurrency=WORKERS, records=records,
        local_missing_inventory='Parent native inventory reports both folds absent; local cached files contain H1/test packs, no matching 2023 trade/mark months.',
        daily_and_funding='Existing external source-bound contexts; no duplicate download.',
        no_proxy_or_access_bypass=True)
    write_json(root / 'INVENTORY.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}), flush=True)


def download(root, fold):
    inv = json.loads((root / 'INVENTORY.json').read_text())
    assert inv['status'] == 'WITHIN_BUDGET' and inv['expected_compressed_bytes'] <= BUDGET
    months = MONTHS[:3] if fold == 'JULY2023' else MONTHS[3:]
    records = [r for r in inv['records'] if r['month'] in months]
    raw_root = root / fold / 'raw'
    assert sum(r['size'] for r in inv['records']) <= BUDGET
    def obtain(record):
        assert shutil.disk_usage(root).free > 15 * 2**30
        path = raw_root / record['family'] / record['symbol'] / Path(record['key']).name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            assert path.stat().st_size == record['size'] and sha(path) == record['SHA256']
            reused = True
        else:
            temporary = path.with_suffix('.zip.partial')
            assert not temporary.exists(), 'Inspect retained partial download before resuming'
            count = 0
            try:
                with urlopen(Request(record['url']), timeout=30) as response, temporary.open('xb') as out:
                    assert response.status == 200
                    assert int(response.headers['Content-Length']) == record['size']
                    while True:
                        chunk = response.read(1 << 20)
                        if not chunk:
                            break
                        count += len(chunk)
                        assert count <= record['size']
                        out.write(chunk)
                assert count == record['size'] and sha(temporary) == record['SHA256']
                temporary.rename(path)
            except BaseException:
                # Retain any incomplete original bytes separately, never label them verified.
                raise
            reused = False
        checksum = Path(str(path) + '.CHECKSUM')
        checksum.write_text(record['checksum_text'])
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None and len(archive.namelist()) == 1
            member = archive.infolist()[0]
            member_info = dict(name=member.filename, bytes=member.file_size, CRC32=f'{member.CRC:08x}')
        print(json.dumps(dict(fold=fold, verified=path.name, family=record['family'], bytes=record['size'])), flush=True)
        return dict(record, relative_raw_path=str(path.relative_to(root / fold)),
            reused_verified_local_file=reused, ZIP_CRC_verified=True, member=member_info)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        verified = list(pool.map(obtain, records))
    result = dict(status='RAW_ARCHIVES_VERIFIED_MINUTE_COVERAGE_NOT_YET_CHECKED', fold=fold,
        archive_count=len(verified), total_original_compressed_bytes=sum(r['size'] for r in verified),
        elapsed_seconds=time.monotonic()-started, records=verified,
        model_fits=0, backtests=0, funding_downloads=0)
    write_json(root / fold / 'RAW_MANIFEST.json', result)
    print(json.dumps({k:v for k,v in result.items() if k != 'records'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inventory', 'download'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--fold', choices=('JULY2023', 'OCTOBER2023'))
    args = parser.parse_args()
    if args.command == 'inventory':
        inventory(args.root)
    else:
        assert args.fold
        download(args.root, args.fold)
