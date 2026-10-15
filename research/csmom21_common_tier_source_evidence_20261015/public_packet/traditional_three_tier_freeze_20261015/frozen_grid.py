"""Fixed source-bound 3 x 3 traditional-strategy DEVELOPMENT grid.

No history loading, wallet loop, fitting, outcome selection or publication.
Canonical functions are loaded by the unchanged published source-only loader.
The new tier scaler is an explicit parameterization of risk_budget.scale,
not a replacement for the native scheduler or a historical execution GO.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as D
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

import numpy as np

HERE = Path(__file__).resolve().parent
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
DAY = 86_400_000_000
STRATEGIES = ('STATIC50', 'H090', 'VOL_MANAGED_HOLD')
VERSION = 'TRADITIONAL_THREE_BY_THREE_SEEN_DEV_V1'
SOURCE_PROVENANCE_SHA256 = 'ef36bee5b7c6d8dbef5ebd10f604b00a2f46aeceab88d848b958b4212416df56'


@dataclass(frozen=True)
class Tier:
    name: str
    gross_cap: float
    annual_vol_target: float
    asset_cap: float = .30


TIERS = (Tier('LOW', .30, .05), Tier('MID', .60, .10), Tier('HIGH', .90, .15))
CONFIGS = tuple((strategy, tier.name) for strategy in STRATEGIES for tier in TIERS)


def tier_named(name):
    for tier in TIERS:
        if name == tier.name:
            return tier
    raise ValueError('EXACT_FIXED_LOW_MID_HIGH_TIER_REQUIRED')


def verify_sources():
    raw = (HERE / 'SOURCE_PROVENANCE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_PROVENANCE_SHA256:
        raise ValueError('SOURCE_PROVENANCE_FREEZE_CHANGED')
    records = json.loads(raw)
    for row in records:
        path = HERE / row['path']
        if path.is_symlink() or not path.is_file():
            raise ValueError('ORDINARY_FROZEN_PUBLIC_SOURCE_REQUIRED')
        body = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
        if (len(body) != row['bytes'] or hashlib.sha256(body).hexdigest() != row['SHA256']
                or blob != row['GitBlobSHA1']):
            raise ValueError('PUBLIC_SOURCE_BYTES_CHANGED:' + row['path'])
    return records


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_ORIGINALS = _H090 = _VENDOR = None


def originals():
    global _ORIGINALS
    verify_sources()
    if _ORIGINALS is None:
        loader = _load('_traditional_exact_original_loader', HERE / 'sources/original_functions.py')
        _ORIGINALS = loader.load_originals(HERE / 'sources')
    return _ORIGINALS


def _h090():
    global _H090
    verify_sources()
    if _H090 is None:
        _H090 = _load('_traditional_exact_h090_source', HERE / 'sources/h090_risk_controller.py')
    return _H090


def _vendor():
    global _VENDOR
    verify_sources()
    if _VENDOR is None:
        name = '_traditional_exact_vendor'
        package = types.ModuleType(name)
        package.__path__ = [str(HERE / 'sources/vendor_quant')]
        sys.modules[name] = package
        _load(name + '.execution_contract', HERE / 'sources/vendor_quant/execution_contract.py')
        _VENDOR = _load(name + '.perpetual_account', HERE / 'sources/vendor_quant/perpetual_account.py')
    return _VENDOR


def _covariance(covariance):
    c = np.asarray(covariance, dtype=np.float64)
    if c.shape != (5, 5) or not np.isfinite(c).all():
        raise ValueError('FINITE_ORDERED_CORE5_COVARIANCE_REQUIRED')
    if not np.allclose(c, c.T, rtol=0, atol=1e-14):
        raise ValueError('SYMMETRIC_COVARIANCE_REQUIRED')
    if np.linalg.eigvalsh(c).min() < -1e-12:
        raise ValueError('NON_PSD_COVARIANCE')
    return c


def scale_to_tier(weight, covariance, tier_name):
    """Uniform retargeting, preserving canonical signed proportions.

    Same desired/cap minimum as original risk_budget.scale. Changes: explicit
    fixed tier arguments; input may be an already canonical H090 intent≤.90;
    covariance/overflow checks fail closed. No per-leg clipping is added here.
    """
    tier = tier_named(tier_name)
    w = np.asarray(weight, dtype=np.float64)
    c = _covariance(covariance)
    if w.shape != (5,) or not np.isfinite(w).all():
        raise ValueError('FINITE_ORDERED_CORE5_INTENT_REQUIRED')
    gross, largest = float(np.abs(w).sum()), float(np.abs(w).max())
    if gross > .90 + 1e-12 or largest > .30 + 1e-12:
        raise ValueError('CANONICAL_INTENT_ENVELOPE_EXCEEDED')
    variance = float(w @ c @ w)
    if not np.isfinite(variance) or variance < -1e-15:
        raise ValueError('INVALID_COVARIANCE_RISK')
    sigma = float(np.sqrt(max(0., variance)))
    if gross == 0:
        return w.copy(), dict(raw_sigma=0., factor=0., post_sigma=0.,
            cap_bound=False, risk_target_met=False, shortfall=tier.annual_vol_target,
            reason='INTRINSIC_CASH', gross=0., largest=0.)
    if sigma <= 1e-12:
        raise ValueError('NONZERO_INTENT_WITH_DEGENERATE_RISK')
    desired = tier.annual_vol_target / sigma
    cap_factor = min(tier.asset_cap / largest, tier.gross_cap / gross)
    factor = min(desired, cap_factor)
    if abs(factor - 1.) <= 1e-12:
        factor = 1.
    out = w * factor
    post = float(np.sqrt(max(0., out @ c @ out)))
    if (not np.isfinite(out).all() or not np.isfinite(post)
            or np.abs(out).max() > tier.asset_cap + 1e-12
            or np.abs(out).sum() > tier.gross_cap + 1e-12
            or post > tier.annual_vol_target + 1e-12):
        raise ValueError('POST_SCALE_RISK_CAP_FAILED')
    cap_bound = bool(cap_factor < desired - 1e-12)
    return out, dict(raw_sigma=sigma, desired_factor=desired, cap_factor=cap_factor,
        factor=factor, post_sigma=post, cap_bound=cap_bound,
        risk_target_met=bool(abs(post - tier.annual_vol_target) <= 1e-12),
        shortfall=max(0., tier.annual_vol_target - post),
        reason='CAP_BOUND' if cap_bound else 'RISK_TARGET_MET',
        gross=float(np.abs(out).sum()), largest=float(np.abs(out).max()))


def canonical_intents(cs_original, past_returns):
    """Exact target-builder equations, before the new tier parameterization.

    STATIC50 is the later portfolio-risk-retargeted canonical .60/.30/.10
    version. The older no-reexpansion mixture is retained as a separate field.
    H090 is formed exactly once from 1.5 * canonical STATIC50, followed by the
    original H090 clip -> gross shrink -> volatility shrink order.
    VOL_MANAGED_HOLD is original constant-long equal CORE5, not inverse vol.
    """
    o = originals()
    r = np.asarray(past_returns, dtype=np.float64)
    cs = np.asarray(cs_original, dtype=np.float64)
    if r.shape != (30, 5) or not np.isfinite(r).all() or cs.shape != (5,):
        raise ValueError('EXACT30_CORE5_RETURNS_AND_CS_REQUIRED')
    if (not np.isfinite(cs).all() or np.abs(cs).max() > .30 + 1e-12
            or np.abs(cs).sum() > .60 + 1e-12):
        raise ValueError('ORIGINAL_CS_TARGET_ENVELOPE')
    cov = _covariance(np.cov(r, rowvar=False, ddof=1) * 365)
    hold, _ = o.signed_risk_weights(np.full(5, .6 / 5), r)
    sigma = lambda w: float(np.sqrt(max(0., w @ cov @ w)))
    sc, sh = sigma(cs), sigma(hold)
    common = min(.10, sc, sh)
    # Generic original match() handles a complete but intrinsically zero-risk
    # CS signal as cash. The old episode builder's nonzero-sigma assertion was
    # narrower than the published reusable matching function.
    old_cs = cs * (common / sc) if sc > 0 else np.zeros(5)
    old_hold = hold * (common / sh) if sh > 0 else np.zeros(5)
    old_static = .5 * old_cs + .5 * old_hold
    static, static_proof = o.scale(old_static, cov)
    h090, hproof, hc = _h090()._math(1.5 * static, r, .90, .30, .15)
    if not np.array_equal(cov, hc):
        raise ValueError('H090_COVARIANCE_MUST_MATCH_ORIGINAL')
    return {'STATIC50': static, 'H090': h090, 'VOL_MANAGED_HOLD': hold}, cov, {
        'STATIC50_OLD_NO_REEXPANSION': old_static.tolist(),
        'STATIC50_CANONICAL_RETARGETED': static_proof,
        'H090_ORIGINAL_ONCE_ONLY': hproof,
        'common_matched_sigma': common,
        'new_alpha_claim': False}


def build_target_grid(close, close_us, available_us, decisions, *, symbols=SYMBOLS):
    """Build nine deterministic targets from in-memory causal daily prices.

    This API does not open input files or generate financial outcomes. It uses
    the exact canonical builder's full-five 200-completed-close readiness.
    Source provenance and historical account integration remain separate gates.
    """
    if tuple(symbols) != SYMBOLS:
        raise ValueError('EXACT_CORE5_ORDER_REQUIRED')
    p = np.asarray(close, dtype=np.float64)
    t, a, d = (np.asarray(x) for x in (close_us, available_us, decisions))
    for clock in (t, a, d):
        if (clock.ndim != 1 or clock.dtype.kind not in 'iu' or not len(clock)
                or np.any(clock > np.iinfo(np.int64).max) or np.any(clock < 0)
                or np.any(clock % DAY) or np.any(np.diff(clock.astype(np.int64)) != DAY)):
            raise ValueError('COMPLETE_UTC_DAILY_INTEGER_CLOCKS_REQUIRED')
    if p.shape != (len(t), 5) or a.shape != t.shape or not np.array_equal(a, t):
        raise ValueError('EXACT_ORIGINAL_COMPLETED_CLOSE_AVAILABILITY_NAMESPACE')
    if not np.isfinite(p).all() or (p <= 0).any():
        raise ValueError('NO_MISSING_IMPUTED_OR_NONPOSITIVE_CLOSES')
    cs, diagnostic = originals().public_targets(p, a, d, SYMBOLS, SYMBOLS)
    eligible = np.asarray(diagnostic['current_eligible'], dtype=bool)
    out = {strategy + '_' + tier: np.empty((len(d), 5)) for strategy, tier in CONFIGS}
    covariances, proofs = [], []
    for i, at in enumerate(d):
        k = int(np.searchsorted(t, at))
        if k < 199 or k >= len(t) or t[k] != at or not eligible[i].all():
            raise ValueError('ORIGINAL_FULL_FIVE_200_COMPLETED_CLOSE_ADMISSION')
        past = p[k-30:k+1]
        returns = np.diff(past, axis=0) / past[:-1]
        intents, covariance, canonical = canonical_intents(cs[i], returns)
        proof = {'decision_us': int(at), 'last_close_available_us': int(a[k]),
            'oldest_close_available_us': int(a[k-199]), 'canonical': canonical, 'tiers': {}}
        for strategy, tier in CONFIGS:
            key = strategy + '_' + tier
            out[key][i], proof['tiers'][key] = scale_to_tier(intents[strategy], covariance, tier)
        covariances.append(covariance)
        proofs.append(proof)
    return d.astype(np.int64), out, np.stack(covariances), proofs


def target_identities(decisions, targets):
    """Exact whole-calendar dedup; numerical similarity never authorizes reuse."""
    d = np.asarray(decisions, dtype='<i8')
    expected = {strategy + '_' + tier for strategy, tier in CONFIGS}
    if set(targets) != expected:
        raise ValueError('EXACT_NINE_TARGET_KEYS_REQUIRED')
    identity, representatives, groups = {}, {}, {}
    namespace = json.dumps(list(SYMBOLS), separators=(',', ':')).encode() + d.tobytes()
    for key in sorted(targets):
        array = np.asarray(targets[key], dtype='<f8')
        if array.shape != (len(d), 5) or not np.isfinite(array).all():
            raise ValueError('COMPLETE_FINITE_NINE_TARGET_ARRAYS')
        digest = hashlib.sha256(namespace + array.tobytes()).hexdigest()
        identity[key] = digest
        rep = representatives.setdefault(digest, key)
        groups.setdefault(rep, []).append(key)
    return {'SHA256_by_config': identity, 'exact_target_equality_groups': list(groups.values()),
        'distinct_target_paths': len(groups), 'independent_alpha_families_claimed': False,
        'execution_reuse_authorized_by_target_equality': False}


def execution_reuse_groups(decisions, targets, *, source_identity, cost_name, execution_identity):
    """Same tier, source, costs, native code and exact targets are all required."""
    for digest in (source_identity, execution_identity):
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('EXACT_SOURCE_AND_EXECUTION_HASHES_REQUIRED')
    if cost_name not in ('BASE27', 'STRESS43'):
        raise ValueError('FIXED_COMMON_COST_SCENARIO_REQUIRED')
    target_info = target_identities(decisions, targets)
    groups = {}
    for strategy, tier in CONFIGS:
        key = strategy + '_' + tier
        binding = (target_info['SHA256_by_config'][key], tier, source_identity,
                   cost_name, execution_identity, VERSION)
        groups.setdefault(binding, []).append(key)
    return list(groups.values())


def make_account(tier_name, cost_name='BASE27'):
    """Same exact public Decimal engine for every tier; generated/offline only.

    Only declarative caps and honest contract metadata vary. Financial methods
    remain inherited and byte-identical. The common old quantity-grid profile
    is retained; native-exchange/filter certification is explicitly absent.
    """
    tier = tier_named(tier_name)
    if cost_name not in ('BASE27', 'STRESS43'):
        raise ValueError('FIXED_COMMON_COST_SCENARIO_REQUIRED')
    engine = _vendor()
    friction = '4' if cost_name == 'BASE27' else '8'
    config = engine.PerpetualConfig(initial_cash='10000', max_gross_weight=str(tier.gross_cap),
        max_asset_weight='.30', leverage='1', half_spread_bps=friction, slippage_bps=friction)
    profile = json.loads((HERE / 'sources/QUANTITY_PROFILE.json').read_text())
    profiles = {s: engine.InstrumentProfile(quantity_step=profile['rows'][s]['quantity_step'],
        min_notional='10') for s in SYMBOLS}
    account = engine.USDTLinearPerpetualAccount(config, symbols=SYMBOLS,
        instrument_profiles=profiles, closing_min_notional_exempt=True)
    return account


def account_contract(tier_name, cost_name='BASE27'):
    """External policy binding, without overwriting inherited contract claims."""
    tier = tier_named(tier_name)
    return {'schema': VERSION, 'tier': tier_name, 'gross_cap': tier.gross_cap,
        'asset_cap': tier.asset_cap, 'annual_vol_target_external_controller': tier.annual_vol_target,
        'annual_vol_actual_fill_guard_status': 'NOT_INTEGRATED_FOR_NEW_GRID',
        'account': make_account(tier_name, cost_name).contract_metadata(),
        'native_venue_certified': False, 'historical_execution_status': 'NO_GO_PENDING_INTEGRATION'}


def require_historical_execution():
    raise RuntimeError('NO_GO_NEW_GRID_NATIVE_SCHEDULER_FRESH_FILL_RISK_SOURCE_AND_RESOURCE_GATES_PENDING')
