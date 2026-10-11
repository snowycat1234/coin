"""Closed-form diagnostics only; do not execute a training optimizer."""

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from . import diagnose_training
from .core import DAY_US, SYMBOLS
from .diagnose_training import adam_update_estimate, batch_diagnostics
from .run import utc_us


def test_saved_adam_moments_reconstruct_first_step_without_optimizer():
    gradient = np.array([0.2, -0.3, 0])
    actual = adam_update_estimate(0.1 * gradient, 0.001 * gradient**2, 1, 0.001, (0.9, 0.999), 1e-8)
    np.testing.assert_allclose(actual, -0.001 * gradient / (np.abs(gradient) + 1e-8))
    with pytest.raises(ValueError, match="moments"):
        adam_update_estimate([0], [-1], 1024, 0.001, (0.9, 0.999), 1e-8)


def test_batch_duplicate_overlap_is_descriptive_not_independent_sample_size():
    rows = np.array([[0, 0]])
    result = batch_diagnostics(rows, 2001)
    assert result["unique_endpoints_visited"] == 1
    assert result["mean_within_batch_duplicate_fraction"] == 127 / 128
    assert result["mean_pair_same_asset_overlapping_63day_input_fraction"] == 1
    assert result["statistical_effective_sample_size"].startswith("UNKNOWN")


@pytest.mark.parametrize("tz", [None, timezone.utc])
def test_training_query_excludes_future_rows_before_feature_processing(tmp_path, monkeypatch, tz):
    archive = tmp_path / "synthetic.zip"
    members = {}
    with zipfile.ZipFile(archive, "w") as z:
        for symbol in SYMBOLS:
            table = pa.table(
                {
                    "dt": [
                        datetime(2020, 1, 1, tzinfo=tz),
                        datetime(2022, 12, 30, tzinfo=tz),
                        datetime(2023, 1, 1, tzinfo=tz),
                    ],
                    "close": [100.0, 200.0, 9e99],
                    "complete_kline": [True, True, True],
                    "symbol": [symbol] * 3,
                }
            )
            buffer = io.BytesIO()
            pq.write_table(table, buffer)
            raw = buffer.getvalue()
            name = f"source_tables_not_model_inputs/daily_features/{symbol}.parquet"
            members[name] = {"SHA256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
            z.writestr(name, raw)
        z.writestr("MEMBERS.json", json.dumps({"files": members}))
    monkeypatch.setattr(
        diagnose_training, "ARCHIVE_SHA", hashlib.sha256(archive.read_bytes()).hexdigest()
    )
    available, close = diagnose_training.read_training_close(archive)
    assert available[-1] == utc_us("2022-12-31")
    assert np.all(available < utc_us("2023-01-01"))
    np.testing.assert_array_equal(close[0], np.full(5, 100))
    np.testing.assert_array_equal(close[-1], np.full(5, 200))
    assert not (close == 9e99).any() and np.all(np.diff(available) == DAY_US)
