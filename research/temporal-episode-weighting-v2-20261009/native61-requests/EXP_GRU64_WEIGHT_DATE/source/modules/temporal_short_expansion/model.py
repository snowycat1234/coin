"""Reuse the exact temporal encoder; add one matched 33-parameter readout."""

import math

import torch
from torch import nn

from modules.temporal_two_expert.model import E5_EXPERT_ORDER

SHORT = "MOMENTUM30_SHORT_ONLY"
E6 = E5_EXPERT_ORDER + (SHORT,)


class ShortSelector(nn.Module):
    def __init__(self, base, *, short_enabled):
        super().__init__()
        if base.family != "GRU64" or not base.cash_enabled or type(short_enabled) is not bool:
            raise ValueError("Matched GRU64 WITH_CASH parent and explicit short arm required")
        self.base, self.short_enabled = base, short_enabled
        # The extra readout consumes no caller RNG; both arms have identical
        # new parameters and initialization. No encoder or dropout is copied.
        with torch.random.fork_rng(devices=[]):
            self.r_head = nn.Linear(32, 1, dtype=torch.float64)
        nn.init.zeros_(self.r_head.weight)
        nn.init.constant_(self.r_head.bias, math.log(0.01 / 0.99))
        self._joint = None
        self._capturing = False
        self.base.w_head.register_forward_pre_hook(self._capture_joint)

    def _capture_joint(self, module, arguments):
        if self._capturing:
            self._joint = arguments[0]

    @property
    def mean(self):
        return self.base.mean

    @property
    def parameter_count(self):
        return sum(p.numel() for p in self.parameters())

    @property
    def contract(self):
        return dict(
            schema="TEMPORAL_MATCHED_APPEND_SHORT_V1",
            base_contract=self.base.contract,
            short_enabled=self.short_enabled,
            request_expert_order=list(E6),
            allowed_actions=["CASH", E6[1], E6[4]] + ([SHORT] if self.short_enabled else []),
            initialization="same_v2_parent;new_r_weight0_bias_logit(.01);control_r_multiplied_by0",
            outputs="CASH=1-s;VOL=s(1-r)(1-w);CS=s(1-r)w;SHORT=sr;slots2/3=0",
            parameter_count=self.parameter_count,
            model_observed_wallet=False,
            additional_features=False,
        )

    def forward(self, values, valid, step_valid):
        self._capturing = True
        try:
            pair = self.base(values, valid, step_valid)
            r = torch.sigmoid(self.r_head(self._joint)).squeeze(-1)
            if not self.short_enabled:
                r = r * 0.0  # matched optimizer births/ages, exactly zero new action
            s = pair[:, 1] + pair[:, 4]
            zero = pair[:, 2]
            return torch.stack(
                (pair[:, 0], pair[:, 1] * (1 - r), zero, zero, pair[:, 4] * (1 - r), s * r),
                dim=-1,
            )
        finally:
            # Retain no old feature graph or transient serialization state.
            self._joint = None
            self._capturing = False
