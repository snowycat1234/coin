"""Four bounded synthetic smoke checks for each pinned trade-flow encoder."""

import copy

import pytest
import torch
from torch import nn

from quant.research_fast.adapters.tlob_adapter import MLPLOBEncoder, TLOBEncoder


@pytest.fixture(params=[MLPLOBEncoder, TLOBEncoder], ids=["mlplob", "tlob"])
def encoder(request):
    torch.manual_seed(20261001)
    torch.set_num_threads(2)
    return request.param(device="cpu").eval()


def history(batch=1):
    generator = torch.Generator(device="cpu").manual_seed(20261001)
    return torch.randn(batch, 256, 68, generator=generator, dtype=torch.float32)


def test_shape_constant_features_and_negative_bin_keep_optimizer_parameters(encoder):
    parameters = {id(value) for value in encoder.parameters()}
    optimizer = torch.optim.SGD(encoder.parameters(), lr=0.01)
    norm = encoder.model.norm_layer
    old_y1, old_y2 = norm.y1, norm.y2
    with torch.no_grad():
        norm.y1.fill_(-0.5)
        norm.y2.fill_(-0.5)
    constant = torch.ones(1, 256, 68, dtype=torch.float32)
    encoded = encoder(constant, torch.ones(1, 256, dtype=torch.bool))
    assert encoded.shape == (1, encoder.representation_dim) == (1, 64)
    assert torch.isfinite(encoded).all()
    assert isinstance(encoder.model.final_layers[-1], nn.Identity)
    assert norm.y1 is old_y1 and norm.y2 is old_y2
    assert {id(value) for value in encoder.parameters()} == parameters
    assert {
        id(value) for group in optimizer.param_groups for value in group["params"]
    } == parameters
    assert norm.y1.item() == pytest.approx(0.01) and norm.y2.item() == pytest.approx(0.01)
    encoded.sum().backward()
    assert all(
        value.grad is None or torch.isfinite(value.grad).all() for value in encoder.parameters()
    )
    optimizer.zero_grad(set_to_none=True)


def test_causal_input_boundary_uses_only_supplied_complete_history(encoder):
    tape = torch.cat([history(), torch.zeros(1, 16, 68)], dim=1)
    with torch.no_grad():
        before = encoder(tape[:, :256])
        tape[:, 256:] = 1e9  # No future row is supplied to either encoder.
        after = encoder(tape[:, :256])
    assert torch.equal(before, after)
    with pytest.raises(ValueError, match="historical"):
        encoder(tape)  # The adapter refuses an incorrectly extended endpoint window.
    mask = torch.ones(1, 256, dtype=torch.bool)
    mask[:, -1] = False
    with pytest.raises(ValueError, match="fully observed"):
        encoder(history(), mask)


def test_deterministic_eval_and_state_dict_roundtrip_use_no_external_data(encoder, tmp_path):
    # The caller supplies --basetemp under native STATE; this is synthetic only.
    x = history()
    parameters_before = copy.deepcopy(encoder.state_dict())
    with torch.no_grad():
        first, second = encoder(x), encoder(x)
    assert torch.equal(first, second)
    assert all(
        torch.equal(value, encoder.state_dict()[name]) for name, value in parameters_before.items()
    )
    checkpoint = tmp_path / "explicit-synthetic-model-smoke.pt"
    torch.save(parameters_before, checkpoint)
    encoder.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
    with torch.no_grad():
        assert torch.equal(first, encoder(x))


def test_no_future_normalization_from_other_batch_members_or_eval_statistics(encoder):
    x = history()
    future_sample = history() * 1e4 + 1e6
    state_before = copy.deepcopy(encoder.state_dict())
    with torch.no_grad():
        alone = encoder(x)
        with_future_member = encoder(torch.cat([x, future_sample], dim=0))[:1]
    torch.testing.assert_close(alone, with_future_member, rtol=2e-5, atol=2e-5)
    assert all(
        torch.equal(value, encoder.state_dict()[name]) for name, value in state_before.items()
    )
    assert not any(
        isinstance(module, nn.modules.batchnorm._BatchNorm) for module in encoder.modules()
    )
