"""Four own-path replays of frozen static requests, with native request exports."""

import argparse
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from modules.temporal_contrast21_probe.labels import forward_reader, standalone
from modules.temporal_short_expansion.adapter import ACTIVE_COORDINATES, compress, expand
from modules.temporal_short_expansion.model import E6
from modules.temporal_two_expert.exact import load_prototype
from modules.temporal_two_expert.inputs import CORE5

from .baseline import PROTOCOL, identity, sha, source_hashes


def context_episode(context, prototype):
    contexts = []
    for i, decision in enumerate(context["decision_us"]):
        mask = context["expert_eligible"][i, ACTIVE_COORDINATES].copy()
        mask[2] = False
        contexts.append(
            prototype.Context(
                int(decision),
                int(decision),
                context["expert_targets"][i, ACTIVE_COORDINATES],
                mask,
                context["past_returns30"][i],
                np.zeros(13),
                context["target_available_us"][i, ACTIVE_COORDINATES],
            )
        )
    return SimpleNamespace(
        contexts=tuple(contexts),
        internal=SimpleNamespace(contexts=tuple(contexts)),
        prices=context["surrogate_prices"],
        funding_coeff=context["surrogate_funding_coeff"],
        eligible=context["expert_eligible"],
        expert_targets=context["expert_targets"],
    )


def evaluate(root, state, selection_path, destination, producer_commit):
    root, state = root.resolve(), state.resolve()
    if destination.exists():
        raise FileExistsError("One fixed baseline output required")
    selection = json.loads(selection_path.read_text())
    saved_identity = selection.pop("selection_identity")
    if identity(selection) != saved_identity or selection["protocol"] != PROTOCOL:
        raise ValueError("Exact frozen no-CASH choices required")
    relative = "research/temporal-prefix-static-baseline-20261010/FROZEN_SELECTIONS.json"
    if (
        subprocess.check_output(["git", "show", producer_commit + ":" + relative], cwd=root)
        != selection_path.read_bytes()
    ):
        raise ValueError("Selected requests must be publicly frozen before evaluation")
    sources = source_hashes(root)
    for name in sources:
        file = root / name
        if (
            subprocess.check_output(["git", "show", producer_commit + ":" + name], cwd=root)
            != file.read_bytes()
        ):
            raise ValueError("Published source identity required")
    reader = forward_reader(root)
    prototype = load_prototype(state / "recovery/source/modules/direct_path/prototype.py")
    native_reference = json.loads(
        (root / "research/temporal-april-transfer-20261009/NATIVE_HANDOFF_RECEIPT.json").read_text()
    )
    records = []
    destination.mkdir(parents=True)
    for choice in selection["folds"]:
        date, slot, control = choice["fold"], choice["E6_slot"], choice["selected_control"]
        clock, paths, context, _, input_hashes = reader.read_bundle(root, date.replace("-", ""))
        request = np.zeros((63, 6))
        request[:, slot] = 1
        np.testing.assert_array_equal(request, paths[control + "_requests"])
        episode = context_episode(context, prototype)
        nav, targets, audit = standalone(episode, prototype, slot)
        np.testing.assert_array_equal(nav, paths[control + "_nav"])
        np.testing.assert_array_equal(targets, paths[control + "_targets"])
        _, mapped = prototype.mapped_path(compress(request), episode.internal.contexts)
        budget = expand(np.stack([r["budget"] for r in mapped]))
        np.testing.assert_array_equal(budget, paths[control + "_budget"])
        np.testing.assert_allclose(budget[:20, slot], np.arange(1, 21) / 20, rtol=0, atol=1e-14)
        np.testing.assert_allclose(budget[20:, slot], 1, rtol=0, atol=1e-14)
        assert (
            np.max(np.abs(np.diff(np.vstack([np.eye(6)[0], budget]), axis=0)).sum(1)) <= 0.1 + 1e-12
        )
        assert not request[:, 0].any() and not targets[-1].any()
        context_name = next(n for n in input_hashes if n.endswith("CURRENT_CONTEXT63.npz"))
        source_result_name = next(n for n in input_hashes if n.endswith("RESULT.json"))
        old = json.loads((root / source_result_name).read_text())["policies"]
        np.testing.assert_allclose(audit["net_PnL"], old[control]["net_PnL"], atol=2e-8, rtol=0)
        mdd = float(np.max(1 - nav / np.maximum.accumulate(nav)))
        np.testing.assert_allclose(mdd, old[control]["maximum_drawdown"], atol=1e-15, rtol=0)
        folder = destination / ("FOLD_" + date.replace("-", ""))
        folder.mkdir()
        request_clock = np.full(63, choice["latest_label_available_us"], np.int64)
        feature_clock = np.maximum(request_clock, context["expert_input_available_us"].max(1))
        assert np.all(feature_clock <= clock) and np.all(request_clock < clock)
        np.savez_compressed(
            folder / "REQUESTS.npz",
            decision_us=clock,
            symbol_order=np.array(CORE5),
            expert_order=np.array(E6),
            desired_expert_budget=request,
            action_eligible=context["expert_eligible"],
            feature_available_us=feature_clock,
            request_available_us=clock,
        )
        np.savez_compressed(
            folder / "SURROGATE_PATH.npz",
            decision_us=clock,
            nav=nav,
            targets=targets,
            mapped_expert_budget=budget,
        )
        comparisons = {}
        for title, key in [("Static50", "VOL50_CS50"), ("Cash50", "CASH50_VOL25_CS25")]:
            v = paths[key + "_nav"]
            comparisons[title] = dict(
                net_PnL=old[key]["net_PnL"],
                maximum_drawdown=old[key]["maximum_drawdown"],
                fees=old[key]["fees"],
                spread=old[key]["spread"],
                slippage=old[key]["slippage"],
                funding=old[key]["funding"],
                charged_reduction_cost=old[key]["charged_reduction_cost"],
                risk_events=old[key]["risk_events"],
                paid_terminal_cash=old[key]["paid_terminal_cash"],
                capital=10000.0,
                independent_wallet=True,
            )
            np.testing.assert_allclose(
                v[-1] - 10000, comparisons[title]["net_PnL"], atol=2e-8, rtol=0
            )
            np.testing.assert_allclose(
                np.max(1 - v / np.maximum.accumulate(v)),
                comparisons[title]["maximum_drawdown"],
                atol=1e-15,
                rtol=0,
            )
        record = dict(
            fold=date,
            choice=choice,
            net_PnL=audit["net_PnL"],
            maximum_drawdown=mdd,
            accounting=audit,
            capital=10000.0,
            comparisons=comparisons,
            PnL_excess_vs_controls={
                n: audit["net_PnL"] - r["net_PnL"] for n, r in comparisons.items()
            },
            selected_saved_control_reproduces_bitwise=True,
            allocated_gross_max=max(r["allocated_leg_gross"] for r in mapped),
            allocated_asset_gross_max=max(
                float(r["allocated_underlier_gross"].max()) for r in mapped
            ),
            startup="CASH10000;previous_quote=None;initial_capacity0",
            actual_ramp_decisions=20,
            paid_terminal_clock_us=int(context["outcome_available_us"][-1]),
            native_results=False,
        )
        (folder / "RESULT.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        manifest = dict(
            schema="SOURCE_HASHED_FROZEN_PREFIX_STATIC_NATIVE63_REQUESTS_V1",
            fold=date,
            producer_commit=producer_commit,
            policy_type="prefix_static_no_CASH_candidate",
            model_parameters=0,
            optimizer_updates=0,
            selection_identity=saved_identity,
            selection_file=relative,
            selection_SHA256=sha(selection_path),
            versioned_sources=sources,
            request_file="REQUESTS.npz",
            request_schema="decision_us,symbol_order,expert_order,desired_expert_budget,action_eligible,feature_available_us,request_available_us",
            forward_context_file=context_name,
            forward_context_SHA256=input_hashes[context_name],
            input_source_files=input_hashes,
            initial_wallet_cash=10000.0,
            native_startup=record["startup"],
            terminal_close_available_us=record["paid_terminal_clock_us"],
            terminal="last_targets_forced_CASH_paid;constant_request_preserved",
            private_mapper_coordinates=list(ACTIVE_COORDINATES),
            native_contract_commit=native_reference["native_contract_commit"],
            native_contract_SHA256=native_reference["native_contract_SHA256"],
            native_rollout_status="NOT_RUN_AWAIT_NATIVE_DECISION",
            no_forward_selection=True,
            files={
                p.name: dict(SHA256=sha(p), bytes=p.stat().st_size)
                for p in sorted(folder.iterdir())
            },
        )
        (folder / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        records.append(record)
        print(
            json.dumps(dict(fold=date, choice=control, PnL=record["net_PnL"], MDD=mdd)), flush=True
        )
    result = dict(
        status="ONE_PREFIX_STATIC_NO_CASH_BASELINE_COMPLETE_AWAIT_NATIVE_DECISION",
        protocol=PROTOCOL,
        selection_identity=saved_identity,
        producer_commit=producer_commit,
        folds=records,
        surrogate_replays=4,
        fits=0,
        downloads=0,
        native_rollouts=0,
        policy_alternatives=0,
        no_return_aggregation_across_wallets=True,
    )
    (destination / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--state", required=True, type=Path)
    p.add_argument("--selections", required=True, type=Path)
    p.add_argument("--destination", required=True, type=Path)
    p.add_argument("--producer-commit", required=True)
    a = p.parse_args()
    evaluate(a.root, a.state, a.selections, a.destination, a.producer_commit)
