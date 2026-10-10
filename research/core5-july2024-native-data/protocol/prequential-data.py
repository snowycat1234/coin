"""Causal prefix adapters; no inherited model/scaler or development inputs."""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_short_expansion.adapter import ExpandedEpisode, load_short_pack
from modules.temporal_two_expert.exact import load_prototype, sha, verify_prototype
from modules.temporal_two_expert.feature_windows import load_feature_inputs
from modules.temporal_two_expert.inputs import DAY_US, WindowBatch, digest, fit_standardizer
from modules.temporal_two_expert.training_packet import ECONOMIC_SHA, load_training_contexts

PACKET_SHA = "0bd135091a913d67fec6af6da1f51a8cda80a09eca1da5a64582ebe68302ddea"
EXECUTION_DELAY_US = 60000001


def load_source(state, *, prototype=None):
    state = Path(state).resolve()
    packet_path = state / "FROZEN_PACKET.json"
    if sha(packet_path) != PACKET_SHA:
        raise ValueError("Exact existing frozen packet required")
    packet = json.loads(packet_path.read_text())
    paths = {}
    # Do not open May-June development inputs, full778 scalers, or old models.
    for key in ("feature_npz", "feature_manifest", "economic_npz", "economic_ready"):
        entry = packet["files"][key]
        path = (state / entry["path"]).resolve()
        if not path.is_relative_to(state) or sha(path) != entry["SHA256"]:
            raise ValueError("Byte-bound local input required")
        paths[key] = path
    if prototype is None:
        prototype = load_prototype(state / "recovery/source/modules/direct_path/prototype.py")
    else:
        verify_prototype(prototype)
    features = load_feature_inputs(paths["feature_npz"], paths["feature_manifest"])
    base = load_training_contexts(
        features, paths["economic_npz"], paths["economic_ready"], prototype
    )
    expanded = load_short_pack(state / "short-source", base, prototype, training=True)
    with np.load(paths["economic_npz"], allow_pickle=False) as z:
        decisions, starts, ends = (
            z[k].copy() for k in ("decision_us", "start_execution_us", "end_execution_us")
        )
    if not np.array_equal(starts, decisions + EXECUTION_DELAY_US) or not np.array_equal(
        ends, starts + DAY_US
    ):
        raise ValueError("Exact producer execution and outcome clocks required")
    clocks = {int(d): int(s) for d, s in zip(decisions, starts, strict=True)}
    return expanded, prototype, clocks


def close_slice(expanded, start, stop, *, cutoff_us, role, wallet_id, execution_clocks):
    """Declare one contiguous wallet and paid closure, without reading a cash suffix outcome."""
    base = expanded.original
    n = len(base.contexts)
    if not 0 <= start < stop <= n or stop - start < 2:
        raise ValueError("At least two contiguous original decisions required")
    d = base.windows.decision_us[start:stop]
    terminal_clock = execution_clocks[int(d[-1])]
    active_clocks = base.label_available_us[start : stop - 1]
    if np.any(active_clocks >= cutoff_us) or terminal_clock >= cutoff_us:
        raise ValueError("Every active outcome and paid terminal close must precede cutoff")
    if int(active_clocks[-1]) != terminal_clock:
        raise ValueError("Last active mark and terminal fill must share producer price/clock")
    w = base.windows
    windows = WindowBatch(
        *(
            getattr(w, key)[start:stop]
            for key in (
                "values",
                "valid",
                "step_valid",
                "completed_us",
                "available_us",
                "decision_us",
            )
        ),
        w.source_sha256,
    )
    # The ABI has n+1 prices and n funding rows. Once forced CASH at n-1,
    # the final interval is structurally flat, so its suffix is a known identity
    # operation, not a missing observation filled with zero. Never read p[stop]
    # or funding[stop-1], which may belong to the future forward interval.
    prices = np.concatenate((base.prices[start:stop], base.prices[stop - 1 : stop]))
    funding = np.concatenate((base.funding_coeff[start : stop - 1], np.zeros((1, 5))))
    labels = np.concatenate((active_clocks, np.array([terminal_clock], np.int64)))
    original = replace(
        base,
        wallet_id=wallet_id,
        windows=windows,
        contexts=base.contexts[start:stop],
        prices=prices,
        funding_coeff=funding,
        label_available_us=labels,
        start_us=int(d[0]),
        end_us=int(d[-1]) + DAY_US,
        split_cutoff_us=cutoff_us,
        role=role,
    )
    internal = replace(original, contexts=expanded.internal.contexts[start:stop])
    sliced = ExpandedEpisode(
        original,
        internal,
        expanded.expert_targets[start:stop],
        expanded.eligible[start:stop],
        expanded.target_available_us[start:stop],
        expanded.payload_sha256,
    )
    episode = expose_episode(sliced)
    proof = dict(
        wallet_id=wallet_id,
        original_wallet_id=base.wallet_id,
        rows=[start, stop],
        decisions=len(d),
        active_intervals=len(d) - 1,
        first_decision_us=int(d[0]),
        last_decision_us=int(d[-1]),
        latest_active_outcome_available_us=int(active_clocks.max()),
        paid_terminal_close_available_us=terminal_clock,
        cutoff_us=cutoff_us,
        terminal_price_equals_last_active_end=True,
        terminal_suffix="known_CASH_identity;repeat_observed_close_price;zero_funding",
        no_future_suffix_consumed=True,
        identity=episode.identity,
    )
    return episode, proof


def fold_inputs(source, execution_clocks, start_us, fold_id):
    train, proofs = [], []
    end_us = start_us + 63 * DAY_US
    forward, forward_proof = None, None
    for e in source:
        d = e.windows.decision_us
        rows = np.flatnonzero(d < start_us)
        if len(rows) >= 2:
            if not np.array_equal(rows, np.arange(len(rows))):
                raise ValueError("Training must retain an original-wallet prefix")
            episode, proof = close_slice(
                e,
                0,
                len(rows),
                cutoff_us=start_us,
                role="TRAIN",
                wallet_id=e.wallet_id + "__PREFIX_" + fold_id,
                execution_clocks=execution_clocks,
            )
            train.append(episode)
            proofs.append(proof)
        rows = np.flatnonzero((d >= start_us) & (d < end_us))
        if len(rows):
            if forward is not None or len(rows) != 63 or not np.all(np.diff(rows) == 1):
                raise ValueError("One intact63-decision forward wallet required")
            forward, forward_proof = close_slice(
                e,
                int(rows[0]),
                int(rows[-1]) + 1,
                cutoff_us=end_us + DAY_US,
                role="SEEN_VALIDATION",
                wallet_id="FORWARD63_" + fold_id,
                execution_clocks=execution_clocks,
            )
    if not train or forward is None:
        raise ValueError("Admissible train and forward wallets required")
    train = tuple(train)
    scaler = fit_standardizer([e.windows for e in train], training_cutoff_us=start_us)
    receipt = dict(
        fold_id=fold_id,
        first_forward_decision_us=start_us,
        forward_end_exclusive_us=end_us,
        training_decisions=sum(len(e.contexts) for e in train),
        training_wallets=proofs,
        forward=forward_proof,
        scaler_identity=scaler.identity,
        scaler_provenance=scaler.provenance,
        additional_embargo_days=0,
        maturity="all_active_outcomes_and_paid_prefix_close_strictly_before_first_forward_decision",
        training_label_horizon="complete_admitted_wallet_prefix_through_paid_close;no_rolling63day_labels",
        shared_past_feature_history_allowed=True,
        proxy_publication_clock_uncertified=True,
    )
    data = dict(
        packet_SHA256=PACKET_SHA,
        economic_SHA256=ECONOMIC_SHA,
        train=[e.identity for e in train],
        forward=forward.identity,
        fold=receipt,
    )
    return train, forward, scaler, dict(data, identity=digest(data)), receipt
