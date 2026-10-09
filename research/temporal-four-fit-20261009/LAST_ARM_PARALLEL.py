"""Scheduling-only fourth-arm worker; original seed/loss/stop/state unchanged."""

import argparse
import importlib.util
import json
import os
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_two_expert.comparison import PROTOCOL, train_arm
from modules.temporal_two_expert.exact import memory_bounded_gradients, sha
from modules.temporal_two_expert.inputs import Standardizer
from modules.temporal_two_expert.model import Selector
from modules.temporal_two_expert.training_packet import load_packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("COIN_CLOUD_BOUNDED") != "1" or len(os.sched_getaffinity(0)) != 1:
        raise ValueError("Original one-CPU bounded launcher required")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    state = args.state.resolve()
    root = state / "four-fit"
    train, development, prototype, identity = load_packet(
        state / "FROZEN_PACKET.json",
        sha(state / "FROZEN_PACKET.json"),
        state / "recovery/source/modules/direct_path/prototype.py",
    )
    group = json.loads((root / "RUN.json").read_text())
    dataset = group["specification"]["dataset"]
    if dataset != dict(
        packet=identity,
        train=[e.identity for e in train],
        development=[e.identity for e in development],
    ):
        raise ValueError("Original immutable data binding required")
    proof = json.loads((root / "SCALER.json").read_text())
    if sha(root / "SCALER.npz") != proof["SHA256"]:
        raise ValueError("Original shared scaler required; never refit")
    with np.load(root / "SCALER.npz", allow_pickle=False) as z:
        scaler = Standardizer(z["mean"], z["scale"], z["count"], proof["provenance"])
    folder = root / "LATEST_MLP_WITH_CASH"
    if (folder / "TERMINAL.json").exists():
        print((folder / "TERMINAL.json").read_text())
        return
    model = Selector(
        scaler,
        family="LATEST_MLP",
        cash_enabled=True,
        zero_readout=True,
        seed=PROTOCOL["seed"],
        dropout=PROTOCOL["dropout"],
    )
    source = Path(__file__).with_name("CONTINUE_AFTER_EXPOSURE_STOP.py")
    spec = importlib.util.spec_from_file_location("_frozen_exposure_stop_controller", source)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    failed = {}

    def checked_gradients(model, episodes, prototype, *, feature_batch_size):
        rng = torch.get_rng_state().clone()
        try:
            return memory_bounded_gradients(
                model, episodes, prototype, feature_batch_size=feature_batch_size
            )
        except prototype.ProxyExposureBreach:
            failed.update(controller.witness(model, episodes, prototype, rng))
            raise

    began = time.monotonic()
    try:
        terminal = train_arm(
            model, train, prototype, folder, dataset, gradient_function=checked_gradients
        )
    except prototype.ProxyExposureBreach:
        terminal = controller.mark_stop(folder, model, failed, time.monotonic() - began)
    print(json.dumps(dict(stage="fourth_arm_terminal", **terminal)), flush=True)


if __name__ == "__main__":
    main()
