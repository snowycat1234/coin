"""Select an explicit window from already accepted public Spot receipts.

Reuses historical QA, verifies current selected file bytes and Parquet footer.
No lock-body, archive download, price row, or private file discovery is needed.
"""
import argparse, calendar, hashlib, json, os, resource, time
from datetime import UTC, date, datetime
from pathlib import Path
import polars as pl
from quant.paths import ROOT, STATE
from quant import disk
from scripts.task_progress_api import Progress

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def read(r):
    p=Path(r['path']).resolve();assert p.is_relative_to(ROOT/'reports') or p.is_relative_to(ROOT/'protocols')
    assert p.stat().st_size<4_000_000 and sha(p)==r['sha256']
    return json.loads(p.read_bytes())

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--output',required=True)
    a=ap.parse_args();began=time.monotonic();c=json.loads(Path(a.config).read_bytes())
    ledger=disk.check(1_000_000);ledger['measured_utc']=datetime.now(UTC).isoformat()
    symbols=c['symbols'];assert symbols and len(set(symbols))==len(symbols)
    lo,hi=c['source_start_month'],c['source_end_month'];months=[]
    y,m=map(int,lo.split('-'))
    while f'{y:04}-{m:02}'<=hi:
        months.append(f'{y:04}-{m:02}');y,m=(y+1,1) if m==12 else (y,m+1)
    assert 0<len(months)<=36 and hi<'2026-03', 'Only explicitly authorized historical development window'
    assert sha(ROOT/'state/dataset_lock.json')==c['private_SHA_only']
    inputs={};catalog={};duplicates=[]
    for r in c['accepted_source_receipts']:
        v=read(r);assert v['status']==r['expected_status'];inputs[r['path']]=r['sha256']
        for row in v['sources']:
            k=row['symbol'],row['month']
            if k[0] not in symbols or k[1] not in months:continue
            if k in catalog:
                assert catalog[k]['normalized_sha256']==row['normalized_sha256']
                duplicates.append(dict(symbol=k[0],month=k[1],same_SHA=True))
            catalog[k]=row
    expected={(s,m) for s in symbols for m in months};assert set(catalog)==expected
    uses=[]
    for r in c['prior_use_protocols']:
        v=read(r);uses.append(dict(reference=r,role=v.get('classification',v.get('data_role','UNKNOWN')),
            research_dates=v.get('folds',dict(start=v.get('period_start'),end_exclusive=v.get('period_end_exclusive')))))
    progress=Progress();rows=[]
    try:
        for i,k in enumerate((s,m) for s in symbols for m in months):
            r=catalog[k];q=r['old_quality'];p=ROOT/'data/normalized/spot'/k[0]/'1m'/(k[1]+'.parquet')
            assert str(p)==r['normalized_path'] and not p.is_symlink() and p.resolve()==p
            count=calendar.monthrange(*map(int,k[1].split('-')))[1]*1440
            assert r['rows']==q['rows']==q['expected_rows']==count
            assert all(q[n]==0 for n in ('missing_rows','duplicate_rows','bad_timestamps','bad_values','gaps','quarantined_rows'))
            assert not q['incomplete_days'] and not q['quarantined_days'] and not q['nonstandard_closes']
            size=p.stat().st_size
            if 'normalized_bytes' in q:assert size==q['normalized_bytes']
            assert sha(p)==r['normalized_sha256']
            assert pl.scan_parquet(p).select(pl.len()).collect().item()==count
            schema=pl.read_parquet_schema(p)
            assert all(schema[n]==pl.Int64 for n in ('open_us','close_us','available_us'))
            rows.append(dict(symbol=k[0],month=k[1],normalized_path=str(p),normalized_sha256=r['normalized_sha256'],
                rows=count,old_quality=dict(normalized_bytes=size),size_scope='CURRENT_BYTES_VERIFIED_BY_ACCEPTED_SHA_NOT_OLD_QA_SIZE',
                source_QA='REUSED_ACCEPTED_EXACT_SOURCE_IDENTITY'))
            progress.update('已接受月源当前字节与元数据',i+1,len(expected),'文件')
    finally:
        progress.stop.set();progress.thread.join(timeout=3)
    out=Path(a.output).resolve();assert out.is_relative_to(ROOT/'reports') or out.is_relative_to(STATE)
    with out.open('x') as f:json.dump(dict(status='PASS_ACCEPTED_SPOT_SOURCE_WINDOW_REUSED_QA_CURRENT_BYTES',
        task_id=os.environ['COIN_TASK_ID'],sources=rows,accepted_receipt_hashes=inputs,prior_use_evidence=uses,
        duplicate_catalog_identities_verified=duplicates,data_role='SEEN_DEVELOPMENT_CHRONOLOGY_NOT_UNSEEN',
        source_start_month=lo,source_end_month=hi,symbols=symbols,private_SHA_only=c['private_SHA_only'],
        private_body_read=False,price_rows_read=False,new_downloads=0,API_calls=0,model_fits=0,
        prior_registry_sha256=c['prior_registry_sha256'],registry_scope='Identity snapshot, not proof of complete historical selection coverage',
        elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        disk_before=ledger,source_sha256=sha(__file__),config_sha256=sha(a.config),created_utc=datetime.now(UTC).isoformat()),f,indent=2)
    print(json.dumps(dict(status='PASS_ACCEPTED_SPOT_SOURCE_WINDOW_REUSED_QA_CURRENT_BYTES',files=len(rows),prior_use='SEEN')))

if __name__=='__main__':main()
