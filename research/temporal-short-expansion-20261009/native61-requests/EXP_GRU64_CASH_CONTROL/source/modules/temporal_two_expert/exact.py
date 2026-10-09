"""Import the unchanged, byte-bound recovered objective; bridge its exact VJP."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from .inputs import DAY_US, WindowBatch, array_digest, digest, require_sha
from .model import predict_windows

RECOVERY_SHA256 = "040429b7de82fcb3efb0f2391701d60349bd02c81f59b3749c28b11ea903551a"
PROTOTYPE_SHA256 = "46a0ca0b76bf29d50133bdd85b5730f4fd029f05378ce2ef086752b869a8fcab"
RECOVERY_ZIP = (
    Path(__file__).resolve().parents[2]
    / "research"
    / "two-expert-exact-recovery-20261009"
    / "coin_two_expert_public_exact_recovery_20261009.zip"
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_recovery(destination):
    """Explicit local-only restoration of the already public ZIP; no fitting."""
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("Use an exclusive new recovery destination")
    if sha(RECOVERY_ZIP) != RECOVERY_SHA256:
        raise ValueError("Exact public recovery archive required")
    with zipfile.ZipFile(RECOVERY_ZIP) as archive:
        if archive.testzip() is not None:
            raise ValueError("Recovery ZIP CRC failure")
        for name in archive.namelist():
            if not (destination / name).resolve().is_relative_to(destination):
                raise ValueError("Unsafe recovery member")
        archive.extractall(destination)
    load_prototype(destination / "source/modules/direct_path/prototype.py")
    return destination


def load_prototype(path):
    """Import exact source under an isolated module name, without overrides."""
    path = Path(path).resolve()
    if sha(path) != PROTOTYPE_SHA256:
        raise ValueError("Exact recovered prototype source required")
    name = "_coin_temporal_exact_prototype_" + PROTOTYPE_SHA256
    if name in sys.modules:
        module = sys.modules[name]
        if Path(module.__file__).resolve() != path:
            raise ValueError("Recovered prototype already loaded from another path")
        return module
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def verify_prototype(prototype):
    if sha(prototype.__file__) != PROTOTYPE_SHA256:
        raise ValueError("Recovered computational source changed")


@dataclass(frozen=True)
class Episode:
    """One producer-declared complete wallet; feature chunks cannot split it.

    start_us/end_us bind the whole wallet interval, end exclusive. Its last
    decision is the common paid flattening day. Active TRAIN labels must mature
    before split_cutoff_us; completed warmup rows are feature-only, never resets.
    """

    wallet_id: str
    windows: WindowBatch
    contexts: tuple
    prices: np.ndarray
    funding_coeff: np.ndarray
    label_available_us: np.ndarray
    start_us: int
    end_us: int
    split_cutoff_us: int
    role: str
    producer_sha256: str

    def __post_init__(self):
        if (
            not isinstance(self.wallet_id, str)
            or not self.wallet_id
            or self.role not in ("TRAIN", "SEEN_VALIDATION")
            or any(
                type(t) is not int or t < 0 or t % DAY_US
                for t in (self.start_us, self.end_us, self.split_cutoff_us)
            )
            or self.end_us > self.split_cutoff_us
        ):
            raise ValueError("Explicit whole-wallet interval, data role and split cutoff required")
        decisions = np.asarray([c.decision_us for c in self.contexts], dtype=np.int64)
        if (
            len(decisions) < 2
            or not np.array_equal(decisions, np.arange(self.start_us, self.end_us, DAY_US))
            or not np.array_equal(decisions, self.windows.decision_us)
        ):
            raise ValueError("Complete chronological wallet and matching windows required")
        for c in self.contexts:
            c.validate()
        labels = np.asarray(self.label_available_us)
        if (
            labels.shape != decisions.shape
            or labels.dtype.kind not in "iu"
            or np.any(labels < 0)
            or np.any(labels[:-1] < decisions[:-1] + DAY_US)
            or np.any(labels[:-1] >= self.split_cutoff_us)
        ):
            raise ValueError("Every active own-path outcome must mature before split cutoff")
        prices, funding = map(np.asarray, (self.prices, self.funding_coeff))
        if (
            prices.shape != (len(decisions) + 1, 5)
            or funding.shape != (len(decisions), 5)
            or not np.isfinite(prices).all()
            or not np.isfinite(funding).all()
            or np.any(prices <= 0)
        ):
            raise ValueError(
                "Complete positive prices and event-mark funding coefficients required"
            )
        require_sha(self.producer_sha256)
        # The original contract excludes the forced terminal action from future
        # label maturity: its paid close is known at that decision. Preserve it.
        # Freeze caller-owned arrays so a concurrent producer cannot mutate the
        # in-memory episode after its input/split identity has been bound.
        frozen_contexts = []
        for context in self.contexts:
            arrays = {}
            for field in (
                "expert_targets",
                "eligible",
                "past_returns30",
                "market13",
                "target_available_us",
            ):
                value = np.array(getattr(context, field), copy=True)
                value.flags.writeable = False
                arrays[field] = value
            frozen_contexts.append(replace(context, **arrays))
        object.__setattr__(self, "contexts", tuple(frozen_contexts))
        for name in ("prices", "funding_coeff", "label_available_us"):
            value = np.array(getattr(self, name), copy=True)
            value.flags.writeable = False
            object.__setattr__(self, name, value)

    @property
    def identity(self):
        contexts = [
            dict(
                decision=c.decision_us,
                available=c.available_us,
                **{
                    k: array_digest(getattr(c, k))
                    for k in (
                        "expert_targets",
                        "eligible",
                        "past_returns30",
                        "market13",
                        "target_available_us",
                    )
                },
            )
            for c in self.contexts
        ]
        return digest(
            dict(
                wallet_id=self.wallet_id,
                windows=self.windows.identity,
                contexts=contexts,
                prices=array_digest(self.prices),
                funding=array_digest(self.funding_coeff),
                labels=array_digest(self.label_available_us),
                start=self.start_us,
                end=self.end_us,
                cutoff=self.split_cutoff_us,
                role=self.role,
                producer=self.producer_sha256,
            )
        )


def request_loss_and_gradient(requests, episode, prototype):
    """Exactly the original own-path numerator and request VJP, no smoothing."""
    verify_prototype(prototype)
    targets, records = prototype.mapped_path(requests, episode.contexts)
    report = prototype.daily_proxy(targets, episode.prices, episode.funding_coeff)
    n = len(episode.contexts)
    gradient = -prototype.mapping_vjp(report["target_gradient"], records, episode.contexts) / n
    return -report["utility_sum"] / n, gradient, report


class _ExactPathLoss(torch.autograd.Function):
    @staticmethod
    def forward(ctx, requests, episode, prototype):
        loss, gradient, _ = request_loss_and_gradient(
            requests.detach().cpu().numpy(), episode, prototype
        )
        ctx.save_for_backward(torch.tensor(gradient, dtype=requests.dtype, device=requests.device))
        return requests.new_tensor(loss)

    @staticmethod
    def backward(ctx, upstream):
        (gradient,) = ctx.saved_tensors
        return upstream * gradient, None, None


def exact_path_loss(requests, episode, prototype):
    if (
        requests.dtype != torch.float64
        or requests.shape != (len(episode.contexts), 5)
        or not torch.isfinite(requests).all()
    ):
        raise ValueError("Chronological float64 E5 request path required")
    return _ExactPathLoss.apply(requests, episode, prototype)


def training_loss(model, episodes, prototype, *, feature_batch_size=32):
    """Row-weighted original objective, one full chronology per declared wallet.

    No optimizer update occurs here. No oracle, wallet features, minibatch
    resets, best-epoch selection, or data retrieval is added.
    """
    episodes = tuple(episodes)
    if (
        not episodes
        or any(e.role != "TRAIN" for e in episodes)
        or len({e.wallet_id for e in episodes}) != len(episodes)
    ):
        raise ValueError("Distinct complete TRAIN wallets required")
    if len({e.split_cutoff_us for e in episodes}) != 1:
        raise ValueError("Common training split cutoff required")
    ordered = sorted(episodes, key=lambda e: e.start_us)
    if any(a.end_us > b.start_us for a, b in zip(ordered, ordered[1:], strict=False)):
        raise ValueError("Overlapping wallets would double-count training chronology")
    total = sum(len(e.contexts) for e in episodes)
    losses = [
        exact_path_loss(
            predict_windows(model, e.windows, feature_batch_size=feature_batch_size), e, prototype
        )
        * len(e.contexts)
        for e in episodes
    ]
    return torch.stack(losses).sum() / total


def feature_chunk(windows, start, size):
    """Views of an already validated window batch; no new economic boundary."""
    return SimpleNamespace(
        **{
            name: getattr(windows, name)[start : start + size]
            for name in ("values", "valid", "step_valid")
        }
    )


def replay_request_gradients(
    model, windows, gradients, rng_states, requests, *, feature_batch_size
):
    """Bound graph memory to one feature chunk and replay identical dropout."""
    final_rng = torch.get_rng_state().clone()
    try:
        for k, start in enumerate(range(0, len(windows.values), feature_batch_size)):
            torch.set_rng_state(rng_states[k])
            output = predict_windows(
                model,
                feature_chunk(windows, start, feature_batch_size),
                feature_batch_size=feature_batch_size,
            )
            expected = torch.tensor(
                requests[start : start + feature_batch_size], dtype=output.dtype
            )
            if not torch.equal(output.detach().cpu(), expected):
                raise ValueError("Dropout/deterministic replay differs; preserve last checkpoint")
            output.backward(
                torch.tensor(
                    gradients[start : start + feature_batch_size],
                    dtype=output.dtype,
                    device=output.device,
                )
            )
    finally:
        # Replay does not consume a second random stream.
        torch.set_rng_state(final_rng)


def memory_bounded_gradients(model, episodes, prototype, *, feature_batch_size=32):
    """Exact full-path gradient with a two-pass exogenous feature calculation.

    First compute ordered requests without retaining graphs. Roll the *whole*
    wallet with the unchanged prototype, then replay feature chunks with their
    original RNG and exact request VJPs. Parameters stay fixed until every
    episode gradient is accumulated. No wallet or economic minibatch resets.
    """
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
        raise ValueError("Overlapping wallets would double-count training chronology")
    total = sum(len(e.contexts) for e in episodes)
    loss_sum = 0.0
    request_paths = []
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
        loss, gradients, _ = request_loss_and_gradient(requests, episode, prototype)
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
        request_paths.append(requests)
    return float(loss_sum), np.concatenate(request_paths)
