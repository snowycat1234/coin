"""One immutable observed-mark storage reference per complete scoring window."""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import polars as pl
from modules.transformer_v2.train import atomic,sha

def prepare_reference(state,window,symbols,collector_root,work,source_run):
    state=Path(state);folder=state/'common-mark-references';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(window['id']+'.parquet');receipt=path.with_suffix('.json')
    binding=dict(window=window,symbols=symbols,work=str(Path(work).resolve()),source_sha256=sha(__file__))
    if receipt.exists():
        old=json.loads(receipt.read_text())
        if old['binding']!=binding or sha(path)!=old['reference_sha256']:raise ValueError('Protected common observed-mark reference changed')
        return path
    from modules.collector_research.validation import runtime
    runtime.configure(SimpleNamespace(collector_root=collector_root,collector_work=work,source_run=source_run,run_dir=state/'reference-control',
                      resource_policy='server',workers=1,minimum_days=30,publish_source_report=False,audit_device='cpu'))
    from modules.collector_research.validation import data
    if data.WORK!=Path(work).resolve():raise ValueError('Use a fresh process for a different market work directory')
    inputs=data.market_window(symbols,window['start'],window['end']);pieces=[]
    for block in inputs['minute_blocks']():
        if not set(window['active_symbols'])<=set(block['market']):raise ValueError('Expected active observed mark missing')
        records=dict(close_us=block['times']+60_000_000)
        for s in symbols:records[s]=block['market'][s]['mark'] if s in block['market'] else np.full(len(block['times']),np.nan)
        pieces.append(pl.DataFrame(records))
    frame=pl.concat(pieces)
    if not np.array_equal(frame['close_us'].to_numpy(),np.arange(window['start']+60_000_000,window['end']+1,60_000_000)):raise ValueError('Complete observed reference clock changed')
    temp=path.with_suffix('.tmp.parquet');frame.write_parquet(temp,compression='zstd',compression_level=9);temp.replace(path)
    atomic(receipt,dict(binding=binding,reference_sha256=sha(path),rows=frame.height,
                       role='LOSSLESS_COMMON_OBSERVED_MARK_STORAGE_REFERENCE; ABSENT_QUOTES_RETAIN_NAN; NOT_ACCOUNT_RETURNS',
                       no_labels=True,no_fits=True,protected_old_files_modified=False))
    return path
