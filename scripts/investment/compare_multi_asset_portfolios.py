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
TARGET_SOURCES=('scripts/investment/public_sma_perpetual.py',
                'scripts/investment/vol_managed_perpetual_target.py')
FINANCE_SOURCES=('src/quant/perpetual_account.py','scripts/investment/perpetual_directional.py',
    'scripts/investment/perpetual_closing_exempt_account.py','src/quant/resources.py',
    'src/quant/execution_contract.py','environments/v8/uv.lock')
EQUAL_ID='COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
INVERSE_ID='COIN_PAST30_INVERSE_VOL_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'


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


def asset_contributions_from_rows(case, trades, funding, initial_capital=10000):
    """Attribute saved realized and terminal marked PnL; never synthesize a close."""
    symbols=case['symbols']
    capital=Decimal(str(initial_capital))
    require(capital.is_finite() and capital>0, 'Positive full shared capital')
    summary=case['summary']
    sums={s:dict(realized=Decimal(0),fees=Decimal(0),execution=Decimal(0),
                 funding=Decimal(0),filled_notional=Decimal(0),fills=0) for s in symbols}
    for name, rows in (('trades.json',trades),('funding.json',funding)):
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
    totals={key:Decimal(0) for key in ('net','gross','unrealized','terminal_notional')}
    for s, one in sums.items():
        position=summary['positions'][s]
        quantity, entry=decimal(position,'quantity'),decimal(position,'entry_price')
        require(quantity.is_finite() and entry.is_finite(), 'Finite terminal quantity and entry')
        mark=Decimal(str(summary['terminal_mark_prices'][s])) if quantity else None
        require(not quantity or (mark.is_finite() and mark>0 and entry>0),
                'Held quantity requires a saved positive causal terminal mark and entry')
        unrealized=quantity*(mark-entry) if quantity else Decimal(0)
        signed_notional=quantity*mark if quantity else Decimal(0)
        gross=one['realized']+unrealized+one['execution']
        net=one['realized']+unrealized-one['fees']+one['funding']
        totals['net']+=net;totals['gross']+=gross;totals['unrealized']+=unrealized
        totals['terminal_notional']+=abs(signed_notional)
        output[s]=dict(gross_USDT=float(gross),fees_USDT=float(one['fees']),
            execution_USDT=float(one['execution']),funding_USDT=float(one['funding']),
            net_USDT=float(net),net_contribution_full_capital_percent=float(net/capital*100),
            realized_price_PnL_USDT=float(one['realized']),terminal_unrealized_PnL_USDT=float(unrealized),
            terminal_quantity=float(quantity),terminal_entry_price=float(entry),
            terminal_mark_price=float(mark) if mark is not None else None,
            terminal_signed_marked_notional_USDT=float(signed_notional),
            terminal_marked_notional_USDT=float(abs(signed_notional)),
            terminal_decimal_strings=dict(quantity=str(quantity),entry_price=str(entry),
                mark_price=str(mark) if mark is not None else None,unrealized_PnL=str(unrealized)),
            fill_notional_USDT=float(one['filled_notional']),fill_legs=one['fills'])
    require(abs(totals['net']-decimal(summary,'net_PnL'))<=Decimal('1e-7'),
            'Per-asset full account net bridge')
    require(abs(totals['gross']-decimal(summary,'gross_PnL_same_quantities'))<=Decimal('1e-7'),
            'Per-asset gross bridge')
    require(abs(totals['unrealized']-decimal(summary,'unrealized_PnL'))<=Decimal('1e-7'),
            'Per-asset terminal unrealized bridge')
    require(abs(totals['terminal_notional']-decimal(summary,'terminal_marked_notional'))<=Decimal('1e-7'),
            'Per-asset terminal notional bridge')
    require(summary['terminal_cash_realized']==all(decimal(summary['positions'][s],'quantity')==0 for s in symbols),
            'Terminal cash identity agrees with every configured quantity')
    return output


def asset_contributions(case):
    rows={name:read(case['artifacts'][name]['path'],case['artifacts'][name]['sha256'])
          for name in ('trades.json','funding.json')}
    return asset_contributions_from_rows(case,rows['trades.json'],rows['funding.json'])


def measures(case):
    s=case['summary']
    return dict(net_USDT=s['net_PnL'],gross_USDT=s['gross_PnL_same_quantities'],
        return_full_capital_percent=s['net_return_on_full_initial_capital_percent'],
        fees_USDT=s['fees_USDT'],execution_USDT=s['execution_cost_USDT'],funding_USDT=s['funding_USDT'],
        turnover_full_capital=s['normalized_total_turnover'],
        actual_daily_annualized_volatility=s['daily_metrics']['annual_volatility'],
        minute_MDD=s['minute_max_drawdown'],**s['realized_exposure'],
        asset_contributions=asset_contributions(case),
        terminal_cash_realized=s['terminal_cash_realized'],
        terminal_marked_notional_USDT=s['terminal_marked_notional'],
        terminal_unrealized_PnL_USDT=s['unrealized_PnL'],
        terminal_quantities={a:str(decimal(s['positions'][a],'quantity')) for a in case['symbols']},
        liquidated_return_full_capital_percent=(s['net_return_on_full_initial_capital_percent']
            if s['terminal_cash_realized'] else None),
        liquidated_return=('EVALUABLE_SAVED_CLOSED_ACCOUNT' if s['terminal_cash_realized'] else 'NOT_EVALUABLE'),
        return_scope=('SAVED_CLOSED_ACCOUNT_NET' if s['terminal_cash_realized']
            else 'SAVED_MARKED_NAV_WITH_UNLIQUIDATED_INVENTORY_NOT_CASH_RETURN'),
        daily_gain_concentration=s['daily_net_gain_concentration'])


def saved_protocol(report):
    command=report['binding']['command']
    require(command.count('--protocol')==1, 'One recorded portfolio protocol')
    path=Path(command[command.index('--protocol')+1]).resolve()
    require(path.is_relative_to(ROOT/'protocols') and path.stat().st_size<=2_000_000 and
        sha(path)==report['binding']['protocol_sha256'], 'Exact saved protocol metadata')
    return json.loads(path.read_bytes()),dict(path=str(path),sha256=sha(path))


def saved_pool_proof(protocol):
    aliases=[k for k in ('selection_proof','pool_receipt') if k in protocol]
    require(len(aliases)==1, 'One explicit saved pool receipt alias')
    proof=protocol[aliases[0]];path=Path(proof['path']).resolve()
    require(path.is_relative_to(ROOT/'reports') and path.stat().st_size<=2_000_000 and
        sha(path)==proof['sha256'], 'Exact pre-score frozen pool receipt')
    return dict(protocol_field=aliases[0],path=str(path),sha256=proof['sha256'])


def allocation_scope(left,right):
    """Check the single allocation contrast before opening saved trade ledgers."""
    a,ap=saved_protocol(left);b,bp=saved_protocol(right)
    require(a['strategy']==EQUAL_ID and a.get('allocation','EQUAL')=='EQUAL' and
        b['strategy']==INVERSE_ID and b['allocation']=='INVERSE_VOL_30D', 'Predeclared equal versus inverse-volatility strategies')
    windows=[]
    for p in (a,b):
        stamps=[datetime.fromisoformat(p[k]) for k in ('start','end_exclusive')]
        require(all(t.tzinfo is not None and t.utcoffset().total_seconds()==0 for t in stamps), 'Explicit UTC period')
        windows.append(tuple(int(t.timestamp()*1_000_000) for t in stamps))
    require(windows[0]==windows[1] and windows[0][1]-windows[0][0]==left['actual_calendar_days']*86_400_000_000, 'Same complete saved scoring period')
    pool_proofs=[saved_pool_proof(p) for p in (a,b)]
    require(a['initial_capital_USDT']==b['initial_capital_USDT']==10000 and
        a['pools']==b['pools'] and pool_proofs[0]['path']==pool_proofs[1]['path'] and
        pool_proofs[0]['sha256']==pool_proofs[1]['sha256'], 'Same ordered frozen pool and full capital')
    require(a['data_manifest']['sha256']==b['data_manifest']['sha256']==left['binding']['manifest_sha256']==right['binding']['manifest_sha256'] and
        Path(a['data_manifest']['path']).resolve()==Path(b['data_manifest']['path']).resolve(), 'Identical accepted price and funding input identity')
    hashes=[p['binding']['source_hashes'] for p in (left,right)]
    require(all(p['source_hashes']==h for p,h in zip((a,b),hashes,strict=True)), 'Actual sources match their saved protocols')
    for key in FINANCE_SOURCES:
        require(hashes[0][key]==hashes[1][key], 'Unchanged account, engine, resource or environment '+key)
    require(left['binding']['environment_lock_sha256']==right['binding']['environment_lock_sha256']==
        hashes[0]['environments/v8/uv.lock'], 'Identical accepted runtime lock')
    changes={k:dict(baseline=h,current=hashes[1][k]) for k,h in hashes[0].items()
             if k in hashes[1] and h!=hashes[1][k]}
    # The saved September account predates the accepted explicit-month reader
    # and CLI metadata change. Their history is disclosed, while exact inputs
    # and the financial engine above remain equal. No other shared source varies.
    compatibility={'scripts/investment/multi_asset_data.py', 'scripts/investment/multi_asset_portfolio.py'}
    require(set(changes)<=set(TARGET_SOURCES)|compatibility, 'Unrelated common source changed in allocation contrast')
    require(all(k in hashes[0] and k in hashes[1] for k in TARGET_SOURCES), 'Both target source identities retained')
    return dict(baseline_protocol=ap,current_protocol=bp,start_us=windows[0][0],end_us=windows[0][1],
        frozen_pool_receipt=pool_proofs[0],current_pool_receipt=pool_proofs[1],predeclared_pools=a['pools'],
        source_changes=changes,allowed_allocation_source_paths=list(TARGET_SOURCES),
        reader_and_cli_compatibility_source_changes={k:v for k,v in changes.items() if k in compatibility},
        unchanged_finance_source_hashes={k:hashes[0][k] for k in FINANCE_SOURCES},
        identical_data_manifest_sha256=a['data_manifest']['sha256'],
        baseline_strategy_id=EQUAL_ID,current_strategy_id=INVERSE_ID,
        baseline_allocation='EQUAL',current_allocation='INVERSE_VOL_30D',
        allocation_changed=True,directional_signal_changed=False,original_SMA_alpha_used=False)


def allocation_case(left,right,scope,days):
    require(left['symbols']==right['symbols'] and left['pool']==right['pool'] and
        left['summary']['contract']==right['summary']['contract'] and
        left['summary']['cost_scenario']==right['summary']['cost_scenario'] and
        left['summary']['unit_scenario']==right['summary']['unit_scenario'] and
        left['summary']['mode']==right['summary']['mode']=='LONG_ONLY' and
        any(p['id']==left['pool'] and p['symbols']==left['symbols'] for p in scope['predeclared_pools']), 'Same ordered assets, risk contract, costs, units and direction')
    metadata=[];proofs=[]
    common_rules=dict(timeframe_minutes=1440,completed_daily_eligibility_bars=200,
        past_covariance_daily_returns=30,annual_volatility_target=.10,
        absolute_target_per_asset=.3,gross_target_cap=.6,direction_is_constant=True,
        SMA_alpha_or_original_Jesse_hooks_used=False)
    for case,identity,allocation in ((left,EQUAL_ID,'EQUAL'),(right,INVERSE_ID,'INVERSE_VOL_30D')):
        artifact=case['artifacts']['target_meta.json'];path=Path(artifact['path'])
        require(path.stat().st_size==artifact['bytes']<=2_000_000, 'Small saved target metadata')
        meta=read(path,artifact['sha256']);rules=meta['rules'];risk=meta['risk']
        require(meta['strategy_id']==identity and meta.get('allocation','EQUAL')==allocation and
            meta['symbols']==case['symbols'] and meta['mode']=='LONG_ONLY' and
            all(rules.get(k)==v for k,v in common_rules.items()), 'Actual target identity and common past-risk rules')
        require(meta['original_SMA_alpha_used'] is False and meta['funding_rates_used_for_signal'] is False and
            meta['fresh_flat_each_window'] is True and meta['native_Jesse_or_Bybit_execution_replicated'] is False,
            'Constant-long causal research metadata, not a new directional signal')
        require([r['decision_us'] for r in risk]==list(range(scope['start_us'],scope['end_us'],86_400_000_000)) and
            len(risk)==days and all(r['symbol_order']==case['symbols'] and r['past_only'] is True for r in risk), 'Same complete daily causal decision clock')
        metadata.append(meta);proofs.append(dict(path=str(path),sha256=artifact['sha256'],bytes=artifact['bytes'],
            strategy_id=identity,allocation=allocation,rules=rules))
    require(metadata[0]['rules']['raw_allocation']=='EQUAL_SHARE_OF_0.6_GROSS_TO_CONFIGURED_ELIGIBLE_MEMBERS' and
        metadata[1]['rules']['raw_allocation']=='0.6_TIMES_NORMALIZED_INVERSE_PAST30_SAMPLE_DAILY_VOLATILITY_THEN_ASSET_CLIP_0.3' and
        metadata[1]['rules']['allocation_sample_std_ddof']==1 and
        metadata[1]['rules']['clipped_budget_redistributed'] is False, 'One fixed raw-allocation factor')
    require([r['covariance_symbol_order'] for r in metadata[0]['risk']]==
        [r['covariance_symbol_order'] for r in metadata[1]['risk']], 'Same eligible covariance input members')
    return dict(baseline=proofs[0],current=proofs[1],directional_signal_changed=False,
        allocation_changed=True,realized_risk_matched=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control',type=Path,required=True)
    parser.add_argument('--pool',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--experiment-id',required=True)
    parser.add_argument('--contrast',choices=('pool','allocation'),default='pool')
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
    contrast_scope=allocation_scope(left,right) if args.contrast=='allocation' else None
    if args.contrast=='pool':
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
        target_contrast=allocation_case(a[key],b[key],contrast_scope,actual_days) if contrast_scope else None
        x,y=measures(a[key]),measures(b[key])
        pairs.append(dict(cost=key[0],funding_unit_scenario=key[1],control=x,pool=y,
            pool_minus_control_net_USDT=y['net_USDT']-x['net_USDT'],
            pool_minus_control_gross_USDT=y['gross_USDT']-x['gross_USDT'],
            pool_minus_control_cost_USDT=(y['fees_USDT']+y['execution_USDT'])-(x['fees_USDT']+x['execution_USDT']),
            pool_minus_control_funding_USDT=y['funding_USDT']-x['funding_USDT'],
            actual_risk_matched=False,**(dict(target_contrast=target_contrast) if target_contrast else {})))
    result=dict(status='COMPLETE_SAVED_MULTI_ASSET_PAIRED_COMPARISON_NOT_APR',
        task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
        control=dict(path=str(args.control),sha256=sha(args.control)),
        pool=dict(path=str(args.pool),sha256=sha(args.pool)),pairs=pairs,
        CASH=dict(net_USDT=0,return_full_capital_percent=0,turnover=0,fees=0,MDD=0),
        actual_days=actual_days,initial_capital_USDT=10000,models_fit=0,orders_sent=0,
        locked_consumed=False,investment='CASH',candidate='NONE',long_term_APR='NOT_EVALUABLE',
        scope='Same fixed past-risk HOLD rule; liquidity pool changes weights/covariance and realized risk. '
              'Saved marked-NAV pairing retains all terminal inventory; unclosed liquidated return is NOT_EVALUABLE. '
              'No free liquidation, independent-account aggregation, post-hoc risk scaling or native Bybit claim.',
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        created_utc=datetime.now(UTC).isoformat())
    if contrast_scope:
        result.update(contrast='allocation',allocation_contrast=contrast_scope,
            scope='Same ordered fixed pool, full capital, accepted inputs, direction, costs and financial risk rules; '
                  'equal versus predeclared past30 inverse-volatility allocation. Actual exposures and realized risk may differ. '
                  'Saved marked-NAV pairing retains terminal inventory; unclosed liquidated return is NOT_EVALUABLE. '
                  'No new directional alpha, free liquidation, post-hoc risk rescaling, account replay or native Bybit claim.')
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False,allow_nan=False)
        stream.write('\n')
    event=dict.fromkeys(FIELDS)
    event.update(event_id=args.experiment_id+':RESULT',event_type='SAVED_RESEARCH_COMPARISON',
        experiment_id=args.experiment_id,data_manifest_hash=result['control']['sha256'],
        success_failure=result['status'],reason_for_next_experiment=(
            'Saved single-factor allocation contribution and unequal actual risk' if contrast_scope else 'Economic pool contribution and actual risk'),
        artifact_path=str(args.output.resolve().relative_to(ROOT)),artifact_sha256=sha(args.output))
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    print(json.dumps(dict(status=result['status'],pairs=len(pairs),output=str(args.output))))


if __name__=='__main__':
    main()
