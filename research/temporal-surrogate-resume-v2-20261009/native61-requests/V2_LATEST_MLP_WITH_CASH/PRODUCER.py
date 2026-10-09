"""Export one terminal arm's actual frozen requests; no scoring or optimizer step."""

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from modules.temporal_surrogate_resume_v2.stage import (
    PROTOCOL_V2,
    load_inputs,
    original_model,
    stage_sources,
)
from modules.temporal_two_expert.checkpoint import load_checkpoint, make_optimizer, model_identity
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.model import E5_EXPERT_ORDER, predict_windows

ADAPTER_COMMIT = "0090a7182c75a655197afd85f4db2c66db6456f6"


def export(state, arm, destination, producer_commit):
    state, destination = Path(state).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("Immutable new native request bundle required")
    train, development, _, _, scaler = load_inputs(state)
    folder = state / "surrogate-v2" / arm
    terminal = json.loads((folder / "TERMINAL.json").read_text())
    binding = json.loads((folder / "RUN.json").read_text())
    pointer = json.loads((folder / "latest.json").read_text())
    assert binding["specification"]["algorithm"]["versioned_sources"] == stage_sources()
    assert terminal["model_identity"] == pointer["model_identity"]
    contract = binding["specification"]["model_contract"]
    model = original_model(scaler, contract["family"], contract["cash_enabled"])
    loaded = load_checkpoint(folder, model, make_optimizer(model), binding)
    assert loaded["model_identity"] == terminal["model_identity"]
    before = model_identity(model)
    model.eval()
    assert len(development) == 1
    episode = development[0]
    assert len(episode.contexts) == 61
    with torch.no_grad():
        requests = predict_windows(
            model, episode.windows, feature_batch_size=PROTOCOL_V2["feature_batch_size"]
        ).numpy()
    assert model_identity(model) == before
    order = tuple(E5_EXPERT_ORDER)
    allowed = (
        ("CASH", "VOL_MANAGED_HOLD", "CSMOM21")
        if model.cash_enabled
        else ("VOL_MANAGED_HOLD", "CSMOM21")
    )
    mask = (
        np.stack([c.eligible for c in episode.contexts])
        & np.array([name in allowed for name in order])[None]
    )
    if np.any(requests[~mask]):
        raise ValueError(
            "Raw frozen requests violate canonical admitted-action mask; no silent conversion"
        )
    feature_clock = np.maximum(
        np.where(episode.windows.valid, episode.windows.available_us, 0).max(axis=(1, 2, 3)),
        episode.windows.completed_us[:, -1],
    ).astype(np.int64)
    assert np.all(feature_clock <= episode.windows.decision_us)
    maximum_scaler_clock = max(
        int(np.where(e.windows.valid, e.windows.available_us, 0).max()) for e in train
    )
    cutoff = train[0].split_cutoff_us
    maximum_label = max(int(e.label_available_us.max()) for e in train)
    assert maximum_label < cutoff and maximum_scaler_clock <= cutoff
    root = Path(__file__).resolve().parents[2]
    producer_name = str(Path(__file__).resolve().relative_to(root))
    assert (
        subprocess.check_output(["git", "show", producer_commit + ":" + producer_name], cwd=root)
        == Path(__file__).read_bytes()
    )
    destination.mkdir(parents=True)
    np.savez_compressed(
        destination / "REQUESTS.npz",
        decision_us=episode.windows.decision_us.astype(np.int64),
        symbol_order=np.array(contract["symbols"]),
        expert_order=np.array(order),
        desired_expert_budget=requests.astype(np.float64),
        action_eligible=mask,
        feature_available_us=feature_clock,
        request_available_us=episode.windows.decision_us.astype(np.int64),
    )
    source_members = {
        "PRODUCER.py": Path(__file__).resolve(),
        "MODEL_SOURCE.py": root / "modules/temporal_two_expert/model.py",
        "INPUT_SOURCE.py": root / "modules/temporal_two_expert/inputs.py",
        "CHECKPOINT_SOURCE.py": root / "modules/temporal_two_expert/checkpoint.py",
        "STAGE_SOURCE.py": root / "modules/temporal_surrogate_resume_v2/stage.py",
        "GRADIENT_SOURCE.py": root / "modules/temporal_surrogate_resume_v2/gradient.py",
        "OBJECTIVE_SOURCE.py": root / "modules/temporal_risk_proxy_v2/proxy.py",
    }
    for name, path in source_members.items():
        shutil.copyfile(path, destination / name)
    shutil.copyfile(folder / pointer["file"], destination / "MODEL_ADAM_RNG.pt")
    shutil.copyfile(state / "four-fit/SCALER.npz", destination / "SCALER.npz")
    shutil.copyfile(
        root / "research/temporal-surrogate-resume-v2-20261009/PROTOCOL.json",
        destination / "TRAINING_PLAN.json",
    )
    for name in ("RUN.json", "TERMINAL.json", "latest.json"):
        shutil.copyfile(folder / name, destination / name)
    files = {
        p.name: dict(bytes=p.stat().st_size, sha256=sha(p))
        for p in sorted(destination.iterdir())
        if p.is_file()
    }
    adapter_path = "research/recover-frozen-runner-20261009/EVALUATE_REQUESTS61_ADAPTER.json"
    adapter_bytes = subprocess.check_output(
        ["git", "show", ADAPTER_COMMIT + ":" + adapter_path], cwd=root
    )
    import hashlib

    manifest = dict(
        schema="SOURCE_HASHED_FROZEN_NATIVE61_REQUESTS_V1",
        arm_id="V2_" + arm,
        objective_version=2,
        prediction_role="HISTORICAL_FROZEN_REPLAY_NOT_LIVE_PREDICTIONS",
        expert_order=list(order),
        allowed_actions=list(allowed),
        uses_feedback_features=False,
        request_file="REQUESTS.npz",
        source_files=list(source_members),
        files=files,
        model_sha256=pointer["SHA256"],
        model_identity=before,
        scaler_sha256=sha(destination / "SCALER.npz"),
        training_plan_sha256=sha(destination / "TRAINING_PLAN.json"),
        producer_commit=producer_commit,
        training_cutoff_us=int(cutoff),
        maximum_training_label_available_us=maximum_label,
        maximum_scaler_input_available_us=maximum_scaler_clock,
        actual_fit_completed_UTC=datetime.fromtimestamp(
            (folder / "TERMINAL.json").stat().st_mtime, timezone.utc
        ).isoformat(),
        completion_timestamp_source="atomic_terminal_record_mtime_in_original_execution_environment",
        terminal_training_status=terminal["status"],
        completed_v2_updates=terminal["completed_stage_updates"],
        cumulative_Adam_step=terminal["cumulative_Adam_step"],
        parent_checkpoint_sha256=terminal["parent_checkpoint_SHA256"],
        native_adapter_commit=ADAPTER_COMMIT,
        native_adapter_contract_sha256=hashlib.sha256(adapter_bytes).hexdigest(),
        masks="exact canonical eligibility intersect admitted current pair/CASH;unused2/3zero",
        export_operation="terminal_model_eval_requests_only;no economic score or optimizer step",
        native_execution_results=False,
    )
    (destination / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            dict(
                status="EXPORTED_TERMINAL_NATIVE61_REQUESTS_NO_SCORE",
                arm=manifest["arm_id"],
                manifest_SHA256=sha(destination / "MANIFEST.json"),
                requests_SHA256=sha(destination / "REQUESTS.npz"),
                completed_v2_updates=terminal["completed_stage_updates"],
            )
        ),
        flush=True,
    )
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--arm", required=True)
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument("--producer-commit", required=True)
    a = p.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    export(a.state, a.arm, a.destination, a.producer_commit)


if __name__ == "__main__":
    main()
