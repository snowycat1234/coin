import importlib.util

import numpy as np
import pytest

from quant.paths import ROOT
from quant.research_fast.cached_dataset import CachedSequenceDataset

spec = importlib.util.spec_from_file_location(
    "common_dataset_fixture", ROOT / "tests/test_fast_dataset.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def test_cached_shared_labels_inputs_and_ids_exactly_equal_reference(tmp_path):
    reference, _ = fixture.write_dataset(tmp_path / "source")
    cached = CachedSequenceDataset(reference.shards)
    cached.prepare_index(tmp_path / "cache.i64")
    np.testing.assert_array_equal(reference.index, cached.index)
    for i in (0, len(reference) // 2, len(reference) - 1):
        a, b = reference[i], cached[i]
        for key in ("x", "y", "y_raw"):
            np.testing.assert_array_equal(a.pop(key), b.pop(key))
        assert a == b
    changed = cached[0]
    changed["x"][:] = 123
    assert not np.all(cached[0]["x"] == 123)
    assert cached._cached_day.cache_info().maxsize == 24


def test_normalized_views_share_source_cache_and_train_only_scalers(tmp_path):
    reference, _ = fixture.write_dataset(tmp_path / "source")
    cached = CachedSequenceDataset(reference.shards)
    cached.prepare_index(tmp_path / "cache.i64")
    fold = fixture.mini_fold()
    scaler, targets = reference.fit_fold_scaler(fold), reference.fit_target_scaler(fold)
    a = reference.normalized(scaler, fold, "test", targets=targets)
    b = cached.normalized(scaler, fold, "test", targets=targets)
    assert b._cached_day is cached._cached_day
    for i in cached.split_indices(fold, "test")[:3]:
        np.testing.assert_array_equal(a[int(i)]["x"], b[int(i)]["x"])
        np.testing.assert_array_equal(a[int(i)]["y"], b[int(i)]["y"])


def test_cached_source_mutation_is_still_rejected(tmp_path):
    reference, _ = fixture.write_dataset(tmp_path / "source")
    cached = CachedSequenceDataset(reference.shards)
    cached.prepare_index(tmp_path / "cache.i64")
    cached[0]
    path = cached.shards[0].path
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Cached source file changed"):
        cached[0]
