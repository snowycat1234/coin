"""Pinned source admission only. No historical scores or basket evaluation.

Complete means complete relative to the immutable retrieved project/archive
observation set. It is deliberately not an independent provider-completeness,
historical arrival-time, rate-unit, or actual charge-time certification.
"""
from __future__ import annotations
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile
from datetime import datetime, timezone
import numpy as np
from core import DAY, SYMBOLS, EventStream

HERE = Path(__file__).resolve().parent
PREP = Path(os.environ.get('FUNDING_RANK_PREPARATION_DIR',
            str(HERE.parent / 'coin_funding_rank_discriminator_20261013'))).resolve()
ROOT = PREP / 'inputs_restored'
PINS = {
    'FUNDING_DIRECTION_INPUTS.zip': ('0d2cf51769f2c9444c83b1715c5a6fd730d282e96cc4e84d1feaecf482ffdcd2', 389393),
    'CORE5_WARMUP_MASKS.npz': ('13d2cd62d6baf3059d991c11f2d2bd887a6faf571c206b11c4b3ba1e8a438bb2', 5980),
    'Y2024_TARGETS.npz': ('4f3b615b524de3220df3c10595ba2a7723f6e62dcff59b31ed82cb9476a9b5d5', 79421),
}
MEMBERS = {
    'Y2023.npz': ('1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f', 109106),
    'Y2025.npz': ('88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add', 131057),
    'Y2023_RAW_EVENTS.json': ('1b86be73f82c3800eead9d527fbdb35c671a93f00ca69d825593d8c1e84eb8e6', 303444),
    'Y2025_RAW_EVENTS.json': ('40d78f2d1650c8b18e7086b3714c857617756597832e057d4207d8d00aea06cf', 305896),
    'PREPARATION.json': ('c24bf0885bdc80ce8c161180099ffca5d3901db630f74b0f2c0be75f780faf47', 985184),
}
PROJECTION_PIN = ('cbe2417ee46c0e37a3e23f4126b89f3f1d84fc52223a68e802489fa13c79bc65', 315881)
EXPORT_MANIFEST_PIN = ('98b2a7dc188b5a93d036d80568e5ff119e5dd7be40bb3fd184a96fd7f97a0b68', 1260)
AUTHORITY = 'EXACT_PINNED_RETRIEVED_PROJECT_ARCHIVE_EVENT_SET_ONLY_PROVIDER_COMPLETENESS_UNCERTIFIED'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked(path, pin):
    raw = Path(path).read_bytes()
    assert len(raw) == pin[1] and sha(raw) == pin[0], str(path)
    return raw


def calendar(year):
    return tuple(int(datetime(y, 1, 1, tzinfo=timezone.utc).timestamp()) * 1_000_000
                 for y in (year, year + 1))


def ready200(t, p):
    out = np.zeros(p.shape, bool)
    for k in range(199, len(t)):
        if np.all(np.diff(t[k-199:k+1]) == DAY):
            h = p[k-199:k+1]
            out[k] = np.all(np.isfinite(h) & (h > 0), axis=0)
    return out


def certificate(times, lower, upper):
    """Materialize exact IDs from a hash-verified canonical reference scope.

    The enclosing source/producer certificate must already declare this scope;
    this function does not infer events, an expected cadence, or a provider set.
    An empty source day is UNKNOWN (not a zero-funding day).
    """
    return {d: times[(times >= d) & (times < d + DAY)].tolist()
            for d in range(lower, upper, DAY)
            if np.any((times >= d) & (times < d + DAY))}


def sealed_stream(item, lower, upper, provenance):
    times = np.asarray(item['times'], dtype=np.int64)
    rates = np.asarray(item['rates'], dtype=float)
    normalized = np.asarray(item['hours'], dtype=float)
    assert np.isfinite(rates).all() and np.isfinite(normalized).all()
    assert (normalized > 0).all() and np.all(np.diff(times) > 0)
    # The sealed transfer field is retained as metadata. Without independently
    # restored literal raw CSV authority it is not promoted to raw reported h.
    return EventStream(times, rates, np.full(len(times), np.nan),
                       certificate(times, lower, upper), normalized, provenance)


def load():
    for n, pin in PINS.items():
        checked(ROOT/n, pin)
    checked(HERE/'Y2021_RAW_EVENTS_PROJECTED.json', PROJECTION_PIN)
    checked(HERE/'TEMPORAL_FEATURE_SOURCE.zip',
            ('bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30', 2246454))
    cubes, raw_members = {}, {}
    with zipfile.ZipFile(ROOT/'FUNDING_DIRECTION_INPUTS.zip') as z:
        assert set(z.namelist()) == set(MEMBERS) and z.testzip() is None
        for n, pin in MEMBERS.items():
            raw = z.read(n)
            assert len(raw) == pin[1] and sha(raw) == pin[0], n
            if n in ('Y2023.npz', 'Y2025.npz'):
                with np.load(io.BytesIO(raw), allow_pickle=False) as a:
                    assert tuple(a['symbol_order']) == SYMBOLS
                    t, p = a['close_available_us'].copy(), a['close'].copy()
                assert t.dtype == np.int64 and p.shape == (len(t), 5)
                assert np.all(np.diff(t) == DAY)
                cubes[n] = (t, p, ready200(t, p))
            else:
                raw_members[n] = json.loads(raw)
    prep = raw_members['PREPARATION.json']
    # Read ONLY source identity/declared source coverage, not prior strategy
    # targets, risk records, rewards or direction counts in this old receipt.
    old_sources = {y: prep['years'][y]['source'] for y in ('2023', '2025')}
    for y in ('2023', '2025'):
        assert prep['years'][y]['RAW_EVENTS_SHA256'] == MEMBERS[f'Y{y}_RAW_EVENTS.json'][0]
        assert prep['years'][y]['status'] == 'PASS_SOURCE_COVERAGE_CAUSAL_TARGETS'
    streams, authority = {}, {}
    p21 = json.loads((HERE/'Y2021_RAW_EVENTS_PROJECTED.json').read_bytes())
    for year in (2021, 2023, 2025):
        lo, hi = calendar(year)
        items = p21 if year == 2021 else raw_members[f'Y{year}_RAW_EVENTS.json']
        assert set(items) == set(SYMBOLS)
        lower = lo - (23 if year == 2021 else 31) * DAY
        scope_hi = hi if year == 2021 else hi + DAY
        streams[year] = [sealed_stream(items[s], lower, scope_hi,
                         'SEALED_ORIGINAL_TRANSFER_FIELD_ONLY_RAW_REPORTED_INTERVAL_UNPROVEN')
                         for s in SYMBOLS]
        full_count = sum(int(((s.times >= lo) & (s.times < hi)).sum()) for s in streams[year])
        assert full_count == 5475
        if year == 2021:
            # Exact original transfer member seals and projection recipe/receipt.
            r = json.loads((HERE/'Y2021_PROJECTION_RECEIPT.json').read_bytes())
            assert r['projected_SHA256'] == PROJECTION_PIN[0]
            assert r['full_year_events'] == full_count
            authority[year] = {'projection_receipt': 'Y2021_PROJECTION_RECEIPT.json',
                               'source_archive_sha256': r['source_archive_SHA256']}
        else:
            authority[year] = {'sealed_source': old_sources[str(year)],
                               'sealed_raw_member_sha256': MEMBERS[f'Y{year}_RAW_EVENTS.json'][0]}
    # 2024 source export was matched row-for-row against the old hash-bound
    # full2024 + warmup reference, with archive/member identities retained.
    epath = HERE/'export2024'
    manifest_raw = checked(epath/'PUBLIC_MANIFEST.json', EXPORT_MANIFEST_PIN)
    manifest = json.loads(manifest_raw)
    for n, pin in manifest['files'].items():
        checked(epath/n, (pin['sha256'], pin['bytes']))
    cov = json.loads((epath/'COVERAGE.json').read_bytes())
    identity = json.loads((epath/'SOURCE_IDENTITY.json').read_bytes())
    assert cov['all_requested_reference_events_recovered'] is True
    assert cov['provider_complete_set_certified'] is False
    assert cov['warmup_reference_missing'] == cov['year2024_reference_missing'] == 0
    body = gzip.decompress((epath/'EVENTS.jsonl.gz').read_bytes())
    extraction = json.loads((epath/'EXTRACTION_RECEIPT.json').read_bytes())
    assert sha(body) == extraction['uncompressed_jsonl_sha256']
    assert len(body) == extraction['uncompressed_jsonl_bytes']
    rows = [json.loads(line) for line in body.splitlines()]
    assert len(rows) == cov['total_events'] == 5820
    assert len({(r['symbol'], r['event_us']) for r in rows}) == len(rows)
    for r in rows:
        assert r['symbol'] in SYMBOLS and r['source_id'] in identity['sources']
        assert isinstance(r['source_row'], int) and r['source_row'] >= 0
        value = float.fromhex(r['source_numeric_float64_hex'])
        assert np.isfinite(value) and value.hex() == r['normalized_float64_hex']
        assert value == r['existing_normalized_rate']
        if r['raw_rate_text'] is not None:
            assert float(r['raw_rate_text']) == value
        h = r['source_reported_interval_hours']
        assert h is None or (np.isfinite(h) and h > 0)
    for group in cov['groups']:
        g = [r for r in rows if r['symbol'] == group['symbol']
             and datetime.fromtimestamp(r['event_us']/1e6, timezone.utc).strftime('%Y-%m') == group['month']]
        gb = b''.join((json.dumps(r, sort_keys=True, separators=(',', ':'))+'\n').encode() for r in g)
        assert len(g) == group['event_count'] and sha(gb) == group['group_sha256']
        assert group['missing_from_hash_bound_existing_reference'] == group['duplicates'] == 0
    streams[2024] = []
    for s in SYMBOLS:
        g = sorted((r for r in rows if r['symbol'] == s), key=lambda r:r['event_us'])
        t = np.array([r['event_us'] for r in g], dtype=np.int64)
        rate = np.array([float.fromhex(r['source_numeric_float64_hex']) for r in g])
        h = np.array([np.nan if r['source_reported_interval_hours'] is None else r['source_reported_interval_hours'] for r in g])
        normalized = np.array([r['existing_normalized_interval_hours'] for r in g])
        streams[2024].append(EventStream(t, rate, h,
            certificate(t, cov['start_inclusive_us'], cov['end_exclusive_us']), normalized,
            'RAW_CSV_H2_REPORTED_HOURS_ELSE_UNKNOWN_ORIGINAL_NORMALIZED_FIELD_SEPARATE'))
    # Independent shared-source overlap: all 330 Dec2023 warmup observations
    # match the already sealed 2023 stream exactly in timestamp and raw rate.
    january,_=calendar(2024)
    for old,new in zip(streams[2023],streams[2024]):
        keep=new.times<january; at=new.times[keep]
        k=np.searchsorted(old.times,at)
        assert np.array_equal(old.times[k],at)
        assert np.array_equal(old.rates[k],new.rates[keep])
    authority[2024] = {'source_export_commit':'44d38d3161b8a6ac11cf5c6a85a1b91dc50e5460',
                      'source_export_path':'research/funding-rank-input-recovery-20261013',
                      'source_identity_sha256':manifest['files']['SOURCE_IDENTITY.json']['sha256'],
                      'coverage_sha256':manifest['files']['COVERAGE.json']['sha256'],
                      'source_reported_interval_null_events':3060}
    # Original all-five mask authority: exact saved2021 masks, original2024
    # past31 covariance parity, and previously independently reviewed producer.
    t3,p3,m3=cubes['Y2023.npz']; t5,p5,m5=cubes['Y2025.npz']
    with np.load(ROOT/'CORE5_WARMUP_MASKS.npz',allow_pickle=False) as a:
        assert tuple(a['symbol_order']) == SYMBOLS
        d=a['decision_us']; k=np.searchsorted(t3,d); assert np.array_equal(t3[k],d)
        saved=np.column_stack([a[s+'_200close'] for s in SYMBOLS])
        assert np.array_equal(m3[k],saved) and np.array_equal(saved.all(1),a['CORE5_200close'])
    with np.load(ROOT/'Y2024_TARGETS.npz',allow_pickle=False) as a:
        assert tuple(a['symbol_order']) == SYMBOLS
        d=a['decision_us']; saved_cov=a['annual_covariance']
    cov_check=[]
    for at in d:
        k=int(np.searchsorted(t5,at)); assert t5[k] == at
        past=p5[k-30:k+1];returns=np.diff(past,axis=0)/past[:-1]
        cov_check.append(np.cov(returns,rowvar=False,ddof=1)*365)
    assert np.array_equal(np.array(cov_check),saved_cov)
    datasets = {y: (*cubes['Y2023.npz' if y in (2021,2023) else 'Y2025.npz'], streams[y])
                for y in (2021,2023,2024,2025)}
    return datasets, authority


def inventory():
    datasets, authority = load()
    years = {}
    for year,(t,p,mask,streams) in datasets.items():
        start,end=calendar(year); days=np.arange(start,end,DAY,dtype=np.int64)
        k=np.searchsorted(t,days); assert np.array_equal(t[k],days)
        source_days=[]
        for d in days:
            # Boolean source coverage QA only; no rate aggregate/price score.
            source_days.append(all(all(q in s.complete_day_event_ids
                                  for q in range(int(d)-22*DAY,int(d)-DAY,DAY)) for s in streams))
        years[str(year)] = {
            'calendar_us':[start,end], 'days':len(days),
            'price_member':'Y2023.npz' if year in (2021,2023) else 'Y2025.npz',
            'original_allfive200_ready_days':int(mask[k].all(1).sum()),
            'funding_window_source_id_coverage_days':int(sum(source_days)),
            'funding_window_source_id_unknown_days':int(len(days)-sum(source_days)),
            'events_per_asset':[len(s.times) for s in streams],
            'raw_reported_interval_unknown_events':[int(np.isnan(s.hours).sum()) for s in streams],
            'authority':authority[year]}
    return {'status':'PASS_HASH_BOUND_PROJECT_SOURCE_ADMISSION_CONDITIONAL_ONLY',
            'historical_status':'NO_GO_PENDING_INDEPENDENT_REVIEW_AND_EXACT_PARENT_GO',
            'completeness_authority':AUTHORITY,'provider_complete_set_certified':False,
            'historical_publication_time_certified':False,'funding_unit_certified':False,
            'actual_charge_time_certified':False,'funding_scale':'CONDITIONAL_RAW_FRACTION1',
            '2024_warmup_vs2023_sealed_stream':'330_TIMESTAMP_AND_RAW_RATE_OBSERVATIONS_EXACT',
            'interval_policy':'Unknown raw reported intervals remain NaN; normalized metadata is separate and never substitutes or weights rates.',
            'years':years,'historical_basket_evaluations':0,'wallets':0,'fits':0,'provider_requests':0}


if __name__ == '__main__':
    result=inventory(); path=HERE/'SOURCE_BINDING_RECEIPT.json'; assert not path.exists()
    path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))
