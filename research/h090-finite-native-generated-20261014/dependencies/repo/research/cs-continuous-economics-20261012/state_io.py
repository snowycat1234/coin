"""Lossless split of the real frozen scheduler snapshot; no live mutation."""
import copy,gzip,hashlib,json
from pathlib import Path
import numpy as np

def split_snapshot(sim):
    view=copy.copy(sim);view.minute_chunks=[]
    snapshot=view.snapshot()
    return snapshot

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def checkpoint(directory,sim,binding):
    directory.mkdir(parents=True,exist_ok=True);chunks=[]
    for i,array in enumerate(sim.minute_chunks):
        p=directory/f'DAY_{i:04d}.npz'
        if not p.exists():np.savez_compressed(p,minute_chunk=array)
        else:
            with np.load(p,allow_pickle=False) as z:np.testing.assert_array_equal(z['minute_chunk'],array)
        chunks.append(dict(path=p.name,SHA256=digest(p),rows=len(array),columns=array.shape[1]))
    snapshot=split_snapshot(sim);raw=json.dumps(snapshot,sort_keys=True,separators=(',',':'),allow_nan=False).encode();p=directory/f'STATE_{sim.rows_written:09d}.json.gz';encoded=gzip.compress(raw,mtime=0)
    if p.exists():assert p.read_bytes()==encoded,'Immutable same-account checkpoint'
    else:p.write_bytes(encoded)
    pointer=dict(binding=binding,state_hash=sim.state_hash(),completed_minutes=sim.rows_written,cursor=sim.cursor,stop=sim.stop,snapshot_path=p.name,snapshot_SHA256=digest(p),chunks=chunks)
    temporary=directory/'POINTER.tmp';temporary.write_text(json.dumps(pointer,sort_keys=True,indent=2)+'\n');temporary.replace(directory/'POINTER.json');return pointer

def restore_snapshot(directory,binding):
    directory=Path(directory);pointer=json.loads((directory/'POINTER.json').read_text());assert pointer['binding']==binding
    assert pointer['snapshot_path']==f"STATE_{pointer['completed_minutes']:09d}.json.gz"
    p=directory/pointer['snapshot_path'];assert digest(p)==pointer['snapshot_SHA256'];snapshot=json.loads(gzip.decompress(p.read_bytes()));chunks=[]
    for i,r in enumerate(pointer['chunks']):
        assert r['path']==f'DAY_{i:04d}.npz';p=directory/r['path'];assert digest(p)==r['SHA256']
        with np.load(p,allow_pickle=False) as z:a=z['minute_chunk']
        assert a.dtype==np.float64 and a.shape==(r['rows'],r['columns']) and np.isfinite(a).all();chunks.append(a)
    assert sum(len(a) for a in chunks)==pointer['completed_minutes'];snapshot['minute_chunks']=chunks
    return snapshot,pointer
