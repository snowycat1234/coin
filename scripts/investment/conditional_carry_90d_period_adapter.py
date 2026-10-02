"""STATE static draft: fixed Dec-Feb context over accepted account kernels.
NOT executed or accepted. No account loop, fee formula or risk rule is copied.
The new source-view and new period-only synthetic acceptance must be frozen first.
"""
from __future__ import annotations
import ast
import json
from pathlib import Path
from types import FunctionType, SimpleNamespace

from scripts.investment import conditional_carry_account as base
from scripts.investment import conditional_carry_reduce_adapter as trim
from scripts.investment import bybit_spot_adapter as native

BASE_SHA = 'd29cf6ba9ec48c27f6b21eaab2167ff9ca7c39be2d762a9178f5e7dc2c6c001e'
TRIM_SHA = '753b1653ff2db46a0e827ba6929b3dabccbb69d1ef98e278b82ccc6c84ca1130'
MONTHS = ('2025-12', '2026-01', '2026-02')
START_US, END_US = 1764547200000000, 1772323200000000
MINUTES, DAYS, PRICE_FILES, FUNDING_FILES = 129600, 90, 18, 6
ROOT_PATH = 'scripts/investment/conditional_carry_90d_period_adapter.py'
TEST = 'tests/test_conditional_carry_90d_period_binding.py'
VIEW_STATUS = 'BOUND_ACCEPTED_CARRY_90D_SOURCE_VIEW_METADATA_ONLY_NOT_ACCOUNT_ACCEPTANCE'
POLICIES = {'ALL_FLAT': base.RULES, 'PAIR_TRIM': trim.RULES}


SOURCE_PROOFS = {
    'REUSED_SPOT': ('reports/fast_research/PUBLIC_STRATEGY_CHRONOLOGY_SOURCE_REUSE_20261002_V1.json',
        '388d3be0611c038df2f955a88c5be822e17d6cbda5f265fdef101f6abe23d8a2',
        'PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_151D_CALENDAR'),
    'NEW_SOURCE_PRODUCER': ('reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_ACTUAL_20261003_V1.json',
        'a67604972a30814c5764b107e7df69a3c08ac98625a78bf91565fa555dc70f0d',
        'OFFICIAL_CARRY_INPUT_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA'),
    'NEW_SOURCE_QA': ('reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_INDEPENDENT_QA_20261003_V1.json',
        '5cdffedb091b2a8ca2e469551a70332c3dd41973d807c267d54ed47d88734c60',
        'PASS_D031_OFFICIAL_SOURCE18_FORMAT_ONLY_INDEPENDENT_QA'),
    'NEW_SOURCE_ROOT_ACCEPTANCE': ('reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_ROOT_ACCEPTANCE_20261003_V1.json',
        'a9c197eb08378f044d1f0510919f71fdad06570a41a1f4927f813193ab75e270',
        'PASS_ROOT_D031_SOURCE18_FORMAT_ONLY_METADATA_ACCEPTANCE_NOT_ECONOMICS'),
}


def _proof_reports(view, spec):
    proofs = view['acceptance_proofs']
    base.need(len(proofs) == len(SOURCE_PROOFS)
        and {p['role'] for p in proofs} == set(SOURCE_PROOFS), 'Four exact accepted metadata roles')
    reports = {}
    for role, (path, digest, status) in SOURCE_PROOFS.items():
        proof = next(p for p in proofs if p['role'] == role)
        base.need((proof['path'], proof['sha256'], proof['required_status']) == (path, digest, status)
            and spec['frozen_sources'].get(path) == digest, 'Frozen official/source acceptance proof identity')
        reports[role] = base.income.project_json(path, digest)
        base.need(reports[role]['status'] == status, 'Exact actual source qualification, not declared PASS')
    root = reports['NEW_SOURCE_ROOT_ACCEPTANCE']
    base.need(root['producer_report_sha256'] == SOURCE_PROOFS['NEW_SOURCE_PRODUCER'][1]
        and root['independent_audit_report_sha256'] == SOURCE_PROOFS['NEW_SOURCE_QA'][1]
        and not root['funding_unit_certified'] and not root['economic_gate_passed'],
        'Producer-QA-root chain certifies source format only')
    return reports


def _one(rows, key, kind=True):
    selected = [r for r in rows if tuple(r[n] for n in
        (('kind', 'symbol', 'month') if kind else ('symbol', 'month'))) == key]
    base.need(len(selected) == 1, 'One exact metadata source row; duplicates rejected')
    return selected[0]


def _check_records(view, reports):
    """Pure direct row comparison; no arbitrary accepted-hash membership."""
    rows = view['sources']
    expected = {(kind, symbol, month) for kind in (*base.basis.KINDS, 'fundingRate')
        for symbol in base.SYMBOLS for month in MONTHS}
    base.need(len(rows) == 24 and
        {(r['kind'], r['symbol'], r['month']) for r in rows} == expected, 'Exactly new period source universe')
    root = reports['NEW_SOURCE_ROOT_ACCEPTANCE']
    base.need(view['accepted_new_source_state_root'] == root['source_data_directory'],
        'Exact actual accepted STATE source root')
    for row in rows:
        base.need(type(row['rows']) is int and row['rows'] > 0, 'Positive integer accepted rows')
        if row['kind'] == 'spot1m':
            old = _one(reports['REUSED_SPOT']['sources'], (row['symbol'], row['month']), False)
            base.need(row['provenance_role'] == 'REUSED_SPOT' and
                (row['rows'], row['parquet_path'], row['parquet_sha256']) ==
                (old['rows'], old['normalized_path'], old['normalized_sha256']),
                'Spot source identity must directly equal its accepted record')
        else:
            key = row['kind'], row['symbol'], row['month']
            rr = _one(root['source_receipt_proofs'], key)
            qa = _one(reports['NEW_SOURCE_QA']['sources'], key)
            producer = _one(reports['NEW_SOURCE_PRODUCER']['sources'], key)
            identity = (row['rows'], row['parquet_path'], row['parquet_sha256'],
                row['receipt_path'], row['receipt_sha256'])
            base.need(row['provenance_role'] == 'NEW_SOURCE_ROOT_ACCEPTANCE' and
                identity == (rr['rows'], rr['parquet']['path'], rr['parquet']['sha256'],
                             rr['receipt_path'], rr['receipt_sha256']),
                'New source identity must directly equal accepted root record')
            base.need(qa['status'] == 'PASS_SOURCE_FORMAT_ONLY' and qa['all_published_values_equal_raw']
                and (qa['rows'], qa['receipt_path'], qa['receipt_sha256']) ==
                    (row['rows'], row['receipt_path'], row['receipt_sha256'])
                and (producer['path'], producer['sha256']) == (row['receipt_path'], row['receipt_sha256']),
                'Each row requires direct independent QA and producer receipt linkage')
        _allowed_path(view, row)  # Metadata route only, no market file content or hash.
    counts = {symbol: sum(r['rows'] for r in rows
        if r['kind'] == 'fundingRate' and r['symbol'] == symbol) for symbol in base.SYMBOLS}
    base.need(counts == view['funding_counts_by_symbol'] and sum(counts.values()) == view['funding_event_total']
        and sum(counts.values()) == root['accepted_format']['funding_events']
        and sum(counts.values()) == reports['NEW_SOURCE_QA']['actual_funding_events'],
        'Observed funding counts derived consistently from all accepted records')
    return counts


def _small_receipt(view, row):
    expected = Path(view['accepted_new_source_state_root']) / (
        row['kind'] + '-' + row['symbol'] + '-' + row['month']) / 'receipt.json'
    path = Path(row['receipt_path'])
    base.need(path == expected and path.is_file() and not path.is_symlink()
        and path.resolve().is_relative_to(base.STATE.resolve()) and path.stat().st_size <= 1_000_000,
        'Only exact small accepted receipt JSON, never ZIP/CSV/Parquet')
    base.need(base.income.file_sha(path) == row['receipt_sha256'], 'Actual small receipt SHA changed')
    receipt = json.loads(path.read_bytes())
    base.need(base.income.file_sha(path) == row['receipt_sha256'], 'Small receipt changed during read')
    entry = receipt['entry']
    base.need((entry['kind'], entry['symbol'], entry['month']) ==
        (row['kind'], row['symbol'], row['month']) and
        (receipt['stats']['rows'], receipt['parquet_path'], receipt['parquet_sha256']) ==
        (row['rows'], row['parquet_path'], row['parquet_sha256']),
        'Actual receipt metadata directly matches selected identity')


def _view(spec):
    base.need(spec['source_view_path'] in spec['frozen_sources'] and
        spec['frozen_sources'][spec['source_view_path']] == spec['source_view_sha256'],
        'New source view frozen separately from old 122d acceptance')
    view = base.income.project_json(spec['source_view_path'], spec['source_view_sha256'])
    base.need(view['status'] == VIEW_STATUS and view['source_calendar'] == list(MONTHS)
        and view['period_start'] == '2025-12-01' and view['period_end_exclusive'] == '2026-03-01'
        and view['symbols'] == list(base.SYMBOLS), 'Exact new development period metadata')
    counts = _check_records(view, _proof_reports(view, spec))
    for row in view['sources']:
        if row['kind'] != 'spot1m':
            _small_receipt(view, row)
    return view, counts


def _allowed_path(view, row):
    # Scope rejection happens before examining any price/funding filesystem path.
    base.need(row['month'] in MONTHS and row['symbol'] in base.SYMBOLS
        and row['kind'] in (*base.basis.KINDS, 'fundingRate'), 'No March/locked source IO')
    opened, closed = base.basis.month_bounds(row['month'])
    base.need(START_US <= opened < closed <= END_US, 'Only Dec-Feb months')
    if row['kind'] == 'spot1m':
        expected = base.ROOT / 'data/normalized/spot' / row['symbol'] / '1m' / (row['month'] + '.parquet')
    else:
        source_root = Path(view['accepted_new_source_state_root']).resolve()
        base.need(source_root.is_relative_to(base.STATE.resolve()), 'New accepted STATE source root')
        expected = source_root / (row['kind'] + '-' + row['symbol'] + '-' + row['month']) / 'source.parquet'
    base.need(Path(row['parquet_path']).resolve() == expected.resolve()
        and not expected.is_symlink(), 'Exact accepted route, no source discovery')
    if row['kind'] != 'fundingRate':
        base.need(row['rows'] == (closed - opened) // base.MINUTE_US, 'Complete price calendar metadata')
    return expected, opened, closed


def verify_spec(spec):
    base.need(spec['contract_id'] == 'CONDITIONAL_CARRY_90D_FIXED_PERIOD_V1'
        and spec['policies'] == POLICIES
        and spec['period_start'] == '2025-12-01'
        and spec['period_end_exclusive'] == '2026-03-01'
        and spec['source_calendar'] == list(MONTHS)
        and spec['symbols'] == list(base.SYMBOLS)
        and spec['expected_price_files'] == PRICE_FILES
        and spec['expected_funding_files'] == FUNDING_FILES
        and spec['expected_minutes_per_asset'] == MINUTES,
        'Only the two fixed controls in one new 90-day development period')
    base.need(spec['frozen_sources'].get('scripts/investment/conditional_carry_account.py') == BASE_SHA
        and spec['frozen_sources'].get('scripts/investment/conditional_carry_reduce_adapter.py') == TRIM_SHA
        and spec['frozen_sources'].get(ROOT_PATH) == native.file_sha(__file__)
        and TEST in spec['frozen_sources'], 'Exact kernels and new period-only case')
    base.need(spec['funding_contract_path'] == 'protocols/FUNDING_INCOME_DIAGNOSTIC_122D_20261003_V1.json'
        and spec['funding_contract_sha256'] == '306749e93b82e70c4597be75dd1f0e548ba63b4937a2094d9d677ede34755db4'
        and spec['fee_reference_profile_path'] == native.PROFILE_PATH
        and spec['fee_reference_profile_sha256'] == native.PINS[native.PROFILE_PATH],
        'Reuse prior unit failure and current fee proof; do not certify new units')
    base.need(0 < spec['maximum_new_owned_bytes'] <= 50_000_000
        and 0 < spec['maximum_wall_seconds'] <= 600, 'Original small account budget')
    view, counts = _view(spec)
    base.need(spec['expected_funding_events'] == sum(counts.values())
        and spec['expected_funding_events_by_symbol'] == counts,
        'Frozen protocol counts must agree with accepted QA, not rate cadence')
    return view, counts


def _patch_function(name, namespace, replacements, literals=()):
    tree = ast.parse((base.ROOT / 'scripts/investment/conditional_carry_account.py').read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    base.need(len(nodes) == 1, 'One exact accepted function ' + name)
    tree = ast.Module(body=nodes, type_ignores=[])
    changes = []
    for label, old, new in replacements:
        tree = native._replace(tree, changes, label, old, new)
    # Explicit occurrences inside one exact original function, never global search/replace.
    for old, new, expected_count in literals:
        hits = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and n.value == old]
        base.need(len(hits) == expected_count, 'Exact period literal count in ' + name)
        for node in hits:
            node.value = new
        changes.append(dict(change='PERIOD_METADATA_LITERAL', old=old, new=new, matches=len(hits)))
    ast.fix_missing_locations(tree)
    namespace['PERIOD_DERIVATION']['function_changes'][name] = changes
    namespace['PERIOD_DERIVATION']['function_AST_sha256'][name] = native._digest(tree)
    exec(compile(tree, ROOT_PATH + ':' + name, 'exec'), namespace)


def context(spec, policy):
    base.need(policy in POLICIES, 'Only fixed ALL_FLAT and PAIR_TRIM controls')
    view, counts = verify_spec(spec)
    base.need(native.file_sha(base.ROOT / 'scripts/investment/conditional_carry_account.py') == BASE_SHA
        and native.file_sha(base.ROOT / 'scripts/investment/conditional_carry_reduce_adapter.py') == TRIM_SHA,
        'Old account source bytes remain exact')
    origin = base.__dict__ if policy == 'ALL_FLAT' else trim._compiled()[0]
    namespace = dict(origin)
    # Rebind existing Python bytecode to isolated globals, never mutate legacy modules.
    for key, obj in origin.items():
        if isinstance(obj, FunctionType) and obj.__globals__ is origin:
            namespace[key] = FunctionType(obj.__code__, namespace, obj.__name__, obj.__defaults__, obj.__closure__)
    proxy_basis = SimpleNamespace(**vars(base.basis))
    proxy_basis.allowed_path = lambda row: _allowed_path(view, row)
    namespace.update(basis=proxy_basis, MONTHS=MONTHS, START_US=START_US, END_US=END_US,
        __file__=str(base.ROOT / ROOT_PATH), RULES=POLICIES[policy], TEST=TEST,
        verify_spec=verify_spec, EXPECTED_FUNDING_TOTAL=sum(counts.values()), EXPECTED_BY_SYMBOL=counts,
        SMOKE_STATUS='PASS_CARRY_90D_PERIOD_SOURCE_ENDPOINT_SYNTHETIC_ONLY',
        ACTUAL_STATUS='COMPLETE_CARRY_90D_DEVELOPMENT_EXTRAPOLATION_CONDITIONAL_NOT_LONG_TERM_APR',
        PERIOD_POLICY=policy, PERIOD_SOURCE_VIEW_SHA256=spec['source_view_sha256'],
        PERIOD_DERIVATION=dict(base_sha256=BASE_SHA, pair_trim_sha256=TRIM_SHA,
            policy=policy, period_calendar=list(MONTHS), function_changes={}, function_AST_sha256={},
            old_simulate_code_unchanged=True, legacy_globals_mutated=False))
    original_validate = namespace['validate_inputs']
    def validate(prices, events):
        closes = original_validate(prices, events)
        base.need(START_US <= closes[0] - base.MINUTE_US < closes[-1] <= END_US,
            'No post-Feb prices, even for the pure endpoint fixture')
        return closes
    namespace['validate_inputs'] = validate
    def proofs(_):
        old = base.income.project_json(spec['funding_contract_path'], spec['funding_contract_sha256'])
        probe = base.income.project_json(old['unit_probe']['path'], old['unit_probe']['sha256'])
        units = base.income.validate_units(old, probe)
        base.need(units.get('conditional_fraction_assumption'), 'Only prior explicit unverified fraction branch')
        units = dict(units, current_period_archive_unit_certified=False,
            current_period_source_calendar=list(MONTHS), legacy_unit_proof_scope='PRIOR_AUG2025_PROBE_ZERO_MATCHED')
        native._pins()
        return ([r for r in view['sources'] if r['kind'] != 'fundingRate'],
                [r for r in view['sources'] if r['kind'] == 'fundingRate'], units)
    namespace['project_proofs'] = proofs
    _patch_function('load_inputs', namespace, [
        ('NEW_QA_DERIVED_EVENT_COUNTS',
         "need(events.height == 732 and all(events.filter(pl.col('symbol') == s).height == 366 for s in SYMBOLS), 'All732 signed events; no selection by rate, month or account state')",
         "need(events.height == EXPECTED_FUNDING_TOTAL and all(events.filter(pl.col('symbol') == s).height == EXPECTED_BY_SYMBOL[s] for s in SYMBOLS), 'All new accepted events; no rate/month/state selection')")],
         [(32, 24, 2)])
    _patch_function('main', namespace, [
        ('ONLY_FIXED_CONTROL_SELECTOR',
         "parser.add_argument('--experiment-id', required=True)",
         "parser.add_argument('--experiment-id', required=True)\nparser.add_argument('--policy', choices=('ALL_FLAT', 'PAIR_TRIM'), required=True)"),
        ('NEW_PERIOD_DERIVATION_AND_SCOPE',
         "started = time.monotonic()",
         "started = time.monotonic()\nreport['period_derivation'] = PERIOD_DERIVATION\nreport['policy'] = PERIOD_POLICY\nreport['source_view_sha256'] = PERIOD_SOURCE_VIEW_SHA256\nreport['research_scope'] = 'DEVELOPMENT_TIME_EXTRAPOLATION_SCREENING_NOT_UNSEEN'"),
        ('NEW_COMPLETE_PERIOD_COUNTS',
         "need(result['minute_nav'].height == 175680 and result['daily_nav'].height == 122 and result['summary']['all_source_events'] == 732, 'Full period and complete original events')",
         "need(result['minute_nav'].height == 129600 and result['daily_nav'].height == 90 and result['summary']['all_source_events'] == EXPECTED_FUNDING_TOTAL, 'Full new90d and all accepted events')")],
         [(32, 24, 1), ('FULL122D_24_CLOSE_AND8_FUNDING_FILES_CONDITIONAL',
           'FULL90D_18_CLOSE_AND6_FUNDING_DEVELOPMENT_CONDITIONAL', 1),
          ('ONE_CONTINUOUS_FULL122D_ACCOUNT', 'ONE_CONTINUOUS_90D_DEVELOPMENT_NOT_UNSEEN', 1)])
    return namespace


def derivation_receipt(spec, policy):
    return context(spec, policy)['PERIOD_DERIVATION']


def simulate_account(spec, policy, prices, events, progress=None):
    result = context(spec, policy)['simulate_account'](prices, events, progress)
    result['summary'].update(period_start='2025-12-01', period_end_exclusive='2026-03-01',
        period_policy=policy, research_scope='DEVELOPMENT_TIME_EXTRAPOLATION_SCREENING_NOT_UNSEEN')
    return result


def main():
    # Delegates the accepted START/finally RESULT/progress/IO/account output runner.
    # The new protocol must point to a fresh 90d period/source/endpoint case and receipt.
    base.need(Path(__file__).resolve() == (base.ROOT / ROOT_PATH).resolve(),
        'STATE draft is never a runnable market entry')
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--policy', choices=tuple(POLICIES), required=True)
    args, _ = parser.parse_known_args()
    spec = base.income.project_json(args.protocol)
    return context(spec, args.policy)['main']()


if __name__ == '__main__':
    main()
