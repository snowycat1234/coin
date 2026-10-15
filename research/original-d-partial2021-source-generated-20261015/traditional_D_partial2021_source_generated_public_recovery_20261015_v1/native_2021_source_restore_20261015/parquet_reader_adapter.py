"""Projection-only replacement for unavailable pyarrow.parquet.read_table.

Uses installed polars for exact named Parquet columns; does not install software,
change numeric source values, or import strategy/account modules.
"""
from pathlib import Path
import io
import os,hashlib,json
import numpy as np
import pandas as pd
import polars as pl

class ProjectedTable:
    def __init__(self, frame): self.frame=frame
    def to_pandas(self):
        return pd.DataFrame({name:self.frame[name].to_numpy() for name in self.frame.columns})

def read_table(source, columns):
    assert isinstance(columns,list) and columns
    assert set(columns)<=set(('dt','open','high','low','close','complete_kline','calc_time_ms','last_funding_rate','funding_interval_hours'))
    # Predicate and projection are applied in the Parquet scan, before a table
    # is collected or converted to pandas. Never materialize later-year rows.
    frame=pl.scan_parquet(source).select(columns)
    if 'calc_time_ms' in columns:
        frame=frame.filter((pl.col('calc_time_ms')>=1609459200000)&(pl.col('calc_time_ms')<1640995200000))
        predicate=dict(field='calc_time_ms',minimum_inclusive=1609459200000,maximum_exclusive=1640995200000,unit='ms')
    elif 'dt' in columns:
        frame=frame.filter(pl.col('dt').dt.epoch('us')<1640995200000000)
        predicate=dict(field='dt',maximum_exclusive=1640995200000000,unit='us',saved_pre2021_daily_history_preserved=True)
    else:
        raise AssertionError('A dated source projection is required')
    frame=frame.collect(engine='streaming')
    assert frame.columns==columns
    log=os.environ.get('COIN_SOURCE_READER_LEDGER_PATH')
    if log:
        body=source.getvalue() if hasattr(source,'getvalue') else Path(source).read_bytes()
        record=dict(source_SHA256=hashlib.sha256(body).hexdigest(),source_bytes=len(body),selected_columns=columns,predicate_applied_before_materialization=predicate,selected_rows=frame.height,prior_mark_fields_selected=False,numeric_values_recomputed=False)
        with open(log,'a') as out:out.write(json.dumps(record,sort_keys=True)+'\n')
    return ProjectedTable(frame)
