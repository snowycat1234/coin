"""Independent recorded-finance audit for one configured N-asset portfolio.

Reuse accepted Decimal journals and minute/day/month assertions without a new
account simulator. Read only this new producer's artifacts and the financially
necessary columns of its bound sources; no old QA/accounts, API or lock body.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
from datetime import UTC, datetime
from types import FunctionType, SimpleNamespace

import numpy as np
import polars as pl
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
MINUTE = 60_000_000
DAY = 86_400_000_000
STATUS = 'PASS_CONFIGURED_N_SHARED_PERPETUAL_RECORDED_ACCOUNTING_AND_TARGET_SCOPE_NOT_NATIVE_OR_APR'
REUSE = 'scripts/investment/audit_turtle_perpetual.py'
REUSE_SHA = '722e48ca19b924d15f8922c13aebf021db8e11145130a97dca4e930e2f93ae53'
PATCH = 'scripts/investment/audit_closing_exempt_research_v2.py'
PATCH_SHA = 'b42a92edee8fd93c2dba0f5d055caee70ef73680bf473af7881f39abbfec514b'
ACTUAL_STATUSES = {'COMPLETE_PREDECLARED_PORTFOLIO_CASES_NOT_CROSS_POOL_COMPARISON_OR_APR',
                   'COMPLETE_MULTI_ASSET_SHARED_CAPITAL_DEVELOPMENT_COMPARISON_NOT_APR'}
ALLOCATION_STRATEGIES = {
    'EQUAL': 'COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE',
    'INVERSE_VOL_30D': 'COIN_PAST30_INVERSE_VOL_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE',
}
SMA_POOL_STRATEGY = 'COIN_JESSE_SMA50_200_1D_USDM_CONFIGURED_POOL_ADAPTER'
MOMENTUM_POOL_STRATEGY = 'COIN_PAST30_ABSOLUTE_MOMENTUM_LONG_CASH_USDM_CONFIGURED_POOL_ADAPTER'


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def module(path, digest, name):
    p = ROOT / path
    need(not p.is_symlink() and sha(p) == digest, 'Exact reused independent source: ' + path)
    spec = importlib.util.spec_from_file_location(name, p)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def prepare_financial(symbols):
    """Only symbol globals change; the accepted closing journal/body is reused."""
    reuse = module(REUSE, REUSE_SHA, 'd050_recorded_financial_reuse')
    patch = module(PATCH, PATCH_SHA, 'd050_accepted_closing_predicate')
    base = patch.patched_base(reuse)
    namespace = dict(vars(base), SYMS=tuple(symbols))
    for name, value in vars(base).items():
        if isinstance(value, FunctionType):
            copied = FunctionType(value.__code__, namespace, value.__name__, value.__defaults__, value.__closure__)
            copied.__kwdefaults__ = value.__kwdefaults__
            namespace[name] = copied
    private = SimpleNamespace(**namespace)
    financial, proof = reuse.prepare_financial_only(private)
    proof.update(symbols=list(symbols), symbol_order_is_account_identity=True,
        independent_closing_journal_derivation=base._closing_journal_derivation,
        financial_function_bytecode_unchanged=True, original_module_globals_mutated=False,
        no_producer_finance_imported=True, full_market_intent_sizing_independently_rebuilt=False)
    return private, financial, proof


def next_month(first):
    """UTC month boundary, including December to January."""
    return first.replace(year=first.year + (first.month == 12), month=first.month % 12 + 1)


def calendar_scope(spec):
    """Authorized seen UTC months and the two fixed continuous quarters."""
    first = datetime.fromisoformat(spec['start'])
    last = datetime.fromisoformat(spec['end_exclusive'])
    need(first.tzinfo is not None and last.tzinfo is not None and
         first.utcoffset().total_seconds() == last.utcoffset().total_seconds() == 0 and
         (first.day, first.hour, first.minute, first.second, first.microsecond) == (1, 0, 0, 0, 0),
         'Complete UTC month starts; no truncated or shifted decision clock')
    if first == datetime(2024, 9, 1, tzinfo=UTC) and last == datetime(2024, 12, 1, tzinfo=UTC):
        need(spec['period_days'] == 91 and
             spec['account_path'] == 'CONTINUOUS_SHARED_ACCOUNT_SEP_NOV_91D' and
             spec['data_role'] == 'SEEN_DEVELOPMENT_CONTINUOUS_ACCEPTED_THREE_MONTH_MANIFEST',
             'Only the predeclared continuous shared-wallet path, without monthly reset')
        return dict(start=first.isoformat(), end_exclusive=last.isoformat(),
            start_us=int(first.timestamp()) * 1_000_000, end_us=int(last.timestamp()) * 1_000_000,
            period_days=91, score_month='2024-09..2024-11',
            score_months=['2024-09', '2024-10', '2024-11'], calendar_months=3,
            required_minutes=131040, period_id='2024-09_2024-11_91D', seen_development=True)
    if first == datetime(2024, 12, 1, tzinfo=UTC) and last == datetime(2025, 3, 1, tzinfo=UTC):
        need(spec['period_days'] == 90 and
             spec['account_path'] == 'CONTINUOUS_SHARED_ACCOUNT_DEC_FEB_90D' and
             spec['data_role'] == 'SEEN_DEVELOPMENT_CONTINUOUS_NEXT_QUARTER_MANIFEST',
             'Only the predeclared fresh winter shared-wallet quarter')
        return dict(start=first.isoformat(), end_exclusive=last.isoformat(),
            start_us=int(first.timestamp()) * 1_000_000, end_us=int(last.timestamp()) * 1_000_000,
            period_days=90, score_month='2024-12..2025-02',
            score_months=['2024-12', '2025-01', '2025-02'], calendar_months=3,
            warmup_months=['2024-09', '2024-10', '2024-11'],
            required_minutes=129600, period_id='2024-12_2025-02_90D', seen_development=True)
    need(first.year == 2024 and first.month in (9, 10, 11) and
         last == next_month(first), 'Only predeclared September-November seen scopes')
    days = (last - first).days
    return dict(start=first.isoformat(), end_exclusive=last.isoformat(),
        start_us=int(first.timestamp()) * 1_000_000, end_us=int(last.timestamp()) * 1_000_000,
        period_days=days, score_month=first.strftime('%Y-%m'),
        period_id=f'{first:%Y-%m}_{days}D', seen_development=True)


def continuous_source_records(value, symbols, guard, scope):
    """Verify three accepted metadata capabilities; never call the producer loader."""
    def metadata(reference):
        path = Path(reference['path'])
        return guard.small(path if path.is_absolute() else guard.project(str(path)), reference['sha256'])[0]
    def identity(reference):
        path = Path(reference['path'])
        return str(path if path.is_absolute() else ROOT / path), reference['sha256']
    def keyed(records, financial_identity=False):
        result = {}
        for row in records:
            key = row['kind'], row['symbol'], row.get('interval'), row['month']
            need(key not in result, 'Unique accepted source aliases in each metadata list')
            result[key] = ({k:row[k] for k in ('kind', 'symbol', 'interval', 'month',
                'normalized_path', 'normalized_sha256', 'normalized_bytes', 'rows')}
                if financial_identity else row)
        return result
    need(value['status'] == 'PASS_D055_CONTINUOUS_91D_ACCEPTED_SOURCE_BINDING_NOT_ECONOMICS' and
         value['source_only'] is True and value['checksummed_source_format_verified'] is True and
         (value['start_us'], value['end_us'], value['days']) == (scope['start_us'], scope['end_us'], 91),
         'Composite is accepted source metadata for exactly the continuous 91-day scope')
    refs, acceptance_refs = value['monthly_manifests'], value['monthly_acceptances']
    need(len(refs) == len(acceptance_refs) == 3, 'Exactly three ordered accepted monthly capabilities')
    manifests = [metadata(r) for r in refs]
    capabilities = [metadata(r) for r in acceptance_refs]
    pool = metadata(value['pool_receipt'])
    need(pool['status'] == 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS' and pool['score_payloads_read'] == 0 and
         value['selected_symbols'] == pool['symbols'] and
         (list(symbols) == pool['symbols'] or tuple(symbols) == ('BTCUSDT', 'ETHUSDT')) and
         len(value['symbols']) == len(set(value['symbols'])) == len(pool['symbols']) and
         set(value['symbols']) == set(pool['symbols']), 'Original July pool; catalogue set and account order are distinct')
    manifest_statuses = ['PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS',
        'PASS_D051_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS',
        'PASS_D054_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS']
    acceptance_statuses = ['PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY',
        'PASS_D051_FIXED_POOL_OCTOBER_SOURCE_FORMAT_ONLY', 'PASS_D054_FIXED_POOL_NOVEMBER_SOURCE_FORMAT_ONLY']
    all_market, certificates = [], []
    for month, manifest, capability, ref, acceptance_ref, mstatus, astatus in zip(
            scope['score_months'], manifests, capabilities, refs, acceptance_refs,
            manifest_statuses, acceptance_statuses, strict=True):
        first = datetime.fromisoformat(month + '-01T00:00:00+00:00')
        start, end = int(first.timestamp()) * 1_000_000, int(next_month(first).timestamp()) * 1_000_000
        need(manifest['status'] == mstatus and manifest['checksummed_source_format_verified'] is True and
             (manifest['start_us'], manifest['end_us']) == (start, end) and
             identity(manifest['pool_receipt']) == identity(value['pool_receipt']) and
             identity(manifest['source_acceptance']) == identity(acceptance_ref) and
             len(manifest['symbols']) == len(set(manifest['symbols'])) == len(pool['symbols']) and
             set(manifest['symbols']) == set(pool['symbols']) and
             manifest['control_daily_records'] == value['control_daily_records'] and
             capability['status'] == astatus and capability['source_only'] is True and
             capability['pool_receipt_sha256'] == value['pool_receipt']['sha256'], 'Exact original monthly capability identities')
        expected_keys = {(kind, symbol, interval, month) for symbol in pool['symbols']
            for kind, interval in (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None))}
        need(set(keyed(manifest['market_records'])) == expected_keys and
             all(capability['normalized_source_hashes'].get(r['normalized_path']) == r['normalized_sha256']
                 for r in manifest['market_records']), 'All original monthly financial sources covered by their capability')
        closed = guard.closed(capability['binding']['task_id'])
        certificates.append(dict(month=month, manifest=ref, acceptance=acceptance_ref, actual_closed_task=closed))
        all_market += manifest['market_records']
    for i in (1, 2):
        need(identity(manifests[i]['warmup_manifest']) == identity(refs[i-1]) and
             identity(manifests[i]['warmup_source_acceptance']) == identity(acceptance_refs[i-1]),
             'Unchanged accepted cross-month warmup capability chain')
        expected_warm = [r for m in manifests[:i] for r in m['market_records'] if r['kind'] == 'klines']
        need(keyed(manifests[i]['warmup_minute_records']) == keyed(expected_warm),
             'Prior minute aliases remain the exact accepted months')
    daily = [r for r in pool['source_records'] if r['symbol'] in value['symbols']]
    need(len(value['control_daily_records']) == 14 and len(daily) == 70 and
         keyed(value['daily_records'], True) == keyed(daily, True) and
         set(keyed(daily)) == {('klines', s, '1d', '2024-' + m) for s in pool['symbols']
                             for m in ('02', '03', '04', '05', '06', '07', '08')} and
         keyed(value['market_records']) == keyed(all_market), 'Exact February-August warmup and three complete scoring months')
    records = [*all_market, *daily, *value['control_daily_records']]
    exact_hashes = {r['normalized_path']: r['normalized_sha256'] for r in records}
    need(len(exact_hashes) == 160 and value['normalized_source_hashes'] == exact_hashes and
         all(capabilities[0]['normalized_source_hashes'].get(r['normalized_path']) == r['normalized_sha256']
             for r in [*daily, *value['control_daily_records']]), 'Composite aliases cannot replace any accepted source bytes')
    return records, certificates


def winter_source_records(value, symbols, guard, scope):
    """New quarter capability plus accepted warmup identities; no payload QA."""
    def metadata(reference):
        path = Path(reference['path'])
        return guard.small(path if path.is_absolute() else guard.project(str(path)), reference['sha256'])[0]
    def identity(reference):
        path = Path(reference['path'])
        return str(path if path.is_absolute() else ROOT / path), reference['sha256']
    def keyed(records):
        result = {}
        for row in records:
            key = row['kind'], row['symbol'], row.get('interval'), row['month']
            need(key not in result, 'Unique winter source aliases')
            result[key] = {k: row[k] for k in ('kind', 'symbol', 'interval', 'month',
                'normalized_path', 'normalized_sha256', 'normalized_bytes', 'rows')}
        return result
    need(value['status'] == 'PASS_D056_SELECTED_PORTFOLIO_WINTER_SOURCE_BINDING_NOT_ECONOMICS' and
         value['source_only'] is True and value['checksummed_source_format_verified'] is True and
         (value['start_us'], value['end_us'], value['days']) ==
         (scope['start_us'], scope['end_us'], scope['period_days']) and
         value['score_months'] == scope['score_months'], 'Exact accepted winter90 source scope')
    warm = metadata(value['warmup_manifest'])
    warm_scope = calendar_scope(dict(start='2024-09-01T00:00:00+00:00',
        end_exclusive='2024-12-01T00:00:00+00:00', period_days=91,
        account_path='CONTINUOUS_SHARED_ACCOUNT_SEP_NOV_91D',
        data_role='SEEN_DEVELOPMENT_CONTINUOUS_ACCEPTED_THREE_MONTH_MANIFEST'))
    _, certificates = continuous_source_records(warm, symbols, guard, warm_scope)
    need(identity(value['pool_receipt']) == identity(warm['pool_receipt']) and
         value['selected_symbols'] == warm['selected_symbols'] and
         len(value['symbols']) == len(set(value['symbols'])) == len(warm['symbols']) and
         set(value['symbols']) == set(warm['symbols']) and
         [identity(r) for r in value['warmup_source_acceptances']] ==
         [identity(r) for r in warm['monthly_acceptances']], 'Original July pool and three warmup capabilities')
    prior_trade = [r for r in warm['market_records'] if r['kind'] == 'klines']
    need(len(value['daily_records']) == 70 and len(value['control_daily_records']) == 14 and
         keyed(value['daily_records']) == keyed(warm['daily_records']) and
         keyed(value['control_daily_records']) == keyed(warm['control_daily_records']) and
         len(value['warmup_minute_records']) == 30 and
         keyed(value['warmup_minute_records']) == keyed(prior_trade),
         'Every accepted February-August daily and September-November minute warmup alias retained')
    capability = metadata(value['source_acceptance'])
    need(capability['status'] == 'PASS_D056_FIXED_POOL_WINTER_SOURCE_FORMAT_ONLY' and
         capability['source_only'] is True and capability['actual_exit_code'] == 0 and
         capability['pool_receipt_sha256'] == value['pool_receipt']['sha256'] and
         (capability['start_us'], capability['end_us']) == (scope['start_us'], scope['end_us']) and
         capability['completed_files'] == 90 and capability['newly_verified_files'] == 72 and
         capability['reused_accepted_files'] == 18, 'One actual accepted72/18 quarter source capability')
    expected = {(kind, symbol, interval, month) for symbol in warm['selected_symbols']
        for month in scope['score_months']
        for kind, interval in (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None))}
    market = keyed(value['market_records'])
    hashes = {r['normalized_path']: r['normalized_sha256'] for r in market.values()}
    need(len(market) == 90 and set(market) == expected and len(hashes) == 90 and
         hashes == capability['normalized_source_hashes'] and keyed(capability['sources']) == market,
         'Exact ninety accepted quarter financial roles')
    original_ref = capability['reused_market_manifest']
    need(original_ref['sha256'] == '8b665b2829eafd192871fe4a3bc418dac1c202ed54f7d2d5494545fa6636fbfa',
         'Original accepted D045 source binding for eighteen control roles')
    original = metadata(original_ref)
    need(original['status'] == 'PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS' and
         original['source_only'] is True, 'Accepted old source capability, not failed parent data')
    original_rows = keyed(original['source_files'].values())
    reused_keys = {key for key in expected if key[1] in ('BTCUSDT', 'ETHUSDT')}
    need(len(reused_keys) == 18 and all(market[k] == original_rows[k] for k in reused_keys),
         'All eighteen original control source identities retained without new QA')
    records = [*value['market_records'], *value['daily_records'], *value['control_daily_records'],
        *value['warmup_minute_records']]
    exact_hashes = {r['normalized_path']: r['normalized_sha256'] for r in records}
    need(len(exact_hashes) == 190 and value['normalized_source_hashes'] == exact_hashes,
         'Exact190 warm-and-score source SHA aliases; no unaccepted replacement')
    certificates.append(dict(scope='WINTER_QUARTER_72_FIRST_QA_18_ACCEPTED_REUSE',
        acceptance=value['source_acceptance'], actual_closed_task=guard.closed(capability['binding']['task_id']),
        warmup_manifest=value['warmup_manifest'], old_warmup_rows_or_CRC_reread=False))
    return records, certificates


def input_reader(spec, symbols, base, guard):
    """Bound normal N sources, not the producer's loader or format QA."""
    manifest = spec['data_manifest']; path = Path(manifest['path'])
    value, _ = guard.small(path, manifest['sha256'])
    scope = calendar_scope(spec)
    start, end = scope['start_us'], scope['end_us']
    month = scope['score_month']
    continuous = 'score_months' in scope
    source_metadata_proofs = []
    times = np.arange(start, end, MINUTE, dtype=np.int64)
    if scope['period_days'] == 90:
        records, source_metadata_proofs = winter_source_records(value, symbols, guard, scope)
    elif continuous:
        records, source_metadata_proofs = continuous_source_records(value, symbols, guard, scope)
    elif spec.get('data_role') == 'EXISTING_ACCEPTED_TWO_ASSET_CONTROL':
        need(month in ('2024-09', '2024-10') and tuple(symbols) == ('BTCUSDT', 'ETHUSDT') and
             manifest['sha256'] == '8b665b2829eafd192871fe4a3bc418dac1c202ed54f7d2d5494545fa6636fbfa' and
             value['status'] == 'PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS',
             'Existing accepted two-asset source scope')
        records = list(value['source_files'].values())
    else:
        manifest_status = {
            '2024-09': 'PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS',
            '2024-10': 'PASS_D051_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS',
            '2024-11': 'PASS_D054_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS',
        }[month]
        need(value['status'] == manifest_status and
             value['checksummed_source_format_verified'] is True and
             (value['start_us'], value['end_us']) == (start, end), 'Accepted selected source scope')
        def metadata(reference):
            path = Path(reference['path'])
            return guard.small(path if path.is_absolute() else guard.project(str(path)), reference['sha256'])[0]
        def reference_identity(reference):
            path = Path(reference['path'])
            return str(path if path.is_absolute() else ROOT / path), reference['sha256']
        pool = metadata(value['pool_receipt'])
        acceptance = metadata(value['source_acceptance'])
        acceptance_status = {
            '2024-09': 'PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY',
            '2024-10': 'PASS_D051_FIXED_POOL_OCTOBER_SOURCE_FORMAT_ONLY',
            '2024-11': 'PASS_D054_FIXED_POOL_NOVEMBER_SOURCE_FORMAT_ONLY',
        }[month]
        need(pool['status'] == 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS' and
             (list(symbols) == pool['symbols'] or tuple(symbols) == ('BTCUSDT', 'ETHUSDT')) and
             len(value['symbols']) == len(set(value['symbols'])) == len(pool['symbols']) and
             set(value['symbols']) == set(pool['symbols']) and pool['score_payloads_read'] == 0 and
             acceptance['status'] == acceptance_status and acceptance['source_only'] is True and
             acceptance['pool_receipt_sha256'] == value['pool_receipt']['sha256'], 'Same pre-score pool/source acceptance')
        warm_records = [*value['control_daily_records'], *pool['source_records']]
        market_records = value['market_records']
        need(all(acceptance['normalized_source_hashes'].get(r['normalized_path']) == r['normalized_sha256']
                 for r in market_records), 'Every scoring source covered by accepted month capability')
        if month == '2024-10':
            prior_manifest = metadata(value['warmup_manifest'])
            prior = metadata(value['warmup_source_acceptance'])
            need(prior_manifest['status'] == 'PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS' and
                 prior_manifest['checksummed_source_format_verified'] is True and
                 prior_manifest['end_us'] == start and
                 reference_identity(prior_manifest['pool_receipt']) == reference_identity(value['pool_receipt']) and
                 reference_identity(prior_manifest['source_acceptance']) == reference_identity(value['warmup_source_acceptance']) and
                 prior_manifest['control_daily_records'] == value['control_daily_records'] and
                 prior['status'] == 'PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY' and
                 prior['source_only'] is True and prior['pool_receipt_sha256'] == value['pool_receipt']['sha256'],
                 'Prior warmup format capability retains the identical July pool')
            minute_warm = value['warmup_minute_records']
            expected_warm = [r for r in prior_manifest['market_records'] if r['kind'] == 'klines']
            need(len(minute_warm) == len(pool['symbols']) and
                 {(r['kind'], r['symbol'], r.get('interval'), r['month']) for r in minute_warm} ==
                 {('klines', s, '1m', '2024-09') for s in pool['symbols']} and
                 {r['symbol']: r for r in minute_warm} == {r['symbol']: r for r in expected_warm},
                 'Only all ten accepted September trade sources supply October causal warmup')
            warm_records += minute_warm
            accepted_warm = prior['normalized_source_hashes']
        elif month == '2024-11':
            prior_manifest = metadata(value['warmup_manifest'])
            prior = metadata(value['warmup_source_acceptance'])
            october_start = int(datetime(2024, 10, 1, tzinfo=UTC).timestamp()) * 1_000_000
            september_start = int(datetime(2024, 9, 1, tzinfo=UTC).timestamp()) * 1_000_000
            need(prior_manifest['status'] == 'PASS_D051_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS' and
                 prior_manifest['checksummed_source_format_verified'] is True and
                 (prior_manifest['start_us'], prior_manifest['end_us']) == (october_start, start) and
                 reference_identity(prior_manifest['pool_receipt']) == reference_identity(value['pool_receipt']) and
                 reference_identity(prior_manifest['source_acceptance']) == reference_identity(value['warmup_source_acceptance']) and
                 prior_manifest['control_daily_records'] == value['control_daily_records'] and
                 prior['status'] == 'PASS_D051_FIXED_POOL_OCTOBER_SOURCE_FORMAT_ONLY' and
                 prior['source_only'] is True and prior['pool_receipt_sha256'] == value['pool_receipt']['sha256'],
                 'November retains the exact accepted October manifest/capability and July pool')
            earlier_manifest = metadata(prior_manifest['warmup_manifest'])
            earlier = metadata(prior_manifest['warmup_source_acceptance'])
            need(earlier_manifest['status'] == 'PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS' and
                 earlier_manifest['checksummed_source_format_verified'] is True and
                 (earlier_manifest['start_us'], earlier_manifest['end_us']) == (september_start, october_start) and
                 reference_identity(earlier_manifest['pool_receipt']) == reference_identity(value['pool_receipt']) and
                 reference_identity(earlier_manifest['source_acceptance']) == reference_identity(prior_manifest['warmup_source_acceptance']) and
                 earlier_manifest['control_daily_records'] == value['control_daily_records'] and
                 earlier['status'] == 'PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY' and
                 earlier['source_only'] is True and earlier['pool_receipt_sha256'] == value['pool_receipt']['sha256'],
                 'October explicitly retains the accepted daily/September warmup capability')
            september_trade = [r for r in earlier_manifest['market_records'] if r['kind'] == 'klines']
            need(len(prior_manifest['warmup_minute_records']) == len(pool['symbols']) and
                 {r['symbol']: r for r in prior_manifest['warmup_minute_records']} ==
                 {r['symbol']: r for r in september_trade}, 'Unchanged original September minute warmup aliases')
            expected_warm = [*september_trade,
                *(r for r in prior_manifest['market_records'] if r['kind'] == 'klines')]
            minute_warm = value['warmup_minute_records']
            need(len(minute_warm) == 2 * len(pool['symbols']) and
                 {(r['kind'], r['symbol'], r.get('interval'), r['month']) for r in minute_warm} ==
                 {('klines', s, '1m', m) for s in pool['symbols'] for m in ('2024-09', '2024-10')} and
                 {(r['symbol'], r['month']): r for r in minute_warm} ==
                 {(r['symbol'], r['month']): r for r in expected_warm},
                 'Only all ten accepted September/October trade sources supply November warmup')
            warm_records += minute_warm
            accepted_warm = dict(earlier['normalized_source_hashes'])
            need(all(path not in accepted_warm or accepted_warm[path] == digest
                     for path, digest in prior['normalized_source_hashes'].items()),
                 'Earlier and October capability aliases cannot disagree')
            accepted_warm.update(prior['normalized_source_hashes'])
        else:
            accepted_warm = acceptance['normalized_source_hashes']
        need(all(accepted_warm.get(r['normalized_path']) == r['normalized_sha256']
                 for r in warm_records if r['symbol'] in symbols),
             'Every financially used source covered by the scoring or prior-warmup capability')
        records = [*market_records, *warm_records]
    catalog = {}
    for row in records:
        key = row['kind'], row['symbol'], row.get('interval'), row['month']
        if key in catalog:
            need(all(catalog[key][k] == row[k] for k in
                     ('normalized_path', 'normalized_sha256', 'normalized_bytes', 'rows')), 'Duplicate source alias must be identical')
        catalog[key] = row
    window = dict(start=start, end=end, count=len(times), days=scope['period_days'],
        required_scope=scope, market={}, bars={}, events=[], proofs=[], source_metadata_proofs=source_metadata_proofs)
    def read(key, columns):
        row = catalog[key]; p = base.payload(row)
        window['proofs'].append(dict(kind=key[0], symbol=key[1], interval=key[2], month=key[3],
            path=str(p), sha256=row['normalized_sha256'], bytes=row['normalized_bytes'], rows=row['rows']))
        return pl.read_parquet(p, columns=columns)
    def daily_close(frame, first, finish):
        stamps = np.arange(first, finish, MINUTE, dtype=np.int64)
        need(np.array_equal(frame['open_us'].to_numpy(), stamps) and
             np.array_equal(frame['available_us'].to_numpy(), stamps + MINUTE),
             'Complete prior/score minute clock and exclusive availability proxy')
        ends = stamps + MINUTE; mask = ends % DAY == 0
        closes = frame['close'].to_numpy()[mask]
        need(np.isfinite(closes).all() and np.all(closes > 0), 'Actual completed-day closes without imputation')
        return pl.DataFrame(dict(open_us=ends[mask] - DAY, close_us=ends[mask],
            available_us=ends[mask], close=closes))
    for symbol in symbols:
        score_months = scope['score_months'] if continuous else [month]
        trade = pl.concat([read(('klines', symbol, '1m', m),
            ['open_us', 'available_us', 'open', 'close', 'quote_volume']) for m in score_months]).sort('open_us')
        mark = pl.concat([read(('markPriceKlines', symbol, '1m', m), ['timestamp_ms', 'close'])
            for m in score_months]).sort('timestamp_ms')
        fund = pl.concat([read(('fundingRate', symbol, None, m), ['calc_time_ms', 'last_funding_rate'])
            for m in score_months]).sort('calc_time_ms')
        warm = pl.concat([read(('klines', symbol, '1d', '2024-' + m),
                ['open_us', 'close_us', 'available_us', 'close'])
            for m in ('02', '03', '04', '05', '06', '07', '08')]).sort('close_us')
        prior_months = scope.get('warmup_months', ()) if continuous else ('2024-09', '2024-10') if month == '2024-11' else ('2024-09',) if month == '2024-10' else ()
        for prior_month in prior_months:
            prior_trade = read(('klines', symbol, '1m', prior_month), ['open_us', 'available_us', 'close']).sort('open_us')
            first = datetime.fromisoformat(prior_month + '-01T00:00:00+00:00')
            prior_start = int(first.timestamp()) * 1_000_000
            prior_end = int(next_month(first).timestamp()) * 1_000_000
            warm = pl.concat([warm, daily_close(prior_trade, prior_start, prior_end)]).sort('close_us')
            del prior_trade
        need(np.array_equal(trade['open_us'].to_numpy(), times) and
             np.array_equal(mark['timestamp_ms'].to_numpy() * 1000, times), 'Full synchronous asset execution/mark clock')
        window['market'][symbol] = dict(open=trade['open'].to_numpy(), quote=trade['quote_volume'].to_numpy(), mark=mark['close'].to_numpy())
        need(all(np.isfinite(a).all() for a in window['market'][symbol].values()) and
             np.all(window['market'][symbol]['open'] > 0) and np.all(window['market'][symbol]['mark'] > 0)
             and np.all(window['market'][symbol]['quote'] >= 0), 'Finite financial prices/capacity without substitution')
        score = daily_close(trade, start, end)
        bars = pl.concat([warm, score]).sort('close_us')
        need(bars['close_us'].n_unique() == bars.height and
             bars['open_us'].eq(bars['close_us'] - DAY).all(), 'Complete unique closed daily price identities')
        window['bars'][symbol] = bars
        for event, rate in fund.iter_rows():
            need(start <= event * 1000 < end and math.isfinite(rate), 'Original signed in-window coupons')
            window['events'].append(dict(symbol=symbol, event_us=event * 1000, raw_rate=rate))
        del trade, mark, fund, warm
    window['events'].sort(key=lambda row: (row['event_us'], row['symbol']))
    need(len(window['events']) == len({(r['symbol'], r['event_us']) for r in window['events']}), 'Original event exact-once identity')
    return window


def inverse_target_reference(window, symbols):
    """Independent sample variance, capped reciprocal sizes, then covariance.

    A current member with an unavailable 200-day history or undefined sample
    volatility makes the whole allocation flat. Clipped budget stays unused.
    This does not solve equal risk contribution or optimize historical returns.
    """
    rows = []
    for decision in range(window['start'], window['end'], DAY):
        memberships = window.get('eligible_by_decision')
        members = set(symbols) if memberships is None else set(memberships.get(decision, ()))
        need(members <= set(symbols), 'Independent membership outside configured identity')
        live, returns, reasons = [], [], {}
        for symbol in symbols:
            bars = window['bars'][symbol]
            i = int(np.searchsorted(bars['close_us'].to_numpy(), decision, side='right') - 1)
            valid = (i >= 199 and bars['close_us'][i] == decision and
                np.all(np.diff(bars['close_us'][i-199:i+1].to_numpy()) == DAY) and
                np.all(bars['available_us'][i-199:i+1].to_numpy() <= decision))
            if symbol not in members or not valid:
                reasons[symbol] = 'POOL_EXIT' if symbol not in members else 'WARMUP_OR_DATA_GAP'
                continue
            close = bars['close'][i-30:i+1].to_numpy()
            need(np.isfinite(close).all() and np.all(close > 0), 'Finite past-only inverse inputs')
            with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
                returns.append(np.diff(close) / close[:-1])
            live.append(symbol)
            reasons[symbol] = 'ELIGIBLE'
        raw = dict.fromkeys(symbols, 0.)
        weights = dict.fromkeys(symbols, 0.)
        unknown = len(live) != len(members) or not live
        if live:
            x = np.column_stack(returns)
            with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
                centered = x - x.mean(axis=0)
                sample_vol = np.sqrt(np.sum(centered * centered, axis=0) / 29)
            unknown = unknown or not np.isfinite(sample_vol).all() or np.any(sample_vol <= 0)
        if unknown:
            for symbol in live:
                reasons[symbol] = 'INVERSE_VOLATILITY_UNKNOWN_FLAT'
        else:
            # Proportional reciprocal normalization avoids overflow without a floor.
            reciprocal = float(np.min(sample_vol)) / sample_vol
            sizes = np.minimum(.3, .6 * reciprocal / np.sum(reciprocal))
            covariance = centered.T @ centered / 29 * 365
            gross = float(np.abs(sizes).sum())
            scaled = sizes.copy()
            if gross > .6:
                scaled *= .6 / gross
            sigma = math.sqrt(max(float(scaled @ covariance @ scaled), 0.))
            if sigma > .10:
                scaled *= .10 / sigma
            raw.update(zip(live, map(float, sizes), strict=True))
            weights.update(zip(live, map(float, scaled), strict=True))
        for symbol in symbols:
            rows.append(dict(available_us=decision, symbol=symbol,
                target_weight=weights[symbol], raw_signed_target=raw[symbol],
                mode='LONG_ONLY', eligibility_reason=reasons[symbol]))
    return pl.DataFrame(rows)


def sma_pool_target_reference(window, symbols):
    """Scalar past200 SMA state plus independently centered past30 covariance.

    Start flat at this scoring window; no warmup inventory or crossing-event
    requirement. Inactive signals retain their membership budget share.
    """
    states = dict.fromkeys(symbols, 0)
    rows, witnesses = [], []
    for decision in range(window['start'], window['end'], DAY):
        memberships = window.get('eligible_by_decision')
        members = set(symbols) if memberships is None else set(memberships.get(decision, ()))
        need(members <= set(symbols), 'Independent SMA membership outside configured identity')
        live, returns, reasons = [], [], {}
        raw, weights = dict.fromkeys(symbols, 0.), dict.fromkeys(symbols, 0.)
        for symbol in symbols:
            bars = window['bars'][symbol]
            i = int(np.searchsorted(bars['close_us'].to_numpy(), decision, side='right') - 1)
            valid = (i >= 199 and bars['close_us'][i] == decision and
                np.all(np.diff(bars['close_us'][i-199:i+1].to_numpy()) == DAY) and
                np.all(bars['available_us'][i-199:i+1].to_numpy() <= decision))
            before = states[symbol]
            if symbol not in members or not valid:
                states[symbol] = 0
                reasons[symbol] = 'POOL_EXIT' if symbol not in members else 'WARMUP_OR_DATA_GAP'
                witnesses.append(dict(decision_us=decision, symbol=symbol, old_state=before,
                    new_state=0, reason=reasons[symbol]))
                continue
            closes = bars['close'][i-199:i+1].to_numpy()
            need(np.isfinite(closes).all() and np.all(closes > 0), 'Finite completed SMA/covariance closes')
            fast = math.fsum(map(float, closes[-50:])) / 50
            slow = math.fsum(map(float, closes)) / 200
            if before:
                states[symbol] = 0 if fast < slow else 1
            elif fast > slow:
                states[symbol] = 1
            # Equality holds the current state; a close cannot reenter this day.
            raw[symbol] = min(.3, .6 / len(members)) * states[symbol]
            past = closes[-31:]
            returns.append(np.diff(past) / past[:-1])
            live.append(symbol)
            reasons[symbol] = 'ELIGIBLE'
            witnesses.append(dict(decision_us=decision, symbol=symbol, fast_SMA50=fast,
                slow_SMA200=slow, old_state=before, new_state=states[symbol], reason='ELIGIBLE'))
        if live:
            x = np.column_stack(returns)
            need(np.isfinite(x).all(), 'Finite complete independent past30 returns')
            centered = x - x.mean(axis=0)
            covariance = centered.T @ centered / 29 * 365
            scaled = np.asarray([raw[s] for s in live], dtype=np.float64)
            gross = float(np.abs(scaled).sum())
            if gross > .6:
                scaled *= .6 / gross
            sigma = math.sqrt(max(float(scaled @ covariance @ scaled), 0.))
            if sigma > .10:
                scaled *= .10 / sigma
            weights.update(zip(live, map(float, scaled), strict=True))
        for symbol in symbols:
            rows.append(dict(available_us=decision, symbol=symbol,
                target_weight=weights[symbol], raw_signed_target=raw[symbol],
                mode='LONG_ONLY', eligibility_reason=reasons[symbol]))
    window['independent_SMA_state_witnesses'] = witnesses
    return pl.DataFrame(rows)


def momentum_pool_target_reference(window, symbols):
    """Independent completed-close predicate and fresh-flat long/cash state.

    Directly compare the latest close with the close thirty UTC days earlier;
    no producer target method, direction hook, return threshold or epsilon band.
    Idle members retain their raw budget, with the accepted covariance scaling.
    """
    states = dict.fromkeys(symbols, 0)
    rows, witnesses = [], []
    for decision in range(window['start'], window['end'], DAY):
        memberships = window.get('eligible_by_decision')
        members = set(symbols) if memberships is None else set(memberships.get(decision, ()))
        need(members <= set(symbols), 'Independent momentum membership outside configured identity')
        live, returns, reasons = [], [], {}
        raw, weights = dict.fromkeys(symbols, 0.), dict.fromkeys(symbols, 0.)
        for symbol in symbols:
            bars = window['bars'][symbol]
            i = int(np.searchsorted(bars['close_us'].to_numpy(), decision, side='right') - 1)
            valid = (i >= 199 and bars['close_us'][i] == decision and
                np.all(np.diff(bars['close_us'][i-199:i+1].to_numpy()) == DAY) and
                np.all(bars['available_us'][i-199:i+1].to_numpy() <= decision))
            before = states[symbol]
            if symbol not in members or not valid:
                states[symbol] = 0
                reasons[symbol] = 'POOL_EXIT' if symbol not in members else 'WARMUP_OR_DATA_GAP'
                witnesses.append(dict(decision_us=decision, symbol=symbol, old_state=before,
                    new_state=0, action='RESET_UNAVAILABLE', reason=reasons[symbol]))
                continue
            closes = bars['close'][i-199:i+1].to_numpy()
            need(np.isfinite(closes).all() and np.all(closes > 0), 'Finite completed momentum/covariance closes')
            latest, previous = float(closes[-1]), float(closes[-31])
            if before:
                states[symbol] = 0 if latest <= previous else 1
                action = 'EXIT_TO_CASH' if states[symbol] == 0 else 'KEEP_LONG'
            else:
                states[symbol] = 1 if latest > previous else 0
                action = 'ENTER_LONG' if states[symbol] else 'STAY_CASH'
            raw[symbol] = min(.3, .6 / len(members)) * states[symbol]
            past = closes[-31:]
            returns.append(np.diff(past) / past[:-1])
            live.append(symbol)
            reasons[symbol] = 'ELIGIBLE'
            witnesses.append(dict(decision_us=decision, symbol=symbol,
                latest_completed_close=latest, completed_close_30_days_earlier=previous,
                prior_close_us=int(bars['close_us'][i-30]), latest_close_us=int(bars['close_us'][i]),
                old_state=before, new_state=states[symbol], action=action, reason='ELIGIBLE'))
        if live:
            x = np.column_stack(returns)
            need(np.isfinite(x).all(), 'Finite complete independent momentum past30 returns')
            centered = x - x.mean(axis=0)
            covariance = centered.T @ centered / 29 * 365
            scaled = np.asarray([raw[s] for s in live], dtype=np.float64)
            gross = float(np.abs(scaled).sum())
            if gross > .6:
                scaled *= .6 / gross
            sigma = math.sqrt(max(float(scaled @ covariance @ scaled), 0.))
            if sigma > .10:
                scaled *= .10 / sigma
            weights.update(zip(live, map(float, scaled), strict=True))
        for symbol in symbols:
            rows.append(dict(available_us=decision, symbol=symbol,
                target_weight=weights[symbol], raw_signed_target=raw[symbol],
                mode='LONG_ONLY', eligibility_reason=reasons[symbol]))
    window['independent_momentum_state_witnesses'] = witnesses
    return pl.DataFrame(rows)


def target_reference(window, symbols, allocation='EQUAL', *, strategy_id=None):
    need(allocation in ALLOCATION_STRATEGIES, 'Only predeclared allocation choices')
    if strategy_id == SMA_POOL_STRATEGY:
        need(allocation == 'EQUAL', 'Predeclared SMA uses original equal member shares only')
        return sma_pool_target_reference(window, symbols)
    if strategy_id == MOMENTUM_POOL_STRATEGY:
        need(allocation == 'EQUAL', 'Predeclared momentum uses original equal member shares only')
        return momentum_pool_target_reference(window, symbols)
    need(strategy_id in (None, ALLOCATION_STRATEGIES[allocation]), 'Explicit independent strategy identity')
    if allocation == 'INVERSE_VOL_30D':
        return inverse_target_reference(window, symbols)
    rows = []
    for decision in range(window['start'], window['end'], DAY):
        returns = []
        for symbol in symbols:
            bars = window['bars'][symbol]; i = int(np.searchsorted(bars['close_us'].to_numpy(), decision, side='right') - 1)
            need(i >= 199 and bars['close_us'][i] == decision and
                 np.all(np.diff(bars['close_us'][i-199:i+1].to_numpy()) == DAY) and
                 np.all(bars['available_us'][i-199:i+1].to_numpy() <= decision), '200 actually completed available days')
            close = bars['close'][i-30:i+1].to_numpy()
            need(np.isfinite(close).all() and np.all(close > 0), 'Finite past-only covariance inputs')
            returns.append(np.diff(close) / close[:-1])
        x = np.column_stack(returns); centered = x - x.mean(axis=0)
        covariance = centered.T @ centered / 29 * 365
        weights = np.full(len(symbols), min(.3, .6 / len(symbols)))
        gross = float(np.abs(weights).sum())
        if gross > .6:
            weights *= .6 / gross
        sigma = math.sqrt(max(float(weights @ covariance @ weights), 0.))
        if sigma > .10:
            weights *= .10 / sigma
        for symbol, weight in zip(symbols, weights, strict=True):
            rows.append(dict(available_us=decision, symbol=symbol, target_weight=float(weight),
                raw_signed_target=min(.3, .6 / len(symbols)), mode='LONG_ONLY', eligibility_reason='ELIGIBLE'))
    return pl.DataFrame(rows)


def continuous_boundary_witnesses(window, result, funding_path, base, errors):
    """Expose already independently verified month-boundary coupons and state."""
    funds = json.loads(funding_path.read_bytes())
    witnesses = []
    for month, previous in zip(window['required_scope']['score_months'][1:], result['months'][:-1], strict=True):
        boundary = int(datetime.fromisoformat(month + '-01T00:00:00+00:00').timestamp()) * 1_000_000
        expected = [r for r in window['events'] if r['event_us'] == boundary]
        observed = [r for r in funds if r['event_us'] == boundary]
        need([(r['symbol'], r['event_us'], r['raw_rate']) for r in observed] ==
             [(r['symbol'], r['event_us'], r['raw_rate']) for r in expected],
             'Every actual boundary coupon retained; no fresh-flat exclusions or assumed eight-hour count')
        for row in observed:
            base.same(row['quantity'], previous['ending_signed_quantities'][row['symbol']],
                'Carried month-boundary funding inventory', errors, base.RATIO_TOL)
        witnesses.append(dict(boundary_us=boundary, previous_month=previous['month'],
            previous_ending_NAV=previous['ending_NAV'],
            carried_signed_quantities=previous['ending_signed_quantities'], original_event_count=len(expected),
            funding_rows=[{k:row[k] for k in ('symbol', 'event_us', 'owned', 'quantity',
                'mark_price', 'mark_close_us', 'signed_funding_USDT')} for row in observed],
            same_timestamp_funding_precedes_fills=True,
            funding_wallet_margin_and_cash_verified_by_original_full_journal=True))
    return witnesses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'actual', 'run-dir', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    need(os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE / 'v8-clean-env-20261002-v2')
         and pl.thread_pool_size() <= 2, 'Actual bounded clean CPU2 execution')
    initial = prepare_financial(('BTCUSDT', 'ETHUSDT'))[0]
    guard = initial.module(initial.GUARD, 'd050_accepted_small_guards', initial.GUARD_SHA)
    need(args.run_dir.parent == STATE and args.run_dir.is_dir() and
         {p.name for p in args.run_dir.iterdir()} == {'ACTUAL_BINDING.json'} and
         args.output.parent == ROOT / 'reports/fast_research' and not args.output.exists(), 'Exclusive prebound audit outputs')
    plan, plan_sha = guard.small(args.run_dir / 'ACTUAL_BINDING.json')
    own = sha(__file__)
    need(plan['ready_to_execute'] is True and plan['checker_sha256'] == own and
         plan['tolerances'] == dict(cash_USDT=1e-7, ratio=1e-10), 'Frozen checker and original tolerances')
    need(plan['protocol_path'] == str(args.protocol.relative_to(ROOT)) and
         plan['actual_report'] == str(args.actual.relative_to(ROOT)), 'Exact protocol/actual invocation')
    binding = dict(task_id=os.environ['COIN_TASK_ID'], checker_sha256=own, ACTUAL_BINDING_sha256=plan_sha,
        actual_reports={str(args.actual): plan['actual_report_sha256']}, source_hashes=plan['source_hashes'])
    guard.write(args.run_dir / 'RUN_BINDING.json', binding)
    before = resources.status(); started = time.monotonic(); errors = dict(cash=0., ratio=0.)
    report = dict(status='FAIL_CONFIGURED_N_PERPETUAL_RECORDED_ACCOUNTING', binding=binding,
        independent_source_sha256=own, run_dir=str(args.run_dir), run_binding_sha256=sha(args.run_dir / 'RUN_BINDING.json'),
        tolerances=plan['tolerances'], maximum_errors=errors, cases=[], completed_cases_verified=0,
        full_market_frozen_order_quantity_sizing_independently_rebuilt=False,
        financial_scope='RECORDED_SIGNED_LEGS_CONDITIONAL_FUNDING_SHARED_WALLET_MINUTE_DAY_MONTH_AND_CONFIGURED_TARGETS',
        funding_unit_certified=False, native_filters_certified=False, publication_certified=False,
        candidate='NO_QUALIFIED_CANDIDATE', long_term_APR='NOT_EVALUABLE', locked_consumed=False,
        models_fit=0, orders_sent=0, GPU=0, old_QA_or_accounts_replayed=False, resources_before=before)
    from scripts.research_v7.oracle_flow_ceiling import Progress
    progress = Progress(); progress.value['detail'] = '仅新N账户的独立已成交账本与条件资金费'
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=args.run_dir.name, event_id=args.run_dir.name + ':START',
        event_type='OPERATIONAL_RESEARCH_START', git_commit=None, data_manifest_hash=None,
        protocol_hash=plan['protocol_sha256'], feature_set='RECORDED_N_SHARED_ACCOUNT', labels='NONE', model_family='NONE',
        hyperparameters={'binding_path': str(args.run_dir / 'ACTUAL_BINDING.json'), 'binding_sha256': plan_sha}, seed=None,
        thresholds=plan['tolerances'], cost_assumptions='BOUND_PRODUCER_TWO_COSTS_TWO_CONDITIONAL_UNITS',
        all_folds='PROTOCOL_BOUND_SEEN_COMPLETE_UTC_CALENDAR_NEW_ACCOUNTS_ONLY', success_failure='START_BEFORE_FINANCIAL_PAYLOAD',
        reason_for_next_experiment='Independent shared-wallet evidence', result_influenced_later_choice=False)
    report['registration_start'] = append_event(ROOT / 'reports/experiment_registry.jsonl', event)
    def bounded():
        guard.bounded(resources.status())
        need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 <= plan['budgets']['peak_RSS_bytes'] and
             time.monotonic() - started <= plan['budgets']['wall_seconds'], 'Finite independent RSS/wall budget')
        need(sum(p.stat().st_size for p in args.run_dir.rglob('*') if p.is_file()) <= plan['budgets']['new_owned_bytes'],
             'Small exclusive audit STATE footprint')
    try:
        bounded()
        for name, digest in plan['source_hashes'].items():
            guard_path = guard.project(plan.get('source_archives', {}).get(name, name))
            need(sha(guard_path) == digest, 'Exact frozen independent helper/source: ' + name)
        spec, _ = guard.small(args.protocol, plan['protocol_sha256'])
        scope = calendar_scope(spec)
        need(plan['required_scope'] == scope, 'Prebound explicit calendar/count scope before financial payload')
        report['required_scope'] = scope
        actual, actual_sha = guard.small(args.actual, plan['actual_report_sha256'])
        need(actual['status'] in ACTUAL_STATUSES and actual['binding']['task_id'] == plan['actual_task_id']
             and actual['binding']['protocol_sha256'] == plan['protocol_sha256'], 'Exact successful new producer')
        report['actual_task'] = guard.closed(plan['actual_task_id'])
        rb, rb_sha = guard.small(Path(actual['run_dir']) / 'RUN_BINDING.json')
        need(rb == actual['binding'], 'Actual producer RUN_BINDING exact')
        need(rb['source_hashes'] == spec['source_hashes'], 'Source map bound before producer execution')
        allocation = spec.get('allocation', 'EQUAL')
        strategy_id = spec['strategy']
        sma_strategy = strategy_id == SMA_POOL_STRATEGY
        momentum_strategy = strategy_id == MOMENTUM_POOL_STRATEGY
        need(allocation in ALLOCATION_STRATEGIES and spec['initial_capital_USDT'] == 10000 and
             (strategy_id == ALLOCATION_STRATEGIES[allocation] or
              (sma_strategy or momentum_strategy) and allocation == 'EQUAL'),
             'Same fixed capital and explicit independent strategy/allocation policy')
        need('score_months' not in scope or not sma_strategy,
             'Continuous quarters contain the predeclared HOLD or past30 long/cash recipes')
        if momentum_strategy:
            need('score_months' in scope and len(actual['cases'][0]['symbols']) == 10 and
                 actual['strategy_id'] == strategy_id and actual['allocation'] == 'EQUAL',
                 'Only the fixed ten-member equal momentum recipe in the two continuous quarters')
        report.update(allocation=allocation, strategy_id=strategy_id,
            inverse_volatility_is_not_equal_risk_contribution=allocation == 'INVERSE_VOL_30D')
        for name, digest in rb['source_hashes'].items():
            path = guard.project(plan.get('source_archives', {}).get(name, name))
            need(sha(path) == digest, 'Actual used source bytes: ' + name)
        report.update(actual_report_sha256=actual_sha, producer_run_binding_sha256=rb_sha,
            verified_source_hashes=rb['source_hashes'], protocol_sha256=plan['protocol_sha256'])
        need(len(actual['cases']) == actual['completed_cases'] == actual['required_cases'] == 4
             and actual['complete_calendar_cases'] == 4, 'Exactly four new complete scenario accounts')
        symbols = tuple(actual['cases'][0]['symbols']); pool_id = actual['cases'][0]['pool']
        pool = next(p for p in spec['pools'] if p['id'] == pool_id)
        need(list(symbols) == pool['symbols'] and len(symbols) == len(set(symbols)), 'One exact configured ordered pool')
        base, financial, proof = prepare_financial(symbols)
        report['financial_derivation'] = proof
        reference = base.module(base.REFERENCE, 'd050_independent_decimal_hand', base.REFERENCE_SHA)
        window = input_reader(spec, symbols, base, guard)
        expected_targets = target_reference(window, symbols, allocation, strategy_id=strategy_id)
        if sma_strategy:
            report.update(independent_SMA_state_witnesses=window['independent_SMA_state_witnesses'],
                independent_SMA_reference='SCALAR_FSUM50_200_FRESH_FLAT_STRICT_PREDICATES_NO_PRODUCER_OR_HOOK_IMPORT',
                equality_tolerance_band_used=False)
        if momentum_strategy:
            report.update(independent_momentum_state_witnesses=window['independent_momentum_state_witnesses'],
                independent_momentum_reference='DIRECT_COMPLETED_CLOSE_VS_30_DAYS_EARLIER_FRESH_FLAT_GT_ENTRY_LE_EXIT_NO_PRODUCER_OR_HOOK_IMPORT',
                momentum_completed_return_days=30, equality_exits_held_long=True,
                exit_then_wait_next_daily_decision=True, idle_raw_budget_redistributed=False,
                equality_tolerance_band_used=False)
        report['financial_input_bindings'] = window['proofs']
        if 'score_months' in scope:
            report.update(accepted_monthly_source_proofs=window['source_metadata_proofs'],
                continuous_account_path=spec['account_path'], monthly_account_reset=False,
                month_financial_attribution_scope='DAILY_ENDPOINT_STATE_INCLUDES_SAME_TIMESTAMP_FUNDING_LABEL_CLOSE_MINUS_1US_NOT_UTC_EVENT_MONTH_SUM',
                only_final_window_terminal_exit=True)
        need({(c['cost_id'], c['unit_id']) for c in actual['cases']} ==
             {(cost, unit) for cost in base.COSTS for unit in base.UNITS}, 'All predeclared cost/unit scenarios, no selection')
        for case in actual['cases']:
            need(tuple(case['symbols']) == symbols and case['pool'] == pool_id, 'Same shared account identity throughout')
            summary = case['summary']; contract = summary['contract']
            need(summary['version'] == 'usdt_linear_perpetual_closing_exempt_account_v2' and
                 contract['symbols'] == list(symbols) and contract['closing_min_notional_exempt'] is True and
                 contract['native_filters_certified'] is False and summary['mode'] == 'LONG_ONLY', 'Normal shared closing-profile identity')
            need(set(contract['instrument_profiles']) == set(symbols) and
                 all(p['quantity_step'] == '1E-8' and float(p['min_notional']) == 10 for p in
                     contract['instrument_profiles'].values()), 'Original declared quantity/minimum profile only')
            paths = {k: base.payload(v, Path(actual['run_dir'])) for k, v in case['artifacts'].items()}
            targets = pl.read_parquet(paths['targets.parquet'])
            need(targets.columns == expected_targets.columns and targets.height == expected_targets.height,
                 'Complete independent configured target schema/calendar')
            exact_keys = ('available_us', 'symbol', 'mode', 'eligibility_reason')
            if allocation == 'EQUAL':
                exact_keys += ('raw_signed_target',)
            for key in exact_keys:
                need(targets[key].to_list() == expected_targets[key].to_list(), 'Causal target identities/raw allocation: ' + key)
            if allocation == 'INVERSE_VOL_30D':
                base.same(targets['raw_signed_target'], expected_targets['raw_signed_target'],
                    'Independent capped past30 reciprocal raw sizes', errors, base.RATIO_TOL)
                zero = expected_targets['raw_signed_target'].eq(0)
                need(targets.filter(zero)['raw_signed_target'].eq(0).all() and
                     targets.filter(zero)['target_weight'].eq(0).all(), 'Unknown/exited allocation is exactly flat')
            base.same(targets['target_weight'], expected_targets['target_weight'], 'Independent N covariance weights', errors, base.RATIO_TOL)
            canonical = dict(case, period=scope['period_id'], mode='LONG_ONLY')
            progress.update('新共享N账户金融核验', len(report['cases']), 4, '账户', symbols=len(symbols),
                cost=case['cost_id'], funding_unit=case['unit_id'])
            result = financial(window, canonical, guard, reference, Path(actual['run_dir']), None, [], errors)
            if 'score_months' in scope:
                need(result['completed_days_verified'] == scope['period_days'] and result['completed_months_verified'] == 3,
                     'Complete continuous daily observations and all three months')
                result.update(continuous_accounting_verified=True,
                    cross_month_boundary_witnesses=continuous_boundary_witnesses(
                        window, result, paths['funding.json'], base, errors))
            report['cases'].append(dict(result, pool=pool_id, symbols=list(symbols),
                independent_HOLD_targets_verified=not (sma_strategy or momentum_strategy),
                independent_HOLD_allocation=allocation if not (sma_strategy or momentum_strategy) else None,
                independent_SMA50_200_targets_verified=sma_strategy, independent_strategy_targets_verified=True,
                independent_past30_momentum_targets_verified=momentum_strategy,
                independent_strategy_id=strategy_id))
            report['completed_cases_verified'] = len(report['cases'])
            gc.collect(); bounded()
        report.update(status=STATUS, required_cases=4, financial_case_calls=4,
            completed_full_calendar_cases_verified=sum(c['complete_calendar_verified'] for c in report['cases']),
            incomplete_or_halted_cases_verified=sum(not c['complete_calendar_verified'] for c in report['cases']),
            completed_source_files_verified=len(window['proofs']), complete_period_days=window['days'],
            completed_minutes_verified=sum(c['completed_minutes_verified'] for c in report['cases']),
            completed_days_verified=sum(c['completed_days_verified'] for c in report['cases']),
            completed_months_verified=sum(c['completed_months_verified'] for c in report['cases']))
    except Exception as error:
        report.update(error_type=type(error).__name__, reason=str(error))
        raise
    finally:
        report.update(elapsed_seconds=time.monotonic() - started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            resources_after=resources.status(), owned_bytes=sum(p.stat().st_size for p in args.run_dir.rglob('*') if p.is_file()))
        guard.write(args.output, report)
        append_event(ROOT / 'reports/experiment_registry.jsonl', dict(event, event_id=args.run_dir.name + ':RESULT',
            event_type='OPERATIONAL_RESEARCH_RESULT', success_failure=report['status'],
            artifact_path=str(args.output.relative_to(ROOT)), artifact_sha256=sha(args.output)))
        progress.stop.set(); progress.thread.join(timeout=3)
    print(json.dumps(dict(status=report['status'], cases=report['completed_cases_verified'], output=str(args.output))))


if __name__ == '__main__':
    main()
