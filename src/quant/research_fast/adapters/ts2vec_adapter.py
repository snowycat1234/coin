"""The pinned official TS2Vec encoder; shared dataset owns preprocessing and labels."""

import importlib.util
import sys

import numpy as np
import torch

from quant.paths import ROOT

COMMIT = "b0088e14a99706c05451316dc6db8d3da9351163"
PRETRAIN_ITERATIONS = 600


def upstream():
    name = "quant.research_fast.adapters._ts2vec_upstream"
    if name not in sys.modules:
        directory = ROOT / "third_party/ts2vec"
        spec = importlib.util.spec_from_file_location(
            name, directory / "__init__.py", submodule_search_locations=[str(directory)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name, None)
            raise
    return sys.modules[name]


class TS2VecEncoder:
    """Official architecture defaults; two probes share one frozen encoder per fold."""

    output_dim = 320

    def __init__(self, seed=20261001):
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.set_num_threads(2)
        self.model = upstream().TS2Vec(input_dims=68, device="cpu", max_train_length=256)

    def fit_train_series(self, unique_normalized_train_rows, *, iterations=PRETRAIN_ITERATIONS):
        values = np.asarray(unique_normalized_train_rows, dtype=np.float32)
        if (
            values.ndim != 2
            or values.shape[1] != 68
            or len(values) < 256
            or not np.isfinite(values).all()
        ):
            raise ValueError("Unique finite shared fitting-period rows required")
        # Upstream performs its own bounded segmentation/cropping/contrastive loss.
        # This is a single chronological row series, not all overlapping windows.
        loss = self.model.fit(values[None], n_iters=iterations)
        self.model.net.eval()
        for parameter in self.model.net.parameters():
            parameter.requires_grad_(False)
        return loss

    def encode(self, windows):
        values = np.asarray(windows, dtype=np.float32)
        if values.ndim != 3 or values.shape[1:] != (256, 68) or not np.isfinite(values).all():
            raise ValueError("Exactly the shared complete past [B,256,68] windows required")
        # A bidirectional encoder may read every token in this supplied past window.
        # There are no tokens after the decision. No token-level causal claim.
        result = self.model.encode(values, encoding_window="full_series", mask="all_true")
        if result.shape != (len(values), self.output_dim) or not np.isfinite(result).all():
            raise ValueError("Invalid official TS2Vec representation")
        return result
