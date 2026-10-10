"""Independent choice/account/request checks; zero fitting or wallet replay."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(root, folder, output):
    if output.exists():
        raise FileExistsError("Exclusive verification receipt required")
    selection_file = folder / "FROZEN_SELECTIONS.json"
    selection = json.loads(selection_file.read_text())
    result = json.loads((folder / "RESULT.json").read_text())
    original = root / "research/temporal-contrast21-probe-20261010"
    with np.load(original / "INPUTS.npz", allow_pickle=False) as z:
        d, av, w, ready = (
            z["train_decisions"],
            z["train_label_available"],
            z["train_wallet_id"],
            z["train_ready"],
        )
    with np.load(original / "TRAIN_STANDALONE_PATHS.npz", allow_pickle=False) as z:
        absolute = np.empty((len(d), 3))
        for wallet in range(5):
            ix = np.flatnonzero(w == wallet)
            n = len(z[f"wallet{wallet}_decisions"])
            starts = np.arange(n - 21)
            np.testing.assert_array_equal(d[ix], z[f"wallet{wallet}_decisions"][starts])
            for j, name in enumerate(["VOL", "CS", "SHORT"]):
                nav = z[f"wallet{wallet}_{name}_nav"]
                absolute[ix, j] = nav[starts + 21] / nav[starts] - 1
    rows = []
    for record, choice in zip(result["folds"], selection["folds"], strict=True):
        cutoff = choice["first_forward_decision_us"]
        ix = np.flatnonzero(ready & (d < cutoff) & (av < cutoff))
        means = absolute[ix].mean(0)
        names = ["VOL_MANAGED_HOLD", "CSMOM21", "MOMENTUM30_SHORT_ONLY"]
        for j, name in enumerate(names):
            assert means[j] == choice["prefix_means"][name]
        assert choice["selected_expert"] == names[int(np.argmax(means))]
        assert (
            len(ix) == choice["mature_labels"]
            and int(av[ix].max()) == choice["latest_label_available_us"] < cutoff
        )
        assert record["choice"] == choice
        bundle = folder / ("FOLD_" + choice["fold"].replace("-", ""))
        manifest = json.loads((bundle / "MANIFEST.json").read_text())
        assert manifest["selection_SHA256"] == sha(selection_file)
        assert manifest["native_rollout_status"] == "NOT_RUN_AWAIT_NATIVE_DECISION"
        for name, entry in manifest["files"].items():
            assert sha(bundle / name) == entry["SHA256"]
        for name, digest in manifest["versioned_sources"].items():
            assert sha(root / name) == digest
        for name, digest in manifest["input_source_files"].items():
            assert sha(root / name) == digest
        with np.load(bundle / "REQUESTS.npz", allow_pickle=False) as z:
            assert set(z.files) == {
                "decision_us",
                "symbol_order",
                "expert_order",
                "desired_expert_budget",
                "action_eligible",
                "feature_available_us",
                "request_available_us",
            }
            clock, request = z["decision_us"], z["desired_expert_budget"]
            expected = np.zeros((63, 6))
            expected[:, choice["E6_slot"]] = 1
            np.testing.assert_array_equal(request, expected)
            assert not request[:, 0].any() and np.all(z["feature_available_us"] <= clock)
            np.testing.assert_array_equal(z["request_available_us"], clock)
            context_name = manifest["forward_context_file"]
            with np.load(root / context_name, allow_pickle=False) as source:
                np.testing.assert_array_equal(z["action_eligible"], source["expert_eligible"])
                np.testing.assert_array_equal(clock, source["decision_us"])
                np.testing.assert_array_equal(z["symbol_order"], source["symbol_order"])
                np.testing.assert_array_equal(z["expert_order"], source["expert_order"])
        with np.load(bundle / "SURROGATE_PATH.npz", allow_pickle=False) as z:
            nav, targets, budget = z["nav"], z["targets"], z["mapped_expert_budget"]
            assert nav.shape == (64,) and nav[0] == 10000 and not targets[-1].any()
            assert np.max(np.abs(targets)) <= 0.3 + 1e-12
            assert np.max(np.abs(targets).sum(1)) <= 0.6 + 1e-12
            np.testing.assert_allclose(
                budget[:20, choice["E6_slot"]], np.arange(1, 21) / 20, atol=1e-14, rtol=0
            )
            np.testing.assert_allclose(budget[20:, choice["E6_slot"]], 1, atol=1e-14, rtol=0)
            assert (
                np.max(np.abs(np.diff(np.vstack([np.eye(6)[0], budget]), axis=0)).sum(1))
                <= 0.1 + 1e-12
            )
            assert record["net_PnL"] == float(nav[-1] - 10000)
            assert record["maximum_drawdown"] == float(np.max(1 - nav / np.maximum.accumulate(nav)))
        selected = {"PnL": record["net_PnL"], "MDD": record["maximum_drawdown"]}
        comparisons = {
            n: {"PnL": r["net_PnL"], "MDD": r["maximum_drawdown"]}
            for n, r in record["comparisons"].items()
        }
        for name, ref in record["comparisons"].items():
            assert record["PnL_excess_vs_controls"][name] == record["net_PnL"] - ref["net_PnL"]
            assert ref["paid_terminal_cash"] and ref["capital"] == 10000
        summary = dict(
            fold=choice["fold"],
            expert=choice["selected_control"],
            prefix_means=choice["prefix_means"],
            selected=selected,
            controls=comparisons,
        )
        rows.append(summary)
        print(json.dumps(summary, sort_keys=True))
    receipt = dict(
        status="FOUR_PREFIX_CHOICES_OWN_PATHS_AND_NATIVE63_REQUEST_BUNDLES_VERIFIED",
        folds=rows,
        request_rows=252,
        new_fits=0,
        new_wallet_replays=0,
        native_rollouts=0,
        threshold_or_weight_alternatives=0,
    )
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--folder", required=True, type=Path)
    p.add_argument("--receipt", required=True, type=Path)
    a = p.parse_args()
    verify(a.root, a.folder, a.receipt)
