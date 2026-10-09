"""Recover published original minute bytes and normalize them offline unchanged."""
import argparse,concurrent.futures,hashlib,json,os,resource,shutil,socket,sys,urllib.request,zipfile
from pathlib import Path
import evaluate_requests63 as native
base=native.base
PUBLIC_DATA={
 'FOLD_20230703':dict(folder='JULY2023',commit='88d6ff788dad5ce68efee1a200605f506c067339',INDEX_SHA256='b8e53d761dd0db3bd506de626fdbabce86cf8dd19398ed22c6f5db1ba41d589e'),
 'FOLD_20231002':dict(folder='OCTOBER2023',commit='03ab52320a3271caabb67caab4a395ad2f922653',INDEX_SHA256='175091eaad7f25173ad59715e484dc040eab6522dc3d1af8710c597f4aba6c68')}


def recover(state,fold):
    r=PUBLIC_DATA[fold];root=state/'prequential2023-data'/r['folder'];root.mkdir(parents=True,exist_ok=True);prefix='research/core5-binance-native-2023-data/'+r['folder']
    def download(name,size=None):
        p=base.member(root,name)
        if not p.exists():
            raw=urllib.request.urlopen(f'https://raw.githubusercontent.com/snowycat1234/coin/{r["commit"]}/{prefix}/{name}',timeout=30).read((size+1) if size else 262145);p.write_bytes(raw)
        return p
    index=download('INDEX.json');base.frozen.require(base.frozen.sha(index)==r['INDEX_SHA256'],'Exact public minute INDEX differs');m=base.frozen.read(index)
    def part(v):
        p=download(v['name'],v['bytes']);base.frozen.require(p.stat().st_size==v['bytes'] and base.frozen.sha(p)==v['SHA256'],'Public minute byte part differs');return p
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:paths=list(ex.map(part,m['parts']))
    archive=root/'originals.zip'
    if not archive.exists():
        with archive.open('xb') as out:
            for p in paths:out.write(p.read_bytes())
    base.frozen.require(archive.stat().st_size==m['package_bytes'] and base.frozen.sha(archive)==m['package_SHA256'],'Original minute package differs');original=root/'original';original.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        base.frozen.require(sorted(z.namelist())==sorted(v['name'] for v in m['members']) and z.testzip() is None,'Original minute ZIP members/CRC differ')
        for v in m['members']:
            p=base.member(original,v['name']);raw=z.read(v['name']);base.frozen.require(len(raw)==v['bytes'] and hashlib.sha256(raw).hexdigest()==v['SHA256'],'Original member differs');p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():base.frozen.require(p.read_bytes()==raw,'Never overwrite original recovery bytes')
            else:p.write_bytes(raw)
    for p in original.rglob('*.zip'):base.frozen.require(base.frozen.sha(p)==p.with_name(p.name+'.CHECKSUM').read_text().split()[0],'Actual official archive checksum differs')
    return root,m


def normalize(state,fold):
    import numpy as np,pandas as pd
    r=PUBLIC_DATA[fold];root=state/'prequential2023-data'/r['folder'];m=base.frozen.read(root/'INDEX.json');original=root/'original';work=root/'h1_market';require=base.frozen.require
    config=root/'offline-normalizer.env';config.write_text('TABLE_FORMAT=parquet\nMIN_FREE_GIB=15\nMAX_WORK_GIB=4\n')
    os.environ.update(CONFIG_FILE=str(config),WORK_DIR=str(work),RAW_CACHE_DIR=str(original/'raw'),TABLE_FORMAT='parquet')
    def blocked(*a,**kw):raise RuntimeError('Offline minute normalization forbids provider/network requests')
    socket.create_connection=blocked;socket.socket.connect=blocked
    sys.path.insert(0,str(base.frozen.REPO))
    from modules.collector_research.pipeline import normalize as n
    for name,sha in m['normalization_source_SHA256'].items():require(base.frozen.sha(base.frozen.REPO/'modules/collector_research/pipeline'/name)==sha,'Exact normalizer source differs')
    published=base.frozen.read(original/'VALIDATION.json');records=[]
    for v in published['monthly_receipts']:
        raw=original/'raw'/v['family']/v['symbol']/(v['symbol']+'-1m-'+v['month']+'.zip');require(base.frozen.sha(raw)==v['original_SHA256'],'Original raw monthly bytes differ');year,month=map(int,v['month'].split('-'));left,right=n.month_limits(year,month);frame,duplicates=n.validate_price(n.numeric_csv(raw),v['family'],left,right);table=n.canonical(frame,v['family'],v['symbol'])
        require(duplicates==0 and len(table)==v['rows'] and np.array_equal(table.timestamp_ms.to_numpy(),np.arange(left,right,60000,dtype=np.int64)),'Actual complete monthly minute grid required')
        if v['family']=='klines':require(hashlib.sha256(table.quote_volume.to_numpy(dtype=np.float64).tobytes()).hexdigest()==v['quote_volume_float64_SHA256'],'Raw quote-USDT capacity values changed')
        path=work/v['normalized_relative_path'];path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            require(shutil.disk_usage(root).free>15*2**30,'15GiB reserve required');candidate=path.with_suffix('.candidate.parquet');table.to_parquet(candidate,engine='pyarrow',compression='zstd',index=False);require(pd.read_parquet(candidate).equals(table),'Canonical numeric Parquet roundtrip differs');candidate.replace(path)
        require(pd.read_parquet(path).equals(table),'Existing normalized values differ; no replacement')
        records.append(dict(relative_path=path.relative_to(work).as_posix(),bytes=path.stat().st_size,sha256=base.frozen.sha(path),original_SHA256=v['original_SHA256'],published_normalized_SHA256=v['normalized_SHA256'],normalized_bytes_identical_to_published_receipt=base.frozen.sha(path)==v['normalized_SHA256'],quote_volume_float64_SHA256=v.get('quote_volume_float64_SHA256'),rows=len(table)))
    retained=state/'h1_validation/original/h1_market/data/normalized'
    for symbol in base.frozen.SYMBOLS:
        for suffix in ('_daily.parquet','_funding_events.parquet'):
            src=retained/(symbol+suffix);dst=work/'data/normalized'/src.name
            if dst.is_symlink():require(dst.resolve()==src.resolve(),'Unexpected existing context symlink');dst.unlink()
            if not dst.exists():os.link(src,dst)
            require(dst.samefile(src) and base.frozen.sha(dst)==base.frozen.sha(src),'Actual retained daily/funding source must remain unchanged');records.append(dict(relative_path=dst.relative_to(work).as_posix(),bytes=src.stat().st_size,sha256=base.frozen.sha(src),role='REUSED_ORIGINAL_DAILY_HISTORY_AND_FUNDING_NOT_DOWNLOADED'))
    report=dict(status='PASS_PUBLIC_ORIGINALS_EXACT_NORMALIZER_VALUES_AND_REUSED_CONTEXT_BYTES',fold=fold,public=PUBLIC_DATA[fold],original_package_SHA256=m['package_SHA256'],raw_manifest_SHA256=base.frozen.sha(original/'RAW_MANIFEST.json'),original_validation_SHA256=base.frozen.sha(original/'VALIDATION.json'),normalization_source_commit=m['normalization_source_commit'],normalization_source_SHA256=m['normalization_source_SHA256'],artifacts=records,source_provenance='ORIGINAL_RAW_MANIFEST_RETAINED_UNCHANGED;ORIGINAL_PROVIDER_RETRIEVAL_TIMESTAMP_NOT_SUPPLIED_BY_PUBLISHED_MANIFEST',provider_downloads=0,fits=0,wallets_run=0,no_synthetic_rows=True,no_fill_forward=True)
    (root/'NORMALIZED_RECOVERY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],fold=fold,normalized_tables=30,reused_daily_funding=10,byte_identical_parquet_receipts=sum(v.get('normalized_bytes_identical_to_published_receipt',False) for v in records))),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('recover','normalize'));p.add_argument('--state',type=Path,required=True);p.add_argument('--fold',choices=tuple(PUBLIC_DATA),required=True);a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','POLARS_MAX_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    if a.command=='recover':recover(a.state,a.fold)
    else:normalize(a.state,a.fold)
