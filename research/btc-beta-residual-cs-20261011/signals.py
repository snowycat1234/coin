"""One causal84d BTC regression, two ranks, one shared hedge/risk rule."""
import numpy as np
from modules.transformer_v2.portfolio import market_neutral
from scripts.investment.public_sma_perpetual import signed_risk_weights

DAY = 86_400_000_000
WEEK = 7 * DAY
ANCHOR = 1_704_067_200_000_000
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')


def context(prices, clocks, decision, symbols=SYMBOLS):
    names = tuple(symbols)
    if len(names) != 5 or set(names) != set(SYMBOLS):
        raise ValueError('Exact CORE5 ordered identity required')
    k = int(np.searchsorted(clocks, decision, side='right')) - 1
    if k < 84 or clocks[k] != decision or np.any(np.diff(clocks[k - 84:k + 1]) != DAY):
        return None
    p = prices[k - 84:k + 1]
    if not np.isfinite(p).all() or np.any(p <= 0):
        return None
    r = np.diff(np.log(p), axis=0)
    market = names.index('BTCUSDT')
    x = r[:, market]
    centered = x - x.mean()
    variance_sum = float(centered @ centered)
    if variance_sum <= 1e-16:
        return None
    beta = centered @ (r - r.mean(0)) / variance_sum
    alpha = r.mean(0) - beta * x.mean()
    beta[market], alpha[market] = 1., 0.
    residual = (r[-21:] - alpha - x[-21:, None] * beta).sum(0)
    raw = p[-1] / p[-22] - 1.
    simple = np.diff(p[-31:], axis=0) / p[-31:-1]
    return dict(beta=beta, alpha=alpha, raw=raw, residual=residual, returns=simple,
                fit_observations=84, latest_input_us=int(clocks[k]), oldest_close_us=int(clocks[k - 84]))


def hedge_and_risk(alt_raw, beta, past_returns, symbols=SYMBOLS):
    market = tuple(symbols).index('BTCUSDT')
    w = np.asarray(alt_raw, dtype=float).copy()
    if w.shape != (5,) or w[market] != 0 or not np.isfinite(beta).all():
        raise ValueError('Ordered alt intent and beta required')
    w[market] = -float(beta @ w)
    # Scale all legs together before the existing kernel's element clipping.
    scale = min(1., .3 / max(np.max(np.abs(w)), 1e-30), .6 / max(np.abs(w).sum(), 1e-30))
    w *= scale
    result, risk = signed_risk_weights(w, past_returns, annual_vol_target=.10)
    modeled_beta = float(beta @ result)
    sigma = float(np.sqrt(max(0., result @ (np.cov(past_returns, rowvar=False) * 365) @ result)))
    if abs(modeled_beta) > 1e-12 or np.max(np.abs(result)) > .3 + 1e-12 or np.abs(result).sum() > .6 + 1e-12 or sigma > .10 + 1e-12:
        raise ValueError('Common risk/hedge bounds violated')
    return result, dict(modeled_beta_error=modeled_beta, post_target_annual_vol=sigma,
                        cap_prescale=scale, unscaled_covariance_vol=risk['unscaled_signed_covariance_annual_vol'])


def paired_targets(prices, clocks, decisions, symbols=SYMBOLS):
    p = np.asarray(prices, dtype=float)
    if np.asarray(clocks).dtype.kind not in 'iu' or np.asarray(decisions).dtype.kind not in 'iu':
        raise ValueError('Integer UTC microsecond clocks required')
    t = np.asarray(clocks, dtype=np.int64)
    d = np.asarray(decisions, dtype=np.int64)
    if p.shape != (len(t), 5) or len(d) == 0 or np.any(np.diff(t) != DAY) or np.any(np.diff(d) != DAY) or np.any(t % DAY) or np.any(d % DAY):
        raise ValueError('Dense common UTC input/decision clocks required')
    names = tuple(symbols)
    if len(names) != 5 or set(names) != set(SYMBOLS):
        raise ValueError('Exact CORE5 ordered identity required')
    market = names.index('BTCUSDT')
    active = np.array([s != 'BTCUSDT' for s in names])
    first = ANCHOR + (int(d[0]) - ANCHOR) // WEEK * WEEK
    output = {int(stamp): i for i, stamp in enumerate(d)}
    weights = {arm: np.zeros((len(d), 5)) for arm in ('raw', 'residual')}
    intents = {arm: np.zeros(5) for arm in weights}
    betas = np.full((len(d), 5), np.nan)
    alphas = np.full((len(d), 5), np.nan)
    ready = np.zeros(len(d), dtype=bool)
    ranks, daily, fits = [], [], 0
    for stamp in range(first, int(d[-1]) + DAY, DAY):
        profile = context(p, t, stamp, names)
        if profile is not None:
            fits += 4
        if (stamp - ANCHOR) % WEEK == 0:
            event = dict(rank_us=stamp, ready=profile is not None, input_cutoff_us=stamp)
            for arm in weights:
                score = profile[arm] if profile is not None else np.full(5, np.nan)
                intents[arm] = market_neutral(score[None], active[None] if profile is not None else np.zeros((1, 5), bool), k=2, gross=.6)[0]
                event[arm + '_alt_weights'] = intents[arm].tolist()
                event[arm + '_scores'] = [float(score[j]) if profile is not None and active[j] else None for j in range(5)]
            event['beta'] = profile['beta'].tolist() if profile is not None else None
            event['alpha'] = profile['alpha'].tolist() if profile is not None else None
            ranks.append(event)
        if profile is None:
            for arm in weights:
                intents[arm][:] = 0.
        if stamp not in output:
            continue
        i = output[stamp]
        witness = dict(decision_us=stamp, ready=profile is not None)
        if profile is not None:
            betas[i], alphas[i], ready[i] = profile['beta'], profile['alpha'], True
            witness.update(input_cutoff_us=profile['latest_input_us'], regression_observations=84)
            for arm in weights:
                weights[arm][i], witness[arm] = hedge_and_risk(intents[arm], profile['beta'], profile['returns'], names)
        daily.append(witness)
    return dict(decision_us=d, symbol_order=np.asarray(names), weights=weights, beta=betas, alpha=alphas,
                ready=ready, rank_events=ranks, daily_checks=daily, rolling_OLS_fits=fits,
                old_weekly_raw_pool_preserved=True, market_index=market)
