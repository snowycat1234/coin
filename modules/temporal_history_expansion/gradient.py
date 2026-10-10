"""Whole-wallet VJP dispatcher; existing wallets retain their original kernel."""

import numpy as np
import torch

from modules.temporal_episode_weighting_v2.gradient import _episodes, weights
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_q4_reserved.terminal import charged_terminal_path
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan
from modules.temporal_short_expansion.adapter import compress, expand
from modules.temporal_short_expansion.gradient import request_gradient as original_gradient
from modules.temporal_two_expert.exact import verify_prototype


def request_gradient(requests, episode, prototype):
    if not getattr(episode, "real_terminal_ABI", False):
        return original_gradient(requests, episode, prototype)
    verify_prototype(prototype)
    internal = episode.internal
    targets, records = prototype.mapped_path(compress(requests), internal.contexts)
    w = torch.tensor(targets, dtype=torch.float64, requires_grad=True)
    with torch.enable_grad():
        report = charged_terminal_path(
            w,
            episode.prices,
            episode.funding_coeff,
            plan=BoundaryPlan.full_fill_diagnostic(len(episode.contexts)),
        )
        target_gradient = torch.autograd.grad(report["utility_sum"], w)[0].detach().numpy()
    n = len(episode.contexts)
    gradient = -prototype.mapping_vjp(target_gradient, records, internal.contexts) / n
    gradient[:, 2] = 0
    return -float(report["utility_sum"].detach()) / n, expand(gradient), report


def memory_bounded_gradients(model, episodes, prototype, *, feature_batch_size=32):
    """Same date weights/dropout replay with one economic rollout per intact wallet.

    Adapted from temporal_episode_weighting_v2: the sole semantic dispatch is
    real-terminal ABI for new2021 wallets. Model/RNG/mapper/cost kernels reused.
    No optimizer, training loop, data acquisition or historical scoring here.
    """
    episodes = _episodes(model, episodes, feature_batch_size)
    coefficients = weights([len(e.contexts) for e in episodes], mixing=0.0)
    result, paths = 0.0, []
    for episode, coefficient in zip(episodes, coefficients, strict=True):
        rng, chunks = [], []
        with torch.no_grad():
            for start in range(0, len(episode.contexts), feature_batch_size):
                rng.append(torch.get_rng_state().clone())
                chunks.append(
                    predict_episode(
                        model,
                        episode,
                        feature_batch_size=feature_batch_size,
                        start=start,
                        stop=start + feature_batch_size,
                    )
                    .numpy()
                    .copy()
                )
        requests = np.concatenate(chunks)
        loss, gradient, _ = request_gradient(requests, episode, prototype)
        if not np.isfinite(loss) or not np.isfinite(gradient).all():
            raise ValueError("Nonfinite complete chronological loss/VJP")
        final_rng = torch.get_rng_state().clone()
        try:
            for k, start in enumerate(range(0, len(episode.contexts), feature_batch_size)):
                torch.set_rng_state(rng[k])
                output = predict_episode(
                    model,
                    episode,
                    feature_batch_size=feature_batch_size,
                    start=start,
                    stop=start + feature_batch_size,
                )
                expected = torch.tensor(
                    requests[start : start + feature_batch_size], dtype=output.dtype
                )
                if not torch.equal(output.detach().cpu(), expected):
                    raise ValueError("Expert-input dropout replay differs")
                output.backward(
                    torch.tensor(
                        gradient[start : start + feature_batch_size] * coefficient,
                        dtype=output.dtype,
                        device=output.device,
                    )
                )
        finally:
            torch.set_rng_state(final_rng)
        result += loss * coefficient
        paths.append(requests)
    return float(result), np.concatenate(paths)
