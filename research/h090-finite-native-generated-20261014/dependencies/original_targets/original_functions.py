"""Execute exact original function ASTs with only their declared numpy inputs.

No full research runner, Ridge, labels, fitting or wallet is imported. Function
bodies and defaults are unchanged. Original complete source files are retained.
"""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import types
import numpy as np

HERE = Path(__file__).resolve().parent
DAY = 86_400_000_000
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_originals(root=HERE):
    root = Path(root)
    manifest = json.loads((root / 'ORIGINAL_REFERENCE.json').read_text())
    if len(manifest) != 6:
        raise ValueError('Exact six-source original closure required')
    sources = {}
    for rec in manifest:
        p = root / rec['local_locator']
        if p.is_symlink() or sha(p) != rec['SHA256'] or p.stat().st_size != rec['bytes']:
            raise ValueError('Original target source changed: ' + rec['local_locator'])
        sources[p.name] = p
    ns = dict(np=np, DAY=DAY, DAY_US=DAY, WEEK_US=7*DAY,
              ANCHOR_US=1_704_067_200_000_000, SYMBOLS=SYMBOLS,
              EXPERTS=('SMA200_SIGNED','CSMOM21_CORE5','HOLD','CASH'),
              ARMS=('CS_MATCHED','VOL_MATCHED','STATIC50'),
              ANNUAL_BUDGET=.10, ASSET_CAP=.30, GROSS_CAP=.60)
    selections = (
        ('public_sma_perpetual.py', ('require', 'symbol_order', 'signed_risk_weights')),
        ('portfolio.py', ('market_neutral',)),
        ('public_cross_section_momentum.py', ('public_targets',)),
        ('joint_expert_information.py', ('signed_intents',)),
        ('match_core.py', ('match',)),
        ('risk_budget.py', ('scale', 'allocate')),
    )
    for name, functions in selections:
        p = sources[name]
        tree = ast.parse(p.read_text(), filename=str(p))
        selected = [node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name in functions]
        if tuple(node.name for node in selected) != functions:
            raise ValueError('Original function inventory changed: ' + name)
        exec(compile(ast.Module(body=selected,type_ignores=[]), str(p), 'exec'), ns)
    return types.SimpleNamespace(**{name: ns[name] for _, names in selections for name in names})
