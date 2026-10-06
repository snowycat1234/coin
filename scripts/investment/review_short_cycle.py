"""Finite paired economic decision over the saved BTC cycle accounts."""
import argparse,json,os
from datetime import UTC,datetime
from pathlib import Path
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment.cta_cycle_source import sha,save

ap=argparse.ArgumentParser();ap.add_argument('--producer',default='reports/fast_research/SHORT_FIXED_CYCLE_2022_2023_BASE27_20261006_V2.json')
a=ap.parse_args();path=(ROOT/a.producer).resolve();assert path.is_relative_to(ROOT/'reports/fast_research')
r=json.loads(path.read_bytes());task=json.loads((STATE/'task-progress'/('task-'+r['binding']['task_id']+'.json')).read_bytes())
assert task['status']=='completed' and task['exit_code']==0 and len(r['cases'])==r['required_accounts']==10
assert r['models_fit']==r['search_configurations']==0 and r['actual_days']==730 and r['protocol']['symbols']==['BTCUSDT']
assert len({c['id'] for c in r['cases']})==10
signal_path=Path(r['run_dir'])/'frozen_signals.parquet'
signals=pl.read_parquet(signal_path)
own_trend={v['close_us']:v['SMA200_SIGNED'] for v in signals.iter_rows(named=True)}
rows=[];paired={}
for c in r['cases']:
    s=c['summary'];assert s['completed_minutes']==s['required_minutes']==1051200 and s['terminal_cash_realized']
    # Price jumps can cross configured caps before the next eligible reduction.
    # Preserve the measured breach; the target reference verifies the caps.
    assert c['independent']['target_reference']['maximum_error']<1e-10
    assert c['independent']['maximum_NAV_error_USDT']<1e-7 and c['independent']['maximum_wallet_error_USDT']<1e-7
    assert abs(s['net_PnL']-(s['gross_PnL_same_quantities']+s['funding_USDT']-s['fees_USDT']-s['execution_cost_USDT']))<1e-7
    years={};own_groups={}
    for d in c['independent']['daily_direction_contributions']:
        year=str(datetime.fromtimestamp((d['day_end_us']-1)//1_000_000,UTC).year)
        v=years.setdefault(year,dict(days=0,LONG=0.,SHORT=0.,net=0.));v['days']+=1
        for k in ('LONG','SHORT'):v[k]+=d[k]
        v['net']+=d['LONG']+d['SHORT']
        own=own_trend[d['day_end_us']-86_400_000_000];assert own in (-1.,0.,1.)
        label={-1.:'BELOW_OWN_SMA200',0.:'EQUAL_OWN_SMA200',1.:'ABOVE_OWN_SMA200'}[own]
        g=own_groups.setdefault(year+'/'+label,dict(days=0,SHORT=0.));g['days']+=1;g['SHORT']+=d['SHORT']
    assert set(years)=={'2022','2023'} and sum(v['days'] for v in years.values())==730
    assert abs(sum(v['net'] for v in years.values())-s['net_PnL'])<1e-7
    assert abs(sum(v['SHORT'] for v in own_groups.values())-s['long_short_marked_contribution']['SHORT']['net_contribution'])<1e-7
    row=dict(id=c['id'],mode=c['mode'],unit=c['unit'],strategy=c['strategy'],net_USDT=s['net_PnL'],gross_USDT=s['gross_PnL_same_quantities'],
        fees_USDT=s['fees_USDT'],execution_USDT=s['execution_cost_USDT'],funding_USDT=s['funding_USDT'],
        drawdown_percent=s['minute_max_drawdown']*100,daily_metrics=s['daily_metrics'],exposure=s['realized_exposure'],
        turnover=s['normalized_total_turnover'],direction=s['long_short_marked_contribution'],calendar_year_contributions=years,
        actual_short_open_legs=c['independent']['actual_short_open_legs'],capital_USDT=10000,terminal_paid_flat=True,
        SHORT_by_past_own_SMA200_and_year=own_groups,concentration=s['daily_net_gain_concentration'])
    row['risk_drift']=dict(maximum_actual_gross_weight=s['maximum_actual_gross_weight'],maximum_actual_asset_weights=s['maximum_actual_asset_weights'],
        risk_reduction_signal_count=s['risk_reduction_signal_count'],maximum_observed_first_risk_reduction_latency_us=s['maximum_observed_first_risk_reduction_latency_us'],
        instantaneous_caps_guaranteed=s['actual_caps_instantaneously_guaranteed'])
    rows.append(row)
    if c['strategy']=='DC_CONFIRMED_SHORT':
        assert (c['mode'],c['unit']) not in paired
        paired[c['mode'],c['unit']]=row
assert len(paired)==6,'HOLD LONG_ONLY is a separate control, never the directional LONG_ONLY strategy'
decisions=[]
for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
    lo=paired['LONG_ONLY',unit];ls=paired['LONG_SHORT',unit]
    # Earlier summary variants expose annual realised vol under the same key.
    vol_lo=lo['daily_metrics']['annual_volatility'];vol_ls=ls['daily_metrics']['annual_volatility']
    short=ls['direction']['SHORT']['net_contribution']
    checks=dict(LS_net_gt_LO=ls['net_USDT']>lo['net_USDT'],total_SHORT_positive=short>0,
        year2022_SHORT_positive=ls['calendar_year_contributions']['2022']['SHORT']>0,
        DD_no_worse=ls['drawdown_percent']<=lo['drawdown_percent'],actual_vol_no_worse=vol_ls<=vol_lo)
    decisions.append(dict(unit=unit,checks=checks,pass_development_gate=all(checks.values()),
        LS_minus_LO_net=ls['net_USDT']-lo['net_USDT'],SHORT2023=ls['calendar_year_contributions']['2023']['SHORT']))
out=dict(status='PASS_PAIRED_FIXED_SHORT_CYCLE_EVIDENCE_NOT_NATIVE_OR_INVESTMENT',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
    producer=dict(path=str(path.relative_to(ROOT)),sha256=sha(path),task_id=r['binding']['task_id']),rows=rows,decisions=decisions,
    decision='RETAIN_D096_WITH_BTC_CYCLE_SUPPORT' if all(v['pass_development_gate'] for v in decisions) else 'NO_PROMOTION_RETAIN_ORIGINAL_SCOPE_ANALYZE_FAILURE',
    signal_proof=dict(path=str(signal_path),sha256=sha(signal_path)),
    attribution_scope='SAME_WALLET_DAILY_SHORT_PNL_BY_PAST_OWN_TREND; NOT_NEW_GATE_ECONOMICS_OR_REASON_CAUSALITY',
    new_accounts=0,fits=0,created_utc=datetime.now(UTC).isoformat(),limitations=['ONE_BTC_OLD_CYCLE_NOT_10COIN_GENERALIZATION','ETH_MARK_INCOMPLETE_PRESERVED',
    'FUNDING_UNIT_TWO_CONDITIONAL_SCALES','BINANCE_PRICE_BYBIT_FEE_PROXY','MMR_AND_QUANTITY_RULES_ASSUMED','DEVELOPMENT_HISTORY_NOT_LOCKED_OR_INVESTMENT_UNSEEN','LONG_TERM_APR_NOT_EVALUABLE'])
save(ROOT/'reports/SHORT_FIXED_CYCLE_REVIEW_20261006_V1.json',out)
print(json.dumps(dict(status=out['status'],decision=out['decision'],paired=decisions)))
