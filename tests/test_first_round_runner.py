"""The shared TS2Vec worker must publish two resumable config receipts."""

import importlib.util
import json
from types import SimpleNamespace

import numpy as np
import pytest

from quant.paths import ROOT
from quant.research_fast.dataset import _sha, file_sha


def runner():
    specification = importlib.util.spec_from_file_location(
        "fr_first_round_test", ROOT / "scripts/fr_run_first_round.py"
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_shared_representation_two_outputs_resume_and_tamper_rejection(tmp_path):
    module = runner()
    run = tmp_path / "owned-run"
    fold = SimpleNamespace(name="shared-fold")
    binding = {"dataset_sha256": "c" * 64, "fixed_protocol": "no_search"}
    indices = np.arange(3)
    decisions = np.arange(3) * 60_000_000 + 1_000_000_000
    ids = tuple(_sha((binding["dataset_sha256"], int(t))) for t in decisions)
    dataset = SimpleNamespace(index=decisions, split_indices=lambda *_: indices)
    shared = run / fold.name / "TS2VEC-SHARED"
    shared.mkdir(parents=True)
    checkpoint = shared / "trusted-synthetic-checkpoint.pt"
    checkpoint.write_bytes(b"handmade-no-real-model-fixture")
    outputs = []
    jobs = {}
    for name, value in (("TS2VEC-LINEAR-1", 0.1), ("TS2VEC-LGB-1", 0.2)):
        output = run / fold.name / name / "attempt"
        output.mkdir(parents=True)
        predicted = np.full((3, 2, 4), value, dtype=np.float32)
        np.save(output / "predictions.npy", predicted, allow_pickle=False)
        np.save(output / "indices.npy", indices, allow_pickle=False)
        metadata = {
            "dataset_sha256": binding["dataset_sha256"],
            "prediction_sha256": __import__("hashlib")
            .sha256(predicted.astype(np.float64).tobytes())
            .hexdigest(),
        }
        evidence = SimpleNamespace(receipt=lambda m=metadata: {"metadata": m})
        jobs[name] = module.complete_job(
            run, fold, name, binding, output, evidence, ids, [checkpoint], publish_completion=False
        )
        outputs.append((name, output))
    group_path = shared / "attempt-one"
    group_path.mkdir()
    module.publish(
        group_path / "GROUP_COMPLETE.json", {"binding_sha256": _sha(binding), "jobs": jobs}
    )
    # Simulate process termination after only the first receipt was committed.
    module.publish(run / fold.name / outputs[0][0] / "COMPLETE.json", jobs[outputs[0][0]])
    module.recover_shared_pair(run, fold, binding, dataset)
    for name, _ in outputs:
        receipt = module.verified(run, fold, name, binding, dataset)
        assert receipt["config"] == name
        assert receipt["artifacts"][str(checkpoint.relative_to(run))] == file_sha(checkpoint)
    first = run / fold.name / outputs[0][0] / "COMPLETE.json"
    altered = json.loads(first.read_text())
    altered["evaluation"]["metadata"]["dataset_sha256"] = "d" * 64
    first.write_text(json.dumps(altered))
    with pytest.raises(ValueError, match="evaluation dataset changed"):
        module.verified(run, fold, outputs[0][0], binding, dataset)
    assert module.verified(run, fold, outputs[1][0], binding, dataset)["config"] == outputs[1][0]
    checkpoint.write_bytes(b"changed-under-both-probes")
    with pytest.raises(ValueError, match="artifact changed"):
        module.verified(run, fold, outputs[1][0], binding, dataset)


def test_insufficient_history_rejects_before_any_fit(monkeypatch, tmp_path):
    module = runner()

    def must_not_open_or_fit(*_):
        raise AssertionError("Missing history must reject before any source open or fit")

    monkeypatch.setitem(
        __import__("sys").modules,
        "hf_fetch_history",
        SimpleNamespace(
            STORE=tmp_path / "absent-development-history", resume_day=must_not_open_or_fit
        ),
    )
    with pytest.raises(ValueError, match="INSUFFICIENT_180D: 720/720 missing; model_fits=0"):
        module.preflight()
