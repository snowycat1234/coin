"""Reuse frozen real episodes, then normalize only matured prefix label windows."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from modules.temporal_balanced_history.inputs import CUTOFF, from_arrays
from modules.temporal_two_expert.exact import load_prototype, sha
from modules.temporal_two_expert.inputs import (
    CORE5,
    DAY_US,
    WindowBatch,
    array_digest,
    digest,
    fit_standardizer,
)

TRAIN_END = 1672531200000000  # 2023-01-01 UTC
SELECT_END = 1704067200000000  # 2024-01-01 UTC
EXPECTED_LABEL_SHA = "29f068185205cce6ac886c16ddb463af42935fcb70ebc1b21b51a6e09c110146"
EXPECTED_EPISODES = [
    "f476d7cbe0b33a5e76f07e02fa04524101317edef0b68480164db65ac629a263",
    "4c4e3fba55a2c85e888e07c1914f39b98dbbb68804abf97d6c81ddf2df734947",
    "1effa0b70e4ee99b5d49edad39da2c449664bb78ed5fc21ac766c52a99b89298",
]


def install_io_guard(state):
    """Hard fail on any 2025-path open; retain observed state input opens."""
    state = str(Path(state).resolve())
    receipt = {"forbidden_2025_attempts": [], "state_file_opens": set()}

    def audit(event, args):
        if event != "open" or not args or not isinstance(args[0], (str, bytes)):
            return
        path = args[0].decode() if isinstance(args[0], bytes) else args[0]
        if "2025" in path:
            receipt["forbidden_2025_attempts"].append(path)
            raise PermissionError("2025 IO is forbidden in this chronological control")
        if str(Path(path).resolve()).startswith(state + "/"):
            receipt["state_file_opens"].add(str(Path(path).resolve()))

    sys.addaudithook(audit)
    return receipt


def io_receipt(receipt):
    return {
        "forbidden_2025_attempts": receipt["forbidden_2025_attempts"],
        "forbidden_2025_reads": 0,
        "state_file_opens": sorted(receipt["state_file_opens"]),
    }


def role_indices(decision, available):
    """Strict maturation purges target overlap, including availability latency."""
    d, a = np.asarray(decision), np.asarray(available)
    if np.any(a <= d) or np.any(a >= CUTOFF) or np.any(np.diff(d) <= 0):
        raise ValueError("Ordered, matured, pre-May2024 labels required")
    result = {
        "TRAIN": np.flatnonzero((d < TRAIN_END) & (a < TRAIN_END)),
        "SELECT2023": np.flatnonzero((d >= TRAIN_END) & (d < SELECT_END) & (a < SELECT_END)),
        "AUDIT2024": np.flatnonzero((d >= SELECT_END) & (a < CUTOFF)),
    }
    result["PURGED"] = np.setdiff1d(np.arange(len(d)), np.concatenate(list(result.values())))
    return result


def slice_windows(w, ix):
    return WindowBatch(
        *(
            getattr(w, name)[ix]
            for name in (
                "values",
                "valid",
                "step_valid",
                "completed_us",
                "available_us",
                "decision_us",
            )
        ),
        w.source_sha256,
    )


def load_episodes(state):
    """Equivalent episode construction; deliberately never call full training scaler."""
    state = Path(state)
    r = state / "data-expansion"
    feature_path, target_path = r / "training1290/FEATURES.npz", r / "training1290/TARGETS.npz"
    f, a = np.load(feature_path), np.load(target_path)
    p = load_prototype(state / "recovery/source/modules/direct_path/prototype.py")
    episodes, inputs = (
        [],
        {
            "training1290/FEATURES.npz": sha(feature_path),
            "training1290/TARGETS.npz": sha(target_path),
        },
    )
    for name, folder in [("Y2020", r / "early2020/economics2020"), ("Y2021", state / "early2021")]:
        path = folder / "ECONOMICS.npz"
        b = np.load(path)
        d = b["decision_us"]
        ix = np.searchsorted(a["decision_us"], d)
        np.testing.assert_array_equal(a["decision_us"][ix], d)
        source = digest(
            {"features": sha(feature_path), "targets": sha(target_path), "economics": sha(path)}
        )
        inputs[str(path.relative_to(state))] = sha(path)
        episodes.append(
            from_arrays(
                name,
                d,
                b["prices"],
                b["funding_coeff"],
                a["expert_targets"][ix],
                a["expert_eligible"][ix],
                a["past_returns30"][ix],
                f,
                p,
                source,
            )
        )
    folder = r / "gap-repair/repaired/economics"
    d = np.arange(1641081600000000, CUTOFF, DAY_US, dtype=np.int64)
    prices, funding, hashes = [], [], {}
    for symbol in CORE5:
        path = folder / f"{symbol}_daily.parquet"
        hashes[symbol] = sha(path)
        inputs[str(path.relative_to(state))] = hashes[symbol]
        b = pd.read_parquet(path).set_index("dt").loc[pd.to_datetime(d, unit="us", utc=True)]
        assert b.complete_kline.all() and b.funding_interval_complete.iloc[:-1].all()
        prices.append(b.exec_price.to_numpy(float))
        funding.append(b.mark_funding_per_unit.to_numpy(float)[:-1])
    source = digest(
        {"features": sha(feature_path), "targets": sha(target_path), "economics": hashes}
    )
    ix = np.searchsorted(a["decision_us"], d)
    np.testing.assert_array_equal(a["decision_us"][ix], d)
    episodes.append(
        from_arrays(
            "Y2022_TO_APR2024",
            d,
            np.stack(prices, 1),
            np.stack(funding, 1),
            a["expert_targets"][ix],
            a["expert_eligible"][ix],
            a["past_returns30"][ix],
            f,
            p,
            source,
        )
    )
    assert [e.identity for e in episodes] == EXPECTED_EPISODES
    return tuple(episodes), inputs


def dataset(state):
    es, bindings = load_episodes(state)
    label_path = Path(state) / "balanced-history/LABELS.json"
    assert sha(label_path) == EXPECTED_LABEL_SHA
    rows = json.loads(label_path.read_text())
    decision = np.array([r["decision_us"] for r in rows], dtype=np.int64)
    available = np.array([r["label_available_us"] for r in rows], dtype=np.int64)
    roles = role_indices(decision, available)
    indices = []
    for r in rows:
        e = es[r["wallet"]]
        i = int(np.searchsorted(e.windows.decision_us, r["decision_us"]))
        u = np.asarray(r["hindsight_fixed_policy_21day_utility"])
        assert e.windows.decision_us[i] == r["decision_us"] and i + 21 <= len(e.contexts) - 1
        assert r["label_available_us"] == int(e.label_available_us[i + 20])
        assert u.shape == (4,) and np.isfinite(u).all() and r["winner"] == int(u.argmax())
        indices.append((r["wallet"], i))
    assert len(rows) == 1230
    prefix = []
    for wallet, e in enumerate(es):
        ix = np.array([indices[k][1] for k in roles["TRAIN"] if indices[k][0] == wallet])
        if len(ix):
            prefix.append(slice_windows(e.windows, ix))
    scaler = fit_standardizer(prefix, training_cutoff_us=TRAIN_END)
    y = np.array([rows[k]["winner"] for k in roles["TRAIN"]], dtype=np.int64)
    counts = np.bincount(y, minlength=4)
    assert (counts > 0).all()
    weights = len(y) / (4 * counts)
    receipt = {
        "episodes": [e.identity for e in es],
        "inputs": bindings,
        "label_SHA256": EXPECTED_LABEL_SHA,
        "scaler_identity": scaler.identity,
        "scaler_provenance": scaler.provenance,
        "class_counts": counts.tolist(),
        "class_prior": (counts / len(y)).tolist(),
        "class_weights": weights.tolist(),
        "training_mean_utility": np.asarray(
            [rows[k]["hindsight_fixed_policy_21day_utility"] for k in roles["TRAIN"]]
        )
        .mean(0)
        .tolist(),
        "roles": {
            name: {
                "rows": len(ix),
                "indices_SHA256": array_digest(ix),
                "decision_min": int(decision[ix].min()),
                "decision_max": int(decision[ix].max()),
                "availability_max": int(available[ix].max()),
            }
            for name, ix in roles.items()
        },
    }
    return es, rows, indices, roles, weights, scaler, receipt


def arrays_for_role(es, rows, indices, roles, name):
    selected = roles[name]
    arrays = []
    for attribute in ("values", "valid", "step_valid", "expert_state"):
        arrays.append(
            np.stack(
                [
                    (
                        getattr(es[indices[k][0]], attribute)
                        if attribute == "expert_state"
                        else getattr(es[indices[k][0]].windows, attribute)
                    )[indices[k][1]]
                    for k in selected
                ]
            )
        )
    y = np.array([rows[k]["winner"] for k in selected], dtype=np.int64)
    utility = np.asarray([rows[k]["hindsight_fixed_policy_21day_utility"] for k in selected])
    d = np.array([rows[k]["decision_us"] for k in selected], dtype=np.int64)
    return arrays, y, utility, d
