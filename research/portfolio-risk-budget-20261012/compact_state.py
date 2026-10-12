"""Thin storage adapter: existing NPZ column codec and genuine native snapshots."""
import gzip, hashlib, importlib.util, io, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('budget_original_state', ROOT / 'research/cs-continuous-economics-20261012/state_io.py')
original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def original_npz(array):
    f = io.BytesIO(); np.savez_compressed(f, minute_chunk=array); return f.getvalue()

def checkpoint(directory, sim, binding):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True); chunks = []
    for i, array in enumerate(sim.minute_chunks):
        assert array.dtype == np.float64 and array.ndim == 2 and array.shape[1] == 36 and np.isfinite(array).all()
        p = directory / f'DAY_{i:04d}.COLUMNS.npz'
        if p.exists():
            with np.load(p, allow_pickle=False) as z:
                np.testing.assert_array_equal(np.ascontiguousarray(z['column_chunk'].T), array)
        else:
            np.savez_compressed(p, column_chunk=np.ascontiguousarray(array.T))
        chunks.append(dict(path=p.name, SHA256=sha(p), rows=len(array), columns=36, original_NPZ_SHA256=hashlib.sha256(original_npz(array)).hexdigest()))
    snapshot = original.split_snapshot(sim)
    raw = json.dumps(snapshot, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    p = directory / f'STATE_{sim.rows_written:09d}.json.gz'; encoded = gzip.compress(raw, mtime=0)
    if p.exists():
        assert p.read_bytes() == encoded
    else:
        p.write_bytes(encoded)
    pointer = dict(binding=binding, state_hash=sim.state_hash(), completed_minutes=sim.rows_written, cursor=sim.cursor, stop=sim.stop, snapshot_path=p.name, snapshot_SHA256=sha(p), chunks=chunks, codec='EXISTING_COLUMN_COPY_NO_ARITHMETIC_ORIGINAL_NPZ_BYTES_REPRODUCIBLE')
    temporary = directory / 'POINTER.tmp'; temporary.write_text(json.dumps(pointer, sort_keys=True, indent=2)+'\n'); temporary.replace(directory/'POINTER.json')
    return pointer

def restore_snapshot(directory, binding):
    directory = Path(directory); pointer = json.loads((directory/'POINTER.json').read_text()); assert pointer['binding'] == binding
    p = directory / pointer['snapshot_path']; assert p.name == f"STATE_{pointer['completed_minutes']:09d}.json.gz" and sha(p) == pointer['snapshot_SHA256']
    snapshot = json.loads(gzip.decompress(p.read_bytes())); chunks = []
    for i, r in enumerate(pointer['chunks']):
        assert r['path'] == f'DAY_{i:04d}.COLUMNS.npz'; p = directory / r['path']; assert sha(p) == r['SHA256']
        with np.load(p, allow_pickle=False) as z:
            a = np.ascontiguousarray(z['column_chunk'].T)
        assert a.dtype == np.float64 and a.shape == (r['rows'], 36) and np.isfinite(a).all()
        assert hashlib.sha256(original_npz(a)).hexdigest() == r['original_NPZ_SHA256']
        chunks.append(a)
    assert sum(len(a) for a in chunks) == pointer['completed_minutes']; snapshot['minute_chunks'] = chunks
    return snapshot, pointer
