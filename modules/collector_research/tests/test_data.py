import hashlib
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from pipeline.download import Job, parse_checksum, validate_range, verify_local
from pipeline.normalize import (PRICE_COLUMNS, FUND_COLUMNS, aggregate_price, deduplicate,
                                 funding_windows, mark_funding, numeric_csv, validate_funding, validate_price)
from pipeline.common import bounds

T = int(pd.Timestamp('2022-01-01', tz='UTC').timestamp() * 1000)


def prices(count=1440, offset=0):
    t = T + (np.arange(count) + offset) * 60000
    return pd.DataFrame(dict(timestamp_ms=t, open=np.full(count, 100.), high=np.full(count, 102.),
         low=np.full(count, 99.), close=np.full(count, 101.), volume=np.ones(count), close_time_ms=t + 59999,
         quote_volume=np.full(count, 100.), trades=np.ones(count), taker_buy_volume=np.zeros(count),
         taker_buy_quote_volume=np.zeros(count), ignore=np.zeros(count)))


def funding(days=5, every=8):
    times = np.arange(T, T + days * 86400000, every * 3600000)
    return pd.DataFrame(dict(calc_time_ms=times, funding_interval_hours=np.full(len(times), every),
                             last_funding_rate=np.full(len(times), .0001), past_mark_price=np.full(len(times), 100.)))


def test_checksum_binds_filename():
    assert parse_checksum('a' * 64 + '  BTC.zip\n', 'BTC.zip') == 'a' * 64
    with pytest.raises(ValueError):
        parse_checksum('a' * 64 + '  ETH.zip', 'BTC.zip')


@pytest.mark.parametrize('text', ['', 'x' * 64 + ' a.zip', 'a' * 64, 'a' * 64 + ' a.zip extra'])
def test_checksum_malformed(text):
    with pytest.raises(ValueError):
        parse_checksum(text, 'a.zip')


def test_range_correct_and_wrong_offset():
    assert validate_range('bytes 3-9/10', 3) == (9, 10)
    for header in (None, 'bytes 0-9/10', 'bytes 3-12/10', 'items 3-9/10'):
        with pytest.raises(ValueError):
            validate_range(header, 3)


def test_price_complete_and_partial_mask():
    p, _ = validate_price(prices(), 'klines', T, T + 86400000)
    daily = aggregate_price(p, 'klines')
    assert bool(daily.complete.iloc[0]) and daily.close.iloc[0] == 101
    partial = aggregate_price(p.drop(index=500), 'klines')
    assert not partial.complete.iloc[0]
    assert partial[['open', 'high', 'low', 'close', 'volume']].iloc[0].isna().all()
    assert partial.exec_price.iloc[0] == 100  # observed fill separate from daily features


def test_duplicate_conflicts_rejected_identical_counted():
    p = prices(2)
    good, count = deduplicate(pd.concat([p, p.iloc[[0]]]), 'timestamp_ms')
    assert len(good) == 2 and count == 1
    wrong = p.iloc[[0]].copy(); wrong['close'] = 100
    with pytest.raises(ValueError, match='Conflicting'):
        deduplicate(pd.concat([p, wrong]), 'timestamp_ms')


@pytest.mark.parametrize('change', ['microseconds', 'seconds', 'off_grid', 'wrong_close', 'negative_price', 'ohlc', 'negative_volume', 'fractional_count'])
def test_invalid_trade_rows(change):
    p = prices(2)
    if change == 'microseconds': p.timestamp_ms *= 1000
    elif change == 'seconds': p.timestamp_ms //= 1000
    elif change == 'off_grid': p.timestamp_ms += 1
    elif change == 'wrong_close': p.close_time_ms += 1
    elif change == 'negative_price': p['close'] = -1
    elif change == 'ohlc': p['high'] = 99
    elif change == 'negative_volume': p['volume'] = -1
    else: p['trades'] = .5
    with pytest.raises(ValueError):
        validate_price(p, 'klines', T, T + 86400000)


def test_negative_premium_is_valid_not_negative_price():
    p = prices(2)
    p[['open', 'high', 'low', 'close']] = [-.001, -.0005, -.002, -.0015]
    assert len(validate_price(p, 'premiumIndexKlines', T, T + 86400000)[0]) == 2


def test_header_and_corrupt_rows_not_silently_dropped(tmp_path):
    p = tmp_path / 'test.zip'
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr('test.csv', 'open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n' + prices(2).to_csv(index=False, header=False))
    assert len(numeric_csv(p)) == 2
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr('test.csv', prices(2).to_csv(index=False, header=False) + 'broken,1,2,3,4,5,6,7,8,9,10,11\n')
    with pytest.raises(ValueError, match='invalid data row'):
        numeric_csv(p)


def test_original_funding_header_and_units(tmp_path):
    p = tmp_path / 'test.zip'
    f = funding().drop(columns='past_mark_price')
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr('test.csv', 'calc_time,funding_interval_hours,last_funding_rate\n' + f.to_csv(index=False, header=False))
    d = numeric_csv(p, funding=True)
    assert list(d.columns) == FUND_COLUMNS
    assert validate_funding(d, T, T + 5 * 86400000)[1] == 0
    d.calc_time_ms *= 1000
    with pytest.raises(ValueError):
        validate_funding(d, T, T + 5 * 86400000)


def test_funding_negative_rate_and_jitter_preserved():
    f = funding().drop(columns='past_mark_price')
    f.calc_time_ms += 1
    f.last_funding_rate = -.0001
    d, _ = validate_funding(f, T, T + 5 * 86400000)
    assert d.calc_time_ms.iloc[0] == T + 1
    assert d.last_funding_rate.iloc[0] == -.0001


def test_funding_interval_gaps_detected_not_day_counts():
    f = funding()
    days = pd.date_range('2022-01-01', periods=5, tz='UTC')
    good = funding_windows(f, days)
    assert bool(good.funding_interval_complete.iloc[1])
    bad = funding_windows(f.drop(index=5), days)
    assert not bool(bad.funding_interval_complete.iloc[1])


def test_funding_four_hour_and_jitter_valid():
    f = funding(every=4)
    f.calc_time_ms += np.arange(len(f)) % 3
    d = funding_windows(f, pd.date_range('2022-01-01', periods=5, tz='UTC'))
    assert bool(d.funding_interval_complete.iloc[1])


def test_daily_funding_features_do_not_inspect_future_events():
    f = funding()
    days = pd.date_range('2022-01-01', periods=5, tz='UTC')
    full = funding_windows(f, days)
    past = funding_windows(f[f.calc_time_ms < T + 3 * 86400000], days)
    pd.testing.assert_series_equal(full.funding.iloc[:3], past.funding.iloc[:3])
    pd.testing.assert_series_equal(full.complete_funding.iloc[:3], past.complete_funding.iloc[:3])


def test_midnight_funding_belongs_to_old_execution_quantity():
    f = funding()
    days = pd.date_range('2022-01-01', periods=5, tz='UTC')
    # Day Jan 2 execution is 00:01: events Jan 2 08/16 and Jan 3 00 are owned.
    f.loc[f.calc_time_ms == T + 2 * 86400000, 'last_funding_rate'] = .001
    q = funding_windows(f, days)
    assert q.mark_funding_per_unit.iloc[1] == pytest.approx(.12)


def test_past_mark_is_strict_and_gaps_not_carried():
    events = pd.DataFrame(dict(calc_time_ms=[T + 120000, T + 120001]))
    marks = pd.DataFrame(dict(available_us=[(T + 60000) * 1000, (T + 120000) * 1000], close=[100., 200.]))
    result = mark_funding(events, marks)
    assert list(result.past_mark_price) == [100., 200.]
    missing = mark_funding(events, marks.iloc[:1])
    assert np.isnan(missing.past_mark_price.iloc[1])


def test_local_checksum_and_zip_member(tmp_path):
    p = tmp_path / 'BTCUSDT-1m-2022-01.zip'
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr(p.stem + '.csv', prices(2).to_csv(index=False, header=False))
    Path(str(p) + '.CHECKSUM').write_text(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name)
    assert verify_local(p)['bytes'] == p.stat().st_size
    p.write_bytes(p.read_bytes() + b'corrupt')
    with pytest.raises(ValueError): verify_local(p)


def test_funding_urls_not_fapi_or_wrong_archive():
    assert '/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2022-01.zip' in Job('BTCUSDT', 'fundingRate', 2022, 1).url
    assert '/premiumIndexKlines/' in Job('BTCUSDT', 'premiumIndexKlines', 2022, 1).url


@pytest.mark.parametrize('end', ['2026-03-01', '2026-08-31', '2026-09-30'])
def test_locked_intersection_blocked(monkeypatch, end):
    monkeypatch.setenv('END_DATE', end)
    with pytest.raises(ValueError, match='LOCKED'):
        bounds()


def test_reordered_price_header_rejected(tmp_path):
    import zipfile
    from pipeline.normalize import numeric_csv
    p=tmp_path/'bad-header.zip'
    header='open_time,open,high,low,close,volume,close_time,count,quote_volume,taker_buy_volume,taker_buy_quote_volume,ignore'
    with zipfile.ZipFile(p,'w') as z:
        z.writestr('data.csv',header+'\n1640995200000,100,101,99,100,1,1640995259999,1,100,0,0,0\n')
    with pytest.raises(ValueError,match='header'): numeric_csv(p)
