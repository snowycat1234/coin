"""One synthetic reason/owner reconciliation; no account or market replay."""
from copy import deepcopy
from decimal import Decimal as D
import json
from pathlib import Path

import pytest

from scripts.investment import turtle_turnover_diagnostic as diagnostic


def test_reason_owner_duplicates_unknown_and_small_close(tmp_path):
    assert tmp_path.resolve().is_relative_to(Path('/home/xflops/coin-state'))
    signal = 1_750_000_000_000_000

    def trade(identity, symbol, side, leg, q, before, after, mid, fill, fee, execution):
        values = dict(quantity=q, quantity_before=before, quantity_after=after,
            position_delta=str(D(q) * (1 if side == 'BUY' else -1)),
            mid_price=mid, execution_mid_price=mid, fill_price=fill,
            fee_USDT_mid=fee, execution_cost=execution)
        return dict(fill_id=identity, symbol=symbol, side=side, leg=leg,
            signal_us=signal, event_us=signal + 60_000_001,
            **{k: float(v) for k, v in values.items()}, decimal_strings=values)

    # Long liquidation is a SELL; the small BUY stop covers a SHORT.
    # Costs match the declared synthetic 5.5bp fee and 8bp execution shift.
    trades = [
        trade('long-close', 'BTCUSDT', 'SELL', 'CLOSE', '.5', '1', '.5',
              '110', '109.912', '.0302258', '.044'),
        trade('short-stop', 'ETHUSDT', 'BUY', 'CLOSE', '.05', '-.1', '-.05',
              '90', '90.072', '.00247698', '.0036'),
        trade('unmapped', 'BTCUSDT', 'BUY', 'OPEN', '.1', '.5', '.6',
              '100', '100.08', '.0055044', '.008'),
    ]
    submitted = [
        dict(event='INTENT_SUBMITTED', id='long-exit', symbol='BTCUSDT',
             side='SELL', signal_us=signal, kind='EXIT'),
        dict(event='INTENT_SUBMITTED', id='short-protection', symbol='ETHUSDT',
             side='BUY', signal_us=signal, kind='STOP'),
    ]
    notifications = [
        dict(event='ACTUAL_FILL_NOTIFIED', fill_id='long-close', intent_id='long-exit'),
        dict(event='ACTUAL_FILL_NOTIFIED', fill_id='short-stop', intent_id='short-protection'),
    ]
    meta = dict(journal=submitted + notifications)
    meta['journal'] += [deepcopy(submitted[0]), deepcopy(notifications[1])]
    summary = dict(trade_legs=3, gross_fill_turnover_USDT=69.4676,
        fees_USDT=.03820718, execution_cost_USDT=.0556,
        normalized_total_turnover=.00694676)
    before = deepcopy((trades, meta, summary))
    result = diagnostic.diagnose_case(trades, meta, summary)
    assert (trades, meta, summary) == before

    def money(actual, expected):
        assert abs(D(str(actual)) - D(str(expected))) <= D('1e-12')

    groups = {(r['direction'], r['symbol'], r['reason']): r for r in result['groups']}
    assert set(groups) == {('LONG', 'BTCUSDT', 'EXIT'),
                          ('SHORT', 'ETHUSDT', 'STOP'), ('LONG', 'BTCUSDT', 'UNKNOWN')}
    totals = result['totals']
    assert totals['legs'] == totals['distinct_fills'] == 3 and totals['logical_intents'] == 2
    expected = dict(mid_notional_USDT='69.5', fill_notional_USDT='69.4676',
        fees_USDT='.03820718', execution_cost_USDT='.0556', total_cost_USDT='.09380718',
        cost_percent_full_capital='.0009380718')
    for key, value in expected.items():
        money(totals[key], value)
        money(sum((D(str(g[key])) for g in groups.values()), D(0)), value)
    stop = groups['SHORT', 'ETHUSDT', 'STOP']
    money(stop['fill_notional_USDT'], '4.5036')
    money(stop['fees_USDT'], '.00247698')
    money(stop['execution_cost_USDT'], '.0036')
    for entry in (totals, stop):
        small = entry['small_fill_notional_lt10']
        assert small['legs'] == 1
        money(small['fill_notional_USDT'], '4.5036')
        money(small['fees_USDT'], '.00247698')
        money(small['execution_cost_USDT'], '.0036')
    assert groups['LONG', 'BTCUSDT', 'UNKNOWN']['legs'] == 1
    assert result['mapping']['mapped_legs'] == 2 and result['mapping']['UNKNOWN_legs'] == 1
    assert result['mapping']['duplicate_notifications'] == 1
    assert result['mapping']['duplicate_intent_submissions'] == 1
    assert result['reconciliation']['saved_summary_trade_legs'] == 3
    assert result['reconciliation']['PASS'] is True

    # A repeated journal message has no new fee; a repeated financial leg
    # cannot be silently accepted or charged twice.
    with pytest.raises(ValueError):
        diagnostic.diagnose_case(trades + [deepcopy(trades[1])], meta, summary)
    conflicting = deepcopy(meta)
    conflicting['journal'].append(dict(event='ACTUAL_FILL_NOTIFIED',
        fill_id='short-stop', intent_id='long-exit'))
    with pytest.raises(ValueError):
        diagnostic.diagnose_case(trades, conflicting, summary)

    # An intent with the wrong symbol/side is UNKNOWN, never an invented STOP.
    mismatch = deepcopy(meta)
    for row in mismatch['journal']:
        if row.get('id') == 'short-protection':
            row['side'] = 'SELL'
    unknown = diagnostic.diagnose_case(trades, mismatch, summary)
    assert unknown['mapping']['mapped_legs'] == 1 and unknown['mapping']['UNKNOWN_legs'] == 2
    assert any(r['direction'] == 'SHORT' and r['reason'] == 'UNKNOWN' for r in unknown['groups'])
    for key, value in expected.items():
        money(unknown['totals'][key], value)

    # A saved exact price can lie below 10 even when its Float64 alias is 10.
    # Decimal multiplication must not round this strict size tag up to 10.
    boundary_trade = trade('near-ten', 'BTCUSDT', 'SELL', 'CLOSE', '1', '1', '0',
        '10', '9.99999999999999999999999999999', '.0055', '0')
    boundary = diagnostic.diagnose_case([boundary_trade], dict(journal=[]),
        dict(trade_legs=1, gross_fill_turnover_USDT=10., fees_USDT=.0055,
             execution_cost_USDT=0., normalized_total_turnover=.001))
    assert boundary['totals']['legs'] == boundary['totals']['small_fill_notional_lt10']['legs'] == 1
    assert boundary['groups'][0]['reason'] == 'UNKNOWN' and boundary['groups'][0]['direction'] == 'LONG'

    # Separate fresh-flat hand cashflows: price gross 10+5, funding 2-3.
    # Four explicit .1 fees and .2 execution costs give net 12.8, not 14.
    attribution_trades = [
        trade('BTC-open', 'BTCUSDT', 'BUY', 'OPEN', '1', '0', '1',
              '100', '100.2', '.1', '.2'),
        trade('BTC-close', 'BTCUSDT', 'SELL', 'CLOSE', '1', '1', '0',
              '110', '109.8', '.1', '.2'),
        trade('ETH-open', 'ETHUSDT', 'SELL', 'OPEN', '1', '0', '-1',
              '50', '49.8', '.1', '.2'),
        trade('ETH-close', 'ETHUSDT', 'BUY', 'CLOSE', '1', '-1', '0',
              '45', '45.2', '.1', '.2'),
    ]
    attribution = diagnostic.asset_attribution(attribution_trades,
        [dict(symbol='BTCUSDT', signed_funding_USDT=2.),
         dict(symbol='ETHUSDT', signed_funding_USDT=-3.)],
        dict(terminal_signed_marked_notional=dict(BTCUSDT=0., ETHUSDT=0.),
             gross_PnL_same_quantities=15., funding_USDT=-1., net_PnL=12.8))
    by_asset = {r['symbol']: r for r in attribution['assets']}
    for symbol, gross, funded, net in (('BTCUSDT', '10', '2', '11.4'),
                                     ('ETHUSDT', '5', '-3', '1.4')):
        money(by_asset[symbol]['price_PnL_gross_USDT'], gross)
        money(by_asset[symbol]['signed_funding_USDT'], funded)
        money(by_asset[symbol]['fees_USDT'], '.2')
        money(by_asset[symbol]['execution_cost_USDT'], '.4')
        money(by_asset[symbol]['net_contribution_USDT'], net)
    money(sum((D(str(r['net_contribution_USDT'])) for r in by_asset.values()), D(0)), '12.8')
    assert set(attribution['summary_bridge_errors_USDT']) == {'gross_PnL_same_quantities', 'funding_USDT', 'net_PnL'}
    assert all(v <= 1e-12 for v in attribution['summary_bridge_errors_USDT'].values())
    assert all(r['net_contribution_USDT'] is None
               for r in result['asset_price_and_funding_attribution']['assets'])

    (tmp_path / 'turnover_reason_evidence.json').write_text(json.dumps(dict(
        scope='SYNTHETIC_REASON_OWNER_AND_TOTALS_ONLY_NOT_ACCOUNT_OR_MARKET_REPLAY',
        expected_totals=expected, result=result, identity_mismatch_result=unknown,
        exact_below_ten_with_rounded_float_alias=boundary,
        independent_asset_cashflow_hand_values=attribution,
        small_closes_retained=True, native_filter_certification=False,
        execution_cost_not_double_counted=True), indent=2, sort_keys=True), encoding='utf-8')
