from __future__ import annotations
import calendar
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .common import (CODE_VERSION, DATA, DAY_MS, EXEC_OFFSET_US, REPORTS, WORK, E,
                     atomic_text, bounds, code_digest, disk_guard, dump, init_dirs,
                     log, months, progress, sha256, symbols)
from .download import sources_for_month, verify_local
from .storage import read_table, suffix, write_table

PRICE_COLUMNS = ['timestamp_ms', 'open', 'high', 'low', 'close', 'volume', 'close_time_ms',
                 'quote_volume', 'trades', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
FUND_COLUMNS = ['calc_time_ms', 'funding_interval_hours', 'last_funding_rate']


def month_limits(y: int, m: int) -> tuple[int, int]:
    left = pd.Timestamp(year=y, month=m, day=1, tz='UTC')
    right = left + pd.offsets.MonthBegin(1)
    return left.value // 1_000_000, right.value // 1_000_000


def numeric_csv(path: Path, funding: bool = False) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) != 1:
            raise ValueError(f'{path.name}: expected a single CSV member')
        # Checksum/ZIP validation is performed independently before every import.
        with archive.open(infos[0]) as f:
            d = pd.read_csv(f, header=None, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    expected = 3 if funding else 12
    if d.shape[1] != expected or d.empty:
        raise ValueError(f'{path.name}: expected nonempty {expected}-column CSV')
    first = str(d.iloc[0, 0]).strip().lower().replace(' ', '_')
    if first in ('open_time', 'open_timestamp', 'calc_time'):
        if funding and list(d.iloc[0]) != ['calc_time', 'funding_interval_hours', 'last_funding_rate']:
            raise ValueError(f'{path.name}: unsupported funding header')
        if not funding:
            aliases = [
                {'open_time', 'open_timestamp'}, {'open'}, {'high'}, {'low'}, {'close'}, {'volume'},
                {'close_time', 'close_timestamp', 'close_time_ms'}, {'quote_volume', 'quote_asset_volume'},
                {'count', 'trades', 'number_of_trades'}, {'taker_buy_volume', 'taker_buy_base_asset_volume'},
                {'taker_buy_quote_volume', 'taker_buy_quote_asset_volume'}, {'ignore'}]
            names = [str(x).strip().lower().replace(' ', '_') for x in d.iloc[0]]
            if any(name not in accepted for name, accepted in zip(names, aliases)):
                raise ValueError(f'{path.name}: unsupported/reordered price header')
        d = d.iloc[1:].copy()
    if d.empty:
        raise ValueError(f'{path.name}: header without data')
    try:
        d = d.apply(pd.to_numeric, errors='raise')
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{path.name}: invalid data row; only a recognized first header may be removed') from exc
    if not np.isfinite(d.to_numpy(dtype=float)).all():
        raise ValueError(f'{path.name}: nonfinite data; not silently dropped')
    d.columns = FUND_COLUMNS if funding else PRICE_COLUMNS
    return d


def deduplicate(d: pd.DataFrame, time_column: str) -> tuple[pd.DataFrame, int]:
    before = len(d)
    distinct = d.drop_duplicates()
    if distinct[time_column].duplicated().any():
        raise ValueError('Conflicting duplicate timestamps; no keep-last policy')
    return distinct.sort_values(time_column).reset_index(drop=True), before - len(distinct)


def validate_price(d: pd.DataFrame, family: str, left_ms: int, right_ms: int) -> tuple[pd.DataFrame, int]:
    d, duplicates = deduplicate(d, 'timestamp_ms')
    t = d.timestamp_ms.to_numpy(dtype=float)
    c = d.close_time_ms.to_numpy(dtype=float)
    if not ((t == np.floor(t)) & (t >= left_ms) & (t < right_ms) & (t % 60000 == 0)).all():
        raise ValueError('USD-M source timestamp must be epoch MILLISECONDS on its stated minute grid; no silent unit conversion')
    if not (c == t + 59999).all():
        raise ValueError('Invalid source close_time; expected open + 59,999 milliseconds')
    if family != 'premiumIndexKlines' and (d[['open', 'high', 'low', 'close']] <= 0).any().any():
        raise ValueError('Nonpositive trade/mark price')
    envelope = (d.low <= d[['open', 'close']].min(axis=1)) & (d.high >= d[['open', 'close']].max(axis=1)) & (d.low <= d.high)
    if not envelope.all():
        raise ValueError('Invalid OHLC envelope')
    if family == 'klines':
        cols = ['volume', 'quote_volume', 'trades', 'taker_buy_volume', 'taker_buy_quote_volume']
        if (d[cols] < 0).any().any() or not np.equal(d.trades, np.floor(d.trades)).all():
            raise ValueError('Invalid trade volume/count')
    d['timestamp_ms'] = d.timestamp_ms.astype('int64')
    d['close_time_ms'] = d.close_time_ms.astype('int64')
    return d, duplicates


def validate_funding(d: pd.DataFrame, left_ms: int, right_ms: int) -> tuple[pd.DataFrame, int]:
    d, duplicates = deduplicate(d, 'calc_time_ms')
    t = d.calc_time_ms.to_numpy(dtype=float)
    if not ((t == np.floor(t)) & (t >= left_ms) & (t < right_ms)).all():
        raise ValueError('Funding calc_time must be original epoch milliseconds in its stated month')
    if not ((d.funding_interval_hours > 0) & (d.funding_interval_hours <= 24)).all():
        raise ValueError('Unsupported funding nominal interval; requires explicit source review')
    d['calc_time_ms'] = d.calc_time_ms.astype('int64')
    return d, duplicates


def aggregate_price(d: pd.DataFrame, family: str) -> pd.DataFrame:
    if d.empty:
        return pd.DataFrame()
    q = d.copy()
    q['dt'] = pd.to_datetime(q.timestamp_ms, unit='ms', utc=True).dt.floor('D')
    grouped = q.groupby('dt', sort=True)
    out = grouped.agg(open=('open', 'first'), high=('high', 'max'), low=('low', 'min'), close=('close', 'last'),
                      volume=('volume', 'sum'), quote_volume=('quote_volume', 'sum'), trades=('trades', 'sum'),
                      rows=('timestamp_ms', 'size'), unique_minutes=('timestamp_ms', 'nunique'),
                      first_ms=('timestamp_ms', 'min'), last_ms=('timestamp_ms', 'max'))
    day_ms = out.index.as_unit('ms').asi8
    out['complete'] = (out.rows.eq(1440) & out.unique_minutes.eq(1440) & out.first_ms.eq(day_ms) & out.last_ms.eq(day_ms + 1439 * 60000))
    # Keep counts for diagnosis; never expose partial OHLC as a completed daily observation.
    values = ['open', 'high', 'low', 'close', 'volume', 'quote_volume', 'trades']
    out.loc[~out.complete, values] = np.nan
    minute1 = q[q.timestamp_ms % DAY_MS == 60000].set_index('dt')['open']
    out['exec_price'] = minute1.reindex(out.index)  # actual observed future fill, NOT a feature
    return out


def canonical(d: pd.DataFrame, family: str, symbol: str) -> pd.DataFrame:
    q = d.copy()
    q.insert(0, 'symbol', symbol)
    if family == 'fundingRate':
        q['raw_rate_unit'] = 'UNCONFIRMED'
        return q
    q['available_us'] = (q.timestamp_ms + 60000) * 1000
    if family == 'klines':
        q['open_us'] = q.timestamp_ms * 1000
        q['close_us'] = q.available_us  # exclusive close, unlike inclusive exchange close_time_ms
    return q


def convert_month(symbol: str, family: str, y: int, m: int) -> tuple[pd.DataFrame, dict, Path | None]:
    paths = sources_for_month(symbol, family, y, m)
    if not paths:
        return pd.DataFrame(), {'symbol': symbol, 'family': family, 'month': f'{y}-{m:02d}', 'status': 'UNAVAILABLE_UNCLASSIFIED'}, None
    proofs = [dict(path=str(p), url_path=f'{family}/{symbol}/{p.name}', **verify_local(p)) for p in paths]
    digest = code_digest()
    base = DATA / 'normalized' / 'minute' / symbol / family / f'{y}-{m:02d}'
    out = Path(str(base) + suffix())
    receipt_path = base.with_suffix('.receipt.json')
    binding = dict(sources=[{'path': x['path'], 'sha256': x['sha256']} for x in proofs], code_sha256=digest,
                   range=[E('WARMUP_START'), E('END_DATE')], table_format=E('TABLE_FORMAT'))
    if out.exists() and receipt_path.exists():
        cached = json.loads(receipt_path.read_text())
        if cached.get('binding') == binding and cached.get('output_sha256') == sha256(out):
            return read_table(out), cached, out
    left, right = month_limits(y, m)
    frames = [numeric_csv(p, family == 'fundingRate') for p in paths]
    d = pd.concat(frames, ignore_index=True)
    d, duplicates = validate_funding(d, left, right) if family == 'fundingRate' else validate_price(d, family, left, right)
    start, end = bounds()
    lo = pd.Timestamp(start, tz='UTC').value // 1_000_000
    hi = (pd.Timestamp(end, tz='UTC') + pd.Timedelta(days=1)).value // 1_000_000
    tcol = 'calc_time_ms' if family == 'fundingRate' else 'timestamp_ms'
    d = d[(d[tcol] >= lo) & (d[tcol] < hi)]
    d = canonical(d, family, symbol)
    out = write_table(d, base)
    receipt = dict(symbol=symbol, family=family, month=f'{y}-{m:02d}', status='VALIDATED_PRESENT_ROWS',
                   rows=len(d), identical_duplicates_removed=duplicates, sources=proofs,
                   binding=binding, output_sha256=sha256(out), output_bytes=out.stat().st_size)
    dump(receipt, receipt_path)
    return d, receipt, out


def mark_funding(events: pd.DataFrame, marks: pd.DataFrame) -> pd.DataFrame:
    result = events.copy()
    if result.empty:
        result['past_mark_price'] = pd.Series(dtype=float)
        result['past_mark_available_us'] = pd.Series(dtype=float)
        return result
    result['past_mark_price'] = np.nan
    result['past_mark_available_us'] = np.nan
    if marks.empty:
        return result
    times = marks.available_us.to_numpy(dtype=np.int64)
    event_us = result.calc_time_ms.to_numpy(dtype=np.int64) * 1000
    positions = np.searchsorted(times, event_us, side='left') - 1
    ok = positions >= 0
    # Require the most recent strictly-past closed minute, not a mark across a gap.
    clipped = np.maximum(positions, 0)
    ok &= (event_us - times[clipped] > 0) & (event_us - times[clipped] <= 60000 * 1000)
    result.loc[ok, 'past_mark_price'] = marks.close.to_numpy()[positions[ok]]
    result.loc[ok, 'past_mark_available_us'] = times[positions[ok]]
    return result


def funding_windows(events: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    out = pd.DataFrame(index=days)
    for col in ('funding', 'funding_events', 'funding_hours', 'funding_rate_sum_interval', 'mark_funding_per_unit'):
        out[col] = np.nan
    out['complete_funding'] = False
    out['funding_interval_complete'] = False
    if events.empty:
        return out
    e, _ = deduplicate(events, 'calc_time_ms')
    times = e.calc_time_ms.to_numpy(dtype=np.int64) * 1000
    hours = e.funding_interval_hours.to_numpy(dtype=float)
    diffs = np.diff(times)
    # Archive calc timestamps can have millisecond jitter; retain raw times unchanged.
    good_gaps = (np.abs(diffs - hours[:-1] * 3_600_000_000) <= 1_000_000) | (np.abs(diffs - hours[1:] * 3_600_000_000) <= 1_000_000)
    rates = e.last_funding_rate.to_numpy(dtype=float)
    marks = e.past_mark_price.to_numpy(dtype=float)

    def complete(left: int, right: int, need_marks: bool, causal: bool = False) -> tuple[bool, np.ndarray]:
        # Window is (left, right]. Require evidence on BOTH sides rather than event-count heuristics.
        before = int(np.searchsorted(times, left, side='right') - 1)
        after = int(np.searchsorted(times, right, side='right'))
        selected = np.flatnonzero((times > left) & (times <= right))
        if causal:
            last = after - 1
            ok = before >= 0 and last >= before
            if ok:
                ok = bool(good_gaps[before:last].all() and right - times[last] <= hours[last] * 3_600_000_000 + 1_000_000)
        else:
            ok = before >= 0 and after < len(times)
            if ok:
                ok = bool(good_gaps[before:after].all())
        if need_marks:
            ok = ok and bool(np.isfinite(marks[selected]).all())
        return ok, selected

    for day in days:
        left = day.value // 1000
        # Features at day close contain ONLY events before the completed-day boundary.
        ok, idx = complete(left - 1, left + DAY_MS * 1000 - 1, False, causal=True)
        out.loc[day, 'funding_events'] = len(idx)
        out.loc[day, 'funding_hours'] = float(hours[idx].sum()) if len(idx) else np.nan
        out.loc[day, 'complete_funding'] = ok
        out.loc[day, 'funding'] = float(rates[idx].sum()) if ok else np.nan
        start = left + EXEC_OFFSET_US
        ok, idx = complete(start, start + DAY_MS * 1000, True)
        out.loc[day, 'funding_interval_complete'] = ok
        if ok:
            out.loc[day, 'funding_rate_sum_interval'] = float(rates[idx].sum())
            out.loc[day, 'mark_funding_per_unit'] = float(np.dot(rates[idx], marks[idx]))
    return out


def artifact(path: Path, role: str) -> dict:
    return {'relative_path': str(path.relative_to(WORK)), 'bytes': path.stat().st_size,
            'sha256': sha256(path), 'role': role}


def normalize() -> dict:
    init_dirs()
    a, b = bounds()
    days = pd.date_range(a, b, freq='D', tz='UTC')
    families = E('FAMILIES').split(',')
    month_list = list(months(a, b))
    artifacts, receipts, audits = [], [], []
    total = len(symbols()) * len(month_list)
    n = 0
    for symbol in symbols():
        aggregates = {f: [] for f in families if f != 'fundingRate'}
        funding_parts = []
        previous_marks = pd.DataFrame()
        for y, m in month_list:
            n += 1
            progress('NORMALIZE', n - 1, total, f'{symbol}/{y}-{m:02d}')
            current = {}
            disk_guard()
            for family in families:
                d, receipt, path = convert_month(symbol, family, y, m)
                receipts.append(receipt)
                if path is not None:
                    artifacts.append(artifact(path, family + '_minute' if family != 'fundingRate' else 'funding_events_raw'))
                current[family] = d
                if family != 'fundingRate' and not d.empty:
                    aggregates[family].append(aggregate_price(d, family))
            marks = pd.concat([previous_marks, current.get('markPriceKlines', pd.DataFrame())], ignore_index=True)
            if not marks.empty:
                marks = marks.sort_values('available_us')
            events = current.get('fundingRate', pd.DataFrame())
            if not events.empty:
                funding_parts.append(mark_funding(events, marks))
            previous_marks = marks.tail(2).copy() if not marks.empty else pd.DataFrame()
            log(f'NORMALIZE {n}/{total} {symbol}/{y}-{m:02d}')
            del current, marks
        daily = pd.DataFrame(index=days)
        for family in ('klines', 'markPriceKlines', 'premiumIndexKlines'):
            parts = aggregates.get(family, [])
            q = pd.concat(parts).sort_index().reindex(days) if parts else pd.DataFrame(index=days)
            flag = {'klines': 'complete_kline', 'markPriceKlines': 'complete_mark', 'premiumIndexKlines': 'complete_premium'}[family]
            daily[flag] = q.get('complete', pd.Series(False, index=days)).fillna(False).astype(bool)
            if family == 'klines':
                for col in ('open', 'high', 'low', 'close', 'volume', 'quote_volume', 'trades', 'rows', 'unique_minutes', 'exec_price'):
                    daily[col] = q.get(col, pd.Series(np.nan, index=days))
            else:
                daily['mark' if family == 'markPriceKlines' else 'premium'] = q.get('close', pd.Series(np.nan, index=days))
        events = pd.concat(funding_parts, ignore_index=True) if funding_parts else pd.DataFrame(columns=FUND_COLUMNS + ['past_mark_price', 'past_mark_available_us'])
        if not events.empty:
            events, _ = deduplicate(events, 'calc_time_ms')
        daily = daily.join(funding_windows(events, days))
        daily['source_state'] = np.where(daily.complete_kline, 'OBSERVED_COMPLETE', 'MISSING_OR_INCOMPLETE_UNCLASSIFIED')
        observed = daily.index[daily.complete_kline]
        first, last = (observed.min(), observed.max()) if len(observed) else (None, None)
        if first is not None:
            daily.loc[daily.index < first, 'source_state'] = 'UNOBSERVED_PREFIX_NOT_LISTING_PROOF'
        daily['symbol'] = symbol
        daily['open_us'] = daily.index.as_unit('us').asi8
        daily['close_us'] = daily.open_us + DAY_MS * 1000
        daily['available_us'] = daily.close_us
        daily.index.name = 'dt'
        dpath = write_table(daily.reset_index(), DATA / 'normalized' / f'{symbol}_daily')
        epath = write_table(events, DATA / 'normalized' / f'{symbol}_funding_events')
        artifacts += [artifact(dpath, 'daily'), artifact(epath, 'funding_events_with_past_marks')]
        between = (daily.index >= first) & (daily.index <= last) if first is not None else np.zeros(len(daily), dtype=bool)
        row = dict(symbol=symbol, calendar_days=len(daily), first_complete_day=str(first) if first is not None else None,
                   last_complete_day=str(last) if last is not None else None,
                   complete_kline_days=int(daily.complete_kline.sum()), complete_mark_days=int(daily.complete_mark.sum()),
                   complete_funding_feature_days=int(daily.complete_funding.sum()),
                   complete_funding_execution_intervals=int(daily.funding_interval_complete.sum()),
                   internal_incomplete_kline_days=int((~daily.loc[between, 'complete_kline']).sum()),
                   funding_events=len(events), listing_status='NOT_INFERRED_FROM_404',
                   missing_days_not_imputed=True)
        audits.append(row)
    audit_csv = REPORTS / 'data_audit.csv'
    atomic_text(audit_csv, pd.DataFrame(audits).to_csv(index=False))
    dump(audits, REPORTS / 'data_audit.json')
    manifest = dict(version=CODE_VERSION, status=('VALIDATED_AVAILABLE_SOURCE_ONLY' if any(x['complete_kline_days'] for x in audits) else 'FAILED_NO_COMPLETE_TRADE_DAYS'),
                    full_requested_coverage_certified=False, code_sha256=code_digest(),
                    source_config={k: E(k) for k in ('FAMILIES', 'TABLE_FORMAT')},
                    date_range={'start': str(a), 'end_inclusive': str(b)}, symbols=symbols(),
                    market='BINANCE_USDM_NOT_BYBIT_NATIVE', raw_timestamp_unit='milliseconds',
                    trade_canonical_unit='microseconds; exclusive close_us=available_us',
                    funding_rate_unit='UNCONFIRMED_RAW_PRESERVED',
                    funding_time_semantics='archive calc_time; exchange publication/charge times not natively certified',
                    artifacts=artifacts, source_receipts=receipts, audit=audits)
    dump(manifest, REPORTS / 'DATASET_MANIFEST.json')
    progress('NORMALIZE', total, total, 'Daily/minute/funding artifacts and manifest written')
    if not any(x['complete_kline_days'] for x in audits):
        raise ValueError('No complete trade day for any requested symbol. Audit written; empty data is not a successful collector result.')
    return manifest


def verify_dataset() -> dict:
    bounds()
    manifest = json.loads((REPORTS / 'DATASET_MANIFEST.json').read_text())
    if manifest.get('status') != 'VALIDATED_AVAILABLE_SOURCE_ONLY':
        raise ValueError('Dataset manifest is not a successful available-source normalization')
    if manifest.get('source_config') != {k: E(k) for k in ('FAMILIES', 'TABLE_FORMAT')}:
        raise ValueError('Dataset family/format config changed; rerun normalize')
    if manifest['date_range'] != {'start': E('WARMUP_START'), 'end_inclusive': E('END_DATE')} or manifest['symbols'] != symbols():
        raise ValueError('Dataset config changed; rerun normalize. Old .done files are not evidence.')
    if manifest['code_sha256'] != code_digest():
        raise ValueError('Source code changed; rerun normalize to bind the corrected pipeline')
    for item in manifest['artifacts']:
        p = (WORK / item['relative_path']).resolve()
        if not p.is_relative_to(WORK) or not p.is_file() or p.stat().st_size != item['bytes'] or sha256(p) != item['sha256']:
            raise ValueError(f'Dataset output missing/corrupt/modified: {item["relative_path"]}')
    return manifest
