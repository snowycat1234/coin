"""Independent scalar integration and direct denominator checks; no diagnose import."""
import argparse
import hashlib
import json
import resource
import time
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.stats import binomtest

from verify_result import scalar_crps


def assert_close(a, b, tolerance=1e-12):
    assert np.max(np.abs(np.asarray(a)-np.asarray(b))) < tolerance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fit-state", type=Path, required=True)
    parser.add_argument("--economic-state", type=Path, required=True)
    parser.add_argument("--diagnostic-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    start = time.monotonic()
    result = json.loads((args.diagnostic_state/"DIAGNOSTIC_RESULT.json").read_text())
    identity = {args.fit_state/"predictions.npz": "old_predictions", args.fit_state/"model.pt": "old_model",
                args.fit_state/"FEATURE_ARCHIVE.zip": "feature_archive", args.economic_state/"UNIT_PROBE.npz": "old_unit_probe"}
    for path, key in identity.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == result["source_sha256"][key]
    assert hashlib.sha256((args.diagnostic_state/"ANALYTIC_CONTROLS.npz").read_bytes()).hexdigest() == result["new_control_artifact_sha256"]
    pred = np.load(args.fit_state/"predictions.npz", allow_pickle=False)
    probe = np.load(args.economic_state/"UNIT_PROBE.npz", allow_pickle=False)
    econ = np.load(args.economic_state/"ECONOMICS.npz", allow_pickle=False)
    controls = np.load(args.diagnostic_state/"ANALYTIC_CONTROLS.npz", allow_pickle=False)
    cfg = json.loads((Path(__file__).parent/"economic_config.json").read_text())
    dc = json.loads((Path(__file__).parent/"diagnostic_config.json").read_text())
    taus = pred["taus"]
    # Actual-return-axis CDF integration, independent of the fitted quantile-coordinate score.
    score_rows = np.unique(np.r_[np.random.default_rng(271203).choice(len(pred["y"]), 18, replace=False),
                                 [0, 1714, 1715, 1914, 1915, 2264]])
    score_errors = {}
    for name, spec in result["analytic_controls"].items():
        q, crps = controls[name+"_quantiles"], controls[name+"_crps"]
        ref = np.array([np.mean([scalar_crps(q[i], y, taus) for y in pred["y"][i]]) for i in score_rows])
        error = float(np.max(abs(ref-crps[score_rows])))
        assert error < 1e-9
        assert_close(crps.mean(), spec["metrics"]["crps_log_return"])
        gain = 1-pred["crps_model"].mean()/crps.mean()
        assert_close(gain, spec["model_relative_gain_against_this_control"])
        score_errors[name] = error
    ix, opp = probe["eligible_interval_indices"], probe["short_opportunity"]
    dates = econ["decision_us"][ix]
    q99 = int(np.flatnonzero(taus == .99)[0])
    q = probe["q_model"][ix, :, q99]
    actual = np.log(econ["prices"][ix+1]/econ["prices"][ix])
    assert np.array_equal(actual, probe["actual_r"])
    hit = (actual > q) & opp
    n, k = int(opp.sum()), int(hit.sum())
    assert (n, k, len(ix)) == (178, 8, 89)
    tail = result["economic_tail"]["arms"]["model"]
    cp = binomtest(k, n).proportion_ci(confidence_level=.95, method="exact")
    assert_close([cp.low, cp.high], tail["iid_cp95"])
    assert int(hit.any(axis=1).sum()) == tail["distinct_exceedance_dates"] == 8
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    for asset, entry in enumerate(tail["by_symbol"]):
        assert entry["symbol"] == symbols[asset]
        assert entry["denominator"] == int(opp[:, asset].sum())
        assert entry["exceedances"] == int(hit[:, asset].sum())
    months = np.array([str(np.datetime64(int(d), "us"))[:7] for d in dates])
    for entry in tail["by_month"]:
        mask = months == entry["month"]
        assert entry["denominator"] == int(opp[mask].sum())
        assert entry["exceedances"] == int(hit[mask].sum())
    cluster_checks = []
    for spec in tail["cluster_sensitivity"]:
        width = spec["width_days"]
        groups = [slice(i, min(i+width, len(ix))) for i in range(0, len(ix), width)]
        hits = np.array([hit[g].sum() for g in groups])
        denoms = np.array([opp[g].sum() for g in groups])
        assert hits.tolist() == spec["exceedance_counts"] and denoms.tolist() == spec["denominators"]
        draws = np.random.default_rng(dc["bootstrap_seed"]+width).integers(0, len(groups), size=(2000, len(groups)))
        # Scalar ratios retain real partial-cluster denominators.
        rates = [sum(int(hits[j]) for j in draw)/sum(int(denoms[j]) for j in draw) for draw in draws]
        assert_close(np.quantile(rates, [.025, .975]), spec["ci95"])
        cluster_checks.append({"width_days": width, "groups": len(groups), "replicates": len(rates)})
    pairs = {(int(d), asset) for row, d in enumerate(dates) for asset in range(5) if opp[row, asset]}
    assert len(pairs) == 178 and (np.diff(dates) == 86400000000).all()
    # Count overlapping future labels without trusting the diagnostic's aggregation.
    occurrence_hit = pred["y"] > pred["q_model"][:, q99, None]
    unique_labels = {(int(t)+(h+1)*86400000000, int(a)) for t, a in zip(pred["origin_us"], pred["asset"], strict=True) for h in range(22)}
    repeated = result["distribution_window_tail"]
    assert len(unique_labels) == repeated["unique_asset_label_pairs"] == 2580
    assert occurrence_hit.size == repeated["return_occurrences"] == 49830
    assert int(occurrence_hit.sum()) == repeated["arms"]["model"]["exceedances_occurrences"] == 1564
    # Three scalar integrals for every opportunity/arm, plus direct cashflow algebra.
    moment_error, net_error, integrals = 0., 0., 0
    for arm, key in [("model", "q_model"), ("gaussian", "q_control")]:
        means, variances, exp_values = [], [], []
        for row, asset in zip(*np.nonzero(opp), strict=True):
            qq = probe[key][ix[row], asset]
            values = [quad(lambda u: float(np.interp(u, taus, qq)), 0., 1., points=taus, epsabs=1e-11, limit=200)[0],
                      quad(lambda u: float(np.interp(u, taus, qq))**2, 0., 1., points=taus, epsabs=1e-11, limit=200)[0],
                      quad(lambda u: np.exp(np.interp(u, taus, qq)), 0., 1., points=taus, epsabs=1e-11, limit=200)[0]]
            mean, second, ee = values
            means.append(mean); variances.append(second-mean*mean); exp_values.append(ee)
            assert ee >= np.exp(mean)-1e-12
            for scale in cfg["funding_scales"]:
                funded = econ["funding_coeff"][ix[row]-2, asset]/econ["prices"][ix[row]-2, asset]*scale
                ref = (1-cfg["execution"])*(1-cfg["fee"])-(1+cfg["execution"])*(1+cfg["fee"])*ee+funded
                saved = probe[f"expected_{arm}_scale_{scale}"][row, asset]
                net_error = max(net_error, abs(ref-saved))
                assert abs(ref-saved) < 1e-10
                assert (ref > 0) == probe[f"selected_{arm}_scale_{scale}"][row, asset]
            integrals += 3
        for values, name in [(means, "expected_log_return"), (variances, "log_variance"), (exp_values, "expected_exp_return")]:
            stats = [min(values), np.mean(values), max(values)]
            saved = [result["zero_selection"][arm][name][x] for x in ["min", "mean", "max"]]
            moment_error = max(moment_error, float(np.max(abs(np.asarray(stats)-saved))))
            assert_close(stats, saved)
    assert result["fit_attempts"] == result["new_model_inference"] == result["native_wallets"] == 0
    # Check original tracked module/results against the immutable delivery snapshot.
    manifest = json.loads((Path(__file__).parent/"DELIVERY_MANIFEST.json").read_text())
    preserved = []
    for name, spec in manifest["files"].items():
        if name in ["README.md", "ATTEMPTS.jsonl"]:
            continue  # These two indexes only receive append-only follow-up links/receipts.
        data = (Path(__file__).parent/name).read_bytes()
        assert len(data) == spec["bytes"] and hashlib.sha256(data).hexdigest() == spec["sha256"]
        preserved.append(name)
    out = {"status": "PASS", "classification": "INDEPENDENT_READ_ONLY_SEEN_HISTORY_DIAGNOSTIC_VERIFICATION",
           "new_fits": 0, "new_neural_inference": 0, "new_wallets": 0,
           "cdf_score_rows_per_control": len(score_rows), "cdf_score_outcomes_per_control": len(score_rows)*22,
           "maximum_crps_error": score_errors, "exact_CP_independent_binomtest": [cp.low, cp.high],
           "tail_count_and_unique_pairs": [k, n], "cluster_checks": cluster_checks,
           "scalar_moment_integrals": integrals, "maximum_moment_summary_error": moment_error,
           "maximum_forecast_net_error": net_error, "original_manifest_files_preserved": preserved,
           "source_sha256": result["source_sha256"], "elapsed_seconds": time.monotonic()-start,
           "max_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    args.output.write_text(json.dumps(out, indent=2)+"\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ["source_sha256", "original_manifest_files_preserved"]}))


if __name__ == "__main__":
    main()
