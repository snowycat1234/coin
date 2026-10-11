"""Frozen post-result attribution. Saved forecasts only; no model fit/inference."""
import argparse
import hashlib
import json
import resource
import time
from pathlib import Path

import numpy as np
from scipy.stats import beta, norm

from economic_probe import expected_exp
from experiment import (
    DAY, HERE, build_samples, clustered_ci, dump, load_daily, metrics, sha,
)


def binomial_interval(hits, denominator):
    if denominator == 0:
        return None
    lo = 0. if hits == 0 else beta.ppf(.025, hits, denominator-hits+1)
    hi = 1. if hits == denominator else beta.ppf(.975, hits+1, denominator-hits)
    return [float(lo), float(hi)]


def cluster_tail_interval(hits, opportunity, dates, days, replicates, seed):
    """Nonoverlapping date clusters with all cross-sectional observations together."""
    if not np.all(np.diff(dates) == DAY):
        raise ValueError("real contiguous day grid required")
    labels = (dates-dates.min())//(days*DAY)
    groups = np.unique(labels)
    k = np.array([np.count_nonzero(hits[labels == g] & opportunity[labels == g]) for g in groups])
    n = np.array([np.count_nonzero(opportunity[labels == g]) for g in groups])
    rng = np.random.default_rng(seed)
    selected = rng.integers(0, len(groups), size=(replicates, len(groups)))
    denominator = n[selected].sum(1)
    valid = denominator > 0
    rate = k[selected][valid].sum(1)/denominator[valid]
    return {"width_days": days, "clusters": len(groups), "exceedance_counts": k.tolist(),
            "denominators": n.tolist(), "replicates": replicates, "ci95": np.quantile(rate, [.025, .975]).tolist(),
            "zero_denominator_resamples": int((~valid).sum()),
            "method": "joint asset nonoverlapping calendar-cluster percentile sensitivity, not IID market evidence"}


def log_moments(q, taus):
    u = np.r_[0., taus, 1.]
    padded = np.concatenate([q[:, :1], q, q[:, -1:]], axis=1)
    left, right = padded[:, :-1], padded[:, 1:]
    mean = (np.diff(u)[None]*(left+right)/2).sum(1)
    second = (np.diff(u)[None]*(left*left+left*right+right*right)/3).sum(1)
    return mean, second-mean*mean


def describe(a):
    return {"min": float(np.min(a)), "mean": float(np.mean(a)), "max": float(np.max(a))}


def mean_price_terms(q, taus):
    mean, variance = log_moments(q, taus)
    ee = expected_exp(q, taus)
    deterministic_price = 1-np.exp(mean)
    convexity = ee-np.exp(mean)
    if convexity.min() < -1e-12:
        raise ValueError("Jensen violation")
    return mean, variance, ee, deterministic_price, convexity


def zero_selection(probe, econ, cfg):
    ix = probe["eligible_interval_indices"]
    opp = probe["short_opportunity"].ravel()
    lagged = (econ["funding_coeff"][ix-2]/econ["prices"][ix-2]).ravel()
    taus = probe["taus"]
    out = {}
    for name, key in [("model", "q_model"), ("gaussian", "q_control")]:
        q = probe[key][ix].reshape(-1, len(taus))
        mean, variance, ee, deterministic_price, convexity = mean_price_terms(q, taus)
        price = 1-ee
        execution = cfg["execution"]*(1+ee)
        fees = cfg["fee"]*((1-cfg["execution"])+(1+cfg["execution"])*ee)
        atoms = taus[0]*np.exp(q[:, 0])+(1-taus[-1])*np.exp(q[:, -1])
        atom_mass = taus[0]+1-taus[-1]
        interior_renormalized = (ee-atoms)/(1-atom_mass)
        atom_net_bound = (1+cfg["execution"])*(1+cfg["fee"])*abs(ee-interior_renormalized)
        entry = {"expected_log_return": describe(mean[opp]), "log_variance": describe(variance[opp]),
                 "expected_exp_return": describe(ee[opp]), "deterministic_log_mean_short_price": describe(deterministic_price[opp]),
                 "convexity_rebound_loss": describe(convexity[opp]), "gross_expected_short_price": describe(price[opp]),
                 "execution_cost": describe(execution[opp]), "fee_cost": describe(fees[opp]),
                 "negative_log_mean_count": int((mean[opp] < 0).sum()), "gross_price_positive_count": int((price[opp] > 0).sum()),
                 "endpoint_atom_mass": float(atom_mass), "endpoint_exp_contribution": describe(atoms[opp]),
                 "max_net_change_from_hypothetical_atom_removal_and_interior_renormalization": float(atom_net_bound[opp].max()),
                 "actual_atom_policy": "UNCHANGED; effect bound is diagnostic only", "scenarios": []}
        for scale in cfg["funding_scales"]:
            funding = lagged*scale
            full = deterministic_price-convexity-execution-fees+funding
            expected = probe[f"expected_{name}_scale_{scale}"].ravel()
            if not np.allclose(full, expected, atol=1e-12, rtol=0):
                raise ValueError("saved expectation differs")
            if not np.array_equal(opp & (full > 0), probe[f"selected_{name}_scale_{scale}"].ravel()):
                raise ValueError("saved selection differs")
            count = lambda value: int((value[opp] > 0).sum())
            entry["scenarios"].append({
                "funding_scale": scale, "forecast_funding": describe(funding[opp]), "full_expected_net": describe(full[opp]),
                "positive_algebraic_counts": {
                    "gross_price": count(price), "price_plus_funding": count(price+funding),
                    "funded_price_minus_execution": count(price+funding-execution),
                    "funded_price_minus_fees": count(price+funding-fees), "full_net": count(full),
                    "net_without_fees": count(full+fees), "net_without_execution": count(full+execution),
                    "net_without_funding": count(full-funding),
                },
                "maximum_saved_net_error": float(abs(full-expected).max()),
                "minimum_negative_net_distance_from_zero": float(-full[opp].max()) if (full[opp] < 0).all() else None,
                "tail_penalty_in_expectation": 0., "actual_threshold": 0.,
                "threshold_adjustment": "NONE", "no_new_trading_policy_or_wallet": True,
            })
        out[name] = entry
    return out


def economic_tail(probe, econ, daily_available, returns, symbols, cfg):
    ix, opp, taus = probe["eligible_interval_indices"], probe["short_opportunity"], probe["taus"]
    dates = econ["decision_us"][ix]
    actual = probe["actual_r"]
    if not np.array_equal(actual, np.log(econ["prices"][ix+1]/econ["prices"][ix])):
        raise ValueError("execution outcomes identity")
    # Completed-close day1 value at D+DAY; it is a separate basis from actual execution.
    lookup = np.searchsorted(daily_available, dates+DAY)
    if not np.array_equal(daily_available[lookup], dates+DAY):
        raise ValueError("close-to-close day1 grid")
    close_y = returns[lookup]
    if not np.isfinite(close_y).all():
        raise ValueError("missing close-basis outcome")
    out = {"opportunities": int(opp.sum()), "available_asset_days": int(actual.size), "available_dates": len(dates),
           "first_entry": str(np.datetime64(int(econ["execution_us"][ix[0]]), "us")),
           "last_exit": str(np.datetime64(int(econ["execution_us"][ix[-1]+1]), "us")),
           "distinct_asset_exit_pairs": int(np.count_nonzero(opp)),
           "overlapping_holding_outcomes": False, "input_windows_overlap": "adjacent22-day windows share21 completed days",
           "common_market_shocks": True, "calendar_overlap_with_late22_day_labels": "only forecasts, no repeated one-day unit outcome",
           "basis_log_return_difference": describe((actual-close_y)[opp]), "arms": {}}
    q99 = int(np.flatnonzero(taus == .99)[0])
    months = np.array([str(np.datetime64(int(t), "us"))[:7] for t in dates])
    hit = {}
    for name, key in [("model", "q_model"), ("gaussian", "q_control")]:
        threshold = probe[key][ix, :, q99]
        exceed = actual > threshold
        hit[name] = exceed & opp
        k, n = int((exceed & opp).sum()), int(opp.sum())
        close_exceed = close_y > threshold
        by_symbol, by_month, symbol_month = [], [], []
        for a, s in enumerate(symbols):
            denom, hits = int(opp[:, a].sum()), int((exceed[:, a] & opp[:, a]).sum())
            by_symbol.append({"symbol": s, "exceedances": hits, "denominator": denom,
                              "rate": hits/denom if denom else None, "iid_cp95": binomial_interval(hits, denom)})
            for m in np.unique(months):
                loc = months == m
                denom, hits = int(opp[loc, a].sum()), int((exceed[loc, a] & opp[loc, a]).sum())
                symbol_month.append({"symbol": s, "month": str(m), "exceedances": hits, "denominator": denom})
        for m in np.unique(months):
            loc = months == m
            denom, hits = int(opp[loc].sum()), int((exceed[loc] & opp[loc]).sum())
            by_month.append({"month": str(m), "exceedances": hits, "denominator": denom,
                             "rate": hits/denom if denom else None})
        witnesses = []
        for row, a in zip(*np.nonzero(exceed & opp), strict=True):
            witnesses.append({"decision_UTC": str(np.datetime64(int(dates[row]), "us")), "symbol": symbols[a],
                              "actual_log_return": float(actual[row, a]), "actual_simple_return": float(np.expm1(actual[row, a])),
                              "predicted_q99_log_return": float(threshold[row, a]), "predicted_q99_simple_return": float(np.expm1(threshold[row, a])),
                              "excess_log_return": float(actual[row, a]-threshold[row, a]),
                              "completed_close_log_return": float(close_y[row, a]),
                              "close_basis_also_exceeds": bool(close_exceed[row, a])})
        out["arms"][name] = {
            "exceedances": k, "denominator": n, "rate": k/n, "nominal_rate": .01,
            "iid_cp95": binomial_interval(k, n), "iid_interval_scope": "descriptive only; market independence not established",
            "cluster_sensitivity": [cluster_tail_interval(exceed, opp, dates, w, cfg["bootstrap_replicates"], cfg["bootstrap_seed"]+w)
                                    for w in cfg["economic_tail_clusters_days"]],
            "distinct_exceedance_dates": int(np.any(exceed & opp, axis=1).sum()), "by_symbol": by_symbol,
            "by_month": by_month, "symbol_month": symbol_month, "event_witnesses": witnesses,
            "close_basis_exceedances": int((close_exceed & opp).sum()),
            "actual_vs_close_changed_tail_membership": int(((close_exceed != exceed) & opp).sum()),
        }
    out["both_arms_same_tail_events"] = int((hit["model"] & hit["gaussian"]).sum())
    return out


def repeated_tail(predictions):
    taus = predictions["taus"]
    q99 = int(np.flatnonzero(taus == .99)[0])
    events = predictions["origin_us"][:, None]+np.arange(1, 23)[None]*DAY
    assets = np.broadcast_to(predictions["asset"][:, None], events.shape)
    pairs = np.stack([events.ravel(), assets.ravel()], axis=1)
    unique, repeats = np.unique(pairs, axis=0, return_counts=True)
    out = {"return_occurrences": int(events.size), "unique_asset_label_pairs": len(unique),
           "minimum_occurrences_per_pair": int(repeats.min()), "maximum_occurrences_per_pair": int(repeats.max()),
           "calendar_labels": len(np.unique(events)), "arms": {}}
    for name in ["model", "control"]:
        q = predictions[f"q_{name}"][:, q99, None]
        hit = predictions["y"] > q
        out["arms"][name] = {
            "exceedances_occurrences": int(hit.sum()), "denominator_occurrences": int(events.size), "rate": float(hit.mean()),
            "unique_asset_label_pairs_with_any_exceedance": len(np.unique(pairs[hit.ravel()], axis=0)),
            "by_horizon": [{"day": d+1, "exceedances": int(hit[:, d].sum()), "denominator": hit.shape[0]}
                           for d in range(22)],
            "interpretation": "one realized return may exceed different origin forecasts repeatedly; not IID trials",
        }
    return out


def comparison_population(pred, probe, econ):
    ix = probe["eligible_interval_indices"]
    old_pairs = {(int(t), int(a)) for t, a in zip(pred["origin_us"], pred["asset"], strict=True)}
    common, later = np.zeros_like(probe["short_opportunity"]), np.zeros_like(probe["short_opportunity"])
    differences = []
    old = {(int(t), int(a)): i for i, (t, a) in enumerate(zip(pred["origin_us"], pred["asset"], strict=True))}
    for row, interval in enumerate(ix):
        for a in range(5):
            pair = int(econ["decision_us"][interval]), a
            common[row, a] = pair in old_pairs
            later[row, a] = pair not in old_pairs
            if pair in old:
                differences.append(np.max(abs(pred["q_model"][old[pair]]-probe["q_model"][interval, a])))
    if max(differences, default=0) > 1e-7:
        raise ValueError("reused forecasts differ beyond batch arithmetic")
    hit = probe["actual_r"] > probe["q_model"][ix, :, int(np.flatnonzero(probe["taus"] == .99)[0])]
    opp = probe["short_opportunity"]
    return {"common_asset_origins": int(common.sum()), "extra_economic_only_asset_origins": int(later.sum()),
            "common_short_opportunities": int((common & opp).sum()), "extra_economic_only_short_opportunities": int((later & opp).sum()),
            "common_tail_exceedances": int((common & opp & hit).sum()), "extra_economic_only_tail_exceedances": int((later & opp & hit).sum()),
            "maximum_reused_model_forecast_batch_difference": float(max(differences, default=0))}


def run(fit_state, economic_state, state, config):
    dist_cfg = json.loads((HERE/"config.json").read_text())
    econ_cfg = json.loads((HERE/"economic_config.json").read_text())
    old = json.loads((fit_state/"RESULT.json").read_text())
    economic = json.loads((economic_state/"ECONOMIC_RESULT.json").read_text())
    for name, spec in old["external_artifacts"].items():
        if sha((fit_state/name).read_bytes()) != spec["sha256"]:
            raise ValueError("old fit identity")
    if sha((economic_state/"UNIT_PROBE.npz").read_bytes()) != economic["external_probe_sha256"]:
        raise ValueError("old unit forecast identity")
    if sha((economic_state/"ECONOMICS.npz").read_bytes()) != economic["source"]["economic_npz_sha256"]:
        raise ValueError("old economic identity")
    pred = np.load(fit_state/"predictions.npz", allow_pickle=False)
    probe = np.load(economic_state/"UNIT_PROBE.npz", allow_pickle=False)
    econ = np.load(economic_state/"ECONOMICS.npz", allow_pickle=False)
    available, x, z, r, sigma, audit = load_daily(fit_state/"FEATURE_ARCHIVE.zip", dist_cfg)
    ev = build_samples(available, x, z, r, sigma, dist_cfg, dist_cfg["evaluation"])
    for name in ["origin_us", "label_end_us", "asset", "block", "y"]:
        if not np.array_equal(ev[name], pred[name]):
            raise ValueError("old samples differ")
    taus = dist_cfg["quantiles"]
    original_q = ev["mu"][:, None]+ev["std"][:, None]*norm.ppf(taus)
    if not np.array_equal(original_q, pred["q_control"]):
        raise ValueError("old Gaussian quantiles differ")
    controls = {"ZERO_MEAN_ROLLING22_SIGMA": ev["std"][:, None]*norm.ppf(taus),
                "ZERO_MEAN_ORIGIN_EWMA_SIGMA": ev["sigma"][:, None]*norm.ppf(taus)}
    old_metrics, old_crps = metrics(pred["q_control"], ev, dist_cfg)
    model_metrics, model_crps = metrics(pred["q_model"], ev, dist_cfg)
    comparisons, artifacts = {}, {}
    for name, q in controls.items():
        summary, crps = metrics(q, ev, dist_cfg)
        periods = []
        for block, period in enumerate(dist_cfg["evaluation"]):
            loc = ev["block"] == block
            subset = {k: v[loc] for k, v in ev.items() if isinstance(v, np.ndarray)}
            periods.append({"period": period, "control": metrics(q[loc], subset, dist_cfg)[0],
                            "model": metrics(pred["q_model"][loc], subset, dist_cfg)[0]})
        comparisons[name] = {"metrics": summary, "relative_gain_vs_original_rolling_gaussian": 1-summary["crps_log_return"]/old_metrics["crps_log_return"],
                             "model_relative_gain_against_this_control": 1-model_metrics["crps_log_return"]/summary["crps_log_return"],
                             "model_minus_this_control_uncertainty": clustered_ci(ev, model_crps-crps, dist_cfg),
                             "this_control_minus_original_uncertainty": clustered_ci(ev, crps-old_crps, dist_cfg), "periods": periods}
        artifacts[name+"_quantiles"] = q
        artifacts[name+"_crps"] = crps
    np.savez_compressed(state/"ANALYTIC_CONTROLS.npz", **artifacts)
    result = {
        "classification": config["classification"], "source_model_predictions_unchanged": True,
        "fit_attempts": 0, "new_model_inference": 0, "native_wallets": 0,
        "original_model": model_metrics, "original_control": old_metrics, "analytic_controls": comparisons,
        "economic_tail": economic_tail(probe, econ, available, r, dist_cfg["symbols"], config),
        "distribution_window_tail": repeated_tail(pred), "population_reconciliation": comparison_population(pred, probe, econ),
        "zero_selection": zero_selection(probe, econ, econ_cfg),
        "source_sha256": {"old_predictions": sha((fit_state/"predictions.npz").read_bytes()),
                          "old_unit_probe": sha((economic_state/"UNIT_PROBE.npz").read_bytes()),
                          "old_model": sha((fit_state/"model.pt").read_bytes()), "feature_archive": audit["archive_sha256"],
                          "diagnostic_config": sha((HERE/"diagnostic_config.json").read_bytes()),
                          "diagnostic_script": sha((HERE/"diagnose.py").read_bytes())},
        "new_control_artifact_sha256": sha((state/"ANALYTIC_CONTROLS.npz").read_bytes()),
        "original_gates_and_thresholds": "UNCHANGED", "nonfinite_or_identity_failures": 0,
    }
    dump(state/"DIAGNOSTIC_RESULT.json", result)
    print(json.dumps({"stage": "DIAGNOSTIC_COMPLETE", "controls": {k: v["metrics"]["crps_log_return"] for k, v in comparisons.items()},
                      "tail": result["economic_tail"]["arms"]["model"]["rate"], "new_fits": 0}), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fit-state", type=Path, required=True)
    p.add_argument("--economic-state", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    args = p.parse_args()
    if args.state.exists():
        raise ValueError("fresh diagnostic output required")
    args.state.mkdir(parents=True)
    config = json.loads((HERE/"diagnostic_config.json").read_text())
    receipt = {"stage": "STARTED", "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "new_fits": 0, "new_neural_inference": 0, "new_wallets": 0}
    start = time.monotonic()
    dump(args.state/"ATTEMPT.json", receipt)
    try:
        run(args.fit_state, args.economic_state, args.state, config)
        receipt["stage"] = "SUCCESS"
    except BaseException as ex:
        receipt.update(stage="FAILED", error_type=type(ex).__name__, error=str(ex))
        raise
    finally:
        receipt["elapsed_seconds"] = time.monotonic()-start
        receipt["max_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        receipt["state_bytes"] = sum(f.stat().st_size for f in args.state.iterdir() if f.is_file())
        dump(args.state/"ATTEMPT.json", receipt)


if __name__ == "__main__":
    main()
