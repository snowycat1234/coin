"""Finite paired economic decision over the saved BTC cycle accounts."""
import argparse,json,os
from datetime import UTC,datetime
from pathlib import Path
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment.reuse_cycle_controls import sha

def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')

ap=argparse.ArgumentParser();ap.add_argument('--producer',action='append')
ap.add_argument('--strategy',choices=['DC_CONFIRMED_SHORT','SMA200_SIGNED','SMA200_SHORT50','PUBLIC_SMA50_200'],default='DC_CONFIRMED_SHORT')
ap.add_argument('--output',default='reports/SHORT_FIXED_CYCLE_REVIEW_20261006_V1.json')
a=ap.parse_args();raws=[];producers=[];cases=[];controls={}
for name in a.producer or ['reports/fast_research/SHORT_FIXED_CYCLE_2022_2023_BASE27_20261006_V2.json']:
    path=(ROOT/name).resolve();assert path.is_relative_to(ROOT/'reports/fast_research')
    part=json.loads(path.read_bytes());task=json.loads((STATE/'task-progress'/('task-'+part['binding']['task_id']+'.json')).read_bytes())
    assert task['status']=='completed' and task['exit_code']==0 and len(part['cases'])==part['required_accounts']
    assert part['models_fit']==part['search_configurations']==0 and part['actual_days']==730 and part['protocol']['symbols']==['BTCUSDT']
    if raws:
        for key in ('symbols','data_manifest','locked_sha256','preparation_start','economics_start','economics_end_exclusive','cost','cost_ids','resources'):
            assert part['protocol'][key]==raws[0]['protocol'][key]
    raws.append(part);cases+=part['cases']
    producers.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path),task_id=part['binding']['task_id']))
    for c in part.get('reused_controls',[]):
        if c['id'] in controls:assert controls[c['id']]==c
        controls[c['id']]=c
    for c in part.get('reused_directional_controls',[]):
        assert a.strategy=='SMA200_SHORT50' and part['unchanged_long_proof']['status']=='PASS_ALL730D_TARGETS_EXACTLY_SAME'
        if c['id'] in controls:assert controls[c['id']]==c
        controls[c['id']]=c
r=raws[0];new_accounts=len(cases);cases+=list(controls.values())
assert len(cases)==len({c['id'] for c in cases})==10
signal_path=Path(r['run_dir'])/'frozen_signals.parquet'
signals=pl.read_parquet(signal_path)
own_trend={v['close_us']:v['SMA200_SIGNED'] for v in signals.iter_rows(named=True)}
rows=[];paired={}
for c in cases:
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
    if c['strategy']==a.strategy or a.strategy=='SMA200_SHORT50' and c['strategy']=='SMA200_SIGNED' and c['mode']=='LONG_ONLY':
        assert (c['mode'],c['unit']) not in paired
        paired[c['mode'],c['unit']]=row
assert len(paired)==6,'HOLD LONG_ONLY is a separate control, never the directional LONG_ONLY strategy'
decisions=[]
reference=None
if a.strategy in ('SMA200_SIGNED','SMA200_SHORT50','PUBLIC_SMA50_200'):
    ref=r['protocol']['comparison_reference'];assert sha(ROOT/ref['path'])==ref['sha256']
    reference=json.loads((ROOT/ref['path']).read_bytes());assert reference['status']=='PASS_PAIRED_FIXED_SHORT_CYCLE_EVIDENCE_NOT_NATIVE_OR_INVESTMENT'
for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
    lo=paired['LONG_ONLY',unit];ls=paired['LONG_SHORT',unit]
    # Earlier summary variants expose annual realised vol under the same key.
    vol_lo=lo['daily_metrics']['annual_volatility'];vol_ls=ls['daily_metrics']['annual_volatility']
    short=ls['direction']['SHORT']['net_contribution']
    checks=dict(LS_net_gt_LO=ls['net_USDT']>lo['net_USDT'],total_SHORT_positive=short>0,
        year2022_SHORT_positive=ls['calendar_year_contributions']['2022']['SHORT']>0)
    if reference is None:
        checks.update(DD_no_worse=ls['drawdown_percent']<=lo['drawdown_percent'],actual_vol_no_worse=vol_ls<=vol_lo)
    else:
        if a.strategy in ('SMA200_SHORT50','PUBLIC_SMA50_200'):
            old=next(v for v in reference['rows'] if v['strategy']=='SMA200_SIGNED' and v['mode']=='LONG_SHORT' and v['unit']==unit)
            checks.update(LS_net_gt_D100_LS=ls['net_USDT']>old['net_USDT'],DD_no_worse_than_D100_LS=ls['drawdown_percent']<=old['drawdown_percent'],
                LS_Sharpe_gt_own_LO=ls['daily_metrics']['sharpe']>lo['daily_metrics']['sharpe'],
                SHORT2023_loss_reduced=ls['calendar_year_contributions']['2023']['SHORT']>old['calendar_year_contributions']['2023']['SHORT'])
            if a.strategy=='PUBLIC_SMA50_200':
                checks.pop('LS_Sharpe_gt_own_LO')
                checks['LS_Sharpe_ge_D100_LS']=ls['daily_metrics']['sharpe']>=old['daily_metrics']['sharpe']
        else:
            old=next(v for v in reference['rows'] if v['strategy']=='DC_CONFIRMED_SHORT' and v['mode']=='LONG_SHORT' and v['unit']==unit)
            checks.update(LS_net_gt_D099_LS=ls['net_USDT']>old['net_USDT'],DD_no_worse_than_D099_LS=ls['drawdown_percent']<=old['drawdown_percent'],
                LS_Sharpe_gt_own_LO=ls['daily_metrics']['sharpe']>lo['daily_metrics']['sharpe'])
    decisions.append(dict(unit=unit,checks=checks,pass_development_gate=all(checks.values()),
        LS_minus_LO_net=ls['net_USDT']-lo['net_USDT'],SHORT2023=ls['calendar_year_contributions']['2023']['SHORT'],
        actual_risk_not_equalized=dict(LO_vol=vol_lo,LS_vol=vol_ls,LO_DD=lo['drawdown_percent'],LS_DD=ls['drawdown_percent'])))
out=dict(status='PASS_PAIRED_FIXED_SHORT_CYCLE_EVIDENCE_NOT_NATIVE_OR_INVESTMENT',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
    producers=producers,rows=rows,decisions=decisions,strategy=a.strategy,
    decision=('RETAIN_PUBLIC_CLASSIC_CYCLE_CHALLENGER_RISK_NOT_EQUALIZED' if a.strategy=='PUBLIC_SMA50_200' else 'RETAIN_PUBLIC_SMA200_CYCLE_CHALLENGER_RISK_NOT_EQUALIZED' if a.strategy.startswith('SMA200') else 'RETAIN_D096_WITH_BTC_CYCLE_SUPPORT') if all(v['pass_development_gate'] for v in decisions) else 'NO_PROMOTION_RETAIN_ORIGINAL_SCOPE_ANALYZE_FAILURE',
    signal_proof=dict(path=str(signal_path),sha256=sha(signal_path)),
    attribution_scope='SAME_WALLET_DAILY_SHORT_PNL_BY_PAST_OWN_TREND; NOT_NEW_GATE_ECONOMICS_OR_REASON_CAUSALITY',
    new_accounts_in_review=0,economic_accounts_referenced=new_accounts,reused_control_accounts=len(controls),fits=0,created_utc=datetime.now(UTC).isoformat(),limitations=['ONE_BTC_OLD_CYCLE_NOT_10COIN_GENERALIZATION','ETH_MARK_INCOMPLETE_PRESERVED',
    'FUNDING_UNIT_TWO_CONDITIONAL_SCALES','BINANCE_PRICE_BYBIT_FEE_PROXY','MMR_AND_QUANTITY_RULES_ASSUMED','DEVELOPMENT_HISTORY_NOT_LOCKED_OR_INVESTMENT_UNSEEN','LONG_TERM_APR_NOT_EVALUABLE'])
if len(producers)==1:out['producer']=producers[0]
output=(ROOT/a.output).resolve();assert output.is_relative_to(ROOT/'reports')
save(output,out)
print(json.dumps(dict(status=out['status'],decision=out['decision'],paired=decisions)))
