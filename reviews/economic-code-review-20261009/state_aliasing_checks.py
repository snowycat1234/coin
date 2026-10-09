"""Two structural witnesses using exact mapper/CS source; no fits or wallets."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
for name in ('native-root', 'temporal-root', 'prototype', 'original-portfolio', 'output'):
    parser.add_argument('--'+name, type=Path, required=True)
parser.add_argument('--h1-context', type=Path)
args = parser.parse_args()
HERE = Path(__file__).resolve().parent
PROTOTYPE = args.prototype
assert hashlib.sha256(PROTOTYPE.read_bytes()).hexdigest() == '46a0ca0b76bf29d50133bdd85b5730f4fd029f05378ce2ef086752b869a8fcab'
spec = importlib.util.spec_from_file_location('review_original_mapper', PROTOTYPE)
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)
day = p.DAY_US
stamp = 1_704_067_200_000_000
expert = np.zeros((5, 5))
expert[1] = .12
expert[4] = [.15, .15, -.15, -.15, 0]
c = p.Context(stamp, stamp, expert, np.ones(5, bool),
    np.sin(np.arange(30)[:, None] + np.arange(5)[None]) * .002,
    np.zeros(13), np.full(5, stamp, np.int64))
histories = []
for selected in (1, 4):
    prior = np.array([1., 0, 0, 0, 0])
    request = np.eye(5)[selected]
    for _ in range(21):
        prior = p.map_budget(prior, request, c)['budget']
    assert np.allclose(prior, request, atol=1e-14, rtol=0)
    current_request = np.array([0., .5, 0, 0, .5])
    mapped = p.map_budget(prior, current_request, c)
    expected_budget = np.array([0., .95, 0, 0, .05]) if selected == 1 else np.array([0., .05, 0, 0, .95])
    assert np.allclose(mapped['budget'], expected_budget, atol=1e-14, rtol=0)
    assert np.allclose(mapped['targets'], expected_budget @ expert, atol=1e-14, rtol=0)
    histories.append(dict(history='21 VOL requests' if selected == 1 else '21 CS requests',
        prior=prior.tolist(), identical_current_request=current_request.tolist(),
        mapped_budget=mapped['budget'].tolist(), mapped_targets=mapped['targets'].tolist()))

# Time-translation preserves every existing market feature value, but the
# fixed CS weekly anchor changes the active ranking date. No calendar feature
# is forwarded by the Selector.
native, temporal = args.native_root.resolve(), args.temporal_root.resolve()
source_hashes = {
    native/'scripts/research/public_cross_section_momentum.py': '7d6f1794c0ade6e2c2d951a325e4e68ca45be0e87c84c68f05061442fad8a38f',
    native/'scripts/investment/public_sma_perpetual.py': 'c9fe8a916f300e91396dba70948ab44348b947ec333d7c82b8429db36e064e18',
    temporal/'modules/temporal_two_expert/model.py': '6ab473b139356c750457991961758bdd450e872d1779d58cfa7a9e09b50ef8a2',
    args.original_portfolio: 'e4e02b0204e2861bb44eb78c8069b13a09edf6ca9390f3c86490d6e6f8a5e68b',
}
for path, expected in source_hashes.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, str(path)
os.environ['QUANT_ROOT'] = str(native)
sys.path[:0] = [str(native/'src'), str(native), str(temporal)]
spec = importlib.util.spec_from_file_location('modules.transformer_v2.portfolio', args.original_portfolio)
portfolio = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = portfolio
spec.loader.exec_module(portfolio)
from scripts.research.public_cross_section_momentum import public_targets, ANCHOR_US

n = 265
returns = np.tile([.0003, .0002, .0001, -.0001, -.0002], (n-1, 1))
returns[-3:, 0] = -.01
returns[-3:, 4] = .01
prices = np.vstack([np.full(5, 100.), 100. * np.cumprod(1 + returns, axis=0)])
clocks = ANCHOR_US + 280*day - (n-1)*day + np.arange(n, dtype=np.int64)*day
phase_records = []
for shift in (0, 3):
    times = clocks + shift*day
    targets, diagnostic = public_targets(prices, times, times[-1:], p.CORE5, p.CORE5)
    raw = np.asarray(diagnostic['rank_events'][-1]['raw_weights'])
    expected = [-.15, .15, 0, -.15, .15] if shift == 0 else [.15, .15, 0, -.15, -.15]
    assert np.array_equal(raw, expected), raw
    phase_records.append(dict(calendar_shift_days=shift, decision_us=int(times[-1]),
        rank_age_days=int((times[-1] - diagnostic['rank_us'][-1])/day), raw=raw.tolist(), targets=targets[0].tolist()))
assert not np.array_equal(phase_records[0]['targets'], phase_records[1]['targets'])

# Bind the recipe witness to the retained original H1 context arrays. The
# arbitrary starting price100 preserves every simple return, covariance and
# cross-sectional21-day score. The first30 returns do not necessarily provide
# the 30-return context of the prior weekly ranking; inspect only dates after
# the first weekly rank with a fully reconstructed context for source parity.
binding = dict(status='NOT_RUN_NO_OPTIONAL_H1_CONTEXT_PROVIDED')
if args.h1_context is not None:
    original = args.h1_context
    assert original.stat().st_size < 4*2**20
    assert hashlib.sha256(original.read_bytes()).hexdigest() == 'c13de3125698f1fc350d1435453cbb6e33b7d5873537d7f859c1570344f081bc'
    with np.load(original, allow_pickle=False) as z:
        original_dates = z['decision_us'].copy()
        original_past = z['past_returns30'].copy()
        original_targets = z['expert_targets'].copy()
        original_order = z['expert_order'].tolist()
    assert original_order == list(p.E5)
    assert original_past.shape == (61, 30, 5)
    assert np.array_equal(original_past[1:, :-1], original_past[:-1, 1:])
    joined_returns = np.vstack([original_past[0], original_past[1:, -1]])
    joined_prices = np.vstack([np.full(5, 100.), 100. * np.cumprod(1 + joined_returns, axis=0)])
    joined_dates = np.arange(original_dates[0]-30*day, original_dates[-1]+day, day, dtype=np.int64)
    regenerated_CS, _ = public_targets(joined_prices, joined_dates, original_dates, p.CORE5, p.CORE5)
    maximum_CS_error = float(np.max(np.abs(regenerated_CS-original_targets[:, 4])))
    first_complete_rank = ANCHOR_US + ((int(joined_dates[30])-ANCHOR_US+7*day-1)//(7*day))*(7*day)
    reconstructed_rank_mask = original_dates >= first_complete_rank
    maximum_CS_error_after_complete_rank = float(np.max(np.abs(regenerated_CS[reconstructed_rank_mask]-original_targets[reconstructed_rank_mask, 4])))
    from scripts.investment.public_sma_perpetual import signed_risk_weights
    regenerated_VOL = np.array([signed_risk_weights(np.full(5, .12), r)[0] for r in original_past])
    maximum_VOL_error = float(np.max(np.abs(regenerated_VOL-original_targets[:, 1])))
    signs = np.sign(original_targets[:, 4])
    changed = np.flatnonzero(np.any(signs[1:] != signs[:-1], axis=1))+1
    weekly_phase = ((original_dates[changed]-ANCHOR_US)//day % 7)
    assert reconstructed_rank_mask.sum() == 56
    assert maximum_CS_error_after_complete_rank < 1e-12
    assert maximum_VOL_error < 1e-12
    assert len(changed) == 8 and np.all(weekly_phase == 0)
    binding_status = ('MATCH' if maximum_CS_error<1e-12 and maximum_VOL_error<1e-12 else
        'PARTIAL_MATCH_AFTER_FIRST_RECONSTRUCTIBLE_WEEKLY_RANK' if maximum_CS_error_after_complete_rank<1e-12 and maximum_VOL_error<1e-12 else
        'RECIPE_RECONSTRUCTION_MISMATCH_NOT_CANONICAL_IDENTITY_PROOF')
    binding = dict(status=binding_status,
        context_sha256=hashlib.sha256(original.read_bytes()).hexdigest(), expert_order=original_order,
        dates=61, exact_overlapping_past_returns=True, maximum_CS_target_error=maximum_CS_error,
        first_complete_reconstructed_rank_us=int(first_complete_rank),
        dates_after_complete_reconstructed_rank=int(reconstructed_rank_mask.sum()),
        maximum_CS_target_error_after_complete_reconstructed_rank=maximum_CS_error_after_complete_rank,
        maximum_VOL_target_error=maximum_VOL_error,
        original_CS_nonzero_counts=np.count_nonzero(original_targets[:, 4], axis=1).tolist(),
        original_CS_sign_change_indices=changed.tolist(),
        original_CS_sign_change_weekly_phase=weekly_phase.tolist(),
        first_original_CS=original_targets[0, 4].tolist(), first_regenerated_CS=regenerated_CS[0].tolist(),
        source_container='H1_VALIDATE fragment, distinct from native H1_E5_INPUTS container')

result = dict(status='VERIFIED_STATE_ALIASING_WITNESSES_NOT_A_PERFORMANCE_OR_BUG_CLAIM',
    mapper_sha256=hashlib.sha256(PROTOTYPE.read_bytes()).hexdigest(),
    CS_source_commit='55ac3d2ee730b1cd1381696330a6abaf1925eb92',
    mapper_histories=histories,
    same_market_different_calendar_CS=phase_records,
    retained_H1_recipe_binding=binding,
    parameter_or_training_changes=0, simulated_wallets=0,
    limits=['Counterfactual request histories; not a measured collision on one fixed trained policy.',
            'Calendar witness uses pinned55ac public CS recipe. Optional retained H1 reconstruction cannot initialize the prior weekly rank for its first five dates; numerical identity is checked only after the first complete reconstructed weekly rank. The retained source container differs from canonical H1_E5_INPUTS.',
            'Does not establish that wallet/expert-state additions improve generalization; prior HGB failure remains relevant.'])
print(json.dumps(result, indent=2))
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2)+'\n')
