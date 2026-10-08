"""Explicit, fixed CPU paired-fit API for the parent to launch AFTER handoff.

No CLI, fit on import, data downloads, checkpoint selection or parameter search.
This API is intentionally NOT invoked by the calibration command or test suite.
Caller supplies byte-bound fragments, preserving input/label provenance.
"""
from __future__ import annotations

from datetime import UTC, datetime
import time

import numpy as np

from .prototype import DAY_US, SmallBudgetHead, loss_and_gradient

EPOCHS = 64
LEARNING_RATE = .001
MAX_ARM_SECONDS = 120
WINDOWS = {
    "BEAR2022NOV": ("2022-11-01", "2022-12-01"),
    "RECOVERY2023JAN": ("2023-01-01", "2023-02-01"),
    "H1_TRAIN": ("2024-01-01", "2024-05-01"),
    "H1_VALIDATE": ("2024-05-01", "2024-07-01"),
}


def stamp(date):
    return int(datetime.fromisoformat(date).replace(tzinfo=UTC).timestamp()) * 1_000_000


def validate_fragment(fragment, tag):
    if tag not in WINDOWS or fragment.get("window_id") != tag:
        raise ValueError("Exact preregistered data role required")
    start, end = map(stamp, WINDOWS[tag])
    contexts = fragment["contexts"]
    decisions = np.asarray([c.decision_us for c in contexts], dtype=np.int64)
    if not np.array_equal(decisions, np.arange(start, end, DAY_US, dtype=np.int64)):
        raise ValueError("Complete declared fragment; no date gaps or extra observations")
    for c in contexts:
        c.validate()
    labels = np.asarray(fragment["label_available_us"])
    if (labels.shape != decisions.shape or labels.dtype.kind not in "iu"
            or np.any(labels[:-1] < decisions[:-1] + DAY_US) or np.any(labels[:-1] >= end)):
        raise ValueError("Every learning label must mature strictly before its split cutoff")
    identity = fragment.get("binding", {})
    for key in ("input_npz_sha256", "teacher_jsonl_sha256", "expert_identity_sha256",
                "mapper_sha256", "market_binding_sha256"):
        value = identity.get(key)
        if (not isinstance(value, str) or len(value) != 64
                or any(c not in "0123456789abcdef" for c in value)):
            raise ValueError("Byte-verified input/label/source provenance required: " + key)
    # SHA strings are provenance, not a substitute for the caller's actual byte
    # verification. Do not use relocated paths without checking their hashes.
    return identity


def common_standardizer(fragments):
    """Training-only transform, calculated ONCE and reused by both arms."""
    x = np.concatenate([np.array([c.features() for c in f["contexts"]]) for f in fragments])
    mean, scale = x.mean(axis=0), x.std(axis=0, ddof=0)
    scale = np.where(scale > 1e-8, scale, 1.)
    return mean, scale


def fit_pair(fragments):
    """Exactly two matched fixed fits, 64 full-fragment CPU epochs each.

    Parent must first review the protocol and validate native adapter/data
    bindings. Calling this function starts real fitting; this delegated task
    did not call it. No validation or later dates influence normalization,
    epochs, costs, architecture, optimizer, seed, or checkpoint selection.
    """
    if [f.get("window_id") for f in fragments] != list(WINDOWS)[:3]:
        raise ValueError("Exactly Nov2022, Jan2023 and Jan-Apr2024 training fragments")
    identities = [validate_fragment(f, f["window_id"]) for f in fragments]
    for key in ("expert_identity_sha256", "mapper_sha256"):
        if len({i[key] for i in identities}) != 1:
            raise ValueError("Same frozen expert and mapper identity across all fragments")
    mean, scale = common_standardizer(fragments)
    result = {}
    for arm in ("IMITATE_REQUEST", "DIRECT_PATH_UTILITY"):
        head = SmallBudgetHead(mean, scale)
        first = {k: np.zeros_like(p) for k, p in head.parameters.items()}
        second = {k: np.zeros_like(p) for k, p in head.parameters.items()}
        began = time.monotonic()
        for epoch in range(1, EPOCHS + 1):
            if time.monotonic() - began > MAX_ARM_SECONDS:
                raise TimeoutError("Fixed 120-second arm budget exhausted; do not retune")
            loss, gradient, _ = loss_and_gradient(head, fragments, arm)
            norm = float(np.sqrt(sum(float((g * g).sum()) for g in gradient.values())))
            if not np.isfinite(loss) or not np.isfinite(norm):
                raise ValueError("Nonfinite pair loss/gradient; stop both arms")
            clip = min(1., 1. / norm) if norm else 1.
            for key, p in head.parameters.items():
                g = gradient[key] * clip
                first[key] = .9 * first[key] + .1 * g
                second[key] = .999 * second[key] + .001 * g * g
                m = first[key] / (1 - .9 ** epoch)
                v = second[key] / (1 - .999 ** epoch)
                p -= LEARNING_RATE * m / (np.sqrt(v) + 1e-8)
            if time.monotonic() - began > MAX_ARM_SECONDS:
                raise TimeoutError("Fixed 120-second arm budget exhausted; do not retune")
        result[arm] = head  # only epoch64; no best-validation or seed selection
    return result
