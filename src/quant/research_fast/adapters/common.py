"""The shared endpoint prediction head for every upstream sequence encoder."""

from torch import nn


class MultiTaskHead(nn.Module):
    """Two Spot symbols, each [flow5m, return5m proxy, flow30s, logRV5m]."""

    def __init__(self, representation_dim: int):
        super().__init__()
        self.layers = nn.Sequential(nn.Linear(representation_dim, 64), nn.GELU(), nn.Linear(64, 8))

    def forward(self, representation):
        return self.layers(representation).reshape(-1, 2, 4)


class SequenceModel(nn.Module):
    def __init__(self, encoder):
        super().__init__()
        self.encoder = encoder
        self.head = MultiTaskHead(encoder.output_dim)

    def forward(self, x, mask=None):
        return self.head(self.encoder(x, mask=mask))
