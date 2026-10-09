"""Fresh parameters and truthful metadata; same13699-parameter architecture."""

import random

import numpy as np
import torch

from modules.temporal_expert_input.model import ExpertSelector
from modules.temporal_two_expert.checkpoint import make_optimizer
from modules.temporal_two_expert.inputs import array_digest, digest
from modules.temporal_two_expert.model import SEED, Selector


class FreshExpertSelector(ExpertSelector):
    @property
    def contract(self):
        result = dict(super().contract)
        result["initialization"] = (
            "fresh_seeded_encoder_joint;w_s_zero;short_logit(.01);projection_zero;no_parent"
        )
        result["fresh_initialization"] = True
        return result


def parameter_identity(model):
    return digest({n: array_digest(p.detach().numpy()) for n, p in model.named_parameters()})


def initialize(scaler):
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    base = Selector(
        scaler, family="GRU64", cash_enabled=True, dropout=0.1, seed=SEED, zero_readout=True
    )
    model = FreshExpertSelector(base, input_enabled=True)
    optimizer = make_optimizer(model)
    if model.parameter_count != 13699 or optimizer.state:
        raise ValueError("Fresh13699-parameter model and empty Adam state required")
    return model, optimizer
