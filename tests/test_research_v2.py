import copy
import json

import numpy as np
import polars as pl
import pytest

from quant.cli_research_v2 import development_files
from quant.features_v2 import FEATURE_NAMES_V2
from quant.operations import date_us
from quant.paths import ROOT
from quant.research_v2 import (
    _fit_export,
    _manifest,
    _verify_native_predictions,
    load_protocol_v2,
    make_folds_v2,
    register_once,
    shared_terminal_flat,
    training_rows,
    verify_registered_sources,
)


def protocol():
    return load_protocol_v2(ROOT / "configs/experiments/nonlinear_v2.json")


def test_nine_folds_purge_future_labels_including_exact_boundary():
    folds = make_folds_v2(protocol())
    assert len(folds) == 9
    assert folds[0] == {
        "id": 0,
        "train_start": "2022-01-01",
        "test_start": "2024-01-01",
        "test_end": "2024-04-01",
    }
    assert folds[-1]["test_end"] == "2026-03-01"
    assert all(
        left["test_end"] == right["test_start"]
        for left, right in zip(folds, folds[1:], strict=False)
    )
    cutoff = date_us("2024-01-01") - 3_600_000_000
    sample = pl.DataFrame(
        {
            "available_us": [date_us("2023-12-31")] * 3 + [date_us("2021-12-31")],
            "label_end_us": [cutoff - 1, cutoff, cutoff + 1, cutoff - 1],
            "label_valid": [True] * 4,
            "gross_return": [0.01] * 4,
            "symbol": ["BTCUSDT"] * 4,
            **{name: [0.0] * 4 for name in FEATURE_NAMES_V2},
        }
    )
    result = training_rows(sample, folds[0])
    assert len(result) == 1 and result["label_end_us"][0] == cutoff - 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("state_path", "state/another_study.json"),
        ("output_dir", "reports/another_study"),
        ("max_configurations", 7),
        ("gpu", True),
    ],
)
def test_new_registry_or_search_budget_is_rejected(tmp_path, field, value):
    value_protocol = copy.deepcopy(protocol())
    value_protocol[field] = value
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(value_protocol))
    with pytest.raises(ValueError):
        load_protocol_v2(path)


def test_once_registry_refuses_changed_inputs_repeated_fit_and_completed_run(tmp_path):
    path = tmp_path / "registry.json"
    binding = {"protocol": "fixed", "input_frames": {"features": "original"}}
    state = register_once(path, binding)
    assert state["fit_count"] == 0 and state["audit"][0]["event"] == "registered_before_any_fit"
    with pytest.raises(RuntimeError, match="changed"):
        register_once(
            path,
            {**binding, "input_frames": {"features": "changed"}},
            resume_reason="host restarted",
        )
    with pytest.raises(RuntimeError, match="reason"):
        register_once(path, binding)
    state["inflight_fit"] = "LGB_A:fold0"
    path.write_text(json.dumps(state))
    with pytest.raises(RuntimeError, match="Uncommitted fit"):
        register_once(path, binding, resume_reason="host restarted")
    state["inflight_fit"] = None
    state["status"] = "STOP_v2"
    path.write_text(json.dumps(state))
    with pytest.raises(RuntimeError, match="completed"):
        register_once(path, binding, resume_reason="try again")


def test_mid_run_source_change_is_rejected_before_committing_fit(tmp_path, monkeypatch):
    import quant.research_v2 as study

    monkeypatch.setattr(study, "ROOT", tmp_path)
    source = tmp_path / "predictor.py"
    source.write_text("accepted code")
    dependency = tmp_path / "uv.lock"
    dependency.write_text("fixed versions")
    protocol_path = ROOT / "configs/experiments/nonlinear_v2.json"
    binding = {"source_hashes": {"predictor.py": study.sha(source)},
               "dependency_lock_sha256": study.sha(dependency),
               "protocol_sha256": study.fingerprint(protocol())}
    verify_registered_sources(binding, protocol_path)
    source.write_text("edited during training")
    with pytest.raises(RuntimeError, match="source changed"):
        verify_registered_sources(binding, protocol_path)


def test_flat_tail_includes_monthly_buyhold_and_preserves_prior_signals():
    hour = 3_600_000_000
    bars = pl.DataFrame({"symbol": ["BTCUSDT"] * 10, "available_us": np.arange(10) * hour})
    targets = pl.DataFrame({"symbol": ["BTCUSDT"], "available_us": [hour], "target_weight": [0.3]})
    result = shared_terminal_flat(targets, bars, 10 * hour)
    assert result["available_us"].to_list() == [hour, 6 * hour, 7 * hour, 8 * hour, 9 * hour]
    assert result["target_weight"].to_list() == [0.3, 0, 0, 0, 0]


def test_monthly_price_selection_excludes_locked_members_before_open():
    months = [
        f"{year}-{month:02d}"
        for year in range(2022, 2027)
        for month in range(1, 13)
        if f"{year}-{month:02d}" <= "2026-08"
    ]
    lock = {
        "minute_files": {
            f"data/normalized/spot/{symbol}/1m/{month}.parquet": "a" * 64
            for symbol in ("BTCUSDT", "ETHUSDT")
            for month in months
        },
        "bar_files": {
            f"data/bars/spot/{symbol}/1h.parquet": "b" * 64 for symbol in ("BTCUSDT", "ETHUSDT")
        },
    }
    minutes, hours = development_files(lock)
    assert len(minutes) == 100 and len(hours) == 2
    assert all(path.stem < "2026-03" for path in minutes)


@pytest.mark.parametrize("model", ["lightgbm", "xgboost"])
def test_synthetic_40_feature_native_export_matches_runtime_float64_inputs(model):
    # Engineering fixture only: two trees on synthetic values, no market data.
    rng = np.random.default_rng(201)
    matrix = rng.normal(size=(80, 40))
    sample = pl.DataFrame(
        {
            **{name: matrix[:, index] for index, name in enumerate(FEATURE_NAMES_V2)},
            "gross_return": matrix[:, 0] * 0.01 + matrix[:, 1] * 0.003,
            "symbol": ["BTCUSDT"] * 80,
            "available_us": date_us("2022-01-01") + np.arange(80) * 3_600_000_000,
            "label_end_us": date_us("2022-01-01") + (np.arange(80) + 4) * 3_600_000_000,
        }
    )
    config = copy.deepcopy(
        next(item for item in protocol()["configurations"] if item["model_type"] == model)
    )
    config["rounds"] = 2
    if model == "lightgbm":
        config["params"]["min_data_in_leaf"] = 5
    else:
        config["params"]["min_child_weight"] = 5
    blob, predicted = _fit_export(config, sample, sample.head(20))
    manifest = _manifest(blob, config, sample, "2024-01-01")
    assert _verify_native_predictions(blob, manifest, sample.head(20), predicted) <= 1e-10
