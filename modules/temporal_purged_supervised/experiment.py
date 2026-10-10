"""Fresh prefix fit; select 20/100 only on 2023; freeze before selected-only 2024 audit."""

import argparse
import fcntl
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_balanced_history.train import save
from modules.temporal_neutral_short.model import initialize
from modules.temporal_short_expansion.checkpoint import (
    _validate_model_state,
    _validate_rng,
    _validate_saved_optimizer,
)
from modules.temporal_two_expert.checkpoint import _atomic_json, _restore_rng, model_identity
from modules.temporal_two_expert.exact import sha

from .inputs import (
    CUTOFF,
    SELECT_END,
    TRAIN_END,
    arrays_for_role,
    dataset,
    install_io_guard,
    io_receipt,
)
from .scoring import correct, metrics, report

ROOT = Path(__file__).resolve().parents[2]
SLOTS = [0, 1, 4, 5]


def sources():
    paths = {
        Path(m.__file__).resolve()
        for name, m in list(sys.modules.items())
        if name.startswith("modules.") and str(getattr(m, "__file__", "")).endswith(".py")
    }
    # python -m executes this file as __main__, outside the modules.* namespace.
    paths.update(Path(__file__).parent.glob("*.py"))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths) if p.is_relative_to(ROOT)}


def ready(state, out, io):
    out.mkdir(exist_ok=False)
    es, rows, indices, roles, weights, scaler, receipt = dataset(state)
    m, opt = initialize(scaler)
    updates = math.ceil(len(roles["TRAIN"]) / 64)
    plan = {
        "schema": "PURGED_CHRONOLOGICAL_SUPERVISED_INTERNAL_CONTROL_V1",
        "status": "PREFIT_NOT_TRAINED",
        "class_order": ["CASH", "VOL", "CS", "SHORT"],
        "hypothesis": (
            "A fresh prefix-trained supervised short timing model may generalize to later old "
            "history. Compare exactly 20 versus 100 epochs to diagnose underfit versus overfit."
        ),
        "data_role": (
            "Previously seen project history, internal chronological development validation; "
            "not pristine OOS. No 2025 IO, selection, calibration, or trading replay."
        ),
        "splits": {
            "train": "Decision before 2023-01-01 and label available strictly before 2023-01-01",
            "selection": "Decision in 2023 and label available strictly before 2024-01-01",
            "audit": "Decision from 2024-01-01 and label available strictly before 2024-05-01",
            "cutoffs_us": [TRAIN_END, SELECT_END, CUTOFF],
            "purge": "21-day targets crossing either boundary excluded; strict maturity latency",
            "lookback": "Unchanged causal 64 real calendar days ending at each decision",
        },
        "objective": "Existing class-balanced CE on fixed four output coordinates [0,1,4,5]",
        "epoch_candidates": [20, 100],
        "total_epochs": 100,
        "batch_size": 64,
        "updates_per_epoch": updates,
        "updates": updates * 100,
        "sampling": "Same seed; every training window once per epoch, shuffled windows only",
        "architecture": "Unchanged neutral-short GRU plus causal expert-state; 13699 parameters",
        "optimizer": "Adam lr0.001 betas0.9/0.999 eps1e-8; dropout0.1; global gradient clip1",
        "initialization": "Fresh fixed seed 20261009; no parent model or optimizer",
        "preprocessing": (
            "fit_standardizer on sliced WindowBatch belonging only to matured TRAIN labels; "
            "deduplicate their valid causal history rows; never use full-history scaler"
        ),
        "probability_rule": "Primary p = q / TRAIN class_weights, normalized; no calibration fit",
        "decision_rule": "argmax primary p; numpy first-coordinate tie rule; no tuned threshold",
        "selection_rule": (
            "Choose minimum corrected multiclass logloss on overlapping SELECT2023 rows; "
            "exact tie chooses epoch20. Raw q is diagnostic only, never selection."
        ),
        "audit_rule": (
            "Freeze SELECTION.json and checkpoint identities before opening audit scoring; "
            "audit selected epoch only, once. Do not switch after audit."
        ),
        "metrics": [
            "multiclass logloss",
            "multiclass Brier",
            "accuracy",
            "SHORT precision/recall/prevalence",
            "mean fixed-policy21day opportunity regret vs prior and training-mean-utility action",
        ],
        "uncertainty": (
            "Report phase0 calendar21day disjoint grid and all21 phases descriptively without "
            "pooling or favorable-phase selection; paired phase0 bootstrap1000 and Wilson "
            "intervals are descriptive with residual serial-dependence/small-sample caveats."
        ),
        "stopping": "One fresh fit100, snapshots20/100, no grid or additional fits after result",
        "resources": "oneCPU/thread; noGPU/swap; RSS2GB/address4GB/host8GB; wall1200sec guard",
        "recovery": "Atomic each minibatch model/Adam/RNG/permutation; exact resume; no refit",
        "data": receipt,
        "source_identity": sources(),
        "initial_model_identity": model_identity(m),
    }
    _atomic_json(out / "PLAN.json", plan)
    binding = {
        "plan_SHA256": sha(out / "PLAN.json"),
        "sources": sources(),
        "data": receipt,
        "torch": str(torch.__version__),
        "numpy": str(np.__version__),
    }
    h = {
        "epoch": 0,
        "offset": 0,
        "permutation": [],
        "loss_sum": 0.0,
        "observations": 0,
        "epoch_records": [],
    }
    save(out, m, opt, 0, binding, 0.0, h)
    np.savez_compressed(
        out / "SCALER.npz", mean=scaler.mean, scale=scaler.scale, count=scaler.count
    )
    _atomic_json(
        out / "READY.json",
        {
            "status": "PREFIT_READY",
            "binding": binding,
            "initial_model_identity": model_identity(m),
            "scaler_SHA256": sha(out / "SCALER.npz"),
        },
    )
    _atomic_json(out / "PREFIT_IO.json", io_receipt(io))
    print(
        json.dumps(
            {
                "status": "PREFIT_READY",
                "plan_SHA256": binding["plan_SHA256"],
                "roles": receipt["roles"],
                "class_counts": receipt["class_counts"],
                "updates": plan["updates"],
            }
        ),
        flush=True,
    )


def checked_data(state, out):
    plan = json.loads((out / "PLAN.json").read_text())
    assert plan["source_identity"] == sources()
    data = dataset(state)
    assert data[-1] == plan["data"]
    return plan, data


def load_checkpoint(out, pointer, scaler, binding):
    assert sha(out / pointer["path"]) == pointer["SHA256"]
    x = torch.load(out / pointer["path"], map_location="cpu", weights_only=True)
    assert x["binding"] == binding and x["step"] == pointer["step"]
    m, opt = initialize(scaler)
    _validate_model_state(m, x["model"], x["model_identity"])
    _validate_saved_optimizer(
        m, opt, x["optimizer"], x["step"], {n: 0 for n, _ in m.named_parameters()}
    )
    _validate_rng(x["rng"])
    m.load_state_dict(x["model"])
    opt.load_state_dict(x["optimizer"])
    _restore_rng(x["rng"])
    return m, opt, x


def tensors(arrays, ix):
    return [
        torch.tensor(a[ix].copy(), dtype=torch.float64 if j in (0, 3) else torch.bool)
        for j, a in enumerate(arrays)
    ]


def train(state, out, publication, io):
    pub = json.loads(Path(publication).read_text())
    assert pub["status"] == "PURGED_SUPERVISED_PREFIT_PUBLIC_VERIFIED"
    assert pub["plan_SHA256"] == sha(out / "PLAN.json")
    lock = (out / "run.lock").open("a+")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (out / "TERMINAL.json").exists():
        print("ALREADY_COMPLETE")
        return
    plan, data = checked_data(state, out)
    es, rows, indices, roles, weights, scaler, _ = data
    arrays, y, _, _ = arrays_for_role(es, rows, indices, roles, "TRAIN")
    binding = json.loads((out / "READY.json").read_text())["binding"]
    pointer = json.loads((out / "latest.json").read_text())
    m, opt, x = load_checkpoint(out, pointer, scaler, binding)
    h, step = x["history"], x["step"]
    cw = torch.tensor(weights, dtype=m.mean.dtype)
    start, prior = time.monotonic(), x["elapsed"]
    m.train()
    while h["epoch"] < 100:
        if not h["permutation"]:
            h["permutation"] = np.random.permutation(len(y)).tolist()
        ix = np.asarray(h["permutation"][h["offset"] : h["offset"] + 64])
        yy = torch.tensor(y[ix], dtype=torch.int64)
        opt.zero_grad(set_to_none=True)
        q = m(*tensors(arrays, ix))[:, SLOTS]
        loss = -(q[torch.arange(len(ix)), yy].clamp_min(1e-12).log() * cw[yy]).mean()
        assert torch.isfinite(loss)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0, error_if_nonfinite=True)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1
        h["offset"] += len(ix)
        h["observations"] += len(ix)
        h["loss_sum"] += float(loss.detach()) * len(ix)
        epoch_finished = h["offset"] == len(y)
        if epoch_finished:
            h["epoch"] += 1
            h["epoch_records"].append(
                {
                    "epoch": h["epoch"],
                    "weighted_CE": h["loss_sum"] / len(y),
                    "presentations": h["observations"],
                }
            )
            h.update(offset=0, permutation=[], loss_sum=0.0, observations=0)
        elapsed = prior + time.monotonic() - start
        pointer = save(out, m, opt, step, binding, elapsed, h)
        if epoch_finished and h["epoch"] in (20, 100):
            _atomic_json(
                out / f"EPOCH{h['epoch']}.json",
                {
                    "epoch": h["epoch"],
                    "model_identity": model_identity(m),
                    "checkpoint": pointer,
                },
            )
        if epoch_finished and h["epoch"] % 10 == 0:
            print(json.dumps(dict(h["epoch_records"][-1], step=step, elapsed=elapsed)), flush=True)
        if time.monotonic() - start >= 1100 and h["epoch"] < 100:
            print("BUDGET_STOP_EXACT_CHECKPOINT_RETAINED", flush=True)
            return
    assert step == plan["updates"]
    _atomic_json(
        out / "TERMINAL.json",
        {
            "status": "FIXED100_PREFIX_COMPLETE",
            "step": step,
            "epoch": 100,
            "elapsed_training": elapsed,
            "checkpoint": pointer,
            "model_identity": model_identity(m),
            "publication": pub,
            "selection_scoring_reads": 0,
            "audit_scoring_reads": 0,
        },
    )
    _atomic_json(out / "TRAIN_IO.json", io_receipt(io))
    print("FIXED100_PREFIX_COMPLETE", flush=True)


def predictions(m, arrays):
    m.eval()
    before = model_identity(m)
    with torch.no_grad():
        q = np.concatenate(
            [
                m(*tensors(arrays, slice(i, i + 32)))[:, SLOTS].numpy()
                for i in range(0, len(arrays[0]), 32)
            ]
        )
    assert model_identity(m) == before
    return q


def select(state, out, io):
    assert (out / "TERMINAL.json").exists()
    assert not (out / "SELECTION.json").exists()
    _, data = checked_data(state, out)
    es, rows, indices, roles, weights, scaler, receipt = data
    binding = json.loads((out / "READY.json").read_text())["binding"]
    prior = np.asarray(receipt["class_prior"])
    action = int(np.argmax(receipt["training_mean_utility"]))
    scores, pointers = {}, {}
    for epoch in (20, 100):
        snapshot = json.loads((out / f"EPOCH{epoch}.json").read_text())
        m, _, _ = load_checkpoint(out, snapshot["checkpoint"], scaler, binding)
        assert model_identity(m) == snapshot["model_identity"]
        score = {}
        for name in ("TRAIN", "SELECT2023"):
            arrays, y, utility, decision = arrays_for_role(es, rows, indices, roles, name)
            q = predictions(m, arrays)
            p = correct(q, weights)
            score[name] = {
                "corrected_primary": report(p, y, utility, decision, prior, action),
                "raw_q_diagnostic_only": metrics(q, y, utility),
            }
            np.savez_compressed(
                out / f"EPOCH{epoch}_{name}_PREDICTIONS.npz",
                decision_us=decision,
                y=y,
                utility=utility,
                q=q,
                p=p,
            )
        scores[str(epoch)] = score
        pointers[str(epoch)] = snapshot
    loss = {
        epoch: scores[str(epoch)]["SELECT2023"]["corrected_primary"]["overlap"]["model"]["logloss"]
        for epoch in (20, 100)
    }
    selected = min((20, 100), key=lambda e: (loss[e], e))
    _atomic_json(
        out / "VALIDATION_SCORES.json",
        {
            "status": "INTERNAL_CHRONOLOGICAL_DEVELOPMENT_VALIDATION",
            "epochs": scores,
            "train_prior": prior.tolist(),
            "training_mean_utility": receipt["training_mean_utility"],
            "plan_SHA256": sha(out / "PLAN.json"),
            "source_identity": sources(),
            "audit_scored": False,
        },
    )
    _atomic_json(
        out / "SELECTION.json",
        {
            "status": "SELECTED_FROZEN_BEFORE2024_AUDIT",
            "epoch": selected,
            "rule": "minimum corrected overlapping2023 multiclass logloss; exact tie epoch20",
            "candidate_logloss": {str(k): v for k, v in loss.items()},
            "snapshot": pointers[str(selected)],
            "plan_SHA256": sha(out / "PLAN.json"),
            "validation_scores_SHA256": sha(out / "VALIDATION_SCORES.json"),
            "source_identity": sources(),
            "audit_scored": False,
        },
    )
    _atomic_json(out / "SELECT_IO.json", io_receipt(io))
    print(
        json.dumps(
            {
                "selected_epoch": selected,
                "candidate_logloss": loss,
                "selection_SHA256": sha(out / "SELECTION.json"),
            }
        ),
        flush=True,
    )


def audit(state, out, frozen, io):
    frozen = json.loads(Path(frozen).read_text())
    assert frozen["status"] == "PURGED_SUPERVISED_SELECTION_PUBLIC_VERIFIED"
    assert frozen["selection_SHA256"] == sha(out / "SELECTION.json")
    assert not (out / "AUDIT_SCORES.json").exists()
    selection = json.loads((out / "SELECTION.json").read_text())
    assert selection["status"] == "SELECTED_FROZEN_BEFORE2024_AUDIT"
    assert selection["validation_scores_SHA256"] == sha(out / "VALIDATION_SCORES.json")
    _, data = checked_data(state, out)
    es, rows, indices, roles, weights, scaler, receipt = data
    binding = json.loads((out / "READY.json").read_text())["binding"]
    m, _, _ = load_checkpoint(out, selection["snapshot"]["checkpoint"], scaler, binding)
    assert model_identity(m) == selection["snapshot"]["model_identity"]
    arrays, y, utility, decision = arrays_for_role(es, rows, indices, roles, "AUDIT2024")
    q = predictions(m, arrays)
    p = correct(q, weights)
    result = {
        "status": "SELECTED_ONLY_2024_INTERNAL_AUDIT_COMPLETE",
        "selected_epoch": selection["epoch"],
        "selection_SHA256": sha(out / "SELECTION.json"),
        "selection_publication": frozen,
        "plan_SHA256": sha(out / "PLAN.json"),
        "source_identity": sources(),
        "model_identity": model_identity(m),
        "corrected_primary": report(
            p,
            y,
            utility,
            decision,
            np.asarray(receipt["class_prior"]),
            int(np.argmax(receipt["training_mean_utility"])),
        ),
        "raw_q_diagnostic_only": metrics(q, y, utility),
        "data_role": "Previously seen history; no pristine OOS, trading returns, or profit claim",
        "additional_epoch_audit": "NOT_RUN; selected epoch only",
    }
    _atomic_json(out / "AUDIT_SCORES.json", result)
    np.savez_compressed(
        out / "AUDIT_PREDICTIONS.npz", decision_us=decision, y=y, utility=utility, q=q, p=p
    )
    _atomic_json(out / "AUDIT_IO.json", io_receipt(io))
    print(
        json.dumps(
            {
                "selected_epoch": selection["epoch"],
                "overlap": result["corrected_primary"]["overlap"],
                "disjoint21_phase0": result["corrected_primary"]["disjoint21_phase0"],
            }
        ),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["ready", "train", "select", "audit"])
    parser.add_argument("--state", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--publication")
    parser.add_argument("--selection-frozen")
    a = parser.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    io = install_io_guard(a.state)
    out = Path(a.out)
    if a.mode == "ready":
        ready(a.state, out, io)
    elif a.mode == "train":
        train(a.state, out, a.publication, io)
    elif a.mode == "select":
        select(a.state, out, io)
    else:
        audit(a.state, out, a.selection_frozen, io)


if __name__ == "__main__":
    main()
