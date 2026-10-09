"""Small exact-parent/data/source preservation check; zero fitting/downloads."""

import argparse
import hashlib
import json
import os
import zipfile
from pathlib import Path

import torch

from modules.temporal_expert_input.stage import ARMS, initialize, inputs, sources
from modules.temporal_two_expert.checkpoint import model_identity
from modules.temporal_two_expert.exact import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    assert os.environ.get("COIN_CLOUD_BOUNDED") == "1"
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    root = Path(__file__).resolve().parents[2]
    state = a.state
    train, _, _, _, scaler = inputs(state)
    ready = json.loads((state / "expert-input/READY.json").read_text())
    assert ready["sources"] == sources()
    arms = [ready["arms"][name] for name in ARMS]
    assert arms[0]["request_identity"] == arms[1]["request_identity"]
    assert arms[0]["Torch_RNG_SHA256"] == arms[1]["Torch_RNG_SHA256"]
    assert arms[0]["train_loss"] == arms[1]["train_loss"]
    frozen = json.loads((state / "short-expansion/READY.json").read_text())["sources"]
    original = json.loads((state / "four-fit/RUN.json").read_text())["specification"]["sources"]
    for name, expected in {**original, **frozen}.items():
        assert sha(root / name) == expected, name
    archives = {}
    for phase, folder in (
        ("temporal-four-fit", "four-fit"),
        ("temporal-surrogate-resume-v2", "surrogate-v2"),
        ("temporal-short-expansion", "short-expansion"),
    ):
        path = root / ("research/" + phase + "-20261009/results/TERMINAL_MODELS_ADAM_RNG.zip")
        members = {}
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                local = state / folder / name
                if name.startswith("SCALER") and not local.exists():
                    local = state / "four-fit" / name
                assert z.read(name) == local.read_bytes(), (phase, name)
                members[name] = sha(local)
        archives[phase] = members
    models, moments, rngs, records = [], [], [], []
    for enabled in (False, True):
        model, optimizer, parent, births = initialize(state, scaler, enabled)
        models.append({n: t.clone() for n, t in model.state_dict().items()})
        moments.append({n: optimizer.state[p] for n, p in model.named_parameters()})
        rngs.append(torch.get_rng_state().clone())
        assert all(
            not optimizer.state[p] for n, p in model.named_parameters() if not n.startswith("base.")
        )
        records.append(
            dict(
                input_enabled=enabled,
                parent_step=parent["step"],
                parameters=model.parameter_count,
                base_identity=model_identity(model.base),
                births=births,
                new_moments_empty=True,
                parent_checkpoint_SHA256=parent["pointer"]["SHA256"],
            )
        )
    assert torch.equal(*rngs)
    for name in models[0]:
        assert torch.equal(models[0][name], models[1][name]), name
    for name in moments[0]:
        for key in moments[0][name]:
            assert torch.equal(moments[0][name][key], moments[1][name][key]), (name, key)
    result = dict(
        schema="MATCHED_EXPERT_INPUT_PREFIT_PRESERVATION_V1",
        status="PASS",
        matched_initialization=records,
        complete_model_tensors_and_Adam_moments_equal=True,
        initial_requests_equal=True,
        initial_train_loss_equal=True,
        initial_RNG_equal=True,
        Torch_RNG_SHA256=hashlib.sha256(rngs[0].numpy().tobytes()).hexdigest(),
        frozen_source_files=len({**original, **frozen}),
        archives_unchanged=archives,
        scaler_identity=scaler.identity,
        training_dates=sum(len(e.contexts) for e in train),
        input_availability=ready["input_audit"],
        source_quality_review_commit="7282bc15e5bcaf0a14d177dbc4cb48fc860caa40",
        provider_downloads=0,
        historical_optimizer_updates=0,
        minute_wallets=0,
        weighting_updates=0,
    )
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            dict(
                status=result["status"],
                source_files=result["frozen_source_files"],
                parameters=13699,
                historical_updates=0,
            )
        )
    )


if __name__ == "__main__":
    main()
