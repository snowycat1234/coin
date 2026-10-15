"""Pure saved-evidence native40 event reconstruction; never constructs an account.

The independent arithmetic below follows the pinned BASE27 1x native debit,
partial-margin and takeover operation order. Raw precision100 stored-delta sums
are retained as diagnostics, never used to repair a financial value.
"""
from decimal import Decimal, localcontext
from hashlib import sha256
import json
from pathlib import Path

VERSION = 'SAVED_NATIVE40_CHRONOLOGICAL_EXACT_RECONSTRUCTION_V1'
INITIAL = Decimal('10000')
FEE_RATE = Decimal('0.00055')  # frozen native BASE27 audit config / grid
LEVERAGE = Decimal('1')
HALTS = ('LIQUIDATION_REQUIRED_HALT', 'BANKRUPT_HALT')


def checker_sha256():
    return sha256(Path(__file__).read_bytes()).hexdigest()


def canonical_sha256(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _d(value):
    if type(value) is not str:
        raise ValueError('EXACT_FINITE_DECIMAL_STRING_REQUIRED')
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError('EXACT_FINITE_DECIMAL_STRING_REQUIRED')
    return result


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def reconcile_saved_native(audit, result=None, *, expected_policy_variant='GUARD50_EXIT_ONLY',
                           expected_continuation_version=None):
    """Reconstruct every saved event and intermediate trade, with exact equality.

    Accepts ordinary saved dictionaries and returns a reporting proof. It has no
    account, scheduler, source, download or output-writing dependency.
    """
    _check(type(audit) is dict, 'SAVED_AUDIT_DICTIONARY_REQUIRED')
    symbols = tuple(audit['symbols'])
    _check(bool(symbols) and len(set(symbols)) == len(symbols), 'EXACT_UNIQUE_SYMBOL_ORDER_REQUIRED')
    _check(set(audit['positions']) == set(symbols), 'EXACT_POSITION_SYMBOLS_REQUIRED')
    config = audit['config']
    _check(_d(config['initial_cash']) == INITIAL and _d(config['fee_rate']) == FEE_RATE
           and _d(config['leverage']) == LEVERAGE
           and _d(config['half_spread_bps']) == Decimal(4)
           and _d(config['slippage_bps']) == Decimal(4)
           and _d(config['maintenance_margin_rate']) == Decimal('.005'), 'FROZEN_BASE27_ONE_X_CONFIG_REQUIRED')
    _check(type(audit.get('transfer_journal')) is list and not audit['transfer_journal']
           and type(audit.get('transfer_ids')) is dict and not audit['transfer_ids'], 'NO_INTERNAL_TRANSFER_RECONSTRUCTION_REQUIRED')
    contract = audit['contract']
    _check(contract.get('policy_variant') == expected_policy_variant
           and contract.get('topup_enabled') is False
           and contract.get('automatic_topup', False) is False, 'SAVED_NO_TOPUP_POLICY_REQUIRED')
    if expected_continuation_version is not None:
        _check(audit.get('continuation_policy') == expected_continuation_version
               and contract.get('continuation_policy') == expected_continuation_version,
               'SAVED_CONTINUATION_VERSION_REQUIRED')
    ledger, trades, funds, settlements = (audit[key] for key in
        ('financial_ledger', 'trades', 'funding', 'settlement_journal'))
    for rows in (ledger, trades, funds, settlements):
        _check(type(rows) is list, 'SAVED_EVENT_LIST_REQUIRED')
    rounded = []
    for rows, identity in ((trades, lambda r:r['fill_id']), (funds, lambda r:r['event_id'])):
        ids = [identity(r) for r in rows]
        _check(all(type(i) is str and i for i in ids) and len(ids) == len(set(ids)), 'UNIQUE_NATIVE_EVENT_IDS_REQUIRED')
        clocks = [r['event_us'] for r in rows]
        _check(all(type(c) is int and c >= 0 for c in clocks) and clocks == sorted(clocks), 'CHRONOLOGICAL_NATIVE_EVENT_CLOCKS_REQUIRED')
    funding_keys = [(r['symbol'],r['event_us']) for r in funds]
    _check(len(funding_keys) == len(set(funding_keys)), 'UNIQUE_NATIVE_SYMBOL_FUNDING_CLOCK_REQUIRED')
    with localcontext() as ctx:
        ctx.prec = 40
        cash, debt = INITIAL, Decimal(0)
        positions = {s: dict(q=Decimal(0), basis=Decimal(0), margin=Decimal(0), opened=None) for s in symbols}
        totals = dict(fees=Decimal(0), realized_PnL=Decimal(0), execution_cost=Decimal(0),
                      funding_cash=Decimal(0), gross_fill_turnover=Decimal(0))
        ti = fi = si = 0
        previous_event = -1

        def debit(symbol, amount):
            nonlocal cash, debt
            _check(min(amount, cash, positions[symbol]['margin'], debt) >= 0, 'NONNEGATIVE_NATIVE_DEBIT_STATE_REQUIRED')
            paid = min(cash, amount)
            cash -= paid
            remainder = amount - paid
            if remainder > 0:
                own = min(positions[symbol]['margin'], remainder)
                positions[symbol]['margin'] -= own
                debt += remainder - own

        def trade(row):
            nonlocal cash, si
            d, symbol = row['decimal_strings'], row['symbol']
            _check(symbol in positions and row['side'] in ('BUY', 'SELL'), 'NATIVE_TRADE_SYMBOL_SIDE_REQUIRED')
            p = positions[symbol]
            q, basis, margin, before_cash = p['q'], p['basis'], p['margin'], cash
            amount, fill, mid = (_d(d[key]) for key in ('quantity', 'fill_price', 'execution_mid_price'))
            direction = Decimal(1 if row['side'] == 'BUY' else -1)
            _check(type(row['signal_us']) is int and row['signal_us'] >= 0, 'EXACT_NATIVE_SIGNAL_CLOCK_REQUIRED')
            _check(row['leg'] == ('OPEN' if not q or q * direction > 0 else 'CLOSE'), 'EXACT_NATIVE_TRADE_LEG_REQUIRED')
            _check(amount > 0 and fill >= 0 and mid >= 0
                   and q == _d(d['quantity_before']) and basis == _d(d['entry_price_before']), 'NATIVE_TRADE_PRESTATE_REQUIRED')
            allocated = released = realized = Decimal(0)
            if row.get('liquidation_takeover'):
                _check(q != 0 and direction * q < 0 and amount == abs(q)
                       and margin == _d(d['takeover_margin_loss'])
                       and fill == basis - (Decimal(1) if q > 0 else Decimal(-1)) * margin / abs(q)
                       and mid == fill, 'EXACT_CONDITIONAL_TAKEOVER_REQUIRED')
                released, realized = margin, -margin
                fee = cost = Decimal(0)
                _check(si < len(settlements), 'TAKEOVER_SETTLEMENT_ROW_REQUIRED')
                settlement = settlements[si];si += 1
                sd = settlement['decimal_strings'];mark = _d(d['mark_price'])
                equity = margin + q * (mark - basis)
                maintenance = abs(q) * mark * _d(config['maintenance_margin_rate'])
                support, forfeiture = max(Decimal(0), -equity), max(Decimal(0), equity)
                _check(settlement['symbol'] == symbol and settlement['event_us'] == row['event_us']
                       and equity <= maintenance and audit['settlement_mode'] == 'CONDITIONAL_COLLATERAL_FORFEITURE',
                       'EXACT_NATIVE_TRIGGERED_CONDITIONAL_SETTLEMENT_REQUIRED')
                for key, value in dict(pre_settlement_equity=equity, pre_settlement_maintenance=maintenance,
                        conditional_NAV_adjustment=-equity, conditional_overshoot_absorption=support,
                        conditional_positive_residual_forfeited=forfeiture, marked_equity_before=equity,
                        conditional_insurance_value_received=support, conditional_forfeiture_value_paid=forfeiture,
                        settlement_value_cashflow=support-forfeiture, marked_equity_after=Decimal(0),
                        value_ledger_error=Decimal(0), free_cash_credit=Decimal(0), additional_liquidation_fee=Decimal(0)).items():
                    _check(_d(sd[key]) == value, 'CONDITIONAL_SETTLEMENT_VALUE_MISMATCH:' + key)
                _check(_d(sd['NAV_after']) - _d(sd['NAV_before']) == -equity,
                       'CONDITIONAL_SETTLEMENT_NAV_MISMATCH')
                p.update(q=Decimal(0), basis=Decimal(0), margin=Decimal(0), opened=None)
            else:
                _check(fill > 0 and mid > 0, 'POSITIVE_PAID_EXECUTION_PRICE_REQUIRED')
                _check(fill == mid * (1 + direction * Decimal('.0008'))
                       and row['event_us'] >= ((row['signal_us'] + 60_000_000 - 1)//60_000_000 + 1)*60_000_000 + 1,
                       'EXACT_BASE27_PRICE_AND_NATIVE_LATENCY_REQUIRED')
                fee = amount * fill * FEE_RATE
                if not q or q * direction > 0:
                    allocated = amount * fill / LEVERAGE
                    _check(cash >= allocated + fee, 'OPEN_NATIVE_FREE_MARGIN_REQUIRED')
                    newq = q + direction * amount
                    p['basis'] = (abs(q) * basis + amount * fill) / abs(newq)
                    cash -= allocated + fee
                    p['margin'] += allocated
                    p['q'] = newq
                    if not q:p['opened'] = row['event_us']
                else:
                    _check(amount <= abs(q), 'CLOSING_LEG_CANNOT_CROSS_ZERO')
                    released = margin if amount == abs(q) else margin * amount / abs(q)
                    realized = (Decimal(1) if q > 0 else Decimal(-1)) * amount * (fill - basis)
                    p['margin'] -= released
                    cash += released
                    p['q'] += direction * amount
                    if realized >= 0:cash += realized
                    else:debit(symbol, -realized)
                    debit(symbol, fee)
                    if not p['q']:
                        cash += p['margin']
                        p.update(margin=Decimal(0), basis=Decimal(0), opened=None)
                cost = amount * abs(fill - mid)
            expected = dict(quantity_after=p['q'], entry_price_after=p['basis'], fee_amount=fee,
                fee_USDT_mid=fee, execution_cost=cost, realized_PnL=realized, margin_allocated=allocated,
                margin_released=released, free_cash_delta=cash-before_cash,
                isolated_balance_delta=p['margin']-margin, gross_quantity=amount,
                position_delta=direction*amount, cash_delta=realized-fee, mid_price=mid)
            for key, value in expected.items():
                _check(_d(d[key]) == value, 'NATIVE_TRADE_EXACT_FIELD_MISMATCH:' + key)
            totals['fees'] += fee;totals['realized_PnL'] += realized
            totals['execution_cost'] += cost;totals['gross_fill_turnover'] += amount * fill

        def funding(row):
            nonlocal cash
            d, symbol = row['decimal_strings'], row['symbol'];p = positions[symbol]
            _check(symbol in positions and type(row['owned']) is bool, 'EXACT_NATIVE_FUNDING_SYMBOL_OWNERSHIP_REQUIRED')
            owned = bool(p['q'] and p['opened'] is not None and p['opened'] < row['event_us'])
            amount = -p['q'] * _d(d['mark_price']) * _d(d['rate_fraction']) if owned else Decimal(0)
            _check(row['owned'] == owned and _d(d['quantity']) == p['q']
                   and _d(d['signed_funding_USDT']) == amount
                   and row['rate_available_us'] <= row['event_us'] and row['mark_close_us'] < row['event_us'],
                   'EXACT_NATIVE_FUNDING_ARITHMETIC_OWNERSHIP_REQUIRED')
            if amount >= 0:cash += amount
            else:debit(symbol, -amount)
            totals['funding_cash'] += amount

        for index, row in enumerate(ledger):
            event = row['event_us'];kind = row['kind']
            _check(type(event) is int and event >= previous_event and type(row['sequence']) is int
                   and row['sequence'] == index + 1, 'CHRONOLOGICAL_CONTIGUOUS_LEDGER_REQUIRED')
            previous_event = event
            before_cash, before_debt, before_si = cash, debt, si
            before_p = {s: dict(p) for s, p in positions.items()}
            before_t = dict(totals)
            while fi < len(funds) and _d(funds[fi]['decimal_strings']['signed_funding_USDT']) == 0 and (funds[fi]['event_us'] < event or kind != 'NATIVE_MARK_RISK' and funds[fi]['event_us'] == event):
                funding(funds[fi]);fi += 1
            if kind == 'NATIVE_FUNDING':
                _check(fi < len(funds) and funds[fi]['event_us'] == event, 'EXACT_FUNDING_LEDGER_ORDER_REQUIRED')
                funding(funds[fi]);fi += 1
            else:
                _check(kind in ('NATIVE_MARK_RISK', 'NATIVE_PAID_FILL'), 'UNEXPECTED_NO_TRANSFER_FINANCIAL_KIND:' + str(kind))
            _check(set(row['quantity_delta']) == set(symbols) and set(row['isolated_delta']) == set(symbols),
                   'EXACT_LEDGER_SYMBOLS_REQUIRED')
            target = {s: _d(row['quantity_delta'][s]) for s in symbols}
            count = row['conditional_settlements_delta']
            _check(type(count) is int and count >= 0, 'EXACT_SETTLEMENT_COUNT_REQUIRED')
            while any(positions[s]['q'] - before_p[s]['q'] != target[s] for s in symbols) or si-before_si != count:
                _check(ti < len(trades) and trades[ti]['event_us'] == event, 'EXACT_TRADE_LEDGER_ORDER_REQUIRED')
                _check(kind == 'NATIVE_PAID_FILL' or trades[ti].get('liquidation_takeover') is True,
                       'MARK_OR_FUNDING_BATCH_CANNOT_CREATE_PAID_FILL')
                trade(trades[ti]);ti += 1
                _check(si-before_si <= count, 'EXACT_SETTLEMENT_LEDGER_COUNT_REQUIRED')
            observed = dict(free_cash_delta=cash-before_cash, unpaid_liability_delta=debt-before_debt,
                fee_delta=totals['fees']-before_t['fees'], realized_delta=totals['realized_PnL']-before_t['realized_PnL'],
                funding_delta=totals['funding_cash']-before_t['funding_cash'], free_cash_after=cash, unpaid_liability_after=debt)
            for key, value in observed.items():
                _check(_d(row[key]) == value, 'NATIVE40_LEDGER_EXACT_FIELD_MISMATCH:' + key)
            balances = [('free_cash', before_cash, cash, _d(row['free_cash_delta'])),
                        ('unpaid_liability', before_debt, debt, _d(row['unpaid_liability_delta']))]
            for s in symbols:
                delta = _d(row['isolated_delta'][s])
                _check(positions[s]['margin']-before_p[s]['margin'] == delta, 'NATIVE40_ISOLATED_DELTA_MISMATCH:' + s)
                balances.append((s, before_p[s]['margin'], positions[s]['margin'], delta))
            with localcontext() as exact:
                exact.prec = 100
                for balance, before, after, delta in balances:
                    residual = after-before-delta
                    if residual:
                        rounded.append(dict(sequence=index+1, kind=kind, event_us=event, balance=balance,
                            before=str(before), after=str(after), stored_native40_delta=str(delta),
                            precision100_subtraction_minus_stored_delta=str(residual)))
        while fi < len(funds):
            _check(_d(funds[fi]['decimal_strings']['signed_funding_USDT']) == 0, 'UNCONSUMED_NONZERO_FUNDING')
            funding(funds[fi]);fi += 1
        _check(ti == len(trades) and si == len(settlements), 'UNCONSUMED_TRADE_OR_SETTLEMENT')
        _check(cash == _d(audit['free_cash']) and debt == _d(audit['unpaid_liability']), 'FINAL_NATIVE_CASH_DEBT_MISMATCH')
        for s, p in positions.items():
            for key, field in (('q', 'quantity'), ('basis', 'entry_price'), ('margin', 'isolated_balance')):
                _check(p[key] == _d(audit['positions'][s][field]), 'FINAL_NATIVE_POSITION_MISMATCH:' + s + ':' + field)
            _check(p['opened'] == audit['positions'][s]['opened_us'], 'FINAL_NATIVE_POSITION_OPEN_CLOCK_MISMATCH')
        for key, value in totals.items():
            _check(value == _d(audit['totals'][key]), 'FINAL_NATIVE_TOTAL_MISMATCH:' + key)
        unrealized = sum((p['q'] * (_d(audit['marks'][s][-1]['price'])-p['basis'])
                          for s, p in positions.items() if p['q']), Decimal(0))
        nav = cash - debt
        for s, p in positions.items():
            nav += p['margin']
            if p['q']:nav += p['q'] * (_d(audit['marks'][s][-1]['price'])-p['basis'])
        gross_mid = totals['realized_PnL'] + unrealized + totals['execution_cost']
        bridge = (nav-INITIAL) - (gross_mid-totals['execution_cost']-totals['fees']+totals['funding_cash'])
        if result is not None:
            summary = result['summary'];ds = summary['decimal_strings']
            for key, value in dict(NAV=nav, free_cash=cash, unpaid_liability=debt,
                    fees_USDT=totals['fees'], funding_USDT=totals['funding_cash'],
                    execution_cost_USDT=totals['execution_cost'], realized_PnL=totals['realized_PnL'],
                    unrealized_PnL=unrealized, accounting_bridge_error_USDT=bridge).items():
                _check(_d(ds[key]) == value, 'SAVED_RESULT_NATIVE_EXACT_FIELD_MISMATCH:' + key)
            _check(summary['account_status'] == audit['status'] and summary.get('halt_witness') == audit.get('halt_witness'),
                   'SAVED_RESULT_STATUS_WITNESS_MISMATCH')
            _check(set(summary['positions']) == set(symbols), 'SAVED_RESULT_POSITION_SYMBOLS_REQUIRED')
            for symbol in symbols:
                sp = summary['positions'][symbol];ap = audit['positions'][symbol]
                for key in ('quantity','entry_price','isolated_balance'):
                    _check(_d(sp['decimal_strings'][key]) == _d(ap[key]), 'SAVED_RESULT_EXACT_POSITION_MISMATCH')
                _check(sp['opened_us'] == ap['opened_us'], 'SAVED_RESULT_POSITION_OPEN_CLOCK_MISMATCH')
            _check(result['trades'] == trades, 'SAVED_RESULT_TRADE_ROWS_MISMATCH')
            reported_funds = {(r['symbol'], r['event_us']): r for r in result['funding']}
            for f in funds:
                rf = reported_funds.get((f['symbol'], f['event_us']))
                _check(isinstance(rf, dict) and rf.get('decimal_strings') == f['decimal_strings'],
                       'SAVED_RESULT_FUNDING_ROWS_MISMATCH')
            economics = result['economics']
            _check(economics['conditional_position_settlements'] == len(settlements)
                   and economics['actual_liquidation_fills'] == 0, 'HONEST_CONDITIONAL_SETTLEMENT_TAXONOMY_REQUIRED')
            support = sum((_d(r['decimal_strings']['conditional_insurance_value_received']) for r in settlements), Decimal(0))
            adjustment = sum((_d(r['decimal_strings']['settlement_value_cashflow']) for r in settlements), Decimal(0))
            _check(_d(economics['conditional_insurance_overshoot_absorption_USDT']) == support
                   and _d(economics['conditional_NAV_adjustment_USDT']) == adjustment,
                   'SAVED_CONDITIONAL_ECONOMIC_TOTAL_MISMATCH')
    with localcontext() as exact:
        exact.prec = 100
        raw_errors = dict(free_cash=str(INITIAL+sum((_d(r['free_cash_delta']) for r in ledger), Decimal(0))-cash),
            unpaid_liability=str(sum((_d(r['unpaid_liability_delta']) for r in ledger), Decimal(0))-debt),
            isolated={s: str(sum((_d(r['isolated_delta'][s]) for r in ledger), Decimal(0))-positions[s]['margin']) for s in symbols})
        for balance in ('free_cash', 'unpaid_liability', *symbols):
            residual = sum((_d(r['precision100_subtraction_minus_stored_delta']) for r in rounded if r['balance'] == balance), Decimal(0))
            expected = _d(raw_errors[balance] if balance in ('free_cash', 'unpaid_liability') else raw_errors['isolated'][balance])
            _check(residual == -expected, 'RAW100_RESIDUAL_EXPLANATION_MISMATCH')
    return dict(schema=VERSION, status='PASS_EXACT_EVERY_NATIVE40_EVENT_STATE', passed=True,
        checker_SHA256=checker_sha256(), audit_canonical_SHA256=canonical_sha256(audit),
        result_canonical_SHA256=canonical_sha256(result) if result is not None else None,
        native_financial_precision=40, raw_diagnostic_precision=100,
        financial_ledger_rows_checked=len(ledger), trade_rows_checked=ti, funding_rows_checked=fi,
        conditional_settlement_rows_checked=si, transfer_rows_checked=0,
        exact_native40_NAV=str(nav), native40_secondary_PnL_bridge_residual=str(bridge),
        raw_precision100_stored_delta_terminal_residuals=raw_errors, rounded_subtraction_rows=rounded,
        authoritative_check='CHRONOLOGICAL_NATIVE40_EVENT_RECONSTRUCTION_NOT_STORED_DELTA_SUM',
        tolerance_or_epsilon_used=False, financial_values_changed=False,
        account_objects_constructed=0, financial_clocks_advanced=0,
        D_no_transfer_invariant=expected_policy_variant == 'GUARD50_EXIT_ONLY',
        native_exchange_or_funding_publication_certified=False)
