"""Saved-policy turnover attribution and cost algebra only; no training entry."""
import argparse
import json
from pathlib import Path

import numpy as np

from .cost_feasibility import (ARMS, EXPERIMENT as COST_EXPERIMENT, FEE, POLICIES,
                               RATE, ROOT, SLIP, SPREAD, arithmetic, git,
                               read_saved, sha, write_json, preserved)

EXPERIMENT = ROOT / "research/slow-momentum-cpd-objective-diagnostic-20261011"
CATEGORIES = ("INITIAL_ENTRY", "ELIGIBILITY_ENTRY", "ELIGIBILITY_EXIT",
              "SIGN_REVERSAL", "SAME_SIGN_AMPLITUDE", "SIGNAL_ZERO_ENTRY_EXIT",
              "TERMINAL_EXIT", "CASH_NO_CHANGE")
COMPONENTS = ("signal", "vol_scaling", "price_drift", "boundary_or_eligibility")


def turnover_attribution(position, vol, eligible, returns):
    p, v, mask, r = np.asarray(position), np.asarray(vol), np.asarray(eligible, bool), np.asarray(returns)
    if p.ndim != 2 or v.shape != p.shape or mask.shape != p.shape or r.shape != p.shape:
        raise ValueError("Ordered calendar/asset axes required")
    if not np.isfinite(p).all() or np.any(p[~mask] != 0):
        raise ValueError("Finite saved positions, cash when ineligible")
    if not (np.isfinite(v[mask]).all() and (v[mask] > 0).all() and np.isfinite(r[mask]).all()):
        raise ValueError("Missing eligible causal vol or mature outcome")
    w = np.zeros_like(p, dtype=float)
    w[mask] = RATE * p[mask] / v[mask] / 5
    summary, _ = arithmetic(w, r)
    previous_w, previous_p, previous_r = np.zeros(p.shape[1]), np.zeros(p.shape[1]), np.zeros(p.shape[1])
    previous_vol, previous_mask = np.full(p.shape[1], np.nan), np.zeros(p.shape[1], bool)
    totals = {k: dict(absolute_component=0., signed_trade_projection=0.) for k in COMPONENTS}
    categories = {k: dict(events=0, turnover=0., fixed_cost=0.) for k in CATEGORIES}
    residual = 0.
    for t in range(len(p) + 1):
        terminal = t == len(p)
        current_w = np.zeros(p.shape[1]) if terminal else w[t]
        carry = previous_w * (1 + previous_r)
        delta = current_w - carry
        for a in range(p.shape[1]):
            comp = dict.fromkeys(COMPONENTS, 0.)
            if terminal:
                category = "TERMINAL_EXIT"
                comp["boundary_or_eligibility"] = delta[a]
            elif t == 0:
                category = "INITIAL_ENTRY"
                comp["boundary_or_eligibility"] = delta[a]
            elif mask[t, a] and previous_mask[a]:
                # Symmetric exact allocation of target-change interaction.
                # These are signed components, not separate tradable/costed legs.
                inv_now, inv_old = 1 / v[t, a], 1 / previous_vol[a]
                comp["signal"] = RATE / 10 * (p[t, a] - previous_p[a]) * (inv_now + inv_old)
                comp["vol_scaling"] = RATE / 10 * (p[t, a] + previous_p[a]) * (inv_now - inv_old)
                comp["price_drift"] = -previous_w[a] * previous_r[a]
                if p[t, a] * previous_p[a] < 0:
                    category = "SIGN_REVERSAL"
                elif p[t, a] == 0 or previous_p[a] == 0:
                    category = "SIGNAL_ZERO_ENTRY_EXIT"
                else:
                    category = "SAME_SIGN_AMPLITUDE"
            elif mask[t, a] and not previous_mask[a]:
                category = "ELIGIBILITY_ENTRY"
                comp["boundary_or_eligibility"] = delta[a]
            elif not mask[t, a] and previous_mask[a]:
                category = "ELIGIBILITY_EXIT"
                comp["boundary_or_eligibility"] = delta[a]
            else:
                category = "CASH_NO_CHANGE"
            error = abs(sum(comp.values()) - delta[a])
            residual = max(residual, error)
            assert error < 1e-14
            amount = abs(float(delta[a]))
            cost = (FEE + SPREAD + SLIP) * amount + FEE * (SPREAD + SLIP) * float(delta[a])
            categories[category]["events"] += int(amount > 0)
            categories[category]["turnover"] += amount
            categories[category]["fixed_cost"] += cost
            for k, value in comp.items():
                totals[k]["absolute_component"] += abs(value)
                totals[k]["signed_trade_projection"] += value * np.sign(delta[a])
        if not terminal:
            previous_w, previous_p, previous_vol, previous_mask = w[t], p[t], v[t], mask[t]
            previous_r = np.zeros(p.shape[1])
            previous_r[mask[t]] = r[t, mask[t]]
    assert abs(sum(c["turnover"] for c in categories.values()) - summary["drift_trade_turnover"]) < 1e-12
    assert abs(sum(c["fixed_cost"] for c in categories.values()) - summary["fixed_cost_total"]) < 1e-12
    assert abs(sum(c["signed_trade_projection"] for c in totals.values()) - summary["drift_trade_turnover"]) < 1e-12
    absolute = np.abs(p[mask])
    return dict(financial=summary, categories=categories, components=totals,
                maximum_signed_decomposition_residual=residual, eligible_count=int(mask.sum()),
                position_abs_mean=float(absolute.mean()) if len(absolute) else None,
                position_abs_quantiles=np.quantile(absolute, [.1, .5, .9, .99]).tolist() if len(absolute) else None,
                abs_position_below_counts={str(x): int((absolute < x).sum()) for x in (.001, .01, .05)},
                position_abs_max=float(absolute.max()) if len(absolute) else None)


def tensor_cost_returns(weights, returns, eligible):
    """Exact differentiable static-reference screen; abs kink uses subgradient0.

    Only synthetic tensors are used by this task. No model or optimizer call.
    This function is not a native wallet or a released training runner.
    """
    import torch
    if weights.ndim != 2 or returns.shape != weights.shape or eligible.shape != weights.shape or eligible.dtype != torch.bool:
        raise ValueError("Wrong ordered tensor axes")
    if not torch.isfinite(weights).all() or not torch.isfinite(returns[eligible]).all() or torch.any(returns[eligible] <= -1):
        raise ValueError("Nonfinite eligible weights/outcomes")
    w = torch.where(eligible, weights, torch.zeros_like(weights))
    r = torch.where(eligible, returns, torch.zeros_like(returns))
    gross = w * r
    carried = w + gross
    delta = torch.cat((w[:1], w[1:] - carried[:-1], -carried[-1:]), dim=0)
    # sign(delta)*abs(delta)==delta, retains exact signed fill-fee derivative.
    c = (FEE + SPREAD + SLIP) * delta.abs() + FEE * (SPREAD + SLIP) * delta
    daily = gross.sum(1) - c[:-1].sum(1)
    daily = daily - torch.cat((torch.zeros_like(daily[:-1]), c[-1:].sum().reshape(1)))
    return daily, c


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    before = verify_evidence()
    args.output.mkdir(parents=True, exist_ok=False)
    blocks = read_saved(2048)
    old = json.loads((COST_EXPERIMENT / "results/RESULT.json").read_text())
    out = dict(schema="SAVED2048_OBJECTIVE_DIAGNOSTIC_V1", checkout_head=git("rev-parse", "HEAD").decode().strip(),
               protocol_sha256=sha((EXPERIMENT / "PROTOCOL.json").read_bytes()),
               executing_source_sha256=sha(Path(__file__).read_bytes()), positions_sha256=old["positions_sha256"],
               cost_result_sha256=sha((COST_EXPERIMENT / "results/RESULT.json").read_bytes()),
               components_meaning="Signed exact symmetric target decomposition plus previous-realized price drift; absolute components may offset and must not be costed separately",
               categories_meaning="Actual trade amount grouped by sign change, same-sign amplitude, or paid boundary; groups are descriptive, never oracle causal return attribution",
               descriptive_near_zero_thresholds=[.001, .01, .05], blocks=[], aggregate={},
               new_training_updates=0, new_model_inferences=0, wallets=0, new_policy_validation_queries=0)
    for b in blocks:
        vol = read_vol_from_source(b)
        values = {}
        for j, policy in enumerate(POLICIES):
            values[policy] = turnover_attribution(b["positions"][:, :, j],
                                                 vol, b["eligible"], b["returns"])
        out["blocks"].append(dict(start=b["start"], policies=values))
    for j, policy in enumerate(POLICIES):
        parts = [x["policies"][policy] for x in out["blocks"]]
        finance = old["aggregate"][policy]
        for b, old_b in zip(out["blocks"], old["blocks"], strict=True):
            for k in ("gross_price_proxy", "fixed_cost_total", "drift_trade_turnover", "fixed_cost_adjusted_price_proxy"):
                assert abs(b["policies"][policy]["financial"][k] - old_b["policies"][policy][k]) < 1e-12
        positions = np.concatenate([b["positions"][:, :, j][b["eligible"].astype(bool)] for b in blocks])
        total = dict(financial=finance, eligible_count=len(positions),
                     position_abs_mean=float(np.abs(positions).mean()),
                     position_abs_quantiles=np.quantile(np.abs(positions), [.1, .5, .9, .99]).tolist(),
                     abs_position_below_counts={str(x): int((np.abs(positions) < x).sum()) for x in (.001, .01, .05)},
                     position_abs_max=float(np.abs(positions).max()), categories={}, components={})
        for group, keys in (("categories", CATEGORIES), ("components", COMPONENTS)):
            for key in keys:
                total[group][key] = {field: sum(b[group][key][field] for b in parts) for field in parts[0][group][key]}
        out["aggregate"][policy] = total
    out["scale_fact"] = "All fixed-reference weights, gross, drift-turnover and BASE27 costs are degree1 homogeneous for positive uniform rescaling. Shrinking/expanding positions alone cannot change signed margin or break-even rate. This is an algebraic fact, no rescaled strategy evaluated. Native minimum/rounding/risk would break homogeneity and remain unmeasured."
    out["preservation"] = verify_evidence()
    assert out["preservation"] == before
    write_json(args.output / "RESULT.json", out)
    print(json.dumps({k: out["aggregate"][k] for k in ("trend_ensemble", "trend_cpd_ensemble")}))


def read_vol_from_source(block):
    # Original saved vol, no inversion through near-zero positions/outcomes.
    import csv
    from .cost_feasibility import SOURCES
    path = ROOT / "research" / SOURCES[2048][0] / "results/POSITIONS.csv"
    with path.open() as handle:
        rows = [row for row in csv.DictReader(handle) if row["block"] == block["start"]]
    return np.array([float(row["daily_vol"] or "nan") for row in rows]).reshape(block["days"], 5)


def verify_evidence():
    old = preserved()
    manifest = json.loads((COST_EXPERIMENT / "DELIVERY_MANIFEST.json").read_text())
    for path, value in manifest["files"].items():
        assert sha((ROOT / path).read_bytes()) == value["sha256"]
        assert (ROOT / path).stat().st_size == value["bytes"]
    return dict(predecessor=old, cost_manifest_files=len(manifest["files"]), status="BYTE_UNCHANGED")


if __name__ == "__main__":
    main()
