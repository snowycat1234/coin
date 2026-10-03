"""Compare saved shared-capital portfolios, without replay or strategy selection."""
from __future__ import annotations
import argparse
from datetime import UTC, datetime
from decimal import Decimal, getcontext
import hashlib
import json
import os
from pathlib import Path
import resource
from quant.paths import ROOT, STATE
from scripts.research_v8.registry import FIELDS, append_event
getcontext().prec=40


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path, digest=None):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT/'reports') or path.is_relative_to(STATE), 'Local result only')
    require(digest is None or sha(path)==digest, 'Saved result changed')
    return json.loads(path.read_bytes())


def decimal(row, key):
    return Decimal(row.get('decimal_strings', {}).get(key, str(row[key])))


def asset_contributions(case):
    """Closed accounts: actual realized PnL+execution costs is gross price PnL."""
    symbols=case['symbols']
    sums={s:dict(realized=Decimal(0),fees=Decimal(0),execution=Decimal(0),
                 funding=Decimal(0),filled_notional=Decimal(0),fills=0) for s in symbols}
    for name in ('trades.json','funding.json'):
        artifact=case['artifacts'][name]
        rows=read(artifact['path'],artifact['sha256'])
        for row in rows:
            require(row['symbol'] in sums, 'Asset outside portfolio')
            one=sums[row['symbol']]
            if name=='trades.json':
                one['realized']+=decimal(row,'realized_PnL')
                one['fees']+=decimal(row,'fee_USDT_mid')
                one['execution']+=decimal(row,'execution_cost')
                one['filled_notional']+=decimal(row,'quantity')*decimal(row,'fill_price')
                one['fills']+=1
            else:
                one['funding']+=decimal(row,'signed_funding_USDT')
    output={}
    for s, one in sums.items():
        gross=one['realized']+one['execution']
        net=one['realized']-one['fees']+one['funding']
        output[s]=dict(gross_USDT=float(gross),fees_USDT=float(one['fees']),
            execution_USDT=float(one['execution']),funding_USDT=float(one['funding']),
            net_USDT=float(net),net_contribution_full_capital_percent=float(net/100),
            fill_notional_USDT=float(one['filled_notional']),fill_legs=one['fills'])
    require(abs(sum(v['net_USDT'] for v in output.values())-case['summary']['net_PnL'])<=1e-7,
            'Per-asset full account net bridge')
    require(abs(sum(v['gross_USDT'] for v in output.values())-case['summary']['gross_PnL_same_quantities'])<=1e-7,
            'Per-asset gross bridge')
    return output


def measures(case):
    s=case['summary']
    require(s['terminal_cash_realized'] and all(s['positions'][a]['quantity']==0 for a in case['symbols']),
            'Only actual fully closed portfolios; no dropped terminal inventory')
    return dict(net_USDT=s['net_PnL'],gross_USDT=s['gross_PnL_same_quantities'],
        return_full_capital_percent=s['net_return_on_full_initial_capital_percent'],
        fees_USDT=s['fees_USDT'],execution_USDT=s['execution_cost_USDT'],funding_USDT=s['funding_USDT'],
        turnover_full_capital=s['normalized_total_turnover'],
        actual_daily_annualized_volatility=s['daily_metrics']['annual_volatility'],
        minute_MDD=s['minute_max_drawdown'],**s['realized_exposure'],
        asset_contributions=asset_contributions(case),
        daily_gain_concentration=s['daily_net_gain_concentration'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control',type=Path,required=True)
    parser.add_argument('--pool',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--experiment-id',required=True)
    args=parser.parse_args()
    require(os.environ.get('COIN_TASK_ID') and not args.output.exists()
        and args.output.resolve().is_relative_to(ROOT/'reports'), 'Bounded new comparison')
    left,right=read(args.control),read(args.pool)
    require(all(p['complete_calendar_cases']==p['completed_cases']==4 and
        p['initial_capital_per_comparison_account_USDT']==10000 and
        p['candidate']=='NONE' and not p['orders_sent'] and not p['locked_consumed']
        for p in (left,right)), 'Four complete scenarios per shared 10k portfolio')
    actual_days=left['actual_calendar_days']
    require(isinstance(actual_days,int) and 28 <= actual_days <= 31 and
            actual_days==right['actual_calendar_days'], 'Same complete predeclared calendar month')
    for name in ('public_sma_perpetual.py','vol_managed_perpetual_target.py',
                 'perpetual_directional.py','perpetual_closing_exempt_account.py'):
        key='scripts/investment/'+name
        require(left['binding']['source_hashes'][key]==right['binding']['source_hashes'][key],
                'Pool contribution requires unchanged strategy and finance')
    require(left['binding']['source_hashes']['src/quant/perpetual_account.py']==
            right['binding']['source_hashes']['src/quant/perpetual_account.py'], 'Same normal account')
    indexed=lambda p:{(c['cost_id'],c['unit_id']):c for c in p['cases']}
    a,b=indexed(left),indexed(right)
    require(len(a)==len(b)==4 and set(a)==set(b), 'All costs and unknown-unit scenarios retained')
    pairs=[]
    for key in a:
        require(a[key]['summary']['clock_us']==b[key]['summary']['clock_us'], 'Same complete end clock')
        x,y=measures(a[key]),measures(b[key])
        pairs.append(dict(cost=key[0],funding_unit_scenario=key[1],control=x,pool=y,
            pool_minus_control_net_USDT=y['net_USDT']-x['net_USDT'],
            pool_minus_control_gross_USDT=y['gross_USDT']-x['gross_USDT'],
            pool_minus_control_cost_USDT=(y['fees_USDT']+y['execution_USDT'])-(x['fees_USDT']+x['execution_USDT']),
            pool_minus_control_funding_USDT=y['funding_USDT']-x['funding_USDT'],
            actual_risk_matched=False))
    result=dict(status='COMPLETE_SAVED_MULTI_ASSET_PAIRED_COMPARISON_NOT_APR',
        task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
        control=dict(path=str(args.control),sha256=sha(args.control)),
        pool=dict(path=str(args.pool),sha256=sha(args.pool)),pairs=pairs,
        CASH=dict(net_USDT=0,return_full_capital_percent=0,turnover=0,fees=0,MDD=0),
        actual_days=actual_days,initial_capital_USDT=10000,models_fit=0,orders_sent=0,
        locked_consumed=False,investment='CASH',candidate='NONE',long_term_APR='NOT_EVALUABLE',
        scope='Same fixed past-risk HOLD rule; liquidity pool changes weights/covariance and realized risk. '
              'No independent-account aggregation, no post-hoc risk scaling, no native Bybit claim.',
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        created_utc=datetime.now(UTC).isoformat())
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False,allow_nan=False)
        stream.write('\n')
    event=dict.fromkeys(FIELDS)
    event.update(event_id=args.experiment_id+':RESULT',event_type='SAVED_RESEARCH_COMPARISON',
        experiment_id=args.experiment_id,data_manifest_hash=result['control']['sha256'],
        success_failure=result['status'],reason_for_next_experiment='Economic pool contribution and actual risk',
        artifact_path=str(args.output.resolve().relative_to(ROOT)),artifact_sha256=sha(args.output))
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    print(json.dumps(dict(status=result['status'],pairs=len(pairs),output=str(args.output))))


if __name__=='__main__':
    main()
