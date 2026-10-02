"""One new small hand fixture; no historical arrays or old green reruns."""
from decimal import Decimal as D

import polars as pl
import pytest

from scripts.investment import conditional_carry_account as carry


def test_fixed_carry_fee_cash_quantity_signed_funding_strict_time_risk_and_causal_prefix():
    start = carry.START_US
    closes = [start + (i + 1) * carry.MINUTE_US for i in range(6)]
    def prices(spot=None, mark=None):
        return {s: pl.DataFrame(dict(open_us=[t - carry.MINUTE_US for t in closes], close_us=closes,
            spot_close=spot or [100.] * 6, mark_close=mark or [100.] * 6, index_close=[100.] * 6))
            for s in carry.SYMBOLS}
    entry, terminal = closes[1] + 1, closes[-1] + 1
    events = pl.DataFrame(dict(symbol=['BTCUSDT'] * 5, event_us=[start, entry, closes[2], closes[3] + 2, closes[-1] - 1],
                              rate=[.5, .5, .001, -.002, .001]))
    result = carry.simulate_account(prices(), events)
    summary, fills, funding = result['summary'], result['fill_ledger'], result['funding_ledger']
    assert summary['first_signal_us'] == closes[0] and summary['entry_us'] == entry and summary['exit_us'] == terminal
    assert summary['fills'] == 8 and summary['owned_funding_events'] == 3 and summary['excluded_funding_events'] == 2
    assert fills.filter(pl.col('reason') != 'PROTOCOL_TERMINAL')['signal_us'].min() == closes[0]
    assert (fills['price_close_us'] < fills['timestamp_us']).all()
    assert fills.filter(pl.col('reason') != 'PROTOCOL_TERMINAL')['timestamp_us'].min() > closes[0] + carry.MINUTE_US
    btc_entry = fills.filter((pl.col('symbol') == 'BTCUSDT') & (pl.col('side') == 'buy') & (pl.col('product') == 'SPOT')).row(0, named=True)
    q, g = D('12.5'), D('12.5') / D('.999')
    assert btc_entry['gross_quantity'] == pytest.approx(float(g), abs=1e-12)
    assert btc_entry['base_position_delta'] == pytest.approx(float(q), abs=1e-12)
    assert btc_entry['fee_asset'] == 'BTC' and btc_entry['fee_amount'] == pytest.approx(float(g * D('.001')))
    assert btc_entry['spot_quote_delta'] == pytest.approx(-float(g * D('100.08')))
    assert summary['matched_quantity_from_native_received_fill'] == pytest.approx(dict.fromkeys(carry.SYMBOLS, 12.5))
    assert funding['signed_funding_USDT'].to_list() == pytest.approx([0., 0., 1.25, -2.5, 1.25])
    assert funding.row(2, named=True)['mark_close_us'] == closes[1]  # Exact bar endpoint cannot supply its own charge mark.
    assert (funding.filter(pl.col('ownership_qualified'))['mark_close_us'] <
            funding.filter(pl.col('ownership_qualified'))['event_us']).all()
    # The constant-mid hedge loses only actual received-asset and quote fees plus proxy execution.
    per_asset_spot_cash = -g * D('100.08') + q * D('99.92') * D('.999')
    per_asset_perp_cash = q * (D('99.92') - D('100.08')) - q * (D('99.92') + D('100.08')) * D('.00055')
    final = D('10000') + 2 * (per_asset_spot_cash + per_asset_perp_cash)
    assert summary['final_nav_USDT'] == pytest.approx(float(final), abs=1e-9)
    assert summary['signed_conditional_funding_USDT'] == pytest.approx(0., abs=1e-12)
    assert result['minute_nav']['free_cash'][1] < 7500  # Short sale is never cash credited.
    assert summary['all_observation_max_drawdown'] >= summary['minute_max_drawdown']
    assert summary['terminal_dust_proxy'] == 0 and summary['capital_net_APR'] == 'NOT_EVALUABLE'
    assert summary['funding_unit_certified'] is False
    # Sizing consumes the signal price, not the unknown next-close fill price.
    higher_entry = carry.simulate_account(prices(spot=[100., 101., 100., 100., 100., 100.]), events)
    assert higher_entry['summary']['planned_quantity_from_first_signal'] == summary['planned_quantity_from_first_signal']
    # One adverse signed event drains free cash, then its own isolated wallet and triggers next-close exit.
    stop_event = closes[2] + 2
    stopped_events = pl.DataFrame(dict(symbol=['BTCUSDT'] * 3,
        event_us=[stop_event, closes[3] + 1, closes[4] + 2], rate=[-4.6, .5, .5]))
    stopped = carry.simulate_account(prices(), stopped_events)
    assert stopped['summary']['stop_signal_us'] == stop_event
    assert stopped['summary']['exit_us'] == closes[3] + 1
    assert stopped['summary']['exit_reason'] == 'SELF_DEFINED_RISK_STOP'
    assert stopped['funding_ledger']['ownership_qualified'].to_list() == [True, False, False]
    assert stopped['funding_ledger']['isolated_balance_debit'][0] > 625
    assert stopped['minute_nav']['BTCUSDT_spot_and_short_q'].tail(3).to_list() == [0., 0., 0.]
    assert stopped['summary']['all_observation_max_drawdown'] >= stopped['summary']['minute_max_drawdown']
    insolvent_events = stopped_events.with_columns(pl.when(pl.col('event_us') == stop_event)
        .then(-5.).otherwise(pl.col('rate')).alias('rate'))
    with pytest.raises(ValueError, match='unmodeled insolvency') as rejected:
        carry.simulate_account(prices(), insolvent_events)
    assert rejected.value.account_failure_witness['timestamp_us'] == stop_event
    assert rejected.value.account_failure_witness['isolated_equity'] <= 0
    future_prices = prices(mark=[100., 100., 100., 100., 100., 110.])
    future_events = events.with_columns(pl.when(pl.col('event_us') == closes[-1] - 1).then(-.03).otherwise(pl.col('rate')).alias('rate'))
    future = carry.simulate_account(future_prices, future_events)
    assert result['minute_nav'].head(5).equals(future['minute_nav'].head(5))
    assert result['funding_ledger'].head(4).equals(future['funding_ledger'].head(4))
    with pytest.raises(ValueError):
        carry.simulate_account({**prices(), 'BTCUSDT': prices()['BTCUSDT'].head(5)}, events)
    with pytest.raises(ValueError):
        carry.simulate_account(prices(), pl.concat([events, events.head(1)]))
    with pytest.raises(ValueError, match='endpoint event'):
        carry.simulate_account(prices(), events.with_columns(pl.when(pl.col('event_us') == closes[-1] - 1)
            .then(closes[-1]).otherwise(pl.col('event_us')).alias('event_us')))
