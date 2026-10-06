"""Explicit month+day compound from two checksummed official archives."""
import csv,io,json,os,zipfile
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.investment.cta_cycle_source import sha,save
from scripts.research_v8 import funding_price_source_v2 as parser
from scripts.research_v8.audit_funding_price_source import audit_one

gap_path=ROOT/'reports/CTA_CYCLE_MARK_GAP_DIAGNOSIS_20261006_V1.json'
day_path=ROOT/'reports/CTA_CYCLE_DAILY_MARK_PROBE_20261006_V1.json'
gap=json.loads(gap_path.read_bytes());daily=json.loads(day_path.read_bytes())
assert gap['missing_minutes']==1440 and daily['status']=='PASS_OFFICIAL_DAILY_MARK_COMPLETE_CALENDAR'
for report in (gap,daily):
    task=json.loads((STATE/'task-progress'/('task-'+report['task_id']+'.json')).read_bytes())
    assert task['status']=='completed' and task['exit_code']==0
parents=[];rows=[]
for path,h in [(gap['archive_path'],gap['archive_sha256']),(daily['archive_path'],daily['archive_sha256'])]:
    archive=Path(path);assert archive.is_relative_to(STATE) and sha(archive)==h
    with zipfile.ZipFile(archive) as z:
        members=z.infolist();assert len(members)==1 and members[0].file_size<128000000
        raw=list(csv.reader(io.StringIO(z.read(members[0]).decode('utf-8-sig'))))
    if raw[0][0]=='open_time':raw.pop(0)
    parents.append(dict(path=path,sha256=h,rows=len(raw)));rows.extend(raw)
assert all(len(v)==12 for v in rows) and [int(v[0]) for v in rows]==list(range(1656633600000,1659312000000,60000))
run=STATE/'d099-btc-jul2022-compound-20261006-v1';assert not run.exists();run.mkdir()
archive=run/'BTCUSDT-1m-2022-07.zip';text=io.StringIO(newline='');csv.writer(text,lineterminator='\n').writerows(rows)
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('BTCUSDT-1m-2022-07.csv',text.getvalue())
checksum=run/(archive.name+'.CHECKSUM');checksum.write_text(sha(archive)+'  '+archive.name+'\n')
protocol=json.loads((ROOT/'protocols/CTA_CYCLE_FULL2022_2023_SOURCE_20261006_V1.json').read_bytes())
entry=dict(gap['entry'],url='derived://BTCUSDT-mark-2022-07-official-month-plus-day',
    checksum=dict(announced_zip_sha256=sha(archive)),announced_zip_bytes=archive.stat().st_size,
    checksum_provenance='LOCAL_DERIVED_CHECKSUM_NOT_BINANCE_OFFICIAL',published_inputs=parents)
parquet=run/'source.parquet';stats=parser.convert_source(archive,entry,protocol['format_rules'],parquet)
receipt=dict(status='SOURCE_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA',entry=entry,zip_path=str(archive),zip_sha256=sha(archive),
    checksum_path=str(checksum),checksum_sha256=sha(checksum),uncompressed_csv_bytes=len(text.getvalue().encode()),
    parquet_path=str(parquet),parquet_sha256=sha(parquet),parquet_bytes=parquet.stat().st_size,stats=stats,
    derivation='EXACT_ORDERED_RAW_ROWS_OF_TWO_ORIGINAL_OFFICIAL_ARCHIVES_NO_INTERPOLATION',original_reports=[dict(path=str(gap_path.relative_to(ROOT)),sha256=sha(gap_path)),dict(path=str(day_path.relative_to(ROOT)),sha256=sha(day_path))])
save(run/'receipt.json',receipt);proof=audit_one(receipt,protocol['format_rules']);save(run/'INDEPENDENT_RAW_REFERENCE.json',proof)
row=dict(entry=gap['entry'],receipt_path=str(run/'receipt.json'),receipt_sha256=sha(run/'receipt.json'),independent_reference=proof,
    acquisition='EXACT_OFFICIAL_MONTH_PLUS_DAILY_ARCHIVE_COMPOUND_NOT_ORIGINAL_COMPLETE_MONTH',official_archive_parents=parents)
out=dict(status='PASS_CYCLE_OFFICIAL_RAW_REFERENCE_FORMAT_NOT_ECONOMICS',binding=dict(task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__)),
    protocol=dict(entries=[gap['entry']]),sources=[row],source_only=True,new_accounts=0,economics='NOT_RUN',missing_imputed=False,
    exact_raw_parent_rows=len(rows),original_monthly_archive_unchanged=True,original_gap_preserved=True)
save(ROOT/'reports/CTA_CYCLE_BTC_JUL2022_COMPOUND_20261006_V1.json',out)
print(json.dumps(dict(status=out['status'],rows=len(rows),derived_zip_is_not_official=True)))
