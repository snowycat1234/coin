"""UNRUN D038: independent scalar50/200 plus unchanged original public hooks.

The accepted D037 daily availability/calendar/intent assertions are reused in
a private namespace. Only indicator predicates, hook state and strategy/vendor
identities change. No production target or account simulator is called.
Strict scalar math.fsum comparisons have no epsilon or retrospective tolerance.
"""
from pathlib import Path
from types import SimpleNamespace
import ast, copy, hashlib, json, math
import numpy as np

ROOT=Path('/mnt/d/codex/coin')
PARENT='docs/archive/PUBLIC_DONCHIAN_DAILY_INDEPENDENT_TARGET_SOURCE_20261003_V1.py'
PARENT_SHA='3a944f46e89600c90886053376fe2224683664e30985f3a11b089d0fd51a4d85'
VENDOR=ROOT/'third_party/jesse_example_smacrossover'
PINS={'smacrossover_original.py':'453440d7b934c494934a1c56b3826d94638594f79ad4e4c7faaff36b96d33fae',
      'LICENSE':'80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d'}
STRATEGY='COIN_JESSE_SMA50_200_1D_SPOT_ADAPTER'

def need(value,message):
    if not bool(value):raise ValueError(message)

class Strategy:
    is_long=False
    is_short=False
    def filters(self):return []

def original_sma_rules():
    for name,digest in PINS.items():
        need(hashlib.sha256((VENDOR/name).read_bytes()).hexdigest()==digest,'Pinned original SMA source/license bytes')
    def sma(candles,period=200):
        need(period in (50,200) and len(candles)>=period,'Only fixed completed50/200 averages')
        return math.fsum(float(v) for v in candles[-period:,2])/period
    raw=ast.parse((VENDOR/'smacrossover_original.py').read_text())
    classes=[n for n in raw.body if isinstance(n,ast.ClassDef) and n.name=='SMACrossover']
    need(len(classes)==1,'Unique original public SMACrossover class')
    private=dict(Strategy=Strategy,ta=SimpleNamespace(sma=sma),utils=None)
    exec(compile(ast.Module(classes,type_ignores=[]),str(VENDOR/'smacrossover_original.py')+'<independent-scalar-SMA>','exec'),private)
    return private['SMACrossover']

def context():
    raw=(ROOT/PARENT).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==PARENT_SHA,'Accepted daily target audit bytes')
    tree=ast.parse(raw);functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    need({'expected_daily_weights','verify_saved_targets'}<=set(functions),'Accepted complete target/intent assertions')
    changes=[]
    replacements={
        'upper=max(float(v) for v in high[index-20:index])':'upper=math.fsum(float(v) for v in close[index-49:index+1])/50',
        'lower=min(float(v) for v in low[index-20:index])':'lower=math.fsum(float(v) for v in close[index-199:index+1])/200',
        'mean=math.fsum(float(v) for v in close[index-199:index+1])/200':'mean=lower',
        'scalar_entry=float(close[index])>upper and float(close[index])>mean':'scalar_entry=upper>lower',
        'scalar_exit=float(close[index])<lower':'scalar_exit=held and upper<lower',
        'rules.close=float(close[index])':'rules.close=float(close[index]);rules.is_long=held;rules.is_short=False',
        'witnesses.append(dict(symbol=symbol,decision_us=decision,held=held,close=float(close[index]),upper=upper,lower=lower,SMA200=mean))':
            'witnesses.append(dict(symbol=symbol,decision_us=decision,held=held,fast_SMA50=upper,slow_SMA200=lower,signed_fast_minus_slow=upper-lower))'}
    anchors={ast.dump(ast.parse(old).body[0],include_attributes=False):(old,new) for old,new in replacements.items()}
    counts=dict.fromkeys(replacements,0)
    class Predicates(ast.NodeTransformer):
        def visit(self,node):
            key=ast.dump(node,include_attributes=False)
            if key in anchors:
                old,new=anchors[key];counts[old]+=1;changes.append(dict(line=node.lineno,old=old,new=new))
                return [ast.copy_location(copy.deepcopy(n),node) for n in ast.parse(new).body]
            return super().visit(node)
        def visit_keyword(self,node):
            node=self.generic_visit(node)
            if node.arg=='donchian_previous_bars':
                need(isinstance(node.value,ast.Constant) and node.value.value==20,'Exact old prior20 proof literal')
                node.arg='fast_SMA_period';node.value=ast.Constant(50)
            return node
    functions['expected_daily_weights']=Predicates().visit(functions['expected_daily_weights'])
    need(all(n==1 for n in counts.values()),'Every new indicator/state patch uniquely replaces an accepted target statement')
    class Identity(ast.NodeTransformer):
        count=0
        def visit_Constant(self,node):
            if node.value=='COIN_JESSE_DONCHIAN_1D_SPOT_ADAPTER':
                self.count+=1;return ast.copy_location(ast.Constant(STRATEGY),node)
            return node
    identity=Identity();functions['verify_saved_targets']=identity.visit(functions['verify_saved_targets'])
    need(identity.count==1,'Only one saved-target identity changes')
    selected=ast.Module([functions['expected_daily_weights'],functions['verify_saved_targets']],type_ignores=[])
    private=dict(__name__='d038_scalar_daily_target_private',__file__=__file__)
    # Imports and generic eligibility helpers only; old raw hook loader is never invoked.
    exec(compile(ast.parse(raw),str(ROOT/PARENT)+'<accepted-definitions>','exec'),private)
    private.update(original_rules=original_sma_rules,PINS=PINS,VENDOR=VENDOR)
    exec(compile(ast.fix_missing_locations(selected),str(ROOT/PARENT)+'<D038-predicates>','exec'),private)
    return private,changes

def verify_saved_targets(daily,calendar,intent,targets,receipt):
    need(receipt['SMA_kernel']=='OFFICIAL_POLARS_ROLLING_MEAN_SCALAR_LAST50_LAST200'
        and not receipt['original_short_and_whole_balance_sizing_transplanted'],
        'Scalar public hook port with common long-only sizing, not native Jesse execution')
    private,changes=context();weights,proof=private['expected_daily_weights'](daily,calendar)
    for column,symbol in enumerate(private['SYMBOLS']):
        saved=intent.filter(private['pl'].col('symbol')==symbol).sort('decision_us')
        need(saved.height==len(calendar),'Complete saved SMA minute intents')
        mismatch=np.flatnonzero(saved['target_weight'].to_numpy()!=weights[:,column])
        if len(mismatch):
            index=int(mismatch[0]);decision=int(calendar[index])
            bars=daily.filter((private['pl'].col('symbol')==symbol)&(private['pl'].col('close_us')<=decision)).sort('close_us')
            closes=bars['close'].to_numpy();fast=math.fsum(float(v) for v in closes[-50:])/50
            slow=math.fsum(float(v) for v in closes[-200:])/200
            witness=dict(symbol=symbol,decision_us=decision,scalar_fast_SMA50=fast,scalar_slow_SMA200=slow,
                expected_weight=float(weights[index,column]),saved_weight=float(saved['target_weight'][index]),epsilon_band_used=False)
            raise ValueError('SMA_TARGET_OR_PREDICATE_DISAGREEMENT '+json.dumps(witness,allow_nan=False))
    private['expected_daily_weights']=lambda *args:(weights,proof)
    result=private['verify_saved_targets'](daily,calendar,intent,targets,receipt)
    result.update(independent_scalar_kernel='MATH_FSUM_LAST50_LAST200_STRICT_NO_EPSILON',
        original_public_SMA_hook_and_long_state_checks=True,
        entry_is_cross_event=False,equal_fast_slow_holds_current_state=True,
        scalar_and_saved_target_predicate_disagreement=False,
        target_namespace_derivation=dict(parent_source=PARENT,parent_sha256=PARENT_SHA,indicator_state_changes=changes),
        production_target_generator_called=False,original_native_Jesse_indicator_kernel_claimed=False)
    return result
