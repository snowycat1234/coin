"""Five-row source trace of zero liquidity; not a full archive QA rerun."""
import csv,hashlib,json,os,zipfile
from pathlib import Path
import polars as pl
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
manifest=json.loads((ROOT/'reports/fast_research/PERPETUAL_303D_INPUT_BINDING_20261003_V1.json').read_bytes())
item=manifest['source_files']['trade:1m:BTCUSDT:2024-10'];receiptpath=Path(item['receipt_path'])
assert sha(receiptpath)==item['receipt_sha256'];receipt=json.loads(receiptpath.read_bytes())
raw=Path(receipt['zip_path']);norm=Path(item['normalized_path'])
assert raw.is_relative_to(STATE) and norm.is_relative_to(STATE) and not raw.is_symlink() and not norm.is_symlink()
assert sha(raw)==receipt['zip_sha256']==item['entry']['checksum']['announced_zip_sha256']
assert sha(norm)==item['normalized_sha256']
starts=[1730145600000000+i*60000000 for i in range(5)]
found=[]
with zipfile.ZipFile(raw) as archive:
    assert len(archive.namelist())==1
    with archive.open(archive.namelist()[0]) as source:
        import io
        rows=csv.reader(io.TextIOWrapper(source));header=next(rows)
        for row in rows:
            t=int(row[0])*1000
            if t in starts:found.append(dict(open_us=t,raw_fields=row))
            if t>starts[-1]:break
assert [r['open_us'] for r in found]==starts
frame=pl.scan_parquet(norm).filter(pl.col('open_us').is_in(starts)).select('open_us','open','close','volume','quote_volume','trade_count').collect().sort('open_us')
normalized=frame.to_dicts();assert len(normalized)==5
for a,b in zip(found,normalized,strict=True):
    assert a['open_us']==b['open_us'] and float(a['raw_fields'][5])==b['volume']==0
    assert float(a['raw_fields'][7])==b['quote_volume']==0 and int(a['raw_fields'][8])==b['trade_count']==0
result=dict(status='PASS_D060_FIVE_ZERO_LIQUIDITY_ROWS_RAW_NORMALIZED_SOURCE_TRACE_NOT_FULL_QA',
    task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(Path(__file__)),official_url=item['entry']['url'],
    raw_zip_sha256=sha(raw),normalized_sha256=sha(norm),observed_raw_header=header,raw_rows=found,normalized_rows=normalized,
    source_rows_traced=5,new_downloads=0,old_full_QA_replayed=False,accounts_replayed=0,
    conclusion='All five prior-minute zero quote/base volume and zero trade count are present in the checksummed official archive; not parser-induced.',
    native_venue_liquidity_or_cause_certified=False,locked_consumed=False)
out=ROOT/'reports/fast_research/TURTLE_NO_ADD_ZERO_LIQUIDITY_RAW_TRACE_20261004_V1.json'
with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(status=result['status'],rows=5,raw_archive_sha256=result['raw_zip_sha256'])),flush=True)
