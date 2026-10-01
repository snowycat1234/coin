import numpy as np
import pytest
import torch

from quant.research_fast.adapters.ts2vec_adapter import TS2VecEncoder


def test_official_fit_shape_frozen_representation_and_save_restore(tmp_path):
    encoder = TS2VecEncoder()
    rng = np.random.default_rng(20261001)
    loss = encoder.fit_train_series(rng.normal(size=(1024, 68)).astype(np.float32), iterations=2)
    assert all(np.isfinite(value) for value in loss)
    x = rng.normal(size=(2, 256, 68)).astype(np.float32)
    first = encoder.encode(x)
    assert first.shape == (2, 320) and np.isfinite(first).all()
    assert not any(p.requires_grad for p in encoder.model.net.parameters())
    checkpoint = tmp_path / "ts2vec.pt"
    encoder.model.save(checkpoint)
    restored = TS2VecEncoder()
    restored.model.load(checkpoint)
    np.testing.assert_array_equal(first, restored.encode(x))
    assert encoder.model.device == "cpu" and torch.version.cuda is None


def test_deterministic_eval_and_other_samples_cannot_change_normalization():
    encoder = TS2VecEncoder()
    x = np.ones((1, 256, 68), np.float32)
    a = encoder.encode(x)
    np.testing.assert_array_equal(a, encoder.encode(x))
    joint = encoder.encode(np.concatenate([x, x * 100]))[:1]
    np.testing.assert_allclose(a, joint, rtol=1e-5, atol=1e-6)


def test_complete_past_boundary_and_nonfinite_rejected():
    encoder = TS2VecEncoder()
    for x in (np.ones((1, 257, 68)), np.ones((1, 255, 68)), np.full((1, 256, 68), np.nan)):
        with pytest.raises(ValueError, match="past"):
            encoder.encode(x)
