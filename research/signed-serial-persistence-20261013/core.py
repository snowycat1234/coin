"""One frozen signed-serial information comparison; no financial engine."""
from __future__ import annotations
import numpy as np

DAY = 86_400_000_000
STEP = 300_000_000
START = 1_609_459_200_000_000
FIT_AT = 1_672_531_200_000_000
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
CONTROL_NAMES = (
    'R1', 'R5', 'R21', 'BTC_R1', 'BTC_R21', 'ETH_R1', 'ETH_R21',
    'logRV1', 'logRV7', 'logRV30', 'down_share', 'log_sampling_ratio',
    'jump_share', 'R1_down_share', 'R1_jump_share', 'R1_sampling_ratio',
)
ALL_NAMES = CONTROL_NAMES + ('R1_signed_serial',)


def annual_grid(year):
    if year not in (2023, 2024, 2025):
        raise ValueError('Only three fixed old development calendars are allowed')
    left = int(np.datetime64(f'{year}-01-01', 'us').astype(np.int64))
    right = int(np.datetime64(f'{year + 1}-01-01', 'us').astype(np.int64))
    return np.arange(left, right, DAY, dtype=np.int64)


def columns(asset, candidate=False):
    """Structural own/major duplicates are removed before any data is read."""
    omit = {'BTC_R1', 'BTC_R21'} if asset == 0 else (
        {'ETH_R1', 'ETH_R21'} if asset == 1 else set())
    return [i for i, name in enumerate(ALL_NAMES)
            if name not in omit and (candidate or i < len(CONTROL_NAMES))]


def path_statistics(panel, previous, available, real, previous_real):
    p = np.asarray(panel, float)
    prev = np.asarray(previous, float)
    t = np.asarray(available)
    observed = np.asarray(real)
    anchor_real = np.asarray(previous_real)
    if p.ndim != 3 or p.shape[1:] != (288, 5):
        raise ValueError('Exactly 288 five-minute endpoints per CORE5 day')
    if prev.shape != (5,) or t.shape != (len(p),) or t.dtype.kind not in 'iu':
        raise ValueError('Explicit preceding endpoint and integer day clocks required')
    if observed.shape != p.shape or observed.dtype != np.bool_:
        raise ValueError('Explicit real-source Boolean endpoint mask required')
    if anchor_real.shape != (5,) or anchor_real.dtype != np.bool_:
        raise ValueError('Explicit genuine preceding-endpoint mask required')
    if len(t) and (np.any(t % DAY) or np.any(np.diff(t) != DAY)):
        raise ValueError('Exact continuous completed-day grid required')
    leading = np.vstack([prev, p[:-1, -1]])
    leading_real = np.vstack([anchor_real, observed[:-1, -1]])
    valid = observed.all(1) & leading_real & np.isfinite(p).all(1) & (p > 0).all(1)
    valid &= np.isfinite(leading) & (leading > 0)
    safe = np.where(observed & np.isfinite(p) & (p > 0), p, np.nan)
    with np.errstate(invalid='ignore', divide='ignore'):
        r = np.diff(np.log(np.concatenate([leading[:, None], safe], axis=1)), axis=1)
    rv = np.square(r).sum(1)
    rs = np.where(r < 0, np.square(r), 0).sum(1)
    bv = (np.pi / 2) * (288 / 287) * (np.abs(r[:, 1:]) * np.abs(r[:, :-1])).sum(1)
    centered = r - r.mean(1, keepdims=True)
    denominator = np.square(centered).sum(1)
    numerator = (centered[:, 1:] * centered[:, :-1]).sum(1)
    valid &= np.isfinite(r).all(1) & (rv > 0) & (denominator > 0)
    out = {name: np.full((len(p), 5), np.nan) for name in
           ('R1', 'RV', 'down_share', 'jump_share', 'signed_serial')}
    np.copyto(out['R1'], r.sum(1), where=valid)
    np.copyto(out['RV'], rv, where=valid)
    np.divide(rs, rv, out=out['down_share'], where=valid)
    np.divide(np.maximum(rv - bv, 0), rv, out=out['jump_share'], where=valid)
    np.divide(numerator, denominator, out=out['signed_serial'], where=valid)
    if np.any(np.abs(out['signed_serial'][valid]) > 1 + 1e-12):
        raise ValueError('Serial statistic outside Cauchy bound')
    out['ready'] = valid
    return out


def make_features(panel, previous, available, real, rv1m, decisions, previous_real):
    t = np.asarray(available)
    d = np.asarray(decisions)
    one = np.asarray(rv1m, float)
    if d.dtype.kind not in 'iu' or d.ndim != 1 or np.any(d % DAY) or np.any(np.diff(d) != DAY):
        raise ValueError('Every natural decision date, in continuous order')
    if one.shape != (len(t), 5):
        raise ValueError('Source-bound daily one-minute RV required')
    z = path_statistics(panel, previous, t, real, previous_real)
    x = np.full((len(d), 5, len(ALL_NAMES)), np.nan)
    reason = np.full(len(d), 'MISSING_COMPLETED_DAY', dtype='<U32')
    for row, decision in enumerate(d):
        k = int(np.searchsorted(t, decision))
        if k >= len(t) or t[k] != decision:
            continue
        if k < 29:
            reason[row] = 'THIRTY_DAY_WARMUP'
            continue
        # Only prefixes ending at this completed day can affect this decision.
        past = z['RV'][k-29:k+1]
        r = z['R1'][k-29:k+1]
        if not (np.isfinite(past).all() and (past > 0).all() and
                np.isfinite(r).all() and np.isfinite(one[k]).all() and (one[k] > 0).all()):
            reason[row] = 'UNKNOWN_PAST_PATH_OR_RV'
            continue
        R = r[-1]
        R5, R21 = r[-5:].sum(0), r[-21:].sum(0)
        sampling = np.log(one[k] / past[-1])
        down, jump = z['down_share'][k], z['jump_share'][k]
        x[row] = np.column_stack([
            R, R5, R21, np.full(5, R[0]), np.full(5, R21[0]),
            np.full(5, R[1]), np.full(5, R21[1]), np.log(past[-1]),
            np.log(past[-7:].mean(0)), np.log(past.mean(0)), down, sampling,
            jump, R * down, R * jump, R * sampling, R * z['signed_serial'][k],
        ])
        reason[row] = 'READY' if np.isfinite(x[row]).all() else 'UNKNOWN_SERIAL'
    return x, reason


def training_mask(d, x, y, mature, minimum=600):
    d, x, y, mature = map(np.asarray, (d, x, y, mature))
    if x.shape != (len(d), 5, len(ALL_NAMES)) or y.shape != (len(d), 5):
        raise ValueError('Explicit common five-asset feature/price-label shapes')
    if d.dtype.kind not in 'iu' or mature.dtype.kind not in 'iu':
        raise ValueError('Integer clocks required')
    if d.ndim != 1 or np.any(d % DAY) or np.any(np.diff(d) != DAY):
        raise ValueError('Unique continuous natural training calendar required')
    np.testing.assert_array_equal(mature, d + 2 * DAY)
    mask = ((d >= START) & (d < FIT_AT) & (mature < FIT_AT) &
            np.isfinite(x).all((1, 2)) & np.isfinite(y).all(1))
    if int(mask.sum()) < minimum:
        raise ValueError('Insufficient genuine common mature training dates')
    return mask


def fit(d, x, y, mature, minimum=600):
    x, y = np.asarray(x, float), np.asarray(y, float)
    mask = training_mask(d, x, y, mature, minimum)
    indices = np.flatnonzero(mask)
    mean, std = x[mask].mean(0), x[mask].std(0, ddof=1)
    label_std = y[mask].std(0, ddof=1)
    if not (np.isfinite(std).all() and (std > 0).all() and
            np.isfinite(label_std).all() and (label_std > 0).all()):
        raise ValueError('Degenerate train scaling; STOP without rescue')
    scaled = (x[mask] - mean) / std
    models, ranks = {}, {}
    for arm, candidate in [('CONTROL', False), ('CANDIDATE', True)]:
        models[arm], ranks[arm] = [], []
        for asset in range(5):
            selected = columns(asset, candidate)
            design = np.column_stack([np.ones(len(indices)), scaled[:, asset, selected]])
            beta, _, rank, _ = np.linalg.lstsq(design, y[mask, asset], rcond=None)
            if rank != design.shape[1]:
                raise ValueError(f'Rank-deficient {arm}/{SYMBOLS[asset]}; STOP without rescue')
            models[arm].append(beta.tolist())
            ranks[arm].append(int(rank))
    return dict(train_indices=indices.tolist(), maximum_train_maturity_us=int(np.asarray(mature)[mask].max()),
                feature_mean=mean.tolist(), feature_std=std.tolist(), label_std=label_std.tolist(),
                coefficients=models, ranks=ranks, feature_order=list(ALL_NAMES), symbol_order=list(SYMBOLS),
                fit_available_us=FIT_AT, extra_candidate_coefficients=5,
                train_label_mean=y[mask].mean(0).tolist(),
                candidate_X_coefficients=[row[-1] for row in models['CANDIDATE']])


def predict(model, d, x):
    d, x = np.asarray(d), np.asarray(x, float)
    if x.shape != (len(d), 5, len(ALL_NAMES)) or np.any(d < model['fit_available_us']):
        raise ValueError('Model must already be available at each decision')
    if d.dtype.kind not in 'iu' or np.any(d % DAY) or np.any(np.diff(d) != DAY):
        raise ValueError('Natural chronological prediction grid required')
    ready = np.isfinite(x).all((1, 2))
    a = (x[ready] - np.asarray(model['feature_mean'])) / np.asarray(model['feature_std'])
    result = {arm: np.full((len(d), 5), np.nan) for arm in ('CONTROL', 'CANDIDATE')}
    for arm, candidate in [('CONTROL', False), ('CANDIDATE', True)]:
        for asset in range(5):
            design = np.column_stack([np.ones(int(ready.sum())), a[:, asset, columns(asset, candidate)]])
            result[arm][ready, asset] = design @ np.asarray(model['coefficients'][arm][asset])
    return result, ready


def bootstrap(delta, seed=811760):
    a = np.asarray(delta, float)
    if a.ndim != 1 or len(a) < 14:
        raise ValueError('Natural-date joint-five-asset loss difference required')
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(a), (1000, (len(a) + 13) // 14))
    ids = ((starts[:, :, None] + np.arange(14)) % len(a)).reshape(1000, -1)[:, :len(a)]
    sampled = a[ids]
    counts = np.isfinite(sampled).sum(1)
    if np.any(counts == 0):
        raise ValueError('Bootstrap draw has no observed labels; STOP without dropping draw')
    means = np.nansum(sampled, axis=1) / counts
    return np.quantile(means, [.025, .975]).tolist(), starts, means


def score(model, d, x, y, mature, year):
    d, y, mature = np.asarray(d), np.asarray(y, float), np.asarray(mature)
    np.testing.assert_array_equal(d, annual_grid(year))
    np.testing.assert_array_equal(mature, d + 2 * DAY)
    predictions, input_ready = predict(model, d, x)
    outcome_ready = np.isfinite(y).all(1)
    common = input_ready & outcome_ready
    if not common.any():
        raise ValueError('No common observed outcome dates')
    loss = {}
    for arm in predictions:
        loss[arm] = np.square((predictions[arm] - y) / np.asarray(model['label_std']))
    delta = np.full(len(d), np.nan)
    delta[common] = (loss['CONTROL'][common] - loss['CANDIDATE'][common]).mean(1)
    ci, starts, means = bootstrap(delta)
    control = float(loss['CONTROL'][common].mean())
    candidate = float(loss['CANDIDATE'][common].mean())
    gain = 1 - candidate / control
    report = dict(natural_dates=len(d), input_ready_dates=int(input_ready.sum()),
                  common_outcome_dates=int(common.sum()), input_unknown_dates=d[~input_ready].tolist(),
                  outcome_unknown_dates=d[~outcome_ready].tolist(), control_MSE=control,
                  candidate_MSE=candidate, relative_MSE_gain=float(gain), joint_loss_CI=ci,
                  information_gate=bool(common.all() and gain >= .02 and ci[0] > 0),
                  per_asset_loss_improvement=(loss['CONTROL'][common] - loss['CANDIDATE'][common]).mean(0).tolist(),
                  halfyear_loss_improvement={})
    middle = int(np.datetime64(str(year) + '-07-01', 'us').astype(np.int64))
    for name, mask in [('H1', d < middle), ('H2', d >= middle)]:
        chosen = common & mask
        report['halfyear_loss_improvement'][name] = float(np.nanmean(delta[chosen])) if chosen.any() else None
    probes, directions = {}, {}
    for arm in predictions:
        probes[arm], directions[arm] = price_cost_probe(predictions[arm], y)
    economic_delta = np.full(len(d), np.nan)
    economic_delta[common] = (probes['CANDIDATE'][common] - probes['CONTROL'][common]).mean(1)
    economic_ci, economic_starts, economic_means = bootstrap(economic_delta)
    candidate_mean = float(probes['CANDIDATE'][common].mean())
    probe_per_asset = {arm: probes[arm][common].mean(0).tolist() for arm in probes}
    probe_halfyear = {}
    for name, mask in [('H1', d < middle), ('H2', d >= middle)]:
        chosen = common & mask
        probe_halfyear[name] = {
            arm: float(probes[arm][chosen].mean()) if chosen.any() else None for arm in probes}
        probe_halfyear[name]['increment'] = float(np.nanmean(economic_delta[chosen])) if chosen.any() else None
    constant_prediction = np.broadcast_to(np.asarray(model['train_label_mean']), y.shape)
    constant_loss = np.square((constant_prediction - y) / np.asarray(model['label_std']))
    report.update(candidate_price_cost_mean=candidate_mean,
                  training_mean_constant_MSE=float(constant_loss[common].mean()),
                  control_price_cost_mean=float(probes['CONTROL'][common].mean()),
                  price_cost_increment=float(np.nanmean(economic_delta)),
                  price_cost_increment_CI=economic_ci,
                  price_cost_gate=bool(common.all() and candidate_mean > 0 and economic_ci[0] > 0),
                  mechanism_direction_gate=bool(np.mean(model['candidate_X_coefficients']) > 0),
                  price_cost_scope='Independent unit-entry-notional one-day roundtrips; no funding/risk/wallet/capacity/compounding',
                  per_asset_price_cost_mean=probe_per_asset,
                  per_asset_price_cost_increment=(probes['CANDIDATE'][common] - probes['CONTROL'][common]).mean(0).tolist(),
                  halfyear_price_cost_mean=probe_halfyear,
                  directions={arm: {str(value): int((directions[arm][input_ready] == value).sum())
                                    for value in (-1, 0, 1)} for arm in directions})
    report['primary_gate'] = bool(report['information_gate'] and report['price_cost_gate'] and
                                 report['mechanism_direction_gate'])
    return report, dict(decision_us=d, label_mature_us=mature, input_ready=input_ready,
                       outcome_ready=outcome_ready, common=common, target_return=y,
                       control_prediction=predictions['CONTROL'], candidate_prediction=predictions['CANDIDATE'],
                       control_loss=loss['CONTROL'], candidate_loss=loss['CANDIDATE'],
                       constant_prediction=constant_prediction, constant_loss=constant_loss,
                       joint_loss_difference=delta, bootstrap_starts=starts, bootstrap_means=means,
                       control_price_cost_probe=probes['CONTROL'], candidate_price_cost_probe=probes['CANDIDATE'],
                       control_direction=directions['CONTROL'], candidate_direction=directions['CANDIDATE'],
                       price_cost_difference=economic_delta, price_cost_bootstrap_starts=economic_starts,
                       price_cost_bootstrap_means=economic_means)


def price_cost_probe(prediction, actual_return):
    """Paid-price-cost information relevance only; never a portfolio/account."""
    mu, y = np.asarray(prediction, float), np.asarray(actual_return, float)
    if mu.shape != y.shape:
        raise ValueError('Identical owned price-return coordinates required')
    buy = (1 + .0008) * (1 + .00055)
    sell = (1 - .0008) * (1 - .00055)
    expected_long = (1 + mu) * sell - buy
    expected_short = sell - (1 + mu) * buy
    direction = np.zeros(mu.shape, np.int8)
    direction[np.isfinite(mu) & (expected_long > 0)] = 1
    direction[np.isfinite(mu) & (expected_short > 0)] = -1
    value = np.zeros(mu.shape, float)
    value[direction == 1] = ((1 + y) * sell - buy)[direction == 1]
    value[direction == -1] = (sell - (1 + y) * buy)[direction == -1]
    value[~np.isfinite(mu) | ~np.isfinite(y)] = np.nan
    return value, direction
