"""Fixed 2021 CORE5 official execution/funding-mark sources; no 2020 bodies."""
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
MONTHS = tuple(f'2021-{month:02d}' for month in range(1,13))
BASE = 'https://data.binance.vision/'
LIST_BASE = 'https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'
BUDGET = 180 * 2**20
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


def inventory(root, supplement=False):
    listings = root / 'official-listings'
    listings.mkdir(parents=True, exist_ok=True)
    requests = []
    assert not supplement, 'Unexpected supplements require a new bounded gap plan'
    for symbol in SYMBOLS:
        for family in FAMILIES:
            periods = MONTHS if family == 'klines' else MONTHS[:-1]
            requests.append((symbol, family, 'monthly', periods, '2020-12', '-1m'))
    prior = None
    if supplement:
        prior = json.loads((root/'INVENTORY.json').read_text())
        gaps = json.loads((root/'SOURCE_GAPS.json').read_text())
        for r in gaps['records']:
            for day in r['target_official_daily_dates']:
                from datetime import date,timedelta
                previous = str(date.fromisoformat(day)-timedelta(days=1))
                requests.append((r['symbol'],r['family'],'daily',(day,),previous,'-1m'))
    def listing(request):
        symbol, family, frequency, periods, previous, interval = request
        prefix = f'data/futures/um/{frequency}/{family}/{symbol}/' + ('1m/' if interval else '')
        stem = symbol + (interval if interval else '-fundingRate')
        url = LIST_BASE + '?' + urlencode(dict(prefix=prefix, **{'list-type': '2', 'start-after': prefix + stem + '-' + previous + '.zip.CHECKSUM', 'max-keys': 2*len(periods)}))
        raw = small_get(url)
        (listings / (symbol + '_' + family + '_' + frequency + '_' + periods[0] + '.xml')).write_bytes(raw)
        tree = ET.fromstring(raw)
        ns = {'s': 'http://s3.amazonaws.com/doc/2006-03-01/'}
        result = {}
        for node in tree.findall('s:Contents', ns):
            key = node.findtext('s:Key', namespaces=ns)
            result[key] = dict(size=int(node.findtext('s:Size', namespaces=ns)),
                last_modified=node.findtext('s:LastModified', namespaces=ns),
                ETag=node.findtext('s:ETag', namespaces=ns), listing_url=url)
        records = []
        for period in periods:
            key = prefix + stem + '-' + period + '.zip'
            assert key in result and key + '.CHECKSUM' in result, key
            records.append(dict(symbol=symbol, family=family, month=period[:7], source_period=period,
                source_frequency=frequency, key=key,
                url=BASE + key, checksum_url=BASE + key + '.CHECKSUM', **result[key]))
        return records
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        records = [r for group in pool.map(listing, requests) for r in group]
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
    planned = json.loads((root/'protocol/MISSING_MINUTE_ORIGINALS.json').read_text())['records']
    planned = {r['key']:r for r in planned if r['month'].startswith('2021-')
        and not (r['family']=='markPriceKlines' and r['month']=='2021-12')}
    assert len(records)==len(planned)==115
    assert sum(r['size'] for r in records)==164149016, 'Unexpected source volume; stop before body download'
    cached = list((root/'Y2021/raw').rglob('*.zip'))
    for record in records:
        assert record['key'] in planned and record['size']==planned[record['key']]['bytes']
        record['cached_verified_path'] = next((str(p) for p in cached if p.name == Path(record['key']).name
            and p.stat().st_size == record['size'] and sha(p) == record['SHA256']), None)
    supplemental = records.copy()
    if supplement:
        for record in records:
            record['gap_supplement'] = True
        oldkeys = {r['key'] for r in prior['records']}
        if any(r['key'] in oldkeys for r in records):
            raise ValueError('Supplement source was already inventoried; reuse evidence')
        records = prior['records']+records
    total = sum(r['size'] for r in records)
    new = sum(r['size'] for r in records if not r['cached_verified_path'])
    result = dict(schema='OFFICIAL_BINANCE_FIXED2021_ECONOMIC_SOURCE_INVENTORY_V1',
        checked_UTC=datetime.now(timezone.utc).isoformat(), symbols=list(SYMBOLS), families=list(FAMILIES),
        archive_count=len(records), expected_compressed_bytes=total, expected_new_download_bytes=new,
        reuse_archive_count=sum(r['cached_verified_path'] is not None for r in records),
        compressed_download_budget_bytes=BUDGET,
        status='WITHIN_BUDGET' if new <= BUDGET else 'STOP_EXPECTED_TOTAL_EXCEEDS_BUDGET',
        modest_concurrency=WORKERS, records=records,
        interval_UTC_start_inclusive='2021-01-01', interval_UTC_end_exclusive='2022-01-01',
        daily_feature_inputs='Existing external primitive tables unchanged; no feature reconstruction.',
        prefix_context='No 2020 minute archive; first January1 midnight funding is unowned by fresh CASH.',
        source_roles='Jan-Dec actual trade minutes; Jan-Nov actual mark minutes; cached Dec actual event marks and original signed funding events reused.',
        no_proxy_or_access_bypass=True)
    write_json(root / 'INVENTORY.json', result)
    if supplement:
        write_json(root/'SUPPLEMENT_INVENTORY.json',dict(reason='Only targeted official daily source units for actual monthly missing minutes',
            additional_archives=len(supplemental),additional_expected_body_bytes=sum(r['size'] for r in supplemental),
            cumulative_new_body_estimate=new,status=result['status'],records=supplemental))
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}), flush=True)


def download(root, fold):
    inv = json.loads((root / 'INVENTORY.json').read_text())
    assert inv['status'] == 'WITHIN_BUDGET' and inv['expected_new_download_bytes'] <= BUDGET
    records = inv['records']
    raw_root = root / fold / 'raw'
    assert sum(r['size'] for r in inv['records'] if not r['cached_verified_path']) <= BUDGET
    def obtain(record):
        assert shutil.disk_usage(root).free > 15 * 2**30
        path = raw_root / record['family'] / record['symbol'] / Path(record['key']).name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            assert path.stat().st_size == record['size'] and sha(path) == record['SHA256']
            reused = True
        elif record['cached_verified_path']:
            cached = Path(record['cached_verified_path'])
            assert cached.stat().st_size == record['size'] and sha(cached) == record['SHA256']
            shutil.copyfile(cached, path)
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
        new_original_download_bytes=sum(r['size'] for r in verified if not r['cached_verified_path']),
        this_pass_original_download_bytes=sum(r['size'] for r in verified if not r['reused_verified_local_file']),
        reused_from_previous_tasks_archive_count=sum(bool(r['cached_verified_path']) and not r.get('selective_public_recovery') for r in verified),
        reused_from_public_repository_archive_count=sum(bool(r.get('selective_public_recovery')) for r in verified),
        reused_verified_archive_count=sum(r['reused_verified_local_file'] for r in verified),
        elapsed_seconds=time.monotonic()-started, records=verified,
        model_fits=0, backtests=0)
    write_json(root / fold / 'RAW_MANIFEST.json', result)
    print(json.dumps({k:v for k,v in result.items() if k != 'records'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inventory', 'download'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--fold', choices=('Y2021',))
    parser.add_argument('--supplement-source-gaps',action='store_true')
    args = parser.parse_args()
    if args.command == 'inventory':
        inventory(args.root,args.supplement_source_gaps)
    else:
        assert args.fold
        download(args.root, args.fold)
