"""Atomic transport of unchanged NativeDailySimulator snapshots; no execution logic."""
import gzip,hashlib,io,json,os
from pathlib import Path
import numpy as np
from prefix_static_native63 import atomic,encoded,read,record,require,sha


def save(root,sim,binding,elapsed):
    root.mkdir(parents=True,exist_ok=True);pointer_path=root/'CHECKPOINT.json';old=read(pointer_path) if pointer_path.exists() else None
    require(sim.rows_written%1440==0 and sim.stop is None,'Only complete successful daily boundaries are recoverable')
    days=sim.rows_written//1440;require((old is None and days==0) or (old['binding']==binding and old['completed_days']+1==days),'Monotone original-account daily checkpoint required')
    chunks=[] if old is None else old['minute_chunks'].copy()
    if days:
        buffer=io.BytesIO();np.save(buffer,sim.minute_chunks[-1],allow_pickle=False);name=f'minute/DAY_{days:03d}.npy';raw=buffer.getvalue();atomic(root/name,raw)
        chunks.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    snapshot=sim.snapshot();snapshot.pop('minute_chunks');name=f'state/DAY_{days:03d}.json.gz';atomic(root/name,gzip.compress(encoded(snapshot),compresslevel=1,mtime=0))
    pointer=dict(schema='ORIGINAL_NATIVE_DAILY_RECOVERY_V1',binding=binding,completed_days=days,completed_minutes=sim.rows_written,elapsed_seconds=elapsed,state_hash=sim.state_hash(),snapshot=dict(path=name,**record(root/name)),minute_chunks=chunks)
    atomic(pointer_path,encoded(pointer));return pointer


def restore(root,binding,window):
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    from prefix_static_native63 import base
    pointer=read(root/'CHECKPOINT.json');require(pointer['schema']=='ORIGINAL_NATIVE_DAILY_RECOVERY_V1' and pointer['binding']==binding,'Exact account/source/request/plan checkpoint binding required')
    require(pointer['completed_minutes']==pointer['completed_days']*1440 and len(pointer['minute_chunks'])==pointer['completed_days'] and 0<=pointer['completed_days']<=63,'Daily recovery count differs')
    entry=pointer['snapshot'];p=base.member(root,entry['path']);require(record(p)=={k:entry[k] for k in ('bytes','sha256')},'Durable financial snapshot bytes differ');snapshot=json.loads(gzip.decompress(p.read_bytes()));chunks=[]
    for i,entry in enumerate(pointer['minute_chunks'],1):
        require(entry['path']==f'minute/DAY_{i:03d}.npy','Exact ordered completed minute chunks required');p=base.member(root,entry['path']);require(record(p)=={k:entry[k] for k in ('bytes','sha256')},'Durable minute bytes differ')
        a=np.load(p,allow_pickle=False);require(a.dtype==np.float64 and a.shape==(1440,36) and np.isfinite(a).all(),'Original native36-column minute chunk required');chunks.append(a)
    require(snapshot['state']['rows_written']==pointer['completed_minutes'] and snapshot['state']['cursor']==window['start']+pointer['completed_minutes']*60000000 and snapshot['persist_cash_close'] and snapshot['final_day_target_zero'],'Original complete-boundary recovery scheduler differs')
    snapshot['minute_chunks']=[a.tolist() for a in chunks];sim=NativeDailySimulator.from_snapshot(snapshot,window,account_class=BybitIsolatedAccount)
    require(sim.state_hash()==pointer['state_hash'] and sim.account.snapshot()==snapshot['account'],'Original full account live state/journal restoration differs')
    require(all(np.array_equal(a,b) for a,b in zip(chunks,sim.minute_chunks,strict=True)),'Original numeric minute journal restoration differs')
    return sim,pointer
