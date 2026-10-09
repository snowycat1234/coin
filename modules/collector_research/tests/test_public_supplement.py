"""Offline fixtures certify adapter behavior, never real venue reachability."""
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
import requests
from pipeline import public_supplement as supplement

START = 1751328000000
DAY = 86400000


def encoded(value):
    return json.dumps(value).encode()


def job(provider='okx', count=3):
    return replace(supplement.daily_jobs(provider)[0], end_ms=START + count * DAY)


def metadata(j):
    if j.provider == 'bybit':
        base = j.instrument_id.removesuffix('USDT')
        row = dict(symbol=j.instrument_id, baseCoin=base, quoteCoin='USDT',
                   contractType='LinearPerpetual', settleCoin='USDT')
        return encoded(dict(retCode=0, result=dict(list=[row])))
    base = j.instrument_id.split('-')[0]
    row = dict(instId=j.instrument_id, instType='SWAP', ctType='linear', ctVal='10',
               ctMult='1', ctValCcy=base, settleCcy='USDT')
    return encoded(dict(code='0', data=[row]))


def candles(j, stamps=None, confirmed='1'):
    stamps = stamps if stamps is not None else range(j.start_ms, j.end_ms, j.step)
    rows = [[str(stamp), '2', '3', '1', '2.5'] for stamp in reversed(list(stamps))]
    for row in rows:
        if j.kind == 'trade':
            row.extend(['10', '100', '250'] if j.provider == 'okx' else ['100', '250'])
        if j.provider == 'okx':
            row.append(confirmed)
    if j.provider == 'okx':
        return encoded(dict(code='0', data=rows))
    return encoded(dict(retCode=0, result=dict(symbol=j.instrument_id,
                                             category='linear', list=rows)))


class Response:
    def __init__(self, content, status=200):
        self.content, self.status_code, self.headers = content, status, {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, size):
        yield self.content


class Session:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        assert self.responses, 'Unexpected network request'
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    monkeypatch.setattr(supplement.time, 'sleep', lambda seconds: None)


def load(result):
    path = Path(result['manifest'])
    return json.loads(path.read_text()), path.parent


def test_complete_preserves_raw_units_clocks_and_resume_without_network(tmp_path):
    j = job()
    source = candles(j)
    session = Session(Response(metadata(j)), Response(source))
    result = supplement.collect(j, tmp_path, supplement.Budget(), session)
    assert result['status'] == 'COMPLETE' and result['coverage']['observed_bars'] == 3
    manifest, directory = load(result)
    assert manifest['binding']['dataset_role'] == 'ALTERNATIVE_VENUE_ROBUSTNESS_ONLY'
    assert manifest['binding']['replaces_original_observations'] is False
    assert result['frozen_selector_certified'] is False
    rows = [json.loads(line) for line in (directory / 'bars.jsonl').read_text().splitlines()]
    assert [row['open_ms'] for row in rows] == [START, START + DAY, START + 2 * DAY]
    assert rows[0]['close'] == '2.5' and rows[0]['native_volume_fields'] == ['10', '100', '250']
    assert rows[0]['raw_sha256'] == hashlib.sha256(source).hexdigest()
    assert rows[0]['historical_available_ms'] is None
    assert rows[0]['available_ms'] == rows[0]['received_ms'] > j.end_ms
    assert rows[0]['close_ms_exclusive'] == START + DAY
    assert result['identity']['contract_value'] == '10'
    assert result['identity']['metadata_scope'] == 'CURRENT_NOT_HISTORICAL_CERTIFICATION'
    assert session.calls[1][1]['params']['bar'] == '1Dutc'
    assert all(call[1]['allow_redirects'] is False for call in session.calls)
    assert supplement.collect(j, tmp_path, supplement.Budget(), Session())['status'] == 'COMPLETE'


@pytest.mark.parametrize('ref,native,units', [('1000PEPEUSDT', '1000PEPEUSDT', '1000'),
                                           ('1000SATSUSDT', '10000SATSUSDT', '10000')])
def test_bybit_multiplier_remains_native_not_binance(ref, native, units):
    j = next(j for j in supplement.daily_jobs('bybit') if j.reference_symbol == ref)
    identity = supplement.instrument_identity(j, metadata(j))
    assert identity['instrument_id'] == native
    assert identity['price_underlying_multiplier'] == units
    assert identity['reference_price_underlying_multiplier'] == '1000'
    assert identity['prices_rescaled'] is False
    rows = supplement.normalize(j, candles(j), identity, j.end_ms + 1, 'a' * 64)
    assert rows[0]['close'] == '2.5'


@pytest.mark.parametrize('status,expected', [(403, 'PERMISSION_DENIED'),
                                           (451, 'PERMISSION_DENIED'), (429, 'RATE_LIMITED'),
                                           (404, 'HTTP_FAILURE'), (302, 'HTTP_FAILURE')])
def test_terminal_http_failure_is_not_retention_or_provider_fallback(tmp_path, status, expected):
    session = Session(Response(b'denied or missing', status))
    result = supplement.collect(job(), tmp_path, supplement.Budget(), session)
    assert result['status'] == expected and len(session.calls) == 1
    assert result['coverage']['missing_bars'] == 3
    manifest, directory = load(result)
    assert (directory / manifest['requests'][0]['raw_file']).read_bytes() == b'denied or missing'
    assert supplement.collect(job(), tmp_path, supplement.Budget(), Session())['status'] == expected
    if status in (403, 451, 429):
        other = replace(job(), reference_symbol='WLDUSDT', instrument_id='WLD-USDT-SWAP')
        assert supplement.collect(other, tmp_path, supplement.Budget(), Session())[
            'status'] == 'PERMISSION_DENIED'


def test_bounded_retry_and_partial_page_resume(tmp_path):
    j = job(count=184)
    first = candles(j, range(START, START + 100 * DAY, DAY))
    session = Session(Response(metadata(j)), Response(first), requests.Timeout('fixture'),
                      requests.Timeout('fixture again'))
    result = supplement.collect(j, tmp_path, supplement.Budget(), session)
    assert result['status'] == 'TRANSPORT_FAILURE'
    assert result['coverage']['observed_bars'] == 100 and len(session.calls) == 4
    assert supplement.collect(j, tmp_path, supplement.Budget(), Session())[
        'status'] == 'RETRY_EXHAUSTED'
    assert supplement.collect(j, tmp_path, supplement.Budget(), Session())[
        'coverage']['observed_bars'] == 100


def test_resume_after_invocation_budget_skips_good_pages(tmp_path):
    j = job(count=184)
    session = Session(Response(metadata(j)),
                      Response(candles(j, range(START, START + 100 * DAY, DAY))))
    result = supplement.collect(j, tmp_path, supplement.Budget(max_requests=2), session)
    assert result['status'] == 'BUDGET_EXHAUSTED' and result['coverage']['observed_bars'] == 100
    tail = Session(Response(candles(j, range(START + 100 * DAY, j.end_ms, DAY))))
    resumed = supplement.collect(j, tmp_path, supplement.Budget(), tail)
    assert resumed['status'] == 'COMPLETE' and resumed['coverage']['observed_bars'] == 184
    assert len(tail.calls) == 1 and tail.calls[0][1]['params']['limit'] == 84


def test_server_error_retry_is_bounded(tmp_path):
    j = job()
    session = Session(Response(b'error', 503), Response(metadata(j)), Response(candles(j)))
    result = supplement.collect(j, tmp_path, supplement.Budget(), session)
    assert result['status'] == 'COMPLETE' and len(session.calls) == 3


@pytest.mark.parametrize('stamps', [[], [START, START + 2 * DAY]])
def test_empty_or_gapped_history_does_not_invent_retention(tmp_path, stamps):
    j = job()
    result = supplement.collect(j, tmp_path, supplement.Budget(),
                                Session(Response(metadata(j)), Response(candles(j, stamps))))
    assert result['status'] == 'INCOMPLETE_COVERAGE'
    assert result['coverage']['missing_bars'] == 3 - len(stamps)
    if stamps:
        assert result['coverage']['missing_ranges_ms_exclusive'] == [[START + DAY, START + 2 * DAY]]


def test_documented_retention_and_minute_live_deferral_do_no_network(tmp_path):
    j = replace(job(), retention_start_ms=START + DAY,
                retention_evidence='Synthetic explicit provider retention statement')
    result = supplement.collect(j, tmp_path, supplement.Budget(), Session())
    assert result['status'] == 'HISTORICAL_RETENTION_MISSING'
    for provider in ('okx', 'bybit'):
        mark = supplement.mark_job(provider)
        assert mark.count == 44640
        assert supplement.collect(mark, tmp_path, supplement.Budget(), Session())[
            'status'] == 'NOT_RUN_MINUTE_HISTORY_NOT_AUTHORIZED'
        mark = replace(mark, end_ms=mark.start_ms + 3 * mark.step)
        identity = supplement.instrument_identity(mark, metadata(mark))
        rows = supplement.normalize(mark, candles(mark), identity, mark.end_ms, 'a' * 64)
        assert rows[0]['kind'] == 'mark' and rows[0]['native_volume_fields'] is None
        assert supplement.coverage(mark, rows)['status'] == 'COMPLETE'
        assert 'mark' in supplement.bars_request(mark, mark.start_ms, mark.end_ms)[0]


@pytest.mark.parametrize('mutation', ['raw', 'normalized', 'binding'])
def test_tampered_cache_is_refused_before_request(tmp_path, mutation):
    j = job()
    result = supplement.collect(j, tmp_path, supplement.Budget(),
                                Session(Response(metadata(j)), Response(candles(j))))
    manifest, directory = load(result)
    if mutation == 'raw':
        (directory / manifest['requests'][0]['raw_file']).write_bytes(b'tampered')
    elif mutation == 'normalized':
        (directory / 'bars.jsonl').write_bytes(b'tampered')
    else:
        manifest['binding']['job']['market'] = 'spot'
        (directory / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='checksum|binding'):
        supplement.collect(j, tmp_path, supplement.Budget(), Session())


def test_invalid_schema_timestamps_prices_products_and_limits(tmp_path):
    j = job('bybit')
    identity = supplement.instrument_identity(j, metadata(j))
    for raw in (b'html', candles(j, [START, START]), candles(j, [START + 1]),
                candles(j).replace(b'"2.5"', b'"NaN"'),
                candles(j).replace(b'WIFUSDT', b'WLDUSDT')):
        with pytest.raises(supplement.Failure):
            supplement.normalize(j, raw, identity, j.end_ms, 'a' * 64)
    with pytest.raises(supplement.Failure, match='identity'):
        supplement.normalize(j, candles(j), {**identity, 'market': 'spot'}, j.end_ms, 'a' * 64)
    with pytest.raises(ValueError, match='Spot'):
        replace(j, market='spot', kind='mark')
    with pytest.raises(ValueError, match='June'):
        replace(j, end_ms=1772323200000)
    with pytest.raises(ValueError, match='Retention'):
        replace(j, retention_start_ms=START + DAY)
    with pytest.raises(ValueError, match='budget'):
        supplement.Budget(max_requests=21)
    result = supplement.collect(job(), tmp_path, supplement.Budget(max_response_bytes=2),
                                Session(Response(b'oversized')))
    assert result['status'] == 'RESPONSE_LIMIT'


def test_unconfirmed_rows_never_count_as_complete(tmp_path):
    j = job()
    result = supplement.collect(j, tmp_path, supplement.Budget(),
                                Session(Response(metadata(j)), Response(candles(j, confirmed='0'))))
    assert result['coverage']['observed_bars'] == 0


def test_june_extension_reuses_metadata_and_h2_without_new_requests(tmp_path):
    j = job(count=184)
    before = supplement.collect(j, tmp_path, supplement.Budget(), Session(
        Response(metadata(j)), Response(candles(j, range(START, START + 100 * DAY, DAY))),
        Response(candles(j, range(START + 100 * DAY, j.end_ms, DAY)))))
    prior, old_dir = load(before)
    old_bytes = (old_dir / 'bars.jsonl').read_bytes()
    june = replace(j, start_ms=supplement.WARMUP_START, end_ms=START)
    budget = supplement.Budget(max_requests=22, requests_used=17)
    session = Session(Response(candles(june)))
    result = supplement.extend_june_warmup(before['manifest'], tmp_path, budget, session)
    assert result['status'] == 'COMPLETE' and result['coverage']['observed_bars'] == 214
    assert budget.requests_used == 18 and len(session.calls) == 1
    assert session.calls[0][1]['params']['limit'] == 30
    assert (old_dir / 'bars.jsonl').read_bytes() == old_bytes
    manifest, directory = load(result)
    assert manifest['binding']['parent_binding'] == prior['binding']
    combined = (directory / 'bars.jsonl').read_bytes()
    assert b''.join(combined.splitlines(keepends=True)[30:]) == old_bytes
    assert supplement.extend_june_warmup(before['manifest'], tmp_path, budget, Session())[
        'status'] == 'COMPLETE'


def test_june_extension_denial_preserves_retained_h2(tmp_path):
    j = job(count=184)
    before = supplement.collect(j, tmp_path, supplement.Budget(), Session(
        Response(metadata(j)), Response(candles(j, range(START, START + 100 * DAY, DAY))),
        Response(candles(j, range(START + 100 * DAY, j.end_ms, DAY)))))
    result = supplement.extend_june_warmup(before['manifest'], tmp_path,
                                          supplement.Budget(max_requests=22),
                                          Session(Response(b'denied', 403)))
    assert result['status'] == 'PERMISSION_DENIED'
    assert result['coverage']['observed_bars'] == 184 and result['coverage']['missing_bars'] == 30
