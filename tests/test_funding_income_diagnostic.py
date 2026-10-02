"""One fixed Decimal coupon/cost case; no historical files or old source QA."""
from decimal import Decimal

import polars as pl
import pytest

from scripts.investment import funding_income_diagnostic as diagnostic


def test_signed_coupon_initial_zero_drawdown_negative_runs_and_two_leg_hurdles():
    # Five hand-authored4h events cross Aug/Sep. Zero ends a negative run.
    stamps = [1756641600001 + step*4*3600000 for step in range(5)]
    frame = pl.DataFrame(dict(symbol=['BTCUSDT']*5+['ETHUSDT']*5,calc_time_ms=stamps*2,
        funding_interval_hours=[4.]*10,
        last_funding_rate=[.0001,-.00005,-.00002,0.,.00008,-.00002,.00001,0.,-.00003,.00004]))
    stats,prefix = diagnostic.coupon_statistics(frame)
    btc,eth = stats
    assert Decimal(str(btc['signed_coupon_bp'])) == Decimal('1.1')
    assert Decimal(btc['signed_raw_rate_sum_decimal']) == Decimal('.00011')
    assert btc['negative_events'] == 2 and btc['zero_events'] == 1
    assert btc['longest_negative_run_events'] == 2
    assert Decimal(str(btc['worst_negative_run_signed_coupon_bp'])) == Decimal('-.7')
    assert Decimal(str(btc['max_prefix_coupon_drawdown_bp'])) == Decimal('.7')
    assert [row['signed_coupon_bp'] for row in btc['months']] == [.3,.8,0.,0.]
    assert all(not row['monthly_costs_subtracted'] for row in btc['months'])
    assert eth['signed_coupon_bp'] == 0. and eth['longest_negative_run_events'] == 1
    assert Decimal(str(eth['max_prefix_coupon_drawdown_bp'])) == Decimal('.4')  # Initial0, not first negative point.
    assert prefix.filter(pl.col('symbol')=='ETHUSDT')['prefix_coupon_drawdown_bp'][0] == .2
    costs = dict(spot_fee_bps_per_side=10,perp_taker_fee_bps_per_side=5.5,
        assumed_slippage_bps_per_side=4,assumed_each_leg_roundtrip_spread_bps=[2,4,8])
    hurdles = diagnostic.cost_hurdles(costs)
    assert [row['total_hurdle_bps'] for row in hurdles] == [31.,51.,55.,63.]
    assert [Decimal(str(btc['signed_coupon_bp']))-Decimal(str(row['total_hurdle_bps'])) for row in hurdles] == [
        Decimal('-29.9'),Decimal('-49.9'),Decimal('-53.9'),Decimal('-61.9')]
    probe = dict(status=diagnostic.PROBE_STATUS,funding_rate_unit='FRACTION',bp_multiplier=10000,
                 unit_evidence=dict(qualification='SYNTHETIC_SCHEMA_ONLY'))
    spec = dict(funding_rate_unit='FRACTION',bp_multiplier=10000,
                unit_probe=dict(basis='SAMPLED_API_PARITY',required_status=diagnostic.PROBE_STATUS))
    unit = diagnostic.validate_units(spec,probe)
    assert not unit['full_732_event_unit_certified'] and not unit['realized_rate_is_available_trading_signal']
    with pytest.raises(ValueError):
        diagnostic.validate_units({**spec,'bp_multiplier':100},probe)
    with pytest.raises(ValueError):
        diagnostic.validate_units(spec,{**probe,'status':'FAIL_OFFICIAL_FUNDING_API_PARITY_UNCONFIRMED'})
    conditional_spec = dict(funding_rate_unit='UNCONFIRMED',assumed_funding_rate_unit='FRACTION',bp_multiplier=10000,
        unit_probe=dict(basis=diagnostic.ASSUMPTION_BASIS,required_status=diagnostic.FAILED_PROBE_STATUS,
                        sha256=diagnostic.FAILED_PROBE_SHA))
    conditional_probe = dict(status=diagnostic.FAILED_PROBE_STATUS,funding_rate_unit='UNCONFIRMED',bp_multiplier=None,
        unit_evidence=dict(qualification='NOT_YET_ESTABLISHED',matched_records=0,sample_parity_status='UNCONFIRMED'),
        comparisons=[],funding_income_calculated=False,mark_index_arrays_read=False,actual_operation_exit_code=1,
        reason='Official API access/rate restriction; stop without another request or bypass',
        requests=[dict(url=diagnostic.RESTRICTED_URL,final_url=diagnostic.RESTRICTED_URL,status='HTTP_FAILURE',
                       http_status=451,retries=0,redirects_followed=0)])
    conditional = diagnostic.validate_units(conditional_spec,conditional_probe)
    assert conditional['conditional_fraction_assumption'] and conditional['raw_rate_unit'] == 'UNCONFIRMED'
    assert conditional['assumed_funding_rate_unit'] == 'FRACTION' and conditional['probe_funding_rows_read'] == 0
    assert not conditional['sampled_API_unit_certified'] and not conditional['full_732_event_unit_certified']
    with pytest.raises(ValueError):
        diagnostic.validate_units({**conditional_spec,'unit_probe':{**conditional_spec['unit_probe'],'basis':'AUTO_FALLBACK'}},conditional_probe)
    with pytest.raises(ValueError):
        diagnostic.validate_units(conditional_spec,{**conditional_probe,'requests':[{**conditional_probe['requests'][0],'http_status':403}]})
    with pytest.raises(ValueError):
        diagnostic.coupon_statistics(pl.concat([frame,frame.head(1)]))
    with pytest.raises(ValueError):
        diagnostic.coupon_statistics(frame.with_columns(pl.lit(float('nan')).alias('last_funding_rate')))
    assert frame.height == 10 and frame['last_funding_rate'][0] == .0001
