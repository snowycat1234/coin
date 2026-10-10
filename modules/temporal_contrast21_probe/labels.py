"""Cost-after standalone labels from cached contexts and the frozen mapper/kernel."""

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch

from modules.temporal_predictability_probe.probe import load
from modules.temporal_prequential_transfer.data import close_slice, load_source
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, charged_boundary_path
from modules.temporal_short_expansion.adapter import ACTIVE_COORDINATES, compress

from .probe import FOLDS, path_windows, sha

EXPERTS = (("VOL", 1), ("SHORT", 5), ("CS", 4))


def standalone(episode, prototype, slot):
    n = len(episode.contexts)
    request = np.zeros((n, 6))
    request[:, slot] = 1
    targets, mapped = prototype.mapped_path(compress(request), episode.internal.contexts)
    with torch.no_grad():
        report = charged_boundary_path(
            torch.tensor(targets, dtype=torch.float64),
            episode.prices,
            episode.funding_coeff,
            plan=BoundaryPlan.full_fill_diagnostic(n),
        )
    if not report["terminal_cash_realized"] or np.any(targets[-1]):
        raise ValueError("Original charged paid terminal flattening required")
    nav = report["nav"].numpy().copy()
    audit = dict(
        fees=float(report["fees"]),
        spread=float(report["spread"]),
        slippage=float(report["slippage"]),
        funding=float(report["funding"]),
        charged_reduction_cost=float(report["charged_reduction_cost"]),
        risk_events=len(report["risk_events"]),
        paid_terminal_cash=True,
        net_PnL=float(report["net_PnL"]),
        eligible_days=int(episode.eligible[:, slot].sum()),
        flat_target_days=int(np.all(episode.expert_targets[:, slot] == 0, axis=1).sum()),
        mapped_gross_max=max(r["allocated_leg_gross"] for r in mapped),
    )
    return nav, targets, audit


def forward_reader(root):
    source = root / "research/temporal-economic-relevance-20261010/READ_ECONOMIC_RELEVANCE.py"
    if sha(source) != "2f8258e17c9a3962555e8e905c613562c623aa1e92bee619a330b6f0e0882c40":
        # The exact identity is filled before publication, never bypassed.
        raise ValueError("Exact frozen economic relevance reader required")
    spec = importlib.util.spec_from_file_location("_frozen_control_reader", source)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    return reader


def prepare(state, root, destination):
    if destination.exists():
        raise FileExistsError("One exclusive fixed label cache required")
    clocks, x, ready, _, _, nomination, features = load(state)
    original, prototype, execution_clocks = load_source(state)
    # Keep each genuine wallet whole. Its already forced-cash last decision
    # pays flattening at the known start mark, with a structural cash suffix.
    # Never treat the unused next-day source mark as another active interval.
    episodes = tuple(
        close_slice(
            e,
            0,
            len(e.contexts),
            cutoff_us=e.split_cutoff_us,
            role="TRAIN",
            wallet_id=e.wallet_id,
            execution_clocks=execution_clocks,
        )[0]
        for e in original
    )
    if not np.array_equal(np.concatenate([e.windows.decision_us for e in episodes]), nomination):
        raise ValueError("Exact five original wallets and778 nominated decisions required")
    train = {
        k: []
        for k in [
            "train_x",
            "train_y",
            "train_ready",
            "train_decisions",
            "train_label_available",
            "train_wallet_id",
        ]
    }
    paths, audits = {}, []
    for wallet, e in enumerate(episodes):
        navs, audit = {}, {}
        for name, slot in EXPERTS:
            nav, targets, record = standalone(e, prototype, slot)
            navs[name], audit[name] = nav, record
            paths[f"wallet{wallet}_{name}_nav"] = nav
            paths[f"wallet{wallet}_{name}_targets"] = targets
        d = e.windows.decision_us
        ix, vol, available, boundary = path_windows(d, e.label_available_us, navs["VOL"])
        labels = np.column_stack(
            [vol - path_windows(d, e.label_available_us, navs[name])[1] for name in ["SHORT", "CS"]]
        )
        rows = np.searchsorted(clocks, d[ix])
        np.testing.assert_array_equal(clocks[rows], d[ix])
        for key, value in dict(
            train_x=x[rows],
            train_y=labels,
            train_ready=ready[rows],
            train_decisions=d[ix],
            train_label_available=available,
            train_wallet_id=np.full(len(ix), wallet, np.int64),
        ).items():
            train[key].append(value)
        paths[f"wallet{wallet}_decisions"] = d
        paths[f"wallet{wallet}_outcome_available"] = e.label_available_us
        boundary["contrasts"] = {
            "VOL_MINUS_" + name: boundary["value"]
            - path_windows(d, e.label_available_us, navs[name])[3]["value"]
            for name in ["SHORT", "CS"]
        }
        audits.append(
            dict(
                wallet_id=e.wallet_id,
                identity=e.identity,
                decisions=len(d),
                full21active_labels=len(ix),
                terminal_span=boundary,
                controls=audit,
            )
        )
        print(
            f"Prepared original wallet{wallet}: {len(d)}decisions, {len(ix)}full labels", flush=True
        )
    cache = {k: np.concatenate(parts) for k, parts in train.items()}
    reader = forward_reader(root)
    forward = {
        k: [] for k in ["forward_x", "forward_y", "forward_decisions", "forward_label_available"]
    }
    forward_audits, sources = [], dict(features)
    for date in FOLDS:
        clock, saved, context, audit, hashes = reader.read_bundle(root, date.replace("-", ""))
        sources.update(hashes)
        # Actual saved context/kernel parity, retaining endogenous risk reductions.
        from types import SimpleNamespace

        internal = []
        for i, decision in enumerate(clock):
            mask = context["expert_eligible"][i, ACTIVE_COORDINATES].copy()
            mask[2] = False
            internal.append(
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
        e = SimpleNamespace(
            contexts=tuple(internal),
            internal=SimpleNamespace(contexts=tuple(internal)),
            prices=context["surrogate_prices"],
            funding_coeff=context["surrogate_funding_coeff"],
            eligible=context["expert_eligible"],
            expert_targets=context["expert_targets"],
        )
        for name, slot in EXPERTS:
            nav, targets, recomputed = standalone(e, prototype, slot)
            np.testing.assert_array_equal(nav, saved[name + "_nav"])
            np.testing.assert_array_equal(targets, saved[name + "_targets"])
            for field in [
                "fees",
                "spread",
                "slippage",
                "funding",
                "charged_reduction_cost",
                "risk_events",
            ]:
                expected = audit[name][
                    "charged_risk_reduction" if field == "charged_reduction_cost" else field
                ]
                np.testing.assert_allclose(recomputed[field], expected, rtol=0, atol=1e-12)
        outcomes = {name: reader.windows(saved[name + "_nav"]) for name, _ in EXPERTS}
        rows = np.searchsorted(clocks, clock[:43])
        np.testing.assert_array_equal(clocks[rows], clock[:43])
        if not ready[rows].all():
            raise ValueError("All fixed forward causal features must be valid")
        for key, value in dict(
            forward_x=x[rows],
            forward_y=np.column_stack([outcomes["VOL"] - outcomes[n] for n in ["SHORT", "CS"]]),
            forward_decisions=clock[:43],
            forward_label_available=context["outcome_available_us"][np.arange(43) + 20],
        ).items():
            forward[key].append(value)
        forward_audits.append(
            dict(fold=date, controls=audit, actual_saved_NAV_and_targets_bit_exact=True)
        )
        print(f"Verified all three frozen {date} control paths bitwise", flush=True)
    cache.update({k: np.stack(v) for k, v in forward.items()})
    destination.mkdir(parents=True)
    np.savez_compressed(destination / "INPUTS.npz", **cache)
    np.savez_compressed(destination / "TRAIN_STANDALONE_PATHS.npz", **paths)
    metadata = dict(
        status="FROZEN_COST_AFTER_STANDALONE_LABEL_CACHE_NO_FITS",
        cache_SHA256=sha(destination / "INPUTS.npz"),
        training_path_SHA256=sha(destination / "TRAIN_STANDALONE_PATHS.npz"),
        input_sources=sources,
        source_packet_SHA256=sha(state / "FROZEN_PACKET.json"),
        original_wallet_audit=audits,
        forward_audit=forward_audits,
        complete_training_labels=len(cache["train_y"]),
        historical_surrogate_paths=15,
        forward_parity_surrogate_paths=12,
        fits=0,
        neural_updates=0,
        native_rollouts=0,
        downloads=0,
        future_training_path_rows="full_original_wallets_cached_once;fit_admits_only_mature21active_labels_before_each_fold;no_future_row_normalization",
        label_fidelity="exact_existing_mapper_and_charged_boundary_kernel;all_forward_NAV_targets_costs_risk_events_reconcile",
    )
    (destination / "PREPARED.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            dict(
                status=metadata["status"],
                full_labels=len(cache["train_y"]),
                surrogate_paths=27,
                fits=0,
            )
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    prepare(args.state, args.root, args.destination)
