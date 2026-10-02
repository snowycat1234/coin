"""One NEW period/source/endpoint case; no old monetary fixtures or market bytes."""
from copy import deepcopy
from pathlib import Path

import polars as pl
import pytest

from scripts.investment import conditional_carry_90d_period_adapter as period


def test_new90_period_source_identity_and_final_endpoint_causality(monkeypatch):
    # Proposed common protocol path: root freezes the actual file before execution.
    spec = period.base.income.project_json(
        period.base.ROOT / 'protocols/CONDITIONAL_CARRY_90D_FIXED_PERIOD_20261003_V1.json')
    view, counts = period.verify_spec(spec)
    reports = period._proof_reports(view, spec)
    assert counts == spec['expected_funding_events_by_symbol']
    assert sum(counts.values()) == spec['expected_funding_events']  # QA-derived, no assumed cadence/count.
    assert len(view['sources']) == 24
    assert len([r for r in view['sources'] if r['kind'] == 'spot1m']) == 6
    assert len([r for r in view['sources'] if r['kind'] == 'fundingRate']) == 6
    assert period._check_records(view, reports) == counts
    for field, changed in [('rows', 1), ('parquet_sha256', '0' * 64)]:
        tampered = deepcopy(view)
        row = next(r for r in tampered['sources'] if r['kind'] == 'fundingRate')
        row[field] = row[field] + changed if field == 'rows' else changed
        with pytest.raises(ValueError, match='source identity'):
            period._check_records(tampered, reports)

    # A post-Feb route must fail before even constructing a filesystem path.
    forbidden = dict(view['sources'][0], month='2026-03',
                     parquet_path='/DO_NOT_OPEN_LOCKED_MARCH/source.parquet')
    with monkeypatch.context() as guard:
        def forbidden_path(*args, **kwargs):
            raise AssertionError('Forbidden month reached a path operation')
        guard.setattr(period, 'Path', forbidden_path)
        with pytest.raises(ValueError, match='No March'):
            period._allowed_path(view, forbidden)

    end = period.END_US
    opens = [end - (4 - i) * period.base.MINUTE_US for i in range(4)]
    closes = [t + period.base.MINUTE_US for t in opens]
    synthetic = {symbol: pl.DataFrame(dict(open_us=opens, close_us=closes,
        spot_close=[100.] * 4, mark_close=[100.] * 4, index_close=[100.] * 4))
        for symbol in period.base.SYMBOLS}
    events = pl.DataFrame(dict(symbol=['BTCUSDT'], event_us=[end - 1], rate=[.001]))
    old_months = period.base.MONTHS
    old_start, old_end = period.base.START_US, period.base.END_US
    for policy in ('ALL_FLAT', 'PAIR_TRIM'):
        ns = period.context(spec, policy)
        assert ns['START_US'] == 1764547200000000 and ns['END_US'] == 1772323200000000
        assert ns['MONTHS'] == ('2025-12', '2026-01', '2026-02')
        origin = period.base.__dict__ if policy == 'ALL_FLAT' else period.trim._compiled()[0]
        assert ns['simulate_account'].__code__ == origin['simulate_account'].__code__
        assert ns['simulate_account'].__globals__ is ns and ns is not origin
        assert ns['validate_inputs'](synthetic, events) == closes
        previous = ns['bisect_left'](closes, end - 1) - 1
        assert previous == 2 and closes[previous] < end - 1 < closes[-1]
        with pytest.raises(ValueError, match='endpoint event'):
            ns['validate_inputs'](synthetic, events.with_columns(pl.lit(end).alias('event_us')))
        march = {s: f.with_columns((pl.col('open_us') + 4 * period.base.MINUTE_US),
                                  (pl.col('close_us') + 4 * period.base.MINUTE_US))
                 for s, f in synthetic.items()}
        march_events = events.with_columns((pl.col('event_us') + 4 * period.base.MINUTE_US))
        with pytest.raises(ValueError, match='post-Feb'):
            ns['validate_inputs'](march, march_events)

    # Original inclusive-ms source endpoint maps to logical Mar1 without reading March.
    raw = pl.DataFrame(dict(timestamp_ms=[t // 1000 for t in opens],
        close_time_ms=[t // 1000 - 1 for t in closes], close=[100.] * 4))
    canonical = period.base.basis.canonical_prices('markPriceKlines', raw, 'BTCUSDT')
    assert canonical['open_us'][-1] < end and canonical['close_us'][-1] == end
    future = raw.with_columns(pl.when(pl.col('timestamp_ms') == opens[-1] // 1000)
        .then(999.).otherwise(pl.col('close')).alias('close'))
    shifted = period.base.basis.canonical_prices('markPriceKlines', future, 'BTCUSDT')
    assert canonical.head(previous + 1).equals(shifted.head(previous + 1))
    assert period.base.MONTHS == old_months and period.base.START_US == old_start and period.base.END_US == old_end
    # No simulate_account/load_inputs invoked: this new case is not a rerun of fee/cash fixtures.
