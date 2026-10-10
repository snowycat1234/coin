"""Utility-gap-weighted pair preferences; outputs are not class probabilities."""

import numpy as np
import torch
import torch.nn.functional as F

PAIRS = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


def fit_scale(utility):
    """One common robust scale from mature TRAIN only; retain all payoff tails."""
    u = np.asarray(utility, dtype=np.float64)
    if u.ndim != 2 or u.shape[1] != 4 or not len(u) or not np.isfinite(u).all():
        raise ValueError("Nonempty finite four-action TRAIN utilities required")
    gaps = np.stack([u[:, i] - u[:, j] for i, j in PAIRS], axis=1)
    nonzero = np.abs(gaps[gaps != 0])
    if not len(nonzero):
        raise ValueError("All TRAIN payoffs tied; scale undefined")
    return float(np.median(nonzero))


def pairwise_loss(scores, utility, scale):
    """Mean over rows/six pairs of gap-weighted logistic preference loss.

    z_ij = log(q_i / q_j). dL/dz = |delta|/scale *
    (sigmoid(z) - 1[delta>0]) before the mean. Exactly tied utilities
    contribute zero loss/gradient. No argmax participates in differentiation.
    """
    if scores.ndim != 2 or scores.shape[1] != 4 or utility.shape != scores.shape:
        raise ValueError("Matching four-action score and utility tensors required")
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("Positive finite TRAIN-only scale required")
    if not torch.isfinite(scores).all() or not torch.isfinite(utility).all():
        raise ValueError("Finite scores and utilities required")
    if bool((scores < 0).any()):
        raise ValueError("Nonnegative preference scores required")
    # float64 tiny, not an economic threshold. No practical softmax clipping.
    logq = scores.clamp_min(torch.finfo(scores.dtype).tiny).log()
    losses = []
    for i, j in PAIRS:
        delta = utility[:, i] - utility[:, j]
        z = logq[:, i] - logq[:, j]
        losses.append(delta.clamp_min(0) * F.softplus(-z) + (-delta).clamp_min(0) * F.softplus(z))
    return torch.stack(losses, dim=1).mean() / scale
