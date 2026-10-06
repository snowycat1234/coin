"""Future-informed, cost-aware opportunity diagnostic; never a trading policy.

Saved expert returns are proportionally rebased onto one diagnostic wealth.
This is not a stitched account or an executable portfolio. Boundary cost is
an explicit target-distance surcharge, not a native fill simulation.
"""
import argparse,json,os,time,resource
from datetime import UTC,datetime
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment.reuse_cycle_controls import sha
from scripts.task_progress_api import Progress

DAY=86_400_000_000
CORE=('scripts/investment/perpetual_directional.py','scripts/investment/perpetual_closing_exempt_account.py',
      'scripts/investment/public_sma_perpetual.py','scripts/investment/bybit_cost_inputs.py',
      'scripts/investment/audit_shared_direction.py','src/quant/perpetual_account.py','scripts/investment/cta_cycle_window.py')

def optimal_path(growth,start_targets,end_targets,side_rate):
    """Exact DP for this stated shadow-wealth objective, not real execution."""
    g=np.asarray(growth,float);start=np.asarray(start_targets,float);end=np.asarray(end_targets,float)
    assert g.ndim==2 and start.ndim==3 and start.shape[:2]==g.shape and end.shape==start.shape and np.isfinite(g).all() and (g>0).all()
    assert np.isfinite(start).all() and np.isfinite(end).all() and 0<=side_rate<=.01
    score=g[0].copy();parents=[]
    for k in range(1,len(g)):
        distance=np.abs(end[k-1,:,None,:]-start[k,None,:,:]).sum(axis=-1)
        np.fill_diagonal(distance,0.)
        factors=1-distance*side_rate;assert (factors>0).all()
        transitions=score[:,None]*factors*g[k][None,:]
        previous=np.argmax(transitions,axis=0);parents.append(previous)
        score=transitions[previous,np.arange(g.shape[1])]
    j=int(np.argmax(score));value=float(score[j]);path=[j]
    for previous in parents[::-1]:j=int(previous[j]);path.append(j)
    return path[::-1],value

def shadow_replay(path,daily_returns,direction_returns,start_targets,end_targets,bounds,side_rate,cost_returns=None):
    wealth=10000.;long=short=extra=turnover=extra_notional=0.;segments=[];daily=[];switches=0
    within=np.zeros(3)
    for k,(begin,end) in enumerate(bounds):
        choice=path[k];cost=volume=0.
        if k and choice!=path[k-1]:
            switches+=1
            volume=float(np.abs(start_targets[k,choice]-end_targets[k-1,path[k-1]]).sum())
            extra_notional+=wealth*volume
            cost=wealth*volume*side_rate;wealth-=cost;extra+=cost;turnover+=volume
        before=wealth;part_long=part_short=0.
        for day in range(begin,end):
            dl=wealth*direction_returns[choice,day,0];ds=wealth*direction_returns[choice,day,1]
            part_long+=dl;part_short+=ds
            if cost_returns is not None:within+=wealth*cost_returns[choice,day]
            wealth*=1+daily_returns[choice,day]
            daily.append(dict(day=day,expert_index=choice,LONG=dl,SHORT=ds,
                extra_switch_cost_USDT=cost if day==begin else 0.,ending_shadow_wealth_USDT=wealth))
        long+=part_long;short+=part_short
        segments.append(dict(segment=k,begin_day=begin,end_day=end,expert_index=choice,
            LONG=part_long,SHORT=part_short,boundary_turnover_NAV_fraction=volume,boundary_extra_cost_USDT=cost,
            segment_after_surcharge_net_USDT=wealth-before,ending_shadow_wealth_USDT=wealth))
    assert abs(wealth-10000-(long+short-extra))<1e-7
    return dict(terminal_shadow_wealth_USDT=wealth,net_shadow_USDT=wealth-10000,LONG=long,SHORT=short,
        extra_switch_cost_USDT=extra,extra_switch_turnover_NAV_fraction=turnover,
        extra_switch_notional_shadow_USDT=extra_notional,
        within_selected_expert_fees_shadow_USDT=float(within[0]),within_selected_expert_execution_shadow_USDT=float(within[1]),
        within_selected_expert_turnover_shadow_USDT=float(within[2]),
        total_shadow_turnover_over_initial_capital=float((within[2]+extra_notional)/10000),
        switches=switches,segments=segments,daily=daily)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',required=True);ap.add_argument('--producer',action='append',required=True)
    ap.add_argument('--output',required=True);a=ap.parse_args();began=time.monotonic()
    spec=json.loads((ROOT/a.protocol).read_bytes());assert os.environ.get('COIN_TASK_ID') and spec['decision_horizons_days']==[60]
    assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
    names=spec['experts'];cases={};producers=[];identity=None;states=None;phase=Progress()
    for name in a.producer:
        phase.update('绑定冻结expert实际完整账户',len(producers),len(a.producer),'工件')
        p=ROOT/name;r=json.loads(p.read_bytes());t=json.loads((STATE/'task-progress'/('task-'+r['binding']['task_id']+'.json')).read_bytes())
        assert t['status']=='completed' and t['exit_code']==0 and len(r['cases'])==r['required_accounts']
        assert r['models_fit']==r['search_configurations']==0 and r['actual_days']==730
        assert r['protocol']['symbols']==['BTCUSDT'] and r['protocol']['cost_ids']==['BASE27']
        key={k:r['protocol'][k] for k in ('symbols','data_manifest','locked_sha256','preparation_start','economics_start','economics_end_exclusive','cost','resources')}
        if identity is None:identity=key;states=r['descriptive_past_states']
        else:assert identity==key
        for path in CORE:assert r['binding']['source_hashes'][path]==sha(ROOT/path),'Common financial/data core '+path
        for c in r['cases']:
            family=c['strategy'];mode=c['mode']
            if family not in names or mode!=('CASH' if family=='CASH' else 'LONG_ONLY' if family=='HOLD' else 'LONG_SHORT'):continue
            s=c['summary'];assert s['completed_minutes']==s['required_minutes']==1051200 and s['terminal_cash_realized']
            assert c['independent']['maximum_NAV_error_USDT']<1e-7 and c['independent']['maximum_wallet_error_USDT']<1e-7
            assert c['independent']['target_reference']['maximum_error']<1e-10
            assert abs(s['net_PnL']-(s['gross_PnL_same_quantities']+s['funding_USDT']-s['fees_USDT']-s['execution_cost_USDT']))<1e-7
            pair=(family,c['unit']);assert pair not in cases;cases[pair]=c
        producers.append(dict(path=name,sha256=sha(p),task_id=r['binding']['task_id']))
    assert len(cases)==2*len(names) and all((n,u) in cases for n in names for u in ('RAW_AS_FRACTION','RAW_AS_PERCENT'))
    bounds=[(b,min(730,b+60)) for b in range(0,730,60)];results=[];library=[]
    for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
        returns=[];directions=[];cost_returns=[];start_targets=[];end_targets=[];timestamps=None
        for name in names:
            c=cases[name,unit];art=c['artifacts'];loaded={}
            for key in ('daily_nav.parquet','targets.parquet'):
                v=art[key];p=Path(v['path']);assert p.is_relative_to(STATE) and sha(p)==v['sha256'] and p.stat().st_size==v['bytes']
                loaded[key]=pl.read_parquet(p)
            nav=loaded['daily_nav.parquet'].sort('day_end_us');target=loaded['targets.parquet'].sort(['available_us','symbol'])
            assert nav.height==target.height==730
            times=nav['day_end_us'].to_numpy();assert np.all(np.diff(times)==DAY)
            assert np.array_equal(target['available_us'].to_numpy()+DAY,times)
            if timestamps is None:timestamps=times
            else:assert np.array_equal(timestamps,times)
            values=np.r_[10000.,nav['nav'].to_numpy()];assert (values>0).all() and abs(values[-1]-c['summary']['NAV'])<1e-7
            daily=np.diff(values)/values[:-1];returns.append(daily)
            components=nav.select('fees','execution_costs','turnover').to_numpy()
            assert np.isfinite(components).all() and components.min()>=-1e-10
            cost_returns.append(components/values[:-1,None])
            d=c['independent']['daily_direction_contributions'];assert [v['day_end_us'] for v in d]==times.tolist()
            by_direction=np.array([[v['LONG'],v['SHORT']] for v in d])/values[:-1,None]
            assert np.max(np.abs(by_direction.sum(axis=1)-daily))<1e-10;directions.append(by_direction)
            weights=target['target_weight'].to_numpy()[:,None]
            start_targets.append(np.array([weights[b] for b,e in bounds]));end_targets.append(np.array([weights[e-1] for b,e in bounds]))
            library.append(dict(expert=name,unit=unit,original_case_id=c['id'],capital_USDT=10000,
                original_net_USDT=c['summary']['net_PnL'],actual_short_open_legs=c['independent']['actual_short_open_legs'],
                artifacts={k:art[k] for k in loaded},source_identity=c['summary']['contract']['cost_provenance']))
        returns=np.array(returns);directions=np.array(directions);cost_returns=np.array(cost_returns)
        starts=np.array(start_targets).transpose(1,0,2);ends=np.array(end_targets).transpose(1,0,2)
        growth=np.array([[np.prod(1+row[b:e]) for row in returns] for b,e in bounds])
        # DP transition uses the previous segment's ending target and incoming
        # segment's starting target; costs inside experts remain in returns.
        variants={}
        for label,rate in [('NO_EXTRA_SWITCH_SURCHARGE',0.),('TARGET_DISTANCE_SWITCH_COST_13_5BP',.00135)]:
            path,value=optimal_path(growth,starts,ends,rate);replayed=shadow_replay(path,returns,directions,starts,ends,bounds,rate,cost_returns)
            assert abs(replayed['terminal_shadow_wealth_USDT']-10000*value)<1e-7
            winners={}
            for v in replayed['segments']:
                t=int(timestamps[v['begin_day']]-DAY);v.update(expert=names[v.pop('expert_index')],decision_us=t,
                    start_UTC=datetime.fromtimestamp(t//1_000_000,UTC).date().isoformat(),past_state=states[str(t)])
                group=v['start_UTC'][:4]+'/'+v['past_state'];w=winners.setdefault(group,{})
                w[v['expert']]=w.get(v['expert'],0)+v['end_day']-v['begin_day']
            actual_years={};daily_winners={}
            for v in replayed['daily']:
                t=int(timestamps[v['day']]-DAY);year=str(datetime.fromtimestamp(t//1_000_000,UTC).year)
                v.update(expert=names[v.pop('expert_index')],day_start_us=t,past_state=states[str(t)])
                g=daily_winners.setdefault(year+'/'+v['past_state'],{})
                g[v['expert']]=g.get(v['expert'],0)+1
                y=actual_years.setdefault(year,dict(days=0,LONG=0.,SHORT=0.,extra_switch_cost_USDT=0.,net_shadow_USDT=0.))
                y['days']+=1
                for key in ('LONG','SHORT','extra_switch_cost_USDT'):y[key]+=v[key]
                y['net_shadow_USDT']+=v['LONG']+v['SHORT']-v['extra_switch_cost_USDT']
            assert sum(v['days'] for v in actual_years.values())==730 and abs(sum(v['net_shadow_USDT'] for v in actual_years.values())-replayed['net_shadow_USDT'])<1e-7
            replayed.update(winner_days_by_start_year_and_past_state=winners,
                winner_days_by_actual_calendar_year_and_past_state=daily_winners,
                calendar_year_shadow_contributions=actual_years)
            variants[label]=replayed
        single=[dict(expert=n,terminal_wealth_USDT=10000*float(np.prod(1+returns[i]))) for i,n in enumerate(names)]
        best=max(single,key=lambda v:v['terminal_wealth_USDT']);costaware=variants['TARGET_DISTANCE_SWITCH_COST_13_5BP']
        increment=costaware['terminal_shadow_wealth_USDT']-best['terminal_wealth_USDT']
        results.append(dict(unit=unit,best_single=best,single_experts=single,oracle_variants=variants,
            cost_aware_oracle_minus_best_single_USDT=increment,pass_opportunity_gate=increment>=500 and costaware['LONG']>0 and costaware['SHORT']>0))
    assert time.monotonic()-began<spec['resource_budget']['wall_seconds']
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<spec['resource_budget']['RSS_bytes']
    out=dict(status='COMPLETE_FROZEN_EXPERT_OPPORTUNITY_DIAGNOSTIC_NOT_EXECUTABLE_OR_INVESTMENT',task_id=os.environ['COIN_TASK_ID'],
        source_sha256=sha(__file__),protocol_sha256=sha(ROOT/a.protocol),protocol=spec,producers=producers,library=library,results=results,
        decision='ADVANCE_PREDICTABILITY_SCREEN_ONLY_NEEDS_ACTUAL_SHARED_WALLET_REPLAY' if all(v['pass_opportunity_gate'] for v in results) else 'PAUSE_SELECTOR_CEILING_INSUFFICIENT_RETAIN_SINGLE_REFERENCE',
        limitations=['REBASED_SAVED_RETURNS_NOT_SHARED_ACCOUNT_REPLAY','TARGET_BOUNDARY_COST_APPROXIMATION_AND_EMBEDDED_COSTS_RETAINED','PER_EXPERT_REJECTION_MIN_NOTIONAL_AND_CAPITAL_PATH_NOT_REPLICATED','FUTURE_WINNER_NONCAUSAL_BY_DESIGN','ONE_BTC_DEVELOPMENT_CYCLE','FUNDING_UNITS_CONDITIONAL','NOT_NATIVE_BYBIT','STATIC_ENSEMBLE_AND_PLACEBOS_NOT_RUN','LONG_TERM_APR_NOT_EVALUABLE'],
        real_accounts_new=0,models_fit=0,locked_consumed=False,investment_status='NONE_CASH',elapsed_seconds=time.monotonic()-began,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,created_utc=datetime.now(UTC).isoformat())
    p=(ROOT/a.output).resolve();assert p.is_relative_to(ROOT/'reports')
    with p.open('x') as f:json.dump(out,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
    phase.update('机会诊断完成：不是可交易收益',len(cases),len(cases),'expert情景');phase.stop.set();phase.thread.join(timeout=3)
    print(json.dumps(dict(status=out['status'],decision=out['decision'],increments=[v['cost_aware_oracle_minus_best_single_USDT'] for v in results])))

if __name__=='__main__':main()
