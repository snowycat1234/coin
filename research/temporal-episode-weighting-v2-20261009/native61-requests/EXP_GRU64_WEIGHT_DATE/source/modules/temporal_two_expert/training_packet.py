"""Minimal frozen handoff: verified features, five real wallets, original seen dev."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .development_inputs import load_development_inputs
from .exact import Episode, load_prototype, sha
from .feature_windows import TRAINING_CUTOFF_US, load_feature_inputs
from .inputs import CORE5, DAY_US, digest
from .model import E5_EXPERT_ORDER

NAMED_ORDER = ("CASH", "VOL_MANAGED_HOLD", "CSMOM21")
NAMED_SLOTS = np.array([0, 1, 4])
ECONOMIC_SHA = "66c5fdb2317689ed1d084c3f8eeb6e1781fa04ccc15e6243784a03a3555e7676"
READY_SHA = "ca9bc89060fd23e6aedd1d52c04f2c100bb52053eca2e2ad8eed04baff254efe"
ECONOMIC_COMMIT = "390271379f24b251eb0659d1e8c62db2c4917af9"
ECONOMIC_FIELDS = {
    "decision_us",
    "episode_id",
    "symbol_order",
    "expert_order",
    "original_E5_indices",
    "expert_targets",
    "expert_raw_targets",
    "expert_eligible",
    "expert_asset_eligible",
    "target_available_us",
    "past_returns30",
    "completed_decision_daily_close",
    "start_execution_us",
    "end_execution_us",
    "start_price",
    "end_price",
    "funding_per_unit",
}
MARKET13 = (
    "mom1",
    "mom5",
    "mom20",
    "mom60",
    "mom200",
    "vol30",
    "vol200",
    "dist50",
    "dist200",
    "funding",
    "breadth20",
    "dispersion20",
    "market_vol20",
)


def named_context(prototype, decision, targets, eligible, past, market, available):
    """Representation only: named 3 -> legacy indices0/1/4; others impossible."""
    t = np.zeros((5, 5), dtype=np.float64)
    e = np.zeros(5, dtype=bool)
    c = np.full(5, decision, dtype=np.int64)
    if (
        np.asarray(targets).shape != (3, 5)
        or np.asarray(eligible).shape != (3,)
        or np.asarray(eligible).dtype != bool
        or np.asarray(available).shape != (3,)
    ):
        raise ValueError("Explicit named three-slot targets/eligibility/availability required")
    t[NAMED_SLOTS], e[NAMED_SLOTS], c[NAMED_SLOTS] = targets, eligible, available
    context = prototype.Context(int(decision), int(decision), t, e, past, market, c)
    context.validate()
    return context


def load_training_contexts(inputs, npz_path, ready_path, prototype):
    if sha(npz_path) != ECONOMIC_SHA or sha(ready_path) != READY_SHA:
        raise ValueError("Exact producer-verified economic payload and readiness receipt required")
    ready = json.loads(Path(ready_path).read_text())
    if (
        ready.get("schema") != "PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXT_READY_V1"
        or ready.get("status") != "READY_FOR_FROZEN_TRAINING_PLAN_NOT_TRAINED"
        or ready.get("input_identity") != inputs.identity
        or ready.get("training_cutoff_us") != TRAINING_CUTOFF_US
        or ready.get("expert_order") != list(NAMED_ORDER)
        or ready.get("original_E5_indices") != NAMED_SLOTS.tolist()
    ):
        raise ValueError("Economic source/order/input/cutoff binding differs")
    with np.load(npz_path, allow_pickle=False) as z:
        if set(z.files) != ECONOMIC_FIELDS:
            raise ValueError("Exact named economic context schema required")
        a = {k: z[k].copy() for k in z.files}
    if (
        tuple(a["symbol_order"]) != CORE5
        or tuple(a["expert_order"]) != NAMED_ORDER
        or not np.array_equal(a["original_E5_indices"], NAMED_SLOTS)
        or len(a["decision_us"]) != 778
        or not np.all(np.diff(a["decision_us"]) > 0)
        or np.any(a["end_execution_us"] >= TRAINING_CUTOFF_US)
        or np.any(a["start_execution_us"] < a["decision_us"])
        or np.any(a["target_available_us"] > a["decision_us"][:, None])
        or not np.array_equal(
            a["expert_targets"][~a["expert_asset_eligible"]],
            np.zeros_like(a["expert_targets"][~a["expert_asset_eligible"]]),
        )
    ):
        raise ValueError("Frozen causal complete named contexts required")
    # Compatibility-only field for the retired 43-feature head. Neither the
    # unchanged mapper/loss nor this neural model reads Context.market13.
    # A known constant is not an observation or an economic missing-value fill.
    market = np.zeros((len(a["decision_us"]), 13), dtype=np.float64)
    contexts = tuple(
        named_context(
            prototype,
            d,
            a["expert_targets"][i],
            a["expert_eligible"][i],
            a["past_returns30"][i],
            market[i],
            a["target_available_us"][i],
        )
        for i, d in enumerate(a["decision_us"])
    )
    episodes = []
    for entry in ready["episodes"]:
        rows = np.flatnonzero(a["episode_id"] == entry["id"])
        decisions = a["decision_us"][rows]
        if (
            len(rows) != entry["decisions"]
            or decisions[0] != entry["first_decision_us"]
            or decisions[-1] != entry["last_decision_us"]
            or not np.all(np.diff(rows) == 1)
            or not np.array_equal(a["end_price"][rows[:-1]], a["start_price"][rows[1:]])
        ):
            raise ValueError("A genuine continuous economic wallet is required")
        prices = np.concatenate((a["start_price"][rows], a["end_price"][rows[-1:]]))
        episodes.append(
            Episode(
                "PRE_MAY_EPISODE_" + str(entry["id"]),
                inputs.windows(decisions),
                tuple(contexts[i] for i in rows),
                prices,
                a["funding_per_unit"][rows],
                a["end_execution_us"][rows],
                int(decisions[0]),
                int(decisions[-1]) + DAY_US,
                TRAINING_CUTOFF_US,
                "TRAIN",
                ECONOMIC_SHA,
            )
        )
    if len(episodes) != 5 or sum(len(e.contexts) for e in episodes) != 778:
        raise ValueError("Exactly five frozen economic episodes required")
    return tuple(episodes)


def load_original_development(inputs, recovery, prototype):
    """Original byte-bound May–June proxy dependencies; no new economic downloads."""
    root = Path(recovery) / "direct_path_fragments"
    index_path = root / "INDEX.json"
    index = json.loads(index_path.read_text())
    entry = next(e for e in index["fragments"] if e["window_id"] == "H1_VALIDATE")
    path = root / entry["file"]
    if sha(path) != entry["sha256"] or tuple(index["market13_order"]) != tuple(
        "BTC_" + k if i < 10 else k for i, k in enumerate(MARKET13)
    ):
        raise ValueError("Original development dependencies required")
    with np.load(path, allow_pickle=False) as z:
        a = {k: z[k].copy() for k in z.files}
    if (
        tuple(a["symbol_order"]) != CORE5
        or tuple(a["expert_order"]) != E5_EXPERT_ORDER
        or not np.array_equal(a["global_forced_terminal_day"], np.arange(61) == 60)
    ):
        raise ValueError("Original CORE5/E5 development contract required")
    d = a["decision_us"]
    contexts = tuple(
        named_context(
            prototype,
            t,
            a["expert_targets"][i, NAMED_SLOTS],
            a["expert_eligible"][i, NAMED_SLOTS],
            a["past_returns30"][i],
            a["market_state13"][i],
            a["target_available_us"][i, NAMED_SLOTS],
        )
        for i, t in enumerate(d)
    )
    return (
        Episode(
            "ORIGINAL_SEEN_MAY_JUNE",
            inputs.windows(d),
            contexts,
            a["prices"],
            a["funding_coeff"],
            a["label_available_us"],
            int(d[0]),
            int(d[-1]) + DAY_US,
            int(d[-1]) + 2 * DAY_US,
            "SEEN_VALIDATION",
            sha(path),
        ),
    )


def load_packet(path, expected_sha256, prototype_path):
    path = Path(path).resolve()
    if sha(path) != expected_sha256:
        raise ValueError("Exact frozen packet SHA required")
    packet = json.loads(path.read_text())
    if (
        packet.get("schema") != "TEMPORAL_FROZEN_FOUR_FIT_PACKET_V1"
        or packet.get("status") != "FROZEN"
    ):
        raise ValueError("Frozen economic/input packet required before any scaler or fit")
    required = {
        "feature_npz",
        "feature_manifest",
        "development_npz",
        "development_manifest",
        "economic_npz",
        "economic_ready",
        "recovery_index",
    }
    if set(packet["files"]) != required:
        raise ValueError("Exact frozen input file set required")
    paths = {}
    for key, entry in packet["files"].items():
        file = (path.parent / entry["path"]).resolve()
        if not file.is_relative_to(path.parent) or sha(file) != entry["SHA256"]:
            raise ValueError("Byte-bound local packet files only")
        paths[key] = file
    prototype = load_prototype(prototype_path)
    inputs = load_feature_inputs(paths["feature_npz"], paths["feature_manifest"])
    train = load_training_contexts(
        inputs, paths["economic_npz"], paths["economic_ready"], prototype
    )
    dev_inputs = load_development_inputs(
        inputs, paths["development_npz"], paths["development_manifest"]
    )
    recovery = paths["recovery_index"].parent.parent
    development = load_original_development(dev_inputs, recovery, prototype)
    identity = dict(
        packet_SHA256=expected_sha256,
        frozen=packet,
        training_input_identity=inputs.identity,
        development_input_identity=dev_inputs.identity,
        representation="named3_to_E5_014_unused_ineligible",
        source_economics_commit=ECONOMIC_COMMIT,
        scaler_rows="union_declared_training_windows_only",
        wallet_resets="five_real_gaps_fresh_CASH_each;paid_terminal_close",
        development="original_seen_MayJune_daily_proxy;not_native_or_OOS",
    )
    return train, development, prototype, dict(identity, identity_SHA256=digest(identity))
