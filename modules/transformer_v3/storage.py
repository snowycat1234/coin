"""Lossless new-wallet storage; protected old files are never rewritten.

Float Parquet uses BYTE_STREAM_SPLIT + ZSTD, with bit-for-bit floating value
checks before replacing a newly generated file. JSON retains its exact bytes
under gzip. Hydration exposes ordinary files to the unchanged native auditor.
"""
from contextlib import contextmanager
import gzip,hashlib,json,tempfile
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import polars as pl
from modules.transformer_v2.train import atomic,sha

def same_arrow_values(before,after):
    if before.schema!=after.schema or before.num_rows!=after.num_rows:return False
    for name in before.column_names:
        a,b=before[name],after[name]
        if pa.types.is_floating(a.type):
            if not a.is_null().equals(b.is_null()):return False
            x,y=a.to_numpy(),b.to_numpy();dtype=np.uint64 if a.type.bit_width==64 else np.uint32
            if not np.array_equal(x.view(dtype),y.view(dtype)):return False
        elif not a.equals(b):return False
    return True

def compact_parquet(source,destination):
    table=pq.read_table(source)
    columns=[f.name for f in table.schema if pa.types.is_floating(f.type)]
    pq.write_table(table,destination,compression='zstd',compression_level=19,use_dictionary=False,
                   use_byte_stream_split=columns,row_group_size=262144)
    if not same_arrow_values(table,pq.read_table(destination)):raise ValueError('Lossless Parquet round trip changed values or schema')

def predictor_groups(frame,reference):
    """Storage predictors only: arbitrary financial deviations remain exact XOR bits."""
    symbols=[n[:-9] for n in frame.columns if n.endswith('_quantity')]
    def array(name):return frame[name].to_numpy()
    marked={s:np.where(array(s+'_quantity')==0.,0.,array(s+'_quantity')*reference[s].to_numpy()) for s in symbols}
    yield {s+'_signed_marked_notional':v for s,v in marked.items()}
    yield {s+'_isolated_equity':np.where(array(s+'_quantity')>=0.,array(s+'_signed_marked_notional'),
           2.*array(s+'_isolated_balance')+array(s+'_signed_marked_notional')) for s in symbols}
    yield dict(nav=array('free_cash')+np.stack([array(s+'_isolated_equity') for s in symbols]).sum(0),
               isolated_balance=np.stack([array(s+'_isolated_balance') for s in symbols]).sum(0),
               gross_notional=np.abs(np.stack([array(s+'_signed_marked_notional') for s in symbols])).sum(0),
               net_signed_notional=np.stack([array(s+'_signed_marked_notional') for s in symbols]).sum(0))
    with np.errstate(divide='ignore',invalid='ignore'):
        yield dict({s+'_signed_weight':array(s+'_signed_marked_notional')/array('nav') for s in symbols},
                   gross_weight=array('gross_notional')/array('nav'),net_signed_weight=array('net_signed_notional')/array('nav'))

def xor_encode(frame,reference):
    result=frame.clone()
    for group in predictor_groups(frame,reference):
        for name,prediction in group.items():
            if frame[name].dtype!=pl.Float64:raise ValueError('XOR codec requires original Float64 fields')
            bits=frame[name].to_numpy().view('uint64')^prediction.view('uint64')
            result=result.with_columns(pl.Series(name,bits,dtype=pl.UInt64))
    return result

def xor_decode(frame,reference):
    result=frame.clone()
    # The generator reads the restored frame between groups, so dependencies
    # are restored first. No mathematical identity discards residual information.
    for group in predictor_groups(result,reference):
        for name,prediction in group.items():
            bits=result[name].to_numpy()^prediction.view('uint64')
            result.replace_column(result.get_column_index(name),pl.Series(name,bits.view('float64')))
    return result

def pack_case(saved,directory,market_reference=None):
    directory=Path(directory).resolve();proof=[]
    reference=None
    if market_reference is not None:
        market_reference=Path(market_reference).resolve();reference=pl.read_parquet(market_reference)
    for name,entry in saved['artifacts'].items():
        p=Path(entry['path'])
        if p.is_symlink() or p.resolve().parent!=directory:raise ValueError('Only newly generated owned account files may be packed')
        original_sha=sha(p);original_bytes=p.stat().st_size
        if original_sha!=entry['sha256']:raise ValueError('Generated wallet changed before packing')
        if p.suffix=='.json':
            raw=p.read_bytes();dest=p.with_suffix('.json.gz')
            if dest.exists():raise ValueError('Preserve previous packed file')
            with dest.open('wb') as f:
                with gzip.GzipFile(filename='',mode='wb',fileobj=f,compresslevel=9,mtime=0) as z:z.write(raw)
            if gzip.decompress(dest.read_bytes())!=raw:raise ValueError('Lossless JSON byte identity failed')
            p.unlink();entry.update(path=str(dest),sha256=sha(dest),bytes=dest.stat().st_size,
                                    storage_encoding='GZIP_EXACT_ORIGINAL_JSON_BYTES',uncompressed_sha256=original_sha)
        elif p.suffix=='.parquet':
            dest=p.with_name(p.stem+'.compact.parquet')
            if name=='minute_nav_inventory.parquet' and reference is not None:
                original=pl.read_parquet(p);ref=reference.head(original.height)
                if not original['close_us'].equals(ref['close_us']):raise ValueError('Lossless common mark reference calendar differs')
                encoded=xor_encode(original,ref)
                encoded.write_parquet(dest,compression='zstd',compression_level=9)
                restored=xor_decode(pl.read_parquet(dest),ref)
                if not same_arrow_values(original.to_arrow(),restored.to_arrow()):raise ValueError('XOR lossless original IEEE float values changed')
                entry['xor_market_reference']=dict(path=str(market_reference),sha256=sha(market_reference),codec='FLOAT64_XOR_PREDICTOR_V1')
            else:compact_parquet(p,dest)
            if dest.stat().st_size<p.stat().st_size:dest.replace(p)
            else:
                dest.unlink();entry.pop('xor_market_reference',None)
            entry.update(sha256=sha(p),bytes=p.stat().st_size,storage_encoding='LOSSLESS_PARQUET_VALUES_SCHEMA_ORDER_PRESERVED')
            if entry.get('xor_market_reference'):entry['storage_encoding']='FLOAT64_XOR_CANONICAL_SCHEMA_RECOVERABLE_WITH_HASH_BOUND_MARK_REFERENCE'
        proof.append(dict(logical_name=name,original_sha256=original_sha,original_bytes=original_bytes,
                          packed_sha256=entry['sha256'],packed_bytes=entry['bytes'],float_precision_reduced=False,
                          xor_market_reference=entry.get('xor_market_reference')))
    path=directory/'storage_manifest.json';atomic(path,dict(version='LOSSLESS_STORAGE_V1',files=proof,pyarrow_version=pa.__version__,protected_old_files_modified=False))
    if any(r['xor_market_reference'] for r in proof):
        saved['artifacts']['common_market_reference.parquet']=dict(path=str(market_reference),sha256=sha(market_reference),bytes=market_reference.stat().st_size,
                                                                 role='SHARED_OBSERVED_MARK_STORAGE_REFERENCE_NOT_A_FINANCIAL_APPROXIMATION')
    saved['artifacts'][path.name]=dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size)
    return saved

@contextmanager
def hydrated_account(directory,scratch_parent):
    directory=Path(directory).resolve();parent=Path(scratch_parent).resolve();parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='wallet-audit-',dir=parent) as temp:
        target=Path(temp)
        manifest=json.loads((directory/'storage_manifest.json').read_text())
        proofs={r['logical_name']:r for r in manifest['files']}
        for p in directory.iterdir():
            if p.name.endswith('.json.gz'):
                name=p.name[:-3];r=proofs[name]
                if sha(p)!=r['packed_sha256']:raise ValueError('Packed JSON changed')
                raw=gzip.decompress(p.read_bytes())
                if hashlib.sha256(raw).hexdigest()!=r['original_sha256']:raise ValueError('Hydrated original JSON bytes changed')
                (target/name).write_bytes(raw)
            elif p.is_file():
                if p.name in proofs and sha(p)!=proofs[p.name]['packed_sha256']:raise ValueError('Packed Parquet changed')
                ref=proofs.get(p.name,{}).get('xor_market_reference')
                if ref:
                    if sha(ref['path'])!=ref['sha256']:raise ValueError('Common observed mark reference changed')
                    frame=pl.read_parquet(p);reference=pl.read_parquet(ref['path']).head(frame.height)
                    xor_decode(frame,reference).write_parquet(target/p.name,compression='zstd')
                else:(target/p.name).symlink_to(p)
        yield target
