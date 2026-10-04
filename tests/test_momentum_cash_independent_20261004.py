"""One hand-state counterexample for the new independent past30 target oracle.

No producer targets/hooks, account simulator, price source QA or old replay.
All arrays below are artificial; the caller supplies an exclusive STATE tmp_path.
"""
import json

import numpy as np
import polars as pl
import pytest

from scripts.investment import multi_asset_financial_audit as audit


def test_independent_momentum_exact30_equality_reset_and_future(tmp_path):
    day = audit.DAY
    symbols = ('ZZZUSDT', 'AAAUSDT', 'MMMUSDT')  # Deliberately not catalogue order.
    tails = ([101., 102., 99., 102., 103., 999.],
             [100., 101., 100., 99., 102., 999.], [100.] * 6)
    bars = {}
    for symbol, tail in zip(symbols, tails, strict=True):
        prices = np.asarray([100.] * 199 + list(tail))
        if symbol == symbols[0]:
            prices[170] = 102.  # A mistaken 29-day anchor blocks the first real entry.
        ends = np.arange(1, len(prices) + 1, dtype=np.int64) * day
        bars[symbol] = pl.DataFrame(dict(open_us=ends-day, close_us=ends,
            available_us=ends, close=prices))
    start, end = 200 * day, 205 * day
    window = dict(start=start, end=end, bars=bars)
    result = audit.target_reference(window, symbols, strategy_id=audit.MOMENTUM_POOL_STRATEGY)
    states = [[1, 0, 0], [0, 1, 0], [0, 0, 0], [1, 0, 0], [1, 1, 0]]
    share = min(.3, .6 / 3)
    for offset, state in enumerate(states):
        one = result.filter(pl.col('available_us') == start + offset * day)
        raw = [share * value for value in state]
        assert one['symbol'].to_list() == list(symbols)
        assert one['raw_signed_target'].to_list() == raw  # Idle budget is not reassigned.
        assert one['mode'].to_list() == ['LONG_ONLY'] * 3
        assert np.all(one['target_weight'].to_numpy() >= 0)
        assert np.all(one['target_weight'].to_numpy() <= np.asarray(raw) + 1e-13)
    evidence = window['independent_momentum_state_witnesses']
    first = evidence[0]
    assert first['old_state'] == 0 and first['action'] == 'ENTER_LONG'
    assert first['prior_close_us'] == first['latest_close_us'] - 30 * day
    assert first['latest_completed_close'] == 101. and first['completed_close_30_days_earlier'] == 100.
    exit_row = next(r for r in evidence if r['symbol'] == symbols[0] and r['decision_us'] == start + day)
    assert exit_row['latest_completed_close'] == exit_row['completed_close_30_days_earlier'] == 102.
    assert exit_row['old_state'] == 1 and exit_row['new_state'] == 0 and exit_row['action'] == 'EXIT_TO_CASH'
    assert next(r for r in evidence if r['symbol'] == symbols[0] and
                r['decision_us'] == start + 3 * day)['action'] == 'ENTER_LONG'

    # No epsilon: a single representable positive step is an entry.
    tiny = dict(bars)
    tiny[symbols[0]] = bars[symbols[0]].with_columns(
        pl.when(pl.col('close_us') == start).then(np.nextafter(100., np.inf))
          .otherwise(pl.col('close')).alias('close'))
    assert audit.target_reference(dict(window, end=start+day, bars=tiny), symbols,
        strategy_id=audit.MOMENTUM_POOL_STRATEGY)['raw_signed_target'][0] == share
    with pytest.raises(ValueError, match='equal member shares'):
        audit.target_reference(window, symbols, 'INVERSE_VOL_30D', strategy_id=audit.MOMENTUM_POOL_STRATEGY)

    future = {s:f.with_columns(pl.when(pl.col('close_us') > start+day).then(pl.col('close')*1000.)
        .otherwise(pl.col('close')).alias('close')) for s, f in bars.items()}
    prefix = audit.target_reference(dict(window, end=start+2*day, bars=future), symbols,
        strategy_id=audit.MOMENTUM_POOL_STRATEGY)
    assert prefix.equals(result.filter(pl.col('available_us') <= start+day))
    delayed = dict(bars)
    delayed[symbols[0]] = bars[symbols[0]].with_columns(
        pl.when(pl.col('close_us') == start).then(pl.col('available_us')+1)
          .otherwise(pl.col('available_us')).alias('available_us'))
    late_window = dict(window, end=start+2*day, bars=delayed)
    late = audit.target_reference(late_window, symbols, strategy_id=audit.MOMENTUM_POOL_STRATEGY)
    assert late['eligibility_reason'][0] == 'WARMUP_OR_DATA_GAP' and late['raw_signed_target'][0] == 0.
    assert late['raw_signed_target'][3] == 0.  # Now available, but equal and freshly flat.
    missing = dict(bars)
    missing[symbols[0]] = bars[symbols[0]].filter(pl.col('close_us') != 199*day)
    gap = audit.target_reference(dict(window, end=start+day, bars=missing), symbols,
        strategy_id=audit.MOMENTUM_POOL_STRATEGY)
    assert gap['eligibility_reason'][0] == 'WARMUP_OR_DATA_GAP' and gap['target_weight'][0] == 0.

    membership = {start:symbols, start+day:symbols[1:], start+2*day:symbols}
    member_window = dict(window, end=start+3*day, eligible_by_decision=membership)
    member = audit.target_reference(member_window, symbols, strategy_id=audit.MOMENTUM_POOL_STRATEGY)
    assert member['eligibility_reason'][3] == 'POOL_EXIT' and member['raw_signed_target'][3] == 0.
    assert member['raw_signed_target'][6] == 0.  # Rejoining does not restore warmup inventory.
    reset = next(r for r in member_window['independent_momentum_state_witnesses']
                 if r['symbol'] == symbols[0] and r['decision_us'] == start+day)
    assert reset['old_state'] == 1 and reset['new_state'] == 0
    (tmp_path/'independent_momentum_evidence.json').write_text(json.dumps(dict(
        source_sha256=audit.sha(audit.ROOT/'scripts/investment/multi_asset_financial_audit.py'),
        expected_states=states, strict_comparison_without_epsilon=True, exact30_days=True,
        future_prefix_unchanged=True, gap_and_membership_reset_verified=True,
        producer_target_or_hook_calls=0, financial_calls=0, source_QA_calls=0, models_fit=0),
        allow_nan=False), encoding='utf-8')
