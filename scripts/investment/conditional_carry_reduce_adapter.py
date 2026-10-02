"""Exact AST pair-trim policy over the frozen conditional carry account.

No new engine: prices, cash, fees, margin, event loop, IO and metrics are reused.
A partial exit retains collateral, settles only its realized PnL, and cannot buy.
"""
from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path

from scripts.investment import conditional_carry_account as base
from scripts.investment import bybit_spot_adapter as native

BASE_PATH = 'scripts/investment/conditional_carry_account.py'
BASE_SHA = 'd29cf6ba9ec48c27f6b21eaab2167ff9ca7c39be2d762a9178f5e7dc2c6c001e'
ROOT_PATH = 'scripts/investment/conditional_carry_reduce_adapter.py'
TEST = 'tests/test_conditional_carry_reduce_adapter.py'
STRATEGY_ID = 'CONDITIONAL_CARRY_MATCHED_PAIR_TRIM_025_V1'
CONTRACT_ID = 'CONDITIONAL_CARRY_PAIR_TRIM_ACCOUNT_V1'
SMOKE_STATUS = 'PASS_CONDITIONAL_CARRY_PAIR_TRIM_SYNTHETIC_NOT_MARKET_RESULT'
ACTUAL_STATUS = 'COMPLETE_CONDITIONAL_CARRY_PAIR_TRIM_PROXY_UNIT_UNCERTIFIED_NOT_NATIVE_OR_LONG_TERM_APR'
RULES = {**base.RULES,
    'stop': 'MARGIN_ALL_FLAT_CAP_MATCHED_PAIR_TRIM_NEXT_STRICTLY_LATER_CLOSE',
    'pair_trim_target_two_leg_gross': .25,
    'pair_trim_quantity': 'MIN_HELD_025_SIGNAL_NAV_OVER_SIGNAL_SPOT_PLUS_MARK',
    'partial_close_collateral': 'RETAIN_OWN_POSTED_BALANCE_NO_RELEASE_OR_TOPUP',
    'partial_realized_PnL': 'FREE_CASH_FIRST_THEN_OWN_ISOLATED_BALANCE_FOR_SHORTFALL',
    'partial_event_ownership': 'AT_TRIM_TIE_EXCLUDE_CLOSING_CHUNK_KEEP_CONTINUING_CHUNK',
    'priority': 'DUE_FULL_EXIT_THEN_DUE_TRIMS_BTC_ETH_SPOT_THEN_PERP',
    'new_margin_signal': 'NO_RETROACTIVE_CANCEL_OF_ALREADY_DUE_TRIM',
    'total_cap_rounding_fallback': 'LARGEST_ASSET_GROSS_SYMBOL_TIE'}

STATE_ANCHOR = "state, exit_reason, pending_exit = 'WAIT_ENTRY', 'PROTOCOL_TERMINAL', None"
STATE_REPLACEMENT = STATE_ANCHOR + '''
pending_reductions, pair_reductions = {}, []

def reduce_due(index):
    for symbol in SYMBOLS:
        scheduled = pending_reductions.get(symbol)
        if scheduled is None or scheduled['fill_index'] != index:
            continue
        pending_reductions.pop(symbol)
        p = positions[symbol]
        quantity = scheduled['reduce_quantity']
        need(0 < quantity <= p['q'] and p['q'] == p['short_q'], 'Reduction only, from the frozen signal quantity')
        reserve_before = p['isolated_balance']
        nav_before = observe(index)[0]
        fill(symbol, 'SPOT', 'sell', quantity, spots[symbol][index], closes[index] + 1,
             closes[index], scheduled['signal_us'], 'MATCHED_PAIR_CAP_TRIM')
        fill(symbol, 'PERP', 'buy', quantity, marks[symbol][index], closes[index] + 1,
             closes[index], scheduled['signal_us'], 'MATCHED_PAIR_CAP_TRIM')
        need(p['q'] == p['short_q'] and p['q'] > 0, 'Matched positive remainder, never reenter or enlarge')
        nav_after, gross_after, assets_after, equity_after = observe(index)
        fill_rows[-1].update(partial_close=True, isolated_balance_released_USDT=0.,
            isolated_balance_before=reserve_before, isolated_balance_after=p['isolated_balance'],
            remaining_spot_quantity=p['q'], remaining_short_quantity=p['short_q'])
        pair_reductions.append(dict(scheduled, symbol=symbol, fill_us=closes[index] + 1,
            fill_price_close_us=closes[index], spot_mid=spots[symbol][index], mark_mid=marks[symbol][index],
            remaining_quantity=p['q'], isolated_balance_before=reserve_before,
            isolated_balance_after=p['isolated_balance'], isolated_equity_after=equity_after[symbol],
            NAV_before=nav_before, NAV_after=nav_after, asset_two_leg_gross_after=assets_after[symbol],
            total_gross_after=gross_after, target_is_signal_not_future_fill=True))
'''

RISK_REPLACEMENT = '''
def risk(index, timestamp, cause):
    nonlocal pending_exit, stop_signal_us, exit_us, exit_reason
    if state != 'HELD':
        return
    nav, gross, assets, equities = observe(index)
    margin = [s for s in SYMBOLS if equities[s] <= INITIAL_MARGIN * .5]
    breached = [s for s in SYMBOLS if assets[s] >= .3]
    reasons = (['TOTAL_GROSS'] if gross >= .6 else [])
    reasons += ['ASSET_GROSS_' + s for s in breached]
    reasons += ['ISOLATED_EQUITY_' + s for s in margin]
    if not reasons:
        return
    breach_rows.append(dict(signal_us=timestamp, cause=cause, reasons=reasons, nav=nav,
        total_gross=gross, asset_two_leg_gross=assets, isolated_equity=equities))
    if pending_exit is not None:
        return
    following = bisect_right(closes, timestamp)
    if following >= len(closes):
        return
    if margin:
        pending_exit = following
        stop_signal_us, exit_us = timestamp, closes[following] + 1
        exit_reason = 'SELF_DEFINED_ISOLATED_MARGIN_ALL_FLAT'
        return
    if gross >= .6 and not breached:
        breached = [max(SYMBOLS, key=lambda s: assets[s])]
    for symbol in breached:
        if symbol in pending_reductions:
            continue
        q = positions[symbol]['short_q']
        keep = min(q, .25 * nav / (spots[symbol][index] + marks[symbol][index]))
        reduction = q - keep
        need(keep > 0 and reduction > 0, 'Cap reduction must retain positive quantity and never buy')
        pending_reductions[symbol] = dict(signal_us=timestamp, signal_price_close_us=closes[index],
            signal_NAV=nav, signal_spot_close=spots[symbol][index], signal_mark_close=marks[symbol][index],
            signal_two_leg_gross=assets[symbol], fill_index=following, signal_held_quantity=q,
            keep_quantity=keep, reduce_quantity=reduction, target_two_leg_gross=.25)
'''

SPOT_ANCHOR = '''
if side == 'sell':
    need(abs(p['q']) <= 1e-10, 'Sell the exact received base; no fictional exchange filter')
    p['q'] = 0.
'''
SPOT_REPLACEMENT = '''
if side == 'sell':
    need(p['q'] >= 0, 'Sell at most the actually received base; never borrow or invent a filter')
'''

PERP_ANCHOR = '''
if side == 'sell':
    p['short_entry_fill'] = fill_price
    p['short_q'] = gross_q
else:
    realized = gross_q * (p['short_entry_fill'] - fill_price)
    cash += p['isolated_balance'] + realized
    p['isolated_balance'] = 0.
    p['short_entry_fill'] = 0.
    p['short_q'] = 0.
'''
PERP_REPLACEMENT = '''
if side == 'sell':
    need(p['short_q'] == 0., 'Only the original entry can increase the short')
    p['short_entry_fill'] = fill_price
    p['short_q'] = gross_q
else:
    need(0 <= gross_q <= p['short_q'], 'Close no more than the actually held short')
    realized = gross_q * (p['short_entry_fill'] - fill_price)
    remaining = p['short_q'] - gross_q
    if remaining == 0.:
        cash += p['isolated_balance'] + realized
        p['isolated_balance'] = 0.
        p['short_entry_fill'] = 0.
    elif realized >= 0.:
        cash += realized
        partial_realized_free_credit = realized
    else:
        partial_realized_free_debit, partial_realized_margin_debit = debit(symbol, -realized)
    p['short_q'] = remaining
'''

DISPATCH_ANCHOR = '''
if state == 'HELD' and (index == pending_exit or index == len(closes) - 1):
    leave(index)
'''
DISPATCH_REPLACEMENT = '''
if state == 'HELD' and (index == pending_exit or index == len(closes) - 1):
    leave(index)
    pending_reductions.clear()
elif state == 'HELD':
    reduce_due(index)
'''

OWNERSHIP_ANCHOR = "owned = state == 'HELD' and entry_us < timestamp < exit_us"
OWNERSHIP_REPLACEMENT = OWNERSHIP_ANCHOR + '''
qualified_quantity = p['short_q'] if owned else 0.
excluded_tie_quantity = p['short_q'] if timestamp == exit_us else 0.
reduction = pending_reductions.get(symbol)
if owned and reduction is not None and closes[reduction['fill_index']] + 1 == timestamp:
    excluded_tie_quantity = reduction['reduce_quantity']
    qualified_quantity = p['short_q'] - excluded_tie_quantity
need(qualified_quantity >= 0., 'Strict per-chunk ownership cannot include a negative quantity')
'''

RETURN_ANCHOR = '''
return dict(summary=summary, minute_nav=minute, daily_nav=daily,
            funding_ledger=pl.DataFrame(funding_rows) if funding_rows else None,
            fill_ledger=pl.DataFrame(fill_rows))
'''
RETURN_REPLACEMENT = '''
trim_nearby = [dict(event_us=row['event_us'], symbol=row['symbol'], fill_us=trim['fill_us'],
                   distance_us=abs(row['event_us']-trim['fill_us']))
               for row in funding_rows for trim in pair_reductions
               if row['symbol'] == trim['symbol'] and abs(row['event_us']-trim['fill_us']) <= 5_000_000]
summary.update(strategy_id=STRATEGY_ID, pair_trim_target_two_leg_gross=.25,
    pair_reductions=pair_reductions, completed_pair_reductions=len(pair_reductions),
    no_extra_capital_or_collateral_topups=True, paired_signal_quantity_only_reduces=True,
    events_within_5s_of_any_pair_reduction=len({(r['symbol'],r['event_us']) for r in trim_nearby}),
    pair_reduction_funding_boundary_witnesses=trim_nearby[:8],
    original_all_flat_source_sha256=BASE_SHA, derivation_receipt=DERIVATION_RECEIPT,
    real_funding_ownership_within_5s_guaranteed=False)
return dict(summary=summary, minute_nav=minute, daily_nav=daily,
            funding_ledger=pl.DataFrame(funding_rows) if funding_rows else None,
            fill_ledger=pl.DataFrame(fill_rows))
'''


def verify_spec(spec):
    base.need(spec['contract_id'] == CONTRACT_ID and spec['rules'] == RULES,
              'Only fixed matched-pair trim .25 at unchanged .3/.6 caps')
    base.need(spec['base_account_path'] == BASE_PATH and spec['base_account_sha256'] == BASE_SHA
              and spec['frozen_sources'].get(BASE_PATH) == BASE_SHA
              and spec['frozen_sources'].get(ROOT_PATH) == native.file_sha(__file__),
              'Separate frozen base and actual wrapper source before any arrays')
    base.verify_spec(dict(spec, contract_id='CONDITIONAL_CARRY_ACCOUNT_V1', rules=base.RULES))


@lru_cache(maxsize=1)
def _compiled():
    source = base.ROOT / BASE_PATH
    base.need(Path(base.__file__).resolve() == source.resolve() and native.file_sha(source) == BASE_SHA,
              'Exact unchanged accepted all-flat implementation required')
    tree = ast.parse(source.read_text())
    changes = []
    replacements = [('01_PENDING_PAIR_STATE', STATE_ANCHOR, STATE_REPLACEMENT)]
    risk_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'risk']
    base.need(len(risk_nodes) == 1, 'One nested original risk function')
    replacements += [('02_CAP_TRIM_MARGIN_FULL_POLICY', ast.unparse(risk_nodes[0]), RISK_REPLACEMENT),
        ('03_PARTIAL_RECEIVED_SPOT_SELL', SPOT_ANCHOR, SPOT_REPLACEMENT),
        ('04A_PARTIAL_REALIZED_WALLET_INITIALIZATION', 'realized = fee_free_debit = fee_margin_debit = 0.',
             'realized = fee_free_debit = fee_margin_debit = 0.\npartial_realized_free_credit = partial_realized_free_debit = partial_realized_margin_debit = 0.'),
        ('04B_PARTIAL_SHORT_REALIZED_RETAIN_RESERVE', PERP_ANCHOR, PERP_REPLACEMENT),
        ('05_FULL_EXIT_THEN_DUE_PAIR_DISPATCH', DISPATCH_ANCHOR, DISPATCH_REPLACEMENT),
        ('06A_STRICT_CHUNK_OWNERSHIP', OWNERSHIP_ANCHOR, OWNERSHIP_REPLACEMENT),
        ('06B_CURRENT_QUALIFIED_Q_FUNDING', "amount = p['short_q'] * marks[symbol][previous] * rate",
             'amount = qualified_quantity * marks[symbol][previous] * rate'),
        ('07_PAIR_POLICY_SUMMARY_AND_DERIVATION', RETURN_ANCHOR, RETURN_REPLACEMENT)]
    for name, old, new in replacements:
        tree = native._replace(tree, changes, name, old, new)
    # Preserve the original row fields, adding explicit partial-ownership witnesses.
    original_funding = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'funding')
    row_nodes = [n for n in ast.walk(original_funding) if isinstance(n, ast.Assign)
                 and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'row']
    base.need(len(row_nodes) == 1, 'One original funding ledger row')
    old_row = ast.unparse(row_nodes[0])
    new_row = old_row + '\nrow.update(qualified_short_quantity=qualified_quantity, closing_at_same_stamp_excluded_quantity=excluded_tie_quantity, ownership_rule="STRICT_ENTRY_PER_CHUNK_EXIT_UNCERTIFIED")'
    tree = native._replace(tree, changes, '06C_PARTIAL_OWNERSHIP_LEDGER', old_row, new_row)
    fill_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                  and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == 'append'
                  and isinstance(n.value.func.value, ast.Name) and n.value.func.value.id == 'fill_rows']
    base.need(len(fill_nodes) == 1, 'One original fill ledger append')
    old_fill = ast.unparse(fill_nodes[0])
    new_fill = old_fill + '\nfill_rows[-1].update(partial_realized_free_cash_credit=partial_realized_free_credit, partial_realized_free_cash_debit=partial_realized_free_debit, partial_realized_isolated_balance_debit=partial_realized_margin_debit, partial_realized_fields_scope="PARTIAL_CLOSE_ONLY")'
    tree = native._replace(tree, changes, '04C_PARTIAL_REALIZED_WALLET_LEDGER', old_fill, new_fill)
    ast.fix_missing_locations(tree)
    receipt = dict(base_path=BASE_PATH, base_sha256=BASE_SHA, adapter_path=str(Path(__file__).resolve()),
        adapter_sha256=native.file_sha(__file__), native_AST_adapter_path='scripts/investment/bybit_spot_adapter.py',
        native_AST_adapter_sha256=native.file_sha(base.ROOT / 'scripts/investment/bybit_spot_adapter.py'),
        derived_AST_sha256=native._digest(tree), changes=changes, expected_exact_anchor_matches=11,
        seven_change_groups=['STATE','RISK','SPOT','PERP','DISPATCH','FUNDING','SUMMARY'],
        original_all_flat_bytes_preserved=True, market_arrays_read_for_derivation=False)
    namespace = {'__name__': 'conditional_carry_pair_trim_derived', '__file__': str(Path(__file__).resolve())}
    exec(compile(tree, BASE_PATH + ':PAIR_TRIM_DERIVED', 'exec'), namespace)
    namespace.update(RULES=RULES, TEST=TEST, SMOKE_STATUS=SMOKE_STATUS, ACTUAL_STATUS=ACTUAL_STATUS,
                     verify_spec=verify_spec, STRATEGY_ID=STRATEGY_ID, BASE_SHA=BASE_SHA, DERIVATION_RECEIPT=receipt)
    return namespace, receipt


def simulate_account(prices, events, progress=None):
    return _compiled()[0]['simulate_account'](prices, events, progress)


def derivation_receipt():
    return _compiled()[1]


def main():
    base.need(Path(__file__).resolve() == (base.ROOT / ROOT_PATH).resolve(),
              'Review STATE draft first; CLI only from the separately frozen project adapter')
    return _compiled()[0]['main']()


if __name__ == '__main__':
    main()