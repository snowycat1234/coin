"""Thin endpoint encoders for the pinned MIT TLOB / MLPLOB implementations.

Trade-flow architecture transfer: the complete input window is already historical.
Neither upstream attention nor BiN provides a causal representation at every token.
The shared dataset owns window endpoints, labels and past-only external normalization.
"""

from __future__ import annotations

import importlib.util
import sys

import torch
from torch import nn

from quant.paths import ROOT

UPSTREAM_COMMIT = "f1c0af4d81067978914361766db0457a7d8b6a46"
SEQUENCE_LENGTH = 256
NUM_FEATURES = 68
HIDDEN_DIM = 64
NUM_LAYERS = 2
NUM_HEADS = 4


def _upstream():
    """Load the repo-local vendor as a package without changing global sys.path."""
    name = "quant.research_fast.adapters._tlob_upstream"
    if name not in sys.modules:
        directory = ROOT / "third_party/tlob"
        specification = importlib.util.spec_from_file_location(
            name, directory / "__init__.py", submodule_search_locations=[str(directory)],
        )
        if specification is None or specification.loader is None:
            raise ImportError("Pinned TLOB vendor package is unavailable")
        module = importlib.util.module_from_spec(specification)
        sys.modules[name] = module
        try:
            specification.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name, None)
            raise
    return sys.modules[name]


class _EndpointEncoder(nn.Module):
    def __init__(self, kind: str, *, device: str | torch.device = "cpu"):
        super().__init__()
        chosen = torch.device(device)
        if chosen.type != "cpu":
            raise ValueError("FR67 currently accepts explicit CPU only")
        self.device = torch.device("cpu")
        self.kind = kind
        upstream = _upstream()
        arguments = {
            "hidden_dim": HIDDEN_DIM, "num_layers": NUM_LAYERS,
            "seq_size": SEQUENCE_LENGTH, "num_features": NUM_FEATURES,
            # Keep the generic matrix path; there is no LOBSTER order-type column.
            "dataset_type": "TRADE_FLOW",
        }
        if kind == "tlob":
            self.model = upstream.TLOB(**arguments, num_heads=NUM_HEADS,
                                       is_sin_emb=False, device=self.device)
        else:
            self.model = upstream.MLPLOB(**arguments)
        original_head = self.model.final_layers[-1]
        if not isinstance(original_head, nn.Linear) or original_head.out_features != 3:
            raise ValueError("Pinned upstream final-head contract changed")
        self.representation_dim = original_head.in_features
        self.output_dim = self.representation_dim
        self.model.final_layers[-1] = nn.Identity()
        self.model.to(self.device)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        if (x.ndim != 3 or x.shape[0] < 1
                or tuple(x.shape[1:]) != (SEQUENCE_LENGTH, NUM_FEATURES)):
            raise ValueError("Require complete historical [B,256,68] windows")
        if x.device.type != "cpu" or x.dtype != torch.float32:
            raise ValueError("Require explicit CPU float32 inputs")
        if not bool(torch.isfinite(x).all()):
            raise ValueError("Shared dataset must provide finite historical features")
        if mask is not None:
            if (mask.dtype != torch.bool or mask.device != x.device
                    or tuple(mask.shape) != tuple(x.shape[:2]) or not bool(mask.all())):
                raise ValueError("Require fully observed windows; do not silently impute a mask")
        # Upstream normalization/attention sees only this supplied historical window.
        # The common future MultiTaskHead consumes this representation separately.
        return self.model(x)


class MLPLOBEncoder(_EndpointEncoder):
    """Fixed MLPLOB-1 backbone, returning a [B,64] endpoint representation."""

    def __init__(self, *, device: str | torch.device = "cpu"):
        super().__init__("mlplob", device=device)


class TLOBEncoder(_EndpointEncoder):
    """Fixed TLOB-1 with learned position embeddings and a [B,64] representation."""

    def __init__(self, *, device: str | torch.device = "cpu"):
        super().__init__("tlob", device=device)
