"""Bind actual native-wallet market bytes to the registered source manifest."""
import hashlib,json
from datetime import datetime,UTC
from pathlib import Path
from modules.transformer_v2.train import atomic,sha

def digest_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):digest.update(block)
    return digest.hexdigest()

def fingerprint(path):
    s=Path(path).stat()
    return s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns

def verify_records(records):
    for r in records:
        path=Path(r['path']);exists=path.is_file()
        if exists!=r['exists']:raise ValueError('Admitted market file availability changed: '+str(path))
        if not exists:continue
        # A same-size overwrite can retain coarse filesystem timestamps. Never
        # promote a metadata cache hit into proof of unchanged economic inputs.
        stat=fingerprint(path)
        if digest_file(path)!=r['sha256']:raise ValueError('Admitted native-wallet source changed: '+str(path))
        if fingerprint(path)!=stat:raise ValueError('Source changed during verification')

def market_paths(work,window,symbols):
    work=Path(work);paths=[];months=set()
    for day in range(window['start'],window['end'],86_400_000_000):months.add(datetime.fromtimestamp(day/1e6,UTC).strftime('%Y-%m'))
    for s in symbols:
        paths.extend(work/'data/normalized'/(s+suffix) for suffix in ('_daily.parquet','_funding_events.parquet'))
        for month in sorted(months):
            paths.extend(work/'data/normalized/minute'/s/family/(month+'.parquet') for family in ('klines','markPriceKlines'))
    return paths

def prepare_binding(state,window,symbols,work,manifest_path=None,expected_manifest_sha256=None):
    state=Path(state);work=Path(work).resolve();source=Path(manifest_path) if manifest_path else work/'reports/DATASET_MANIFEST.json'
    if expected_manifest_sha256 and sha(source)!=expected_manifest_sha256:raise ValueError('Registered market manifest changed')
    manifest=json.loads(source.read_text());registered={}
    for e in manifest['artifacts']:
        p=Path(e['path']) if 'path' in e else work/e['relative_path'];registered[str(p.absolute())]=e['sha256']
    records=[]
    for p in market_paths(work,window,symbols):
        present=p.is_file();expected=registered.get(str(p.absolute()))
        if present and expected is None:raise ValueError('Native input absent from source manifest: '+str(p))
        if p.name.endswith(('_daily.parquet','_funding_events.parquet')) and not present:raise ValueError('Required causal daily/funding source missing')
        records.append(dict(path=str(p),exists=present,sha256=expected if present else None))
    verify_records(records)
    value=dict(window=window,symbols=symbols,work=str(work),source_manifest_path=str(source),source_manifest_sha256=sha(source),
        files=records,source_sha256=sha(__file__),missing_source_files_remain_explicit=True)
    path=state/'market-input-bindings'/(window['id']+'.json')
    if path.exists():
        if json.loads(path.read_text())!=value:raise ValueError('Immutable native market input binding changed')
    else:atomic(path,value)
    return path

def verify_binding(path,expected_sha256):
    if sha(path)!=expected_sha256:raise ValueError('Native input binding changed')
    value=json.loads(Path(path).read_text())
    if sha(value['source_manifest_path'])!=value['source_manifest_sha256']:raise ValueError('Source manifest changed after native input freeze')
    verify_records(value['files']);return value
