"""Unchanged objective-v2 wallet and request VJP, appended output coordinates."""

import numpy as np
import torch

from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, request_loss_and_gradient_v2
from modules.temporal_two_expert.exact import feature_chunk, replay_request_gradients
from modules.temporal_two_expert.model import predict_windows

from .adapter import compress, expand


def request_gradient(requests, episode, prototype):
    loss, gradient, report = request_loss_and_gradient_v2(
        compress(requests),
        episode.internal,
        prototype,
        plan=BoundaryPlan.full_fill_diagnostic(len(episode.contexts)),
    )
    gradient[:, 2] = 0  # fixed-zero inactive private coordinate
    return loss, expand(gradient), report


def memory_bounded_gradients(model, episodes, prototype, *, feature_batch_size=32):
    episodes = tuple(episodes)
    if (
        model.mean.device.type != "cpu"
        or not episodes
        or any(e.role != "TRAIN" for e in episodes)
        or len({e.wallet_id for e in episodes}) != len(episodes)
        or len({e.split_cutoff_us for e in episodes}) != 1
    ):
        raise ValueError("Distinct complete CPU TRAIN wallets required")
    ordered = sorted(episodes, key=lambda e: e.start_us)
    if any(a.end_us > b.start_us for a, b in zip(ordered, ordered[1:], strict=False)):
        raise ValueError("Overlapping wallet chronology rejected")
    total, result, paths = sum(len(e.contexts) for e in episodes), 0.0, []
    for episode in episodes:
        rng, chunks = [], []
        with torch.no_grad():
            for start in range(0, len(episode.contexts), feature_batch_size):
                rng.append(torch.get_rng_state().clone())
                chunks.append(
                    predict_windows(
                        model,
                        feature_chunk(episode.windows, start, feature_batch_size),
                        feature_batch_size=feature_batch_size,
                    )
                    .numpy()
                    .copy()
                )
        requests = np.concatenate(chunks)
        loss, gradient, _ = request_gradient(requests, episode, prototype)
        if not np.isfinite(loss) or not np.isfinite(gradient).all():
            raise ValueError("Nonfinite complete chronological loss/VJP")
        weight = len(episode.contexts) / total
        replay_request_gradients(
            model,
            episode.windows,
            gradient * weight,
            rng,
            requests,
            feature_batch_size=feature_batch_size,
        )
        result += loss * weight
        paths.append(requests)
    return float(result), np.concatenate(paths)
