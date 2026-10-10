import numpy as np
import torch

from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_prequential_transfer.model import initialize as old_initialize
from modules.temporal_two_expert.checkpoint import _rng_state

from .data import inputs
from .model import initialize
from .protocol import ROOT, protocol


def test_only_short_prior_changes_and_inputs_identical():
    torch.set_num_threads(1)
    train, _, _, scaler = inputs(
        ROOT.parent / "coin_single_state", ROOT.parent / "coin_single_state/early2021"
    )
    assert sum(len(e.contexts) - 1 for e in train) == 1137
    assert scaler.identity == "fe3b4cc5f7f58343efa10afc660924f766b8e1c7198c991af1470d5aeb678b55"
    old, oldopt = old_initialize(scaler)
    oldrng = tree_identity(_rng_state())
    new, opt = initialize(scaler)
    assert tree_identity(_rng_state()) == oldrng
    assert (
        not opt.state and not oldopt.state and new.parameter_count == old.parameter_count == 13699
    )
    changed = [k for k, v in old.state_dict().items() if not torch.equal(v, new.state_dict()[k])]
    assert changed == ["r_head.bias"]
    new.eval()
    with torch.no_grad():
        p = predict_episode(new, train[0], stop=2).numpy()
    np.testing.assert_allclose(
        p, np.broadcast_to([0.5, 1 / 6, 0, 0, 1 / 6, 1 / 6], p.shape), atol=1e-15, rtol=0
    )
    assert protocol()["planned_fits"] == 1 and protocol()["updates"] == 256
    assert "1/3" in new.contract["initialization"]


def test_launchers_import_without_opening_wallets():
    from . import evaluate, verify

    assert callable(evaluate.run) and callable(verify.verify)
