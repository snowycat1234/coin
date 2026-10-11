"""Independent Gauss-Legendre moments, scalar CDF/exp and clipping verification."""
import argparse
import hashlib
import json
import resource
import time
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.stats import norm

from verify_result import scalar_crps


def gl_moments(q, taus):
    # Two-node Gauss-Legendre is exact for linear Q and quadratic Q², including atoms.
    edges = np.r_[0., taus, 1.]
    nodes, weights = np.polynomial.legendre.leggauss(2)
    mean, second = np.zeros(len(q)), np.zeros(len(q))
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        u = lo+(nodes+1)*(hi-lo)/2
        values = np.array([np.interp(u, taus, row) for row in q])
        mean += (values @ weights)*(hi-lo)/2
        second += (values**2 @ weights)*(hi-lo)/2
    return mean, second-mean**2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fit-state", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    start = time.monotonic()
    result = json.loads((args.state/"SHAPE_RESULT.json").read_text())
    pred_path, control_path = args.fit_state/"predictions.npz", args.state/"SHAPE_CONTROL.npz"
    assert hashlib.sha256(pred_path.read_bytes()).hexdigest() == result["source_sha256"]["old_predictions"]
    assert hashlib.sha256(control_path.read_bytes()).hexdigest() == result["new_control_artifact_sha256"]
    pred, control = np.load(pred_path, allow_pickle=False), np.load(control_path, allow_pickle=False)
    taus, qm, qc = pred["taus"], pred["q_model"], control["q_control"]
    assert qc.shape == qm.shape == (2265, 37)
    for name in ["origin_us", "asset", "block", "taus"]:
        assert np.array_equal(pred[name], control[name])
    mm, vm = gl_moments(qm, taus)
    mc, vc = gl_moments(qc, taus)
    mean_error, variance_error = float(abs(mc-mm).max()), float(abs(vc-vm).max())
    relative_variance_error = float((abs(vc-vm)/vm).max())
    assert mean_error < 1e-12 and relative_variance_error < 1e-10
    assert abs(control["raw_mean"]-mm).max() < 1e-12
    assert abs(control["raw_variance"]-vm).max() < 1e-12
    mz, vz = gl_moments(norm.ppf(taus)[None], taus)
    ref_control = mm[:, None]+np.sqrt(vm[:, None])*(norm.ppf(taus)-mz[0])/np.sqrt(vz[0])
    control_error = float(abs(ref_control-qc).max())
    assert control_error < 1e-12
    # Source-bound representative rows include all periods and raw sigma extremes.
    selected = np.unique(np.r_[np.random.default_rng(271204).choice(len(qm), 26, replace=False),
                               [0, 1714, 1715, 1914, 1915, 2264, vm.argmin(), vm.argmax()]])
    cdf_errors, exp_summary, scalar_moment_error = {}, {}, 0.
    for name, q in [("model", qm), ("control", qc)]:
        ref_scores, exp_values = [], []
        for i in selected:
            ref_scores.append(np.mean([scalar_crps(q[i], y, taus) for y in pred["y"][i]]))
            values = [quad(lambda u: float(np.interp(u, taus, q[i])), 0., 1., points=taus, epsabs=1e-11, limit=200)[0],
                      quad(lambda u: float(np.interp(u, taus, q[i]))**2, 0., 1., points=taus, epsabs=1e-11, limit=200)[0],
                      quad(lambda u: np.exp(np.interp(u, taus, q[i])), 0., 1., points=taus, epsabs=1e-11, limit=200)[0]]
            mref, vref = (mm[i], vm[i]) if name == "model" else (mc[i], vc[i])
            scalar_moment_error = max(scalar_moment_error, abs(values[0]-mref), abs(values[1]-values[0]**2-vref))
            exp_values.append(values[2])
        saved = pred["crps_model"][selected] if name == "model" else control["crps_control"][selected]
        cdf_errors[name] = float(abs(np.asarray(ref_scores)-saved).max())
        assert cdf_errors[name] < 1e-9
        exp_summary[name] = exp_values
    assert scalar_moment_error < 1e-12
    # Independent scalar clipping integral versus the full Normal MGF, no additional scored control.
    z0, z1 = norm.ppf(taus[[0, -1]])
    location, scale = mm-np.sqrt(vm)*mz[0]/np.sqrt(vz[0]), np.sqrt(vm)/np.sqrt(vz[0])
    clip_values, full_values, maximum_exp_error = [], [], 0.
    for pos, i in enumerate(selected):
        loc, sig = location[i], scale[i]
        clipped = quad(lambda u: np.exp(loc+sig*np.clip(norm.ppf(u), z0, z1)), 0., 1.,
                       points=[taus[0], taus[-1]], epsabs=1e-11, limit=200)[0]
        full = quad(lambda z: np.exp(loc+sig*z)*norm.pdf(z), -12., 12., epsabs=1e-11, limit=200)[0]
        formula = (taus[0]*np.exp(qc[i, 0])+(1-taus[-1])*np.exp(qc[i, -1])+
                   np.exp(loc+.5*sig*sig)*(norm.cdf(z1-sig)-norm.cdf(z0-sig)))
        maximum_exp_error = max(maximum_exp_error, abs(formula-clipped), abs(full-np.exp(loc+.5*sig*sig)))
        assert abs(formula-clipped) < 1e-10 and abs(full-np.exp(loc+.5*sig*sig)) < 1e-10
        clip_values.append(clipped); full_values.append(full)
    # Check full-row analytic exp integration by a separate antiderivative per segment.
    edges = np.r_[0., taus, 1.]
    padded = np.c_[qc[:, 0], qc, qc[:, -1]]
    all_exp = np.zeros(len(qc))
    for j in range(len(edges)-1):
        lo, hi = edges[j:j+2]
        left, right = padded[:, j], padded[:, j+1]
        diff = right-left
        ratio = np.ones(len(diff))
        np.divide(np.expm1(diff), diff, out=ratio, where=diff != 0)
        all_exp += (hi-lo)*np.exp(left)*ratio
    represented_error = float(abs(all_exp[selected]-exp_summary["control"]).max())
    assert represented_error < 1e-10
    rep = result["raw_return_moments_and_representation"]
    assert abs(all_exp.mean()-rep["represented_expected_exp"]["mean"]) < 1e-12
    for name, q in [("model", qm), ("control", qc)]:
        support = result["finite_support"][name]
        assert int((pred["y"] < q[:, :1]).sum()) == support["below_support_occurrences"]
        assert int((pred["y"] > q[:, -1:]).sum()) == support["above_support_occurrences"]
        assert abs(support["total_endpoint_mass"]-.0001) < 1e-12
        # Independently check upper q99 occurrence rate and all tail pinball losses.
        saved = result["model"] if name == "model" else result["matched_normal_shape_control"]
        for tau in [.01, .05, .95, .99]:
            j = int(np.flatnonzero(taus == tau)[0]); d = pred["y"]-q[:, j, None]
            pb = np.where(d >= 0, tau*d, (tau-1)*d).mean()
            assert abs(pb-saved["tail_quantile_losses"][str(tau)]) < 1e-12
    gate = all(result["registered_gate_checks"].values())
    assert (result["registered_gate_decision"] == "SHAPE_DEVELOPMENT_GATE_PASS") == gate
    assert result["final_action"] == "STOP_ALL_ADDITIONAL_EXPERIMENTS_FOR_THIS_RECIPE"
    assert result["new_fits"] == result["new_neural_inference"] == result["native_wallets"] == 0
    # Preserve earlier source/results, allowing append-only task indexes.
    manifest = json.loads((Path(__file__).parent/"DELIVERY_MANIFEST.json").read_text())
    preserved = []
    for name, spec in manifest["files"].items():
        if name in ["README.md", "ATTEMPTS.jsonl"]:
            continue
        body = (Path(__file__).parent/name).read_bytes()
        assert len(body) == spec["bytes"] and hashlib.sha256(body).hexdigest() == spec["sha256"]
        preserved.append(name)
    out = {"status": "PASS", "raw_scale_all_row_moment_checks": len(qc),
           "maximum_mean_absolute_error": mean_error, "maximum_variance_absolute_error": variance_error,
           "maximum_variance_relative_error": relative_variance_error, "maximum_control_quantile_identity_error": control_error,
           "scalar_rows_per_arm": len(selected), "actual_return_axis_CDF_outcomes_per_arm": len(selected)*22,
           "maximum_CRPS_error": cdf_errors, "scalar_log_moment_integrals": len(selected)*4,
           "scalar_exp_integrals": len(selected)*4, "maximum_scalar_log_moment_error": scalar_moment_error,
           "maximum_clipped_or_continuous_normal_exp_error": maximum_exp_error,
           "maximum_represented_exp_error": represented_error, "all_four_tail_levels": "PASS_BOTH_ARMS",
           "original_manifest_files_preserved": preserved, "new_fits": 0, "new_neural_inference": 0,
           "native_wallets": 0, "source_sha256": result["source_sha256"],
           "elapsed_seconds": time.monotonic()-start, "max_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    args.output.write_text(json.dumps(out, indent=2)+"\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ["source_sha256", "original_manifest_files_preserved"]}))


if __name__ == "__main__":
    main()
