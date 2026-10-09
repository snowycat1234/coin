"""Tiny non-economic throughput check: generated inputs, analytic synthetic VJP."""

import json
import resource
import time
from types import SimpleNamespace

import numpy as np
import torch

from .checkpoint import make_optimizer
from .exact import feature_chunk, replay_request_gradients
from .inputs import Standardizer
from .model import Selector


def main():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    rng = np.random.default_rng(20261009)
    count, batch_size = 128, 32
    values = rng.normal(0.0, 1.0, (count, 64, 5, 24))
    scale = Standardizer(
        np.zeros(24),
        np.ones(24),
        np.ones(24, np.int64),
        dict(role="synthetic_throughput_only_no_scaler_fit"),
    )
    results = []
    for family in ("GRU64", "LATEST_MLP"):
        for masked in (False, True):
            valid = np.ones_like(values, dtype=bool)
            step = np.ones(values.shape[:-1], dtype=bool)
            if masked:
                step[:, 31, 2] = False
                valid[:, 31, 2] = False
            windows = SimpleNamespace(values=values, valid=valid, step_valid=step)
            model = Selector(scale, family=family, cash_enabled=True, zero_readout=True).train()
            optimizer = make_optimizer(model)
            torch.manual_seed(20261012)
            timings = []
            for _update in range(5):
                began = time.monotonic()
                optimizer.zero_grad(set_to_none=True)
                states, chunks = [], []
                with torch.no_grad():
                    for start in range(0, count, batch_size):
                        states.append(torch.get_rng_state().clone())
                        chunks.append(model_forward(model, windows, start, batch_size))
                requests = np.concatenate(chunks)
                target = np.tile([0.1, 0.3, 0.0, 0.0, 0.6], (count, 1))
                gradient = 2 * (requests - target) / requests.size
                replay_request_gradients(
                    model, windows, gradient, states, requests, feature_batch_size=batch_size
                )
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                timings.append(time.monotonic() - began)
            results.append(
                dict(
                    family=family,
                    masked_history=masked,
                    generated_windows=count,
                    feature_batch_size=batch_size,
                    synthetic_updates=5,
                    measured_seconds=timings[1:],
                    median_seconds_per_128=float(np.median(timings[1:])),
                )
            )
    print(
        json.dumps(
            dict(
                schema="NON_ECONOMIC_THROUGHPUT_V1",
                economic_fits=0,
                real_data_normalizer_fits=0,
                native_wallets=0,
                CPU_threads=1,
                peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                results=results,
            ),
            indent=2,
        )
    )


def model_forward(model, windows, start, batch_size):
    from .model import predict_windows

    return (
        predict_windows(
            model, feature_chunk(windows, start, batch_size), feature_batch_size=batch_size
        )
        .cpu()
        .numpy()
        .copy()
    )


if __name__ == "__main__":
    main()
