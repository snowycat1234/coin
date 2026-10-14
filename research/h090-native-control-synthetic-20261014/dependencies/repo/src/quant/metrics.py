"""Daily UTC performance statistics. No intraday Sharpe annualisation."""

from __future__ import annotations

import math

import numpy as np
import polars as pl


def daily_metrics(daily_nav: pl.DataFrame, initial_cash: float) -> dict[str, float | int]:
    """Compute net mark-to-market statistics, including the initial cash observation."""
    if daily_nav.is_empty():
        raise ValueError("daily_nav must contain at least one UTC daily valuation")
    nav = daily_nav.get_column("nav").to_numpy().astype(float)
    previous = np.r_[initial_cash, nav[:-1]]
    returns = nav / previous - 1
    days = len(nav)
    total_return = float(nav[-1] / initial_cash - 1)
    annual_return = (
        float((nav[-1] / initial_cash) ** (365 / days) - 1) if nav[-1] > 0 else -1.0
    )
    volatility = float(np.std(returns, ddof=1) * math.sqrt(365)) if days > 1 else 0.0
    sharpe = float(np.mean(returns) * 365 / volatility) if volatility > 0 else 0.0
    full_nav = np.r_[initial_cash, nav]
    drawdown = full_nav / np.maximum.accumulate(full_nav) - 1
    return {
        "days": days,
        "initial_nav": float(initial_cash),
        "final_nav": float(nav[-1]),
        "total_return": total_return,
        "annual_return": annual_return,
        "annual_volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": float(-np.min(drawdown)),
        "fees": float(daily_nav.get_column("fees").sum()),
        "execution_costs": float(daily_nav.get_column("execution_costs").sum()),
        "turnover": float(daily_nav.get_column("turnover").sum()),
    }


def block_bootstrap_mean_ci(
    daily_returns: np.ndarray,
    *,
    block_days: int = 7,
    samples: int = 2_000,
    seed: int = 20260930,
) -> tuple[float, float]:
    """A reproducible circular block bootstrap CI for mean daily excess returns.

    Use paired candidate-minus-baseline daily returns. The interval is descriptive,
    does not correct for strategy selection and is not an acceptance guarantee.
    """
    values = np.asarray(daily_returns, dtype=float)
    if not len(values) or not np.all(np.isfinite(values)):
        raise ValueError("finite daily returns are required")
    if block_days < 1 or samples < 1:
        raise ValueError("block_days and samples must be positive")
    rng = np.random.default_rng(seed)
    means = np.empty(samples)
    offsets = np.arange(min(block_days, len(values)))
    blocks = math.ceil(len(values) / len(offsets))
    for i in range(samples):
        starts = rng.integers(0, len(values), size=blocks)
        indices = ((starts[:, None] + offsets) % len(values)).ravel()[: len(values)]
        means[i] = np.mean(values[indices])
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)
