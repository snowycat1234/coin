import copy
from dataclasses import replace
from datetime import date

import numpy as np
import polars as pl
import pytest
from sklearn.preprocessing import StandardScaler

from quant.research_fast.dataset import (
    BAR_US,
    ENDPOINT_STEP_US,
    FEATURE_COLUMNS,
    LABEL_LAG_US,
    SCALE_INDICES,
    START,
    STREAMS,
    FastSequenceDataset,
    Fold,
    ShardSpec,
    day_us,
    feature_matrix,
    file_sha,
    make_folds,
    protocol,
    tabular_view,
)
from quant.research_fast.labels import label_table

BASE = day_us(START)


def synthetic_frame(stream, count=1000, future_change=None):
    market, symbol = stream.split("_")
    index = np.arange(count)
    opened = BASE + index * BAR_US
    price = 100 + index / 100 + np.sin(index / 13) / 10
    if future_change is not None:
        price[index >= future_change] *= 10
    buy, sell = 100 + index % 7, 80 + index % 11
    values = {
        "version": ["trade_flow_5s_v2"] * count,
        "market": [market] * count,
        "symbol": [symbol] * count,
        "date": [START.isoformat()] * count,
        "timestamp": opened,
        "close_us": opened + BAR_US,
        "available_us": opened + BAR_US,
        "quality": np.zeros(count, dtype=np.uint16),
        "open": price,
        "high": price + 0.1,
        "low": price - 0.1,
        "close": price + 0.02,
        "vwap": price + 0.01,
        "trade_count": np.full(count, 4),
        "buy_count": np.full(count, 2),
        "sell_count": np.full(count, 2),
        "agg_count": np.full(count, 4),
        "base_volume": (buy + sell) / price,
        "quote_notional": buy + sell,
        "aggressive_buy_notional": buy,
        "aggressive_sell_notional": sell,
        "flow_imbalance": (buy - sell) / (buy + sell),
        "mean_trade_size": (buy + sell) / 2,
        "max_trade_size": buy + sell - 20,
        "large_trade_share": np.zeros(count),
        "mean_interarrival": np.full(count, 0.2),
        "std_interarrival": np.full(count, 0.1),
        "interarrival_count": np.full(count, 2),
        "return_5s": np.sin(index / 17) / 1000,
        "signed_price_impact": np.sin(index / 7) / 1000,
        "first_trade_us": opened + 100_000,
        "last_trade_us": opened + 900_000,
        "empty_bin": np.zeros(count, dtype=bool),
    }
    return pl.DataFrame(values)


def write_dataset(folder, *, future_change=None, bad=None):
    assert str(folder.resolve()).startswith("/home/xflops/coin-state/")
    folder.mkdir(parents=True)
    specs = []
    for stream in STREAMS:
        frame = synthetic_frame(stream, future_change=future_change)
        if bad is not None and stream == STREAMS[0]:
            frame = frame.with_columns(bad)
        path = folder / f"{START}-{stream}.parquet"
        frame.write_parquet(path, row_group_size=128)
        market, symbol = stream.split("_")
        specs.append(ShardSpec(path, market, symbol, START, frame.height, file_sha(path)))
    dataset = FastSequenceDataset(specs)
    receipt = dataset.prepare_index(folder / "endpoints.i64")
    return dataset, receipt


@pytest.fixture
def common(tmp_path):
    return write_dataset(tmp_path / "common")


def mini_fold():
    # Deliberately small ENGINEERING-only boundaries to verify timing without a fake 180d run.
    return Fold(
        "engineering_mini", BASE, BASE + 3_000_000_000, BASE + 4_000_000_000, BASE + 5_000_000_000
    )


def test_protocol_budget_shape_six_fixed_folds_and_short_data_gate(common):
    dataset, receipt = common
    contract = protocol()
    assert contract["budget"]["configs_first_round"] == len(contract["configs"]) == 10
    assert contract["budget"]["seed"] == 20261001
    assert contract["samples"]["input_shape"] == [256, 68]
    assert len(FEATURE_COLUMNS) == 68
    assert contract["samples"]["target_shape"] == [2, 4]
    assert contract["loss"]["per_spot_task_weights"] == [1, 1, 0.1, 0.1]
    folds = make_folds()
    assert len(folds) == 6 and [item.name for item in folds] == [
        "rolling_00",
        "rolling_04",
        "rolling_09",
        "rolling_13",
        "rolling_18",
        "rolling_22",
    ]
    assert all(f.test_start_us - f.train_start_us == 14 * 86_400_000_000 for f in folds)
    assert receipt["status"] == "SMOKE_ONLY" and receipt["complete_common_days"] == 0
    with pytest.raises(ValueError, match="180 complete"):
        FastSequenceDataset(dataset.shards, mode="formal")


def test_all_adapters_use_identical_tensor_sample_and_tabular_summary(common):
    dataset, receipt = common
    assert receipt["endpoints"] > 0 and all(dataset.index % ENDPOINT_STEP_US == 0)
    sample = dataset[0]
    assert sample["x"].shape == (256, 68) and sample["y"].shape == (2, 4)
    assert sample["x"].dtype == sample["y"].dtype == np.float32
    assert np.isfinite(sample["x"]).all() and np.isfinite(sample["y"]).all()
    assert sample["label_available_us"] == sample["decision_us"] + LABEL_LAG_US
    assert len(sample["sample_id"]) == 64 and sample["sample_id"] == dataset[0]["sample_id"]
    np.testing.assert_array_equal(sample["x"], dataset[0]["x"])
    summarized = tabular_view(sample["x"])
    assert summarized.shape == (204,)
    np.testing.assert_array_equal(summarized[:68], sample["x"][-1])
    np.testing.assert_array_equal(summarized[68:136], sample["x"].mean(axis=0))


def test_labels_match_direct_future_sums_proxy_times_and_realized_variance(common):
    dataset, _ = common
    sample = dataset[0]
    decision = sample["decision_us"]
    joint = dataset.joint_rows(decision - 256 * BAR_US, decision + LABEL_LAG_US)
    future = joint.slice(256, 60)
    stream = "spot_BTCUSDT"
    buy, sell = (
        future[f"{stream}__aggressive_buy_notional"].sum(),
        future[f"{stream}__aggressive_sell_notional"].sum(),
    )
    assert sample["y"][0, 0] == pytest.approx((buy - sell) / (buy + sell + 1e-12))
    entry, exit_price = joint[f"{stream}__open"][257], joint[f"{stream}__open"][317]
    assert sample["y"][0, 1] == pytest.approx(exit_price / entry - 1)
    assert sample["qa"][f"{stream}__entry_trade_us"] == decision + BAR_US + 100_000
    assert sample["qa"][f"{stream}__exit_trade_us"] == decision + 305_000_000 + 100_000
    rv = future[f"{stream}__return_5s"].pow(2).sum()
    assert sample["y"][0, 3] == pytest.approx(np.log(rv + 1e-12))
    assert f"{stream}__flow_5m_raw_net_notional" in sample["qa"]
    altered = joint.with_columns(
        (pl.col(f"{stream}__first_trade_us") + 3_000_000).alias(f"{stream}__first_trade_us")
    )
    assert not label_table(altered)["label_valid"][255]


def test_current_window_unchanged_by_future_prices_or_future_labels(common, tmp_path):
    dataset, _ = common
    sample = dataset[0]
    endpoint = (sample["decision_us"] - BASE) // BAR_US
    changed, _ = write_dataset(tmp_path / "changed", future_change=endpoint)
    altered = changed[np.flatnonzero(changed.index == sample["decision_us"])[0]]
    np.testing.assert_array_equal(sample["x"], altered["x"])
    joint = dataset.joint_rows(
        sample["decision_us"] - 256 * BAR_US, sample["decision_us"] + LABEL_LAG_US
    )
    assert feature_matrix(joint.head(256)).shape == (256, 68)


def test_frozen_sklearn_feature_target_normalization_no_val_test_fit_and_inverse(common):
    dataset, _ = common
    fold = mini_fold()
    normalizer = dataset.fit_fold_scaler(fold)
    targets = dataset.fit_target_scaler(fold)
    assert isinstance(normalizer.scaler, StandardScaler)
    assert normalizer.fit_last_us <= fold.fit_cutoff_us
    assert targets.fit_last_label_available_us <= fold.fit_cutoff_us
    before = copy.deepcopy(normalizer.receipt()), copy.deepcopy(targets.receipt())
    view = dataset.normalized(normalizer, fold, "train", targets=targets)
    index = int(dataset.split_indices(fold, "train")[0])
    sample = view[index]
    assert sample["target_units"] == "standardized"
    np.testing.assert_allclose(
        targets.inverse_transform(sample["y"]), sample["y_raw"], rtol=1e-5, atol=1e-6
    )
    raw = dataset[index]["x"]
    mask_columns = [i for i in range(68) if i not in SCALE_INDICES]
    np.testing.assert_array_equal(sample["x"][:, mask_columns], raw[:, mask_columns])
    assert before == (normalizer.receipt(), targets.receipt())
    with pytest.raises(ValueError, match="Wrong/future"):
        dataset.normalized(
            replace(normalizer, fit_last_us=fold.test_start_us), fold, "test", targets=targets
        )
    with pytest.raises(ValueError, match="bound fold"):
        dataset.normalized(normalizer, fold, "test", targets=targets)[index]


def test_maturity_embargo_mask_and_missing_quality_boundaries(common, tmp_path):
    dataset, _ = common
    fold = mini_fold()
    for split in ("train", "validation", "test"):
        indices = dataset.split_indices(fold, split)
        start, end, mature_by = fold.interval(split)
        assert all(dataset.index[indices] >= start) and all(dataset.index[indices] < end)
        assert all(dataset.index[indices] + LABEL_LAG_US <= mature_by)
    bad = pl.when(pl.col("timestamp") == BASE + 20 * BAR_US).then(1).otherwise(0).alias("quality")
    with pytest.raises(ValueError, match="invalid"):
        write_dataset(tmp_path / "badquality", bad=bad)
    with pytest.raises(ValueError, match="all four"):
        FastSequenceDataset(dataset.shards[:-1])
    with pytest.raises(ValueError, match="locked"):
        dataset.joint_rows(day_us(date(2026, 3, 1)), day_us(date(2026, 3, 2)))


def test_sealed_date_rejected_before_open_and_source_hash_mutation(common, monkeypatch):
    dataset, _ = common

    def forbidden_open(*args, **kwargs):
        raise AssertionError("Locked source was opened")

    with monkeypatch.context() as context:
        context.setattr("quant.research_fast.dataset.file_sha", forbidden_open)
        with pytest.raises(ValueError, match="outside"):
            FastSequenceDataset([replace(dataset.shards[0], day=date(2026, 3, 1))])
    with pytest.raises(ValueError, match="SHA mismatch"):
        FastSequenceDataset([replace(item, sha256="0" * 64) for item in dataset.shards])
    manifest = dataset.shards[0].path.parent / "2026-03-01.manifest.json"
    with pytest.raises(ValueError, match="Manifest date"):
        ShardSpec.from_manifest(manifest)


def test_real_torch_dataset_loader_shape_cpu_only_shared_labels(common):
    torch = pytest.importorskip("torch")
    from torch.utils.data import DataLoader

    dataset, _ = common
    loader = DataLoader(dataset.as_torch_dataset(), batch_size=2, num_workers=0, shuffle=False)
    batch = next(iter(loader))
    assert batch["x"].shape == (2, 256, 68) and batch["y"].shape == (2, 2, 4)
    assert batch["x"].device.type == "cpu" and not batch["x"].requires_grad
    assert torch.equal(batch["y"][0], torch.from_numpy(dataset[0]["y"]))
    assert batch["sample_id"][0] == dataset[0]["sample_id"]
