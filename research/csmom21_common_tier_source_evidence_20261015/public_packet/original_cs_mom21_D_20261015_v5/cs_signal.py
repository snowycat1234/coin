"""Exact original CS_MOM21 function ASTs. Source code only, no input loading.

The original weekly signal and its original downward-only daily risk sizing
are preserved. CSMOM21_COMMON_TIER is a separately named sizing adaptation.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
DAY = 86_400_000_000
ANCHOR = 1_704_067_200_000_000
SOURCE_PINS = {
    'public_cross_section_momentum.py': '7d6f1794c0ade6e2c2d951a325e4e68ca45be0e87c84c68f05061442fad8a38f',
    'public_sma_perpetual.py': 'c9fe8a916f300e91396dba70948ab44348b947ec333d7c82b8429db36e064e18',
    'portfolio.py': 'e4e02b0204e2861bb44eb78c8069b13a09edf6ca9390f3c86490d6e6f8a5e68b',
}
GRID_PATH = ROOT / 'traditional_three_tier_freeze_20261015/frozen_grid.py'
GRID_SHA256 = 'a64abec4b396b17ff1e93bbc95ad77c6a76a26e54ecdf36bb5c9ddaedac6b8f1'
_ORIGINAL = _GRID = None


def originals():
    """Load only exact function ASTs; do not import a research runner."""
    global _ORIGINAL
    selections = (
        ('public_sma_perpetual.py', ('require', 'symbol_order', 'signed_risk_weights')),
        ('portfolio.py', ('market_neutral',)),
        ('public_cross_section_momentum.py', ('public_targets',)),
    )
    for name, expected in SOURCE_PINS.items():
        path = HERE / 'sources/reference' / name
        if path.is_symlink() or sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('EXACT_ORIGINAL_CS_SOURCE_REQUIRED:' + name)
    if _ORIGINAL is None:
        ns = dict(np=np, DAY_US=DAY, WEEK_US=7 * DAY, ANCHOR_US=ANCHOR)
        for name, names in selections:
            path = HERE / 'sources/reference' / name
            selected = [node for node in ast.parse(path.read_text()).body
                        if isinstance(node, ast.FunctionDef) and node.name in names]
            if tuple(node.name for node in selected) != names:
                raise ValueError('EXACT_ORIGINAL_CS_FUNCTION_INVENTORY_REQUIRED')
            exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), ns)
        if ns['public_targets'].__kwdefaults__ != {'short_absolute_confirmation': False}:
            raise ValueError('ORIGINAL_UNFILTERED_CS_DEFAULT_REQUIRED')
        _ORIGINAL = SimpleNamespace(**{name: ns[name] for _, names in selections for name in names})
    return _ORIGINAL


def common_grid():
    """Execute only exact common-tier math ASTs, with no account/import seams."""
    global _GRID
    if GRID_PATH.is_symlink() or sha256(GRID_PATH.read_bytes()).hexdigest() != GRID_SHA256:
        raise ValueError('EXACT_CURRENT_COMMON_TIER_SOURCE_REQUIRED')
    if _GRID is None:
        tree = ast.parse(GRID_PATH.read_text())
        names = ('Tier', 'tier_named', '_covariance', 'scale_to_tier')
        selected = []
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names:
                selected.append(node)
            elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'TIERS' for target in node.targets):
                selected.append(node)
        namespace = dict(np=np, dataclass=dataclass, __name__=__name__)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(GRID_PATH), 'exec'), namespace)
        _GRID = SimpleNamespace(**{name: namespace[name] for name in (*names, 'TIERS')})
    return _GRID


def project_arrays(close, close_us, available_us, decisions):
    """Pure in-memory projection, used by generated and gated source stages.

    There is deliberately no file/provider/history/actual-source API here.
    Authority is owned by cs_entry, never by this pure mathematical function.
    """
    p = np.asarray(close, dtype=np.float64)
    t, a, d = (np.asarray(x) for x in (close_us, available_us, decisions))
    for clock in (t, a, d):
        if (clock.ndim != 1 or clock.dtype.kind not in 'iu' or not len(clock)
                or np.any(clock > np.iinfo(np.int64).max) or np.any(clock < 0)
                or np.any(clock % DAY) or np.any(np.diff(clock.astype(np.int64)) != DAY)):
            raise ValueError('COMPLETE_UTC_DAILY_INTEGER_CLOCKS_REQUIRED')
    if p.shape != (len(t), 5) or a.shape != t.shape or not np.array_equal(t, a):
        raise ValueError('EXACT_COMPLETED_CLOSE_AVAILABILITY_REQUIRED')
    if not np.isfinite(p).all() or np.any(p <= 0):
        raise ValueError('NO_MISSING_IMPUTED_OR_NONPOSITIVE_CLOSES')
    # No keyword override: this executes the exact original False default.
    original_sized, diag = originals().public_targets(p, a, d, SYMBOLS, SYMBOLS)
    if diag.get('momentum_days') != 21 or diag.get('weekly_anchor_us') != ANCHOR:
        raise ValueError('UNCHANGED_ORIGINAL_CS21_DEFAULT_PROVENANCE_REQUIRED')
    raw = np.empty_like(original_sized)
    rank_events = {row['rank_us']: row for row in diag['rank_events']}
    covariance, proofs = [], []
    targets = {tier: np.empty_like(original_sized) for tier in ('LOW', 'MID', 'HIGH')}
    for i, at in enumerate(d):
        k = int(np.searchsorted(t, at))
        if (k < 199 or k >= len(t) or t[k] != at
                or not all(diag['current_eligible'][i])):
            raise ValueError('SHARED_FULL_FIVE_200_COMPLETED_CLOSE_ADMISSION_REQUIRED')
        raw[i] = rank_events[diag['rank_us'][i]]['raw_weights']
        raw[i, ~np.asarray(diag['current_eligible'][i], dtype=bool)] = 0.
        past = p[k - 30:k + 1]
        returns = np.diff(past, axis=0) / past[:-1]
        cov = common_grid()._covariance(np.cov(returns, rowvar=False, ddof=1) * 365)
        covariance.append(cov)
        proof = {'decision_us': int(at), 'last_close_available_us': int(a[k]),
                 'oldest_admitted_close_available_us': int(a[k - 199]),
                 'rank_us': int(diag['rank_us'][i]), 'tiers': {}}
        for tier in targets:
            targets[tier][i], proof['tiers'][tier] = common_grid().scale_to_tier(original_sized[i], cov, tier)
        proofs.append(proof)
    return raw, original_sized, targets, np.stack(covariance), diag, proofs
