"""One metadata audit: official HEAD/CHECKSUM and primary docs, no ZIP body."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import resource
import time

import httpx

ROOT=Path('/mnt/d/codex/coin')
STATE=Path('/home/xflops/coin-state')
UPSTREAM='f446ce3812bd4e5521f21faecd4ae3c6460e49fc'
BASE='https://data.binance.vision/data'
FOLDS=(('v8_A','2025-08-20','2025-08-27'),('v8_B','2025-09-25','2025-10-02'),
       ('v8_C','2025-10-24','2025-10-31'),('v8_D','2025-11-18','2025-11-25'))
SYMBOLS=('BTCUSDT','ETHUSDT')

def sha(data):return hashlib.sha256(data).hexdigest()
parser=argparse.ArgumentParser()
parser.add_argument('--run-dir',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
run,output=args.run_dir.resolve(),args.output.resolve()
assert run.is_relative_to(STATE) and not run.exists()
assert output.is_relative_to(ROOT/'reports/fast_research') and not output.exists()
run.mkdir()
started=time.monotonic()
client=httpx.Client(timeout=httpx.Timeout(12,connect=10),follow_redirects=False,
                    headers={'User-Agent':'coin-v8-public-metadata-audit/1.0'})

def access(url,method='GET',limit=4096):
    value={'url':url,'method':method,'access_utc':datetime.now(UTC).isoformat()}
    try:
        with client.stream(method,url) as response:
            value.update(http_status=response.status_code,content_length=response.headers.get('content-length'),
                         content_type=response.headers.get('content-type'),etag=response.headers.get('etag'),
                         last_modified=response.headers.get('last-modified'),location=response.headers.get('location'))
            if method=='HEAD':
                value.update(body_downloaded=False,body_bytes_read=0)
                return value,None
            data=bytearray()
            for chunk in response.iter_bytes():
                if len(data)+len(chunk)>limit:
                    value.update(body_truncated=True,body_bytes_read=len(data),partial_body_sha256=sha(data))
                    return value,None
                data.extend(chunk)
            value.update(body_downloaded=True,body_bytes_read=len(data),body_sha256=sha(data),body_truncated=False)
            return value,bytes(data)
    except Exception as error:
        value.update(http_status=None,error_type=type(error).__name__,error=str(error)[:300])
        return value,None

primary=[]
documents=[('pinned_readme',f'https://raw.githubusercontent.com/binance/binance-public-data/{UPSTREAM}/README.md'),
           ('pinned_data_terms',f'https://raw.githubusercontent.com/binance/binance-public-data/{UPSTREAM}/TERMS_AND_CONDITIONS.md'),
           ('futures_market_data','https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data'),
           ('futures_account','https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account'),
           ('spot_market_streams','https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/ws-streams/~'),
           ('data_landing','https://data.binance.vision/')]
for name,url in documents:
    record,body=access(url,limit=2_000_000)
    record['name']=name
    if body is not None:
        path=run/(name+'.primary-body')
        with path.open('xb') as stream:stream.write(body)
        record['local_body_path']=str(path)
    primary.append(record)
    print(json.dumps({'phase':'官方文档访问','name':name,'http_status':record['http_status'],'body_truncated':record.get('body_truncated')}),flush=True)

for number in (372,437,447):
    url=f'https://api.github.com/repos/binance/binance-public-data/issues/{number}/comments'
    record,body=access(url,limit=1_000_000)
    record['name']=f'official_repository_issue_{number}_comments'
    if body is not None:
        path=run/f'official-repo-issue-{number}-comments.json'
        with path.open('xb') as stream:stream.write(body)
        record['local_body_path']=str(path)
        if record['http_status']==200:
            record['maintainer_comments']=[{'url':item['html_url'],'author':item['user']['login'],
                'author_association':item['author_association'],'body_sha256':sha(item['body'].encode()),
                'created_at':item['created_at']} for item in json.loads(body)
                if item['author_association'] in ('MEMBER','OWNER','COLLABORATOR')]
    primary.append(record)

entries=[]
for fold,first,end in FOLDS:
    day=date.fromisoformat(first)
    while day<date.fromisoformat(end):
        assert date(2025,8,1)<=day<date(2025,12,1)
        for symbol in SYMBOLS:
            for market,kind in (('spot','bookTicker'),('futures/um','bookTicker'),('futures/um','bookDepth')):
                entries.append({'fold':fold,'market':market,'kind':kind,'date':str(day),'partition':'daily',
                    'symbol':symbol,'url':f'{BASE}/{market}/daily/{kind}/{symbol}/{symbol}-{kind}-{day}.zip'})
        day+=timedelta(days=1)
for month in ('2025-08','2025-09','2025-10','2025-11'):
    for symbol in SYMBOLS:
        for market,kind in (('spot','bookTicker'),('futures/um','bookTicker'),('futures/um','bookDepth'),
                            ('futures/um','fundingRate'),('futures/um','markPriceKlines'),
                            ('futures/um','indexPriceKlines'),('futures/um','premiumIndexKlines')):
            is_kline=kind.endswith('Klines')
            suffix='/1m' if is_kline else ''
            filename=f'{symbol}-1m-{month}.zip' if is_kline else f'{symbol}-{kind}-{month}.zip'
            entries.append({'fold':None,'market':market,'kind':kind,'month':month,'partition':'monthly',
                'symbol':symbol,'interval':'1m' if is_kline else None,
                'url':f'{BASE}/{market}/monthly/{kind}/{symbol}{suffix}/{filename}'})

def inspect(entry):
    head,_=access(entry['url'],'HEAD')
    proof,body=access(entry['url']+'.CHECKSUM')
    checksum=None
    if proof['http_status']==200 and body is not None:
        fields=body.decode().strip().split()
        valid=len(fields)==2 and len(fields[0])==64 and all(c in '0123456789abcdef' for c in fields[0].lower()) and fields[1].lstrip('*')==entry['url'].rsplit('/',1)[-1]
        checksum={'format_and_filename_valid':valid,'announced_zip_sha256':fields[0].lower() if valid else None,
                  'checksum_text':body.decode() if valid else None}
    length=None
    if head['http_status']==200 and head.get('content_length','').isdigit():length=int(head['content_length'])
    return {**entry,'head':head,'checksum_access':proof,'checksum':checksum,
            'announced_zip_bytes':length,'archive_body_downloaded':False,
            'archive_integrity_or_rows_verified':False,
            'metadata_object_available':head['http_status']==200 and checksum is not None and checksum['format_and_filename_valid']}

checked=[]
with ThreadPoolExecutor(max_workers=4) as pool:
    futures=[pool.submit(inspect,entry) for entry in entries]
    for future in as_completed(futures):
        checked.append(future.result())
        print(json.dumps({'phase':'官方档案HEAD与CHECKSUM','completed_metadata_objects':len(checked),
                          'total_metadata_objects':len(entries),'unit':'档案元数据'}),flush=True)
checked.sort(key=lambda value:(value['market'],value['kind'],value['partition'],value.get('date') or value.get('month'),value['symbol']))
groups=[]
for market,kind,partition in sorted({(row['market'],row['kind'],row['partition']) for row in checked}):
    rows=[row for row in checked if (row['market'],row['kind'],row['partition'])==(market,kind,partition)]
    sizes=[row['announced_zip_bytes'] for row in rows if row['metadata_object_available']]
    groups.append({'market':market,'kind':kind,'partition':partition,'metadata_objects_checked':len(rows),
        'objects_available_with_official_checksum':sum(row['metadata_object_available'] for row in rows),
        'head_http_status_counts':dict(Counter(str(row['head']['http_status']) for row in rows)),
        'checksum_http_status_counts':dict(Counter(str(row['checksum_access']['http_status']) for row in rows)),
        'compressed_bytes_for_available_objects':sum(sizes) if sizes and None not in sizes else None,
        'compressed_capacity_all_required_objects':sum(sizes) if len(sizes)==len(rows) and None not in sizes else None,
        'uncompressed_capacity':None,'actual_row_calendar_coverage':'UNKNOWN_METADATA_ONLY'})
report={'status':'COMPLETED_OFFICIAL_INPUT_METADATA_AUDIT_NOT_SOURCE_ACCEPTANCE',
    'created_utc':datetime.now(UTC).isoformat(),'upstream_commit':UPSTREAM,'folds':FOLDS,
    'primary_accesses':primary,'groups':groups,'objects':checked,
    'archive_bodies_downloaded':False,'archive_zip_bytes_read':0,'row_or_model_outcomes_read':False,
    'locked_consumed':False,'market_models_fit':0,'orders_sent':0,'keys_used':False,'paid_services_used':False,
    'collector_or_framework_created':False,'shared_registry_appended':False,'new_scan_executed':False,
    'script_sha256':sha(Path(__file__).read_bytes()),'elapsed_seconds':time.monotonic()-started,
    'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    'software_license':'README MIT declaration, no standalone LICENSE; dataset terms are separate',
    'data_terms_sha256':next((item.get('body_sha256') for item in primary if item['name']=='pinned_data_terms'),None)}
with output.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps({'status':report['status'],'objects':len(checked),'groups':groups,
                  'elapsed_seconds':report['elapsed_seconds'],'peak_rss_bytes':report['peak_rss_bytes'],
                  'output_sha256':sha(output.read_bytes())}),flush=True)
