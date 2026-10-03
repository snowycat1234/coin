"""D037 startup-only namespace correction; frozen V1 source math unchanged."""
from __future__ import annotations
import ast, hashlib, importlib.util
from copy import deepcopy
from pathlib import Path
from quant.paths import ROOT

V1='scripts/investment/public_daily_official_source.py'
V1_SHA='2d6a06f1e935ff3c39d39c725c9acfc7304a35eda3023810398972a795b6d650'
path=ROOT/V1
if hashlib.sha256(path.read_bytes()).hexdigest()!=V1_SHA:
    raise ValueError('Frozen unexecuted V1 daily source bytes changed')
spec=importlib.util.spec_from_file_location('_d037_original_daily_source_private',path)
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
private=dict(original.__dict__)
private.update(__file__=str(Path(__file__).resolve()),hashlib=hashlib,
    PINS={**original.PINS,V1:V1_SHA})
utility=ROOT/'scripts/investment/bybit_spot_adapter.py'
if hashlib.sha256(utility.read_bytes()).hexdigest()!=original.PINS[utility.relative_to(ROOT).as_posix()]:
    raise ValueError('Accepted exact AST utility changed')
names={'_digest','_one_statement','_ExactPatch','_replace'}
nodes=[n for n in ast.parse(utility.read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
if len(nodes)!=4 or {n.name for n in nodes}!=names:raise ValueError('Exact accepted AST utility definitions')
patch_namespace=dict(ast=ast,deepcopy=deepcopy,hashlib=hashlib)
exec(compile(ast.Module(nodes,type_ignores=[]),str(utility)+'<exact-utilities>','exec'),patch_namespace)
selected={'exact_patch','adapted_functions','main'}
functions=[n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name in selected]
if len(functions)!=3 or {n.name for n in functions}!=selected:raise ValueError('Three private V1 entry/functions only')
tree=ast.Module(functions,type_ignores=[]);changes=[]
tree=patch_namespace['_replace'](tree,changes,'Required stdlib digest in AST helper namespace',
    'namespace=dict(ast=ast,deepcopy=deepcopy)',
    'namespace=dict(ast=ast,deepcopy=deepcopy,hashlib=hashlib)')
exec(compile(ast.fix_missing_locations(tree),str(path)+'<private-V2-stdlib-only>','exec'),private)
if original.exact_patch.__globals__.get('hashlib') is not None:
    raise ValueError('Original V1 module globals unexpectedly modified')
main=private['main']
adapted_functions=private['adapted_functions']
original_data=original.original_data
original_source=original.original_source
PINS=private['PINS']
NAMESPACE_CORRECTION=changes

if __name__=='__main__':main()
