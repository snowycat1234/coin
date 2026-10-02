"""One fixed conditional long-Spot/short-mark account, never native carry proof.

Reuses accepted close sources, received-asset commission and daily metrics.
The small state loop exists solely for two legs, isolated reserves and funding;
it neither changes the frozen Spot engine nor models a venue liquidation rule.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from datetime import UTC, datetime
import json
import math
import os
from pathlib import Path
import resource
import shlex
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import polars as pl

from quant import disk, resources
from quant.metrics import daily_metrics
from quant.paths import ROOT, STATE
from scripts.investment import basis_risk_diagnostic as basis
from scripts.investment import funding_income_diagnostic as income
from scripts.investment import bybit_spot_adapter as native
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v8.registry import FIELDS, append_event

SYMBOLS, MONTHS = basis.SYMBOLS, basis.MONTHS
MINUTE_US, START_US, END_US = basis.MINUTE_US, basis.START_US, basis.END_US
INITIAL_CASH = 10000.
NOMINAL_PER_LEG = INITIAL_MARGIN = 1250.
SPOT_FEE, PERP_FEE, HALF_SPREAD, SLIPPAGE = .001, .00055, .0004, .0004
TEST = 'tests/test_conditional_carry_account.py'
SMOKE_STATUS = 'PASS_CONDITIONAL_CARRY_SYNTHETIC_ACCOUNTING_NOT_MARKET_RESULT'
ACTUAL_STATUS = 'COMPLETE_CONDITIONAL_CARRY_PROXY_ACCOUNT_UNIT_UNCERTIFIED_NOT_NATIVE_OR_LONG_TERM_APR'
RULES = dict(initial_capital_USDT=10000, nominal_per_asset_per_leg_at_signal_USDT=1250,
    isolated_initial_margin_per_asset_USDT=1250, quantity='SIGNAL_SPOT_CLOSE_NET_BASE_MATCHED_FRACTIONAL',
    total_gross_stop_at_or_above=.6, asset_two_leg_gross_stop_at_or_above=.3,
    isolated_equity_stop_at_or_below_initial_margin_fraction=.5,
    isolated_equity_at_or_below_zero='FAIL_UNMODELED_INSOLVENCY_NO_CROSS_LEG_RESCUE',
    stop='NEXT_STRICTLY_LATER_CLOSED_MINUTE_ALL_FLAT_THEN_PERMANENT_CASH',
    entry='FIRST_CLOSE_SIGNAL_SECOND_CLOSE_PLUS_ONE_MICROSECOND_FILL',
    terminal='FINAL_ALLOWED_CLOSE_PLUS_ONE_MICROSECOND_PROTOCOL_KNOWN_FORCE_EXIT',
    funding_ownership='STRICT_ENTRY_LT_EVENT_LT_EXIT', funding_mark='LAST_CLOSE_STRICTLY_LT_EVENT',
    wallet='FUNDING_AND_PERP_FEES_FREE_CASH_FIRST_THEN_OWN_ISOLATED_BALANCE',
    simultaneous_events='SYMBOL_ASCENDING_BEFORE_FILL_AT_SAME_TIMESTAMP',
    spot_fee_bps_per_side=10, perp_fee_bps_per_side=5.5,
    each_leg_roundtrip_spread_bps=8, slippage_bps_per_side=4,
    real_lot_filters=False, fractional_matching_dust_proxy=0, monthly_reset=False, reentry=False)


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def project_proofs(spec):
    """Small frozen receipts only. Calling this does not read price/rate arrays."""
    old = income.project_json(spec['funding_contract_path'], spec['funding_contract_sha256'])
    probe = income.project_json(old['unit_probe']['path'], old['unit_probe']['sha256'])
    units = income.validate_units(old, probe)
    need(units.get('conditional_fraction_assumption') and not units['full_732_event_unit_certified'],
         'Only the explicit unverified fraction branch; no automatic certified-unit promotion')
    native._pins()
    return basis.accepted_options(spec), income.accepted_sources(old), units


def validate_inputs(prices, events):
    need(set(prices) == set(SYMBOLS), 'Exactly the two fixed assets')
    closes = None
    for symbol in SYMBOLS:
        frame = prices[symbol]
        need(set(frame.columns) == {'open_us', 'close_us', 'spot_close', 'mark_close', 'index_close'}
             and frame.height >= 3 and frame['open_us'].dtype == frame['close_us'].dtype == pl.Int64,
             'Explicit joined original close schema and at least three closed minutes')
        basis.complete_calendar(frame, int(frame['open_us'][0]), int(frame['close_us'][-1]))
        need(frame['close_us'].eq(frame['open_us'] + MINUTE_US).all()
             and frame.null_count().to_numpy().sum() == 0
             and all(frame[k].is_finite().all() and frame[k].gt(0).all()
                     for k in ('spot_close', 'mark_close', 'index_close')), 'Finite same-minute close proxies')
        stamps = frame['close_us'].to_list()
        need(closes is None or stamps == closes, 'Identical complete asset calendars; never fill/drop rows')
        closes = stamps
    need(events.schema == {'symbol': pl.String, 'event_us': pl.Int64, 'rate': pl.Float64}
         and events.null_count().to_numpy().sum() == 0 and events['rate'].is_finite().all()
         and set(events['symbol'].unique().to_list()) <= set(SYMBOLS)
         and events.height == events.unique(['symbol', 'event_us']).height,
         'Unique finite original signed events with explicit integer microsecond conversion')
    need(events['event_us'].is_between(closes[0] - MINUTE_US, closes[-1], closed='left').all(),
         'All events in this full calendar; no locked or endpoint event')
    return closes


def simulate_account(prices, events, progress=None):
    """Pure deterministic proxy arithmetic; input frames are already supplied.

    Quantity is fixed from the first signal, before the second close is known.
    Close availability is represented by close+1us. Funding event ownership is
    an explicit hypothesis, including exclusion at an exact entry/exit tie.
    """
    closes = validate_inputs(prices, events)
    native._pins()
    spots = {s: prices[s]['spot_close'].to_list() for s in SYMBOLS}
    marks = {s: prices[s]['mark_close'].to_list() for s in SYMBOLS}
    desired = {s: NOMINAL_PER_LEG / spots[s][0] for s in SYMBOLS}
    cash = INITIAL_CASH
    positions = {s: dict(q=0., short_q=0., isolated_balance=0., short_entry_fill=0.) for s in SYMBOLS}
    entry_us, exit_us, stop_signal_us = closes[1] + 1, closes[-1] + 1, None
    state, exit_reason, pending_exit = 'WAIT_ENTRY', 'PROTOCOL_TERMINAL', None
    fees = spread_costs = slippage_costs = turnover = funding_cash = 0.
    peak = INITIAL_CASH
    all_mdd = minute_mdd = 0.
    minute_peak = INITIAL_CASH
    maximum_gross = 0.
    max_asset_gross = dict.fromkeys(SYMBOLS, 0.)
    min_margin_equity = dict.fromkeys(SYMBOLS, INITIAL_MARGIN)
    nav_rows, funding_rows, fill_rows, breach_rows = [], [], [], []
    event_rows = list(events.sort(['event_us', 'symbol']).iter_rows(named=True))
    cursor = 0
    observation_us, observation_cause = closes[0] - MINUTE_US, 'INITIAL_CASH'

    def valuation(index):
        spot_values, short_values, isolated_equities = {}, {}, {}
        for symbol in SYMBOLS:
            p = positions[symbol]
            spot_values[symbol] = p['q'] * spots[symbol][index] if index >= 0 else 0.
            short_values[symbol] = p['short_q'] * marks[symbol][index] if index >= 0 else 0.
            unrealized = p['short_q'] * (p['short_entry_fill'] - marks[symbol][index]) if index >= 0 else 0.
            isolated_equities[symbol] = p['isolated_balance'] + unrealized
        nav = cash + sum(spot_values.values()) + sum(isolated_equities.values())
        need(math.isfinite(nav), 'Finite account NAV required, never clip an adverse balance')
        gross = sum(spot_values.values()) + sum(short_values.values())
        asset_gross = {s: (spot_values[s] + short_values[s]) / nav if nav > 0 else
                       (float('inf') if spot_values[s] else 0.) for s in SYMBOLS}
        return nav, gross / nav if nav > 0 else (float('inf') if gross else 0.), asset_gross, isolated_equities

    def observe(index):
        nonlocal peak, all_mdd, maximum_gross
        nav, gross, assets, equities = valuation(index)
        peak = max(peak, nav)
        all_mdd = max(all_mdd, (peak - nav) / peak)
        maximum_gross = max(maximum_gross, gross)
        for s in SYMBOLS:
            max_asset_gross[s] = max(max_asset_gross[s], assets[s])
            if positions[s]['short_q']:
                min_margin_equity[s] = min(min_margin_equity[s], equities[s])
                if equities[s] <= 0:
                    witness = dict(timestamp_us=observation_us, phase=observation_cause, symbol=s,
                        isolated_equity=equities[s], isolated_balance=positions[s]['isolated_balance'],
                        held_short_quantity=positions[s]['short_q'], free_cash=cash, nav=nav,
                        price_close_us=closes[index] if index >= 0 else None,
                        mark_proxy=marks[s][index] if index >= 0 else None,
                        scope='UNMODELED_ISOLATED_INSOLVENCY_NO_CROSS_LEG_RESCUE')
                    error = ValueError('Active isolated equity at or below zero; unmodeled insolvency: ' + json.dumps(witness))
                    error.account_failure_witness = witness
                    raise error
        # A nonpositive NAV is a failure of the proxy account, not unlimited leverage.
        need(nav > 0, 'Proxy account insolvent; preserve failure, do not clamp NAV or exposure')
        return nav, gross, assets, equities

    def debit(symbol, amount):
        nonlocal cash
        need(amount >= 0 and math.isfinite(amount), 'Finite nonnegative quote debit')
        from_free = max(0., min(cash, amount))
        cash -= from_free
        positions[symbol]['isolated_balance'] -= amount - from_free
        return from_free, amount - from_free

    def risk(index, timestamp, cause):
        nonlocal pending_exit, stop_signal_us, exit_us, exit_reason
        if state != 'HELD':
            return
        nav, gross, assets, equities = observe(index)
        reasons = (['TOTAL_GROSS'] if gross >= .6 else [])
        reasons += ['ASSET_GROSS_' + s for s in SYMBOLS if assets[s] >= .3]
        reasons += ['ISOLATED_EQUITY_' + s for s in SYMBOLS if equities[s] <= INITIAL_MARGIN * .5]
        if reasons:
            breach_rows.append(dict(signal_us=timestamp, cause=cause, reasons=reasons, nav=nav,
                total_gross=gross, asset_two_leg_gross=assets, isolated_equity=equities))
            if pending_exit is None:
                following = bisect_right(closes, timestamp)
                # A signal at close+1 must wait for the following closed minute.
                if following >= len(closes):
                    return  # Only the already fixed terminal exit exists; never invent a future price.
                pending_exit = following
                stop_signal_us = timestamp
                exit_us = closes[pending_exit] + 1
                exit_reason = 'SELF_DEFINED_RISK_STOP'

    def fill(symbol, product, side, gross_q, mid, timestamp, price_close_us, signal_us, reason):
        nonlocal cash, fees, spread_costs, slippage_costs, turnover, observation_us, observation_cause
        observation_us, observation_cause = timestamp, 'FILL_' + product + '_' + side
        p = positions[symbol]
        index = bisect_left(closes, price_close_us)
        nav_before = observe(index)[0]
        fill_price = mid * (1 + (HALF_SPREAD + SLIPPAGE) * (1 if side == 'buy' else -1))
        before = cash
        realized = fee_free_debit = fee_margin_debit = 0.
        if product == 'SPOT':
            quote_delta, base_delta, asset, amount, fee = native._received_asset_fill(
                symbol, side, gross_q, fill_price, mid, SPOT_FEE)
            cash += quote_delta
            p['q'] += base_delta
            if side == 'sell':
                need(abs(p['q']) <= 1e-10, 'Sell the exact received base; no fictional exchange filter')
                p['q'] = 0.  # Exact fractional all-position sell is a declared dust-zero proxy.
        else:
            base_delta, quote_delta, asset = 0., 0., 'USDT'
            amount = fee = gross_q * fill_price * PERP_FEE
            fee_free_debit, fee_margin_debit = debit(symbol, fee)
            if side == 'sell':
                p['short_entry_fill'] = fill_price
                p['short_q'] = gross_q
            else:
                realized = gross_q * (p['short_entry_fill'] - fill_price)
                cash += p['isolated_balance'] + realized
                p['isolated_balance'] = 0.
                p['short_entry_fill'] = 0.
                p['short_q'] = 0.
        spread = gross_q * mid * HALF_SPREAD
        slippage = gross_q * mid * SLIPPAGE
        fees += fee; spread_costs += spread; slippage_costs += slippage
        turnover += gross_q * mid / INITIAL_CASH
        nav_after = observe(index)[0]
        fill_rows.append(dict(timestamp_us=timestamp, price_close_us=price_close_us,
            signal_us=signal_us, symbol=symbol, product=product, side=side, reason=reason,
            gross_quantity=gross_q, base_position_delta=base_delta, fill_price=fill_price, mid_proxy=mid,
            cash_before=before, cash_after=cash, spot_quote_delta=quote_delta,
            fee_asset=asset, fee_amount=amount, fee_USDT=fee, spread_USDT=spread,
            slippage_USDT=slippage, gross_mid_notional_USDT=gross_q * mid,
            perp_realized_PnL_USDT=realized, fee_free_cash_debit=fee_free_debit,
            fee_isolated_balance_debit=fee_margin_debit, nav_before=nav_before, nav_after=nav_after,
            prefix_peak_nav=peak, prefix_max_drawdown=all_mdd,
            no_short_sale_proceeds=True, fractional_quantity_proxy=True))

    def enter(index):
        nonlocal cash, state
        for symbol in SYMBOLS:
            cash -= INITIAL_MARGIN
            positions[symbol]['isolated_balance'] = INITIAL_MARGIN
            gross_q = desired[symbol] / (1 - SPOT_FEE)
            fill(symbol, 'SPOT', 'buy', gross_q, spots[symbol][index], entry_us,
                 closes[index], closes[0], 'FIXED_INITIAL_HEDGE')
            q = positions[symbol]['q']
            need(q > 0 and abs(q - desired[symbol]) <= 1e-10 and cash >= 0,
                 'Net base is the reused received-asset return, with sufficient reserved cash')
            fill(symbol, 'PERP', 'sell', q, marks[symbol][index], entry_us,
                 closes[index], closes[0], 'MATCH_ACTUAL_NET_BASE')
            need(positions[symbol]['short_q'] == positions[symbol]['q'], 'Exact held net-base hedge match')
        state = 'HELD'

    def leave(index):
        nonlocal state
        for symbol in SYMBOLS:
            q = positions[symbol]['q']
            fill(symbol, 'SPOT', 'sell', q, spots[symbol][index], exit_us,
                 closes[index], stop_signal_us if stop_signal_us is not None else closes[-1], exit_reason)
            # Save q before the Spot sale, because both legs must close the same held quantity.
            fill(symbol, 'PERP', 'buy', q, marks[symbol][index], exit_us,
                 closes[index], stop_signal_us if stop_signal_us is not None else closes[-1], exit_reason)
        state = 'PERMANENT_CASH'

    def funding(event):
        nonlocal cash, funding_cash, observation_us, observation_cause
        symbol, timestamp, rate = event['symbol'], event['event_us'], event['rate']
        observation_us, observation_cause = timestamp, 'FUNDING_EVENT_BEFORE_CASH'
        previous = bisect_left(closes, timestamp) - 1
        before_nav = observe(previous)[0]
        p = positions[symbol]
        owned = state == 'HELD' and entry_us < timestamp < exit_us
        amount, free_debit, margin_debit = 0., 0., 0.
        need(not owned or previous >= 0, 'An owned event must have an actually past closed mark')
        if owned:
            amount = p['short_q'] * marks[symbol][previous] * rate
            if amount >= 0:
                cash += amount
            else:
                free_debit, margin_debit = debit(symbol, -amount)
            funding_cash += amount
        observation_cause = 'FUNDING_EVENT_AFTER_CASH'
        after_nav = observe(previous)[0]
        row = dict(event_us=timestamp, symbol=symbol, raw_rate=rate,
            ownership_qualified=owned, ownership_rule='STRICT_ENTRY_LT_EVENT_LT_EXIT_UNCERTIFIED',
            held_short_quantity=p['short_q'], mark_close_us=closes[previous] if previous >= 0 else None,
            mark_proxy=marks[symbol][previous] if previous >= 0 else None,
            signed_funding_USDT=amount, free_cash_debit=free_debit, isolated_balance_debit=margin_debit,
            nav_before=before_nav, nav_after=after_nav, cumulative_funding_USDT=funding_cash,
            prefix_peak_nav=peak, prefix_max_drawdown=all_mdd,
            reason='CONDITIONAL_SIGNED_FUNDING' if owned else 'OUTSIDE_STRICT_HOLD_INTERVAL',
            funding_unit_certified=False, charge_mark_or_native_settlement_certified=False)
        funding_rows.append(row)
        risk(previous, timestamp, 'FUNDING_EVENT_AFTER_CASH')

    for index, closed in enumerate(closes):
        snapshot = closed + 1
        # At an exact entry/exit tie, funding is excluded by strict ownership.
        while cursor < len(event_rows) and event_rows[cursor]['event_us'] <= snapshot:
            funding(event_rows[cursor]); cursor += 1
        observation_us, observation_cause = snapshot, 'CLOSED_MINUTE_BEFORE_SCHEDULED_FILLS'
        observe(index)  # Price movement before fills is part of the NAV peak/trough path.
        risk(index, snapshot, 'CLOSED_MINUTE_BEFORE_SCHEDULED_FILLS')
        if index == 1 and state == 'WAIT_ENTRY':
            enter(index)
        if state == 'HELD' and (index == pending_exit or index == len(closes) - 1):
            leave(index)
        nav, gross, assets, equities = observe(index)
        minute_peak = max(minute_peak, nav)
        minute_mdd = max(minute_mdd, (minute_peak - nav) / minute_peak)
        risk(index, snapshot, 'CLOSED_MINUTE_AFTER_FILLS')
        nav_rows.append((closed, snapshot, nav, cash, gross, assets['BTCUSDT'], assets['ETHUSDT'],
            positions['BTCUSDT']['q'], positions['ETHUSDT']['q'], equities['BTCUSDT'], equities['ETHUSDT'],
            fees, spread_costs, slippage_costs, turnover, funding_cash, peak, all_mdd))
        if progress and (index % 1440 == 0 or index == len(closes) - 1):
            progress.update('连续条件双腿账本', index + 1, len(closes), '闭合分钟', 已处理事件=cursor,
                            账户状态=state)
    need(cursor == len(event_rows) and state == 'PERMANENT_CASH', 'All events exactly once and terminal flat')
    columns = ('close_us', 'valuation_us', 'nav', 'free_cash', 'total_gross', 'BTCUSDT_gross', 'ETHUSDT_gross',
        'BTCUSDT_spot_and_short_q', 'ETHUSDT_spot_and_short_q', 'BTCUSDT_isolated_equity', 'ETHUSDT_isolated_equity',
        'cumulative_fees', 'cumulative_spread', 'cumulative_slippage', 'cumulative_turnover',
        'cumulative_funding', 'all_observation_peak_nav', 'all_observation_max_drawdown')
    minute = pl.DataFrame(nav_rows, schema=list(columns), orient='row')
    minute = minute.with_columns(pl.from_epoch(pl.col('close_us') - 1, time_unit='us').dt.date().alias('date'))
    daily = minute.group_by('date', maintain_order=True).agg(pl.col('nav').last(),
        pl.col('cumulative_fees').last().alias('fee_cumulative'),
        (pl.col('cumulative_spread') + pl.col('cumulative_slippage')).last().alias('cost_cumulative'),
        pl.col('cumulative_turnover').last().alias('turnover_cumulative'))
    daily = daily.with_columns(pl.col('fee_cumulative').diff().fill_null(pl.col('fee_cumulative')).alias('fees'),
        pl.col('cost_cumulative').diff().fill_null(pl.col('cost_cumulative')).alias('execution_costs'),
        pl.col('turnover_cumulative').diff().fill_null(pl.col('turnover_cumulative')).alias('turnover'))
    metrics = daily_metrics(daily, INITIAL_CASH)
    for row in funding_rows:
        row.update(distance_from_entry_us=abs(row['event_us'] - entry_us),
                   distance_from_exit_us=abs(row['event_us'] - exit_us))
    nearby = [r for r in funding_rows if min(r['distance_from_entry_us'], r['distance_from_exit_us']) <= 5_000_000]
    final_nav = float(minute['nav'][-1])
    months, previous_nav, previous_totals = [], INITIAL_CASH, dict.fromkeys(('fees', 'spread', 'slippage', 'funding'), 0.)
    grouped = minute.with_columns(pl.col('date').dt.strftime('%Y-%m').alias('month')).group_by('month', maintain_order=True).agg(
        pl.col('nav').last(), *[pl.col('cumulative_' + key).last().alias(key) for key in previous_totals])
    for row in grouped.iter_rows(named=True):
        amounts = {key: float(row[key]) - previous_totals[key] for key in previous_totals}
        net = float(row['nav']) - previous_nav
        months.append(dict(month=row['month'], start_NAV=previous_nav, end_NAV=float(row['nav']),
            net_PnL_USDT=net, gross_cost_addback_PnL_USDT=net + amounts['fees'] + amounts['spread'] + amounts['slippage'],
            fees_USDT=amounts['fees'], spread_USDT=amounts['spread'], slippage_USDT=amounts['slippage'],
            signed_funding_USDT=amounts['funding'], monthly_account_reset=False))
        previous_nav = float(row['nav']); previous_totals = {key: float(row[key]) for key in previous_totals}
    summary = dict(initial_capital_USDT=INITIAL_CASH, final_nav_USDT=final_nav,
        net_PnL_USDT=final_nav - INITIAL_CASH, period_net_return=final_nav / INITIAL_CASH - 1,
        gross_cost_addback_PnL_USDT=final_nav - INITIAL_CASH + fees + spread_costs + slippage_costs,
        gross_definition='SAME_COSTED_QUANTITIES_FILL_TIME_COST_ADDBACK_NOT_FEE_FREE_RESIZING',
        fees_USDT=fees, assumed_spread_USDT=spread_costs, assumed_slippage_USDT=slippage_costs,
        signed_conditional_funding_USDT=funding_cash, turnover=turnover, fills=len(fill_rows),
        all_source_events=len(funding_rows), owned_funding_events=sum(r['ownership_qualified'] for r in funding_rows),
        excluded_funding_events=sum(not r['ownership_qualified'] for r in funding_rows),
        first_signal_us=closes[0], entry_us=entry_us, exit_us=exit_us, stop_signal_us=stop_signal_us,
        exit_reason=exit_reason, permanent_cash_after_exit=True, rows=minute.height,
        planned_quantity_from_first_signal=desired, matched_quantity_from_native_received_fill={s:
            next(r['gross_quantity'] for r in fill_rows if r['symbol'] == s and r['product'] == 'PERP' and r['side'] == 'sell')
            for s in SYMBOLS},
        minute_max_drawdown=minute_mdd, all_observation_max_drawdown=all_mdd,
        drawdown_observations='INITIAL_CASH_EVERY_CLOSE_PRE_POST_FILL_AND_FUNDING_PRE_POST_CASH',
        maximum_total_gross=maximum_gross, maximum_asset_two_leg_gross=max_asset_gross,
        minimum_isolated_equity=min_margin_equity, risk_breach_witnesses=breach_rows,
        caps_are_exit_triggers_not_guaranteed_execution_caps=True,
        events_within_5s_of_entry_or_exit=len(nearby), near_boundary_event_witnesses=nearby[:8],
        real_funding_ownership_within_5s_guaranteed=False, terminal_spot_quantity=dict.fromkeys(SYMBOLS, 0.),
        terminal_short_quantity=dict.fromkeys(SYMBOLS, 0.), terminal_dust_proxy=0.,
        months=months, continuous_monthly_net_reconciliation_error_USDT=sum(r['net_PnL_USDT'] for r in months) - (final_nav - INITIAL_CASH),
        per_asset=[dict(symbol=s, signed_funding_USDT=sum(r['signed_funding_USDT'] for r in funding_rows if r['symbol'] == s),
            spot_fee_USDT=sum(r['fee_USDT'] for r in fill_rows if r['symbol'] == s and r['product'] == 'SPOT'),
            perp_fee_USDT=sum(r['fee_USDT'] for r in fill_rows if r['symbol'] == s and r['product'] == 'PERP'),
            actual_entry_spot_mid_notional_USDT=next(r['gross_mid_notional_USDT'] for r in fill_rows if
                r['symbol'] == s and r['product'] == 'SPOT' and r['side'] == 'buy'),
            actual_entry_perp_mid_notional_USDT=next(r['gross_mid_notional_USDT'] for r in fill_rows if
                r['symbol'] == s and r['product'] == 'PERP' and r['side'] == 'sell')) for s in SYMBOLS],
        daily_metrics=metrics, annual_return_interpretation='DESCRIPTIVE_CONDITIONAL_SCREENING_NOT_LONG_TERM_APR',
        candidate_status='NO_QUALIFIED_CANDIDATE', capital_net_APR='NOT_EVALUABLE', unseen_qualification=False,
        native_execution_or_margin_liquidation_proven=False, funding_unit_certified=False)
    return dict(summary=summary, minute_nav=minute, daily_nav=daily,
                funding_ledger=pl.DataFrame(funding_rows) if funding_rows else None,
                fill_ledger=pl.DataFrame(fill_rows))


def verify_spec(spec):
    need(spec['contract_id'] == 'CONDITIONAL_CARRY_ACCOUNT_V1' and spec['rules'] == RULES
         and spec['period_start'] == '2025-08-01' and spec['period_end_exclusive'] == '2025-12-01'
         and spec['symbols'] == list(SYMBOLS) and spec['source_calendar'] == list(MONTHS)
         and spec['expected_price_files'] == 24 and spec['expected_funding_files'] == 8
         and spec['expected_minutes_per_asset'] == 175680 and spec['expected_funding_events'] == 732,
         'Only the preregistered fixed continuous122day conditional account')
    need(spec['funding_contract_path'] == 'protocols/FUNDING_INCOME_DIAGNOSTIC_122D_20261003_V1.json'
         and spec['funding_contract_sha256'] == '306749e93b82e70c4597be75dd1f0e548ba63b4937a2094d9d677ede34755db4'
         and spec['fee_reference_profile_path'] == native.PROFILE_PATH
         and spec['fee_reference_profile_sha256'] == native.PINS[native.PROFILE_PATH], 'Original unit/failure and fee proof binding')
    need(0 < spec['maximum_new_owned_bytes'] <= 50_000_000 and 0 < spec['maximum_wall_seconds'] <= 600,
         'Small fixed bounded account output and wall budget')


def load_inputs(price_sources, funding_sources, report, progress):
    prices = {}
    for symbol in SYMBOLS:
        streams = {}
        for kind in basis.KINDS:
            frames = []
            for month in MONTHS:
                row = next(r for r in price_sources if (r['kind'], r['symbol'], r['month']) == (kind, symbol, month))
                path, opened, closed = basis.allowed_path(row)
                need(income.file_sha(path) == row['parquet_sha256'], 'Explicit accepted price bytes changed')
                cols = ['open_us', 'close_us', 'close', 'symbol', 'valid_day'] if kind == 'spot1m' else ['timestamp_ms', 'close_time_ms', 'close']
                report['price_arrays_read'] = True
                frame = basis.canonical_prices(kind, pl.read_parquet(path, columns=cols), symbol)
                basis.complete_calendar(frame, opened, closed)
                need(income.file_sha(path) == row['parquet_sha256'], 'Price source changed while reading')
                frames.append(frame)
                report['input_bindings'].append(dict(kind=kind, symbol=symbol, month=month,
                    parquet_path=str(path), parquet_sha256=row['parquet_sha256'], rows=frame.height))
                progress.update('复用已接受原close与funding源', len(report['input_bindings']), 32, '文件')
            streams[kind] = pl.concat(frames)
        prices[symbol] = basis.join_prices(*(streams[k] for k in basis.KINDS), START_US, END_US)
    event_frames = []
    for row in funding_sources:
        path = Path(row['parquet_path'])
        need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(STATE.resolve())
             and income.file_sha(path) == row['parquet_sha256'], 'Explicit accepted funding bytes changed')
        report['funding_arrays_read'] = True
        frame = pl.read_parquet(path)
        need(frame.schema == income.SCHEMA and frame.height == row['rows'] and
             frame.null_count().to_numpy().sum() == 0 and frame['last_funding_rate'].is_finite().all()
             and frame['funding_interval_hours'].is_finite().all() and frame['funding_interval_hours'].gt(0).all(),
             'Same accepted original funding fields; no eight-hour interpolation')
        opened, closed = basis.month_bounds(row['month'])
        need((frame['calc_time_ms'] * 1000).is_between(opened, closed, closed='left').all(), 'Explicit source month bounds')
        event_frames.append(frame.select(pl.lit(row['symbol']).alias('symbol'),
            (pl.col('calc_time_ms') * 1000).alias('event_us'), pl.col('last_funding_rate').alias('rate')))
        need(income.file_sha(path) == row['parquet_sha256'], 'Funding source changed while reading')
        report['input_bindings'].append(dict(kind='fundingRate', symbol=row['symbol'], month=row['month'],
            parquet_path=str(path), parquet_sha256=row['parquet_sha256'], rows=frame.height))
        progress.update('复用已接受原close与funding源', len(report['input_bindings']), 32, '文件')
    events = pl.concat(event_frames)
    need(events.height == 732 and all(events.filter(pl.col('symbol') == s).height == 366 for s in SYMBOLS),
         'All732 signed events; no selection by rate, month or account state')
    return prices, events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--smoke', action='store_true'); mode.add_argument('--research', action='store_true')
    for name in ('protocol', 'run-dir', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--experiment-id', required=True)
    args = parser.parse_args()
    work, output, protocol = args.run_dir.resolve(), args.output.resolve(), args.protocol.resolve()
    need(work.is_relative_to(STATE.resolve()) and not work.exists() and
         output.is_relative_to((ROOT / 'reports/fast_research').resolve()) and not output.exists()
         and os.environ.get('COIN_TASK_ID'), 'Exclusive STATE/output and actual bounded/progress wrapper')
    resources.status()
    need(sys.prefix == str(STATE / 'v8-clean-env-20261002-v2') and pl.thread_pool_size() <= 2, 'Frozen small clean CPU environment')
    spec = income.project_json(protocol); verify_spec(spec)
    hashes = {name: income.file_sha(ROOT / name) for name in spec['frozen_sources']}
    need(hashes == spec['frozen_sources'] and TEST in hashes and 'environments/v8/uv.lock' in hashes,
         'Explicit frozen source/test/environment binding before IO')
    hashes.update({str(protocol.relative_to(ROOT)): income.file_sha(protocol),
                   str(Path(__file__).resolve().relative_to(ROOT)): income.file_sha(__file__)})
    command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
    test_command = [sys.executable, '-m', 'pytest', TEST, '-q', '--basetemp=' + str(work / 'pytest'),
        '-o', 'cache_dir=' + str(work / 'pytest-cache'), '--junitxml=' + str(work / 'junit.xml')]
    binding = dict(git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        source_hashes=hashes, protocol_sha256=income.file_sha(protocol), task_id=os.environ['COIN_TASK_ID'],
        sys_prefix=sys.prefix, exact_command=shlex.join(command),
        exact_test_command=shlex.join(test_command) if args.smoke else None,
        environment_lock_sha256=hashes['environments/v8/uv.lock'], rules=RULES,
        data_scope='SYNTHETIC_ONLY' if args.smoke else 'FULL122D_24_CLOSE_AND8_FUNDING_FILES_CONDITIONAL')
    work.mkdir(); income.exclusive_json(work / 'RUN_BINDING.json', binding)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=args.experiment_id, event_id=args.experiment_id + ':START', event_type='OPERATIONAL_START',
        git_commit=binding['git_commit'], data_manifest_hash=spec['source_options_sha256'],
        protocol_hash=binding['protocol_sha256'], feature_set='EXISTING_CLOSES_AND_SIGNED_FUNDING', labels='NONE',
        model_family='NONE', hyperparameters=RULES, seed='NONE_DETERMINISTIC', thresholds='FIXED_SELF_DEFINED_RISK_EXIT',
        cost_assumptions={k: RULES[k] for k in ('spot_fee_bps_per_side', 'perp_fee_bps_per_side',
            'each_leg_roundtrip_spread_bps', 'slippage_bps_per_side')}, all_folds='ONE_CONTINUOUS_FULL122D_ACCOUNT',
        success_failure='START_BEFORE_ANY_MARKET_ARRAY_READ',
        reason_for_next_experiment='Close conditional carry capital/cash/cost/risk together without HPO or native claims',
        result_influenced_later_choice=False, source_hashes=hashes, exact_command=binding['exact_command'],
        run_binding_sha256=income.file_sha(work / 'RUN_BINDING.json'))
    registered = append_event(ROOT / 'reports/experiment_registry.jsonl', event)
    report = dict(status='FAIL_CONDITIONAL_CARRY_ACCOUNT', binding=binding, registration_start=registered,
        run_dir=str(work), candidate_status='NO_QUALIFIED_CANDIDATE', capital_net_APR='NOT_EVALUABLE',
        unseen_qualification=False, models_fit=0, orders_sent=0, GPU=0, locked_consumed=False,
        price_arrays_read=False, funding_arrays_read=False, old_QA_or_green_tests_repeated=False,
        funding_unit_certified=False, native_Bybit_prices_or_filters=False, real_liquidation_MMR_or_ADL_modeled=False,
        funding_event_ownership_and_charge_mark_certified=False, source_bytes_unchanged=False, input_bindings=[],
        output_bindings=[], limitations=['Binance close/rate proxies plus Bybit current ordinary fee hypotheses',
            'Uncertified funding fraction and mark/event ownership; five-second boundary ambiguity',
            'No observed BBO, native depth/capacity/filters, financing, real margin or liquidation/ADL',
            'Fixed fractional quantity, assumed spread/slippage and self-defined risk stop; seen history only'])
    progress = Progress(); progress.value['detail'] = '固定连续条件双腿现金/费用/保证金账本，不是原生收益或长期APR'
    started = time.monotonic()
    try:
        progress.update('核对冻结小凭证', 0, 32, '文件')
        selected, funding_sources, units = project_proofs(spec)
        report['unit_interpretation'] = units
        report['disk'] = dict(scan_started_utc=datetime.now(UTC).isoformat(),
            **disk.check(spec['maximum_new_owned_bytes']), scan_finished_utc=datetime.now(UTC).isoformat())
        if args.smoke:
            progress.update('唯一新双腿合成验收', 0, 1, '用例')
            run = subprocess.run(test_command, cwd=ROOT, check=False)
            report['test_exit_code'] = run.returncode
            if (work / 'junit.xml').is_file():
                tree = ET.parse(work / 'junit.xml').getroot()
                report['junit_counts'] = {key: sum(int(s.attrib.get(key, 0)) for s in tree.iter('testsuite'))
                                        for key in ('tests', 'errors', 'failures', 'skipped')}
                report['junit_sha256'] = income.file_sha(work / 'junit.xml')
            need(run.returncode == 0 and report.get('junit_counts') == dict(tests=1, errors=0, failures=0, skipped=0),
                 'Only the new hand-calculated fixture must pass')
            report['status'] = SMOKE_STATUS
        else:
            smoke = income.project_json(spec['required_smoke_receipt'])
            need(smoke['status'] == SMOKE_STATUS and smoke['test_exit_code'] == 0 and
                 not smoke['price_arrays_read'] and not smoke['funding_arrays_read'] and
                 smoke['source_bytes_unchanged'] and smoke['binding']['source_hashes'] == hashes,
                 'Same frozen code/protocol synthetic acceptance before actual arrays')
            task = json.loads((STATE / 'task-progress' / ('task-' + smoke['binding']['task_id'] + '.json')).read_bytes())
            need(task['status'] == 'completed' and task['exit_code'] == 0 and
                 task['id'] == smoke['binding']['task_id'], 'Synthetic actual task must be completed zero with the exact ID')
            report['accepted_smoke_sha256'] = income.file_sha(ROOT / spec['required_smoke_receipt'])
            prices, events = load_inputs(selected, funding_sources, report, progress)
            result = simulate_account(prices, events, progress)
            need(result['minute_nav'].height == 175680 and result['daily_nav'].height == 122
                 and result['summary']['all_source_events'] == 732, 'Full period and complete original events')
            report['summary'] = result['summary']
            for name in ('minute_nav', 'daily_nav', 'funding_ledger', 'fill_ledger'):
                frame = result[name]
                path = work / (name + '.parquet')
                frame.write_parquet(path, compression='zstd')
                report['output_bindings'].append(dict(kind=name, path=str(path), sha256=income.file_sha(path),
                    bytes=path.stat().st_size, rows=frame.height, schema={k: str(v) for k, v in frame.schema.items()}))
            report['status'] = ACTUAL_STATUS
        need(time.monotonic() - started <= spec['maximum_wall_seconds'], 'Fixed wall budget exceeded')
        need(hashes == {name: income.file_sha(ROOT / name) for name in hashes}, 'Frozen source bytes changed during task')
        report['source_bytes_unchanged'] = True
    except Exception as error:
        report.update(status='FAIL_CONDITIONAL_CARRY_ACCOUNT', error_type=type(error).__name__, reason=str(error))
        if hasattr(error, 'account_failure_witness'):
            report['account_failure_witness'] = error.account_failure_witness
        raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(), elapsed_seconds=time.monotonic() - started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, resources=resources.status(),
            owned_bytes=sum(p.stat().st_size for p in work.rglob('*') if p.is_file()))
        if report['owned_bytes'] + len(json.dumps(report, ensure_ascii=False).encode()) > spec['maximum_new_owned_bytes']:
            report.update(status='FAIL_CONDITIONAL_CARRY_ACCOUNT', reason='Actual new output budget exceeded')
        income.exclusive_json(output, report)
        append_event(ROOT / 'reports/experiment_registry.jsonl', dict(event, event_id=args.experiment_id + ':RESULT',
            event_type='OPERATIONAL_RESULT', success_failure=report['status'], artifact_path=str(output.relative_to(ROOT)),
            artifact_sha256=income.file_sha(output)))
        progress.stop.set(); progress.thread.join(timeout=3)
    need(report['status'] in (SMOKE_STATUS, ACTUAL_STATUS), 'Failed result preserved')
    print(json.dumps(dict(status=report['status'], output=str(output), sha256=income.file_sha(output))))


if __name__ == '__main__':
    main()
