"""Frozen256 inference, source-bound native requests, exactly four daily wallets."""

import argparse
import csv
import json
import shutil
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import torch

from modules.temporal_episode_weighting_v2.export import ADAPTER_COMMIT, ADAPTER_SHA256
from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_fresh_initialization.export import feature_clock
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, BoundaryStop
from modules.temporal_selected_refit.protocol import protocol
from modules.temporal_selected_refit.protocol import sources as fitting_sources
from modules.temporal_selected_refit.stage import ARM, frozen_state
from modules.temporal_short_expansion.adapter import compress, expand
from modules.temporal_short_expansion.model import E6
from modules.temporal_two_expert.checkpoint import _atomic_json, _rng_state, model_identity
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import CORE5, array_digest, digest

from .data import EXECUTION_DELAY_US, ROOT, load
from .reconcile import reconcile
from .terminal import charged_terminal_path

CONTROLS = dict(
    FROZEN_VOL=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    Static50=[0.0, 0.5, 0.0, 0.0, 0.5, 0.0],
    Cash50=[0.5, 0.25, 0.0, 0.0, 0.25, 0.0],
)
ORDER = ["SELECTED_FULL773_256", *CONTROLS]


def sources():
    return {
        **fitting_sources(),
        **{str(p.relative_to(ROOT)): sha(p) for p in Path(__file__).parent.glob("*.py")},
        **{
            str(p.relative_to(ROOT)): sha(p)
            for p in (ROOT / "modules/temporal_july_transfer").rglob("*.py")
        },
    }


def manifest(directory):
    return {
        str(p.relative_to(directory)): dict(bytes=p.stat().st_size, SHA256=sha(p))
        for p in directory.rglob("*")
        if p.is_file() and p.name != "MANIFEST.json"
    }


def native_export(output, fit_output, episode, request, model, saved, terminal, inputs):
    """Actual requests exported and read back before economic scoring."""
    bundle = output / "native-handoff"
    bundle.mkdir()
    mask = episode.eligible & np.array([n in model.contract["allowed_actions"] for n in E6])
    if np.any(request[~mask]):
        raise ValueError("Actual native requests must respect exact eligible action mask")
    np.savez_compressed(
        bundle / "REQUESTS.npz",
        decision_us=episode.windows.decision_us,
        symbol_order=np.array(CORE5),
        expert_order=np.array(E6),
        desired_expert_budget=request,
        action_eligible=mask,
        feature_available_us=feature_clock(episode),
        request_available_us=episode.windows.decision_us,
    )
    for name, vector in CONTROLS.items():
        np.savez_compressed(
            bundle / ("REQUESTS_" + name + ".npz"),
            decision_us=episode.windows.decision_us,
            symbol_order=np.array(CORE5),
            expert_order=np.array(E6),
            desired_expert_budget=np.tile(vector, (92, 1)),
            action_eligible=mask,
            feature_available_us=feature_clock(episode),
            request_available_us=episode.windows.decision_us,
        )
    np.savez_compressed(
        bundle / "CURRENT_EXPERT_INPUTS92.npz",
        decision_us=episode.windows.decision_us,
        symbol_order=np.array(CORE5),
        expert_order=np.array(E6),
        expert_targets=episode.expert_targets,
        expert_eligible=episode.eligible,
        target_available_us=episode.target_available_us,
        past_returns30=np.stack([c.past_returns30 for c in episode.contexts]),
        expert_state=episode.expert_state,
        input_available_us=episode.expert_input_available_us,
    )
    folder = Path(fit_output) / ARM
    pointer = json.loads((folder / "latest.json").read_text())
    shutil.copy2(folder / pointer["file"], bundle / "MODEL_ADAM_RNG.pt")
    for name in ("RUN.json", "TERMINAL.json", "latest.json", "SCALER.npz", "SCALER.json"):
        shutil.copy2(folder / name, bundle / name)
    _atomic_json(bundle / "PROTOCOL.json", protocol())
    all_sources = sources()
    for name in all_sources:
        path = bundle / "source" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, path)
    record = dict(
        schema="SOURCE_BOUND_SELECTED256_Q4_NATIVE92_REQUESTS_V1",
        classification="PROJECT_SEEN_BUT_UNTOUCHED_BY_THIS_TUNING_STUDY",
        model_identity=model_identity(model),
        checkpoint_SHA256=terminal["checkpoint_SHA256"],
        protocol_identity=protocol()["identity"],
        protocol_SHA256=sha(bundle / "PROTOCOL.json"),
        run_id=saved["binding"]["run_id"],
        training_updates=256,
        parameters=13699,
        fresh_all_Adam_ages=256,
        scaler_identity=inputs["scaler_identity"],
        scaler_training_rows=907,
        decisions=92,
        active_intervals=91,
        expert_order=list(E6),
        symbol_order=list(CORE5),
        uses_feedback_features=False,
        economic_source_commit=inputs["economics"]["source_commit"],
        terminal_execution_us=int(episode.windows.decision_us[-1] + EXECUTION_DELAY_US),
        terminal_UTC="2024-12-31T00:01:00.000001Z",
        paid_final_flat=True,
        native_execution_results=False,
        reference_native61_adapter_commit=ADAPTER_COMMIT,
        reference_native61_adapter_contract_sha256=ADAPTER_SHA256,
        native92_adapter_certified=False,
        future_native_replay_requires_calendar_adapter=True,
        execution_contract="shared10000wallet;gross.6;asset.3;budgetL1.1;originalsignedfunding/costs/eligibility;paidclose",
        source_files=all_sources,
        episode_identity=episode.identity,
        files=manifest(bundle),
        request_file="REQUESTS.npz",
        control_request_files={name: "REQUESTS_" + name + ".npz" for name in CONTROLS},
        current_expert_input_file="CURRENT_EXPERT_INPUTS92.npz",
    )
    _atomic_json(bundle / "MANIFEST.json", record)
    for name, entry in record["files"].items():
        path = bundle / name
        if entry != dict(bytes=path.stat().st_size, SHA256=sha(path)):
            raise ValueError("Native bundle byte readback differs")
    if sha(bundle / "MODEL_ADAM_RNG.pt") != terminal["checkpoint_SHA256"]:
        raise ValueError("Native checkpoint bytes differ")
    with np.load(bundle / "REQUESTS.npz", allow_pickle=False) as z:
        np.testing.assert_array_equal(z["desired_expert_budget"], request)
        for name, expected in dict(
            decision_us=episode.windows.decision_us,
            symbol_order=np.array(CORE5),
            expert_order=np.array(E6),
            action_eligible=mask,
            feature_available_us=feature_clock(episode),
            request_available_us=episode.windows.decision_us,
        ).items():
            np.testing.assert_array_equal(z[name], expected)
        if np.any(z["feature_available_us"] > z["decision_us"]) or np.any(request[:, 2:4]):
            raise ValueError("Native causal masks differ")
    with np.load(bundle / "CURRENT_EXPERT_INPUTS92.npz", allow_pickle=False) as z:
        for name, expected in dict(
            decision_us=episode.windows.decision_us,
            symbol_order=np.array(CORE5),
            expert_order=np.array(E6),
            expert_targets=episode.expert_targets,
            expert_eligible=episode.eligible,
            target_available_us=episode.target_available_us,
            past_returns30=np.stack([c.past_returns30 for c in episode.contexts]),
            expert_state=episode.expert_state,
            input_available_us=episode.expert_input_available_us,
        ).items():
            np.testing.assert_array_equal(z[name], expected)
    return record


def run(state, economics, fit_output, output, input_binding):
    output = Path(output)
    if output.exists():
        raise FileExistsError("Exclusive once-only Q4 output required; never rescore")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    pa.set_io_thread_count(1)
    pa.set_cpu_count(1)
    model, optimizer, scaler, saved, terminal = frozen_state(state, fit_output)
    # The completed/frozen refit is checked before any feature or economics rows.
    episode, prototype, inputs = load(state, economics, scaler, terminal)
    bound = json.loads(Path(input_binding).read_text())
    if (
        bound["episode_identity"] != episode.identity
        or bound["features_identity"] != episode.windows.identity
        or bound["prices_identity"] != array_digest(episode.prices)
        or bound["funding_identity"] != array_digest(episode.funding_coeff)
        or bound["expert_state_identity"] != array_digest(episode.expert_state)
        or bound["checkpoint_SHA256"] != terminal["checkpoint_SHA256"]
        or bound["versioned_sources"] != sources()
    ):
        raise ValueError("Frozen pre-score Q4 input/source/checkpoint binding changed")
    identity, rng, adam = (
        model_identity(model),
        tree_identity(_rng_state()),
        tree_identity(optimizer.state_dict()),
    )
    model.eval()
    began = time.monotonic()
    with torch.no_grad():
        request = predict_episode(model, episode, feature_batch_size=32).numpy()
    if (
        request.shape != (92, 6)
        or not np.isfinite(request).all()
        or np.any(request < 0)
        or np.any(request[:, 2:4])
        or not np.allclose(request.sum(1), 1, rtol=0, atol=1e-12)
    ):
        raise ValueError("Finite canonical masked request simplex required")
    output.mkdir()
    _atomic_json(
        output / "ONCE_ONLY_STARTED.json",
        dict(
            model_identity=identity,
            training_updates=256,
            protocol_identity=protocol()["identity"],
            policy_order=ORDER,
            episode_identity=episode.identity,
        ),
    )
    native_export(output, fit_output, episode, request, model, saved, terminal, inputs)
    arrays, records, events, daily = {}, {}, {}, []
    for name in ORDER:
        actual = request if name == ORDER[0] else np.tile(CONTROLS[name], (92, 1))
        targets, mapped = prototype.mapped_path(compress(actual), episode.internal.contexts)
        try:
            with torch.no_grad():
                report = charged_terminal_path(
                    torch.tensor(targets, dtype=torch.float64),
                    episode.prices,
                    episode.funding_coeff,
                    plan=BoundaryPlan.full_fill_diagnostic(92),
                )
        except BoundaryStop as error:
            records[name] = dict(
                status="STOP_FINANCIAL_PATH_FAILURE",
                reason=error.reason,
                day_index=error.day_index,
                marked_equity_at_stop=error.equity,
                quantity_at_stop=error.quantity.tolist(),
                mark_at_stop=error.mark.tolist(),
                reduction_cost_at_stop=error.reduction_cost,
                paid_terminal_cash=False,
            )
            events[name] = [records[name]]
            arrays.update(
                {
                    name + "_requests": actual,
                    name + "_targets": targets,
                    name + "_budget": expand(np.stack([r["budget"] for r in mapped])),
                }
            )
            _atomic_json(output / (name + "_FAILED.json"), records[name])
            np.savez_compressed(
                output / (name + "_PATH.npz"),
                **{k: v for k, v in arrays.items() if k.startswith(name + "_")},
            )
            continue
        metrics, rows = reconcile(actual, episode, targets, mapped, report)
        records[name], events[name] = metrics, report["risk_events"]
        daily.extend([dict(policy=name, **r) for r in rows])
        arrays.update(
            {
                name + "_" + k: v
                for k, v in dict(
                    requests=actual,
                    targets=targets,
                    budget=expand(np.stack([r["budget"] for r in mapped])),
                    nav=report["nav"].numpy(),
                    quantity=report["quantity"].numpy(),
                    boundary_held_quantity=report["boundary_held_quantity"].numpy(),
                ).items()
            }
        )
        # Durable completed path makes an interruption auditable; never rerun it.
        _atomic_json(output / (name + "_COMPLETED.json"), metrics)
        np.savez_compressed(
            output / (name + "_PATH.npz"),
            **{k: v for k, v in arrays.items() if k.startswith(name + "_")},
        )
    np.savez_compressed(
        output / "PAIRED_PATHS.npz",
        decision_us=episode.windows.decision_us,
        symbol_order=np.array(CORE5),
        expert_order=np.array(E6),
        **arrays,
    )
    np.savez_compressed(
        output / "CURRENT_CONTEXT.npz",
        decision_us=episode.windows.decision_us,
        prices=episode.prices,
        funding_coeff=episode.funding_coeff,
        expert_targets=episode.expert_targets,
        expert_eligible=episode.eligible,
        target_available_us=episode.target_available_us,
        past_returns30=np.stack([c.past_returns30 for c in episode.contexts]),
        expert_state=episode.expert_state,
        input_available_us=episode.expert_input_available_us,
        outcome_available_us=episode.label_available_us,
    )
    values = np.concatenate((episode.windows.values[0], episode.windows.values[1:, -1]))
    clocks = np.r_[episode.windows.completed_us[0], episode.windows.completed_us[1:, -1]]
    np.savez_compressed(
        output / "FEATURE_ROWS.npz",
        completed_us=clocks,
        values=values,
        valid=np.concatenate((episode.windows.valid[0], episode.windows.valid[1:, -1])),
        step_valid=np.concatenate(
            (episode.windows.step_valid[0], episode.windows.step_valid[1:, -1])
        ),
        symbol_order=np.array(CORE5),
        feature_order=np.array(inputs["feature_order"]),
        aggregate_order=np.array(inputs["aggregate_order"]),
    )
    with (output / "DAILY_ACCOUNTING.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(daily[0]) if daily else ["policy"], lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(daily)
    selected, vol = records[ORDER[0]], records["FROZEN_VOL"]
    if (
        identity != model_identity(model)
        or rng != tree_identity(_rng_state())
        or adam != tree_identity(optimizer.state_dict())
    ):
        raise ValueError("Frozen inference/scoring changed model/Adam/allRNG")

    def comparison(key):
        return selected[key] - vol[key] if key in selected and key in vol else None

    failures = [n for n, r in records.items() if r["status"] == "STOP_FINANCIAL_PATH_FAILURE"]
    score = dict(
        schema="SELECTED_FULL773_FRESH256_RESERVED_Q4_ONCE_DAILY_V1",
        classification="PROJECT_SEEN_BUT_UNTOUCHED_BY_THIS_TUNING_STUDY",
        status="CHARGED_DAILY_SURROGATE_NOT_NATIVE"
        if not failures
        else "FINANCIAL_PATH_FAILURE_RECORDED",
        failed_policies=failures,
        policies=records,
        policy_order=ORDER,
        primary_control="FROZEN_VOL",
        primary_PnL_excess=comparison("net_PnL"),
        primary_utility_excess=comparison("utility_sum"),
        primary_drawdown_difference=comparison("maximum_daily_drawdown"),
        model_identity=identity,
        checkpoint_SHA256=terminal["checkpoint_SHA256"],
        protocol_identity=protocol()["identity"],
        parameters=13699,
        training_updates=256,
        reserve_model_scores=1,
        daily_wallets=4,
        native_wallets=0,
        optimizer_updates=0,
        scaler_updates=0,
        provider_downloads=0,
        synthetic_input_rows=0,
        terminal_UTC="2024-12-31T00:01:00.000001Z",
        elapsed_seconds=time.monotonic() - began,
        model_Adam_all_RNG_unchanged=True,
        no_Q4_checkpoint_selection=True,
        no_model_promotion=True,
        input_binding_SHA256=sha(Path(input_binding)),
        verified_existing_Q4_controls_reused=False,
        control_reuse_reason="No existing identical Q4 paths; one score for each fixed control",
    )
    for name, value in (
        ("RESULT.json", score),
        ("INPUT_RECEIPT.json", inputs),
        ("RISK_EVENTS.json", events),
    ):
        _atomic_json(output / name, value)
    _atomic_json(
        output / "MANIFEST.json",
        dict(
            files=manifest(output),
            versioned_sources=sources(),
            episode_identity=episode.identity,
            feature_rows_identity=array_digest(values),
            completed_us_identity=array_digest(clocks),
            result_identity=digest(score),
        ),
    )
    print(
        json.dumps(
            dict(
                status=score["status"],
                primary_PnL_excess=score["primary_PnL_excess"],
                policies={
                    n: dict(
                        status=r["status"],
                        net_PnL=r.get("net_PnL"),
                        MDD=r.get("maximum_daily_drawdown"),
                    )
                    for n, r in records.items()
                },
            )
        ),
        flush=True,
    )
    return score


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("state", "economics", "fit-output", "output", "input-binding"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    run(args.state, args.economics, args.fit_output, args.output, args.input_binding)
