import json

import numpy as np
import torch

from modules.temporal_cached_july.data import inputs as july_inputs
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_two_expert.inputs import fit_standardizer

from .data import inputs
from .eval_inputs import q4_inputs
from .protocol import ROOT, protocol

STATE = ROOT.parent / "coin_single_state"


def test_exact_training_data_and_only_normalization_change():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    train, _, data, scaler = inputs(STATE, STATE / "early2021")
    assert [len(e.contexts) for e in train] == [365, 54, 88, 62, 144, 430]
    assert sum(len(e.contexts) - 1 for e in train) == 1137
    assert scaler.provenance["real_row_count"] == 1273
    assert all(np.max(e.windows.completed_us) < 1714521600000000 for e in train)
    model, opt = initialize(scaler)
    old = json.loads(
        (ROOT / "research/temporal-expanded-refit-q4-20261010/prefit-safe/READY.json").read_text()
    )
    assert parameter_identity(model) == old["initial_parameter_identity"] and not opt.state
    assert model.parameter_count == 13699
    reference = fit_standardizer([e.windows for e in train], training_cutoff_us=1714521600000000)
    assert scaler.identity == reference.identity
    assert protocol()["planned_fits"] == 1 and protocol()["updates"] == 256


def test_cached_periods_keep_distinct_terminal_abis():
    july = july_inputs(STATE)[0]
    q4 = q4_inputs(STATE)[0]
    assert july.prices.shape == (64, 5) and july.funding_coeff.shape == (63, 5)
    assert q4.prices.shape == (92, 5) and q4.funding_coeff.shape == (91, 5)
    assert len(july.windows.decision_us) == 63 and len(q4.windows.decision_us) == 92
