"""Unexecuted D033-only adapters over accepted native numerical finance checks."""
import ast, copy, hashlib, importlib.util
from pathlib import Path
import numpy as np
import polars as pl
from decimal import localcontext
ROOT=Path('/mnt/d/codex/coin')
ACCEPTED='docs/archive/PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_AUDIT_CHECKER_20261002_V1.py'
ACCEPTED_SHA='d79bc8a156987786e190e606d27a1656dc059137e739cbc919780e7b12e77135'
FINANCIAL_SHA='4b6e0514898676ea2fc1a75881917b2cb480e5f2f0501621008e13617924d04f'
MIN=60000000;DAY=86400000000
PUBLIC='COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER'
HYBRID='COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER'
SLEEVES=('CASH',PUBLIC,HYBRID)

def imported(path,digest,label):
    path=Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Accepted small code SHA changed')
    spec=importlib.util.spec_from_file_location(label,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def prepared_financial():
    """One accepted body; fixed-cost membership and zero-fill string compatibility only."""
    path=ROOT/ACCEPTED;raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ACCEPTED_SHA:raise ValueError('Accepted native audit changed')
    tree=ast.parse(raw);func=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='check_period']
    if len(func)!=1:raise ValueError('Unique accepted check_period function')
    loops=[n for n in ast.walk(func[0]) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='item'
           and ast.dump(n.iter,include_attributes=False)==ast.dump(ast.parse('fold["results"]',mode='eval').body,include_attributes=False)]
    if len(loops)!=1:raise ValueError('Unique accepted per-ledger finance loop')
    begin=raw.index(b'        for item in fold["results"]:')
    finish=raw.index(b'    need(len(seen)==3',begin)
    span=raw[begin:finish]
    if hashlib.sha256(span).hexdigest()!=FINANCIAL_SHA:raise ValueError('Accepted complete finance byte span')
    nodes=copy.deepcopy(loops[0].body);changes=[]
    for node in ast.walk(ast.Module(body=nodes,type_ignores=[])):
        if isinstance(node,ast.Tuple) and all(isinstance(e,ast.Constant) for e in node.elts) and [e.value for e in node.elts]==[2,4,8]:
            node.elts=[ast.Constant(value=8)];changes.append(dict(line=node.lineno,old=[2,4,8],new=[8]))
    if len(changes)!=1:raise ValueError('Only one accepted cost membership anchor')
    # Exact NumPy empty-string compatibility: nonempty original expression stays identical.
    before=ast.parse('np.char.replace(fills["symbol"].to_numpy().astype(str),"USDT","")',mode='eval').body
    after=ast.parse('np.array([],dtype=str) if fills.height==0 else np.char.replace(fills["symbol"].to_numpy().astype(str),"USDT","")',mode='eval').body
    class EmptyStrings(ast.NodeTransformer):
        count=0
        def visit_Call(self,node):
            node=self.generic_visit(node)
            if ast.dump(node,include_attributes=False)==ast.dump(before,include_attributes=False):
                self.count+=1;changes.append(dict(line=node.lineno,change='ZERO_FILL_STRING_ARRAY_ONLY',old_AST_sha256=hashlib.sha256(ast.dump(before,include_attributes=False).encode()).hexdigest(),new_AST_sha256=hashlib.sha256(ast.dump(after,include_attributes=False).encode()).hexdigest()))
                return ast.copy_location(copy.deepcopy(after),node)
            return node
    compatibility=EmptyStrings();module=compatibility.visit(ast.Module(body=nodes,type_ignores=[]));nodes=module.body
    if compatibility.count!=1:raise ValueError('Unique empty-fill asset-name compatibility expression')
    args=('item','fold','spec','r','audit','start','end','days','fm','per','close_times','target_bound')
    function=ast.FunctionDef(name='verify_one_existing_native_ledger',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=p) for p in args],
        vararg=None,kwarg=None,kwonlyargs=[],kw_defaults=[],defaults=[]),body=ast.parse('seen=set()').body+nodes+ast.parse('return audit["ledgers"][-1]').body,
        decorator_list=[],returns=None,type_comment=None,type_params=[])
    compiled=ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[]))
    old=imported(path,ACCEPTED_SHA,'d033_accepted_native_checks');ns=dict(vars(old));exec(compile(compiled,str(path)+':D033_547D_SINGLE_COST','exec'),ns)
    return ns[function.name],old,dict(accepted_source_path=str(path),accepted_source_sha256=ACCEPTED_SHA,
        original_financial_byte_sha256=FINANCIAL_SHA,financial_begin_line=loops[0].lineno,financial_end_line=loops[0].end_lineno,
        only_changed_financial_nodes=changes,derived_financial_AST_sha256=hashlib.sha256(ast.dump(compiled,include_attributes=False).encode()).hexdigest(),
        unchanged_fee_cash_net_inventory_capacity_lot_risk_sizing_cycle_minute_daily_month_statements=True,
        period_days_is_explicit_function_argument=547,production_backtest_or_fixed_targets_called=False)

def targets(fm,intent,receipt,calendar,strategy,accepted):
    """Use accepted hybrid rule arithmetic; public2h uses identical pinned prior20/SMA200 formulas."""
    need=accepted.need
    need(receipt['strategy_id']==strategy and receipt['paired_comparison_allowed'] and not receipt['warmup_failed'],'New target ready')
    need(receipt['calendar_sha256']==hashlib.sha256(calendar.tobytes()).hexdigest() and receipt['decision_count']==len(calendar),'Full target calendar')
    if strategy==HYBRID:return accepted.verify_hybrid_target(fm,intent,receipt,calendar)
    if strategy==PUBLIC:
        need(receipt['timeframe_minutes']==120 and receipt['donchian_period']==20 and receipt['trend_sma_period']==200,'Fixed public2h recipe')
        need(receipt['signal_hooks_reused_unmodified'] and not receipt['native_Jesse_engine_replicated'] and not receipt['upstream_balance_sizing_called'] and receipt['model_fits']==0,'Public hook port scope')
        upstream={'donchian_original.py':'fc635b257ad1e12951dc140dae46a63bd37e9abfa5f2d681ef1e754d8ce393fe','donchian_indicator_original.py':'b7e96ebe3ba476c771a65b353c269a84d02e04587f0d76166c5f322bbbb3a401','LICENSE':'80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d','JESSE_LICENSE':'8985ca8447e233f34397a52fe77989c02e27b8145d43bd8c715ae9c7a96056d4'}
        need(receipt['public_upstream_sha256']==upstream,'Exact pinned public2h hooks/license receipt')
    total_entries=total_exits=0;lower=int(fm['open_us'].min())
    for symbol in accepted.SYMS:
        one=intent.filter(pl.col('symbol')==symbol).sort('decision_us')
        need(one.height==len(calendar) and np.array_equal(one['decision_us'].to_numpy(),calendar),'One intent per minute')
        if strategy=='CASH':
            need(one['target_weight'].eq(0.).all() and one['reason'][:-1].eq('CASH').all() and one['reason'][-1]=='COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL','Cash never invests and frozen terminal intent reason');continue
        rows=fm.filter(pl.col('symbol')==symbol).sort('open_us');bar=120;bar_us=bar*MIN
        need(rows.height%bar==0,'Complete UTC2h grouping')
        close=rows['close'].to_numpy().reshape(-1,bar)[:,-1]
        high=rows['high'].to_numpy().reshape(-1,bar).max(axis=1);low=rows['low'].to_numpy().reshape(-1,bar).min(axis=1)
        available=rows['available_us'].to_numpy().reshape(-1,bar).max(axis=1);stamps=lower+np.arange(1,len(close)+1,dtype=np.int64)*bar_us
        need(np.array_equal(available,stamps),'Public2h exclusive-close availability')
        weights=np.zeros(len(calendar));held=False;prior=None
        for i,decision in enumerate(calendar):
            index=int((decision-lower)//bar_us-1)
            need(index>=199 and stamps[index]==decision//bar_us*bar_us and np.all(available[index-199:index+1]<=decision),'200 past closed2h bars')
            if index!=prior:
                if held:
                    if close[index]<low[index-20:index].min():held=False;total_exits+=1
                elif close[index]>high[index-20:index].max() and close[index]>close[index-199:index+1].mean():
                    held=True;total_entries+=1
                prior=index
            weights[i]=.3 if held else 0.
        need(np.array_equal(one['reason'].to_numpy(),np.where(weights==.3,'PUBLIC_RULE_LONG','PUBLIC_RULE_FLAT')),'Public reasons follow held-state hook')
        weights[-1]=0.
        need(np.array_equal(one['target_weight'].to_numpy(),weights),'Pinned public2h prior20/SMA200 chronology')
    return dict(independent_saved_input_rule_arithmetic=True,fixed_targets_called=False,full_calendar_minutes=len(calendar),
        entries_across_symbols=total_entries,exit_events_across_symbols=total_exits,warmup_bars=200 if strategy!='CASH' else 0)

def sparse_decimal(item,per,core,start,end):
    """Replay recorded Spot settlement only, never choose a signal/order/fill."""
    path=Path(item['directory']);fills=pl.read_parquet(path/'trades.parquet').sort('execution_us',maintain_order=True)
    cash=core.CAPITAL;shadow=core.CAPITAL;held=dict.fromkeys(core.SYMBOLS,core.ZERO)
    fees=execution=core.ZERO;core.MAX_USDT_ERROR=core.MAX_RATIO_ERROR=core.ZERO;minimum_cash=cash
    with localcontext() as context:
        context.prec=80
        for row in fills.iter_rows(named=True):
            core.need(start<row['execution_us']<end and row['execution_us']%MIN==1,'No warmup/terminal-outside fill')
            s=row['symbol'];index=(row['execution_us']-start-1)//MIN;mid=core.number(per[s]['open'][index]);q=core.number(row['quantity'])
            expected=core.expected_fill(s,'SPOT',row['side'],q,mid)
            for output,key in (('fill_price','fill_price'),('fee_amount','fee_amount'),('fee_USDT_mid','fee_USDT'),('position_delta','base_position_delta'),('cash_delta','spot_quote_delta')):
                core.close(row[output],expected[key],core.QTY_TOL if output=='position_delta' else core.USDT_TOL)
            core.need(row['fee_asset']==expected['fee_asset'],'Native received fee asset')
            if row['side']=='sell':core.need(q<=held[s]+core.QTY_TOL,'No gross-buy quantity oversell')
            cash+=expected['spot_quote_delta'];held[s]+=expected['base_position_delta'];shadow-=expected['base_position_delta']*mid
            fees+=expected['fee_USDT'];execution+=q*abs(expected['fill_price']-mid);minimum_cash=min(minimum_cash,cash)
            core.need(cash>=-core.USDT_TOL and held[s]>=-core.QTY_TOL,'No borrowed cash/net inventory')
            core.close(row['cash_after'],cash)
            nav=cash+sum((held[z]*core.number(per[z]['open'][index]) for z in core.SYMBOLS),core.ZERO)
            core.close(row['nav_after'],nav)
        residual=sum((held[s]*core.number(per[s]['close'][-1]) for s in core.SYMBOLS),core.ZERO)
        nav=cash+residual;gross=shadow+residual
        core.close(item['summary']['final_nav'],nav);core.close(item['summary']['fees'],fees)
        core.close(item['summary']['execution_costs'],execution);core.need(abs(gross-nav-fees-execution)<=core.USDT_TOL,'Decimal same-net-inventory gross-cost bridge')
    return dict(verified_sparse_Decimal_fills=fills.height,fee_formula_source_sha256=hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest(),
        Decimal_scope='RECORDED_SPOT_SETTLEMENT_CASH_NET_QTY_FEE_AND_TERMINAL_BRIDGE_ONLY',
        minute_daily_month_checks='REUSED_ACCEPTED_NUMPY_NUMERICAL_ASSERTIONS_NOT_ALL_DECIMAL',
        maximum_Decimal_cash_error_USDT=float(core.MAX_USDT_ERROR),maximum_Decimal_ratio_error=None,Decimal_ratio_assertions_performed=False,
        terminal_Decimal_cash_USDT=str(cash),terminal_Decimal_marked_residual_USDT=str(residual),minimum_Decimal_cash_USDT=str(minimum_cash),
        full_event_drawdown_verified=False,original_orders_or_account_simulated=False)