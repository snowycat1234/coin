"""Canonical E6 data and a lossless active-leg adapter to the frozen E5 ABI.

Public slots are never replaced. The unchanged mapper's finite five-coordinate
container carries [CASH,VOL,unused,CS,SHORT] internally; zero public slot3 is
omitted. An explicit coordinate map, not public E5 expert identity, defines this
private ABI. CASH is the mapper's only distinguished coordinate. Every admitted
leg, release, L1 norm, target, covariance check and reverse adjoint is preserved.
"""

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import CORE5, array_digest, digest

from .model import E6, SHORT

SOURCE_COMMIT = "1291857d53360e4e06a4dd50540c130886deffbf"
PAYLOADS = {
    "TRAIN778_MOMENTUM_SHORT_CONTEXTS.npz": (
        "64accfc82f78034af0da48561ef7e2fabfc8712760066860194e3d2bce9e382d"
    ),
    "DEV61_MOMENTUM_SHORT_CONTEXTS.npz": (
        "89183eb92bd45b65a1209aa139f80964cc013c62015a803336db7a7bbd90840d"
    ),
}
ACTIVE_COORDINATES = (0, 1, 2, 4, 5)


def compress(requests):
    a = np.asarray(requests)
    if a.ndim != 2 or a.shape[1] != 6 or not np.isfinite(a).all() or np.any(a[:, 2:4]):
        raise ValueError("Finite canonical E6 requests with slots2/3 exactly zero required")
    return a[:, ACTIVE_COORDINATES].copy()


def expand(array):
    a = np.asarray(array)
    if a.ndim != 2 or a.shape[1] != 5:
        raise ValueError("Private five-coordinate array required")
    result = np.zeros((len(a), 6), dtype=a.dtype)
    result[:, ACTIVE_COORDINATES] = a
    return result


@dataclass(frozen=True)
class ExpandedEpisode:
    original: object
    internal: object
    expert_targets: np.ndarray
    eligible: np.ndarray
    target_available_us: np.ndarray
    payload_sha256: str

    def __getattr__(self, name):
        return getattr(self.original, name)

    @property
    def identity(self):
        return digest(
            dict(
                original=self.original.identity,
                short_payload=self.payload_sha256,
                canonical_order=E6,
                private_coordinates=ACTIVE_COORDINATES,
                targets=array_digest(self.expert_targets),
                eligible=array_digest(self.eligible),
                target_clocks=array_digest(self.target_available_us),
            )
        )


def append_episode(episode, targets, eligible, clocks, prototype, payload_sha256):
    n = len(episode.contexts)
    targets, eligible, clocks = map(np.asarray, (targets, eligible, clocks))
    decisions = episode.windows.decision_us
    if (
        targets.shape != (n, 1, 5)
        or targets.dtype != np.float64
        or not np.isfinite(targets).all()
        or np.any(targets > 0)
        or eligible.shape != (n, 1)
        or eligible.dtype != bool
        or clocks.shape != (n, 1)
        or clocks.dtype != np.int64
        or np.any(clocks < 0)
        or np.any(clocks > decisions[:, None])
    ):
        raise ValueError("Frozen causal ordered short-only context required")
    canonical = np.concatenate(
        (np.stack([c.expert_targets for c in episode.contexts]), targets), axis=1
    )
    masks = np.concatenate((np.stack([c.eligible for c in episode.contexts]), eligible), axis=1)
    available = np.concatenate(
        (np.stack([c.target_available_us for c in episode.contexts]), clocks), axis=1
    )
    contexts = []
    for i, original in enumerate(episode.contexts):
        # Fixed unused coordinate cannot receive budget. No old public target
        # or expert label is overwritten in canonical data.
        mask = masks[i, ACTIVE_COORDINATES].copy()
        mask[2] = False
        contexts.append(
            prototype.Context(
                original.decision_us,
                original.available_us,
                canonical[i, ACTIVE_COORDINATES].copy(),
                mask,
                original.past_returns30,
                original.market13,
                available[i, ACTIVE_COORDINATES].copy(),
            )
        )
    internal = replace(episode, contexts=tuple(contexts))
    for value in (canonical, masks, available):
        value.flags.writeable = False
    return ExpandedEpisode(episode, internal, canonical, masks, available, payload_sha256)


def load_short_pack(directory, episodes, prototype, *, training):
    name = (
        "TRAIN778_MOMENTUM_SHORT_CONTEXTS.npz" if training else "DEV61_MOMENTUM_SHORT_CONTEXTS.npz"
    )
    path = Path(directory) / name
    if sha(path) != PAYLOADS[name]:
        raise ValueError("Exact public short context bytes required")
    # Producer reasons are object arrays. Never deserialize them or enable
    # pickle; the byte-bound producer's numeric masks/clocks are sufficient.
    with np.load(path, allow_pickle=False) as z:
        keys = (
            "decision_us",
            "episode_id",
            "expert_targets",
            "expert_eligible",
            "target_available_us",
            "expert_asset_eligible",
            "asset_context_available_us",
        )
        a = {k: z[k].copy() for k in keys}
        if tuple(z["symbol_order"]) != CORE5 or tuple(z["expert_order"]) != (SHORT,):
            raise ValueError("Frozen CORE5 and named momentum short required")
    decisions = np.concatenate([e.windows.decision_us for e in episodes])
    expected_episode = np.concatenate([np.full(len(e.contexts), i) for i, e in enumerate(episodes)])
    if (
        not np.array_equal(a["decision_us"], decisions)
        or not np.array_equal(a["episode_id"], expected_episode)
        or a["expert_asset_eligible"].dtype != bool
        or a["expert_asset_eligible"].shape != (len(decisions), 1, 5)
        or np.any(a["expert_targets"][~a["expert_asset_eligible"]])
        or a["asset_context_available_us"].shape != (len(decisions), 5)
        or np.any(a["asset_context_available_us"] > decisions[:, None])
    ):
        raise ValueError("Exact episode dates and causal asset masks/clocks required")
    output, start = [], 0
    for episode in episodes:
        end = start + len(episode.contexts)
        output.append(
            append_episode(
                episode,
                a["expert_targets"][start:end],
                a["expert_eligible"][start:end],
                a["target_available_us"][start:end],
                prototype,
                PAYLOADS[name],
            )
        )
        start = end
    return tuple(output)
