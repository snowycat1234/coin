"""Expose exact decision-bound Context quantities, never economic outcomes."""

from dataclasses import dataclass

import numpy as np

from modules.temporal_two_expert.inputs import CORE5, array_digest, digest

from .model import INPUT_EXPERT_INDICES, INPUT_NAMES, TARGET_SCALE


@dataclass(frozen=True)
class ExpertEpisode:
    original: object
    expert_state: np.ndarray
    expert_input_available_us: np.ndarray

    def __getattr__(self, name):
        return getattr(self.original, name)

    @property
    def identity(self):
        return digest(
            dict(
                original=self.original.identity,
                layout=INPUT_NAMES,
                symbols=CORE5,
                target_scale=TARGET_SCALE,
                state=array_digest(self.expert_state),
                clocks=array_digest(self.expert_input_available_us),
            )
        )


def expose_episode(episode):
    n = len(episode.contexts)
    decisions = episode.windows.decision_us
    targets = np.asarray(episode.expert_targets)
    eligible = np.asarray(episode.eligible)
    clocks = np.asarray(episode.target_available_us)
    if (
        targets.shape != (n, 6, 5)
        or targets.dtype != np.float64
        or eligible.shape != (n, 6)
        or eligible.dtype != bool
        or clocks.shape != (n, 6)
        or clocks.dtype != np.int64
        or np.any(clocks < 0)
        or np.any(clocks > decisions[:, None])
        or any(
            c.decision_us != int(t) or c.available_us > t
            for c, t in zip(episode.contexts, decisions, strict=True)
        )
    ):
        raise ValueError("Exact canonical E6 targets/masks and causal decision clocks required")
    signed = targets[:, INPUT_EXPERT_INDICES]
    masks = eligible[:, INPUT_EXPERT_INDICES]
    # Mask before arithmetic. Flat and ineligible both have zero values but
    # different explicit eligibility. No funding/outcome/label/wallet is read.
    signed = np.where(masks[:, :, None], signed, 0.0)
    if not np.isfinite(signed).all() or np.any(np.abs(signed) > TARGET_SCALE + 1e-12):
        raise ValueError("Observed expert targets must be finite within existing perasset cap")
    state = np.concatenate((signed.reshape(n, 15) / TARGET_SCALE, masks.astype(float)), axis=1)
    selected_clocks = clocks[:, INPUT_EXPERT_INDICES]
    available = np.concatenate((np.repeat(selected_clocks, 5, axis=1), selected_clocks), axis=1)
    for value in (state, available):
        value.flags.writeable = False
    return ExpertEpisode(episode, state, available)
