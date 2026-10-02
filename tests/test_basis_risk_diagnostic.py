"""One hand-calculated alignment/risk/prefix case; no historical files."""
import polars as pl
import pytest

from scripts.investment import basis_risk_diagnostic as diagnostic


def test_fixed_quantity_basis_sign_drawdown_local_baseline_decomposition_and_alignment():
    start = 1756684740000000  # Aug31 23:59UTC; next three candles belong to September.
    stamps = [start + i * diagnostic.MINUTE_US for i in range(4)]
    spot = pl.DataFrame(dict(open_us=stamps, close_us=[t + diagnostic.MINUTE_US for t in stamps],
        close=[100.] * 4, symbol=['BTCUSDT'] * 4, valid_day=[True] * 4))
    mark = pl.DataFrame(dict(timestamp_ms=[t // 1000 for t in stamps],
        close_time_ms=[t // 1000 + 59999 for t in stamps], close=[101., 100., 103., 102.]))
    index = mark.with_columns(pl.lit(100.5).alias('close'))
    def join(spot_source=spot, mark_source=mark, index_source=index):
        return diagnostic.join_prices(diagnostic.canonical_prices('spot1m', spot_source, 'BTCUSDT'),
            diagnostic.canonical_prices('markPriceKlines', mark_source, 'BTCUSDT'),
            diagnostic.canonical_prices('indexPriceKlines', index_source, 'BTCUSDT'),
            start, start + 4 * diagnostic.MINUTE_US)
    joined = join()
    path = diagnostic.basis_path(joined)
    assert path['basis'].to_list() == [1., 0., 3., 2.]
    assert path['basis_change_bp'].to_list() == [0., -100., 200., 100.]
    assert path['basis_valuation_change_bp'].to_list() == [0., 100., -200., -100.]
    assert path['basis_drawdown_bp'].to_list() == [0., 0., 300., 200.]
    full = diagnostic.window_statistics(joined)
    assert full['denominator_S0'] == 100. and full['start_difference'] == 1. and full['end_difference'] == 2.
    assert full['terminal_change_bp'] == 100. and full['terminal_valuation_change_bp'] == -100.
    assert full['max_adverse_change_bp'] == 200. and full['max_favorable_change_bp'] == 100.
    assert full['max_valuation_drawdown_bp'] == 300. and full['initial_zero_in_running_peak']
    assert full['maximum_decomposition_change_error_bp'] == 0. and full['maximum_decomposition_level_error_bp'] == 0.
    assert full['components']['index_spot']['terminal_change_bp'] == 0.
    month = diagnostic.window_statistics(joined.tail(3))
    assert month['start_difference'] == 0. and month['terminal_change_bp'] == 200.
    assert month['max_adverse_change_bp'] == 300. and month['max_valuation_drawdown_bp'] == 300.
    changed_mark = mark.with_columns(pl.when(pl.col('timestamp_ms') == stamps[-1] // 1000)
        .then(150.).otherwise(pl.col('close')).alias('close'))
    future_path = diagnostic.basis_path(join(mark_source=changed_mark))
    assert path.head(3).equals(future_path.head(3))  # Future source perturbation cannot change past derived values.
    with pytest.raises(ValueError):
        join(mark_source=mark.head(3))
    with pytest.raises(ValueError):
        join(index_source=index.with_columns((pl.col('close_time_ms') + 1).alias('close_time_ms')))
    with pytest.raises(ValueError):
        join(spot_source=spot.with_columns((pl.col('close_us') - 1).alias('close_us')))
    with pytest.raises(ValueError):
        join(spot_source=spot.with_columns(pl.lit(False).alias('valid_day')))
    with pytest.raises(ValueError):
        join(spot_source=spot.with_columns(pl.lit(None, dtype=pl.Boolean).alias('valid_day')))
    with pytest.raises(ValueError):
        join(spot_source=spot.with_columns(pl.lit(None, dtype=pl.String).alias('symbol')))
    with pytest.raises(ValueError):
        join(mark_source=mark.with_columns(pl.lit(float('nan')).alias('close')))
    with pytest.raises(ValueError):
        join(mark_source=pl.concat([mark, mark.head(1)]))
