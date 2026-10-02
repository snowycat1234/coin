"""Independent invented-input probes of target intents; no market or fitting."""
from pathlib import Path
from datetime import date
import sys

import numpy as np
import polars as pl
import pytest

ROOT = Path('/mnt/d/codex/coin')
sys.path.insert(0, str(ROOT))
from scripts.research_v8 import benchmark_targets_v2 as b

RISKY = ('SPOT_BUY_AND_HOLD', 'VOL_MANAGED_BUY_AND_HOLD', 'FIXED_TREND', 'FIXED_MEAN_REVERSION')
BASE = int(np.datetime64('2025-12-10T00:00:00', 'us').astype(np.int64))

@pytest.fixture
def invented():
    calendar = BASE + np.arange(72, dtype=np.int64)*b.MINUTE_US
    times = BASE + np.arange(-280, 90, dtype=np.int64)*b.MINUTE_US
    bars = pl.DataFrame([{'symbol': symbol, 'close_us': int(stamp), 'available_us': int(stamp),
        'close': float(100+10*s+.015*i+.06*np.sin(i/4))}
        for s,symbol in enumerate(b.SYMBOLS) for i,stamp in enumerate(times)])
    ends = BASE + np.arange(-7,1,dtype=np.int64)*b.DAY_US
    risk = pl.DataFrame({'day_end_us': ends, 'available_us': ends,
                         'gross_exposure_return': np.array([-.08,.06,-.04,.07,-.05,.03,-.07,.04])})
    return bars,calendar,risk

def same_calendar(plan, calendar):
    assert plan.calendar_ledger.height == 2*len(calendar)
    for symbol in b.SYMBOLS:
        ledger=plan.calendar_ledger.filter(pl.col('symbol')==symbol)
        assert np.array_equal(ledger['decision_us'].to_numpy(),calendar)
        assert np.array_equal(ledger['earliest_permissible_order_us'].to_numpy(),calendar+5_000_000)
    assert plan.receipt['costs_paid'] is False and plan.receipt['economic_metrics'] is None
    assert not plan.receipt['V8_execution_engine_accepted'] and not plan.receipt['P1_economic_gate_passed']
    weights=plan.calendar_ledger['target_weight'].to_numpy()
    assert np.isfinite(weights).all() and (weights>=0).all() and (weights<=.3+1e-12).all()
    aggregate=plan.calendar_ledger.group_by('decision_us').agg(pl.col('target_weight').sum())
    assert aggregate['target_weight'].max()<=.6+1e-12

@pytest.mark.parametrize('identifier',RISKY)
def test_future_close_mutation_and_append_preserves_past_targets(invented,identifier):
    bars,calendar,risk=invented
    cutoff=int(calendar[18])
    altered=bars.with_columns(pl.when(pl.col('close_us')>cutoff).then(pl.col('close')*3.7)
                             .otherwise(pl.col('close')).alias('close'))
    future=pl.DataFrame([{'symbol':symbol,'close_us':int(calendar[-1]+(j+30)*b.MINUTE_US),
        'available_us':int(calendar[-1]+(j+30)*b.MINUTE_US),'close':float(2000+j)}
        for symbol in b.SYMBOLS for j in range(3)])
    plans=[b.fixed_targets(identifier,value,calendar,daily_returns=risk) for value in (bars,pl.concat([altered,future]))]
    for plan in plans:same_calendar(plan,calendar)
    assert plans[0].calendar_ledger.filter(pl.col('decision_us')<=cutoff).equals(
           plans[1].calendar_ledger.filter(pl.col('decision_us')<=cutoff))

def test_future_daily_returns_cannot_change_past_risk_or_targets(invented):
    bars,calendar,risk=invented
    future=pl.DataFrame({'day_end_us':[BASE+b.DAY_US,BASE+2*b.DAY_US],
        'available_us':[BASE+b.DAY_US,BASE+2*b.DAY_US],'gross_exposure_return':[-.95,4.]})
    changed=pl.concat([risk,future])
    assert b.causal_vol_multiplier(risk,int(calendar[0]))==b.causal_vol_multiplier(changed,int(calendar[0]))
    left=b.fixed_targets('VOL_MANAGED_BUY_AND_HOLD',bars,calendar,daily_returns=risk)
    right=b.fixed_targets('VOL_MANAGED_BUY_AND_HOLD',bars,calendar,daily_returns=changed)
    assert left.calendar_ledger.equals(right.calendar_ledger)
    same_calendar(left,calendar)
    small=risk.with_columns(pl.lit(.001).alias('gross_exposure_return'))
    assert b.causal_vol_multiplier(small,int(calendar[0]))==1.
    assert 0<b.causal_vol_multiplier(risk,int(calendar[0]))<1.

def frozen(frame,calendar,artifact):
    proof={'model_sha256':b.file_sha(artifact),'predictions_sha256':b.frame_sha(frame),
        'labels':'V8_NONOVERLAP_DIRECT_RETURN_BASELINE',
        'label_contract_sha256':b.file_sha(ROOT/'protocols/LABEL_CONTRACT_V8.json'),
        'label_implementation_source_sha256':b.file_sha(ROOT/'scripts/research_v8/labels_v3.py'),
        'strategy_source_sha256':'a'*64,'data_manifest_sha256':'b'*64,
        'fit_cutoff_us':BASE-3*b.MINUTE_US,'embargo_us':b.MINUTE_US,
        'max_fitting_label_mature_us':BASE-4*b.MINUTE_US,
        'forecast_decision_us':calendar.tolist(),'forecast_row_ids':list(range(len(calendar))),
        'fit_row_ids':[-7,-6]}
    return b.FrozenReturnPredictions(frame,proof,artifact)

def test_future_frozen_prediction_values_preserve_past_targets(invented,tmp_path):
    bars,calendar,_=invented
    artifact=tmp_path/'invented-frozen.fixture'
    artifact.write_bytes(b'INVENTED_FROZEN_BYTES_NOT_A_TRAINED_MARKET_MODEL')
    frame=pl.DataFrame([{'decision_us':int(t),'available_us':int(t),'symbol':s,'predicted_return':.004}
                        for t in calendar for s in b.SYMBOLS])
    cutoff=int(calendar[18])
    altered=frame.with_columns(pl.when(pl.col('decision_us')>cutoff).then(-.01)
                              .otherwise(pl.col('predicted_return')).alias('predicted_return'))
    left=b.fixed_targets('CURRENT_XGB',bars,calendar,frozen_predictions=frozen(frame,calendar,artifact))
    right=b.fixed_targets('CURRENT_XGB',bars,calendar,frozen_predictions=frozen(altered,calendar,artifact))
    assert left.calendar_ledger.filter(pl.col('decision_us')<=cutoff).equals(
           right.calendar_ledger.filter(pl.col('decision_us')<=cutoff))
    assert not left.calendar_ledger.equals(right.calendar_ledger)
    for plan in (left,right):same_calendar(plan,calendar)

def test_calendar_domain_rejects_coercion_holes_duplicates_and_locked(invented):
    bars,calendar,_=invented
    locked=int(np.datetime64('2026-03-01T00:00:00','us').astype(np.int64))
    variants=[calendar.astype(float),calendar.astype(float)+.5,calendar[None,:],
              np.delete(calendar,4),np.insert(calendar,4,calendar[4]),calendar[::-1],
              calendar-calendar[0]+locked]
    for malformed in variants:
        with pytest.raises(ValueError):b.fixed_targets('CASH',bars,malformed)

def test_missing_input_keeps_calendar_and_invalidates_entire_paired_period(invented):
    bars,calendar,risk=invented
    missing=bars.filter(~((pl.col('symbol')=='ETHUSDT') & (pl.col('close_us')==calendar[18])))
    cash=b.fixed_targets('CASH',bars,calendar)
    for identifier in RISKY:
        plan=b.fixed_targets(identifier,missing,calendar,daily_returns=risk)
        same_calendar(plan,calendar)
        assert plan.receipt['warmup_failed'] and not plan.receipt['paired_comparison_allowed']
        assert plan.receipt['calendar_sha256']==cash.receipt['calendar_sha256']
        with pytest.raises(ValueError):b.assert_paired_comparison([cash,plan])

def test_insufficient_warmup_never_selects_shorter_score_window(invented):
    bars,calendar,risk=invented
    cash=b.fixed_targets('CASH',bars,calendar)
    inputs=[('FIXED_TREND',bars.filter(pl.col('close_us')>=BASE-30*b.MINUTE_US),risk),
            ('FIXED_MEAN_REVERSION',bars.filter(pl.col('close_us')>=BASE-30*b.MINUTE_US),risk),
            ('VOL_MANAGED_BUY_AND_HOLD',bars,risk.tail(6))]
    for identifier,source,risk_source in inputs:
        plan=b.fixed_targets(identifier,source,calendar,daily_returns=risk_source)
        same_calendar(plan,calendar)
        assert plan.receipt['warmup_failed']
        with pytest.raises(ValueError):b.assert_paired_comparison([cash,plan])

def test_missing_carry_predictions_and_partial_ensemble_are_explicit(invented):
    bars,calendar,risk=invented
    plans={identifier:b.fixed_targets(identifier,bars,calendar,daily_returns=risk)
           for identifier in ('CASH','FIXED_TREND','FUNDING_BASIS_CARRY','CURRENT_XGB')}
    for name in ('FUNDING_BASIS_CARRY','CURRENT_XGB'):
        plan=plans[name];same_calendar(plan,calendar)
        assert plan.receipt['status'].startswith('NOT_EVALUABLE')
        assert not plan.receipt['paired_comparison_allowed']
    missing=('VOL_MANAGED_BUY_AND_HOLD','FIXED_MEAN_REVERSION','FUNDING_BASIS_CARRY','CURRENT_XGB')
    partial=b.partial_equal_risk_ensemble({'FIXED_TREND':plans['FIXED_TREND']},calendar,
                                        preregistered_missing_members=missing)
    same_calendar(partial,calendar)
    assert partial.strategy_id=='PARTIAL_ENSEMBLE_WITH_CASH_FOR_UNAVAILABLE_SLEEVES'
    assert partial.receipt['economic_comparison_status'].startswith('NOT_EVALUABLE')
    assert partial.receipt['cash_reserved_sleeve_budget']==.8 and not partial.receipt['full_ensemble_evaluable']
    assert partial.calendar_ledger['target_weight'].max()==.06
    with pytest.raises(ValueError):b.assert_paired_comparison([plans['CASH'],partial])
    with pytest.raises(ValueError):b.partial_equal_risk_ensemble({'FIXED_TREND':plans['FIXED_TREND']},calendar,
                                                              preregistered_missing_members=())
