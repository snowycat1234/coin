"""One fixed-20 objective substitution; 2023 gate precedes optional 2024 audit."""

import argparse
import fcntl
import json
import math
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_balanced_history.train import save
from modules.temporal_neutral_short.model import initialize
from modules.temporal_purged_supervised.experiment import load_checkpoint, predictions, tensors
from modules.temporal_purged_supervised.experiment import sources as inherited_sources
from modules.temporal_purged_supervised.inputs import (
    arrays_for_role,
    dataset,
    install_io_guard,
    io_receipt,
)
from modules.temporal_purged_supervised.scoring import correct
from modules.temporal_two_expert.checkpoint import _atomic_json, model_identity
from modules.temporal_two_expert.exact import sha

from .objective import PAIRS, fit_scale, pairwise_loss
from .scoring import adoption_gate, comparison

ROOT = Path(__file__).resolve().parents[2]
SLOTS = [0, 1, 4, 5]


def sources():
    return {
        **inherited_sources(),
        **{str(p.relative_to(ROOT)): sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
    }


def baseline_binding(baseline, data_receipt):
    plan = json.loads((baseline / "PLAN.json").read_text())
    ready = json.loads((baseline / "READY.json").read_text())
    snapshot = json.loads((baseline / "EPOCH20.json").read_text())
    selected = json.loads((baseline / "SELECTION.json").read_text())
    assert plan["data"] == data_receipt and selected["epoch"] == 20
    assert ready["binding"]["plan_SHA256"] == sha(baseline / "PLAN.json")
    assert snapshot == selected["snapshot"] and snapshot["checkpoint"]["step"] == 240
    for name, identity in plan["source_identity"].items():
        assert sha(ROOT / name) == identity
    assert sha(baseline / snapshot["checkpoint"]["path"]) == snapshot["checkpoint"]["SHA256"]
    names = [
        "PLAN.json",
        "READY.json",
        "EPOCH20.json",
        "SELECTION.json",
        "EPOCH20_TRAIN_PREDICTIONS.npz",
        "EPOCH20_SELECT2023_PREDICTIONS.npz",
    ]
    return {
        "path": str(baseline.resolve()),
        "files": {n: sha(baseline / n) for n in names},
        "snapshot": snapshot,
        "initial_model_identity": plan["initial_model_identity"],
        "public_research_commit": "9209c9f7473d69230f3e84e53f1db11d09680462",
    }


def baseline_scores(baseline, name, y, u, d, weights, binding):
    path = baseline / f"EPOCH20_{name}_PREDICTIONS.npz"
    assert sha(path) == binding["files"][path.name]
    z = np.load(path)
    for key, array in (("y", y), ("utility", u), ("decision_us", d)):
        np.testing.assert_array_equal(z[key], array)
    np.testing.assert_allclose(z["p"], correct(z["q"], weights), rtol=0, atol=1e-15)
    return z["p"]


def ready(state, out, baseline, io):
    data = dataset(state)
    es, rows, indices, roles, _, scaler, receipt = data
    _, _, u, _ = arrays_for_role(es, rows, indices, roles, "TRAIN")
    scale = fit_scale(u)
    base = baseline_binding(baseline, receipt)
    m, opt = initialize(scaler)
    assert model_identity(m) == base["initial_model_identity"]
    nonzero = np.abs(np.stack([u[:, i] - u[:, j] for i, j in PAIRS], 1))
    out.mkdir(exist_ok=False)
    plan = {
        "schema": "MATCHED_FIXED20_PAYOFF_PAIRWISE_INTERNAL_CONTROL_V1",
        "status": "PREFIT_NOT_TRAINED",
        "hypothesis": (
            "SHORT timing association may survive economic-error weighting when all four "
            "alternatives remain available"
        ),
        "data_role": (
            "Previously seen internal chronological development history; neither 2023 nor 2024 "
            "is pristine OOS; no 2025 IO"
        ),
        "class_order": ["CASH", "VOL", "CS", "SHORT"],
        "output_slots": SLOTS,
        "architecture": "Unchanged 13,699-parameter GRU64 plus causal expert state",
        "initialization": "Same fresh seed 20261009, neutral SHORT 1/3; no parent model or Adam",
        "total_epochs": 20,
        "batch_size": 64,
        "updates": math.ceil(len(roles["TRAIN"]) / 64) * 20,
        "sampling": (
            "Each TRAIN window once per epoch; same seeded numpy permutation and dropout "
            "sequence as CE20"
        ),
        "optimizer": (
            "Unchanged Adam lr .001, betas .9/.999, eps 1e-8; dropout .1; global gradient clip 1; "
            "no extra regularization"
        ),
        "objective": {
            "pairs": [list(p) for p in PAIRS],
            "pair_logit": "log(q_i/q_j)",
            "delta": "u_i-u_j from the same frozen hindsight fixed-policy 21-day label",
            "loss": (
                "Mean over rows and six pairs of ([delta]+ softplus(-z_ij) "
                "+ [-delta]+ softplus(z_ij)) / TRAIN_scale"
            ),
            "scale_rule": "Median nonzero absolute gap across 744 TRAIN rows and six pairs only",
            "scale": scale,
            "tail_clipping": "NONE",
            "class_balancing": "NONE",
            "argmax_gradient": "NONE",
        },
        "score_contract": (
            "Raw simplex q are preference scores, not calibrated winner probabilities or "
            "estimated utility; no CE inverse-weight correction"
        ),
        "decision_rule": (
            "Argmax raw q, first-coordinate tie rule; no threshold or forced SHORT frequency"
        ),
        "changed_variable": (
            "Replace balanced winner CE with magnitude-weighted all-pair logistic loss; "
            "remove its associated inverse-class-weight probability correction"
        ),
        "matched_controls": (
            "Reuse exact CE20; unchanged architecture, data, scaler, initialization, batch order, "
            "update count, Adam, dropout and clip. Fixed epoch 20 is inherited, not newly optimized"
        ),
        "selection_rule": (
            "2023 adoption gate only: overlap regret strictly below both CE20 and constant VOL; "
            "fixed phase-0 regret no worse than either. Exact ties fail strict overlap criteria"
        ),
        "audit_rule": (
            "If the gate fails, stop before old AUDIT_PREDICTIONS or new 2024 inference/scoring. "
            "If it passes, publicly freeze selection/checkpoint before selected-only 2024 "
            "development audit; no replacement after audit"
        ),
        "stopping": (
            "Exactly one fresh 20-epoch fit, 240 updates; no epoch/model/calibration/threshold "
            "grid or further fit"
        ),
        "metrics": (
            "Action opportunity regret/mean utility, SHORT precision/recall/prevalence, "
            "confusion, paired fixed phase-0 utility-difference bootstrap 1000. No proper "
            "logloss/Brier for preference outputs"
        ),
        "uncertainty": (
            "Overlapping daily 21-day horizons; fixed phase 0 primary descriptive view and all "
            "21 phases reported without pooling/selection; residual dependence and small n"
        ),
        "label_semantics": (
            "Sum 21 daily [log1p(netreturn)-5min(netreturn,0)^2] from separately continuous "
            "fixed-policy wallets under charged-boundary full-fill diagnostic; cash 0. Horizon "
            "start inherits fixed-policy holdings. Not reset/switching trade returns, "
            "minute-native execution or profit"
        ),
        "binary_gate_recommendation": (
            "Reject SHORT versus VOL collapse: CASH/CS retain meaningful TRAIN oracle "
            "opportunities; use all four actions"
        ),
        "binary_gate_TRAIN_diagnostic": {
            "excluded_winner_rows": int(np.isin(u.argmax(1), [0, 2]).sum()),
            "oracle_four_minus_SHORT_VOL_mean": float((u.max(1) - u[:, [1, 3]].max(1)).mean()),
        },
        "TRAIN_gap_diagnostic": {
            "nonzero_count": int((nonzero > 0).sum()),
            "max_abs_gap": float(nonzero.max()),
            "median_nonzero": scale,
            "max_gap_over_scale": float(nonzero.max() / scale),
        },
        "data": receipt,
        "baseline": base,
        "source_identity": sources(),
        "initial_model_identity": model_identity(m),
        "resources": "One CPU/thread; no GPU/swap; RSS 2 GB/address 4 GB/host 8 GB; wall 1200 sec",
        "recovery": (
            "Atomic every minibatch model/Adam/RNG/permutation; exact resume; "
            "no checkpoint overwrite"
        ),
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
                "scale": scale,
                "binary_gate_TRAIN_diagnostic": plan["binary_gate_TRAIN_diagnostic"],
            }
        ),
        flush=True,
    )


def checked_data(state, out):
    plan = json.loads((out / "PLAN.json").read_text())
    assert plan["source_identity"] == sources()
    data = dataset(state)
    assert data[-1] == plan["data"]
    assert baseline_binding(Path(plan["baseline"]["path"]), data[-1]) == plan["baseline"]
    return plan, data


def train(state, out, publication, io):
    pub = json.loads(Path(publication).read_text())
    assert pub["status"] == "PAYOFF_PAIRWISE_PREFIT_PUBLIC_VERIFIED" and pub["plan_SHA256"] == sha(
        out / "PLAN.json"
    )
    lock = (out / "run.lock").open("a+")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (out / "TERMINAL.json").exists():
        print("ALREADY_COMPLETE")
        return
    plan, (es, rows, indices, roles, _, scaler, _) = checked_data(state, out)
    arrays, _, u, _ = arrays_for_role(es, rows, indices, roles, "TRAIN")
    binding = json.loads((out / "READY.json").read_text())["binding"]
    pointer = json.loads((out / "latest.json").read_text())
    m, opt, x = load_checkpoint(out, pointer, scaler, binding)
    h, step, start, prior = x["history"], x["step"], time.monotonic(), x["elapsed"]
    elapsed = prior  # Final-minibatch recovery can enter with the training loop already complete.
    m.train()
    while h["epoch"] < 20:
        if not h["permutation"]:
            h["permutation"] = np.random.permutation(len(u)).tolist()
        ix = np.asarray(h["permutation"][h["offset"] : h["offset"] + 64])
        opt.zero_grad(set_to_none=True)
        q = m(*tensors(arrays, ix))[:, SLOTS]
        loss = pairwise_loss(
            q, torch.tensor(u[ix], dtype=torch.float64), plan["objective"]["scale"]
        )
        assert torch.isfinite(loss)
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0, error_if_nonfinite=True)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1
        h["offset"] += len(ix)
        h["observations"] += len(ix)
        h["loss_sum"] += float(loss.detach()) * len(ix)
        done = h["offset"] == len(u)
        if done:
            h["epoch"] += 1
            h["epoch_records"].append(
                {
                    "epoch": h["epoch"],
                    "pairwise_payoff_loss": h["loss_sum"] / len(u),
                    "presentations": h["observations"],
                    "last_gradient_norm": float(norm),
                }
            )
            h.update(offset=0, permutation=[], loss_sum=0.0, observations=0)
        elapsed = prior + time.monotonic() - start
        pointer = save(out, m, opt, step, binding, elapsed, h)
        if done:
            print(json.dumps(dict(h["epoch_records"][-1], step=step, elapsed=elapsed)), flush=True)
        if time.monotonic() - start >= 1100 and h["epoch"] < 20:
            print("BUDGET_STOP_EXACT_CHECKPOINT_RETAINED", flush=True)
            return
    assert step == plan["updates"] == 240
    snapshot = {"epoch": 20, "model_identity": model_identity(m), "checkpoint": pointer}
    _atomic_json(out / "EPOCH20.json", snapshot)
    _atomic_json(
        out / "TERMINAL.json",
        {
            "status": "FIXED20_PREFIX_COMPLETE",
            "step": step,
            "epoch": 20,
            "elapsed_training": elapsed,
            "snapshot": snapshot,
            "publication": pub,
            "selection_scoring_reads": 0,
            "audit_scoring_reads": 0,
        },
    )
    _atomic_json(out / "TRAIN_IO.json", io_receipt(io))


def select(state, out, io):
    assert (out / "TERMINAL.json").exists() and not (out / "SELECTION.json").exists()
    plan, (es, rows, indices, roles, weights, scaler, receipt) = checked_data(state, out)
    binding = json.loads((out / "READY.json").read_text())["binding"]
    snapshot = json.loads((out / "EPOCH20.json").read_text())
    m, _, _ = load_checkpoint(out, snapshot["checkpoint"], scaler, binding)
    scores = {}
    for name in ("TRAIN", "SELECT2023"):
        arrays, y, u, d = arrays_for_role(es, rows, indices, roles, name)
        q = predictions(m, arrays)
        baseline = baseline_scores(
            Path(plan["baseline"]["path"]), name, y, u, d, weights, plan["baseline"]
        )
        scores[name] = comparison(q, baseline, y, u, d, np.asarray(receipt["class_prior"]))
        np.savez_compressed(
            out / f"EPOCH20_{name}_PREFERENCES.npz",
            decision_us=d,
            y=y,
            utility=u,
            q=q,
            baseline_p=baseline,
        )
    gate = adoption_gate(scores["SELECT2023"])
    _atomic_json(
        out / "VALIDATION_SCORES.json",
        {
            "status": "INTERNAL_DEVELOPMENT_VALIDATION",
            "roles": scores,
            "plan_SHA256": sha(out / "PLAN.json"),
            "audit_scored": False,
        },
    )
    selection = {
        "status": "PASS_FROZEN_BEFORE2024" if gate["passed"] else "FAIL_STOP_NO2024_AUDIT",
        "gate": gate,
        "snapshot": snapshot,
        "plan_SHA256": sha(out / "PLAN.json"),
        "validation_scores_SHA256": sha(out / "VALIDATION_SCORES.json"),
        "audit_scored": False,
    }
    _atomic_json(out / "SELECTION.json", selection)
    _atomic_json(out / "SELECT_IO.json", io_receipt(io))
    print(
        json.dumps(
            {
                "status": selection["status"],
                "gate": gate,
                "overlap": scores["SELECT2023"]["overlap"],
                "phase0": scores["SELECT2023"]["disjoint21_phase0"],
                "selection_SHA256": sha(out / "SELECTION.json"),
            }
        ),
        flush=True,
    )


def audit(state, out, frozen, io):
    # Reject before dataset/load/inference/oldAUDIT reads if the adoption gate failed.
    selection = json.loads((out / "SELECTION.json").read_text())
    assert selection["status"] == "PASS_FROZEN_BEFORE2024" and selection["gate"]["passed"]
    assert not (out / "AUDIT_SCORES.json").exists()
    pub = json.loads(Path(frozen).read_text())
    assert pub["status"] == "PAYOFF_PAIRWISE_SELECTION_PUBLIC_VERIFIED" and pub[
        "selection_SHA256"
    ] == sha(out / "SELECTION.json")
    assert selection["validation_scores_SHA256"] == sha(out / "VALIDATION_SCORES.json")
    plan, (es, rows, indices, roles, weights, scaler, receipt) = checked_data(state, out)
    binding = json.loads((out / "READY.json").read_text())["binding"]
    m, _, _ = load_checkpoint(out, selection["snapshot"]["checkpoint"], scaler, binding)
    arrays, y, u, d = arrays_for_role(es, rows, indices, roles, "AUDIT2024")
    q = predictions(m, arrays)
    baseline = Path(plan["baseline"]["path"])
    base_ready = json.loads((baseline / "READY.json").read_text())
    base_m, _, _ = load_checkpoint(
        baseline, plan["baseline"]["snapshot"]["checkpoint"], scaler, base_ready["binding"]
    )
    base_p = correct(predictions(base_m, arrays), weights)
    result = {
        "status": "SELECTED_ONLY2024_INTERNAL_DEVELOPMENT_AUDIT",
        "selection_publication": pub,
        "selection_SHA256": sha(out / "SELECTION.json"),
        "plan_SHA256": sha(out / "PLAN.json"),
        "scores": comparison(q, base_p, y, u, d, np.asarray(receipt["class_prior"])),
    }
    np.savez_compressed(
        out / "AUDIT_PREFERENCES.npz", decision_us=d, y=y, utility=u, q=q, baseline_p=base_p
    )
    _atomic_json(out / "AUDIT_SCORES.json", result)
    _atomic_json(out / "AUDIT_IO.json", io_receipt(io))
    print(json.dumps(result["scores"]["overlap"]), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["ready", "train", "select", "audit"])
    parser.add_argument("--state", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--baseline")
    parser.add_argument("--publication")
    parser.add_argument("--selection-frozen")
    a = parser.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    io = install_io_guard(a.state)
    state, out = Path(a.state), Path(a.out)
    if a.mode == "ready":
        ready(state, out, Path(a.baseline), io)
    elif a.mode == "train":
        train(state, out, a.publication, io)
    elif a.mode == "select":
        select(state, out, io)
    else:
        audit(state, out, a.selection_frozen, io)


if __name__ == "__main__":
    main()
