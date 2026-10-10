"""Two fixed historical wallets after public terminal freeze; no result selection."""

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import torch

from modules.temporal_cached_july.data import inputs as july_inputs
from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_july_transfer.evaluate import reconcile as july_reconcile
from modules.temporal_q4_reserved.evaluate import manifest
from modules.temporal_q4_reserved.reconcile import reconcile as q4_reconcile
from modules.temporal_q4_reserved.terminal import charged_terminal_path
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, charged_boundary_path
from modules.temporal_scaler_refit.eval_inputs import q4_inputs
from modules.temporal_short_expansion.adapter import compress, expand
from modules.temporal_two_expert.checkpoint import _atomic_json, _rng_state, model_identity
from modules.temporal_two_expert.exact import sha

from .protocol import ARM, protocol, sources
from .stage import frozen_state


def run(state, economics, fit, output, publication):
    out = Path(output)
    out.mkdir()
    _atomic_json(out / "STARTED.json", dict(periods=["July", "Q4"], once_only=True))
    records = {}
    began = time.monotonic()
    try:
        model, optimizer, scaler, snapshot, terminal = frozen_state(state, economics, fit)
        public = json.loads(Path(publication).read_text())
        assert public["status"] == "PASS_ALL_PUBLIC_BYTES"
        assert public["checkpoint_SHA256"] == terminal["checkpoint_SHA256"]
        assert public["terminal_SHA256"] == sha(Path(fit) / ARM / "TERMINAL.json")
        assert public["source_identity"] == sources()
        before = (
            model_identity(model),
            tree_identity(optimizer.state_dict()),
            tree_identity(_rng_state()),
        )
        model.eval()
        for label in ["July", "Q4"]:
            if label == "July":
                e, p, receipt, _, _ = july_inputs(state)
            else:
                e, p, receipt = q4_inputs(state)
            n = len(e.contexts)
            with torch.no_grad():
                request = predict_episode(model, e, feature_batch_size=32).numpy()
            assert (
                request.shape == (n, 6)
                and np.isfinite(request).all()
                and not np.any(request[~e.eligible])
                and not np.any(request[:, 2:4])
            )
            np.testing.assert_allclose(request.sum(1), 1, atol=1e-12, rtol=0)
            np.savez_compressed(
                out / (label + "_REQUESTS.npz"),
                request=request,
                decision_us=e.windows.decision_us,
                eligible=e.eligible,
            )
            targets, mapped = p.mapped_path(compress(request), e.internal.contexts)
            with torch.no_grad():
                kernel = charged_boundary_path if label == "July" else charged_terminal_path
                report = kernel(
                    torch.tensor(targets, dtype=torch.float64),
                    e.prices,
                    e.funding_coeff,
                    plan=BoundaryPlan.full_fill_diagnostic(n),
                )
            record, rows = (july_reconcile if label == "July" else q4_reconcile)(
                request, e, targets, mapped, report
            )
            assert before == (
                model_identity(model),
                tree_identity(optimizer.state_dict()),
                tree_identity(_rng_state()),
            )
            np.savez_compressed(
                out / (label + "_PATH.npz"),
                request=request,
                targets=targets,
                budget=expand(np.stack([r["budget"] for r in mapped])),
                nav=report["nav"].numpy(),
                quantity=report["quantity"].numpy(),
                boundary_held_quantity=report["boundary_held_quantity"].numpy(),
            )
            with (out / (label + "_DAILY.csv")).open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
                w.writeheader()
                w.writerows(rows)
            _atomic_json(out / (label + "_INPUT_RECEIPT.json"), receipt)
            _atomic_json(out / (label + "_COMPLETED.json"), record)
            records[label] = record
        result = dict(
            status="TWO_FIXED_PERIODS_COMPLETE_DAILY_NOT_NATIVE",
            policies=records,
            terminal=terminal,
            normalization=scaler.provenance,
            scaler_identity=scaler.identity,
            model_Adam_RNG_unchanged=True,
            new_wallets=2,
            model_inferences=2,
            optimizer_updates=0,
            scaler_updates=0,
            control_reruns=0,
            no_new_OOS=True,
            no_promotion=True,
            elapsed_seconds=time.monotonic() - began,
            public_terminal_commit=public["remote_SHA"],
        )
    except Exception as exc:
        result = dict(
            status="STOP_ONCE_ONLY_EVALUATION_FAILURE",
            error=type(exc).__name__,
            reason=str(exc),
            policies=records,
            retry_authorized=False,
        )
    _atomic_json(out / "RESULT.json", result)
    _atomic_json(
        out / "MANIFEST.json", dict(files=manifest(out), sources=sources(), protocol=protocol())
    )
    print(json.dumps(result), flush=True)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for n in ("state", "economics", "fit", "output", "publication"):
        p.add_argument("--" + n, type=Path, required=True)
    a = p.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    run(a.state, a.economics, a.fit, a.output, a.publication)
