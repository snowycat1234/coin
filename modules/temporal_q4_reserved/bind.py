"""Freeze Q4 inputs after terminal256; no inference or economic wallet."""

import argparse
import json
from pathlib import Path

import pyarrow as pa
import torch

from modules.temporal_selected_refit.stage import frozen_state
from modules.temporal_two_expert.inputs import array_digest

from .data import load
from .evaluate import sources

parser = argparse.ArgumentParser(description=__doc__)
for name in ("state", "economics", "fit-output", "output"):
    parser.add_argument("--" + name, type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    raise FileExistsError("Exclusive input binding receipt required")
torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
pa.set_cpu_count(1)
pa.set_io_thread_count(1)
_, _, scaler, _, terminal = frozen_state(args.state, args.fit_output)
episode, _, receipt = load(args.state, args.economics, scaler, terminal)
receipt.update(
    status="INPUTS_BOUND_AFTER_PUBLIC_FROZEN256_BEFORE_ONCE_SCORING",
    public_frozen_refit_commit="6124170b9d0f8c7eed5e7faf7584f56044ad752c",
    model_identity=terminal["model_identity"],
    checkpoint_SHA256=terminal["checkpoint_SHA256"],
    features_identity=episode.windows.identity,
    expert_state_identity=array_digest(episode.expert_state),
    prices_identity=array_digest(episode.prices),
    funding_identity=array_digest(episode.funding_coeff),
    versioned_sources=sources(),
    optimizer_updates=0,
    model_inferences=0,
    economic_wallets=0,
    native_wallets=0,
    provider_downloads=0,
)
with args.output.open("x") as stream:
    stream.write(json.dumps(receipt, indent=2) + "\n")
print(
    json.dumps(
        {
            k: receipt[k]
            for k in (
                "status",
                "completed_input_rows",
                "windows_shape",
                "all64_steps_observed",
                "expert_eligibility_counts",
                "scaler_training_rows",
                "episode_identity",
            )
        }
    )
)
