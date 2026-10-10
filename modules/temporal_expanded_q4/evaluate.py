"""Thin one-model adapter; unchanged Q4 source, mapper, paid wallet and accounting."""

import argparse
import csv
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import torch

from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_expanded_refit.protocol import ARM, ROOT, protocol
from modules.temporal_expanded_refit.protocol import sources as fit_sources
from modules.temporal_expanded_refit.stage import frozen_state
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_fresh_initialization.export import feature_clock
from modules.temporal_q4_reserved.data import EXECUTION_DELAY_US, load
from modules.temporal_q4_reserved.evaluate import manifest
from modules.temporal_q4_reserved.reconcile import reconcile
from modules.temporal_q4_reserved.terminal import charged_terminal_path
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan
from modules.temporal_short_expansion.adapter import compress, expand
from modules.temporal_short_expansion.model import E6
from modules.temporal_two_expert.checkpoint import _atomic_json, _rng_state, model_identity
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import CORE5, array_digest

CLASSIFICATION = "SEEN_HISTORICAL_DEVELOPMENT_CONTROLLED_ADDED_DATA_COMPARISON"
OLD_RESULT_SHA = "cfb72dc34ad686a389cc49106a2f0b581fe84b33e1edabe53c36acbe92921471"
OLD_EPISODE = "7cadc047584f6d0044c16f2682270cf6ecb641992625b7e482cf7428eb1cf7ff"
OLD_DIR = ROOT / "research/temporal-selected-refit-q4-20261010/q4-results"


def sources():
    return {
        **fit_sources(),
        **{
            str(p.relative_to(ROOT)): sha(p)
            for folder in ("temporal_expanded_q4", "temporal_q4_reserved", "temporal_july_transfer")
            for p in (ROOT / "modules" / folder).rglob("*.py")
        },
    }


def checked_request(request, episode, model):
    mask = episode.eligible & np.array([n in model.contract["allowed_actions"] for n in E6])
    if (
        request.shape != (92, 6)
        or not np.isfinite(request).all()
        or np.any(request < 0)
        or np.any(request[~mask])
        or np.any(request[:, 2:4])
        or not np.allclose(request.sum(1), 1, rtol=0, atol=1e-12)
        or np.any(feature_clock(episode) > episode.windows.decision_us)
    ):
        raise ValueError("Canonical causal masked92 request simplex required")
    return mask


def reuse(episode, inputs):
    """Only read old receipts/arrays; never call old model or a comparator wallet."""
    if sha(OLD_DIR / "RESULT.json") != OLD_RESULT_SHA or episode.identity != OLD_EPISODE:
        raise ValueError("Immutable saved comparison identity changed")
    old_manifest = json.loads((OLD_DIR / "MANIFEST.json").read_text())
    for name in ("CURRENT_CONTEXT.npz", "FEATURE_ROWS.npz", "INPUT_RECEIPT.json"):
        if sha(OLD_DIR / name) != old_manifest["files"][name]["SHA256"]:
            raise ValueError("Saved comparison inputs changed")
    old_inputs = json.loads((OLD_DIR / "INPUT_RECEIPT.json").read_text())
    if inputs["scaler_identity"] != old_inputs["scaler_identity"]:
        raise ValueError("Same907 scaler required for paired added-data comparison")
    context = dict(
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
    with np.load(OLD_DIR / "CURRENT_CONTEXT.npz", allow_pickle=False) as old:
        for name, value in context.items():
            np.testing.assert_array_equal(old[name], value)
    values = np.concatenate((episode.windows.values[0], episode.windows.values[1:, -1]))
    clocks = np.r_[episode.windows.completed_us[0], episode.windows.completed_us[1:, -1]]
    with np.load(OLD_DIR / "FEATURE_ROWS.npz", allow_pickle=False) as old:
        for name, value in dict(
            completed_us=clocks,
            values=values,
            valid=np.concatenate((episode.windows.valid[0], episode.windows.valid[1:, -1])),
            step_valid=np.concatenate(
                (episode.windows.step_valid[0], episode.windows.step_valid[1:, -1])
            ),
            symbol_order=np.array(CORE5),
        ).items():
            np.testing.assert_array_equal(old[name], value)
    return json.loads((OLD_DIR / "RESULT.json").read_text())["policies"]


def differences(actual, comparators):
    return {
        name: {
            key: actual[key] - metrics[key]
            for key in ("net_PnL", "utility_sum", "maximum_daily_drawdown")
        }
        for name, metrics in comparators.items()
    }


def native_export(output, fit_output, episode, request, mask, terminal, saved, inputs):
    bundle = output / "native-handoff"
    bundle.mkdir()
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
    with np.load(bundle / "REQUESTS.npz", allow_pickle=False) as z:
        np.testing.assert_array_equal(z["desired_expert_budget"], request)
        np.testing.assert_array_equal(z["action_eligible"], mask)
        np.testing.assert_array_equal(z["decision_us"], episode.windows.decision_us)
    folder = Path(fit_output) / ARM
    pointer = json.loads((folder / "latest.json").read_text())
    if sha(folder / pointer["file"]) != terminal["checkpoint_SHA256"]:
        raise ValueError("Exact frozen checkpoint required")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    record = dict(
        schema="SOURCE_BOUND_EXPANDED1137_FIXED907_FRESH256_Q4_NATIVE92_V1",
        classification=CLASSIFICATION,
        decisions=92,
        active_intervals=91,
        model_identity=terminal["model_identity"],
        checkpoint_SHA256=terminal["checkpoint_SHA256"],
        checkpoint_public_path="research/temporal-expanded-refit-q4-20261010/frozen/"
        + pointer["file"],
        run_id=saved["binding"]["run_id"],
        protocol=protocol(),
        source_commit=head,
        source_files=sources(),
        scaler_identity=inputs["scaler_identity"],
        scaler_training_rows=907,
        episode_identity=episode.identity,
        economic_source=inputs["economics"],
        expert_order=list(E6),
        symbol_order=list(CORE5),
        execution_contract="shared10000;gross.6;asset.3;budgetL1.1;originalcost/signedfunding/risk;paidclose",
        terminal_execution_us=int(episode.windows.decision_us[-1] + EXECUTION_DELAY_US),
        terminal_UTC="2024-12-31T00:01:00.000001Z",
        paid_final_flat=True,
        native_execution_results=False,
        controls_reused_without_new_requests=True,
        current_context_reference="research/temporal-selected-refit-q4-20261010/q4-results/CURRENT_CONTEXT.npz",
        current_context_SHA256=sha(OLD_DIR / "CURRENT_CONTEXT.npz"),
        feature_rows_reference="research/temporal-selected-refit-q4-20261010/q4-results/FEATURE_ROWS.npz",
        feature_rows_SHA256=sha(OLD_DIR / "FEATURE_ROWS.npz"),
        files=manifest(bundle),
    )
    _atomic_json(bundle / "MANIFEST.json", record)
    return record


def publication_gate(public, terminal, checkpoint_file):
    expected_path = "research/temporal-expanded-refit-q4-20261010/frozen/" + checkpoint_file
    if public["status"] != "PASS_ALL_PUBLIC_BYTES" or not any(
        f["path"] == expected_path and f["SHA256"] == terminal["checkpoint_SHA256"]
        for f in public["files"]
    ):
        raise ValueError("Actual public terminal freeze readback required before Q4 inputs")
    source_path = "research/temporal-expanded-refit-q4-20261010/frozen/EVALUATION_SOURCES.json"
    if not any(
        f["path"] == source_path and f["SHA256"] == sha(ROOT / source_path) for f in public["files"]
    ):
        raise ValueError("Published pre-score evaluation source receipt required")
    if json.loads((ROOT / source_path).read_text()) != sources():
        raise ValueError("Frozen evaluation source set changed before Q4 loading")


def run(state, train_economics, q4_economics, fit_output, output, publication):
    output = Path(output)
    output.mkdir()  # Exclusive durable claim before even loading the frozen model.
    _atomic_json(
        output / "ONCE_ONLY_STARTED.json",
        dict(classification=CLASSIFICATION, phase="frozen_model_load"),
    )
    began = time.monotonic()
    try:
        model, optimizer, scaler, saved, terminal = frozen_state(state, train_economics, fit_output)
        public = json.loads(Path(publication).read_text())
        publication_gate(
            public,
            terminal,
            json.loads((Path(fit_output) / ARM / "latest.json").read_text())["file"],
        )
        episode, prototype, inputs = load(state, q4_economics, scaler, terminal)
        inputs["classification"] = CLASSIFICATION
        comparators = reuse(episode, inputs)
        identity, rng, adam = (
            model_identity(model),
            tree_identity(_rng_state()),
            tree_identity(optimizer.state_dict()),
        )
        _atomic_json(
            output / "INPUT_BINDING.json",
            dict(
                checkpoint_SHA256=terminal["checkpoint_SHA256"],
                public_terminal_commit=public["remote_SHA"],
                episode_identity=episode.identity,
                features_identity=episode.windows.identity,
                prices_identity=array_digest(episode.prices),
                funding_identity=array_digest(episode.funding_coeff),
                source_files=sources(),
                saved_comparison_SHA256=OLD_RESULT_SHA,
            ),
        )
        model.eval()
        with torch.no_grad():
            request = predict_episode(model, episode, feature_batch_size=32).numpy()
        mask = checked_request(request, episode, model)
        native_export(output, fit_output, episode, request, mask, terminal, saved, inputs)
        targets, mapped = prototype.mapped_path(compress(request), episode.internal.contexts)
        with torch.no_grad():
            report = charged_terminal_path(
                torch.tensor(targets, dtype=torch.float64),
                episode.prices,
                episode.funding_coeff,
                plan=BoundaryPlan.full_fill_diagnostic(92),
            )
        metrics, rows = reconcile(request, episode, targets, mapped, report)
        np.savez_compressed(
            output / "EXPANDED_PATH.npz",
            decision_us=episode.windows.decision_us,
            request=request,
            targets=targets,
            budget=expand(np.stack([r["budget"] for r in mapped])),
            nav=report["nav"].numpy(),
            quantity=report["quantity"].numpy(),
            boundary_held_quantity=report["boundary_held_quantity"].numpy(),
        )
        with (output / "DAILY_ACCOUNTING.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        if (identity, rng, adam) != (
            model_identity(model),
            tree_identity(_rng_state()),
            tree_identity(optimizer.state_dict()),
        ):
            raise ValueError("Frozen model/Adam/allRNG changed")
        score = dict(
            status="CHARGED_DAILY_SURROGATE_NOT_NATIVE",
            classification=CLASSIFICATION,
            policies={ARM: metrics, **comparators},
            differences=differences(metrics, comparators),
            old_result_SHA256=OLD_RESULT_SHA,
            old_model_and_three_controls_reused=True,
            new_model_scores=1,
            new_daily_wallets=1,
            new_native_wallets=0,
            training_updates=256,
            parameters=13699,
            normalization_refitted=False,
            model_identity=identity,
            checkpoint_SHA256=terminal["checkpoint_SHA256"],
            model_Adam_all_RNG_unchanged=True,
            provider_downloads=0,
            no_new_OOS_claim=True,
            no_checkpoint_selection=True,
            no_promotion=True,
            elapsed_seconds=time.monotonic() - began,
        )
        _atomic_json(output / "INPUT_RECEIPT.json", inputs)
        _atomic_json(output / "RISK_EVENTS.json", report["risk_events"])
    except Exception as error:
        score = dict(
            status="STOP_ONCE_ONLY_EVALUATION_FAILURE",
            classification=CLASSIFICATION,
            exception=type(error).__name__,
            reason=str(error),
            elapsed_seconds=time.monotonic() - began,
            retry_authorized=False,
        )
        _atomic_json(output / "FAILURE.json", score)
    _atomic_json(output / "RESULT.json", score)
    _atomic_json(output / "MANIFEST.json", dict(files=manifest(output), source_files=sources()))
    print(json.dumps(score, allow_nan=False), flush=True)
    return score


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("state", "train-economics", "q4-economics", "fit-output", "output", "publication"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    run(
        args.state,
        args.train_economics,
        args.q4_economics,
        args.fit_output,
        args.output,
        args.publication,
    )
