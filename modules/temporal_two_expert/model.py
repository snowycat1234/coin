"""One fixed temporal-vs-latest architecture comparison, paired CASH arms."""

from __future__ import annotations

import torch
from torch import nn

from .inputs import CORE5, FEATURE_NAMES, LOOKBACK, MARKET_CONTEXT, Standardizer

SEED = 20261009
FAMILIES = ("GRU64", "LATEST_MLP")
E5_EXPERT_ORDER = (
    "CASH",
    "VOL_MANAGED_HOLD",
    "PUBLIC_SMA50_200_SIGNED",
    "DONCHIAN_EXIT10",
    "CSMOM21",
)
DEFAULT_FIXED_EXPERT_SET = ("VOL_MANAGED_HOLD", "CSMOM21")
# Pool expansion requires a verified, frozen named set. Only this existing pair
# is registered now; the head/serialization interface can retain explicit names.
VERIFIED_FIXED_EXPERT_SETS = {frozenset(DEFAULT_FIXED_EXPERT_SET)}


class Selector(nn.Module):
    def __init__(
        self,
        standardizer: Standardizer,
        *,
        family="GRU64",
        cash_enabled=False,
        dropout=0.1,
        seed=SEED,
        fixed_expert_set=DEFAULT_FIXED_EXPERT_SET,
    ):
        super().__init__()
        if family not in FAMILIES or type(cash_enabled) is not bool or not 0 <= dropout < 1:
            raise ValueError("Fixed selector family, boolean CASH arm and valid dropout required")
        self.family, self.cash_enabled = family, cash_enabled
        pool = tuple(fixed_expert_set)
        if (
            len(pool) < 2
            or len(set(pool)) != len(pool)
            or any(e not in E5_EXPERT_ORDER or e == "CASH" for e in pool)
            or frozenset(pool) not in VERIFIED_FIXED_EXPERT_SETS
        ):
            raise ValueError(
                "A verified frozen named expert set is required; no unverified actions"
            )
        self.fixed_expert_set = pool
        self.dropout_probability, self.seed = float(dropout), int(seed)
        self.normalization_provenance = standardizer.provenance
        self.standardizer_identity = standardizer.identity
        self.register_buffer("mean", torch.tensor(standardizer.mean.copy(), dtype=torch.float64))
        self.register_buffer("scale", torch.tensor(standardizer.scale.copy(), dtype=torch.float64))
        self.register_buffer("normalization_count", torch.tensor(standardizer.count.copy()))
        # Constructors do not alter caller RNG. Matching final layers use the
        # same seed independently of encoder parameter count or CASH head size.
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(self.seed)
            if family == "GRU64":
                self.encoder = nn.GRU(48, 32, batch_first=True)
            else:
                self.encoder = nn.Sequential(
                    nn.Linear(48, 96), nn.Tanh(), nn.Dropout(dropout), nn.Linear(96, 32), nn.Tanh()
                )
            torch.manual_seed(self.seed + 1)
            self.joint = nn.Linear(160, 32)
            torch.manual_seed(self.seed + 2)
            self.w_head = nn.Linear(32, len(pool) - 1)
            self.s_head = nn.Linear(32, 1) if cash_enabled else None
        self.state_dropout = nn.Dropout(dropout)
        self.joint_dropout = nn.Dropout(dropout)
        self.double()  # exact mapper simplex tolerance is 1e-12

    @property
    def parameter_count(self):
        return sum(p.numel() for p in self.parameters())

    @property
    def contract(self):
        return dict(
            schema="TEMPORAL_TWO_EXPERT_V1",
            family=self.family,
            cash_enabled=self.cash_enabled,
            dropout=self.dropout_probability,
            seed=self.seed,
            symbols=list(CORE5),
            features=list(FEATURE_NAMES),
            aggregate_market_context=list(MARKET_CONTEXT),
            fixed_expert_set=list(self.fixed_expert_set),
            request_expert_order=list(E5_EXPERT_ORDER),
            lookback=LOOKBACK,
            input="24_scaled_values_plus24_validity_masks_per_asset_per_completed_day",
            outputs=("CASH=1-s;named_non_cash_reference_logits;NO_CASH_s=1"),
            other_E5_outputs="exact_zero",
            hidden=32,
            dtype="float64",
            wallet_observed=False,
            parameter_count=self.parameter_count,
            standardizer_identity=self.standardizer_identity,
            normalization_provenance=self.normalization_provenance,
        )

    def forward(self, values, valid, step_valid):
        if (
            values.ndim != 4
            or tuple(values.shape[1:]) != (LOOKBACK, 5, 24)
            or valid.shape != values.shape
            or valid.dtype != torch.bool
            or step_valid.shape != values.shape[:-1]
            or step_valid.dtype != torch.bool
            or values.dtype != self.mean.dtype
            or values.device != self.mean.device
            or valid.device != values.device
            or step_valid.device != values.device
        ):
            raise ValueError(
                "Matched float64 CORE5/64/24 values and boolean feature/time masks required"
            )
        if torch.any(valid & ~step_valid.unsqueeze(-1)) or not torch.isfinite(values[valid]).all():
            raise ValueError("Every observed feature must be finite and time-valid")
        # Mask BEFORE arithmetic, so invalid NaN/Inf slots never enter gradients.
        clean = torch.where(valid, values, self.mean)
        scaled = (clean - self.mean) / self.scale
        z = torch.cat((scaled, valid.to(values.dtype)), dim=-1)
        if self.family == "GRU64":
            z = z.permute(0, 2, 1, 3).reshape(-1, LOOKBACK, 48)
            observed = step_valid.permute(0, 2, 1).reshape(-1, LOOKBACK)
            if bool(observed.all()):
                _, h = self.encoder(z)
                state = h[0]
            else:
                # A missing calendar row carries state; it is never treated as
                # a synthetic observed zero price or removed from the calendar.
                h = z.new_zeros((1, len(z), 32))
                for t in range(LOOKBACK):
                    _, proposed = self.encoder(z[:, t : t + 1], h)
                    h = torch.where(observed[:, t][None, :, None], proposed, h)
                state = h[0]
            state = state.reshape(-1, 5, 32)
        else:
            state = self.encoder(z[:, -1])
        state = torch.where(step_valid[:, -1, :, None], state, 0.0)
        joint = self.joint_dropout(torch.tanh(self.joint(self.state_dropout(state).flatten(1))))
        logits = self.w_head(joint)
        s = (
            torch.sigmoid(self.s_head(joint)).squeeze(-1)
            if self.cash_enabled
            else torch.ones_like(logits[:, 0])
        )
        if len(self.fixed_expert_set) == 2:
            # Preserve the original sigmoid pair exactly for the current pool.
            w = torch.sigmoid(logits).squeeze(-1)
            weights = torch.stack((1.0 - w, w), dim=-1)
        else:
            # A later evidenced set can register additional names without a
            # hindsight classifier or changes to the E5 request mapper.
            reference = torch.zeros_like(logits[:, :1])
            weights = torch.cat((reference, logits), dim=-1).softmax(-1)
        named = {name: s * weights[:, i] for i, name in enumerate(self.fixed_expert_set)}
        named["CASH"] = 1.0 - s
        zero = torch.zeros_like(s)
        return torch.stack([named.get(name, zero) for name in E5_EXPERT_ORDER], dim=-1)


def predict_windows(model, windows, *, feature_batch_size=32):
    """Batch independent windows, preserving output order and the autograd graph.

    Training dropout consumes RNG in chunk order. Exact resume requires the
    same feature_batch_size, episode order and Torch environment in run binding.
    This function never chunks or resets the economic wallet.
    """
    if type(feature_batch_size) is not int or feature_batch_size < 1:
        raise ValueError("Positive feature-window batch size required")
    outputs = []
    for start in range(0, len(windows.values), feature_batch_size):
        end = start + feature_batch_size
        tensors = [
            torch.tensor(a[start:end].copy(), device=model.mean.device)
            for a in (windows.values, windows.valid, windows.step_valid)
        ]
        tensors[0] = tensors[0].to(model.mean.dtype)
        outputs.append(model(*tensors))
    return torch.cat(outputs)
