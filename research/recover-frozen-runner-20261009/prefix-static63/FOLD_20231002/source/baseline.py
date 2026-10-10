"""Freeze an expert using only common mature original-wallet21-day labels."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from modules.temporal_contrast21_probe.probe import FOLDS, path_windows, prefix_rows

EXPERTS = ("VOL_MANAGED_HOLD", "CSMOM21", "MOMENTUM30_SHORT_ONLY")
CONTROLS = ("VOL", "CS", "SHORT")
SLOTS = (1, 4, 5)
PINNED = {
    "INPUTS.npz": "20bc280e95435450677ddc0fa8edc979d5e5543abf4fda65236645e74db5a788",
    "TRAIN_STANDALONE_PATHS.npz": (
        "4315d9987354d58080e5e3ae78ac96ff40965f6934582043207fe2ed70c67e23"
    ),
    "PREPARED.json": "22072e506663f5fd062c982cdc2f9ee9664193026290f4b037722ad1e19d6aed",
}
PROTOCOL = dict(
    schema="ONE_MATURE_PREFIX_STATIC_THREE_EXPERT_NO_CASH_BENCHMARK_V1",
    folds=list(FOLDS),
    candidates=list(EXPERTS),
    explicit_CASH_candidate=False,
    criterion="largest_arithmetic_mean_of_cost_after21activeinterval_standalone_NAV_returns_on_identical_mature_prefix_labels",
    weighting="each_complete_common_nominated_label_equal_weight;unchanged371_462_553_644_rows;no_alternative_lookback",
    exclusions="incomplete_features;unmatured_labels;cross_episode_gap_or_paid_terminal_windows;unchanged_direct21_cohort",
    expert_inactivity="preserved;flat_short_and_eligibility_release_to_cash_remain_outcomes",
    ties="exact_argmax_first_in_fixed_VOL_CS_SHORT_order;no_tolerance_or_search",
    requests="constant_onehot_selected_canonical_E6_slot_for_all63_decisions;no_explicit_CASH_request",
    mapper="same_causal_eligibility_release_L1.1_cash_start20decision_ramp_gross.6_asset.3",
    wallet="one_continuous_fresh10000_shared_CORE5_wallet_per_fold;common_paid_terminal_flattening",
    accounting="unchanged_charged_daily_boundary_kernel_costs_funding_endogenous_risk_reductions",
    controls=["Static50=VOL50_CS50", "Cash50=CASH50_VOL25_CS25"],
    source_labels="inherited_standalone_marked_subperiods_not_fresh21day_wallet_or_switching_profits",
    role="repeatedly_examined_historical_development_not_novel_pristine_OOS",
    fits=0,
    model_parameters=0,
    downloads=0,
    native_rollouts=0,
    maximum_surrogate_replays=4,
    stop="one_specification;no_weights_lookback_choice_rule_alternatives;await_native_decision",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def source_hashes(root):
    files = list(Path(__file__).parent.glob("*.py"))
    files += [
        root / name
        for name in (
            "modules/temporal_contrast21_probe/labels.py",
            "modules/temporal_contrast21_probe/probe.py",
            "modules/temporal_predictability_probe/probe.py",
            "modules/temporal_risk_proxy_v2/proxy.py",
            "modules/temporal_short_expansion/adapter.py",
            "modules/temporal_short_expansion/model.py",
            "modules/temporal_two_expert/exact.py",
            "modules/temporal_two_expert/model.py",
            "modules/temporal_two_expert/inputs.py",
            "research/temporal-economic-relevance-20261010/READ_ECONOMIC_RELEVANCE.py",
        )
    ]
    return {str(p.relative_to(root)): sha(p) for p in files}


def choose(absolute, cache, cutoff):
    rows = prefix_rows(cache, cutoff)
    if (
        absolute.shape != (len(cache["train_decisions"]), 3)
        or not len(rows)
        or not np.isfinite(absolute[rows]).all()
    ):
        raise ValueError("Three comparable finite mature prefix outcomes required")
    means = absolute[rows].mean(0)
    selected = int(np.argmax(means))
    return selected, means, rows


def historical_panel(root):
    folder = root / "research/temporal-contrast21-probe-20261010"
    for name, expected in PINNED.items():
        if sha(folder / name) != expected:
            raise ValueError("Exact closed direct-contrast source artifacts required")
    # Deliberately load no forward labels, forward features or forward outcomes.
    with np.load(folder / "INPUTS.npz", allow_pickle=False) as z:
        cache = {
            k: z[k].copy()
            for k in [
                "train_decisions",
                "train_label_available",
                "train_wallet_id",
                "train_ready",
                "train_y",
            ]
        }
    with np.load(folder / "TRAIN_STANDALONE_PATHS.npz", allow_pickle=False) as z:
        paths = {k: z[k].copy() for k in z.files}
    absolute = np.empty((len(cache["train_decisions"]), 3))
    for wallet in range(5):
        rows = np.flatnonzero(cache["train_wallet_id"] == wallet)
        d, available = (
            paths[f"wallet{wallet}_decisions"],
            paths[f"wallet{wallet}_outcome_available"],
        )
        for j, name in enumerate(CONTROLS):
            starts, values, mature, _ = path_windows(
                d, available, paths[f"wallet{wallet}_{name}_nav"]
            )
            np.testing.assert_array_equal(d[starts], cache["train_decisions"][rows])
            np.testing.assert_array_equal(mature, cache["train_label_available"][rows])
            absolute[rows, j] = values
    np.testing.assert_allclose(
        absolute[:, 0] - absolute[:, 2], cache["train_y"][:, 0], atol=1e-15, rtol=0
    )
    np.testing.assert_allclose(
        absolute[:, 0] - absolute[:, 1], cache["train_y"][:, 1], atol=1e-15, rtol=0
    )
    return absolute, cache


def freeze(root, destination):
    if destination.exists():
        raise FileExistsError("Selections must be frozen once before forward reading")
    absolute, cache = historical_panel(root)
    folds = []
    for date, expected in zip(FOLDS, [371, 462, 553, 644], strict=True):
        start = int(np.datetime64(date, "us").astype(np.int64))
        selected, means, rows = choose(absolute, cache, start)
        if len(rows) != expected or cache["train_label_available"][rows].max() >= start:
            raise ValueError("Exact strict maturity/cohort required")
        folds.append(
            dict(
                fold=date,
                selected_expert=EXPERTS[selected],
                selected_control=CONTROLS[selected],
                E6_slot=SLOTS[selected],
                prefix_means=dict(zip(EXPERTS, means.tolist(), strict=True)),
                mature_labels=len(rows),
                first_forward_decision_us=start,
                latest_label_available_us=int(cache["train_label_available"][rows].max()),
                labels_by_original_wallet={
                    str(int(w)): int((cache["train_wallet_id"][rows] == w).sum())
                    for w in np.unique(cache["train_wallet_id"][rows])
                },
            )
        )
    receipt = dict(
        status="ALL_FOUR_PREFIX_ONLY_STATIC_CHOICES_FROZEN_BEFORE_FORWARD_READ",
        protocol=PROTOCOL,
        source_files=PINNED,
        folds=folds,
        forward_outcomes_read=0,
        fits=0,
    )
    receipt["selection_identity"] = identity(receipt)
    destination.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            dict(status=receipt["status"], choices=[f["selected_control"] for f in folds], fits=0)
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--destination", required=True, type=Path)
    a = p.parse_args()
    freeze(a.root, a.destination)
