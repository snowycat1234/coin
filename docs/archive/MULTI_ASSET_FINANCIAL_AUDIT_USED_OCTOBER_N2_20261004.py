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


def calendar_scope(spec):
    """Only the two explicitly authorized, complete seen UTC month windows."""
    first = datetime.fromisoformat(spec['start'])
    last = datetime.fromisoformat(spec['end_exclusive'])
    need(first.tzinfo is not None and last.tzinfo is not None and
         first.utcoffset().total_seconds() == last.utcoffset().total_seconds() == 0 and
         (first.day, first.hour, first.minute, first.second, first.microsecond) == (1, 0, 0, 0, 0),
         'Complete UTC month starts; no truncated or shifted decision clock')
    need(first.year == 2024 and first.month in (9, 10) and
         last == first.replace(month=first.month + 1), 'Only predeclared September/October seen scopes')
    days = (last - first).days
    return dict(start=first.isoformat(), end_exclusive=last.isoformat(),
        start_us=int(first.timestamp()) * 1_000_000, end_us=int(last.timestamp()) * 1_000_000,
        period_days=days, score_month=first.strftime('%Y-%m'),
        period_id=f'{first:%Y-%m}_{days}D', seen_development=True)


def input_reader(spec, symbols, base, guard):
    """Bound normal N sources, not the producer's loader or format QA."""
    manifest = spec['data_manifest']; path = Path(manifest['path'])
    value, _ = guard.small(path, manifest['sha256'])
    scope = calendar_scope(spec)
    start, end = scope['start_us'], scope['end_us']
    month = scope['score_month']
    times = np.arange(start, end, MINUTE, dtype=np.int64)
    if spec.get('data_role') == 'EXISTING_ACCEPTED_TWO_ASSET_CONTROL':
        need(tuple(symbols) == ('BTCUSDT', 'ETHUSDT') and
             manifest['sha256'] == '8b665b2829eafd192871fe4a3bc418dac1c202ed54f7d2d5494545fa6636fbfa' and
             value['status'] == 'PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS',
             'Existing accepted two-asset source scope')
        records = list(value['source_files'].values())
    else:
        manifest_status = ('PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS' if month == '2024-09'
            else 'PASS_D051_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS')
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
        acceptance_status = ('PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY' if month == '2024-09'
            else 'PASS_D051_FIXED_POOL_OCTOBER_SOURCE_FORMAT_ONLY')
        need(pool['status'] == 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS' and
             (list(symbols) == pool['symbols'] or tuple(symbols) == ('BTCUSDT', 'ETHUSDT')) and
             value['symbols'] == pool['symbols'] and pool['score_payloads_read'] == 0 and
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
        required_scope=scope, market={}, bars={}, events=[], proofs=[])
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
        trade = read(('klines', symbol, '1m', month), ['open_us', 'available_us', 'open', 'close', 'quote_volume']).sort('open_us')
        mark = read(('markPriceKlines', symbol, '1m', month), ['timestamp_ms', 'close']).sort('timestamp_ms')
        fund = read(('fundingRate', symbol, None, month), ['calc_time_ms', 'last_funding_rate']).sort('calc_time_ms')
        warm = pl.concat([read(('klines', symbol, '1d', '2024-' + m),
                ['open_us', 'close_us', 'available_us', 'close'])
            for m in ('02', '03', '04', '05', '06', '07', '08')]).sort('close_us')
        if month == '2024-10':
            prior_trade = read(('klines', symbol, '1m', '2024-09'), ['open_us', 'available_us', 'close']).sort('open_us')
            prior_start = int(datetime(2024, 9, 1, tzinfo=UTC).timestamp()) * 1_000_000
            warm = pl.concat([warm, daily_close(prior_trade, prior_start, start)]).sort('close_us')
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


def target_reference(window, symbols):
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
        financial_scope='RECORDED_SIGNED_LEGS_CONDITIONAL_FUNDING_SHARED_WALLET_MINUTE_DAY_MONTH_AND_HOLD_TARGETS',
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
        all_folds='PROTOCOL_BOUND_SEEN_FULL_UTC_MONTH_NEW_ACCOUNTS_ONLY', success_failure='START_BEFORE_FINANCIAL_PAYLOAD',
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
        need(spec['initial_capital_USDT'] == 10000 and
             spec['strategy'] == 'COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE', 'Same fixed capital and HOLD policy')
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
        expected_targets = target_reference(window, symbols)
        report['financial_input_bindings'] = window['proofs']
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
                 'Complete independent HOLD target schema/calendar')
            for key in ('available_us', 'symbol', 'raw_signed_target', 'mode', 'eligibility_reason'):
                need(targets[key].to_list() == expected_targets[key].to_list(), 'Causal target identities/raw allocation: ' + key)
            base.same(targets['target_weight'], expected_targets['target_weight'], 'Independent N covariance weights', errors, base.RATIO_TOL)
            canonical = dict(case, period=scope['period_id'], mode='LONG_ONLY')
            progress.update('新共享N账户金融核验', len(report['cases']), 4, '账户', symbols=len(symbols),
                cost=case['cost_id'], funding_unit=case['unit_id'])
            result = financial(window, canonical, guard, reference, Path(actual['run_dir']), None, [], errors)
            report['cases'].append(dict(result, pool=pool_id, symbols=list(symbols), independent_HOLD_targets_verified=True))
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
