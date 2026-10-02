"""Only the new D032 cash-window/scheduling branch; no old money suite replay."""
from pathlib import Path

import polars as pl
import pytest

from scripts.investment import conditional_carry_account as base
from scripts.investment import conditional_carry_past_funding_exit_adapter as gate


def test_fixed_owned_lag_window_midnight_next_close_permanent_cash_and_future_invariance():
    spec = base.income.project_json(gate.PROTOCOL)
    original_start, original_rules = base.START_US, dict(base.RULES)
    ns122, ns90 = gate.context(spec, '122D'), gate.context(spec, '90D')
    assert ns90['START_US'] == 1764547200000000 and ns90['END_US'] == 1772323200000000
    assert ns122['START_US'] == base.START_US and ns122['END_US'] == base.END_US
    assert ns122['simulate_account'].__globals__ is ns122
    assert ns90['simulate_account'].__globals__ is ns90
    assert ns122['FUNDING_GATE_DERIVATION']['derived_simulate_AST_sha256'] == ns90['FUNDING_GATE_DERIVATION']['derived_simulate_AST_sha256']
    assert len(ns122['FUNDING_GATE_DERIVATION']['new_gate_changes']) == 3
    assert not ns122['FUNDING_GATE_DERIVATION']['event_loop_reordered']
    day = base.START_US + 9 * gate.DAY_US
    start, end = day - 8 * gate.DAY_US, day - gate.DAY_US
    def row(t, value, owned=True):
        return dict(event_us=t, ownership_qualified=owned, signed_funding_USDT=value)
    rows = [row(start-1000, 999.), row(start, -2.), row(end-1000, 2.),
            row(end, -999.), row(start+1000, -999., False), row(day, -999.)]
    witness = gate.gate_witness(day, start-1, rows)
    assert witness['eligible'] and witness['condition_met'] and witness['signed_owned_funding_sum_USDT'] == 0.
    assert witness['selected_row_indices'] == [1, 2] and witness['owned_event_count'] == 2
    negative = [dict(r) for r in rows]
    negative[2]['signed_funding_USDT'] = 1.
    assert gate.gate_witness(day, start-1, negative)['signed_owned_funding_sum_USDT'] == -1.
    assert gate.gate_witness(day, start-1, negative)['condition_met']
    positive = [dict(r) for r in rows]
    positive[2]['signed_funding_USDT'] = 3.
    assert not gate.gate_witness(day, start-1, positive)['condition_met']
    assert witness['window_start_us'] == start and witness['window_end_exclusive_us'] == end
    assert witness['decision_observation_us'] == day + 1 and not witness['historical_availability_certified']
    assert not gate.gate_witness(day, start, rows)['eligible']  # window start must be strictly after entry
    assert not gate.gate_witness(day, start+1, rows)['eligible']  # exact eight-day holding guard
    with pytest.raises(ValueError):
        gate.gate_witness(day+1, start-1, rows)  # no near-midnight masquerade
    with pytest.raises(ValueError):
        gate.gate_witness(float(day), start-1, rows)  # no timestamp truncation
    modified = [dict(r) for r in rows]
    modified[-1]['signed_funding_USDT'] = 1e100
    modified[3]['signed_funding_USDT'] = 1e100
    assert gate.gate_witness(day, start-1, modified) == witness

    # A small12day constant-price calendar exercises only the new gate path.
    # No old financial hand calculation or old accepted control is rerun.
    count = 12 * 1440
    closes = [base.START_US + (i+1)*base.MINUTE_US for i in range(count)]
    frames = {symbol: pl.DataFrame(dict(open_us=[t-base.MINUTE_US for t in closes], close_us=closes,
        spot_close=[100.]*count, mark_close=[100.]*count, index_close=[100.]*count))
        for symbol in base.SYMBOLS}
    event_times = [base.START_US + i*gate.DAY_US + gate.DAY_US//2 for i in range(12)]
    rates = [.000001] + [-.000001]*7 + [.01, .001, .001, .001]
    events = pl.DataFrame(dict(symbol=['BTCUSDT']*12, event_us=event_times, rate=rates))
    result = ns122['simulate_account'](frames, events)
    summary = result['summary']
    assert summary['exit_reason'] == gate.EXIT_REASON and summary['past_funding_gate_scheduled'] == 1
    decision = base.START_US + 9*gate.DAY_US
    fill_close, fill_time = decision + base.MINUTE_US, decision + base.MINUTE_US + 1
    assert summary['stop_signal_us'] == decision+1 and summary['exit_us'] == fill_time
    assert summary['permanent_cash_after_exit'] and summary['fills'] == 8
    fired = next(r for r in summary['past_funding_gate_checks'] if r['action'] == 'SCHEDULE_PERMANENT_FULL_EXIT')
    assert fired['decision_price_close_us'] == decision and fired['scheduled_fill_us'] == fill_time
    selected = result['funding_ledger'].filter(pl.col('ownership_qualified') &
        pl.col('event_us').is_between(fired['window_start_us'], fired['window_end_exclusive_us'], closed='left'))
    assert fired['owned_event_count'] == selected.height
    assert fired['signed_owned_funding_sum_USDT'] == pytest.approx(selected['signed_funding_USDT'].sum(), abs=1e-12)
    assert max(fired['selected_event_times_us']) < decision-gate.DAY_US
    late = result['funding_ledger'].filter(pl.col('event_us') > fill_time)
    assert not late['ownership_qualified'].any() and late['signed_funding_USDT'].eq(0.).all()
    assert result['minute_nav'].filter(pl.col('close_us') > fill_close)['BTCUSDT_spot_and_short_q'].eq(0.).all()
    assert result['minute_nav'].filter(pl.col('close_us') > fill_close)['ETHUSDT_spot_and_short_q'].eq(0.).all()
    assert summary['fees_USDT'] > 0 and summary['capital_net_APR'] == 'NOT_EVALUABLE'
    # Perturb funding after the frozen exit: no prior signal, ownership or NAV change.
    future_rates = list(rates)
    future_rates[9:] = [1., -1., .5]
    perturbed = pl.DataFrame(dict(symbol=['BTCUSDT']*12, event_us=event_times, rate=future_rates))
    future = ns122['simulate_account'](frames, perturbed)
    assert future['summary']['past_funding_gate_checks'] == summary['past_funding_gate_checks']
    assert future['minute_nav'].equals(result['minute_nav'])
    # New interaction: a same-observation margin order keeps priority over the gate.
    decision_index = closes.index(decision)
    margin_frames = dict(frames)
    margin_frames['BTCUSDT'] = frames['BTCUSDT'].with_columns(
        pl.Series('mark_close', [100.]*decision_index + [151.]*(count-decision_index)))
    margin = ns122['simulate_account'](margin_frames, events)
    assert margin['summary']['exit_reason'] == 'SELF_DEFINED_ISOLATED_MARGIN_ALL_FLAT'
    assert margin['summary']['past_funding_gate_scheduled'] == 0
    assert any(r['action'] == 'KEEP_ALREADY_PENDING_FULL_EXIT'
               for r in margin['summary']['past_funding_gate_checks'])
    # An already due cap trim is still dispatched before the later gate full exit.
    partial_frames = dict(frames)
    shifted = [100.]*(decision_index-1) + [121.]*(count-decision_index+1)
    partial_frames['BTCUSDT'] = frames['BTCUSDT'].with_columns(
        pl.Series('spot_close', shifted), pl.Series('mark_close', shifted))
    partial = ns122['simulate_account'](partial_frames, events)
    assert partial['summary']['exit_reason'] == gate.EXIT_REASON
    assert partial['summary']['completed_pair_reductions'] == 1
    assert partial['summary']['pair_reductions'][0]['fill_us'] == decision+1
    assert partial['summary']['exit_us'] == fill_time
    partial_fired = next(r for r in partial['summary']['past_funding_gate_checks']
                         if r['action'] == 'SCHEDULE_PERMANENT_FULL_EXIT')
    assert partial_fired['pending_pair_symbols_before'] == ['BTCUSDT']
    assert base.START_US == original_start and base.RULES == original_rules