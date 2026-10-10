"""Source-verified six-wallet assembly without any new normalization fit."""

import numpy as np

from modules.temporal_history_expansion.data import cached_inputs, new_episodes
from modules.temporal_history_expansion.packet import load_packet
from modules.temporal_selected_refit.stage import inputs as original_inputs
from modules.temporal_two_expert.inputs import DAY_US, array_digest, digest

from .protocol import CONSUMER_SHA, SCALER, SOURCE_COMMIT


def combine(original, added, scaler):
    original, added = tuple(original), tuple(added)
    if (
        [len(e.contexts) for e in original] != [54, 88, 62, 144, 430]
        or [len(e.contexts) for e in added] != [365]
        or scaler.identity != SCALER
        or scaler.provenance["real_row_count"] != 907
    ):
        raise ValueError("Exactly original five wallets, full2021 and unchanged907 scaler required")
    combined = added + original
    decisions, active = [], []
    for e in combined:
        d = e.windows.decision_us
        if (
            e.role != "TRAIN"
            or not np.array_equal(d, np.arange(e.start_us, e.end_us, DAY_US))
            or np.any(e.label_available_us >= e.split_cutoff_us)
            or any(
                c.past_returns30.shape != (30, 5) or not np.isfinite(c.past_returns30).all()
                for c in e.contexts
            )
        ):
            raise ValueError("Complete causal mature fixed5 training chronology required")
        decisions.extend(d.tolist())
        active.extend(d[:-1].tolist())
    if (
        len(decisions) != 1143
        or len(set(decisions)) != 1143
        or len(active) != 1137
        or len(set(active)) != 1137
        or any(a.end_us > b.start_us for a, b in zip(combined, combined[1:], strict=False))
    ):
        raise ValueError("1137 distinct active intervals and six nonoverlapping wallets required")
    if not all(a is b for a, b in zip(combined[-5:], original, strict=True)):
        raise ValueError("Original five objects must remain unchanged")
    old_rows = {int(t) for e in original for t in e.windows.completed_us.ravel()}
    added_rows = set(map(int, np.unique(added[0].windows.completed_us)))
    counts = dict(
        before_active=773,
        added_active=364,
        after_active=1137,
        decisions=1143,
        duplicate_decisions=0,
        wallets=6,
        paid_closures=6,
        wallet_lengths=[len(e.contexts) for e in combined],
        date_weights=[len(e.contexts) / 1143 for e in combined],
        original_identities=[e.identity for e in original],
        original_boundaries=[[e.start_us, e.end_us] for e in original],
        original_objects_retained=True,
        expanded_identities=[e.identity for e in combined],
        active_date_SHA256=array_digest(np.array(active, dtype=np.int64)),
        feature_rows=dict(
            old=907,
            new_candidate=428,
            overlap=len(old_rows & added_rows),
            unique_added=len(added_rows - old_rows),
            expanded_union=len(old_rows | added_rows),
        ),
        normalization_refitted=False,
        scaler_rows=907,
        scaler_identity=scaler.identity,
        old_scaler_object_retained=True,
    )
    return combined, scaler, counts


def inputs(state, economics):
    original, prototype, previous_data, scaler = original_inputs(state)
    causal = cached_inputs(state, prototype)
    packet = load_packet(economics, source_commit=SOURCE_COMMIT, consumer_sha256=CONSUMER_SHA)
    added, admission = new_episodes(packet, causal, prototype)
    if admission["admitted_active_intervals"] != 364 or admission["rejected_active_intervals"]:
        raise ValueError("Reviewed packet must add exactly364 intervals with zero exclusions")
    train, same_scaler, counts = combine(original, added, scaler)
    data = dict(
        previous_data_identity=digest(previous_data),
        packet=packet.identity,
        source=packet.receipt,
        causal=causal.receipt,
        admission=admission,
        counts=counts,
    )
    return train, prototype, data, same_scaler
