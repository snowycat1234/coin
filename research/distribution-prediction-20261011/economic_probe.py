"""Frozen paired short-unit decision diagnostic, never a native wallet claim."""
import argparse
import io
import json
import resource
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
from scipy.special import exprel
from scipy.stats import norm

from experiment import DAY, HERE, QLSTM, cdf_at, dump, load_daily, quantile_crps, sha


def expected_exp(q, taus):
    """Analytic E[exp(r)] for linear quantiles and the same endpoint atoms."""
    u = np.r_[0., taus, 1.]
    padded = np.concatenate([q[:, :1], q, q[:, -1:]], axis=1)
    return (np.diff(u)[None]*np.exp(padded[:, :-1])*exprel(np.diff(padded, axis=1))).sum(1)


def unit_components(log_return, funding, fee, execution):
    ratio = np.exp(log_return)
    price = 1-ratio
    costs = execution*(1+ratio)
    fees = fee*((1-execution)+ratio*(1+execution))
    return {"price": price, "execution": costs, "fees": fees, "funding": funding,
            "net": price-costs-fees+funding}


def expected_net(q, taus, forecast_funding, fee, execution):
    return (1-execution)*(1-fee)-(1+execution)*(1+fee)*expected_exp(q, taus)+forecast_funding


def profit_cutoff(forecast_funding, fee, execution):
    numerator = (1-execution)*(1-fee)+forecast_funding
    if (numerator <= 0).any():
        raise ValueError("invalid forecast funding cutoff")
    return np.log(numerator/((1+execution)*(1+fee)))


def lagged_funding(coeff, prices, starts, ends, decisions, lag=2):
    ix = np.arange(lag, len(coeff))
    if not (ends[ix-lag] < decisions[ix]).all():
        raise ValueError("funding forecast not strictly mature")
    if not (starts[ix-lag] < ends[ix-lag]).all():
        raise ValueError("invalid funding clock")
    return ix, coeff[ix-lag]/prices[ix-lag]


def git_bytes(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=HERE)


def source_packet(config, state):
    index_body = git_bytes(config["data_commit"], config["data_prefix"]+"CONSUMER_INDEX.json")
    consumer = json.loads(index_body)
    body = git_bytes(config["data_commit"], config["data_prefix"]+"Q42024/ECONOMICS.npz")
    if sha(body) != config["economics_sha256"]:
        raise ValueError("economic bytes identity")
    specs = [d for d in consumer["derived_artifacts"] if d["path"] == "ECONOMICS.npz"] if "derived_artifacts" in consumer else []
    # Consumer schema uses explicit supplied field names, inspected without outcome metrics.
    if not specs:
        for value in consumer.values():
            if isinstance(value, list):
                specs.extend(d for d in value if isinstance(d, dict) and d.get("path") == "ECONOMICS.npz")
    if len(specs) != 1 or specs[0]["SHA256"] != sha(body) or specs[0]["bytes"] != len(body):
        raise ValueError("consumer binding")
    ctx = git_bytes(config["context_commit"], config["context_prefix"]+"CURRENT_EXPERT_INPUTS92.npz")
    manifest_body = git_bytes(config["context_commit"], config["context_prefix"]+"MANIFEST.json")
    manifest = json.loads(manifest_body)
    if sha(ctx) != config["context_sha256"] or manifest["files"]["CURRENT_EXPERT_INPUTS92.npz"]["SHA256"] != sha(ctx):
        raise ValueError("causal target bytes identity")
    (state/"ECONOMICS.npz").write_bytes(body)
    (state/"SHORT_CONTEXT.npz").write_bytes(ctx)
    return np.load(io.BytesIO(body), allow_pickle=False), np.load(io.BytesIO(ctx), allow_pickle=False), {
        "economic_commit": config["data_commit"], "economic_npz_sha256": sha(body),
        "consumer_sha256": sha(index_body), "context_commit": config["context_commit"],
        "context_npz_sha256": sha(ctx), "context_manifest_sha256": sha(manifest_body),
        "provider_download_bytes": 0, "new_market_source": False,
    }


def daily_ci(values, days, config):
    start = days.min()
    group = (days-start)//(config["cluster_days"]*DAY)
    clusters = [values[group == k] for k in np.unique(group)]
    counts = np.asarray([len(c) for c in clusters])
    totals = np.asarray([c.sum() for c in clusters])
    rng = np.random.default_rng(config["bootstrap_seed"])
    sample = rng.integers(0, len(clusters), (config["bootstrap_replicates"], len(clusters)))
    means = totals[sample].sum(1)/counts[sample].sum(1)
    return {"mean_model_minus_gaussian_unit_net": float(values.mean()),
            "ci95": np.quantile(means, [.025, .975]).tolist(), "calendar_clusters": len(clusters),
            "count_per_cluster": counts.tolist(), "method": "paired44-day calendar clusters on existing short opportunities; few clusters"}


def component_means(parts, ix):
    if not ix.any():
        return {k: None for k in parts}
    return {k: float(v[ix].mean()) for k, v in parts.items()}


def run(fit_state, state, config):
    result = json.loads((fit_state/"RESULT.json").read_text())
    if not all(result["gate"].values()):
        raise ValueError("distribution gate failed")
    for name, spec in result["external_artifacts"].items():
        if sha((fit_state/name).read_bytes()) != spec["sha256"]:
            raise ValueError("fit artifact differs")
    for name in ["experiment.py", "config.json"]:
        if sha((HERE/name).read_bytes()) != result["source_sha256"].get(name, result["config_sha256"]):
            raise ValueError("frozen distribution source differs")
    dist_cfg = json.loads((HERE/"config.json").read_text())
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    checkpoint = torch.load(fit_state/"model.pt", map_location="cpu", weights_only=False)
    model = QLSTM(dist_cfg)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    scalers = checkpoint["scalers"]
    avail, x, z, r, sigma, _ = load_daily(fit_state/"FEATURE_ARCHIVE.zip", dist_cfg)
    econ, ctx, bindings = source_packet(config, state)
    if econ["symbol_order"].tolist() != dist_cfg["symbols"] or ctx["symbol_order"].tolist() != dist_cfg["symbols"]:
        raise ValueError("symbol order")
    if not np.array_equal(econ["decision_us"], ctx["decision_us"]) or not np.all(np.diff(econ["decision_us"]) == DAY):
        raise ValueError("causal target calendar")
    if econ["prices"].shape != (92, 5) or econ["funding_coeff"].shape != (91, 5):
        raise ValueError("real unpadded calendar")
    if not np.isfinite(econ["prices"]).all() or not (econ["prices"] > 0).all() or not np.isfinite(econ["funding_coeff"]).all():
        raise ValueError("unknown economic input")
    if not (econ["execution_us"] == econ["decision_us"]+60_000_001).all():
        raise ValueError("economic execution basis")
    slot = ctx["expert_order"].tolist().index(config["expert"])
    if not (ctx["target_available_us"][:, slot] <= ctx["decision_us"]).all():
        raise ValueError("future targets")
    days, assets, xx, zz, ss, mu, std = [], [], [], [], [], [], []
    for t in econ["decision_us"]:
        index = int(np.searchsorted(avail, t))
        if index >= len(avail) or avail[index] != t:
            raise ValueError("absent completed-day price features")
        for a in range(5):
            xa, za = x[index-21:index+1, a], z[index-21:index+1]
            if not np.isfinite(xa).all() or not np.isfinite(za).all():
                raise ValueError("missing causal feature")
            days.append(t); assets.append(a); xx.append(xa); zz.append(za); ss.append(sigma[index, a])
            past = r[index-21:index+1, a]
            mu.append(past.mean()); std.append(max(past.std(ddof=1), dist_cfg["sigma_floor"]))
    X = torch.tensor((np.asarray(xx)-scalers["x"]["mean"])/scalers["x"]["std"], dtype=torch.float32)
    Z = torch.tensor((np.asarray(zz)-scalers["z"]["mean"])/scalers["z"]["std"], dtype=torch.float32)
    S = torch.tensor(ss, dtype=torch.float32)
    with torch.no_grad():
        qm = model(X, Z, S)[1].numpy().astype(float).reshape(92, 5, -1)
    qb = (np.asarray(mu)[:, None]+np.asarray(std)[:, None]*norm.ppf(dist_cfg["quantiles"])).reshape(92, 5, -1)
    dates = econ["decision_us"]
    ix, lagged = lagged_funding(econ["funding_coeff"], econ["prices"], econ["funding_interval_start_us"],
                              econ["funding_interval_end_us"], dates, config["funding_lag_intervals"])
    actual_r = np.log(econ["prices"][ix+1]/econ["prices"][ix])
    opportunity = (ctx["expert_targets"][ix, slot] < 0) & ctx["expert_eligible"][ix, slot, None]
    if not opportunity.any():
        raise ValueError("no existing short context; no artificial substitute")
    q = {"model": qm[ix].reshape(-1, 37), "gaussian": qb[ix].reshape(-1, 37)}
    day_grid = np.repeat(dates[ix], 5)
    opportunity_flat = opportunity.ravel()
    scenarios = []
    saved = {"decision_us": dates, "q_model": qm, "q_control": qb, "eligible_interval_indices": ix,
             "actual_r": actual_r, "short_opportunity": opportunity, "taus": dist_cfg["quantiles"]}
    for scale in config["funding_scales"]:
        forecast = (lagged*scale).ravel()
        actual_funding = (econ["funding_coeff"][ix]/econ["prices"][ix]*scale).ravel()
        parts = unit_components(actual_r.ravel(), actual_funding, config["fee"], config["execution"])
        profit = parts["net"] > 0
        probes, decisions = {}, {}
        for name, quantiles in q.items():
            expected = expected_net(quantiles, dist_cfg["quantiles"], forecast, config["fee"], config["execution"])
            p_profit = cdf_at(quantiles, profit_cutoff(forecast, config["fee"], config["execution"]), dist_cfg["quantiles"])
            selected = opportunity_flat & (expected > 0)
            decisions[name] = selected
            up99 = dist_cfg["quantiles"].index(.99)
            tail = float((actual_r.ravel()[opportunity_flat] > quantiles[opportunity_flat, up99]).mean())
            probes[name] = {
                "selected_opportunities": int(selected.sum()), "declined_opportunities": int((opportunity_flat & ~selected).sum()),
                "selected_unit_component_means": component_means(parts, selected),
                "expected_unit_net_on_opportunities_mean": float(expected[opportunity_flat].mean()),
                "profit_brier_on_opportunities": float(((p_profit-profit)**2)[opportunity_flat].mean()),
                "predicted_profit_probability_mean": float(p_profit[opportunity_flat].mean()),
                "predicted_down_probability_mean": float(cdf_at(quantiles, 0., dist_cfg["quantiles"])[opportunity_flat].mean()),
                "observed_profit_frequency": float(profit[opportunity_flat].mean()),
                "upper1pct_price_tail_exceedance": tail,
                "declined_winners": int((opportunity_flat & ~selected & profit).sum()),
                "declined_losers": int((opportunity_flat & ~selected & ~profit).sum()),
                "selected_winners": int((selected & profit).sum()),
                "selected_losers": int((selected & ~profit).sum()),
                "unconditional_candidate_unit_net_mean": float((parts["net"]*selected)[opportunity_flat].mean()),
            }
            saved[f"selected_{name}_scale_{scale}"] = selected.reshape(len(ix), 5)
            saved[f"expected_{name}_scale_{scale}"] = expected.reshape(len(ix), 5)
            saved[f"profit_probability_{name}_scale_{scale}"] = p_profit.reshape(len(ix), 5)
        delta = parts["net"]*(decisions["model"].astype(int)-decisions["gaussian"].astype(int))
        ci = daily_ci(delta[opportunity_flat], day_grid[opportunity_flat], config)
        mg, bg = probes["model"], probes["gaussian"]
        selected_mean = mg["selected_unit_component_means"]["net"]
        gates = {
            "model_selected_at_least20": mg["selected_opportunities"] >= config["minimum_selected_opportunities"],
            "paired_utility_lower95_positive": ci["ci95"][0] > 0,
            "model_selected_net_mean_positive": selected_mean is not None and selected_mean > 0,
            "profit_brier_no_worse": mg["profit_brier_on_opportunities"] <= bg["profit_brier_on_opportunities"],
            "upper1pct_tail_exceedance_at_most2pct": mg["upper1pct_price_tail_exceedance"] <= config["max_upper1pct_tail_exceedance"],
        }
        scenarios.append({"funding_scale": scale, "arms": probes, "all_existing_short_unit_components": component_means(parts, opportunity_flat),
                          "down_days_still_net_losers": int(((actual_r.ravel() < 0) & ~profit & opportunity_flat).sum()),
                          "paired_unit_utility": ci, "native_spending_gate": gates})
        saved[f"actual_net_scale_{scale}"] = parts["net"].reshape(len(ix), 5)
    np.savez_compressed(state/"UNIT_PROBE.npz", **saved)
    result = {
        "classification": config["classification"], "source": bindings, "existing_expert": config["expert"],
        "available_asset_days": len(ix)*5, "available_decision_days": len(ix),
        "existing_short_opportunities": int(opportunity.sum()), "first2_days_without_mature_funding_forecast": True,
        "funding_prediction_clock_maximum_lag_interval_end_us": int(econ["funding_interval_end_us"][ix[-1]-2]),
        "first_forecast_date": str(np.datetime64(int(dates[ix[0]]), "us")),
        "last_held_interval_exit": str(np.datetime64(int(econ["execution_us"][ix[-1]+1]), "us")),
        "scenarios": scenarios, "native_wallets": 0,
        "decision": "READY_TO_FREEZE_NATIVE_PAIR" if all(all(s["native_spending_gate"].values()) for s in scenarios) else "STOP_ECONOMIC_RECIPE_NO_NATIVE_REPLAY",
        "basis_mismatch": "forecast uses completed-close daily returns; diagnostic labels use actual00:01 execution-to-execution",
        "fit_model_sha256": sha((fit_state/"model.pt").read_bytes()),
        "economic_config_sha256": sha((HERE/"economic_config.json").read_bytes()),
        "economic_source_sha256": sha((HERE/"economic_probe.py").read_bytes()),
        "external_probe_sha256": sha((state/"UNIT_PROBE.npz").read_bytes()),
        "no_capital_return_or_APR": True, "no_native_margin_or_capacity_claim": True,
        "inference_only_no_retrain": True,
    }
    dump(state/"ECONOMIC_RESULT.json", result)
    print(json.dumps({"stage": "COMPLETE_UNIT_PROBE", "opportunities": result["existing_short_opportunities"],
                      "decision": result["decision"], "selected": [s["arms"]["model"]["selected_opportunities"] for s in scenarios]}), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fit-state", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    args = p.parse_args()
    if args.state.exists():
        raise ValueError("fresh probe directory required")
    args.state.mkdir(parents=True)
    config = json.loads((HERE/"economic_config.json").read_text())
    receipt = {"stage": "STARTED", "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "source_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip(),
               "model_fits": 0, "native_wallets": 0}
    start = time.monotonic()
    dump(args.state/"ATTEMPT.json", receipt)
    try:
        run(args.fit_state, args.state, config)
        receipt["stage"] = "SUCCESS"
    except BaseException as ex:
        receipt.update(stage="FAILED", error_type=type(ex).__name__, error=str(ex))
        raise
    finally:
        receipt["elapsed_seconds"] = time.monotonic()-start
        receipt["max_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        dump(args.state/"ATTEMPT.json", receipt)


if __name__ == "__main__":
    main()
