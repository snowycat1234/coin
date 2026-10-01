"""Thin endpoint adapter for pytorch-tcn 1.2.3; no local convolution implementation."""

import torch
from pytorch_tcn import TCN
from torch import nn

CHANNELS = {"TCN-S": [64, 64, 96, 96], "TCN-M": [64, 96, 128, 128, 128]}


class TCNEncoder(nn.Module):
    def __init__(self, config_id: str, num_features: int = 68):
        super().__init__()
        self.output_dim = CHANNELS[config_id][-1]
        self.num_features = num_features
        self.backbone = TCN(
            num_inputs=num_features, num_channels=CHANNELS[config_id], kernel_size=3,
            dropout=0.1, causal=True, lookahead=0, use_skip_connections=True,
            input_shape="NLC", use_norm="weight_norm",
        )

    def forward(self, x, mask=None):
        if x.ndim != 3 or x.shape[-1] != self.num_features or x.shape[1] == 0:
            raise ValueError("TCN requires a complete historical [B,T,F] window")
        if mask is not None and (mask.shape != x.shape[:2] or not bool(torch.all(mask))):
            raise ValueError("Common dataset excludes incomplete input windows; no mask imputation")
        return self.backbone(x)[:, -1, :]
