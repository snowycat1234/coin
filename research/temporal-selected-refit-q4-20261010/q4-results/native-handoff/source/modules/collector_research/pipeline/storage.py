from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
from .common import E, disk_guard


def suffix() -> str:
    fmt = E('TABLE_FORMAT')
    if fmt not in ('parquet', 'csv.gz'):
        raise ValueError('TABLE_FORMAT must be parquet or csv.gz')
    return '.parquet' if fmt == 'parquet' else '.csv.gz'


def write_table(frame: pd.DataFrame, base: Path) -> Path:
    path = Path(str(base) + suffix())
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.' + path.name + '.part')
    disk_guard(int(frame.memory_usage(deep=True).sum()), scan=False)
    try:
        if suffix() == '.parquet':
            frame.to_parquet(tmp, engine='pyarrow', compression='zstd', index=False)
        else:
            frame.to_csv(tmp, index=False, compression={'method': 'gzip', 'mtime': 0})
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return path


def read_table(path: Path) -> pd.DataFrame:
    d = pd.read_parquet(path, engine='pyarrow') if str(path).endswith('.parquet') else pd.read_csv(path)
    for c in ('dt', 'decision_available_at', 'label_end_at'):
        if c in d:
            d[c] = pd.to_datetime(d[c], utc=True)
    for c in d.columns:
        if c.startswith('complete_') or c in ('feature_ready', 'label_ready', 'funding_interval_complete'):
            if not pd.api.types.is_bool_dtype(d[c]):
                d[c] = d[c].map({True: True, False: False, 'True': True, 'False': False}).fillna(False).astype(bool)
    return d
