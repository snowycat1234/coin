"""Check only official daily marks needed for observed owned funding-mark gaps."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta,date
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import acquire

ROOT=Path('/workspace/coin-2021-data')
folder=ROOT/'Y2021'
validation=json.loads((folder/'VALIDATION.json').read_text())
inventory=json.loads((ROOT/'INVENTORY.json').read_text())
assert inventory['archive_count']==115,'Gap plan is single-pass, do not duplicate requests'
targets=[]
for symbol in acquire.SYMBOLS:
    events=pq.read_table(folder/f'derived/economics/{symbol}_funding_events.parquet',use_threads=False).to_pandas(use_threads=False)
    t=events.calc_time_ms.to_numpy(np.int64)*1000
    owned=(t>1609459260000001)&(t<=1640908860000001)
    invalid=~np.isfinite(events.past_mark_price.to_numpy(float))
    missing_open=((t[owned&invalid]-1)//60000000)*60000000-60000000
    days=sorted(set(str(d.date()) for d in pd.to_datetime(missing_open,unit='us',utc=True)))
    targets.extend((symbol,day) for day in days)
assert len(targets)<=25 and all('2021-01-01'<=d<='2021-11-30' for s,d in targets)

def listing(target):
    symbol,day=target;prefix=f'data/futures/um/daily/markPriceKlines/{symbol}/1m/'
    previous=str(date.fromisoformat(day)-timedelta(days=1))
    key=prefix+f'{symbol}-1m-{day}.zip'
    url=acquire.LIST_BASE+'?'+urlencode(dict(prefix=prefix,**{'list-type':2,'start-after':prefix+f'{symbol}-1m-{previous}.zip.CHECKSUM','max-keys':2}))
    body=acquire.small_get(url);(ROOT/'official-listings'/f'{symbol}_markPriceKlines_daily_{day}.xml').write_bytes(body)
    tree=ET.fromstring(body);ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
    listed={x.findtext('s:Key',namespaces=ns):x for x in tree.findall('s:Contents',ns)}
    if key not in listed or key+'.CHECKSUM' not in listed:
        return dict(symbol=symbol,day=day,status='OFFICIAL_DAILY_ARCHIVE_NOT_LISTED',listing_URL=url,archive_body_bytes=0)
    x=listed[key];size=int(x.findtext('s:Size',namespaces=ns));assert size<250000,'Unexpected daily body volume'
    archive_url=acquire.BASE+key;checksum_url=archive_url+'.CHECKSUM'
    checksum=acquire.small_get(checksum_url,1000);words=checksum.decode().strip().split()
    assert len(words)==2 and words[1]==key.rsplit('/',1)[1] and len(words[0])==64
    with urlopen(Request(archive_url,method='HEAD'),timeout=30) as r:
        assert r.status==200 and int(r.headers['Content-Length'])==size
    record=dict(symbol=symbol,family='markPriceKlines',month=day[:7],source_period=day,source_frequency='daily',
        key=key,url=archive_url,checksum_url=checksum_url,size=size,SHA256=words[0],checksum_text=checksum.decode(),
        ETag=x.findtext('s:ETag',namespaces=ns),last_modified=x.findtext('s:LastModified',namespaces=ns),
        listing_url=url,cached_verified_path=None,gap_supplement=True)
    return dict(symbol=symbol,day=day,status='AVAILABLE_TARGETED_OFFICIAL_DAILY',record=record)

with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(listing,targets))
available=[r['record'] for r in results if 'record' in r]
new=sum(r['size'] for r in available)
assert 164149016+new<=180*2**20
receipt=dict(schema='OBSERVED_OWNED2021_FUNDING_MARK_GAP_PLAN_V1',checked_UTC=datetime.now(timezone.utc).isoformat(),
    requested_daily_sources=len(targets),available_daily_sources=len(available),additional_body_bytes=new,
    cumulative_official_archive_body_bytes=164149016+new,remaining_budget_bytes=180*2**20-164149016-new,
    date_selection='Only actual missing strict-prior marks of owned funding events; no returns selection',results=results)
(ROOT/'SUPPLEMENT_INVENTORY.json').write_text(json.dumps(receipt,indent=2)+'\n')
inventory['records']+=available;inventory['archive_count']+=len(available)
inventory['expected_compressed_bytes']+=new;inventory['expected_new_download_bytes']+=new
(ROOT/'INVENTORY.json').write_text(json.dumps(inventory,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='results'}),flush=True)
if available:acquire.download(ROOT,'Y2021')
