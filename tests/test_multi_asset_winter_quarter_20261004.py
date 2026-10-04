"""One winter calendar/metadata-routing case; no market arrays or finance calls."""
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

import pytest

from scripts.investment import multi_asset_financial_audit as audit


def test_winter_calendar_keeps_exact_accepted_warmup_roles(tmp_path):
    spec = dict(start='2024-12-01T00:00:00+00:00', end_exclusive='2025-03-01T00:00:00+00:00',
        period_days=90, account_path='CONTINUOUS_SHARED_ACCOUNT_DEC_FEB_90D',
        data_role='SEEN_DEVELOPMENT_CONTINUOUS_NEXT_QUARTER_MANIFEST')
    scope = audit.calendar_scope(spec)
    assert scope['required_minutes'] == 129600 and scope['period_days'] == 90
    assert scope['score_months'] == ['2024-12', '2025-01', '2025-02']
    assert audit.next_month(datetime(2024, 12, 1, tzinfo=UTC)) == datetime(2025, 1, 1, tzinfo=UTC)
    assert audit.next_month(datetime(2025, 2, 1, tzinfo=UTC)) == datetime(2025, 3, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match='winter shared-wallet'):
        audit.calendar_scope(dict(spec, period_days=91))
    with pytest.raises(ValueError, match='seen scopes'):
        audit.calendar_scope(dict(spec, end_exclusive='2025-02-28T00:00:00+00:00'))

    selected = ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', '1000PEPEUSDT', 'XRPUSDT',
        'WIFUSDT', 'WLDUSDT', 'DOGEUSDT', '1000SATSUSDT', 'ORDIUSDT']
    symbols = sorted(selected)
    def put(name, value):
        path = tmp_path / (name + '.json')
        path.write_text(json.dumps(value, allow_nan=False), encoding='utf-8')
        return dict(path=str(path), sha256=audit.sha(path))
    def record(kind, symbol, interval, month):
        name = f'{kind}-{symbol}-{interval}-{month}'
        return dict(kind=kind, symbol=symbol, interval=interval, month=month,
            normalized_path=str(tmp_path / 'UNOPENED_SYNTHETIC_SOURCE' / (name + '.parquet')),
            normalized_sha256=hashlib.sha256(name.encode()).hexdigest(), normalized_bytes=64, rows=1)
    def source_hashes(rows):
        return {r['normalized_path']: r['normalized_sha256'] for r in rows}
    task_refs = {}
    def capability(name, **fields):
        task_id = hashlib.sha256(name.encode()).hexdigest()[:32]
        task_refs[task_id] = put(name + '-synthetic-task', dict(id=task_id,
            status='completed', exit_code=0, synthetic_fixture_only=True))
        return put(name, dict(source_only=True, actual_exit_code=0,
            binding=dict(task_id=task_id), **fields))
    class MetadataGuard:
        reads = 0
        def small(self, path, digest):
            path = Path(path)
            assert path.is_relative_to(tmp_path) and audit.sha(path) == digest
            self.reads += 1
            return json.loads(path.read_bytes()), digest
        def closed(self, task_id):
            task, _ = self.small(**dict(path=task_refs[task_id]['path'], digest=task_refs[task_id]['sha256']))
            assert task['synthetic_fixture_only'] and task['status'] == 'completed' and task['exit_code'] == 0
            return dict(task_id=task_id, synthetic_fixture_only=True, status='completed', exit_code=0)

    daily = [record('klines', s, '1d', '2024-' + m) for s in symbols
        for m in ('02', '03', '04', '05', '06', '07', '08')]
    controls = [r for r in daily if r['symbol'] in ('BTCUSDT', 'ETHUSDT')]
    pool = put('synthetic-pool', dict(status='POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS',
        score_payloads_read=0, symbols=selected, source_records=daily))
    months = ['2024-09', '2024-10', '2024-11']
    manifest_statuses = ['PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS',
        'PASS_D051_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS',
        'PASS_D054_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS']
    cap_statuses = ['PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY',
        'PASS_D051_FIXED_POOL_OCTOBER_SOURCE_FORMAT_ONLY', 'PASS_D054_FIXED_POOL_NOVEMBER_SOURCE_FORMAT_ONLY']
    refs, caps, old_market = [], [], []
    for month, mstatus, cstatus in zip(months, manifest_statuses, cap_statuses, strict=True):
        first = datetime.fromisoformat(month + '-01T00:00:00+00:00')
        rows = [record(k, s, i, month) for s in symbols
            for k, i in (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None))]
        cap = capability(month + '-cap', status=cstatus, pool_receipt_sha256=pool['sha256'],
            normalized_source_hashes=source_hashes(rows + (daily if not caps else [])))
        manifest = dict(status=mstatus, symbols=symbols, checksummed_source_format_verified=True,
            start_us=int(first.timestamp()) * 1_000_000,
            end_us=int(audit.next_month(first).timestamp()) * 1_000_000,
            pool_receipt=pool, source_acceptance=cap, control_daily_records=controls, market_records=rows)
        if refs:
            manifest.update(warmup_manifest=refs[-1], warmup_source_acceptance=caps[-1],
                warmup_minute_records=[r for r in old_market if r['kind'] == 'klines'])
        refs.append(put(month + '-manifest', manifest)); caps.append(cap); old_market += rows
    warm_value = dict(status='PASS_D055_CONTINUOUS_91D_ACCEPTED_SOURCE_BINDING_NOT_ECONOMICS',
        source_only=True, checksummed_source_format_verified=True, start_us=1725148800000000,
        end_us=1733011200000000, days=91, symbols=symbols, selected_symbols=selected,
        pool_receipt=pool, monthly_manifests=refs, monthly_acceptances=caps,
        daily_records=daily, control_daily_records=controls, market_records=old_market,
        normalized_source_hashes=source_hashes(old_market + daily))
    warm_ref = put('synthetic-warm-composite', warm_value)

    # Only the small accepted D045 metadata bytes are copied. No source file,
    # archive, financial artifact, locked body or producer function is opened.
    old_path = Path(__file__).resolve().parents[1] / 'reports/fast_research/PERPETUAL_303D_INPUT_BINDING_20261003_V1.json'
    old_bytes = old_path.read_bytes()
    old_sha = '8b665b2829eafd192871fe4a3bc418dac1c202ed54f7d2d5494545fa6636fbfa'
    assert len(old_bytes) < 2_000_000 and hashlib.sha256(old_bytes).hexdigest() == old_sha
    copied_old = tmp_path / 'original-accepted-control-metadata.json'
    copied_old.write_bytes(old_bytes)
    original = json.loads(old_bytes)
    old_rows = {(r['kind'], r['symbol'], r['interval'], r['month']): r
        for r in original['source_files'].values()}
    score = [deepcopy(old_rows[(k, s, i, m)]) if s in ('BTCUSDT', 'ETHUSDT') else record(k, s, i, m)
        for m in scope['score_months'] for s in symbols
        for k, i in (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None))]
    quarter_cap = capability('winter-cap', status='PASS_D056_FIXED_POOL_WINTER_SOURCE_FORMAT_ONLY',
        pool_receipt_sha256=pool['sha256'], start_us=scope['start_us'], end_us=scope['end_us'],
        completed_files=90, newly_verified_files=72, reused_accepted_files=18,
        normalized_source_hashes=source_hashes(score), sources=score,
        reused_market_manifest=dict(path=str(copied_old), sha256=old_sha))
    warm_trade = [r for r in old_market if r['kind'] == 'klines']
    value = dict(status='PASS_D056_SELECTED_PORTFOLIO_WINTER_SOURCE_BINDING_NOT_ECONOMICS',
        source_only=True, checksummed_source_format_verified=True, start_us=scope['start_us'],
        end_us=scope['end_us'], days=90, score_months=scope['score_months'], symbols=symbols,
        selected_symbols=selected, pool_receipt=pool, source_acceptance=quarter_cap,
        warmup_manifest=warm_ref, warmup_source_acceptances=caps, market_records=score,
        daily_records=daily, control_daily_records=controls, warmup_minute_records=warm_trade,
        normalized_source_hashes=source_hashes(score + daily + warm_trade))
    guard = MetadataGuard()
    result, proofs = audit.winter_source_records(value, tuple(selected), guard, scope)
    assert len({r['normalized_path'] for r in result}) == 190 and len(proofs) == 4
    audit.winter_source_records(value, ('BTCUSDT', 'ETHUSDT'), guard, scope)
    missing = deepcopy(value)
    missing['warmup_minute_records'] = [r for r in warm_trade if not
        (r['month'] == '2024-11' and r['symbol'] == 'BTCUSDT')]
    with pytest.raises(ValueError, match='warmup alias retained'):
        audit.winter_source_records(missing, tuple(selected), guard, scope)
    replaced = deepcopy(value)
    replaced['warmup_minute_records'][0]['normalized_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='warmup alias retained'):
        audit.winter_source_records(replaced, tuple(selected), guard, scope)
    (tmp_path / 'winter_metadata_evidence.json').write_text(json.dumps(dict(
        scope='SYNTHETIC_CALENDAR_AND_METADATA_ROUTING_ONLY', period_days=90, minutes=129600,
        warmup_roles=100, score_roles=90, missing_or_replaced_warmup_rejected=True,
        original_small_metadata_sha256=old_sha, market_payloads_read=0, financial_case_calls=0,
        producer_loader_calls=0, source_QA_calls=0, training_calls=0)), encoding='utf-8')
