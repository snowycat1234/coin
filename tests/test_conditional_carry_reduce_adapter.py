"""One new partial-pair hand case; no history, old suite, fit or real order."""
from decimal import Decimal as D
import importlib.util
from pathlib import Path

import polars as pl
import pytest

from scripts.investment import conditional_carry_account as control

if Path(__file__).with_name('adapter.py').is_file():
    module_spec = importlib.util.spec_from_file_location('pair_trim_state_draft', Path(__file__).with_name('adapter.py'))
    trim = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(trim)
else:
    from scripts.investment import conditional_carry_reduce_adapter as trim


def test_pair_trim_signal_qty_received_fee_partial_realized_reserve_chunk_time_margin_and_future_prefix():
    start = control.START_US
    closes = [start + (i + 1) * control.MINUTE_US for i in range(8)]
    def prices(btc_spot=None, btc_mark=None):
        spot = btc_spot or [100., 100., 120., 120., 120., 120., 120., 120.]
        mark = btc_mark or spot
        return {symbol: pl.DataFrame(dict(open_us=[t-control.MINUTE_US for t in closes], close_us=closes,
            spot_close=spot if symbol == 'BTCUSDT' else [100.]*8,
            mark_close=mark if symbol == 'BTCUSDT' else [100.]*8, index_close=[100.]*8))
            for symbol in control.SYMBOLS}
    entry = closes[1] + 1
    trim_fill = closes[3] + 1
    events = pl.DataFrame(dict(symbol=['BTCUSDT']*5,
        event_us=[start, entry, trim_fill, closes[4]+2, closes[-1]-1],
        rate=[.5, .5, .001, -.001, 0.]))
    result = trim.simulate_account(prices(), events)
    summary = result['summary']
    assert summary['strategy_id'] == trim.STRATEGY_ID and summary['completed_pair_reductions'] == 1
    assert summary['exit_reason'] == 'PROTOCOL_TERMINAL' and summary['exit_us'] == closes[-1]+1
    assert summary['fills'] == 10 and summary['terminal_dust_proxy'] == 0
    receipt = trim.derivation_receipt()
    assert receipt['base_sha256'] == trim.BASE_SHA and receipt['expected_exact_anchor_matches'] == 11
    assert len(receipt['changes']) == 11 and all(row['matches'] == 1 for row in receipt['changes'])
    reduction = summary['pair_reductions'][0]
    q, g = D('12.5'), D('12.5')/D('.999')
    initial_nav = D('10000')+2*(q*D('100')-g*D('100.08')+q*(D('99.92')-D('100'))-q*D('99.92')*D('.00055'))
    keep = D('.25')*initial_nav/D('240')
    removed = q-keep
    assert reduction['symbol'] == 'BTCUSDT' and reduction['signal_us'] == closes[2]+1
    assert reduction['signal_price_close_us'] == closes[2] and reduction['fill_us'] == trim_fill
    assert reduction['signal_NAV'] == pytest.approx(float(initial_nav), abs=1e-9)
    assert reduction['keep_quantity'] == pytest.approx(float(keep), abs=1e-11)
    assert reduction['reduce_quantity'] == pytest.approx(float(removed), abs=1e-11)
    assert reduction['remaining_quantity'] == pytest.approx(float(keep), abs=1e-11)
    assert reduction['isolated_balance_before'] == reduction['isolated_balance_after'] == 1250.
    fills = result['fill_ledger'].filter(pl.col('reason') == 'MATCHED_PAIR_CAP_TRIM')
    assert fills.height == 2 and fills['product'].to_list() == ['SPOT','PERP']
    spot, perp = fills.row(0,named=True), fills.row(1,named=True)
    assert spot['gross_quantity'] == perp['gross_quantity'] == pytest.approx(float(removed), abs=1e-11)
    assert spot['fee_asset'] == perp['fee_asset'] == 'USDT'
    spot_fill, perp_fill = D('119.904'), D('120.096')
    expected_realized = removed*(D('99.92')-perp_fill)
    assert spot['spot_quote_delta'] == pytest.approx(float(removed*spot_fill*D('.999')), abs=1e-9)
    assert spot['fee_USDT'] == pytest.approx(float(removed*spot_fill*D('.001')), abs=1e-11)
    assert perp['fee_USDT'] == pytest.approx(float(removed*perp_fill*D('.00055')), abs=1e-11)
    assert perp['perp_realized_PnL_USDT'] == pytest.approx(float(expected_realized), abs=1e-9)
    assert perp['partial_realized_free_cash_debit'] == pytest.approx(-float(expected_realized), abs=1e-9)
    assert perp['partial_realized_isolated_balance_debit'] == 0. and perp['isolated_balance_released_USDT'] == 0.
    expected_nav_drop = float(removed*spot_fill*D('.001')+removed*perp_fill*D('.00055')+2*removed*D('120')*D('.0008'))
    assert reduction['NAV_before']-reduction['NAV_after'] == pytest.approx(expected_nav_drop, abs=1e-8)
    funding = result['funding_ledger']
    tied = funding.filter(pl.col('event_us') == trim_fill).row(0,named=True)
    assert tied['ownership_qualified'] and tied['mark_close_us'] == closes[3]
    assert tied['held_short_quantity'] == pytest.approx(12.5)
    assert tied['qualified_short_quantity'] == pytest.approx(float(keep), abs=1e-11)
    assert tied['closing_at_same_stamp_excluded_quantity'] == pytest.approx(float(removed), abs=1e-11)
    assert tied['signed_funding_USDT'] == pytest.approx(float(keep*D('120')*D('.001')), abs=1e-10)
    assert summary['signed_conditional_funding_USDT'] == pytest.approx(0., abs=1e-10)
    assert summary['all_observation_max_drawdown'] >= summary['minute_max_drawdown']
    assert summary['no_extra_capital_or_collateral_topups'] and summary['capital_net_APR'] == 'NOT_EVALUABLE'

    # Future fill prices may alter execution, but cannot resize the already frozen signal quantity.
    future = trim.simulate_account(prices(btc_spot=[100.,100.,120.,125.,125.,125.,125.,125.]), events)
    assert result['minute_nav'].head(3).equals(future['minute_nav'].head(3))
    assert future['summary']['pair_reductions'][0]['reduce_quantity'] == reduction['reduce_quantity']
    # Margin <=625 takes all-flat priority over the cap, without relaxing any limit.
    margin = trim.simulate_account(prices(btc_spot=[100.]*8, btc_mark=[100.,100.,160.,160.,160.,160.,160.,160.]), events)
    assert margin['summary']['exit_reason'] == 'SELF_DEFINED_ISOLATED_MARGIN_ALL_FLAT'
    assert margin['summary']['completed_pair_reductions'] == 0 and margin['summary']['fills'] == 8
    assert margin['summary']['exit_us'] == trim_fill
    assert trim.RULES['asset_two_leg_gross_stop_at_or_above'] == .3 and trim.RULES['total_gross_stop_at_or_above'] == .6
    assert trim.RULES['isolated_equity_stop_at_or_below_initial_margin_fraction'] == .5