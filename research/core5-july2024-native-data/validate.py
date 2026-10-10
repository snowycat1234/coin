"""Restore only fixed July2024 execution/minute/funding inputs via the frozen normalizer."""
import argparse
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import zipfile

CORE5 = ['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT']
FOLD = 'JULY2024'
PROTOCOL_COMMIT = '6cdddbe57485066e2a98a0042da398494f55b709'
ORIGINAL_SOURCE_COMMIT = 'b8299bc22321b9dadf707f14da83ac40a39b5491'
MANIFEST_SHA = '99f07ef591581a51babb0b4a8b3079310f24a8bfe0e91b09103c4a68ffa82130'
DAY_US = 86400000000
MINUTE_US = 60000000


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):
            h.update(chunk)
    return h.hexdigest()


def dump(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def validate(root,source_root):
    folder = root / FOLD
    raw = json.loads((folder/'RAW_MANIFEST.json').read_text())
    protocol_dir = root/'protocol'
    protocol = json.loads((protocol_dir/'PROTOCOL.json').read_text())
    manifest_path = protocol_dir/'ORIGINAL_SOURCE_MANIFEST.json'
    if sha(manifest_path) != MANIFEST_SHA:
        raise ValueError('Frozen original source manifest identity changed')
    manifest = json.loads(manifest_path.read_text())
    bindings = {}
    for name in ('normalize','common','download','storage'):
        relative = f'modules/collector_research/pipeline/{name}.py'
        expected = manifest['versioned_sources'][relative]
        if sha(source_root/relative) != expected:
            raise ValueError('Frozen normalizer dependency changed: '+relative)
        bindings[relative] = expected
    sys.path.insert(0,str(source_root))
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    from modules.collector_research.pipeline import normalize as original
    if Path(original.__file__).resolve() != (source_root/'modules/collector_research/pipeline/normalize.py').resolve():
        raise ValueError('Unexpected imported normalizer path')
    left_us,right_us = protocol['calendar']['start_us'],protocol['calendar']['end_exclusive_us']
    decisions = np.arange(left_us,right_us,DAY_US,dtype=np.int64)
    if len(decisions)!=63 or int(decisions[-1])+MINUTE_US+1 != 1725148860000001:
        raise ValueError('Fixed July2024 calendar or paid close changed')
    grid = np.arange(left_us//1000,right_us//1000,60000,dtype=np.int64)
    if len(grid)!=90720:
        raise ValueError('Expected 63-day minute grid')
    receipts,artifacts,coverage,supplement_checks = [],[],{},[]
    native = folder/'normalized'
    began = time.monotonic()
    prices,coefficients = [],[]
    def write(frame,relative,role):
        path = native/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        pq.write_table(pa.Table.from_pandas(frame,preserve_index=False),path,compression='zstd')
        back = pq.read_table(path,use_threads=False).to_pandas(use_threads=False)
        if not frame.equals(back):
            raise ValueError('Canonical Parquet round trip changed values/types')
        artifacts.append(dict(path=str(path.relative_to(folder)),bytes=path.stat().st_size,SHA256=sha(path),role=role,rows=len(frame)))
        return path
    for symbol in CORE5:
        frames = {f:[] for f in ('klines','markPriceKlines','fundingRate')}
        for record in (r for r in raw['records'] if r['symbol']==symbol):
            path = folder/record['relative_raw_path']
            if path.stat().st_size!=record['size'] or sha(path)!=record['SHA256']:
                raise ValueError('Original official archive SHA/size changed')
            with zipfile.ZipFile(path) as z:
                if z.testzip() is not None:
                    raise ValueError('ZIP CRC failed')
            y,m = map(int,record['month'].split('-'))
            lo,hi = original.month_limits(y,m)
            family = record['family']
            d = original.numeric_csv(path,funding=family=='fundingRate')
            if family=='fundingRate':
                d,duplicates = original.validate_funding(d,lo,hi)
                q = original.canonical(d,family,symbol)
                stamp = q.calc_time_ms.to_numpy(np.int64)
                unit_complete = None
                expected_count = None
                quote_digest = None
            else:
                d,duplicates = original.validate_price(d,family,lo,hi)
                q = original.canonical(d,family,symbol)
                stamp = q.timestamp_ms.to_numpy(np.int64)
                if record['source_frequency']=='daily':
                    lo = pd.Timestamp(record['source_period'],tz='UTC').value//1000000
                    hi = lo+86400000
                expected = np.arange(lo,hi,60000,dtype=np.int64)
                unit_complete = bool(np.array_equal(stamp,expected))
                expected_count = len(expected)
                missing = np.setdiff1d(expected,stamp)
                if not np.array_equal(q.available_us.to_numpy(),(stamp+60000)*1000):
                    raise ValueError('Completed-minute availability changed')
                if not np.array_equal(q.quote_volume.to_numpy(),d.quote_volume.to_numpy()):
                    raise ValueError('Original quote-USDT volume changed')
                quote_digest = hashlib.sha256(np.asarray(q.quote_volume.to_numpy(),dtype='<f8').tobytes()).hexdigest()
            source_rows = len(q)
            if record.get('gap_supplement'):
                primary=pd.concat(frames[family],ignore_index=True).set_index('timestamp_ms')
                duplicate=q[q.timestamp_ms.isin(primary.index)].set_index('timestamp_ms')
                cols=[c for c in original.PRICE_COLUMNS if c!='timestamp_ms']
                if not np.array_equal(duplicate[cols].to_numpy(),primary.loc[duplicate.index,cols].to_numpy()):
                    raise ValueError('Supplemental official daily source conflicts with overlapping monthly observations')
                additions=q[~q.timestamp_ms.isin(primary.index)].copy()
                supplement_checks.append(dict(symbol=symbol,family=family,source_period=record['source_period'],
                    official_daily_SHA256=record['SHA256'],overlap_rows_equal=len(duplicate),
                    genuine_missing_rows_added=len(additions),added_timestamp_ms=additions.timestamp_ms.tolist()))
                q=additions
            frames[family].append(q)
            receipts.append(dict(symbol=symbol,family=family,source_period=record['source_period'],
                source_frequency=record['source_frequency'],original_SHA256=record['SHA256'],rows=source_rows,
                expected_source_minute_rows=expected_count,full_source_unit_grid_complete=unit_complete,
                source_missing_ms=[] if family=='fundingRate' else missing.tolist(),
                identical_duplicates_removed=duplicates,timestamp_unit='original epoch milliseconds',
                quote_volume_float64_SHA256=quote_digest,
                quote_volume_preserved_exactly=family!='fundingRate'))
            del d
        trade = pd.concat(frames['klines'],ignore_index=True)
        marks = pd.concat(frames['markPriceKlines'],ignore_index=True)
        events = pd.concat(frames['fundingRate'],ignore_index=True)
        trade,_ = original.deduplicate(trade,'timestamp_ms')
        marks,_ = original.deduplicate(marks,'timestamp_ms')
        events,_ = original.deduplicate(events,'calc_time_ms')
        native_missing={}
        for family,frame in (('klines',trade),('markPriceKlines',marks)):
            times = frame.timestamp_ms.to_numpy(np.int64)
            observed = times[(times>=left_us//1000)&(times<right_us//1000)]
            native_missing[family]=np.setdiff1d(grid,observed)
            for month,selected in frame.groupby(pd.to_datetime(frame.timestamp_ms,unit='ms',utc=True).dt.strftime('%Y-%m'),sort=True):
                write(selected.reset_index(drop=True),Path('data/normalized/minute')/symbol/family/(month+'.parquet'),family+'_native_minute')
        # Preserve exact event timestamps/rates; only requested interval events are canonicalized.
        event_us = events.calc_time_ms.to_numpy(np.int64)*1000
        events = events[(event_us>=left_us)&(event_us<right_us)].reset_index(drop=True)
        events = original.mark_funding(events,marks)
        event_us = events.calc_time_ms.to_numpy(np.int64)*1000
        available = events.past_mark_available_us.to_numpy(float)
        # Independent clock formula, including the exact closed-minute boundary case.
        expected_available = ((event_us-1)//MINUTE_US)*MINUTE_US
        if not np.array_equal(available,expected_available) or not np.all(np.diff(event_us)>0):
            raise ValueError('Actual funding marks are not the latest strictly prior completed minute')
        expected_mark = pd.Series(marks.close.to_numpy(float),index=marks.available_us.to_numpy(np.int64)).reindex(expected_available).to_numpy(float)
        if not np.array_equal(events.past_mark_price.to_numpy(float),expected_mark) or not np.isfinite(expected_mark).all() or (expected_mark<=0).any():
            raise ValueError('Funding mark price differs from actual completed source minute')
        write(events,Path('data/normalized')/(symbol+'_funding_events.parquet'),'actual_event_funding_with_strictly_prior_marks')
        windows = original.funding_windows(events,pd.to_datetime(decisions[:-1],unit='us',utc=True))
        if len(windows)!=62 or not windows.funding_interval_complete.all():
            raise ValueError('Not all 62 fixed held intervals have actual event brackets/marks')
        coefficients_symbol = windows.mark_funding_per_unit.to_numpy(float)
        max_error = 0.0
        for i,start in enumerate(decisions[:-1]+MINUTE_US+1):
            selected = (event_us>start)&(event_us<=start+DAY_US)
            reference = math.fsum(float(rate)*float(mark) for rate,mark in zip(events.last_funding_rate.to_numpy(float)[selected],expected_mark[selected]))
            error = abs(coefficients_symbol[i]-reference)
            if not math.isclose(coefficients_symbol[i],reference,rel_tol=2e-15,abs_tol=1e-10):
                raise ValueError('Signed quantity-denominated funding differs from independent event sum')
            max_error = max(max_error,error)
        windows = windows.reset_index(names='dt')
        windows.insert(0,'symbol',symbol)
        write(windows,Path('economics')/(symbol+'_funding_intervals.parquet'),'62_actual_held_funding_intervals_no_terminal_padding')
        # Economic daily source schema is derived via the unchanged minute aggregator;
        # no primitive feature table or feature/mask builder is read or altered.
        daily = original.aggregate_price(trade,'klines')
        daily = daily.reindex(pd.to_datetime(decisions,unit='us',utc=True))
        if not daily.complete.all() or not daily.unique_minutes.eq(1440).all():
            raise ValueError('Forward economic source days incomplete')
        exec_times = decisions+MINUTE_US
        expected_price = pd.Series(trade.open.to_numpy(float),index=trade.timestamp_ms.to_numpy(np.int64)*1000).reindex(exec_times).to_numpy(float)
        if not np.array_equal(daily.exec_price.to_numpy(float),expected_price) or not np.isfinite(expected_price).all() or (expected_price<=0).any():
            raise ValueError('Execution price must equal actual 00:01 trade-minute OPEN')
        daily = daily.rename(columns={'complete':'complete_kline'}).reset_index(names='dt')
        daily.insert(0,'symbol',symbol)
        daily['open_us'] = decisions
        daily['close_us'] = decisions+DAY_US
        daily['available_us'] = daily.close_us
        write(daily,Path('data/normalized')/(symbol+'_daily.parquet'),'63_execution_economic_rows_not_model_daily_features')
        prices.append(expected_price)
        coefficients.append(coefficients_symbol)
        held = (event_us>decisions[0]+MINUTE_US+1)&(event_us<=decisions[-1]+MINUTE_US+1)
        coverage[symbol] = dict(trade_minutes=90720-len(native_missing['klines']),mark_minutes=90720-len(native_missing['markPriceKlines']),
            missing_trade_minutes=len(native_missing['klines']),missing_mark_minutes=len(native_missing['markPriceKlines']),
            missing_mark_timestamp_ms=native_missing['markPriceKlines'].tolist(),
            execution_prices=63,complete_execution_days=63,complete_held_funding_intervals=62,
            funding_events_in_requested_63_days=len(events),funding_events_held_to_paid_close=int(held.sum()),
            strict_prior_funding_marks_valid=int(np.isfinite(expected_mark).sum()),
            maximum_independent_funding_coefficient_error=max_error,
            minimum_funding_mark_age_us=int((event_us-expected_available).min()),maximum_funding_mark_age_us=int((event_us-expected_available).max()),
            zero_quote_volume_minutes=int(((trade.timestamp_ms*1000>=left_us)&(trade.timestamp_ms*1000<right_us)&trade.quote_volume.eq(0)).sum()))
        print(json.dumps(dict(symbol=symbol,**coverage[symbol])),flush=True)
        del frames,trade,marks,events,windows,daily
        gc.collect()
    economics = folder/'ECONOMICS.npz'
    np.savez_compressed(economics,symbol_order=np.asarray(CORE5),decision_us=decisions,
        execution_us=decisions+MINUTE_US+1,prices=np.column_stack(prices),
        funding_interval_start_us=decisions[:-1]+MINUTE_US+1,
        funding_interval_end_us=decisions[1:]+MINUTE_US+1,funding_coeff=np.column_stack(coefficients))
    artifacts.append(dict(path=economics.name,bytes=economics.stat().st_size,SHA256=sha(economics),
        role='63 observed execution prices and 62 actual funding coefficients; unpadded',price_shape=[63,5],funding_shape=[62,5]))
    native_complete=all(r['missing_trade_minutes']==0 and r['missing_mark_minutes']==0 for r in coverage.values())
    result = dict(schema='FIXED_JULY2024_NATIVE_AND_DAILY_ECONOMIC_INPUT_READINESS_V1',
        status='VERIFIED_COMPLETE_FIXED_JULY2024_MINUTES_EXECUTION_AND_HELD_FUNDING' if native_complete else 'VERIFIED_COMPLETE_EXECUTION_AND_HELD_FUNDING_NATIVE_MARK_GAPS_REMAIN',fold=FOLD,
        execution_and_held_funding_ready=True,native_minute_grid_complete=native_complete,
        interval_UTC_start_inclusive='2024-07-01',interval_UTC_end_exclusive='2024-09-02',
        paid_close_UTC=protocol['calendar']['paid_close_UTC'],protocol_commit=PROTOCOL_COMMIT,
        protocol_SHA256=sha(protocol_dir/'PROTOCOL.json'),original_source_commit=ORIGINAL_SOURCE_COMMIT,
        original_source_manifest_SHA256=MANIFEST_SHA,normalization_source_commit=ORIGINAL_SOURCE_COMMIT,
        normalization_source_SHA256=bindings,symbols_order=CORE5,
        original_archive_count=raw['archive_count'],original_compressed_bytes=raw['total_original_compressed_bytes'],
        new_original_download_bytes=raw['new_original_download_bytes'],reused_verified_archive_count=raw['reused_verified_archive_count'],
        new_download_budget_bytes=180*1024*1024,monthly_and_daily_source_receipts=receipts,
        coverage=coverage,supplement_checks=supplement_checks,derived_artifacts=artifacts,minute_availability='exclusive close: (timestamp_ms+60000)*1000',
        execution_price_source='original trade minute OPEN at 00:01; execution clock adds one microsecond',
        quote_capacity_source='original klines.quote_volume (USDT), unchanged',
        funding_source='original raw signed last_funding_rate and calc_time_ms; source units/charge clock proxy assumptions remain the unchanged frozen contract',
        funding_mark_source='actual close of latest source minute with available_us strictly less than actual event_us; age <=60000000us',
        no_synthetic_observations=True,no_terminal_padding_in_artifact=True,no_September2_outcome_consumed=True,
        primitive_daily_features_rebuilt=False,feature_masks_or_model_changed=False,
        elapsed_seconds=time.monotonic()-began,model_fits=0,policy_inferences=0,backtests=0,wallets=0)
    dump(folder/'VALIDATION.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('monthly_and_daily_source_receipts','derived_artifacts','coverage')}),flush=True)


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True)
    a=p.parse_args()
    validate(a.root,a.source_root)
