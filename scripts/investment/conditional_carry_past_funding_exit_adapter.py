"""D032 static draft: one past-owned-coupon exit over two frozen carry contexts.

No new money loop. The legacy event loop, wallets, fee/quantity math and dispatch
are reused by exact AST anchors. This STATE draft is never a market CLI entry.
"""
from __future__ import annotations

import argparse
import ast
import math
from pathlib import Path
from types import FunctionType

from scripts.investment import conditional_carry_account as base
from scripts.investment import conditional_carry_reduce_adapter as trim
from scripts.investment import conditional_carry_90d_period_adapter as period90
from scripts.investment import bybit_spot_adapter as native

ROOT_PATH = 'scripts/investment/conditional_carry_past_funding_exit_adapter.py'
TEST = 'tests/test_conditional_carry_past_funding_exit.py'
PROTOCOL = 'protocols/CARRY_PAST_FUNDING_EXIT_D032_20261003_V1.json'
CONTRACT_ID = 'CARRY_PAST_FUNDING_EXIT_D032_V1'
STRATEGY_ID = 'CONDITIONAL_CARRY_PAIR_TRIM_PAST_OWNED_FUNDING_7D_LAG1_EXIT_V1'
DAY_US = 86_400_000_000
PINS = {
    trim.BASE_PATH: trim.BASE_SHA,
    trim.ROOT_PATH: '753b1653ff2db46a0e827ba6929b3dabccbb69d1ef98e278b82ccc6c84ca1130',
    period90.ROOT_PATH: 'a88b3d5d551216c34ab66abad07ecc4502c065de4c0eb6e9fdd0aa4a0c919574',
}
PARENT_CONTRACTS = {
    '122D': ('protocols/CONDITIONAL_CARRY_PAIR_TRIM_122D_20261003_V1.json',
             '5c13850c48e0cbd86bf2ae3629284f6b14d61803b0c299fef3796582ae5eba49'),
    '90D': ('protocols/CONDITIONAL_CARRY_90D_FIXED_PERIOD_20261003_V1.json',
            '84e14795c2622067b42c978225525773a06ecda3b8661f37f62cbc369609c3a3'),
}
GATE_RULES = dict(
    minimum_hold_us=8 * DAY_US, decision_clock='DAILY_UTC_CLOSED_DAY_00_00',
    decision_observation_offset_us=1, observed_window='[D-8DAY,D-1DAY)',
    window_start_strictly_after_entry=True, threshold_signed_owned_cash_USDT=0.,
    condition='SUM_LE_ZERO', publication_assumption='UNCERTIFIED_ONE_UTC_DAY_LAG',
    decision_arithmetic='MATH_FSUM_OF_ACTUAL_CREDITED_FLOAT64_LEDGER_CASH_EXACT_LE_ZERO_NO_BAND',
    input='ACTUALLY_OWNED_SIGNED_FUNDING_CASH_ACCOUNT_SUM_BOTH_SYMBOLS',
    action='NEXT_STRICTLY_LATER_CLOSED_MINUTE_ALL_FLAT_PERMANENT_CASH',
    priority='ALREADY_PENDING_FULL_EXIT_FIRST_EXISTING_DUE_TRIM_DISPATCH_UNCHANGED',
    no_reentry=True, no_extra_capital=True, no_HPO=True)
RULES = {**trim.RULES, 'past_funding_exit': GATE_RULES}
SMOKE_STATUS = 'PASS_D032_PAST_FUNDING_EXIT_SYNTHETIC_NOT_MARKET_OR_AVAILABILITY_PROOF'
ACTUAL_STATUS = 'COMPLETE_D032_PAST_FUNDING_EXIT_CONDITIONAL_SCREENING_NOT_LONG_TERM_APR'
EXIT_REASON = 'PAST_OWNED_FUNDING_7D_LAG1_NONPOSITIVE_PERMANENT_CASH'


def gate_witness(day_close_us, entry_us, funding_rows):
    """Read only mature owned cash rows, with a named unverified one-day lag."""
    base.need(type(day_close_us) is int and type(entry_us) is int,
              'Exact integer microsecond gate timestamps')
    base.need(day_close_us % DAY_US == 0, 'Only actual UTC day boundaries')
    observed_us = day_close_us + 1
    start, end = day_close_us - 8 * DAY_US, day_close_us - DAY_US
    result = dict(decision_price_close_us=day_close_us, decision_observation_us=observed_us,
        window_start_us=start, window_end_exclusive_us=end, entry_us=entry_us,
        publication_assumption=GATE_RULES['publication_assumption'],
        historical_availability_certified=False, eligible=False, action='NO_ACTION',
        selected_row_indices=[], selected_event_times_us=[], owned_event_count=0,
        signed_owned_funding_sum_USDT=None, maximum_assumed_available_us=None)
    if observed_us - entry_us < 8 * DAY_US:
        result['reason'] = 'HOLD_LESS_THAN_EXACT_EIGHT_DAYS'
        return result
    if start <= entry_us:
        result['reason'] = 'WINDOW_START_NOT_STRICTLY_AFTER_ENTRY'
        return result
    values, indices, stamps = [], [], []
    for index, row in enumerate(funding_rows):
        timestamp = row['event_us']
        base.need(type(timestamp) is int, 'Exact original event timestamp required')
        if not start <= timestamp < end:
            continue
        base.need(type(row['ownership_qualified']) is bool, 'Original ownership witness must be boolean')
        if not row['ownership_qualified']:
            continue
        value = row['signed_funding_USDT']
        base.need(type(value) in (int, float) and math.isfinite(value), 'Finite actually owned cash only')
        base.need(timestamp + DAY_US < observed_us, 'Selected event must satisfy the explicit lag')
        values.append(value); indices.append(index); stamps.append(timestamp)
    total = math.fsum(values)
    result.update(eligible=True, reason='FIXED_FULL_WINDOW_UNCERTIFIED_OWNED_CASH',
        selected_row_indices=indices, selected_event_times_us=stamps, owned_event_count=len(values),
        signed_owned_funding_sum_USDT=total,
        maximum_assumed_available_us=max(stamps) + DAY_US if stamps else None,
        condition_met=total <= 0.)
    return result


GATE_STATE_ANCHOR = 'pending_reductions, pair_reductions = {}, []'
GATE_STATE_REPLACEMENT = GATE_STATE_ANCHOR + '''
funding_gate_checks = []

def past_funding_exit(index, closed, snapshot):
    nonlocal pending_exit, stop_signal_us, exit_us, exit_reason
    if state != 'HELD' or closed % DAY_US:
        return
    witness = FUNDING_GATE_WITNESS(closed, entry_us, funding_rows)
    witness.update(account_state=state, pending_full_exit_before=pending_exit,
                   pending_pair_symbols_before=sorted(pending_reductions))
    if not witness['eligible']:
        funding_gate_checks.append(witness)
        return
    if pending_exit is not None:
        witness.update(action='KEEP_ALREADY_PENDING_FULL_EXIT', existing_exit_reason=exit_reason)
    elif witness['condition_met']:
        following = bisect_right(closes, snapshot)
        if following >= len(closes):
            witness.update(action='NO_FUTURE_CLOSED_PRICE_FIXED_TERMINAL_ONLY')
        else:
            pending_exit = following
            stop_signal_us, exit_us = snapshot, closes[following] + 1
            exit_reason = FUNDING_EXIT_REASON
            witness.update(action='SCHEDULE_PERMANENT_FULL_EXIT', fill_index=following,
                scheduled_fill_price_close_us=closes[following], scheduled_fill_us=exit_us)
    funding_gate_checks.append(witness)
'''
RISK_HOOK = "risk(index, snapshot, 'CLOSED_MINUTE_BEFORE_SCHEDULED_FILLS')"


def _fixed_parent(spec, selected):
    base.need(spec['contract_id'] == CONTRACT_ID and spec['rules'] == RULES
              and spec['gate_rules'] == GATE_RULES and set(spec['period_contracts']) == set(PARENT_CONTRACTS),
              'Exactly one fixed D032 gate across both accepted periods')
    base.need(selected in PARENT_CONTRACTS and 0 < spec['maximum_new_owned_bytes'] <= 25_000_000
              and 0 < spec['maximum_wall_seconds'] <= 600,
              'Two new accounts together no more than50MB; unchanged bounded wall budget')
    for name, expected in PINS.items():
        base.need(spec['frozen_sources'].get(name) == expected
                  and native.file_sha(base.ROOT / name) == expected, 'Exact accepted account code ' + name)
    for key, (path, sha) in PARENT_CONTRACTS.items():
        item = spec['period_contracts'][key]
        base.need(item['path'] == path and item['sha256'] == sha
                  and spec['frozen_sources'].get(path) == sha, 'Both exact accepted parent contracts')
    path, sha = PARENT_CONTRACTS[selected]
    parent = base.income.project_json(path, sha)
    if selected == '122D':
        trim.verify_spec(parent)
    else:
        period90.verify_spec(parent)
    base.need(spec['fee_reference_profile_path'] == parent['fee_reference_profile_path']
        and spec['fee_reference_profile_sha256'] == parent['fee_reference_profile_sha256'],
        'No lower fee or changed received-asset settlement')
    return parent


def _clone(origin):
    namespace = dict(origin)
    for key, obj in origin.items():
        if isinstance(obj, FunctionType) and obj.__globals__ is origin:
            namespace[key] = FunctionType(obj.__code__, namespace, obj.__name__, obj.__defaults__, obj.__closure__)
    return namespace


def _function_tree(name):
    source = base.ROOT / trim.BASE_PATH
    base.need(native.file_sha(source) == trim.BASE_SHA, 'Frozen base function source')
    nodes = [node for node in ast.parse(source.read_text()).body
             if isinstance(node, ast.FunctionDef) and node.name == name]
    base.need(len(nodes) == 1, 'Exactly one existing function ' + name)
    return ast.Module(body=nodes, type_ignores=[])


def _replay(tree, recorded, output):
    for row in recorded:
        if 'old_statement' in row:
            tree = native._replace(tree, output, 'REUSE_' + row['change'], row['old_statement'], row['new_statement'])
        else:
            base.need(row['change'] == 'PERIOD_METADATA_LITERAL', 'Only explicit accepted period literals')
            hits = [node for node in ast.walk(tree) if isinstance(node, ast.Constant) and node.value == row['old']]
            base.need(len(hits) == row['matches'], 'Exact accepted period literal count')
            for node in hits:
                node.value = row['new']
            output.append(dict(row, change='REUSE_PERIOD_METADATA_LITERAL'))
    return tree


def context(spec, selected):
    parent = _fixed_parent(spec, selected)
    origin = trim._compiled()[0] if selected == '122D' else period90.context(parent, 'PAIR_TRIM')
    namespace = _clone(origin)
    parent_receipt = trim.derivation_receipt()
    tree, changes = _function_tree('simulate_account'), []
    tree = _replay(tree, parent_receipt['changes'], changes)
    new_changes = []
    tree = native._replace(tree, new_changes, 'D032_GATE_STATE_AND_SCHEDULER',
                           GATE_STATE_ANCHOR, GATE_STATE_REPLACEMENT)
    tree = native._replace(tree, new_changes, 'D032_AFTER_EXISTING_RISK_BEFORE_FIXED_DISPATCH',
                           RISK_HOOK, RISK_HOOK + '\npast_funding_exit(index, closed, snapshot)')
    result_anchor = trim.RETURN_ANCHOR
    extra_summary = '''
summary.update(strategy_id=FUNDING_STRATEGY_ID, past_funding_exit_rules=FUNDING_GATE_RULES,
    past_funding_gate_checks=funding_gate_checks,
    past_funding_gate_scheduled=sum(r['action'] == 'SCHEDULE_PERMANENT_FULL_EXIT' for r in funding_gate_checks),
    funding_gate_publication_certified=False, gate_derivation=FUNDING_GATE_DERIVATION)
'''
    tree = native._replace(tree, new_changes, 'D032_GATE_CAUSAL_WITNESSES_ONLY',
                           result_anchor, extra_summary + result_anchor)
    ast.fix_missing_locations(tree)
    receipt = dict(base_sha256=trim.BASE_SHA, pair_trim_sha256=PINS[trim.ROOT_PATH],
        accepted_trim_derivation_sha256=parent_receipt['derived_AST_sha256'],
        period=selected, parent_contract_path=PARENT_CONTRACTS[selected][0],
        parent_contract_sha256=PARENT_CONTRACTS[selected][1],
        prior_period_derivation=origin.get('PERIOD_DERIVATION'),
        reused_accepted_trim_changes=changes, new_gate_changes=new_changes,
        derived_simulate_AST_sha256=native._digest(tree), event_loop_reordered=False,
        legacy_globals_mutated=False, original_financial_sources_unchanged=True)
    namespace.update(__file__=str(base.ROOT / ROOT_PATH), TEST=TEST, RULES=RULES,
        PARENT_SOURCE_MANIFEST_SHA256=parent['source_options_sha256'],
        FUNDING_PARENT_CONTRACT_PATH=PARENT_CONTRACTS[selected][0],
        FUNDING_PARENT_CONTRACT_SHA256=PARENT_CONTRACTS[selected][1],
        FUNDING_PERIOD_START=parent['period_start'], FUNDING_PERIOD_END=parent['period_end_exclusive'],
        SMOKE_STATUS=SMOKE_STATUS, ACTUAL_STATUS=ACTUAL_STATUS, PERIOD_ID=selected,
        FUNDING_GATE_WITNESS=gate_witness, FUNDING_GATE_RULES=GATE_RULES,
        FUNDING_GATE_DERIVATION=receipt, FUNDING_STRATEGY_ID=STRATEGY_ID,
        FUNDING_EXIT_REASON=EXIT_REASON, DAY_US=DAY_US)
    namespace['verify_spec'] = lambda candidate: _fixed_parent(candidate, selected)
    if selected == '122D':
        namespace['project_proofs'] = lambda _: base.project_proofs(parent)
    else:
        proof_function = origin['project_proofs']
        namespace['project_proofs'] = lambda _: proof_function(parent)
    exec(compile(tree, ROOT_PATH + ':D032_GATE_ONLY', 'exec'), namespace)
    # The existing runner/IO/START/finally RESULT stays authoritative. Only
    # replay accepted90 metadata and add a fixed selector + truthful gate report.
    main_tree, main_changes = _function_tree('main'), []
    if selected == '90D':
        main_tree = _replay(main_tree, origin['PERIOD_DERIVATION']['function_changes']['main'], main_changes)
        main_tree = native._replace(main_tree, main_changes, 'D032_KEEP_ONLY_PAIR_TRIM_PARENT',
            "parser.add_argument('--policy', choices=('ALL_FLAT', 'PAIR_TRIM'), required=True)",
            "parser.add_argument('--policy', choices=('PAIR_TRIM',), default='PAIR_TRIM')")
    else:
        main_tree = native._replace(main_tree, main_changes, 'D032_KEEP_ONLY_PAIR_TRIM_PARENT',
            "parser.add_argument('--experiment-id', required=True)",
            "parser.add_argument('--experiment-id', required=True)\nparser.add_argument('--policy', choices=('PAIR_TRIM',), default='PAIR_TRIM')")
    main_tree = native._replace(main_tree, main_changes, 'D032_FIXED_PERIOD_SELECTOR',
        'args = parser.parse_args()',
        "parser.add_argument('--period', choices=('122D', '90D'), required=True)\nargs = parser.parse_args()\nneed(args.period == PERIOD_ID and args.policy == 'PAIR_TRIM', 'Bootstrap period and fixed parent must agree')")
    main_tree = native._replace(main_tree, main_changes, 'D032_REPORT_RULE_AND_ASSUMPTION',
        'started = time.monotonic()',
        "started = time.monotonic()\nreport['gate_derivation'] = FUNDING_GATE_DERIVATION\nreport['period_id'] = PERIOD_ID\nreport['gate_rules'] = FUNDING_GATE_RULES\nreport['publication_assumption_certified'] = False\nreport['period_calendar'] = list(MONTHS)\nreport['period_start'] = FUNDING_PERIOD_START\nreport['period_end_exclusive'] = FUNDING_PERIOD_END\nreport['parent_contract_path'] = FUNDING_PARENT_CONTRACT_PATH\nreport['parent_contract_sha256'] = FUNDING_PARENT_CONTRACT_SHA256\nreport['parent_source_options_sha256'] = PARENT_SOURCE_MANIFEST_SHA256\nreport['research_scope'] = 'SEEN_WHOLE_PERIOD_SCREENING_NOT_UNSEEN'")
    # Registry data identity must be the selected accepted parent source manifest.
    manifest_keywords = [keyword for node in ast.walk(main_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name) and node.func.value.id == 'event'
        and node.func.attr == 'update' for keyword in node.keywords if keyword.arg == 'data_manifest_hash']
    base.need(len(manifest_keywords) == 1 and native._digest(manifest_keywords[0].value) ==
        native._digest(ast.parse("spec['source_options_sha256']", mode='eval').body),
        'One exact original registry manifest keyword, no source confusion between periods')
    manifest_keywords[0].value = ast.Name(id='PARENT_SOURCE_MANIFEST_SHA256', ctx=ast.Load())
    main_changes.append(dict(change='D032_SELECTED_PARENT_REGISTRY_SOURCE_MANIFEST', matches=1,
        value='EXACT_PARENT_SOURCE_OPTIONS_SHA256_NO_NEW_MARKET_MANIFEST'))
    ast.fix_missing_locations(main_tree)
    receipt.update(main_changes=main_changes, derived_main_AST_sha256=native._digest(main_tree))
    exec(compile(main_tree, ROOT_PATH + ':REUSE_EXISTING_MAIN', 'exec'), namespace)
    return namespace


def simulate_account(spec, selected, prices, events, progress=None):
    return context(spec, selected)['simulate_account'](prices, events, progress)


def derivation_receipt(spec, selected):
    return context(spec, selected)['FUNDING_GATE_DERIVATION']


def main():
    base.need(Path(__file__).resolve() == (base.ROOT / ROOT_PATH).resolve(),
              'Static STATE draft must be copied and independently frozen first')
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--period', choices=tuple(PARENT_CONTRACTS), required=True)
    args, _ = parser.parse_known_args()
    return context(base.income.project_json(args.protocol), args.period)['main']()


if __name__ == '__main__':
    main()