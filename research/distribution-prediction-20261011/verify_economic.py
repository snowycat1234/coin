"""Independent Decimal realized cashflows and scalar forecast integration."""
import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import numpy as np
from scipy.integrate import quad


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    r = json.loads((args.state/"ECONOMIC_RESULT.json").read_text())
    cfg = json.loads((Path(__file__).parent/"economic_config.json").read_text())
    files = {"ECONOMICS.npz": r["source"]["economic_npz_sha256"],
             "SHORT_CONTEXT.npz": r["source"]["context_npz_sha256"], "UNIT_PROBE.npz": r["external_probe_sha256"]}
    for name, digest in files.items():
        assert hashlib.sha256((args.state/name).read_bytes()).hexdigest() == digest
    a = np.load(args.state/"UNIT_PROBE.npz", allow_pickle=False)
    e = np.load(args.state/"ECONOMICS.npz", allow_pickle=False)
    c = np.load(args.state/"SHORT_CONTEXT.npz", allow_pickle=False)
    ix = a["eligible_interval_indices"]
    assert ix.tolist() == list(range(2, 91))
    assert (e["funding_interval_end_us"][ix-2] < e["decision_us"][ix]).all()
    slot = c["expert_order"].tolist().index("CSMOM21")
    opp = (c["expert_targets"][ix, slot] < 0) & c["expert_eligible"][ix, slot, None]
    assert np.array_equal(opp, a["short_opportunity"]) and opp.sum() == r["existing_short_opportunities"]
    assert (e["execution_us"][ix+1]-e["execution_us"][ix] == 86400000000).all()
    f, s = Decimal(str(cfg["fee"])), Decimal(str(cfg["execution"]))
    max_error, forecast_error = 0., 0.
    # Independent quadrature for every short candidate, both forecast arms.
    reference_exp = {}
    for arm, key in [("model", "q_model"), ("gaussian", "q_control")]:
        vals = np.full((len(ix), 5), np.nan)
        for row, asset in zip(*np.nonzero(opp), strict=True):
            q = a[key][ix[row], asset]
            vals[row, asset] = quad(lambda u: np.exp(np.interp(u, a["taus"], q)), 0., 1.,
                                    points=a["taus"], epsabs=1e-11, limit=200)[0]
        reference_exp[arm] = vals
    for scenario in r["scenarios"]:
        scale = scenario["funding_scale"]
        ref = np.zeros((len(ix), 5))
        for row, interval in enumerate(ix):
            for asset in range(5):
                entry, exit = Decimal(str(e["prices"][interval, asset])), Decimal(str(e["prices"][interval+1, asset]))
                receipt = Decimal(str(e["funding_coeff"][interval, asset]))*Decimal(str(scale))
                sold, bought = entry*(1-s), exit*(1+s)
                ref[row, asset] = float((sold-bought-f*(sold+bought)+receipt)/entry)
        actual = a[f"actual_net_scale_{scale}"]
        max_error = max(max_error, float(abs(ref-actual).max()))
        assert np.max(abs(ref-actual)) < 1e-12
        profit = ref > 0
        rdown = a["actual_r"] < 0
        assert int((rdown & ~profit & opp).sum()) == scenario["down_days_still_net_losers"]
        lagged = e["funding_coeff"][ix-2]/e["prices"][ix-2]*scale
        for arm in ["model", "gaussian"]:
            expected = float((1-s)*(1-f))-float((1+s)*(1+f))*reference_exp[arm]+lagged
            saved = a[f"expected_{arm}_scale_{scale}"]
            forecast_error = max(forecast_error, float(abs(expected[opp]-saved[opp]).max()))
            assert np.max(abs(expected[opp]-saved[opp])) < 1e-10
            selected = (expected > 0) & opp
            assert np.array_equal(selected, a[f"selected_{arm}_scale_{scale}"])
            summary = scenario["arms"][arm]
            assert int(selected.sum()) == summary["selected_opportunities"]
            if selected.any():
                assert abs(ref[selected].mean()-summary["selected_unit_component_means"]["net"]) < 1e-12
            else:
                assert summary["selected_unit_component_means"]["net"] is None
            assert abs((ref*selected)[opp].mean()-summary["unconditional_candidate_unit_net_mean"]) < 1e-12
    assert r["native_wallets"] == 0 and r["decision"] == "STOP_ECONOMIC_RECIPE_NO_NATIVE_REPLAY"
    out = {"status": "PASS", "actual_cashflow_checks": len(ix)*5*len(r["scenarios"]),
           "scalar_forecast_integral_checks": int(opp.sum())*2,
           "maximum_Decimal_realized_net_error": max_error, "maximum_quadrature_expected_net_error": forecast_error,
           "funding_forecast_strictly_mature": True, "decision_and_zero_activity_checks": "PASS",
           "native_wallet_validation": "NOT_RUN_NO_NATIVE_ACCOUNT_CREATED", "no_profit_OR_APR_claim": True}
    args.output.write_text(json.dumps(out, indent=2)+"\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
