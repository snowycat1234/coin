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
SMA_SIGNAL_ID='COIN_JESSE_SMA50_200_1D_USDM_CONFIGURED_POOL_ADAPTER'
SIGNAL_SOURCE_PINS={
    'scripts/investment/public_sma_pool_target.py':'0d8eca6fe244630e77bbd0bd8592bbcbd70c10463f4a211588f6ee3c8595b485',
    'scripts/investment/public_sma_perpetual.py':'37e126709d479fd4f99487e3a8a66deda8889286154e2f6ed04d180a2987ca47',
    'scripts/investment/public_sma_daily.py':'a675428941dbae1fe07dbab5f6edd33597475bda5df4c2b1bf9f0a0c74048be3',
    'scripts/investment/vol_managed_perpetual_target.py':'a1f73af45253f42b557d902da79eea94148c4e487be178891279558d3d9bb54b',
    'third_party/jesse_example_smacrossover/smacrossover_original.py':'453440d7b934c494934a1c56b3826d94638594f79ad4e4c7faaff36b96d33fae',
    'third_party/jesse_example_smacrossover/LICENSE':'80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d'}
LEGACY_EQUAL_TARGET_PINS={
    'scripts/investment/public_sma_perpetual.py':'ba9fdacc5856324a16c858c99bc9346efc1be51c2d990af7c28069cf9671e079',
    'scripts/investment/vol_managed_perpetual_target.py':'e9544541d6e749704f9ea828c98f4c345e95f8c04227548913b5bf87043cc3c0'}


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


def signal_scope(left,right):
    """Bind a known equal-HOLD control to one fixed original SMA signal port."""
    a,ap=saved_protocol(left);b,bp=saved_protocol(right)
    require(a['strategy']==EQUAL_ID and b['strategy']==SMA_SIGNAL_ID and
        a.get('allocation','EQUAL')==b.get('allocation','EQUAL')=='EQUAL', 'Only constant-long versus fixed SMA long-flat, equal allocation')
    windows=[]
    for p in (a,b):
        stamps=[datetime.fromisoformat(p[k]) for k in ('start','end_exclusive')]
        require(all(t.tzinfo is not None and t.utcoffset().total_seconds()==0 for t in stamps), 'Explicit UTC period')
        windows.append(tuple(int(t.timestamp()*1_000_000) for t in stamps))
    require(windows[0]==windows[1] and windows[0][1]-windows[0][0]==left['actual_calendar_days']*86_400_000_000, 'Same complete signal scoring period')
    proofs=[saved_pool_proof(p) for p in (a,b)]
    require(a['initial_capital_USDT']==b['initial_capital_USDT']==10000 and a['pools']==b['pools'] and
        proofs[0]['path']==proofs[1]['path'] and proofs[0]['sha256']==proofs[1]['sha256'], 'Same frozen ordered pool and full capital')
    require(a['data_manifest']['sha256']==b['data_manifest']['sha256']==left['binding']['manifest_sha256']==right['binding']['manifest_sha256'] and
        Path(a['data_manifest']['path']).resolve()==Path(b['data_manifest']['path']).resolve(), 'Identical accepted signal and execution input identity')
    hashes=[p['binding']['source_hashes'] for p in (left,right)]
    require(all(p['source_hashes']==h for p,h in zip((a,b),hashes,strict=True)), 'Actual sources match their saved signal protocols')
    for key in FINANCE_SOURCES:
        require(hashes[0][key]==hashes[1][key], 'Unchanged signal account, engine, resource or environment '+key)
    require(left['binding']['environment_lock_sha256']==right['binding']['environment_lock_sha256']==
        hashes[0]['environments/v8/uv.lock'], 'Identical signal comparison runtime lock')
    require(all(hashes[0].get(k)==v for k,v in LEGACY_EQUAL_TARGET_PINS.items()) and
        all(hashes[1].get(k)==v for k,v in SIGNAL_SOURCE_PINS.items()), 'Known accepted equal targets and explicit original SMA port source pins')
    changes={k:dict(baseline=v,current=hashes[1][k]) for k,v in hashes[0].items()
             if k in hashes[1] and v!=hashes[1][k]}
    compatibility={'scripts/investment/multi_asset_data.py','scripts/investment/multi_asset_portfolio.py'}
    require(set(changes)<=set(TARGET_SOURCES)|compatibility and set(hashes[0])<=set(hashes[1]) and
        set(hashes[1])-set(hashes[0])<=set(SIGNAL_SOURCE_PINS), 'No unrelated source dropped, changed or introduced')
    # D052 added an optional inverse branch; this exact handcase also checked
    # the preserved default equal targets. Only that known source pair is used.
    proof_path='reports/fast_research/INVERSE_VOL_PORTFOLIO_TARGET_SYNTHETIC_20261004_V2.json'
    proof_sha='41e1cd397c7a1712c651549153c4396721be8bc4d9bd6873e615404dea9cb374'
    accepted=read(ROOT/proof_path,proof_sha)
    require(accepted['status']=='PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT' and
        accepted['test_exit_code']==0 and accepted['source_bytes_unchanged'] is True and
        accepted['junit_counts']==dict(tests=1,errors=0,failures=0,skipped=0) and
        all(accepted['binding']['source_hashes'][k]==SIGNAL_SOURCE_PINS[k] for k in TARGET_SOURCES), 'Known default equal-target compatibility proof')
    return dict(baseline_protocol=ap,current_protocol=bp,start_us=windows[0][0],end_us=windows[0][1],
        predeclared_pools=a['pools'],frozen_pool_receipt=proofs[0],current_pool_receipt=proofs[1],
        identical_data_manifest_sha256=a['data_manifest']['sha256'],source_changes=changes,
        unchanged_finance_source_hashes={k:hashes[0][k] for k in FINANCE_SOURCES},
        explicit_signal_source_pins=SIGNAL_SOURCE_PINS,
        reader_and_cli_compatibility_source_changes={k:v for k,v in changes.items() if k in compatibility},
        known_equal_target_compatibility=dict(baseline_pins=LEGACY_EQUAL_TARGET_PINS,
            current_pins={k:SIGNAL_SOURCE_PINS[k] for k in TARGET_SOURCES},proof_path=proof_path,proof_sha256=proof_sha),
        baseline_strategy_id=EQUAL_ID,current_strategy_id=SMA_SIGNAL_ID,baseline_signal='CONSTANT_LONG',
        current_signal='ORIGINAL_SMA50_200_LONG_FLAT',allocation='EQUAL',allocation_changed=False,
        directional_signal_changed=True,realized_risk_matched=False)


def signal_case(left,right,scope,days):
    require(left['pool']==right['pool']=='LIQUIDITY_TEN' and left['symbols']==right['symbols'] and
        len(left['symbols'])==len(set(left['symbols']))==10 and
        any(p['id']==left['pool'] and p['symbols']==left['symbols'] for p in scope['predeclared_pools']) and
        left['summary']['contract']==right['summary']['contract'] and
        left['summary']['cost_scenario']==right['summary']['cost_scenario'] and
        left['summary']['unit_scenario']==right['summary']['unit_scenario'] and
        left['summary']['mode']==right['summary']['mode']=='LONG_ONLY', 'Same ordered N10, risk contract, costs, units and long-only mode')
    equal_rules=dict(timeframe_minutes=1440,completed_daily_eligibility_bars=200,
        past_covariance_daily_returns=30,annual_volatility_target=.10,absolute_target_per_asset=.3,
        gross_target_cap=.6,direction_is_constant=True,
        raw_allocation='EQUAL_SHARE_OF_0.6_GROSS_TO_CONFIGURED_ELIGIBLE_MEMBERS',SMA_alpha_or_original_Jesse_hooks_used=False)
    sma_rules=dict(equal_rules,direction_is_constant=False,SMA_alpha_or_original_Jesse_hooks_used=True,
        fast_SMA_period=50,slow_SMA_period=200,SMA_includes_current_completed_day=True,
        entry_predicate='FAST_GT_SLOW_NOT_CROSS_EVENT',exit_predicate='HELD_LONG_AND_FAST_LT_SLOW',
        equal_policy='HOLD_CURRENT_STATE',close_then_wait_next_daily_decision_to_reenter=True,
        inactive_signal_budget_redistributed=False,allocation='EQUAL',fresh_flat_each_window=True,
        native_Jesse_or_Bybit_execution_replicated=False,funding_rates_used_for_signal=False,
        daily_availability='EXCLUSIVE_UTC_DAY_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED')
    metadata=[];proofs=[]
    for case,identity,rules,uses_hooks in ((left,EQUAL_ID,equal_rules,False),(right,SMA_SIGNAL_ID,sma_rules,True)):
        artifact=case['artifacts']['target_meta.json'];path=Path(artifact['path'])
        require(path.stat().st_size==artifact['bytes']<=2_000_000, 'Small saved signal target metadata')
        meta=read(path,artifact['sha256']);risk=meta['risk']
        require(meta['strategy_id']==identity and meta.get('allocation','EQUAL')=='EQUAL' and
            meta['symbols']==case['symbols'] and meta['mode']=='LONG_ONLY' and meta['rules']==rules and
            meta['original_SMA_alpha_used'] is uses_hooks and
            meta['original_long_and_short_and_exit_hooks_reused'] is uses_hooks and
            meta['direction_context_is_Jesse_strategy'] is uses_hooks, 'Actual fixed signal port and unchanged equal risk rules')
        require(meta['fresh_flat_each_window'] is True and meta['funding_rates_used_for_signal'] is False and
            meta['native_Jesse_or_Bybit_execution_replicated'] is False and meta['complete_daily_warmup']==200,
            'Fresh-flat completed-day research signal, no funding or native execution claim')
        require([r['decision_us'] for r in risk]==list(range(scope['start_us'],scope['end_us'],86_400_000_000)) and
            len(risk)==days and all(r['symbol_order']==case['symbols'] and r['past_only'] is True for r in risk), 'Same complete daily signal decision clock')
        metadata.append(meta);proofs.append(dict(path=str(path),sha256=artifact['sha256'],bytes=artifact['bytes'],
            strategy_id=identity,allocation='EQUAL',rules=rules))
    require([r['covariance_symbol_order'] for r in metadata[0]['risk']]==
        [r['covariance_symbol_order'] for r in metadata[1]['risk']], 'Same eligible covariance input members for signal contrast')
    require(metadata[1]['fast_period']==50 and metadata[1]['slow_period']==200 and
        metadata[1]['close_then_wait_next_daily_decision_to_reenter'] is True and
        metadata[1]['equality_holds_current_position'] is True, 'Original strict SMA predicates and close-then-wait state semantics')
    return dict(baseline=proofs[0],current=proofs[1],allocation_changed=False,directional_signal_changed=True,
        realized_risk_matched=False,alpha_identified=False)


def pool_scope(left, right):
    """New pool comparisons share one accepted source, including control subsets.

    Prior comparisons with separately accepted sources remain reproducible at
    their original Git commit. Their saved results are never rewritten here.
    """
    a, ap = saved_protocol(left); b, bp = saved_protocol(right)
    require(a['strategy'] == b['strategy'] == EQUAL_ID and
        a.get('allocation', 'EQUAL') == b.get('allocation', 'EQUAL') == 'EQUAL' and
        a['initial_capital_USDT'] == b['initial_capital_USDT'] == 10000 and
        a['pools'] == b['pools'], 'Fixed equal HOLD and identical predeclared pools/capital')
    require(a['start'] == b['start'] and a['end_exclusive'] == b['end_exclusive'],
        'Identical full scoring window')
    members = [{frozenset(c['symbols']) for c in report['cases']} for report in (left, right)]
    require(all(len(pools) == 1 for pools in members) and members[0] != members[1],
        'Each report contains one pool and the pool comparison changes asset membership')
    proofs = [saved_pool_proof(p) for p in (a, b)]
    require(proofs[0]['path'] == proofs[1]['path'] and proofs[0]['sha256'] == proofs[1]['sha256'],
        'Same historical liquidity pool receipt')
    require(a['data_manifest']['sha256'] == b['data_manifest']['sha256'] ==
        left['binding']['manifest_sha256'] == right['binding']['manifest_sha256'] and
        Path(a['data_manifest']['path']).resolve() == Path(b['data_manifest']['path']).resolve(),
        'Pool/control subsets of the same accepted price, mark and funding manifest')
    for report, spec in ((left, a), (right, b)):
        require(report['binding']['source_hashes'] == spec['source_hashes'],
            'Actual sources match their prospective protocol')
    hashes = [p['binding']['source_hashes'] for p in (left, right)]
    require(hashes[0] == hashes[1], 'Same active loader, targets, finance and runtime sources')
    return dict(baseline_protocol=ap, current_protocol=bp,
        predeclared_pools=a['pools'], common_data_manifest=a['data_manifest'],
        frozen_pool_receipt=proofs[0], strategy_id=EQUAL_ID, allocation='EQUAL',
        asset_pool_changed=True, directional_signal_changed=False,
        unchanged_finance_source_hashes={k:hashes[0][k] for k in FINANCE_SOURCES},
        realized_risk_matched=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control',type=Path,required=True)
    parser.add_argument('--pool',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--experiment-id',required=True)
    parser.add_argument('--contrast',choices=('pool','allocation','signal'),default='pool')
    args=parser.parse_args()
    require(os.environ.get('COIN_TASK_ID') and not args.output.exists()
        and args.output.resolve().is_relative_to(ROOT/'reports'), 'Bounded new comparison')
    left,right=read(args.control),read(args.pool)
    require(all(p['complete_calendar_cases']==p['completed_cases']==4 and
        p['initial_capital_per_comparison_account_USDT']==10000 and
        p['candidate']=='NONE' and not p['orders_sent'] and not p['locked_consumed']
        for p in (left,right)), 'Four complete scenarios per shared 10k portfolio')
    actual_days=left['actual_calendar_days']
    require(isinstance(actual_days,int) and actual_days==right['actual_calendar_days'],
            'Same actual full calendar length')
    if actual_days == 91:
        a_spec,_ = saved_protocol(left); b_spec,_ = saved_protocol(right)
        require(all(r.get('account_path') == p.get('account_path') ==
                'CONTINUOUS_SHARED_ACCOUNT_SEP_NOV_91D' and
                p['start'] == '2024-09-01T00:00:00+00:00' and
                p['end_exclusive'] == '2024-12-01T00:00:00+00:00' and
                p.get('data_role') == 'SEEN_DEVELOPMENT_CONTINUOUS_ACCEPTED_THREE_MONTH_MANIFEST'
                for r,p in ((left,a_spec),(right,b_spec))),
                'Fixed continuous capital path, not concatenated fresh monthly NAV')
    else:
        require(28 <= actual_days <= 31, 'Predeclared single month or accepted continuous 91D scope')
    contrast_scope=allocation_scope(left,right) if args.contrast=='allocation' else None
    signal_context=signal_scope(left,right) if args.contrast=='signal' else None
    pool_context=pool_scope(left,right) if args.contrast=='pool' else None
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
        if pool_context:
            require(a[key]['summary']['cost_scenario'] == b[key]['summary']['cost_scenario'] and
                a[key]['summary']['unit_scenario'] == b[key]['summary']['unit_scenario'] and
                all(any(p['id'] == c['pool'] and p['symbols'] == c['symbols']
                    for p in pool_context['predeclared_pools']) for c in (a[key], b[key])),
                'Actual ordered identities and complete cost/unit scenarios')
        target_contrast=allocation_case(a[key],b[key],contrast_scope,actual_days) if contrast_scope else None
        if signal_context:
            target_contrast=signal_case(a[key],b[key],signal_context,actual_days)
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
    if pool_context:
        result.update(contrast='pool', pool_contrast=pool_context)
    if signal_context:
        result.update(contrast='signal',signal_contrast=signal_context,
            scope='Same ordered July N10 pool, full capital, accepted inputs, equal raw allocation, costs and financial risk rules; '
                  'constant-long HOLD versus fixed original SMA50/200 long-flat signal. Actual exposure and realized risk are not matched. '
                  'Saved marked-NAV pairing retains terminal inventory; unclosed liquidated return is NOT_EVALUABLE. '
                  'No post-hoc risk scaling, account replay, identified alpha, native Bybit or long-term APR claim.')
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False,allow_nan=False)
        stream.write('\n')
    event=dict.fromkeys(FIELDS)
    event.update(event_id=args.experiment_id+':RESULT',event_type='SAVED_RESEARCH_COMPARISON',
        experiment_id=args.experiment_id,data_manifest_hash=result['control']['sha256'],
        success_failure=result['status'],reason_for_next_experiment=(
            'Saved single-factor original SMA signal contribution and unequal actual risk' if signal_context else
            'Saved single-factor allocation contribution and unequal actual risk' if contrast_scope else 'Economic pool contribution and actual risk'),
        artifact_path=str(args.output.resolve().relative_to(ROOT)),artifact_sha256=sha(args.output))
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    print(json.dumps(dict(status=result['status'],pairs=len(pairs),output=str(args.output))))


if __name__=='__main__':
    main()
