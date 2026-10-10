"""Predetermined whole-wallet coefficients with frozen expert-input request adjoints."""

from numbers import Real

import numpy as np
import torch

from modules.temporal_expert_input.gradient import predict_episode, request_gradient
from modules.temporal_two_expert.checkpoint import _restore_rng, _rng_state, model_identity
from modules.temporal_two_expert.inputs import DAY_US


def weights(lengths, mixing=0.0):
    """(1-mixing)*date share + mixing*equal-wallet share, without day sampling."""
    lengths = np.asarray(lengths)
    if (
        lengths.ndim != 1
        or not len(lengths)
        or lengths.dtype.kind not in "iu"
        or np.any(lengths <= 0)
        or isinstance(mixing, (bool, np.bool_))
        or not isinstance(mixing, Real)
        or not np.isfinite(mixing)
        or not 0 <= mixing <= 1
    ):
        raise ValueError("Positive integer wallet lengths and finite mixing in [0,1] required")
    result = lengths.astype(np.float64) / sum(map(int, lengths))
    if mixing:
        result = (1.0 - mixing) * result + mixing / len(lengths)
    result.flags.writeable = False
    return result


def _episodes(model, episodes, feature_batch_size):
    episodes = tuple(episodes)
    if (
        model.mean.device.type != "cpu"
        or type(feature_batch_size) is not int
        or feature_batch_size < 1
        or not episodes
        or any(e.role != "TRAIN" for e in episodes)
        or len({e.wallet_id for e in episodes}) != len(episodes)
        or len({e.split_cutoff_us for e in episodes}) != 1
    ):
        raise ValueError("Distinct complete CPU TRAIN wallets and positive feature batch required")
    for episode in episodes:
        decisions = np.asarray(episode.windows.decision_us)
        if (
            len(episode.contexts) < 2
            or not np.array_equal(decisions, np.arange(episode.start_us, episode.end_us, DAY_US))
            or len(decisions) != len(episode.contexts)
            or not np.array_equal(decisions, [c.decision_us for c in episode.contexts])
        ):
            raise ValueError("Every wallet must retain its complete daily chronology")
    for left, right in zip(episodes, episodes[1:], strict=False):
        if left.start_us > right.start_us:
            raise ValueError("Wallets must remain in their declared chronological order")
        if left.end_us > right.start_us:
            raise ValueError("Overlapping wallet chronology rejected")
    return episodes


def memory_bounded_gradients(model, episodes, prototype, *, feature_batch_size=32, mixing=0.0):
    """Replay unchanged complete-wallet VJPs with one fixed coefficient per wallet."""
    episodes = _episodes(model, episodes, feature_batch_size)
    coefficients = weights([len(e.contexts) for e in episodes], mixing)
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


def _vector(model):
    if any(p.grad is None or not torch.isfinite(p.grad).all() for p in model.parameters()):
        raise ValueError("Complete finite snapshot gradients required")
    return torch.cat([p.grad.detach().flatten().clone() for p in model.parameters()])


def _summary(vectors, losses, lengths, mixing):
    coefficients = weights(lengths, mixing)
    contributions = [g * float(a) for g, a in zip(vectors, coefficients, strict=True)]
    total = torch.stack(contributions).sum(0)
    squared = float(total.square().sum())
    shares = (
        [float((g * total).sum()) / squared for g in contributions]
        if squared
        else [None] * len(vectors)
    )
    return dict(
        mixing=float(mixing),
        coefficients=coefficients.tolist(),
        weighted_mean_loss=float(
            sum(a * loss for a, loss in zip(coefficients, losses, strict=True))
        ),
        weighted_loss_contributions=[
            float(a * loss) for a, loss in zip(coefficients, losses, strict=True)
        ],
        gradient_norm=float(torch.linalg.vector_norm(total)),
        weighted_gradient_vector_norms=[float(torch.linalg.vector_norm(g)) for g in contributions],
        signed_projection_shares=shares,
        signed_projection_defined=bool(squared),
        signed_projection_sum=float(sum(shares)) if squared else None,
        projection_definition="dot(a_i*g_i,G)/squared_norm(G);signed_and_additive;not_gradient_norm_fraction",
    ), total


def episode_diagnostic(
    model,
    episodes,
    prototype,
    *,
    mixing=0.0,
    feature_batch_size=32,
    snapshot_step=None,
    check_aggregate=False,
):
    """Deterministic snapshot decomposition; optimizer state is never accessed.

    Compute each intact wallet once. Both common objective summaries reuse its
    exact gradient vector. These are gradients at the supplied model snapshot,
    not the accumulated stochastic directions used by earlier Adam updates.
    """
    episodes = _episodes(model, episodes, feature_batch_size)
    weights([len(e.contexts) for e in episodes], mixing)
    if any(p.grad is not None for p in model.parameters()):
        raise ValueError("Snapshot diagnostic requires no pending gradients")
    if snapshot_step is not None and (type(snapshot_step) is not int or snapshot_step < 0):
        raise ValueError("Explicit nonnegative completed snapshot step required")
    identity, rng = model_identity(model), _rng_state()
    modes = [(module, module.training) for module in model.modules()]
    snapshot = {k: v.detach().clone() for k, v in model.state_dict().items()}
    try:
        model.eval()
        vectors, losses = [], []
        for episode in episodes:
            model.zero_grad(set_to_none=True)
            loss, _ = memory_bounded_gradients(
                model, [episode], prototype, feature_batch_size=feature_batch_size, mixing=0.0
            )
            losses.append(loss)
            vectors.append(_vector(model))
        lengths = [len(e.contexts) for e in episodes]
        date, date_vector = _summary(vectors, losses, lengths, 0.0)
        mixed, mixed_vector = _summary(vectors, losses, lengths, 0.5)
        if mixing == 0.0:
            trained, trained_vector = date, date_vector
        elif mixing == 0.5:
            trained, trained_vector = mixed, mixed_vector
        else:
            trained, trained_vector = _summary(vectors, losses, lengths, mixing)
        full_check = None
        if check_aggregate:
            model.zero_grad(set_to_none=True)
            loss, _ = memory_bounded_gradients(
                model, episodes, prototype, feature_batch_size=feature_batch_size, mixing=mixing
            )
            actual = _vector(model)
            torch.testing.assert_close(actual, trained_vector, rtol=2e-11, atol=1e-14)
            if not np.isclose(loss, trained["weighted_mean_loss"], rtol=2e-13, atol=1e-16):
                raise ValueError("Complete gradient aggregation loss differs")
            full_check = dict(
                maximum_gradient_abs_error=float((actual - trained_vector).abs().max()),
                loss_abs_error=abs(loss - trained["weighted_mean_loss"]),
            )
        records = [
            dict(
                wallet_id=e.wallet_id,
                dates=n,
                own_path_mean_loss=float(loss),
                individual_gradient_norm=float(torch.linalg.vector_norm(g)),
                coefficient=trained["coefficients"][i],
                weighted_loss_contribution=trained["weighted_loss_contributions"][i],
                weighted_gradient_vector_norm=trained["weighted_gradient_vector_norms"][i],
                signed_projection_share_of_total_gradient=trained["signed_projection_shares"][i],
                date_coefficient=date["coefficients"][i],
                mixed_coefficient=mixed["coefficients"][i],
            )
            for i, (e, n, loss, g) in enumerate(
                zip(episodes, lengths, losses, vectors, strict=True)
            )
        ]
        return dict(
            schema="DETERMINISTIC_WHOLE_EPISODE_GRADIENT_DIAGNOSTIC_V2",
            snapshot_step=snapshot_step,
            model_identity=identity,
            data_role="TRAIN_ONLY",
            objective_version=2,
            dropout=False,
            optimizer_updates=0,
            gradient_role="deterministic_supplied_snapshot;not_accumulated_stochastic_Adam_direction",
            episodes=records,
            date_mean_loss=date["weighted_mean_loss"],
            mixed_mean_loss=mixed["weighted_mean_loss"],
            date_gradient_summary=date,
            mixed_gradient_summary=mixed,
            trained_objective_summary=trained,
            independent_full_sum_check=full_check,
            weights_unchanged=True,
            RNG_unchanged=True,
            training_modes_preserved=True,
            gradients_cleared=True,
            optimizer_state_accesses=0,
        )
    finally:
        model.zero_grad(set_to_none=True)
        changed = model_identity(model) != identity
        if changed:
            model.load_state_dict(snapshot, strict=True)
        for module, mode in modes:
            module.training = mode
        _restore_rng(rng)
        if changed:
            raise ValueError(
                "Snapshot diagnostic unexpectedly changed model state; restored original"
            )
