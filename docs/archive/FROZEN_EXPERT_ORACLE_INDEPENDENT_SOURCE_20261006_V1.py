"""Independent scalar reconstruction of the saved shadow diagnostic, not DP."""
import json,os,math
from pathlib import Path
from datetime import UTC,datetime
import polars as pl
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
name='reports/FROZEN_EXPERT_ORACLE_OPPORTUNITY_20261006_V2.json';r=json.loads((ROOT/name).read_bytes())
cases={}
for producer in r['producers']:
    assert sha(ROOT/producer['path'])==producer['sha256']
    for c in json.loads((ROOT/producer['path']).read_bytes())['cases']:
        mode='CASH' if c['strategy']=='CASH' else 'LONG_ONLY' if c['strategy']=='HOLD' else 'LONG_SHORT'
        if c['mode']==mode:cases[c['strategy'],c['unit']]=c
max_error=0.;details=[]
for result in r['results']:
    source={};names=r['protocol']['experts']
    for expert in names:
        c=cases[expert,result['unit']];nav=pl.read_parquet(c['artifacts']['daily_nav.parquet']['path']).sort('day_end_us')
        targets=pl.read_parquet(c['artifacts']['targets.parquet']['path']).sort('available_us')['target_weight'].to_list()
        assert len(targets)==nav.height==730
        if expert=='CASH':assert nav['nav'].eq(10000).all() and sum(abs(v) for v in targets)==0
        assert c['summary']['contract']['nominal_roundtrip_bps']==27.
        source[expert]=dict(nav=[10000.]+nav['nav'].to_list(),targets=targets,rows=list(nav.iter_rows(named=True)),
            directions=c['independent']['daily_direction_contributions'])
    for label,v in result['oracle_variants'].items():
        rate=0. if label=='NO_EXTRA_SWITCH_SURCHARGE' else .00135
        wealth=10000.;long=short=cost=fee=execution=turnover=extra_notional=0.;previous=None;switches=0
        for segment in v['segments']:
            expert=segment['expert'];s=source[expert];b,e=segment['begin_day'],segment['end_day']
            assert b==segment['segment']*60 and e==min(730,b+60)
            if previous is not None and previous!=expert:
                distance=abs(s['targets'][b]-source[previous]['targets'][b-1])
                extra_notional+=wealth*distance
                paid=wealth*distance*rate;cost+=paid;wealth-=paid;switches+=1
            for day in range(b,e):
                before=s['nav'][day];after=s['nav'][day+1];d=s['directions'][day];row=s['rows'][day]
                long+=wealth*d['LONG']/before;short+=wealth*d['SHORT']/before
                fee+=wealth*row['fees']/before;execution+=wealth*row['execution_costs']/before
                turnover+=wealth*row['turnover']/before
                wealth*=after/before
            previous=expert
        expected={'terminal_shadow_wealth_USDT':wealth,'LONG':long,'SHORT':short,'extra_switch_cost_USDT':cost,
            'within_selected_expert_fees_shadow_USDT':fee,'within_selected_expert_execution_shadow_USDT':execution,
            'within_selected_expert_turnover_shadow_USDT':turnover,'extra_switch_notional_shadow_USDT':extra_notional}
        error=max(abs(v[k]-value) for k,value in expected.items());max_error=max(max_error,error)
        assert error<1e-7 and switches==v['switches']
        assert abs(wealth-10000-(long+short-cost))<1e-7
        assert abs(v['total_shadow_turnover_over_initial_capital']-(turnover+extra_notional)/10000)<1e-10
        assert sum(g['days'] for g in v['calendar_year_shadow_contributions'].values())==730
        assert sum(sum(g.values()) for g in v['winner_days_by_actual_calendar_year_and_past_state'].values())==730
        details.append(dict(unit=result['unit'],variant=label,maximum_scalar_error_USDT=error,switches=switches))
    best=max((source[n]['nav'][-1],n) for n in names)
    assert best[1]==result['best_single']['expert'] and abs(best[0]-result['best_single']['terminal_wealth_USDT'])<1e-7
    assert abs(result['cost_aware_oracle_minus_best_single_USDT']-(result['oracle_variants']['TARGET_DISTANCE_SWITCH_COST_13_5BP']['terminal_shadow_wealth_USDT']-best[0]))<1e-7
assert r['investment_status']=='NONE_CASH' and r['real_accounts_new']==0 and not r['locked_consumed']
out=dict(status='PASS_INDEPENDENT_SCALAR_ORACLE_SHADOW_WEALTH_COST_AND_ATTRIBUTION_NOT_EXECUTABLE',task_id=os.environ['COIN_TASK_ID'],
    source_sha256=sha(__file__),input=dict(path=name,sha256=sha(ROOT/name)),maximum_scalar_error_USDT=max_error,details=details,
    scope='Independent published-path scalar recurrence, all730days, one10kwealth, embedded fees not deducted twice, boundary switch cost, both units. Does not certify executable fills, future availability or global real-account upper bound.',
    new_accounts=0,models_fit=0,created_utc=datetime.now(UTC).isoformat())
with (ROOT/'reports/FROZEN_EXPERT_ORACLE_INDEPENDENT_20261006_V1.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(dict(status=out['status'],maximum_error=max_error)))
