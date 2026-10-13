"""Actual final six CSV quotes for the frozen five terminal attempts; no fills."""
from __future__ import annotations
from collections import deque
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd
from original_functions import SYMBOLS

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SOURCE=ROOT/'coin_2021_source_closure_20261013'
MINUTE=60_000_000
END=1_640_995_200_000_000

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def final_rows(body):
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        if len(z.namelist())!=1 or z.testzip() is not None:
            raise ValueError('SOURCE_STOP: terminal original ZIP CRC/member failure')
        raw=z.read(z.namelist()[0])
    rows=list(deque(csv.reader(io.StringIO(raw.decode('utf-8-sig'))),maxlen=6))
    if len(rows)!=6 or any(len(r)!=12 for r in rows):
        raise ValueError('SOURCE_STOP: six actual terminal rows required')
    return rows,hashlib.sha256(raw).hexdigest()

def validate_terminal_rows(times,available,opens,marks,quote_volume,end=END):
    times=np.asarray(times);available=np.asarray(available)
    if (not np.array_equal(times,np.arange(end-6*MINUTE,end,MINUTE,dtype=np.int64))
            or not np.array_equal(available,times+MINUTE)):
        raise ValueError('SOURCE_STOP: actual terminal quote clocks do not admit five attempts')
    for a in (opens,marks):
        if np.asarray(a).shape!=(6,) or not np.isfinite(a).all() or (np.asarray(a)<=0).any():
            raise ValueError('SOURCE_STOP: terminal positive actual prices required')
    if (np.asarray(quote_volume).shape!=(6,) or not np.isfinite(quote_volume).all()
            or (np.asarray(quote_volume)<0).any()):
        raise ValueError('SOURCE_STOP: terminal actual prior quote volume required')
    return dict(signal_us=end-6*MINUTE,
                attempt_us=[int(x+1) for x in times[1:]],
                prior_capacity_source_open_us=[int(x) for x in times[:-1]],
                prior_capacity_available_us=[int(x) for x in available[:-1]],
                final_mark_available_us=int(available[-1]),attempt_count=5,
                all_attempts_before_calendar_end=bool((times[1:]+1<end).all()))

def check():
    index_path=SOURCE/'prepared_2021/SOURCE_INDEX.json'
    if sha(index_path)!='13a0d6551deef1e5cc6865ff4487ebf3fed5dd518364e909fb25ab228838eb33':
        raise ValueError('SOURCE_STOP: bound full2021 index changed')
    index=json.loads(index_path.read_text());rec=index['months'][-1]
    cache=SOURCE/'prepared_2021/months/2021-12.npz'
    if sha(cache)!=rec['source_NPZ_SHA256']:
        raise ValueError('SOURCE_STOP: final month changed')
    output={}
    with np.load(cache,allow_pickle=False) as a,zipfile.ZipFile(SOURCE/'source/Y2021.zip') as outer:
        for s in SYMBOLS:
            trade=outer.read(f'raw/klines/{s}/{s}-1m-2021-12.zip')
            mark=(SOURCE/'source/DEC2021'/s/(s+'-1m-2021-12.zip')).read_bytes()
            originals={r['family']:r for r in rec['sources'] if r['symbol']==s}
            for family,body in [('klines',trade),('markPriceKlines',mark)]:
                owner=originals[family]
                if hashlib.sha256(body).hexdigest()!=owner['ZIP_SHA256']:
                    raise ValueError('SOURCE_STOP: terminal original ZIP changed')
                rows,csv_sha=final_rows(body)
                if csv_sha!=owner['parsed']['CSV_SHA256']:
                    raise ValueError('SOURCE_STOP: terminal original CSV changed')
                t=np.asarray([int(r[0])*1000 for r in rows],dtype=np.int64)
                av=np.asarray([int(r[6])*1000+1000 for r in rows],dtype=np.int64)
                np.testing.assert_array_equal(t,a['times'][-6:])
                np.testing.assert_array_equal(av,a['available_us'][-6:])
                for col,key in [(1,'open' if family=='klines' else 'mark_open'),
                                (4,'close' if family=='klines' else 'mark')]:
                    value=pd.to_numeric(pd.Series([r[col] for r in rows])).to_numpy(dtype=float)
                    np.testing.assert_array_equal(value,a[s+'_'+key][-6:])
                    if value.tobytes()!=a[s+'_'+key][-6:].tobytes():
                        raise ValueError('SOURCE_STOP: terminal source price bits')
                if family=='klines':
                    value=pd.to_numeric(pd.Series([r[7] for r in rows])).to_numpy(dtype=float)
                    np.testing.assert_array_equal(value,a[s+'_quote_volume'][-6:])
            output[s]={**validate_terminal_rows(a['times'][-6:],a['available_us'][-6:],
                          a[s+'_open'][-6:],a[s+'_mark'][-6:],a[s+'_quote_volume'][-6:]),
                'trade_ZIP_SHA256':originals['klines']['ZIP_SHA256'],
                'mark_ZIP_SHA256':originals['markPriceKlines']['ZIP_SHA256'],
                'actual_trade_and_mark_CSV_rows_checked':12,
                'attempt_open_prices':[float(x) for x in a[s+'_open'][-5:]],
                'prior_quote_volume':[float(x) for x in a[s+'_quote_volume'][-6:-1]],
                'last_actual_mark_close':float(a[s+'_mark'][-1])}
    return dict(status='PASS_ACTUAL_FIVE_TERMINAL_QUOTES_NO_FILL_PROMISE',
        source_index_SHA256=sha(index_path),December_cache_SHA256=sha(cache),
        actual_raw_CSV_rows_checked=60,symbols=output,
        contract='Signal Dec31 23:54; attempts 23:55..23:59 plus1us; prior completed quote_volume × .001 capacity; reductions precede increases; fees/slippage charged; never force free flat.',
        arrival_authority='Original frozen timing remains conditional; raw open/close clocks are source evidence, not historical arrival certification.',
        terminal_paid_flat_assumed=False,new_historical_wallets=0,provider_downloads=0)

if __name__=='__main__': print(json.dumps(check(),indent=2))
