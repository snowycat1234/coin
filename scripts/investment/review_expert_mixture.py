"""Paired actual-wallet economics; keep informed oracle outside candidates."""
import argparse,json,os
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.investment.reuse_cycle_controls import sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--producer',action='append',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    refs=[];cases=[];controls={};first=None
    for name in a.producer:
        p=ROOT/name;r=json.loads(p.read_bytes());t=json.loads((STATE/'task-progress'/('task-'+r['binding']['task_id']+'.json')).read_bytes())
        assert t['status']=='completed' and t['exit_code']==0 and len(r['cases'])==r['required_accounts']
        assert r['actual_days']==730 and r['models_fit']==r['search_configurations']==0
        if first is None:first=r
        else:
            for key in ('symbols','data_manifest','locked_sha256','preparation_start','economics_start','economics_end_exclusive','cost','resources','expert_mixture'):
                assert first['protocol'][key]==r['protocol'][key]
        for name,h in r['binding']['source_hashes'].items():assert sha(ROOT/name)==h
        refs.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),task_id=t['id']));cases+=r['cases']
        for c in r['reused_controls']:
            if c['id'] in controls:assert c==controls[c['id']]
            controls[c['id']]=c
    assert len(cases)==len({c['id'] for c in cases})==6 and len(controls)==4
    ref=first['protocol']['comparison_reference'];assert sha(ROOT/ref['path'])==ref['sha256'];prior=json.loads((ROOT/ref['path']).read_bytes())
    reference=[v for v in prior['rows'] if v['strategy']=='SMA200_SIGNED' and v['mode'] in ('LONG_ONLY','LONG_SHORT')];assert len(reference)==4
    diag_ref=first['protocol']['expert_mixture'];assert sha(ROOT/diag_ref['path'])==diag_ref['sha256'];diag=json.loads((ROOT/diag_ref['path']).read_bytes())
    rows=[]
    for c in cases+list(controls.values()):
        s=c['summary'];assert s['completed_minutes']==s['required_minutes']==1051200 and s['terminal_cash_realized']
        assert c['independent']['maximum_NAV_error_USDT']<1e-7 and c['independent']['maximum_wallet_error_USDT']<1e-7
        assert c['independent']['target_reference']['maximum_error']<1e-10
        assert abs(s['net_PnL']-(s['gross_PnL_same_quantities']+s['funding_USDT']-s['fees_USDT']-s['execution_cost_USDT']))<1e-7
        future=c['strategy']=='ORACLE60D'
        if c in cases:
            m=c['artifacts']['target_meta.json'];assert sha(m['path'])==m['sha256'];meta=json.loads(Path(m['path']).read_bytes())
            assert meta['future_winner_used']==future and meta['causal_strategy']==(not future)
            assert meta['one_shared_full_capital_account'] and meta['shadow_cost_surcharge_not_applied_actual_fills_costed_once']
        years={}
        for d in c['independent']['daily_direction_contributions']:
            year=str(datetime.fromtimestamp((d['day_end_us']-1)//1_000_000,UTC).year);v=years.setdefault(year,dict(days=0,LONG=0.,SHORT=0.,net=0.));v['days']+=1
            v['LONG']+=d['LONG'];v['SHORT']+=d['SHORT'];v['net']+=d['LONG']+d['SHORT']
        assert sum(v['days'] for v in years.values())==730 and abs(sum(v['net'] for v in years.values())-s['net_PnL'])<1e-7
        rows.append(dict(id=c['id'],strategy=c['strategy'],mode=c['mode'],unit=c['unit'],capital_USDT=10000,
            future_winner_used=future,role='NONCAUSAL_INFORMED_ACCOUNT_NOT_CANDIDATE' if future else 'CAUSAL_FIXED_DEVELOPMENT_ACCOUNT',
            net_USDT=s['net_PnL'],gross_USDT=s['gross_PnL_same_quantities'],fees_USDT=s['fees_USDT'],execution_USDT=s['execution_cost_USDT'],funding_USDT=s['funding_USDT'],
            direction=s['long_short_marked_contribution'],calendar_year_contributions=years,turnover=s['normalized_total_turnover'],
            daily_metrics=s['daily_metrics'],drawdown_percent=s['minute_max_drawdown']*100,actual_exposure=s['realized_exposure'],concentration=s['daily_net_gain_concentration'],
            actual_short_open_legs=c['independent']['actual_short_open_legs'],terminal_paid_flat=True,
            risk_drift=dict(maximum_actual_gross_weight=s['maximum_actual_gross_weight'],maximum_actual_asset_weights=s['maximum_actual_asset_weights'],
                risk_reduction_signal_count=s['risk_reduction_signal_count'],maximum_observed_first_risk_reduction_latency_us=s['maximum_observed_first_risk_reduction_latency_us'],instantaneous_caps_guaranteed=s['actual_caps_instantaneously_guaranteed'])))
    decisions=[]
    for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
        oldls=next(v for v in reference if v['unit']==unit and v['mode']=='LONG_SHORT');oldlo=next(v for v in reference if v['unit']==unit and v['mode']=='LONG_ONLY')
        oracle=next(v for v in rows if v['unit']==unit and v['strategy']=='ORACLE60D')
        d=next(v for v in diag['results'] if v['unit']==unit);assert d['best_single']['expert']=='SMA200_SIGNED'
        assert abs(d['best_single']['terminal_wealth_USDT']-10000-oldls['net_USDT'])<1e-7
        statics=[]
        for family in ('EQUAL_EXPERTS','STATIC_DIRECTION3'):
            v=next(v for v in rows if v['unit']==unit and v['strategy']==family)
            checks=dict(net_ge_old_LO=v['net_USDT']>=oldlo['net_USDT'],Sharpe_ge_old_LO=v['daily_metrics']['sharpe']>=oldlo['daily_metrics']['sharpe'],DD_le_old_LO=v['drawdown_percent']<=oldlo['drawdown_percent'])
            statics.append(dict(strategy=family,checks=checks,pass_research_challenger=all(checks.values()),net_minus_old_LO=v['net_USDT']-oldlo['net_USDT']))
        decisions.append(dict(unit=unit,actual_oracle_minus_best_single_USDT=oracle['net_USDT']-oldls['net_USDT'],
            actual_oracle_opportunity_gate=oracle['net_USDT']-oldls['net_USDT']>=500,
            actual_minus_shadow_oracle_USDT=oracle['net_USDT']-d['oracle_variants']['TARGET_DISTANCE_SWITCH_COST_13_5BP']['net_shadow_USDT'],
            oracle_switches_preserved=d['oracle_variants']['TARGET_DISTANCE_SWITCH_COST_13_5BP']['switches'],static_checks=statics,
            oracle_actual_risk=dict(vol=oracle['daily_metrics']['annual_volatility'],DD=oracle['drawdown_percent']),
            best_single_actual_risk=dict(vol=oldls['daily_metrics']['annual_volatility'],DD=oldls['drawdown_percent'])))
    qualified=[family for family in ('EQUAL_EXPERTS','STATIC_DIRECTION3') if all(next(v for v in d['static_checks'] if v['strategy']==family)['pass_research_challenger'] for d in decisions)]
    out=dict(status='PASS_PAIRED_ACTUAL_SHARED_WALLET_MIXTURES_ORACLE_NONCAUSAL_NOT_INVESTMENT',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
        producers=refs,baseline_reference=ref,baseline_rows=reference,oracle_diagnostic_reference=diag_ref,rows=rows,decisions=decisions,
        qualified_static_research_challengers=qualified,oracle_opportunity_persists=all(v['actual_oracle_opportunity_gate'] for v in decisions),
        investment_candidate='NONE_CASH',models_fit=0,new_accounts_in_review=0,economic_accounts_referenced=6,reused_control_accounts=4,
        limits=['NONCAUSAL_ORACLE_CAN_NEVER_BE_CANDIDATE','NOT_GLOBAL_MAXIMUM_OF_ACTUAL_EXECUTION','FIXED_STATIC_WEIGHTS_NOT_ADAPTIVE_ALPHA','ONE_BTC_SEEN_DEVELOPMENT_CYCLE','FUNDING_UNIT_CONDITIONAL','BINANCE_PRICE_BYBIT_COST_PROXY','MMR_QUANTITY_RULES_ASSUMED','SAME_CAPS_NOT_RISK_MATCHED','LOCKED_NOT_USED','LONG_TERM_APR_NOT_EVALUABLE'],
        created_utc=datetime.now(UTC).isoformat())
    p=(ROOT/a.output).resolve();assert p.is_relative_to(ROOT/'reports')
    with p.open('x') as f:json.dump(out,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=out['status'],oracle_opportunity=out['oracle_opportunity_persists'],static_challengers=qualified,paired=decisions)))

if __name__=='__main__':main()
