"""Fixed descriptive saved-forecast witnesses; never a new trading rule."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--economic-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads((args.economic_state/"ECONOMIC_RESULT.json").read_text())
    assert hashlib.sha256((args.economic_state/"UNIT_PROBE.npz").read_bytes()).hexdigest() == result["external_probe_sha256"]
    a = np.load(args.economic_state/"UNIT_PROBE.npz", allow_pickle=False)
    e = np.load(args.economic_state/"ECONOMICS.npz", allow_pickle=False)
    cfg = json.loads((Path(__file__).parent/"economic_config.json").read_text())
    ix = a["eligible_interval_indices"]
    pairs = list(zip(*np.nonzero(a["short_opportunity"]), strict=True))
    q = np.array([a["q_model"][ix[row], asset] for row, asset in pairs])
    pdown = np.array([np.interp(0., qq, a["taus"], left=0., right=1.) for qq in q])
    expected = np.array([a["expected_model_scale_1.0"][row, asset] for row, asset in pairs])
    actual = np.array([a["actual_net_scale_1.0"][row, asset] for row, asset in pairs])
    funding = np.array([e["funding_coeff"][ix[row]-2, asset]/e["prices"][ix[row]-2, asset] for row, asset in pairs])
    ee = ((1-cfg["execution"])*(1-cfg["fee"])+funding-expected)/((1+cfg["execution"])*(1+cfg["fee"]))
    funded_gross_positive = np.flatnonzero(1-ee+funding > 0)
    descriptions = [("highest_forecast_down_probability", int(pdown.argmax())),
                    ("largest_realized_net_winner", int(actual.argmax())),
                    ("largest_realized_net_loser", int(actual.argmin())),
                    ("closest_expected_net_to_zero", int(expected.argmax()))]
    if len(funded_gross_positive) == 1:
        descriptions.append(("sole_positive_funded_gross_price", int(funded_gross_positive[0])))
    witnesses = []
    for reason, pos in descriptions:
        row, asset = pairs[pos]
        qq = q[pos]
        mean = quad(lambda u: float(np.interp(u, a["taus"], qq)), 0., 1., points=a["taus"], epsabs=1e-11, limit=200)[0]
        er = quad(lambda u: np.exp(np.interp(u, a["taus"], qq)), 0., 1., points=a["taus"], epsabs=1e-11, limit=200)[0]
        assert abs(er-ee[pos]) < 1e-12
        witnesses.append({"reason": reason, "decision_UTC": str(np.datetime64(int(e["decision_us"][ix[row]]), "us")),
                          "symbol": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"][asset],
                          "down_probability": float(pdown[pos]), "log_mean": float(mean),
                          "gross_price_expectation": float(1-er), "rebound_convexity": float(er-np.exp(mean)),
                          "lagged_funding_scale1": float(funding[pos]),
                          "execution_cost": float(cfg["execution"]*(1+er)),
                          "fee_cost": float(cfg["fee"]*((1-cfg["execution"])+(1+cfg["execution"])*er)),
                          "expected_net_scale1": float(expected[pos]),
                          "profit_probability_scale1": float(a["profit_probability_model_scale_1.0"][row, asset]),
                          "expected_net_scale001": float(a["expected_model_scale_0.01"][row, asset]),
                          "profit_probability_scale001": float(a["profit_probability_model_scale_0.01"][row, asset]),
                          "actual_net_scale1": float(actual[pos]),
                          "original_selected": bool(a["selected_model_scale_1.0"][row, asset])})
    out = {"classification": "RETROSPECTIVE_DESCRIPTIVE_COUNTEREXAMPLES_SAVED_FORECASTS_ONLY",
           "new_policy_or_threshold": False, "neural_fit_or_inference": 0, "funding_units_uncertified": True,
           "opportunities": len(pairs), "p_down_gt_half": int((pdown > .5).sum()),
           "all_expected_nets_negative": bool((expected < 0).all()),
           "p_down_min_mean_max": [float(pdown.min()), float(pdown.mean()), float(pdown.max())],
           "witnesses": witnesses, "source_unit_probe_sha256": result["external_probe_sha256"]}
    args.output.write_text(json.dumps(out, indent=2)+"\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
