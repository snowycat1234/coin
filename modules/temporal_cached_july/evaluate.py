"""Original paired evaluator with an explicit byte-bound cached input adapter.
Execution and accounting loop copied unchanged from 27f8a91e.
"""
import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import torch

from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_july_transfer.evaluate import reconcile
from modules.temporal_q4_reserved.evaluate import manifest
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, charged_boundary_path
from modules.temporal_short_expansion.adapter import compress, expand
from modules.temporal_short_expansion.model import E6
from modules.temporal_two_expert.checkpoint import _atomic_json, _rng_state, model_identity

from .data import inputs
from modules.temporal_added_history_july.data import prior_paths
from modules.temporal_added_history_july.models import frozen_model, shared_scaler
from .protocol import CLASSIFICATION, MODELS, ORDER, SCALER, protocol, public_gate, sources


def checked_request(request, episode, model):
    mask = episode.eligible & np.array([n in model.contract["allowed_actions"] for n in E6])
    if (
        request.shape != (63, 6)
        or not np.isfinite(request).all()
        or np.any(request < 0)
        or np.any(request[~mask])
        or np.any(request[:, 2:4])
        or not np.allclose(request.sum(1), 1, rtol=0, atol=1e-12)
    ):
        raise ValueError("Exact canonical masked63 request simplex required")
    return mask


def prepare(state, economics, output):
    output = Path(output)
    output.mkdir()
    audit = prior_paths(state)
    scaler = shared_scaler()
    identities, contracts = {}, []
    for name in ORDER:
        model, optimizer, snapshot = frozen_model(name, scaler)
        contracts.append(model.contract)
        identities[name] = dict(
            model_identity=model_identity(model),
            checkpoint_SHA256=MODELS[name]["checkpoint_SHA256"],
            step=snapshot["step"],
            Adam_parameter_ages=[int(optimizer.state[p]["step"]) for p in model.parameters()],
        )
    if contracts[0] != contracts[1]:
        raise ValueError("Exactly matched model/scaler/architecture required")
    _, _, _, binding, _ = inputs(state, economics)
    receipt = dict(
        status="PAIRED_PREFLIGHT_NO_INFERENCE_NO_WALLETS",
        protocol=protocol(),
        sources=sources(),
        models=identities,
        input_binding=binding,
        reuse_audit=audit,
        model_inferences=0,
        daily_wallets=0,
        fits=0,
        optimizer_updates=0,
        normalization_updates=0,
        provider_downloads=0,
    )
    _atomic_json(output / "PRESCORE.json", receipt)
    print(
        json.dumps(dict(status=receipt["status"], models=identities, reuse_audit=audit)), flush=True
    )
    return receipt


def run(state, economics, output, publication):
    output = Path(output)
    output.mkdir()  # Once-only claim precedes input or model inference.
    _atomic_json(output / "STARTED.json", dict(classification=CLASSIFICATION, policies=ORDER))
    began = time.monotonic()
    records, events, completed = {}, {}, []
    try:
        ready, public = public_gate(publication)
        episode, prototype, data, binding, controls = inputs(state, economics)
        if binding != ready["input_binding"]:
            raise ValueError("Published paired input binding changed")
        scaler = shared_scaler()
        for name in ORDER:
            model, optimizer, snapshot = frozen_model(name, scaler)
            before = (
                model_identity(model),
                tree_identity(_rng_state()),
                tree_identity(optimizer.state_dict()),
            )
            model.eval()
            with torch.no_grad():
                request = predict_episode(model, episode, feature_batch_size=32).numpy()
            mask = checked_request(request, episode, model)
            # Preserve actual causal requests before the one economic path.
            np.savez_compressed(
                output / (name + "_REQUESTS.npz"),
                request=request,
                decision_us=episode.windows.decision_us,
                eligible=mask,
            )
            targets, mapped = prototype.mapped_path(compress(request), episode.internal.contexts)
            with torch.no_grad():
                report = charged_boundary_path(
                    torch.tensor(targets, dtype=torch.float64),
                    episode.prices,
                    episode.funding_coeff,
                    plan=BoundaryPlan.full_fill_diagnostic(63),
                )
            record, rows = reconcile(request, episode, targets, mapped, report)
            if before != (
                model_identity(model),
                tree_identity(_rng_state()),
                tree_identity(optimizer.state_dict()),
            ):
                raise ValueError("Frozen model/Adam/allRNG changed during score")
            records[name], events[name] = record, report["risk_events"]
            np.savez_compressed(
                output / (name + "_PATH.npz"),
                request=request,
                targets=targets,
                budget=expand(np.stack([r["budget"] for r in mapped])),
                nav=report["nav"].numpy(),
                quantity=report["quantity"].numpy(),
                boundary_held_quantity=report["boundary_held_quantity"].numpy(),
            )
            with (output / (name + "_DAILY.csv")).open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            _atomic_json(output / (name + "_COMPLETED.json"), record)
            completed.append(name)
        a, b = (records[n] for n in ORDER)
        result = dict(
            status="TWO_FIXED_DAILY_WALLETS_COMPLETE_NOT_NATIVE",
            classification=CLASSIFICATION,
            policies=records,
            controls_reused=controls,
            expanded_minus773={
                k: b[k] - a[k]
                for k in (
                    "net_PnL",
                    "utility_sum",
                    "maximum_daily_drawdown",
                    "total_cost",
                    "funding",
                    "mean_active_opening_actual_gross",
                    "mean_active_boundary_actual_gross",
                )
            },
            model_identities=ready["models"],
            protocol_identity=protocol()["identity"],
            public_prescore_commit=public["remote_SHA"],
            scaler_identity=SCALER,
            new_daily_wallets=2,
            model_inferences=2,
            control_wallets_rerun=0,
            native_wallets=0,
            fits=0,
            optimizer_updates=0,
            scaler_updates=0,
            provider_downloads=0,
            model_Adam_all_RNG_unchanged=True,
            stop_after_fixed_pair=True,
            native_mark_gap=protocol()["native_mark_gap"],
            no_new_OOS=True,
            no_promotion=True,
            elapsed_seconds=time.monotonic() - began,
        )
        _atomic_json(output / "INPUT_RECEIPT.json", data)
    except Exception as error:
        result = dict(
            status="STOP_ONCE_ONLY_PAIRED_FAILURE",
            classification=CLASSIFICATION,
            completed_policies=completed,
            policies=records,
            error=type(error).__name__,
            reason=str(error),
            retry_authorized=False,
            elapsed_seconds=time.monotonic() - began,
        )
    _atomic_json(output / "RESULT.json", result)
    _atomic_json(output / "RISK_EVENTS.json", events)
    _atomic_json(
        output / "MANIFEST.json",
        dict(
            files=manifest(output), sources=sources(), protocol=protocol(), model_identities=MODELS
        ),
    )
    print(json.dumps(result, allow_nan=False), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    for name in ("state", "economics", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--publication", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    if args.action == "prepare":
        prepare(args.state, args.economics, args.output)
    else:
        if args.publication is None:
            parser.error("Verified public paired pre-score receipt required")
        run(args.state, args.economics, args.output, args.publication)
