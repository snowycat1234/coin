"""Exact own-wallet VJP with four-input feature replay and unchanged date weights."""

import numpy as np
import torch

from modules.temporal_short_expansion.gradient import request_gradient


def predict_episode(model, episode, *, feature_batch_size=32, start=0, stop=None):
    if type(feature_batch_size) is not int or feature_batch_size < 1:
        raise ValueError("Positive feature-window batch size required")
    stop = len(episode.contexts) if stop is None else min(stop, len(episode.contexts))
    outputs = []
    for i in range(start, stop, feature_batch_size):
        end = min(i + feature_batch_size, stop)
        tensors = [
            torch.tensor(a[i:end].copy(), device=model.mean.device)
            for a in (
                episode.windows.values,
                episode.windows.valid,
                episode.windows.step_valid,
                episode.expert_state,
            )
        ]
        tensors[0] = tensors[0].to(model.mean.dtype)
        tensors[3] = tensors[3].to(model.mean.dtype)
        outputs.append(model(*tensors))
    return torch.cat(outputs)


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
        weight = len(episode.contexts) / total
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
                        gradient[start : start + feature_batch_size] * weight,
                        dtype=output.dtype,
                        device=output.device,
                    )
                )
        finally:
            torch.set_rng_state(final_rng)
        result += loss * weight
        paths.append(requests)
    return float(result), np.concatenate(paths)
