"""One official daily archive check, using the unchanged public-data utility."""
import csv,io,json,os,zipfile
from pathlib import Path
import httpx
from quant.paths import ROOT,STATE
from scripts.investment.cta_cycle_source import sha,save
from scripts.investment.official_carry_chronology_source import metadata_inspector
from scripts.investment.perpetual_trade_source import file_deadline
from scripts.research_v8.funding_price_source_v2 import official_module

run=STATE/'d099-official-daily-mark-probe-20261006-v1';assert not run.exists();run.mkdir()
url='https://data.binance.vision/data/futures/um/daily/markPriceKlines/BTCUSDT/1m/BTCUSDT-1m-2022-07-31.zip'
entry=dict(market='futures/um',partition='daily',kind='markPriceKlines',symbol='BTCUSDT',interval='1m',day='2022-07-31',url=url,checksum_url=url+'.CHECKSUM')
r=dict(status='DAILY_MARK_SOURCE_UNAVAILABLE_NOT_IMPUTED',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),entry=entry,
    missing_imputed=False,new_accounts=0,economics='NOT_RUN')
try:
    with httpx.Client(timeout=12,follow_redirects=False) as client:r['metadata']=metadata_inspector(client)(entry)
    e=r['metadata'];save(run/'METADATA.json',e)
    if e['metadata_object_available']:
        assert 0<e['announced_zip_bytes']<2000000
        component=json.loads((ROOT/'reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V2.json').read_bytes())
        module=official_module(component);base=url.removeprefix(module.BASE_URL);prefix,name=base.rsplit('/',1);prefix+='/'
        with file_deadline():
            module.download_file(prefix,name,folder=str(run));module.download_file(prefix,name+'.CHECKSUM',folder=str(run))
        archive=run/base;checksum=run/(base+'.CHECKSUM');fields=checksum.read_text().split()
        assert archive.stat().st_size==e['announced_zip_bytes'] and sha(archive)==e['checksum']['announced_zip_sha256']==fields[0] and fields[1]==name
        with zipfile.ZipFile(archive) as zipped:
            assert len(zipped.infolist())==1 and zipped.infolist()[0].file_size<1000000
            rows=list(csv.reader(io.StringIO(zipped.read(zipped.infolist()[0]).decode('utf-8-sig'))))
        header=None
        if rows[0][0]=='open_time':header=rows.pop(0)
        times=[int(v[0]) for v in rows];assert all(len(v)==12 for v in rows)
        expected=list(range(1659225600000,1659312000000,60000))
        r.update(status='PASS_OFFICIAL_DAILY_MARK_COMPLETE_CALENDAR' if times==expected else 'OFFICIAL_DAILY_MARK_ALSO_INCOMPLETE',
            archive_path=str(archive),archive_sha256=sha(archive),checksum_path=str(checksum),checksum_sha256=sha(checksum),
            header=header,rows=len(rows),first_ms=times[0],last_ms=times[-1],calendar_complete=times==expected)
except Exception as error:r.update(error_type=type(error).__name__,error=str(error));raise
finally:save(ROOT/'reports/CTA_CYCLE_DAILY_MARK_PROBE_20261006_V1.json',r)
print(json.dumps(dict(status=r['status'],rows=r.get('rows'),calendar_complete=r.get('calendar_complete'))))
