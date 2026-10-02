"""Existing allowed-date Spot archive integrity and read-only live minute metadata."""
from datetime import UTC,datetime
import hashlib,json,sqlite3,zipfile
from pathlib import Path

root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for symbol in ('BTCUSDT','ETHUSDT'):
    for month in ('2025-08','2025-09','2025-10','2025-11'):
        zip_path=root/'data/raw/spot'/symbol/'1m'/f'{symbol}-1m-{month}.zip'
        check=zip_path.with_name(zip_path.name+'.CHECKSUM')
        row={'symbol':symbol,'month':month,'path':str(zip_path),'official_url':f'https://data.binance.vision/data/spot/monthly/klines/{symbol}/1m/{zip_path.name}',
             'exists':zip_path.is_file(),'checksum_exists':check.is_file(),'acceptance':'NOT_EVALUATED_EXISTING_BYTES_ONLY'}
        if zip_path.is_file() and check.is_file():
            fields=check.read_text().split();digest=sha(zip_path)
            row.update(zip_bytes=zip_path.stat().st_size,zip_sha256=digest,checksum_sha256=sha(check),
                       checksum_matches=len(fields)==2 and fields[0].lower()==digest and fields[1].lstrip('*')==zip_path.name)
            with zipfile.ZipFile(zip_path) as archive:
                row.update(members=[{'name':i.filename,'uncompressed_bytes':i.file_size} for i in archive.infolist()],crc_full_read=archive.testzip() is None)
        rows.append(row)
live={'path':str(state/'live.sqlite3'),'mode':'READ_ONLY_CALENDAR_METADATA_NO_PRICES'}
if Path(live['path']).exists():
    with sqlite3.connect('file:'+live['path']+'?mode=ro',uri=True,timeout=5) as db:
        live['closed_bars']=[{'symbol':r[0],'rows':r[1],'first_open_ms':r[2],'last_open_ms':r[3]} for r in db.execute('SELECT symbol,count(*),min(open_ms),max(open_ms) FROM closed_bars GROUP BY symbol')]
        live['historical_2025_folds_from_live_db']=False
result={'status':'EXISTING_SPOT_SOURCE_METADATA_CHECK_COMPLETE_NOT_NEW_ACCEPTANCE','created_utc':datetime.now(UTC).isoformat(),
        'allowed_start':'2025-08-01','allowed_end_exclusive':'2025-12-01','archives':rows,'live':live,
        'new_archives_downloaded':0,'locked_or_aggregate_bar_files_read':False,'price_or_model_outcomes_read':False,
        'fill_qualification':'OHLC is a price proxy; real BBO,size,latency missing. Mark/index never used as fill.',
        'source_sha256':sha(Path(__file__))}
out=root/'reports/fast_research/V8_EXISTING_SPOT_MINUTE_SOURCE_METADATA_20261002_V1.json'
with out.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(result))
