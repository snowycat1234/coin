"""UNRUN D038 thin private-namespace adapter over accepted D037 finance.

Only metadata version names, SMA recipe, independent target oracle and new
output/STATE identities change. No account or financial loop is copied.
CLI and ACTUAL_BINDING schema are exactly those of the accepted D037 entry.
Vendor/target binding constants must be finalized before any actual invocation.
"""
from pathlib import Path
import ast, copy, hashlib

ROOT=Path('/mnt/d/codex/coin')
PARENT='scripts/investment/audit_public_daily_ledgers.py'
PARENT_SHA='330be71c11a4d1400003e377cf7027bdee76dd2a2ff05ac0f9172dfe4f9f102d'
TARGET='docs/archive/PUBLIC_SMA_DAILY_INDEPENDENT_TARGET_SOURCE_20261003_V1.py'
TARGET_SHA='bbd989de812104c3144c51a05563690f14e8ed26c00943205c1145370a5b652e'
STRATEGY='COIN_JESSE_SMA50_200_1D_SPOT_ADAPTER'
OUT=ROOT/'reports/fast_research/PUBLIC_SMA_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json'
SUCCESS='PASS_D038_THREE_SMA_DAILY_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'
SMOKE='tests/test_public_sma_daily_v2.py'

def need(value,message):
    if not bool(value):raise ValueError(message)

def sma_recipe(spec):
    """Exact new recipe mapping is finalized from frozen source, never outcomes."""
    need(spec['common_config']['initial_cash']==10000,'Original10k capital')
    need(spec['strategy_rules']==SMA_RULES,'Exact fixed50/200 state recipe')

SMA_RULES=dict(timeframe_minutes=1440,fast_SMA_period=50,slow_SMA_period=200,
    SMA_includes_current_completed_day=True,entry_predicate='FAST_GT_SLOW_NOT_CROSS_EVENT',
    exit_predicate='HELD_LONG_AND_FAST_LT_SLOW',equal_policy='HOLD_CURRENT_STATE',
    long_only=True,per_symbol_target=.3,fresh_flat_each_scoring_period=True,
    warmup_positions=False,day_close_equals_decision_permitted=True,
    daily_availability='EXCLUSIVE_UTC_DAY_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED',
    missing_policy='WHOLE_PAIRED_PERIOD_NOT_EVALUABLE_NO_RETROACTIVE_TARGET_ZEROING')

def context():
    raw=(ROOT/PARENT).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==PARENT_SHA,'Exact accepted D037 independent source')
    need(len(TARGET_SHA)==64 and STRATEGY!='PENDING_UNRUN_PRODUCTION_STRATEGY_ID'
        and SMA_RULES is not None and SMOKE.startswith('tests/'),'D038 static draft not frozen for execution')
    tree=ast.parse(raw); changes=[]
    originals={n.name:hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest()
        for n in tree.body if isinstance(n,ast.FunctionDef)}
    replacements={
        'protocols/PUBLIC_DONCHIAN_DAILY_':'protocols/PUBLIC_SMA_DAILY_',
        'reports/fast_research/PUBLIC_DONCHIAN_DAILY_':'reports/fast_research/PUBLIC_SMA_DAILY_',
        'tests/test_public_donchian_daily.py':SMOKE,
        'd037-':'d038-',
        'FAIL_D037_THREE_DAILY_PUBLIC_LEDGER_AUDIT':'FAIL_D038_THREE_SMA_DAILY_LEDGER_AUDIT'}
    counts=dict.fromkeys(replacements,0)
    class Rename(ast.NodeTransformer):
        def visit_Constant(self,node):
            if isinstance(node.value,str) and node.value in replacements:
                counts[node.value]+=1
                changes.append(dict(line=node.lineno,old=node.value,new=replacements[node.value]))
                return ast.copy_location(ast.Constant(value=replacements[node.value]),node)
            return node
    tree=Rename().visit(tree)
    need(all(n==1 for n in counts.values()),'Unique old version/STATE/smoke literals')
    metadata=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='metadata']
    need(len(metadata)==1,'Unique accepted metadata function')
    selectors=[n for n in metadata[0].body if isinstance(n,ast.Assign)
        and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='proto']
    need(len(selectors)==1,'Unique old fixed-version protocol selector')
    original_selector=selectors[0];position=metadata[0].body.index(original_selector)
    dynamic=ast.parse("proto=item['protocol_path']\nneed(Path(proto).parent==Path('protocols') and Path(proto).name.startswith('PUBLIC_SMA_DAILY_'+fold+'_20261003_') and Path(proto).suffix=='.json','Explicit new SMA protocol version from exact prebinding')").body
    metadata[0].body[position:position+1]=[ast.copy_location(n,original_selector) for n in dynamic]
    changes.append(dict(line=original_selector.lineno,change='BOUND_PROTOCOL_PATH_FROM_PLAN_WITH_FIXED_FOLD_PREFIX_AND_SHA'))
    recipe=[]
    for statement in metadata[0].body:
        if isinstance(statement,ast.Expr) and isinstance(statement.value,ast.Call):
            call=statement.value
            if isinstance(call.func,ast.Name) and call.func.id=='need' and len(call.args)==2 \
                and isinstance(call.args[1],ast.Constant) and call.args[1].value=='Fixed daily recipe/fresh-flat/10k capital':
                recipe.append(statement)
    need(len(recipe)==1,'Unique old Donchian recipe guard; financial guards unchanged')
    statement=recipe[0];position=metadata[0].body.index(statement)
    metadata[0].body[position]=ast.copy_location(ast.parse('sma_recipe(spec)').body[0],statement)
    changes.append(dict(line=statement.lineno,change='ONLY_NEW_SMA_RECIPE_METADATA_GUARD'))
    private={'__name__':'d038_independent_private','__file__':__file__}
    exec(compile(ast.fix_missing_locations(tree),str(ROOT/PARENT)+'<D038-identities>','exec'),private)
    private.update(STRATEGY=STRATEGY,TARGET=TARGET,TARGET_SHA=TARGET_SHA,OUT=OUT,SUCCESS=SUCCESS,sma_recipe=sma_recipe)
    unchanged={name:hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest()==originals[name]
        for n in tree.body if isinstance(n,ast.FunctionDef) for name in (n.name,)
        if name not in ('metadata','main')}
    need(all(unchanged.values()),'All source/input/numerical/Decimal helpers retain accepted ASTs')
    prior_write=private['write']
    def write(g,path,value):
        if Path(path)==OUT:
            value['independent_namespace_derivation']=dict(parent_source=PARENT,parent_sha256=PARENT_SHA,
                version_and_recipe_changes=changes,unchanged_function_ASTs=unchanged,
                original_financial_body_copied_or_rewritten=False,
                accepted_main_financial_statements_reused=True)
        return prior_write(g,path,value)
    private['write']=write
    return private

def main():context()['main']()

if __name__=='__main__':main()
