"""Add the same zero-initialized input projection to both frozen encoder arms."""

import torch
from torch import nn

from modules.temporal_short_expansion.model import ShortSelector

INPUT_EXPERT_INDICES = (1, 4, 5)
INPUT_NAMES = ("VOL_MANAGED_HOLD", "CSMOM21", "MOMENTUM30_SHORT_ONLY")
TARGET_SCALE = 0.3  # fixed financial fraction unit; no fitted statistic
INPUT_WIDTH = 18


class ExpertSelector(ShortSelector):
    def __init__(self, base, *, input_enabled):
        if type(input_enabled) is not bool:
            raise ValueError("Explicit matched input arm required")
        super().__init__(base, short_enabled=True)
        self.input_enabled = input_enabled
        with torch.random.fork_rng(devices=[]):
            self.expert_projection = nn.Linear(INPUT_WIDTH, 32, bias=False, dtype=torch.float64)
        nn.init.zeros_(self.expert_projection.weight)
        self._expert_state = None
        self.base.joint.register_forward_hook(self._add_expert_state)

    def _add_expert_state(self, module, arguments, output):
        if self._expert_state is None:
            return output
        state = self._expert_state if self.input_enabled else self._expert_state * 0.0
        return output + self.expert_projection(state)

    @property
    def contract(self):
        result = dict(super().contract)
        result.update(
            schema="TEMPORAL_MATCHED_CURRENT_EXPERT_INPUT_V1",
            input_enabled=self.input_enabled,
            additional_features=True,
            current_expert_input=dict(
                names=list(INPUT_NAMES),
                canonical_indices=list(INPUT_EXPERT_INDICES),
                layout="expert_major_signed_targets3x5_then_expert_eligible3",
                target_scale=TARGET_SCALE,
                width=INPUT_WIDTH,
                projection="18to32_biasFalse_zero_init_added_before_joint_tanh",
                eligibility="unavailable_targets_masked_before_scaling;flat_remains_distinct",
                clock="saved_available<=decision;strictly_before_execution;no_backdating",
                control="same_parameters_and_optimizer_ages;block_multiplied_by0",
            ),
            parameter_count=self.parameter_count,
        )
        return result

    def forward(self, values, valid, step_valid, expert_state):
        if (
            expert_state.shape != (len(values), INPUT_WIDTH)
            or expert_state.dtype != self.mean.dtype
            or expert_state.device != self.mean.device
            or not torch.isfinite(expert_state).all()
        ):
            raise ValueError("Finite ordered float64 current expert block required")
        if self._expert_state is not None:
            raise ValueError("Reentrant expert inference rejected")
        self._expert_state = expert_state
        try:
            return super().forward(values, valid, step_valid)
        finally:
            self._expert_state = None
