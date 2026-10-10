import json
import subprocess
from pathlib import Path

import numpy as np

from modules.temporal_fresh_initialization.export import feature_clock
from modules.temporal_july_transfer.data import load
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import array_digest, digest

from .models import commit_bytes
from .protocol import CONTROLS, MODELS, OLD, ROOT, SCALER


def inputs(state, economics):
    episode, prototype, legacy_scaler, receipt = load(state, economics)
    if sha(OLD / "MANIFEST.json") != commit_bytes(
        "90b8fd65d092b52091b3fee7717c0478b265bc6e",
        str((OLD / "MANIFEST.json").relative_to(ROOT)),
    ):
        raise ValueError("Pinned original July manifest required before reading control identities")
    manifest = json.loads((OLD / "MANIFEST.json").read_text())
    if not {"RESULT.json", "CURRENT_CONTEXT.npz", "FEATURE_ROWS.npz"} <= manifest["files"].keys():
        raise ValueError("Complete saved control/input manifest required")
    for name, entry in manifest["files"].items():
        if sha(OLD / name) != entry["SHA256"] or sha(OLD / name) != commit_bytes(
            "90b8fd65d092b52091b3fee7717c0478b265bc6e",
            str((OLD / name).relative_to(ROOT)),
        ):
            raise ValueError("Pinned saved July input/control/result bytes changed")
    if episode.identity != manifest["episode_identity"]:
        raise ValueError("Exact original July episode identity required")
    context = dict(
        decision_us=episode.windows.decision_us,
        expert_targets=episode.expert_targets,
        expert_eligible=episode.eligible,
        target_available_us=episode.target_available_us,
        past_returns30=np.stack([c.past_returns30 for c in episode.contexts]),
        expert_state=episode.expert_state,
        expert_input_available_us=episode.expert_input_available_us,
        prices=episode.prices,
        funding_coeff=episode.funding_coeff,
        outcome_available_us=episode.label_available_us,
    )
    with np.load(OLD / "CURRENT_CONTEXT.npz", allow_pickle=False) as z:
        for name, actual in context.items():
            np.testing.assert_array_equal(z[name], actual)
    with np.load(OLD / "FEATURE_ROWS.npz", allow_pickle=False) as z:
        for i in range(63):
            for name, actual in dict(
                values=episode.windows.values,
                valid=episode.windows.valid,
                step_valid=episode.windows.step_valid,
            ).items():
                np.testing.assert_array_equal(z[name][i : i + 64], actual[i])
        feature_identity = array_digest(z["values"])
        clock_identity = array_digest(z["completed_us"])
    if np.any(feature_clock(episode) > episode.windows.decision_us):
        raise ValueError("Causal feature/expert clock required")
    saved = json.loads((OLD / "RESULT.json").read_text())
    controls = {n: saved["policies"][n] for n in CONTROLS}
    result = dict(
        receipt,
        original_loader_scaler_identity=legacy_scaler.identity,
        scaler_identity=SCALER,
        scaler_rows=907,
        controls_reused=CONTROLS,
    )
    binding = dict(
        episode_identity=episode.identity,
        feature_identity=feature_identity,
        feature_clock_identity=clock_identity,
        context_identity=digest({k: array_digest(v) for k, v in context.items()}),
        control_RESULT_SHA256=sha(OLD / "RESULT.json"),
        data=result,
    )
    return episode, prototype, result, binding, controls


def prior_paths(state):
    """Check saved result receipts before deciding which actual paths need execution."""
    tracked = subprocess.run(
        ["git", "ls-files", "research"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    files = {ROOT / n for n in tracked if n.endswith("/RESULT.json")}
    files.update(Path(state).rglob("RESULT.json"))
    candidates, exact = [], []
    for path in sorted(files):
        r = json.loads(path.read_text())
        for name, entry in MODELS.items():
            if r.get("model_identity") == entry["model_identity"]:
                candidates.append(
                    dict(
                        path=str(path),
                        policy=name,
                        checkpoint_SHA256=r.get("checkpoint_SHA256"),
                        calendar=r.get("calendar"),
                        classification=r.get("classification"),
                    )
                )
                if (
                    r.get("checkpoint_SHA256") == entry["checkpoint_SHA256"]
                    and r.get("calendar", {}).get("start_us") == 1719792000000000
                    and r.get("calendar", {}).get("end_exclusive_us") == 1725235200000000
                ):
                    exact.append(str(path))
    if exact:
        raise ValueError(
            "Exact prior July path found; bind and reuse before any new execution: " + str(exact)
        )
    return dict(
        saved_RESULT_receipts_checked=len(files),
        targeted_model_candidates=candidates,
        exact_July_paths_found=0,
        earlier_April512_path_not_equivalent=True,
    )
