"""D037 startup-only Path bridge; original source format/math unchanged."""
from __future__ import annotations
import ast, hashlib, importlib.util
from pathlib import Path
from quant.paths import ROOT

V2='scripts/investment/public_daily_official_source_v2.py'
V2_SHA='079bc2ec5cf635afdc9b277aa3dbbc8f2cdaad520537a04b8275d16e49bfa83d'
path=ROOT/V2
if hashlib.sha256(path.read_bytes()).hexdigest()!=V2_SHA:
    raise ValueError('Frozen V2 namespace correction source changed')
spec=importlib.util.spec_from_file_location('_d037_daily_source_v2_private_reuse',path)
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
private=dict(original.private)
private.update(__file__=str(Path(__file__).resolve()),
    PINS={**original.PINS,V2:V2_SHA},
    sha=lambda value:original.original_data.sha256_file(Path(value)))
base=ROOT/original.V1
nodes=[n for n in ast.parse(base.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='main']
if len(nodes)!=1:raise ValueError('One unchanged frozen main function')
exec(compile(ast.Module(nodes,type_ignores=[]),str(base)+'<private-V3-Path-only>','exec'),private)
if original.private['sha'] is not original.original_data.sha256_file:
    raise ValueError('Original V2 globals unexpectedly modified')
main=private['main']
PINS=private['PINS']
PATH_NORMALIZATION_ONLY=True

if __name__=='__main__':main()
