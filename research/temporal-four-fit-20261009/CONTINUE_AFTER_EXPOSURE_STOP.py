"""Finish remaining predeclared arms after the exact proxy STOP; no refit/rescue.

Invocation: bounded_comparison --report STATE/CONTINUATION_RESOURCES.json
python this_file --state STATE. Frozen modules/prototype stay byte-identical.
"""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    load_checkpoint,
    make_optimizer,
    model_identity,
    run_guard,
    save_checkpoint,
)
from modules.temporal_two_expert.comparison import ARMS, PROTOCOL, train_arm
from modules.temporal_two_expert.exact import (
    memory_bounded_gradients,
    request_loss_and_gradient,
    sha,
)
from modules.temporal_two_expert.inputs import Standardizer
from modules.temporal_two_expert.model import Selector, predict_windows
from modules.temporal_two_expert.training_packet import load_packet


def witness(model, episodes, prototype, rng):
    final_rng = torch.get_rng_state().clone()
    torch.set_rng_state(rng)
    try:
        for episode in episodes:
            with torch.no_grad():
                requests = predict_windows(
                    model, episode.windows, feature_batch_size=PROTOCOL["feature_batch_size"]
                ).numpy()
            try:
                request_loss_and_gradient(requests, episode, prototype)
            except prototype.ProxyExposureBreach as error:
                return dict(
                    status="STOP_PROXY_EXPOSURE_BREACH",
                    wallet_id=episode.wallet_id,
                    day_index=error.day_index,
                    boundary_index=error.boundary_index,
                    decision_us=int(episode.windows.decision_us[error.day_index]),
                    equity=float(error.equity),
                    exposure=error.exposure.tolist(),
                    exposure_fraction=(error.exposure / error.equity).tolist(),
                    gross_fraction=float(error.exposure.sum() / error.equity),
                    failed_model_identity=model_identity(model),
                    dropout_training=model.training,
                )
        raise AssertionError("Failed exact proxy path did not reproduce")
    finally:
        torch.set_rng_state(final_rng)


def mark_stop(folder, model, witness_record, elapsed=None):
    binding = json.loads((folder / "RUN.json").read_text())
    optimizer = make_optimizer(model)
    loaded = load_checkpoint(folder, model, optimizer, binding)
    state = loaded["trainer_state"]
    state.update(
        status="STOP_PROXY_EXPOSURE_BREACH",
        failure=witness_record,
        terminal_rule="last_atomic_completed_update;no_retry_no_rescue_no_epoch_search",
    )
    consumed = max(loaded["elapsed_seconds"], elapsed or 0.0)
    save_checkpoint(
        folder,
        model,
        optimizer,
        binding,
        step=loaded["step"],
        elapsed_seconds=consumed,
        trainer_state=state,
    )
    result = dict(
        status=state["status"],
        step=loaded["step"],
        run_id=binding["run_id"],
        model_identity=model_identity(model),
        elapsed_seconds=consumed,
        failure=witness_record,
        refits=0,
    )
    _atomic_json(folder / "TERMINAL.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("COIN_CLOUD_BOUNDED") != "1" or len(os.sched_getaffinity(0)) != 1:
        raise ValueError("Frozen one-CPU resource launcher required")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    state = args.state.resolve()
    root = state / "four-fit"
    train, dev, prototype, identity = load_packet(
        state / "FROZEN_PACKET.json",
        sha(state / "FROZEN_PACKET.json"),
        state / "recovery/source/modules/direct_path/prototype.py",
    )
    proof = json.loads((root / "SCALER.json").read_text())
    if sha(root / "SCALER.npz") != proof["SHA256"]:
        raise ValueError("Reuse original frozen shared scaler")
    with np.load(root / "SCALER.npz", allow_pickle=False) as z:
        scaler = Standardizer(z["mean"], z["scale"], z["count"], proof["provenance"])
    group = json.loads((root / "RUN.json").read_text())
    dataset = group["specification"]["dataset"]
    if dataset != dict(
        packet=identity, train=[e.identity for e in train], development=[e.identity for e in dev]
    ):
        raise ValueError("Same original frozen data required; no replacement episodes")
    models, terminal = {}, {}
    with run_guard(root, group):
        if (root / "DEVELOPMENT_RESULTS.json").exists():
            print((root / "DEVELOPMENT_RESULTS.json").read_text())
            return
        for family, cash in ARMS:
            name = family + ("_WITH_CASH" if cash else "_NO_CASH")
            folder = root / name
            model = Selector(
                scaler,
                family=family,
                cash_enabled=cash,
                zero_readout=True,
                seed=PROTOCOL["seed"],
                dropout=PROTOCOL["dropout"],
            )
            if (folder / "TERMINAL.json").exists():
                terminal[name] = json.loads((folder / "TERMINAL.json").read_text())
                binding = json.loads((folder / "RUN.json").read_text())
                load_checkpoint(folder, model, make_optimizer(model), binding)
            elif name == "GRU64_NO_CASH":
                record = json.loads((state / "EXPOSURE_STOP_WITNESS.json").read_text())
                phase1 = json.loads((state / "FOUR_FIT_RESOURCES.json").read_text())
                terminal[name] = mark_stop(folder, model, record, phase1["elapsed_seconds"])
            else:
                failed = {}

                def checked_gradients(
                    model, episodes, prototype, *, feature_batch_size, _failed=failed
                ):
                    rng = torch.get_rng_state().clone()
                    try:
                        return memory_bounded_gradients(
                            model, episodes, prototype, feature_batch_size=feature_batch_size
                        )
                    except prototype.ProxyExposureBreach:
                        _failed.update(witness(model, episodes, prototype, rng))
                        raise

                began = time.monotonic()
                try:
                    terminal[name] = train_arm(
                        model,
                        train,
                        prototype,
                        folder,
                        dataset,
                        gradient_function=checked_gradients,
                    )
                except prototype.ProxyExposureBreach:
                    if not (folder / "latest.json").exists():
                        raise
                    terminal[name] = mark_stop(folder, model, failed, time.monotonic() - began)
                    print(
                        json.dumps(dict(stage="terminal_failure", arm=name, **terminal[name])),
                        flush=True,
                    )
            models[name] = model.eval()
        _atomic_json(
            root / "ALL_FOUR_TERMINAL.json",
            dict(
                status="ALL_FOUR_FROZEN_BEFORE_DEVELOPMENT",
                terminal=terminal,
                scaler_identity=scaler.identity,
                group_identity=group["run_id"],
                failure_handling="mechanical_exact_proxy_STOP;no_training_retry_or_rescue",
            ),
        )
        arms = {}
        for name, model in models.items():
            reports = []
            frozen_model = model_identity(model)
            for episode in dev:
                with torch.no_grad():
                    requests = predict_windows(
                        model, episode.windows, feature_batch_size=PROTOCOL["feature_batch_size"]
                    ).numpy()
                try:
                    loss, _, report = request_loss_and_gradient(requests, episode, prototype)
                    reports.append(
                        dict(
                            wallet_id=episode.wallet_id,
                            loss=loss,
                            **{
                                k: report[k]
                                for k in (
                                    "net_PnL",
                                    "utility_sum",
                                    "fees",
                                    "spread",
                                    "slippage",
                                    "funding",
                                    "terminal_cash_realized",
                                    "status",
                                )
                            },
                        )
                    )
                except prototype.ProxyExposureBreach as error:
                    reports.append(
                        dict(
                            wallet_id=episode.wallet_id,
                            status="STOP_PROXY_EXPOSURE_BREACH",
                            loss=None,
                            net_PnL=None,
                            day_index=error.day_index,
                            boundary_index=error.boundary_index,
                            equity=float(error.equity),
                            exposure=error.exposure.tolist(),
                            terminal_cash_realized=False,
                            full_path_result_unavailable=True,
                        )
                    )
            assert model_identity(model) == frozen_model
            arms[name] = dict(training=terminal[name], development=reports)
        stopped = any(t["status"] == "STOP_PROXY_EXPOSURE_BREACH" for t in terminal.values())
        capped = any(t["status"] == "CAPPED_NOT_CONVERGED" for t in terminal.values())
        result = dict(
            status="EXPOSURE_STOP_COMPARISON_INCOMPLETE"
            if stopped
            else ("CAPPED_COMPARISON_NOT_CONVERGED" if capped else "TRAIN_CRITERIA_MET"),
            planned_fits=4,
            actual_fits=4,
            refits=0,
            arms=arms,
            development_classification="SEEN_PROXY_NOT_UNTOUCHED_OOS",
            data_identity=dataset,
            protocol_SHA256=group["specification"]["protocol_SHA256"],
            scaler_identity=scaler.identity,
            native_wallets=0,
            convergence_is_not_economic_qualification=True,
            failure_amendment="retain_last_atomic_completed_update_on_exact_proxy_exposure_STOP;continue_only_remaining_predeclared_arms",
        )
        _atomic_json(root / "DEVELOPMENT_RESULTS.json", result)
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
