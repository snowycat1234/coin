"""Four external-model smoke obligations, not a reimplementation of upstream tests."""

import pytest
import torch

from quant.research_fast.adapters.common import SequenceModel
from quant.research_fast.adapters.tcn_adapter import TCNEncoder


@pytest.fixture(params=["TCN-S", "TCN-M"])
def encoder(request):
    torch.manual_seed(20261001)
    torch.set_num_threads(2)
    return TCNEncoder(request.param).eval()


def test_shape(encoder):
    x = torch.zeros(2, 256, 68)
    with torch.no_grad():
        assert encoder(x).shape == (2, encoder.output_dim)
        assert SequenceModel(encoder).eval()(x).shape == (2, 2, 4)


def test_causal_input(encoder):
    x = torch.randn(1, 256, 68)
    changed = x.clone()
    changed[:, 128:] = 100
    with torch.no_grad():
        original, altered = encoder.backbone(x), encoder.backbone(changed)
    torch.testing.assert_close(original[:, :128], altered[:, :128], rtol=0, atol=0)


def test_deterministic_eval(encoder):
    x = torch.randn(2, 256, 68)
    with torch.no_grad():
        first, second = encoder(x), encoder(x)
    torch.testing.assert_close(first, second, rtol=0, atol=0)


def test_no_future_normalization(encoder):
    x = torch.ones(2, 256, 68)
    with torch.no_grad():
        solo, joint = encoder(x[:1]), encoder(torch.cat([x[:1], x[1:] * 100]))[:1]
    torch.testing.assert_close(solo, joint, rtol=1e-5, atol=1e-6)
    assert torch.isfinite(solo).all()
    assert not any(isinstance(module, nn_type) for module in encoder.modules()
                   for nn_type in (torch.nn.BatchNorm1d, torch.nn.BatchNorm2d))
