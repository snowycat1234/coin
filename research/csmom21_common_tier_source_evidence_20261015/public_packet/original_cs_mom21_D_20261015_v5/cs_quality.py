"""Exact original 2022 typed causal carry validation, no old scope or GO."""
import ast
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

import cs_common as c

MINUTE = 60_000_000
_LOADED = None
PATH = c.ROOT / 'traditional_D_full2022_20261015_v2/full_source.py'
PIN = '28071fcc9058fe2f89edffc53f8b02813db5b99a93da13a07ae4a5bef8c009e3'


def original_quality():
    """Execute unchanged QualityCell/validator ASTs, not the old entry module."""
    global _LOADED
    raw = c.exact(PATH, PIN)
    if _LOADED is None:
        tree = ast.parse(raw)
        names = ('QualityCell', 'validate_quality_binding')
        selected = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names]
        if tuple(node.name for node in selected) != names:
            raise ValueError('EXACT_ORIGINAL_2022_QUALITY_AST_INVENTORY_REQUIRED')
        namespace = dict(__name__=__name__, dataclass=dataclass, Decimal=Decimal, MINUTE=MINUTE, digest=c.digest)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(PATH), 'exec'), namespace)
        _LOADED = SimpleNamespace(**{name: namespace[name] for name in names})
    return _LOADED


def quality_cells_2022(sidecar, expected_points, expected_cells_sha):
    old = original_quality()
    if (type(sidecar) is not dict or sidecar.get('quality') != 'UNKNOWN_OR_DERIVED'
            or sidecar.get('arrival_status') != 'UNKNOWN_NOT_CERTIFIED'
            or sidecar.get('derived_mark_cells') != 27 or sidecar.get('certifies_liquidation') is not False
            or sidecar.get('certifies_no_liquidation') is not False
            or sidecar.get('actual_publication_arrival_installation') != 'UNKNOWN_NOT_CERTIFIED'
            or sidecar.get('actual_event_impacts') != 'PENDING_ACTUAL_SAVED_EVIDENCE'):
        raise ValueError('EXACT_2022_UNKNOWN_SOURCE_ONLY_SIDECAR_REQUIRED')
    rows = sidecar.get('cells')
    if type(rows) is not list or c.jsha(rows) != expected_cells_sha:
        raise ValueError('EXACT27_SOURCE_AGE_PROVENANCE_FLAGS_REQUIRED')
    cells = tuple(old.QualityCell(**row) for row in rows)
    old.validate_quality_binding(cells, expected_missing_cells=tuple(tuple(row) for row in expected_points))
    return cells


def intervals(cells):
    by = {}
    for cell in cells:
        by.setdefault(cell.completed_us, set()).add(cell.symbol)
    result = []
    for at, symbols in sorted(by.items()):
        names = tuple(sorted(symbols))
        if result and result[-1][1] == at and result[-1][2] == names:
            result[-1] = (result[-1][0], at + MINUTE, names)
        else:
            result.append((at, at + MINUTE, names))
    return tuple(result)
