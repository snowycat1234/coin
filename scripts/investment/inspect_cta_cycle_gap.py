"""Read-only calendar gap diagnosis and one official public mark query."""
import argparse,csv,io,json,os,zipfile
from datetime import UTC,datetime,timedelta
from pathlib import Path
import httpx
from quant.paths import ROOT,STATE
from scripts.investment.cta_cycle_source import sha,save

ap=argparse.ArgumentParser();ap.add_argument('--source',default='reports/fast_research/CTA_CYCLE_FULL2022_2023_SOURCE_20261006_V1.json')
ap.add_argument('--output',default='reports/CTA_CYCLE_MARK_GAP_DIAGNOSIS_20261006_V1.json')
ap.add_argument('--run-name',default='d099-cycle-gap-inspection-20261006-v1');ap.add_argument('--probe-public',action='store_true');a=ap.parse_args()
report=ROOT/a.source
r=json.loads(report.read_bytes());assert r['status']=='FAILED_CYCLE_SOURCE'
e=r['objects'][len(r['sources'])];assert e['kind']=='markPriceKlines' and e['symbol'] in ('BTCUSDT','ETHUSDT')
job=Path(r['run_dir'])/f"markPriceKlines-{e['symbol']}-1m-{e['month']}"
archives=[p for p in job.rglob('*.zip') if p.name==f"{e['symbol']}-1m-{e['month']}.zip"];assert len(archives)==1
archive=archives[0];assert sha(archive)==e['checksum']['announced_zip_sha256'] and archive.stat().st_size==e['announced_zip_bytes']
with zipfile.ZipFile(archive) as z:
    members=z.infolist();assert len(members)==1 and members[0].file_size<128000000
    rows=list(csv.reader(io.StringIO(z.read(members[0]).decode('utf-8-sig'))))
assert all(len(v)==12 for v in rows)
header=None
if rows[0][0]=='open_time':
    header=rows.pop(0);assert header==r['protocol']['format_rules']['price_header']
times=[int(v[0]) for v in rows];first=datetime.fromisoformat(e['month']+'-01').replace(tzinfo=UTC)
start=int(first.timestamp()*1000);end=int((first+timedelta(days=32)).replace(day=1).timestamp()*1000)
expected=set(range(start,end,60000));observed=set(times);missing=sorted(expected-observed)
assert len(missing)<10000 and observed<=expected and len(times)==len(observed)
ranges=[]
for t in missing:
    if ranges and ranges[-1][1]==t:ranges[-1][1]=t+60000
    else:ranges.append([t,t+60000])
run=STATE/a.run_name;assert run.parent==STATE and not run.exists();run.mkdir()
out=dict(status='PASS_READ_ONLY_OFFICIAL_MARK_GAP_DIAGNOSIS',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
    source_report_sha256=sha(report),entry=e,archive_path=str(archive),archive_sha256=sha(archive),
    expected_minutes=len(expected),actual_rows=len(times),observed_header=header,missing_minutes=len(missing),
    missing_ranges=[dict(start_ms=a,end_ms_exclusive=b,start_utc=datetime.fromtimestamp(a/1000,UTC).isoformat(),end_utc=datetime.fromtimestamp(b/1000,UTC).isoformat()) for a,b in ranges],
    missing_imputed=False,economics='NOT_RUN')
out['downloaded_daily_gaps']=[]
for daily in job.rglob('*.zip'):
    if daily==archive:continue
    with zipfile.ZipFile(daily) as z:
        raw=list(csv.reader(io.StringIO(z.read(z.infolist()[0]).decode('utf-8-sig'))))
    if raw[0][0]=='open_time':raw.pop(0)
    clock=[int(v[0]) for v in raw];opened=min(clock)//86400000*86400000
    fields=Path(str(daily)+'.CHECKSUM').read_text().split();assert fields[0]==sha(daily)
    holes=sorted(set(range(opened,opened+86400000,60000))-set(clock))
    out['downloaded_daily_gaps'].append(dict(path=str(daily),sha256=sha(daily),rows=len(raw),missing_minutes=len(holes),
        missing_start_ms=holes[0] if holes else None,missing_end_ms_exclusive=holes[-1]+60000 if holes else None))
if missing and a.probe_public:
    params=dict(symbol=e['symbol'],interval='1m',startTime=missing[0],endTime=missing[0]+59999,limit=1)
    out['official_public_probe']=dict(url='https://fapi.binance.com/fapi/v1/markPriceKlines',parameters=params,keys_used=False)
    try:
        with httpx.Client(timeout=12,follow_redirects=False) as client:
            response=client.get(out['official_public_probe']['url'],params=params)
            assert len(response.content)<=100000
            body=run/'official_public_response.bin';body.write_bytes(response.content)
            out['official_public_probe'].update(http_status=response.status_code,body_path=str(body),body_sha256=sha(body),body_bytes=len(response.content))
            if response.status_code==200:out['official_public_probe']['json']=response.json()
    except Exception as error:out['official_public_probe'].update(error_type=type(error).__name__,error=str(error))
save(ROOT/a.output,out)
print(json.dumps(dict(status=out['status'],missing_minutes=len(missing),ranges=out['missing_ranges'],probe=out.get('official_public_probe'))))
