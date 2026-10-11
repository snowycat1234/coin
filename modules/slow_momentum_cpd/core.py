"""Train-frozen Matérn CPD and causal paper-inspired trend features.

Equations adapted from Wood, Roberts, Zohren (2105.13727v3) and MIT-licensed
kieranjwood/trading-momentum-transformer e0352cb0. Deliberate differences are
registered in the experiment protocol. No strategy or wallet is implemented here.
"""

from dataclasses import dataclass

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize
from scipy.special import expit, logsumexp

DAY_US = 86_400_000_000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
FEATURES = ("ret1", "ret21", "ret63", "ret126", "ret252", "macd8_24", "macd16_48", "macd32_96")


def rolling_std(x, width):
    out = np.full(len(x), np.nan)
    if len(x) >= width:
        windows = np.lib.stride_tricks.sliding_window_view(x, width)
        good = np.isfinite(windows).all(axis=1)
        values = np.full(len(windows), np.nan)
        values[good] = windows[good].std(axis=1, ddof=1)
        out[width - 1 :] = values
    return out


def ewm(x, alpha, minimum=1, std=False):
    """Causal adjusted exponential moments, resetting on every missing observation."""
    out = np.full(len(x), np.nan)
    weight = weight2 = total = square = 0.0
    count = 0
    decay = 1 - alpha
    for t, value in enumerate(x):
        if not np.isfinite(value):
            weight = weight2 = total = square = 0.0
            count = 0
            continue
        weight = weight * decay + 1
        weight2 = weight2 * decay**2 + 1
        total = total * decay + value
        square = square * decay + value**2
        count += 1
        if count >= minimum:
            variance = max(0.0, square / weight - (total / weight) ** 2)
            correction = 1 - weight2 / weight**2
            out[t] = (
                np.sqrt(variance / correction)
                if std and correction > 0
                else total / weight
                if not std
                else np.nan
            )
    return out


def trend_features(close):
    """Eight past-only inputs; no winsorisation, imputation or future bfill."""
    close = np.asarray(close, dtype=float)
    n, assets = close.shape
    result = np.full((n, assets, 8), np.nan)
    returns = np.full((n, assets), np.nan)
    vol = np.full_like(returns, np.nan)
    for asset in range(assets):
        p = close[:, asset].copy()
        observed = np.isfinite(p) & (p > 0)
        p[~observed] = np.nan
        streak = np.zeros(n, dtype=int)
        for t in range(n):
            streak[t] = (streak[t - 1] if t else 0) + 1 if observed[t] else 0
        r = np.full(n, np.nan)
        valid = observed[1:] & observed[:-1]
        r[1:][valid] = p[1:][valid] / p[:-1][valid] - 1
        returns[:, asset] = r
        v = ewm(r, 2 / 61, minimum=60, std=True)
        v[v <= 1e-10] = np.nan
        vol[:, asset] = v
        for column, horizon in enumerate((1, 21, 63, 126, 252)):
            value = np.full(n, np.nan)
            good = streak[horizon:] > horizon
            value[horizon:][good] = p[horizon:][good] / p[:-horizon][good] - 1
            result[:, asset, column] = value / (v * np.sqrt(horizon))
        price_std = rolling_std(p, 63)
        price_std[price_std <= 1e-10] = np.nan
        for column, (short, long) in enumerate(((8, 24), (16, 48), (32, 96)), 5):
            q = (ewm(p, 1 / short) - ewm(p, 1 / long)) / price_std
            qstd = rolling_std(q, 252)
            qstd[qstd <= 1e-10] = np.nan
            result[:, asset, column] = q / qstd
    return result, returns, vol


def sample_index(features, returns, vol, available_us, start_us, end_us, sequence=63):
    """Exact paired sample axis with mature labels strictly before the boundary.

    A bar available at D predicts the next bar's close-to-close return, known
    at D+one day. This is a statistical label, not an executable-price PnL.
    """
    rows = []
    for t in range(sequence - 1, len(features) - 1):
        if not start_us <= available_us[t] < end_us:
            continue
        if available_us[t + 1] >= end_us:  # strict maturity/purge, including equality
            continue
        for asset in range(features.shape[1]):
            if (
                np.isfinite(features[t - sequence + 1 : t + 1, asset]).all()
                and np.isfinite(returns[t + 1, asset])
                and np.isfinite(vol[t, asset])
                and vol[t, asset] > 0
            ):
                rows.append((t, asset))
    return np.asarray(rows, dtype=int).reshape(-1, 2)


@dataclass(frozen=True)
class Scaler:
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, features, rows, sequence=63):
        # Unique training input observations; overlapping windows are counted once.
        used = np.zeros(features.shape[:2], dtype=bool)
        for t, asset in rows:
            used[t - sequence + 1 : t + 1, asset] = True
        values = features[used]
        if not len(values) or not np.isfinite(values).all():
            raise ValueError("No complete training scaler observations")
        scale = values.std(axis=0)
        scale[scale < 1e-8] = 1
        return cls(values.mean(axis=0), scale), used

    def transform(self, values):
        return (values - self.mean) / self.scale


def matern32(x, variance, length):
    distance = np.abs(x[:, None] - x[None, :]) * np.sqrt(3) / length
    return variance * (1 + distance) * np.exp(-distance)


def covariance(theta, size, location=None):
    """CP sides have independently fitted variances and lengths, fixed at score time."""
    x = np.arange(size, dtype=float)
    if location is None:
        variance, length, noise = np.exp(theta)
        return matern32(x, variance, length) + np.eye(size) * (noise + 1e-7)
    v1, l1, v2, l2, noise, steep = np.exp(theta)
    gate = expit(steep * (x - location))
    return (
        matern32(x, v1, l1) * np.outer(1 - gate, 1 - gate)
        + matern32(x, v2, l2) * np.outer(gate, gate)
        + np.eye(size) * (noise + 1e-7)
    )


def nlml(cov, windows):
    """One independent GP likelihood per row; never concatenate assets/time windows."""
    factor = cho_factor(cov, lower=True)
    quadratic = np.sum(windows * cho_solve(factor, windows.T).T, axis=1)
    return (
        0.5 * quadratic + np.log(np.diag(factor[0])).sum() + 0.5 * cov.shape[0] * np.log(2 * np.pi)
    )


def cp_summary(stationary_nlml, cp_nlml, locations, window):
    """Uniform, frozen grid prior. Severity is evidence score, not event probability."""
    log_cp_evidence = logsumexp(-cp_nlml, axis=1) - np.log(len(locations))
    weights = np.exp(-cp_nlml - logsumexp(-cp_nlml, axis=1, keepdims=True))
    age = 1 - (weights @ locations) / window  # official-code orientation
    severity = expit(stationary_nlml + log_cp_evidence)
    return np.stack((age, severity), axis=1)


@dataclass(frozen=True)
class FrozenGP:
    mean: float
    scale: float
    stationary: np.ndarray
    change: np.ndarray
    locations: np.ndarray
    window: int
    fit_info: dict

    @classmethod
    def fit(cls, returns, available_us, start_us, end_us, window=21, maxiter=60, per_asset=64):
        windows = []
        identities = []
        for asset in range(returns.shape[1]):
            candidates = [
                t
                for t in range(window, len(returns))
                if start_us <= available_us[t] < end_us - DAY_US
                and np.isfinite(returns[t - window : t + 1, asset]).all()
            ]
            selected = np.unique(
                np.linspace(0, len(candidates) - 1, min(per_asset, len(candidates))).astype(int)
            )
            for index in selected:
                t = candidates[index]
                windows.append(returns[t - window : t + 1, asset])
                identities.append((t, asset))
        raw = np.asarray(windows)
        if raw.ndim != 2 or not len(raw):
            raise ValueError("No training CP windows")
        # Unique selected training observations for the global return standardisation.
        used = np.zeros(returns.shape, dtype=bool)
        for t, asset in identities:
            used[t - window : t + 1, asset] = True
        mean = float(returns[used].mean())
        scale = float(returns[used].std())
        if scale <= 1e-10:
            raise ValueError("Degenerate training GP scale")
        y = (raw - mean) / scale
        locations = np.array((3.0, 6.0, 9.0, 12.0, 15.0, 18.0))
        initial_m = np.log((0.5, 2.0, 0.5))
        initial_c = np.log((0.5, 2.0, 0.5, 2.0, 0.5, 1.0))

        def stationary_loss(theta):
            return float(nlml(covariance(theta, window + 1), y).mean())

        def change_loss(theta):
            scores = np.stack(
                [nlml(covariance(theta, window + 1, c), y) for c in locations], axis=1
            )
            return float((-logsumexp(-scores, axis=1) + np.log(len(locations))).mean())

        bounds_m = [(-6, 3), (-3, 4), (-6, 3)]
        bounds_c = [(-6, 3), (-3, 4), (-6, 3), (-3, 4), (-6, 3), (-3, 3)]
        m = minimize(
            stationary_loss,
            initial_m,
            method="L-BFGS-B",
            bounds=bounds_m,
            options={"maxiter": maxiter},
        )
        c = minimize(
            change_loss, initial_c, method="L-BFGS-B", bounds=bounds_c, options={"maxiter": maxiter}
        )
        info = {
            "windows": len(raw),
            "identities": identities,
            "latest_fit_available_us": int(max(available_us[t] for t, _ in identities)),
            "scaler_unique_return_rows": int(used.sum()),
            "stationary": {
                "success": bool(m.success),
                "iterations": int(m.nit),
                "message": str(m.message),
                "loss": float(m.fun),
            },
            "change": {
                "success": bool(c.success),
                "iterations": int(c.nit),
                "message": str(c.message),
                "loss": float(c.fun),
            },
        }
        if not np.isfinite(m.fun) or not np.isfinite(c.fun):
            raise ValueError("Nonfinite training GP likelihood")
        return cls(mean, scale, m.x, c.x, locations, window, info)

    def transform(self, returns):
        # No optimiser/scaler fit/location fit in inference; only fixed likelihoods.
        out = np.full((*returns.shape, 2), np.nan)
        for asset in range(returns.shape[1]):
            if len(returns) <= self.window:
                continue
            windows = np.lib.stride_tricks.sliding_window_view(returns[:, asset], self.window + 1)
            good = np.isfinite(windows).all(axis=1)
            y = (windows[good] - self.mean) / self.scale
            m = nlml(covariance(self.stationary, self.window + 1), y)
            c = np.stack(
                [nlml(covariance(self.change, self.window + 1, loc), y) for loc in self.locations],
                axis=1,
            )
            out[self.window :, asset][good] = cp_summary(m, c, self.locations, self.window)
        return out
