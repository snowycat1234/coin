"""UNEXECUTED D033 draft: private date namespaces over pinned public/native loops.

Reuses original function ASTs; only date globals, fixed source counts and cost
selection change. No shared module/global/file is mutated. Source acceptance,
new protocol and one synthetic boundary acceptance remain required before IO.
"""
from __future__ import annotations
import argparse, ast, hashlib, json
from copy import deepcopy
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from quant.paths import ROOT
from scripts.investment import compare_simple_strategies as old
from scripts.investment import bybit_spot_adapter as native
from scripts.investment import public_donchian_hybrid as hybrid
from scripts.investment import bulk_fixed_targets as bulk
from scripts.research_v8 import benchmark_targets as v1
from scripts.research_v8 import benchmark_targets_v2 as v2
from scripts.research_v8 import labels_v3 as timeguard
from scripts.research_v8 import public_donchian_adapter as public

SCOPE='DEC2023_JUN2025'
SOURCE_STATUS='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_578D_CALENDAR'
MONTHS=('2023-12',)+tuple(f'2024-{m:02d}' for m in range(1,13))+tuple(f'2025-{m:02d}' for m in range(1,7))
SLEEVES=('CASH',public.STRATEGY_2H_ID,hybrid.STRATEGY_ID)
LOWER, END=date(2023,12,1), date(2025,7,1)
PINS={
 'scripts/investment/compare_simple_strategies.py':'3dfa0e3176791980de51e5bc990b1998f93eb24c02bdc1261a074eab92fb52f1',
 'scripts/investment/bybit_spot_adapter.py':'8c8852bf70813ada5720c210f50c9038a5ecaadee1b4f38b77a71aa9e8b038ca',
 'scripts/investment/public_donchian_hybrid.py':'80e4b24319becacefb0d6c9551473e3d4214cf3167ae45f5ac8ff7f559c27d68',
 'scripts/investment/bulk_fixed_targets.py':'d750b99449cba479544a6003d455bedba2776959c48c09342252828ef413d58f',
 'scripts/research_v8/public_donchian_adapter.py':'169d7ba6ebde24be5ce4730c5e741ed281a0155e4cadc22f1bb2bedccb4093c2',
 'scripts/research_v8/benchmark_targets.py':'cb3158116494c41b6649f80dc4013b3c1ff9e495773b3ae298d9d5b6e9d46652',
 'scripts/research_v8/benchmark_targets_v2.py':'72235137633847101af57e658f8a50ea50494e1a63de663784754d72fef81a82',
 'scripts/research_v8/labels_v3.py':'cedc8fff7cca288bb318b272e3718ac9cb1df6edc6be924e6112d1af9cb5d078'}

def literal(tree, changes, label, before, after, expected):
    old_node=ast.parse(before,mode='eval').body; new_node=ast.parse(after,mode='eval').body
    patch=native._ExactPatch(old_node,new_node); tree=patch.visit(tree)
    if patch.count!=expected: raise ValueError(f'{label}: {patch.count} anchors, expected {expected}')
    changes.append(dict(change=label,matches=patch.count,old_ast_sha256=native._digest(old_node),new_ast_sha256=native._digest(new_node)))
    return tree

def namespace(module, names, overrides, receipt, transform=None):
    """Compile selected unchanged AST functions into private globals, no imports."""
    source=Path(module.__file__); tree=ast.parse(source.read_text())
    selected=[deepcopy(node) for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    if len(selected)!=len(names): raise ValueError('Exact pinned function selectors required')
    environment=dict(vars(module)); environment.update(overrides)
    for node in selected:
        before=native._digest(node); changes=[]
        if transform is not None: node=transform(node,changes)
        exec(compile(ast.fix_missing_locations(ast.Module([node],type_ignores=[])),str(source)+'<D033-private>','exec'),environment)
        receipt.append(dict(module=str(source.relative_to(ROOT)),function=node.name,
            original_AST_sha256=before,derived_AST_sha256=native._digest(node),changes=changes))
    return environment

def common_changes(node, changes):
    if node.name=='comparison_plan':
        return native._replace(node,changes,'ONE_COST_PLANNED_LEDGER_COUNT',
            'planned = len(windows) * len(strategies) * 3','planned = len(windows) * len(strategies)')
    if node.name=='verify_source_calendar':
        return literal(node,changes,'EXACT_38_SOURCE_RECEIPT_COUNTS','10','38',2)
    if node.name=='period_aggregate':
        return literal(node,changes,'ONLY_ACCEPTED_SPREAD8_AGGREGATE','(2,4,8)','(8,)',1)
    if node.name=='verify_sources':
        return native._replace(node,changes,'PRIVATE_NATIVE_DATE_WRAPPER',
            'from scripts.investment import bybit_spot_adapter','bybit_spot_adapter = PERIOD_NATIVE')
    if node.name=='research':
        node=literal(node,changes,'SOURCE_COUNT_AND_PROGRESS_38','10','38',3)
        node=literal(node,changes,'ONLY_ACCEPTED_SPREAD8_ACTUAL_LOOP','(2,4,8)','(8,)',1)
        node=native._replace(node,changes,'PRIVATE_NATIVE_RESEARCH_ROUTE',
            'from scripts.investment import bybit_spot_adapter','bybit_spot_adapter = PERIOD_NATIVE')
        node=native._replace(node,changes,'PRIVATE_HYBRID_RESEARCH_ROUTE',
            'from scripts.investment import public_donchian_hybrid','public_donchian_hybrid = PERIOD_HYBRID')
        return native._replace(node,changes,'ONE_COST_FOLD_COMPLETION_COUNT',
            'fold_record["status"] = "COMPLETE_PROXY_COMPARISON" if len(fold_record["results"]) == len(strategies) * 3 else "PARTIAL_INPUT_COVERAGE"',
            'fold_record["status"] = "COMPLETE_PROXY_COMPARISON" if len(fold_record["results"]) == len(strategies) else "PARTIAL_INPUT_COVERAGE"')
    if node.name=='main':
        return native._replace(node,changes,'EXPLICIT_PRIVATE_PERIOD_DERIVATION',
            'progress = Progress()','report["period_namespace_derivation"] = PERIOD_DERIVATION\nprogress = Progress()')
    return node

def context(spec):
    """Metadata/AST only; does not accept sources or read any market array."""
    for path,digest in PINS.items():
        if native.file_sha(ROOT/path)!=digest: raise ValueError('Frozen reused source changed: '+path)
    if tuple(spec['strategy_ids'])!=SLEEVES or spec['planned_ledgers']!=3 or len(spec['folds'])!=1:
        raise ValueError('Exactly three existing sleeves, one full period, one cost')
    fold=spec['folds'][0]
    if fold['period_start']!='2024-01-01' or fold['period_end_exclusive']!='2025-07-01': raise ValueError('Fixed547day full period')
    if spec['source_scope']!=SCOPE or tuple(spec['source_calendar'])!=MONTHS or spec['source_days_per_symbol']!=578:
        raise ValueError('Exact31day warmup and19month calendar')
    if spec['costs']['spread_bps']!=[8] or spec['costs']['nominal_roundtrip_bps']!=[36] or spec['costs']['fee_bps_per_side']!=10 or spec['costs']['slippage_bps_per_side']!=4:
        raise ValueError('Only existing36bp nominal conservative scenario')
    required={'initial_cash':10000,'target_annual_vol':.10,'gross_cap':.6,'per_symbol_cap':.3,
        'latency_minutes':1,'vol_window_days':30,'min_vol_days':20,'participation_rate':.001,'max_order_wait_minutes':5,'liquidate_at_end':True}
    if any(spec['common_config'][key]!=value for key,value in required.items()): raise ValueError('Original common capital/risk/timing/capacity')
    if spec['fee_settlement']!='BYBIT_SPOT_RECEIVED_ASSET_V1' or any(key in spec for key in ('reused_minute_input','reused_reference_report','reused_target_inputs')):
        raise ValueError('Same received-asset account, new accepted period inputs and targets only')
    receipt=[]; start_us,end_us=old.day_us(LOWER),old.day_us(END)
    private_time=SimpleNamespace(**namespace(timeguard,('_integer_array','_timestamps','_stamp','_minute_decisions'),
        dict(BEGIN=start_us,END=end_us),receipt))
    private_v1=SimpleNamespace(**namespace(v1,('calendar_array','_plan','fixed_targets'),dict(START=LOWER,LOCKED=END),receipt))
    private_v2=SimpleNamespace(**namespace(v2,('calendar_array','_integer_timestamp_columns','_version','fixed_targets'),
        dict(_time=private_time,_v1=private_v1),receipt))
    private_public=SimpleNamespace(**namespace(public,('_load_public_hooks','closed_hours','fixed_targets'),
        dict(common=private_v2,original=private_v1),receipt))
    private_hybrid=SimpleNamespace(**namespace(hybrid,('fixed_targets',),
        dict(public=private_public,common=private_v2,original=private_v1),receipt))
    private_bulk=SimpleNamespace(**namespace(bulk,('fixed_targets',),dict(common=private_v2,original=private_v1),receipt))
    private_native=SimpleNamespace(**namespace(native,('run_backtest',),dict(BEGIN_US=start_us,END_US=end_us),receipt))
    derived=dict(classification='D033_547D_PREVIOUSLY_SEEN_DEVELOPMENT_SCREENING_NOT_UNSEEN',
        source_scope=SCOPE,source_receipt_status_required=SOURCE_STATUS,warmup_start='2023-12-01',
        period_start='2024-01-01',period_end_exclusive='2025-07-01',days=547,warmup_days=31,
        source_files=38,source_days_per_symbol=578,source_rows=1664640,research_minutes_per_asset=787680,
        fixed_spread_bps=[8],nominal_roundtrip_bps=[36],accounts=3,pinned_sources=PINS,functions=receipt,
        original_modules_or_globals_mutated=False,new_engine_or_account_loop_written=False,
        native_financial_kernel_AST_unchanged=True,public_hooks_unchanged=True,
        source_acceptance_performed_by_context=False,market_arrays_read_by_context=False,
        long_term_APR_or_native_execution_qualification=False)
    environment=namespace(old,('source_scope','allowed_source_path','minute_view','signal_close_view','comparison_plan','period_aggregate',
        'verify_source_calendar','verify_sources','research','main'),dict(START=LOWER,LOCKED=END,
        SOURCE_SCOPES={SCOPE:(MONTHS,578,SOURCE_STATUS)},benchmarks=private_v2,public_strategy=private_public,
        bulk_fixed_targets=private_bulk,PERIOD_NATIVE=private_native,PERIOD_HYBRID=private_hybrid,PERIOD_DERIVATION=derived),receipt,common_changes)
    environment['__file__']=str(Path(__file__).resolve())
    return environment

def main():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--protocol',type=Path,required=True)
    args,_=parser.parse_known_args();path=args.protocol.resolve()
    if not path.is_relative_to(ROOT/'protocols') or not path.is_file() or path.stat().st_size>=2_000_000:
        raise ValueError('Future exclusive ROOT protocol required before actual execution')
    context(json.loads(path.read_text()))['main']()

if __name__=='__main__': main()
