"""Change only the fresh conditional SHORT prior, leaving architecture intact."""

import math
import random

import numpy as np
import torch

from modules.temporal_prequential_transfer.model import FreshExpertSelector
from modules.temporal_two_expert.checkpoint import make_optimizer
from modules.temporal_two_expert.model import SEED, Selector


class NeutralShortSelector(FreshExpertSelector):
    @property
    def contract(self):
        result = dict(super().contract)
        result["initialization"] = (
            "fresh_seeded_encoder_joint;w_s_zero;short_logit(1/3);projection_zero;no_parent"
        )
        result["initial_conditional_short_probability"] = 1.0 / 3.0
        return result


def initialize(scaler):
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    base = Selector(
        scaler, family="GRU64", cash_enabled=True, dropout=0.1, seed=SEED, zero_readout=True
    )
    model = NeutralShortSelector(base, input_enabled=True)
    torch.nn.init.constant_(model.r_head.bias, math.log(0.5))
    optimizer = make_optimizer(model)
    assert model.parameter_count == 13699 and not optimizer.state
    return model, optimizer
