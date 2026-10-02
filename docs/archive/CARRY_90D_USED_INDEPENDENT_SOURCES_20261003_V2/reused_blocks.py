"""Unrun thin access to accepted independent finance and clock checks.
No production account function is imported. Only period constants and the exact
new accepted futures directory differ from the accepted independent functions.
"""
import ast, copy, hashlib, importlib.util
from pathlib import Path
from types import SimpleNamespace
ROOT=Path('/mnt/d/codex/coin')
START=1764547200000000;END=1772323200000000;COUNT=129600
MONTHS=('2025-12','2026-01','2026-02')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(ok,message):
    if not ok:raise AssertionError(message)
def imported(label,path,digest):
    need(sha(path)==digest,'Accepted independent source changed:'+str(path))
    spec=importlib.util.spec_from_file_location(label,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def reader_for_new_owner(reader,owner):
    """Reuse every value/clock check; replace only the exact futures STATE basename."""
    tree=ast.parse(Path(reader.__file__).read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='source_rows']
    need(len(nodes)==1,'One accepted source_rows function')
    node=copy.deepcopy(nodes[0]);old='v8-funding-mark-index-source-20261002-v1'
    hits=[n for n in ast.walk(node) if isinstance(n,ast.Constant) and n.value==old]
    need(len(hits)==1 and owner.parent==reader.STATE and owner.name=='carry-chronology-source-actual-20261003-v1',
         'One exact new accepted futures source root')
    before=ast.dump(node,include_attributes=False);hits[0].value=owner.name
    namespace=dict(vars(reader));tree=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
    exec(compile(tree,str(reader.__file__)+':new_source_path_only','exec'),namespace)
    return SimpleNamespace(**dict(vars(reader),source_rows=namespace['source_rows'])),dict(
        original_function_AST_sha256=hashlib.sha256(before.encode()).hexdigest(),
        derived_function_AST_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),
        changes=[dict(old=old,new=owner.name,matches=1)],all_value_clock_schema_checks_unchanged=True)

def financial(core,trim,delta,policy):
    """Extract accepted financial block; no copy of a financial loop to this file."""
    origin=core if policy=='ALL_FLAT' else trim
    tree=ast.parse(Path(origin.__file__).read_text())
    mains=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main']
    need(len(mains)==1,'One accepted audit entry')
    trials=[n for n in mains[0].body if isinstance(n,ast.Try)]
    need(len(trials)==1,'One accepted financial guarded section')
    body=trials[0].body
    def assignment(node,name):
        return isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets)
    begins=[i for i,n in enumerate(body) if assignment(n,'entry' if policy=='ALL_FLAT' else 'wallet')]
    if policy=='PAIR_TRIM':ends=[i for i,n in enumerate(body) if assignment(n,'receipt')]
    else:ends=[i for i,n in enumerate(body) if isinstance(n,ast.For) and
               ast.unparse(n.iter)=="bound['small_inputs'].items()"]
    need(len(begins)==1,'Unique accepted financial beginning')
    ends=[i for i in ends if i>begins[0]]
    need(len(begins)==len(ends)==1 and begins[0]<ends[0],'Unique accepted financial-only span')
    statements=copy.deepcopy(body[begins[0]:ends[0]])
    original=ast.dump(ast.Module(body=statements,type_ignores=[]),include_attributes=False)
    substitutions={175680:COUNT,732:540,122:90};changes=[]
    for statement in statements:
        for node in ast.walk(statement):
            if isinstance(node,ast.Constant) and type(node.value) is int and node.value in substitutions:
                old=node.value;node.value=substitutions[old]
                changes.append(dict(old=old,new=node.value,line=node.lineno))
    need({r['old'] for r in changes}==set(substitutions),'Each period/count constant is explicitly adapted')
    args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=n) for n in
        ('actual','summary','prices','events','frames','fills','fundrows','daily','report')],
        vararg=None,kwonlyargs=[],kw_defaults=[],kwarg=None,defaults=[])
    function=ast.FunctionDef(name='verify_accepted_financial_block',args=args,
        body=statements+[ast.Return(value=ast.Call(func=ast.Name(id='locals',ctx=ast.Load()),args=[],keywords=[]))],
        decorator_list=[],type_params=[])
    module=ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[]))
    namespace=dict(vars(origin));namespace.update(START=START,END=END,MONTHS=MONTHS,COUNT=COUNT)
    if policy=='PAIR_TRIM':namespace.update(core=core,delta=delta,need=core.need,close=core.close,
        number=core.number,D=core.D,Z=core.ZERO)
    exec(compile(module,str(origin.__file__)+':fixed_90d_financial_only','exec'),namespace)
    return namespace[function.name],dict(origin_path=str(origin.__file__),
        original_financial_AST_sha256=hashlib.sha256(original.encode()).hexdigest(),
        derived_financial_AST_sha256=hashlib.sha256(ast.dump(module,include_attributes=False).encode()).hexdigest(),
        changes=changes,only_integer_period_counts_changed=True,
        start_line=statements[0].lineno,end_line=statements[-1].end_lineno,
        production_simulator_called=False)