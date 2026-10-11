"""One frozen analytic shape control, saved raw forecasts only; no fit/inference."""
import argparse
import json
import resource
import time
from pathlib import Path

import numpy as np
from scipy.stats import norm

from diagnose import log_moments
from economic_probe import expected_exp
from experiment import DAY, HERE, clustered_ci, dump, metrics, sha


def describe(a):
    a = np.asarray(a)
    return {"min": float(a.min()), "mean": float(a.mean()), "max": float(a.max())}


def matched_normal(q, taus):
    q, taus = np.asarray(q, dtype=float), np.asarray(taus, dtype=float)
    if (q.ndim != 2 or taus.ndim != 1 or q.shape[1] != len(taus) or
            not np.isfinite(q).all() or not np.isfinite(taus).all() or
            not (np.diff(taus) > 0).all() or not (0 < taus[0] < taus[-1] < 1) or
            not (np.diff(q, axis=1) >= 0).all()):
        raise ValueError("invalid quantile identity/order")
    mean, variance = log_moments(q, taus)
    if not np.isfinite(variance).all() or (variance <= 0).any():
        raise ValueError("nonpositive/nonfinite raw variance; no tuned floor")
    z = norm.ppf(taus)
    mz, vz = log_moments(z[None], taus)
    standardized = (z-mz[0])/np.sqrt(vz[0])
    control = mean[:, None]+np.sqrt(variance[:, None])*standardized
    return control, mean, variance, float(mz[0]), float(vz[0])


def paired_intervals(pred, model_score, control_score, config):
    # Same grouping/order/random draws as the original registered clustered_ci.
    labels, groups = [], []
    for block, period in enumerate(config["evaluation"]):
        start = int(np.datetime64(period[0], "us").astype(np.int64))
        chunk = (pred["origin_us"]-start)//(config["bootstrap"]["calendar_block_days"]*DAY)
        for group in np.unique(chunk[pred["block"] == block]):
            loc = (pred["block"] == block) & (chunk == group)
            labels.append(block)
            groups.append(loc)
    totals_model = np.array([model_score[g].sum() for g in groups])
    totals_control = np.array([control_score[g].sum() for g in groups])
    counts = np.array([g.sum() for g in groups])
    rng = np.random.default_rng(config["bootstrap"]["seed"])
    delta, gain = [], []
    for _ in range(config["bootstrap"]["replicates"]):
        picked = []
        for block in sorted(set(labels)):
            indices = np.flatnonzero(np.asarray(labels) == block)
            picked.extend(rng.choice(indices, len(indices), replace=True))
        sum_model, sum_control = totals_model[picked].sum(), totals_control[picked].sum()
        delta.append((sum_model-sum_control)/counts[picked].sum())
        gain.append(1-sum_model/sum_control)
    primary = clustered_ci(pred, model_score-control_score, config)
    independent_delta = np.quantile(delta, [.025, .975])
    if not np.allclose(independent_delta, primary["ci95"], atol=1e-14, rtol=0):
        raise ValueError("different primary cluster draws")
    return {**primary, "relative_gain": float(1-model_score.mean()/control_score.mean()),
            "relative_gain_ci95": np.quantile(gain, [.025, .975]).tolist(),
            "gain_ci_method": "paired ratio of total scores on the same stratified joint-asset cluster draws"}


def support_audit(q, pred):
    y, taus = pred["y"], pred["taus"]
    lower, upper = y < q[:, :1], y > q[:, -1:]
    dates = pred["origin_us"][:, None]+np.arange(1, 23)[None]*DAY
    assets = np.broadcast_to(pred["asset"][:, None], dates.shape)
    pairs = np.stack([dates.ravel(), assets.ravel()], axis=1)
    unique = lambda hit: len(np.unique(pairs[hit.ravel()], axis=0))
    return {"lower_endpoint_mass": float(taus[0]), "upper_endpoint_mass": float(1-taus[-1]),
            "total_endpoint_mass": float(taus[0]+1-taus[-1]), "support_low": describe(q[:, 0]),
            "support_high": describe(q[:, -1]), "return_occurrences": int(y.size),
            "below_support_occurrences": int(lower.sum()), "above_support_occurrences": int(upper.sum()),
            "outside_support_occurrences": int((lower | upper).sum()),
            "below_support_unique_asset_labels": unique(lower), "above_support_unique_asset_labels": unique(upper),
            "outside_support_unique_asset_labels": unique(lower | upper),
            "max_lower_log_return_excess": float(np.maximum(q[:, :1]-y, 0).max()),
            "max_upper_log_return_excess": float(np.maximum(y-q[:, -1:], 0).max()),
            "interpretation": "fixed finite forecast support; observed misses repeat across origins; true neural tails unknown"}


def normal_representation(control, mean, variance, mz, vz, taus):
    sigma = np.sqrt(variance)
    scale, location = sigma/np.sqrt(vz), mean-sigma*mz/np.sqrt(vz)
    z0, z1 = norm.ppf(taus[[0, -1]])
    p0, p1 = taus[0], 1-taus[-1]
    clip_z_mean = z0*p0+norm.pdf(z0)-norm.pdf(z1)+z1*p1
    clip_z_second = (1-p0-p1)+z0*norm.pdf(z0)-z1*norm.pdf(z1)+z0*z0*p0+z1*z1*p1
    clipped_mean = location+scale*clip_z_mean
    clipped_variance = scale*scale*(clip_z_second-clip_z_mean*clip_z_mean)
    full_exp = np.exp(location+.5*scale*scale)
    clipped_exp = (p0*np.exp(location+scale*z0)+p1*np.exp(location+scale*z1)+
                   full_exp*(norm.cdf(z1-scale)-norm.cdf(z0-scale)))
    represented_exp = expected_exp(control, taus)
    identity_error = represented_exp-full_exp-(clipped_exp-full_exp)-(represented_exp-clipped_exp)
    if abs(identity_error).max() > 1e-12:
        raise ValueError("clipping/interpolation identity")
    cm, cv = log_moments(control, taus)
    mean_error, variance_error = abs(cm-mean), abs(cv-variance)
    if mean_error.max() > 1e-12 or (variance_error/variance).max() > 1e-10:
        raise ValueError("raw return-scale moments fail to match")
    return {
        "grid_standard_normal_mean": mz, "grid_standard_normal_variance": vz,
        "fixed_grid_centering": -mz/np.sqrt(vz), "fixed_grid_scale": 1/np.sqrt(vz),
        "raw_log_model_mean": describe(mean), "raw_log_model_variance": describe(variance),
        "maximum_raw_log_mean_absolute_error": float(mean_error.max()),
        "maximum_raw_log_variance_absolute_error": float(variance_error.max()),
        "maximum_raw_log_variance_relative_error": float((variance_error/variance).max()),
        "continuous_normal_location": describe(location), "continuous_normal_scale": describe(scale),
        "represented_minus_continuous_log_mean": describe(mean-location),
        "represented_minus_continuous_log_variance": describe(variance-scale*scale),
        "standard_normal_clipped_mean": float(clip_z_mean),
        "standard_normal_clipped_variance": float(clip_z_second-clip_z_mean*clip_z_mean),
        "tail_clipping_log_mean_change": describe(clipped_mean-location),
        "tail_clipping_log_variance_change": describe(clipped_variance-scale*scale),
        "interpolation_log_mean_change": describe(mean-clipped_mean),
        "interpolation_log_variance_change": describe(variance-clipped_variance),
        "continuous_normal_expected_exp": describe(full_exp), "clipped_normal_expected_exp": describe(clipped_exp),
        "represented_expected_exp": describe(represented_exp),
        "tail_clipping_expected_exp_change": describe(clipped_exp-full_exp),
        "interpolation_expected_exp_change": describe(represented_exp-clipped_exp),
        "total_representation_expected_exp_change": describe(represented_exp-full_exp),
        "maximum_Eexp_decomposition_error": float(abs(identity_error).max()),
        "endpoint_policy": "UNCHANGED; no tail refit or extrapolation; interpolation effect is not numerical integration error",
    }


def run(fit_state, diagnostic_state, state, cfg):
    dist_cfg = json.loads((HERE/"config.json").read_text())
    old = json.loads((fit_state/"RESULT.json").read_text())
    if sha((fit_state/"predictions.npz").read_bytes()) != cfg["prediction_sha256"]:
        raise ValueError("frozen prediction identity")
    if sha((diagnostic_state/"ANALYTIC_CONTROLS.npz").read_bytes()) != cfg["old_analytic_control_sha256"]:
        raise ValueError("saved A1 score identity")
    pred = np.load(fit_state/"predictions.npz", allow_pickle=False)
    if pred["q_model"].shape != (2265, 37) or pred["y"].shape != (2265, 22):
        raise ValueError("frozen prediction shape")
    if not np.array_equal(pred["taus"], dist_cfg["quantiles"]):
        raise ValueError("quantile grid changed")
    if not np.all(pred["label_end_us"]-pred["origin_us"] == 22*DAY):
        raise ValueError("label maturity identity")
    control, mean, variance, mz, vz = matched_normal(pred["q_model"], pred["taus"])
    print(json.dumps({"stage": "RAW_MOMENT_MATCH", "rows": len(control), "new_fits": 0, "new_inference": 0}), flush=True)
    control_metrics, crps_control = metrics(control, pred, dist_cfg)
    model_metrics, crps_model = metrics(pred["q_model"], pred, dist_cfg)
    if not np.array_equal(crps_model, pred["crps_model"]):
        raise ValueError("frozen model score changed")
    if model_metrics != old["model"]:
        raise ValueError("original model metrics differ")
    uncertainty = paired_intervals(pred, crps_model, crps_control, dist_cfg)
    a1 = np.load(diagnostic_state/"ANALYTIC_CONTROLS.npz", allow_pickle=False)
    a1_uncertainty = paired_intervals(pred, crps_model, a1["ZERO_MEAN_ORIGIN_EWMA_SIGMA_crps"], dist_cfg)
    periods = []
    for block, period in enumerate(dist_cfg["evaluation"]):
        loc = pred["block"] == block
        subset = {name: pred[name][loc] for name in ["y", "origin_us", "asset", "block", "label_end_us"]}
        cm, _ = metrics(control[loc], subset, dist_cfg)
        mm, _ = metrics(pred["q_model"][loc], subset, dist_cfg)
        periods.append({"period": period, "windows": int(loc.sum()), "control": cm, "model": mm,
                        "model_minus_control": float((crps_model-crps_control)[loc].mean()),
                        "relative_gain": float(1-crps_model[loc].mean()/crps_control[loc].mean())})
    checks = {
        "point_relative_gain_ge_1pct": uncertainty["relative_gain"] >= dist_cfg["gate"]["min_crps_relative_gain"],
        "paired_upper_interval_below_zero": uncertainty["ci95"][1] < 0,
        "tail_pinball_ratio_le_1_05": model_metrics["tail_pinball"]/control_metrics["tail_pinball"] <= dist_cfg["gate"]["max_tail_pinball_ratio"],
        "calibration_error_increase_le_0_01": model_metrics["max_tail_calibration_error"]-control_metrics["max_tail_calibration_error"] <= dist_cfg["gate"]["max_calibration_error_increase"],
    }
    representation = normal_representation(control, mean, variance, mz, vz, pred["taus"])
    np.savez_compressed(state/"SHAPE_CONTROL.npz", q_control=control, raw_mean=mean, raw_variance=variance,
                        crps_control=crps_control, crps_model=crps_model, origin_us=pred["origin_us"],
                        asset=pred["asset"], block=pred["block"], taus=pred["taus"])
    result = {
        "classification": cfg["classification"], "new_fits": 0, "new_neural_inference": 0,
        "new_analytic_controls": 1, "native_wallets": 0, "provider_downloads": 0,
        "evaluation_windows": 2265, "daily_return_occurrences": 49830,
        "model": model_metrics, "matched_normal_shape_control": control_metrics,
        "paired_effect_and_uncertainty": uncertainty, "periods": periods,
        "earlier_EWMA_comparison_paired_uncertainty": a1_uncertainty,
        "registered_gate_checks": checks,
        "registered_gate_decision": "SHAPE_DEVELOPMENT_GATE_PASS" if all(checks.values()) else "NO_RELIABLE_SHAPE_INCREMENT_FOR_THIS_RECIPE",
        "threshold_interpretation": "point-estimate registration; 0.99699986% versus1% is not an economically meaningful boundary; paired uncertainty retained",
        "tail_pinball_ratio_model_to_control": model_metrics["tail_pinball"]/control_metrics["tail_pinball"],
        "calibration_error_increase_model_to_control": model_metrics["max_tail_calibration_error"]-control_metrics["max_tail_calibration_error"],
        "raw_return_moments_and_representation": representation,
        "finite_support": {"model": support_audit(pred["q_model"], pred), "control": support_audit(control, pred)},
        "original_artifacts_and_results": "UNCHANGED", "no_new_policy_or_tradable_return_claim": True,
        "final_action": "STOP_ALL_ADDITIONAL_EXPERIMENTS_FOR_THIS_RECIPE",
        "source_sha256": {"old_predictions": cfg["prediction_sha256"], "old_analytic_controls": cfg["old_analytic_control_sha256"],
                          "shape_config": sha((HERE/"shape_config.json").read_bytes()), "shape_script": sha(Path(__file__).read_bytes()),
                          "original_metrics_script": sha((HERE/"experiment.py").read_bytes()), "moment_script": sha((HERE/"diagnose.py").read_bytes())},
        "new_control_artifact_sha256": sha((state/"SHAPE_CONTROL.npz").read_bytes()),
    }
    dump(state/"SHAPE_RESULT.json", result)
    print(json.dumps({"stage": "SHAPE_ABLATION_COMPLETE", "effect": uncertainty,
                      "decision": result["registered_gate_decision"], "final_action": result["final_action"]}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fit-state", type=Path, required=True)
    parser.add_argument("--diagnostic-state", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    if args.state.exists():
        raise ValueError("fresh shape state required")
    args.state.mkdir(parents=True)
    cfg = json.loads((HERE/"shape_config.json").read_text())
    receipt = {"stage": "STARTED", "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "new_fits": 0, "new_neural_inference": 0, "native_wallets": 0}
    start = time.monotonic()
    dump(args.state/"ATTEMPT.json", receipt)
    try:
        run(args.fit_state, args.diagnostic_state, args.state, cfg)
        total = sum(f.stat().st_size for f in args.state.iterdir() if f.is_file())
        if total > cfg["state_max_bytes"]:
            raise ValueError("state budget exceeded")
        receipt["stage"] = "SUCCESS"
    except BaseException as error:
        receipt.update(stage="FAILED", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        receipt["elapsed_seconds"] = time.monotonic()-start
        receipt["max_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        receipt["state_bytes"] = sum(f.stat().st_size for f in args.state.iterdir() if f.is_file())
        dump(args.state/"ATTEMPT.json", receipt)


if __name__ == "__main__":
    main()
