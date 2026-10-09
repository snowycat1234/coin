"""Bounded feature graphs, unchanged full chronological economic wallets."""

import numpy as np
import torch

from modules.temporal_risk_proxy_v2.proxy import (
    BoundaryPlan,
    BoundaryStop,
    request_loss_and_gradient_v2,
)
from modules.temporal_two_expert.exact import feature_chunk, replay_request_gradients
from modules.temporal_two_expert.model import predict_windows


class PathFailure(ValueError):
    def __init__(self, episode, error):
        self.record = dict(
            reason=error.reason,
            wallet_id=episode.wallet_id,
            day_index=error.day_index,
            decision_us=int(episode.windows.decision_us[error.day_index]),
            equity=error.equity,
            quantity=error.quantity.tolist(),
            mark=error.mark.tolist(),
            charged_reduction_cost=error.reduction_cost,
        )
        super().__init__(str(error))


def memory_bounded_gradients_v2(model, episodes, prototype, *, feature_batch_size=32):
    episodes = tuple(episodes)
    if (
        model.mean.device.type != "cpu"
        or not episodes
        or any(e.role != "TRAIN" for e in episodes)
        or len({e.wallet_id for e in episodes}) != len(episodes)
        or len({e.split_cutoff_us for e in episodes}) != 1
    ):
        raise ValueError("Distinct complete CPU TRAIN wallets with common cutoff required")
    ordered = sorted(episodes, key=lambda e: e.start_us)
    if any(a.end_us > b.start_us for a, b in zip(ordered, ordered[1:], strict=False)):
        raise ValueError("Overlapping wallets would double-count chronology")
    total = sum(len(e.contexts) for e in episodes)
    loss_sum, paths = 0.0, []
    for episode in episodes:
        rng_states, chunks = [], []
        with torch.no_grad():
            for start in range(0, len(episode.windows.values), feature_batch_size):
                rng_states.append(torch.get_rng_state().clone())
                chunks.append(
                    predict_windows(
                        model,
                        feature_chunk(episode.windows, start, feature_batch_size),
                        feature_batch_size=feature_batch_size,
                    )
                    .cpu()
                    .numpy()
                    .copy()
                )
        requests = np.concatenate(chunks)
        try:
            loss, gradients, report = request_loss_and_gradient_v2(
                requests,
                episode,
                prototype,
                plan=BoundaryPlan.full_fill_diagnostic(len(episode.contexts)),
            )
        except BoundaryStop as error:
            raise PathFailure(episode, error) from error
        if not np.isfinite(loss) or not np.isfinite(gradients).all():
            raise ValueError("Nonfinite charged-surrogate loss/request VJP")
        del report
        weight = len(episode.contexts) / total
        replay_request_gradients(
            model,
            episode.windows,
            gradients * weight,
            rng_states,
            requests,
            feature_batch_size=feature_batch_size,
        )
        loss_sum += loss * weight
        paths.append(requests)
    return float(loss_sum), np.concatenate(paths)
