"""Restore exactly the existing six training wallets, then refit training-only scale."""

import json
from pathlib import Path

from modules.temporal_added_history_july.models import shared_scaler
from modules.temporal_expanded_refit.data import combine
from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_history_expansion.data import cached_inputs, new_episodes
from modules.temporal_history_expansion.packet import load_packet
from modules.temporal_short_expansion.adapter import load_short_pack
from modules.temporal_two_expert.exact import load_prototype
from modules.temporal_two_expert.feature_windows import load_feature_inputs
from modules.temporal_two_expert.inputs import digest, fit_standardizer
from modules.temporal_two_expert.training_packet import load_training_contexts

from .protocol import CONSUMER_SHA, ROOT, SOURCE_COMMIT


def inputs(state, economics):
    state = Path(state)
    prototype = load_prototype(state / "recovery/source/modules/direct_path/prototype.py")
    folder = state / "feature-input/verified"
    features = load_feature_inputs(
        folder / "features/CORE5_PRE_MAY2024.npz", folder / "FEATURE_MANIFEST.json"
    )
    original = load_training_contexts(
        features,
        state / "economic-contexts/CONTEXTS.npz",
        state / "economic-contexts/TRAIN_CONTEXT_READY.json",
        prototype,
    )
    original = tuple(
        map(
            expose_episode,
            load_short_pack(state / "short-source", original, prototype, training=True),
        )
    )
    old_scaler = shared_scaler()
    old_refit = fit_standardizer(
        [e.windows for e in original], training_cutoff_us=original[0].split_cutoff_us
    )
    assert old_refit.identity == old_scaler.identity
    causal = cached_inputs(state, prototype)
    packet = load_packet(economics, source_commit=SOURCE_COMMIT, consumer_sha256=CONSUMER_SHA)
    added, admission = new_episodes(packet, causal, prototype)
    train, _, counts = combine(original, added, old_scaler)
    old = json.loads(
        (ROOT / "research/temporal-expanded-refit-q4-20261010/frozen/RUN.json").read_text()
    )["specification"]["data_split_identity"]
    assert (
        counts == old["counts"]
        and packet.identity == old["packet"]
        and admission == old["admission"]
        and causal.receipt == old["causal"]
    )
    scaler = fit_standardizer(
        [e.windows for e in train], training_cutoff_us=train[0].split_cutoff_us
    )
    assert scaler.provenance["real_row_count"] == 1273 and scaler.identity != old_scaler.identity
    current_counts = dict(
        counts,
        scaler_rows=1273,
        scaler_identity=scaler.identity,
        normalization_refitted=True,
        old_scaler_object_retained=False,
    )
    data = dict(
        original_data_identity=digest(old),
        episode_identities=[e.identity for e in train],
        counts=current_counts,
        normalization=dict(
            previous=old_scaler.identity,
            current=scaler.identity,
            unique_rows=1273,
            cutoff_us=train[0].split_cutoff_us,
            algorithm="unchanged unique valid rows mean/std ddof0",
        ),
        packet=packet.identity,
    )
    return train, prototype, data, scaler
