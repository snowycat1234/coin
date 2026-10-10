"""Pinned serialized historical evaluation inputs, separate from training loader."""

import json
from pathlib import Path

import numpy as np

from modules.temporal_added_history_july.models import commit_bytes
from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_q4_reserved.data import TerminalEpisode
from modules.temporal_short_expansion.adapter import append_episode
from modules.temporal_two_expert.exact import load_prototype, sha
from modules.temporal_two_expert.inputs import DAY_US, FeatureTimeline, digest
from modules.temporal_two_expert.training_packet import named_context

from .protocol import ROOT


def q4_inputs(state):
    folder = ROOT / "research/temporal-selected-refit-q4-20261010/q4-results"
    commit = "657aeaff93889da600ad88b3603739508ba03216"
    mpath = folder / "MANIFEST.json"
    assert sha(mpath) == commit_bytes(commit, str(mpath.relative_to(ROOT)))
    manifest = json.loads(mpath.read_text())
    for n in ("CURRENT_CONTEXT.npz", "FEATURE_ROWS.npz", "INPUT_RECEIPT.json", "RESULT.json"):
        p = folder / n
        assert (
            sha(p)
            == manifest["files"][n]["SHA256"]
            == commit_bytes(commit, str(p.relative_to(ROOT)))
        )
    receipt = json.loads((folder / "INPUT_RECEIPT.json").read_text())
    with np.load(folder / "CURRENT_CONTEXT.npz", allow_pickle=False) as z:
        c = {k: z[k].copy() for k in z.files}
    with np.load(folder / "FEATURE_ROWS.npz", allow_pickle=False) as z:
        f = {k: z[k].copy() for k in z.files}
    src = receipt["primitive_SHA256"]
    d = c["decision_us"]
    timeline = FeatureTimeline(
        f["values"],
        f["valid"],
        f["step_valid"],
        f["completed_us"],
        np.broadcast_to(f["completed_us"][:, None, None], f["values"].shape).copy(),
        digest(src),
    )
    prototype = load_prototype(Path(state) / "recovery/source/modules/direct_path/prototype.py")
    contexts = tuple(
        named_context(
            prototype,
            int(t),
            c["expert_targets"][i, [0, 1, 4]],
            c["expert_eligible"][i, [0, 1, 4]],
            c["past_returns30"][i],
            np.zeros(13),
            c["target_available_us"][i, [0, 1, 4]],
        )
        for i, t in enumerate(d)
    )
    provenance = {
        k: receipt[k]
        for k in ("primitive_SHA256", "risk_sources", "short_producer_SHA256", "economics")
    }
    episode = TerminalEpisode(
        "FIXED_Q4_SELECTED256",
        timeline.windows(d),
        contexts,
        c["prices"],
        c["funding_coeff"],
        c["outcome_available_us"],
        int(d[0]),
        int(d[-1] + DAY_US),
        int(d[-1] + 2 * DAY_US),
        "SEEN_VALIDATION",
        digest(provenance),
    )
    e = expose_episode(
        append_episode(
            episode,
            c["expert_targets"][:, 5:6],
            c["expert_eligible"][:, 5:6],
            c["target_available_us"][:, 5:6],
            prototype,
            digest(dict(recipe=receipt["short_producer_SHA256"], source=src)),
        )
    )
    assert e.identity == manifest["episode_identity"] == receipt["episode_identity"]
    for k, v in dict(
        expert_targets=e.expert_targets,
        expert_eligible=e.eligible,
        expert_state=e.expert_state,
        input_available_us=e.expert_input_available_us,
    ).items():
        np.testing.assert_array_equal(c[k], v)
    return e, prototype, receipt
