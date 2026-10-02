"""Received-asset Spot fees over the fixed COIN simulator, with audited AST deltas.

This models fee settlement on Binance minute proxies; it is not evidence of Bybit
historical prices, filters, BBO, capacity or authenticated account fee rates.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path

import numpy as np
import polars as pl
from quant import backtest as legacy
from quant.paths import ROOT, STATE

VERSION = "BYBIT_SPOT_RECEIVED_ASSET_V1"
PROFILE_PATH = "protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json"
PROTOCOL_PATH = "protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json"
PINS = {
    "src/quant/backtest.py": "ee333d4e5cbadb489e5d467619d0872f78ccb2d86d8b5f46eacc69cb63f9829a",
    "src/quant/execution_contract.py": "b7fc110d84240233611e2f7e7360c1b7cc5c92308f842a796560964db33f97d1",
    "src/quant/execution.py": "8d886164668f3ae4b0be47f9cc04c99a78ce85e8f96fe10d6a04d6bd89addd3b",
    PROFILE_PATH: "d6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f",
}
BASE = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}
BEGIN_US, END_US = 1751328000000000, 1772323200000000


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pins():
    for name, expected in PINS.items():
        if file_sha(ROOT / name) != expected:
            raise ValueError("Frozen Bybit adapter dependency changed: " + name)
    if Path(legacy.__file__).resolve() != (ROOT / "src/quant/backtest.py").resolve():
        raise ValueError("Original project engine import required")


def _digest(node):
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


def _one_statement(source):
    nodes = ast.parse(source).body
    if len(nodes) != 1:
        raise ValueError("One exact statement anchor required")
    return nodes[0]


class _ExactPatch(ast.NodeTransformer):
    def __init__(self, old, new):
        self.anchor = ast.dump(old, include_attributes=False)
        self.new, self.count = new, 0

    def visit(self, node):
        if ast.dump(node, include_attributes=False) == self.anchor:
            self.count += 1
            return deepcopy(self.new)
        return super().visit(node)


def _replace(tree, changes, name, old, new):
    original = _one_statement(old)
    replacements = ast.parse(new).body
    patch = _ExactPatch(original, replacements)
    result = patch.visit(tree)
    if patch.count != 1:
        raise ValueError(f"Exact AST anchor {name} occurs {patch.count} times, expected one")
    changes.append({"change": name, "matches": 1, "old_ast_sha256": _digest(original),
        "new_ast_sha256": _digest(ast.Module(replacements, type_ignores=[])),
        "old_statement": ast.unparse(original), "new_statement": ast.unparse(ast.Module(replacements, type_ignores=[]))})
    return result


def _extend_dict(tree, changes, name, keys, values, additions):
    expected = ast.Dict([ast.Constant(key) for key in keys],
        [ast.parse(value, mode='eval').body for value in values])
    candidates = [node for node in ast.walk(tree) if isinstance(node, ast.Dict)
        and ast.dump(node, include_attributes=False)==ast.dump(expected, include_attributes=False)]
    if len(candidates) != 1:
        raise ValueError("Unique pinned dictionary anchor required: " + name)
    node = candidates[0]
    old = deepcopy(node)
    for key, value in additions.items():
        node.keys.append(ast.Constant(key)); node.values.append(ast.parse(value, mode="eval").body)
    changes.append({"change": name, "matches": 1, "old_ast_sha256": _digest(old), "new_ast_sha256": _digest(node),
        "old_statement": ast.unparse(old), "new_statement": ast.unparse(node)})


@lru_cache(maxsize=1)
def _commission_function():
    """Reuse the three original commissionAsset balance updates without its engine."""
    tree = ast.parse((ROOT / "src/quant/execution.py").read_text())
    statements = []
    for text in (
        "balances[base] = balances.get(base, ZERO) + direction * amount",
        "balances[cash] = balances.get(cash, ZERO) - direction * cost",
        "balances[trade['commissionAsset']] = balances.get(trade['commissionAsset'], ZERO) - fee",
    ):
        anchor = ast.dump(_one_statement(text), include_attributes=False)
        matches = [node for node in ast.walk(tree) if ast.dump(node, include_attributes=False) == anchor]
        if len(matches) != 1:
            raise ValueError("Unique frozen execution commissionAsset update required")
        statements.append(deepcopy(matches[0]))
    function = ast.parse("def commission(balances, base, cash, direction, amount, cost, trade, fee):\n    pass").body[0]
    function.body = statements
    namespace = {"ZERO": 0.0}
    exec(compile(ast.fix_missing_locations(ast.Module([function], type_ignores=[])),
        "<pinned-execution-commission-balances>", "exec"), namespace)
    return namespace["commission"]


def _received_asset_fill(symbol, side, gross, fill, mid, rate):
    base = BASE[symbol]
    asset = base if side == "buy" else "USDT"
    amount = gross * rate if side == "buy" else gross * fill * rate
    balances = {base: 0.0, "USDT": 0.0}
    _commission_function()(balances, base, "USDT", 1 if side == "buy" else -1,
        gross, gross * fill, {"commissionAsset": asset}, amount)
    return balances["USDT"], balances[base], asset, amount, amount * mid if side == "buy" else amount


@lru_cache(maxsize=1)
def _compiled():
    _pins()
    original = ast.parse((ROOT / "src/quant/backtest.py").read_text())
    functions = [node for node in original.body if isinstance(node, ast.FunctionDef) and node.name == "run_backtest"]
    if len(functions) != 1:
        raise ValueError("One original pinned simulator function required")
    tree = deepcopy(functions[0]); original_hash = _digest(tree); changes = []
    replacements = [
        ("BUY_NET_UNIT_AND_COST", "cost_per_quantity = abs(fill - mid) + fill * config.fee_rate",
         "received_mid = mid * (1 - config.fee_rate) if side == 'buy' else mid\n"
         "cost_per_quantity = fill - received_mid if side == 'buy' else abs(fill - mid) + fill * config.fee_rate"),
        ("NET_TARGET_DENOMINATOR", "desired_quantity = abs(desired_dollars) / (mid + weight * cost_per_quantity if side == 'buy' else mid - weight * cost_per_quantity)",
         "desired_quantity = abs(desired_dollars) / (received_mid + weight * cost_per_quantity if side == 'buy' else mid - weight * cost_per_quantity)"),
        ("NET_ASSET_CAP_DENOMINATOR", "asset_limit = max(0.0, (config.max_weight * nav - positions[symbol] * mid) / (mid + config.max_weight * cost_per_quantity))",
         "asset_limit = max(0.0, (config.max_weight * nav - positions[symbol] * mid) / (received_mid + config.max_weight * cost_per_quantity))"),
        ("NET_GROSS_CAP_DENOMINATOR", "gross_limit = max(0.0, (config.max_gross * nav - gross) / (mid + config.max_gross * cost_per_quantity))",
         "gross_limit = max(0.0, (config.max_gross * nav - gross) / (received_mid + config.max_gross * cost_per_quantity))"),
        ("BUY_CASH_FILL_ONLY", "quantity = min(quantity, cash / (fill * (1 + config.fee_rate)), asset_limit, gross_limit)",
         "quantity = min(quantity, cash / fill, asset_limit, gross_limit)"),
        ("NO_GROSS_LOT_OVERSELL_NET_HOLDINGS", "quantity = math.floor(quantity / step + 1e-9) * step",
         "quantity = math.floor(quantity / step + 1e-9) * step\n"
         "if side == 'sell' and quantity > positions[symbol]:\n    quantity = max(0.0, quantity - step)"),
        ("RECEIVED_ASSET_COMMISSION", "fee = notional * config.fee_rate",
         "cash_delta, position_delta, fee_asset, fee_amount, fee_USDT_mid = _received_asset_fill(symbol, side, quantity, fill, mid, config.fee_rate)\nfee = fee_USDT_mid"),
        ("NATIVE_CASH_UPDATE", "cash -= direction * notional + fee", "cash += cash_delta"),
        ("NET_RECEIVED_POSITION_UPDATE", "positions[symbol] += direction * quantity", "positions[symbol] += position_delta"),
        ("PRESERVE_POSITIVE_SUBLOT_DUST", "if abs(positions[symbol]) < 1e-10:\n    positions[symbol] = 0.0",
         "if positions[symbol] < 0:\n    raise AssertionError('Received-asset settlement cannot oversell net spot inventory')"),
        ("BUY_CYCLE_NO_QUOTE_FEE_DOUBLE_CHARGE", "cycle['cost'] += notional + fee", "cycle['cost'] += notional"),
        ("ORDER_GROSS_FILLED_QUANTITY", "order['filled_notional'] = notional", "order['filled_notional'] = notional\norder['quantity'] = quantity"),
    ]
    for name, old, new in replacements:
        tree = _replace(tree, changes, name, old, new)
    _extend_dict(tree, changes, "ORDER_QUANTITY_INITIAL_ZERO", ["open_us","signal_us","capacity_open_us","symbol","side","requested_notional","capacity","filled_notional","status"],
        ["timestamp","goal['signal_us']","ExecutionContractV2().capacity_minute_us(timestamp)","symbol","side","abs(desired_dollars)","liquidity[symbol]*config.participation_rate","0.0","''"], {"quantity":"0.0"})
    _extend_dict(tree, changes, "TRADE_NET_SETTLEMENT_FIELDS", ["execution_us","signal_us","capacity_open_us","target_weight","symbol","side","quantity","mid_price","fill_price","notional","fee","execution_cost","cash_after","nav_after","asset_weight_after","gross_weight_after","capacity"],
        ["timestamp+1","goal['signal_us']","order['capacity_open_us']","weight","symbol","side","quantity","mid","fill","notional","fee","execution_cost","cash","nav_after","asset_weight","gross_weight","order['capacity']"],
        {"gross_quantity":"quantity","position_delta":"position_delta","cash_delta":"cash_delta","fee_asset":"fee_asset","fee_amount":"fee_amount","fee_USDT_mid":"fee_USDT_mid"})
    _extend_dict(tree, changes, "TRADE_NET_SETTLEMENT_SCHEMA", ["execution_us","signal_us","capacity_open_us","target_weight","symbol","side","quantity","mid_price","fill_price","notional","fee","execution_cost","cash_after","nav_after","asset_weight_after","gross_weight_after","capacity"],
        ["pl.Int64","pl.Int64","pl.Int64","pl.Float64","pl.String","pl.String",*(["pl.Float64"]*11)],
        {"gross_quantity":"pl.Float64","position_delta":"pl.Float64","cash_delta":"pl.Float64","fee_asset":"pl.String","fee_amount":"pl.Float64","fee_USDT_mid":"pl.Float64"})
    _extend_dict(tree, changes, "ORDER_GROSS_QUANTITY_SCHEMA", ["open_us","signal_us","capacity_open_us","symbol","side","requested_notional","capacity","filled_notional","status"],
        ["pl.Int64","pl.Int64","pl.Int64","pl.String","pl.String","pl.Float64","pl.Float64","pl.Float64","pl.String"], {"quantity":"pl.Float64"})
    tree.name = "run_bybit_received_asset_backtest"
    ast.fix_missing_locations(tree)
    module = ast.Module([tree], type_ignores=[])
    namespace = dict(vars(legacy)); namespace.update(__name__=__name__, _received_asset_fill=_received_asset_fill)
    exec(compile(module, "<pinned-bybit-received-asset-simulator>", "exec"), namespace)
    return namespace[tree.name], tree, original_hash, changes


def derivation_receipt():
    _pins(); _, tree, original_hash, changes = _compiled()
    return {"fee_settlement_version":VERSION, "adapter_source_sha256":file_sha(__file__),
        "dependency_source_sha256":dict(PINS), "adapter_protocol_sha256":file_sha(ROOT/PROTOCOL_PATH),
        "original_function_ast_sha256":original_hash, "derived_AST_SHA256":_digest(tree),
        "allowed_ast_changes":deepcopy(changes), "original_globals_mutated":False,
        "fee_asset_semantics":"REUSED_PINNED_EXECUTION_COMMISSION_ASSET_BALANCE_UPDATES",
        "native_bybit_market_execution_proven":False}


def export_derivation(directory):
    directory=Path(directory).resolve()
    if not directory.is_relative_to(STATE.resolve()):
        raise ValueError("Derivation export must be in D-hosted native STATE")
    directory.mkdir(parents=True,exist_ok=True)
    receipt=derivation_receipt(); _,tree,_,_=_compiled()
    source=directory/'derived_engine_ast.py'; metadata=directory/'derivation.json'
    with source.open('x') as stream:stream.write(ast.unparse(tree)+'\n')
    receipt['derived_source_file_sha256']=file_sha(source)
    with metadata.open('x') as stream:json.dump(receipt,stream,indent=2,allow_nan=False)
    return {**receipt,"derived_source_path":str(source),"receipt_path":str(metadata),"receipt_sha256":file_sha(metadata)}


def run_backtest(bars, minutes, targets, config=None):
    """Drop-in research entry; net fees alter actual buy sizing/cash/positions."""
    _pins()
    config=legacy.BacktestConfig() if config is None else config
    if config.fee_bps!=10 or config.fee_multiplier!=1:
        raise ValueError("Fixed Bybit ordinary Spot Non-VIP10bp required; no perpetual substitution")
    if set(minutes['symbol'].unique().to_list())-BASE.keys():
        raise ValueError("Only BTCUSDT/ETHUSDT received-asset mapping accepted")
    for frame,column,end_allowed in ((minutes,'open_us',False),(targets,'available_us',False)):
        if frame.schema[column]!=pl.Int64 or frame[column].null_count():
            raise ValueError("Original integer development timestamps required")
        stamps=frame[column].to_numpy()
        if not np.all((stamps>=BEGIN_US)&(stamps<END_US)):
            raise ValueError("Development prices/signals only; locked input forbidden")
    function,_,_,_=_compiled()
    result=function(bars,minutes,targets,config)
    receipt=derivation_receipt()
    result.summary.update(fee_settlement_version=VERSION, bybit_fee_profile_sha256=PINS[PROFILE_PATH],
        derived_AST_SHA256=receipt['derived_AST_SHA256'], quantity_semantics='GROSS_TRADE_AND_ORDER_QUANTITY_NET_POSITION_DELTA',
        fee_summary_units='USDT_FILL_TIME_MID_VALUE_BUY_BASE_FEE_SELL_QUOTE_FEE',
        gross_pnl_definition='SAME_NET_RECEIVED_POSITION_DELTA_GROSS_SHADOW_NOT_FEE_FREE_GROSS_ORDER_INVENTORY',
        fill_time_cost_addback_pnl_diagnostic=result.summary['gross_pnl_before_costs'],
        old_execution_contract_binding_scope='TIMING_AND_ORIGINAL_RISK_SOURCE_NEW_FEE_SETTLEMENT_ID_SEPARATE',
        native_bybit_market_execution_proven=False, candidate_qualification_allowed=False)
    return result


def _smoke_main():
    """Standalone synthetic acceptance; parent owns the shared registry."""
    import argparse, os, resource, shlex, shutil, subprocess, sys, time
    import xml.etree.ElementTree as ET
    from datetime import UTC, datetime
    from quant import resources
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke',action='store_true',required=True)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();work=args.run_dir.resolve();out=args.output.resolve()
    if not work.is_relative_to(STATE.resolve()) or work.exists() or not out.is_relative_to((ROOT/'reports/fast_research').resolve()) or out.exists():
        raise ValueError('Exclusive STATE acceptance and small project receipt required')
    if Path(sys.prefix).resolve()!=Path('/home/xflops/coin-state/v8-clean-env-20261002-v2') or pl.thread_pool_size()>2:
        raise ValueError('Accepted clean CPU environment with at most2 Polars threads required')
    resources.status();work.mkdir()
    names=[*PINS,PROTOCOL_PATH,'scripts/investment/bybit_spot_adapter.py','tests/test_bybit_spot_adapter.py','environments/v8/uv.lock']
    hashes={name:file_sha(ROOT/name) for name in names}
    command=[sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]
    tests=[sys.executable,'-m','pytest','tests/test_bybit_spot_adapter.py','-q',
        '--basetemp='+str(work/'pytest'),'-o','cache_dir='+str(work/'pytest-cache'),'--junitxml='+str(work/'junit.xml')]
    binding={'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_hashes':hashes,'environment_lock_sha256':hashes['environments/v8/uv.lock'],'sys_prefix':sys.prefix,
        'exact_command':shlex.join(command),'exact_test_command':shlex.join(tests),'task_id':os.environ['COIN_TASK_ID'],
        'data_scope':'SYNTHETIC_ONLY_NO_MARKET_PRICE_IO','models_fit':0,'GPU':0,'seed':'NOT_APPLICABLE_DETERMINISTIC'}
    for name in hashes:
        copied=work/'source-snapshot'/name;copied.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,copied)
    with (work/'RUN_BINDING.json').open('x') as stream:json.dump(binding,stream,indent=2,allow_nan=False)
    with (work/'START.json').open('x') as stream:json.dump({**binding,'status':'PREBOUND_START','created_utc':datetime.now(UTC).isoformat()},stream,indent=2,allow_nan=False)
    report={'status':'FAIL_BYBIT_RECEIVED_ASSET_SYNTHETIC','binding':binding,'run_dir':str(work),
        'run_binding_sha256':file_sha(work/'RUN_BINDING.json'),'market_inputs_read':False,'market_models_fit':0,
        'orders_sent':0,'locked_consumed':False,'candidate_status':'NO_QUALIFIED_CANDIDATE'}
    started=time.monotonic()
    try:
        report['derivation']=export_derivation(work/'derivation')
        result=subprocess.run(tests,cwd=ROOT,check=False);report['test_exit_code']=result.returncode
        if (work/'junit.xml').exists():
            suites=ET.parse(work/'junit.xml').getroot()
            report['junit_counts']={key:sum(int(suite.attrib.get(key,'0')) for suite in suites.iter('testsuite')) for key in ('tests','errors','failures','skipped')}
            report['junit_sha256']=file_sha(work/'junit.xml')
        if result.returncode!=0:raise ValueError('Received-asset acceptance failed; preserve this receipt and snapshot')
        if hashes!={name:file_sha(ROOT/name) for name in hashes}:raise ValueError('Acceptance source changed during run')
        report.update(status='PASS_BYBIT_RECEIVED_ASSET_SYNTHETIC_NOT_MARKET_QUALIFICATION',source_bytes_unchanged=True)
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=sum(path.stat().st_size for path in work.rglob('*') if path.is_file()),resources=resources.status())
        with out.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False)
        print(json.dumps({'status':report['status'],'output':str(out),'sha256':file_sha(out)}))


if __name__=='__main__':
    _smoke_main()
