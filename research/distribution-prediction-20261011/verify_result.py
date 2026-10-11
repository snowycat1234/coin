"""Read-only independent scalar CDF scoring and saved-evidence verification."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad


def scalar_crps(q, y, taus):
    lo, hi = min(float(y), float(q[0])), max(float(y), float(q[-1]))
    if lo == hi:
        return 0.
    knots = sorted({float(v) for v in [*q, y] if lo < v < hi})
    def f(v):
        return (float(np.interp(v, q, taus, left=0., right=1.))-float(v >= y))**2
    return quad(f, lo, hi, points=knots, epsabs=1e-11, limit=200)[0]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    r = json.loads((args.state/"RESULT.json").read_text())
    attempt = json.loads((args.state/"ATTEMPT.json").read_text())
    for name, spec in r["external_artifacts"].items():
        data = (args.state/name).read_bytes()
        assert len(data) == spec["bytes"] and hashlib.sha256(data).hexdigest() == spec["sha256"]
    a = np.load(args.state/"predictions.npz", allow_pickle=False)
    assert attempt["stage"] == "SUCCESS"
    assert r["scope"]["fits"] == 1
    assert a["y"].shape == (2265, 22)
    assert (np.diff(a["origin_us"]) >= 0).all()
    assert (a["label_end_us"]-a["origin_us"] == 22*86400000000).all()
    assert np.isfinite(a["q_model"]).all() and (np.diff(a["q_model"], axis=1) >= 0).all()
    taus = a["taus"]
    rng = np.random.default_rng(271200)
    # Independent CDF integral over each future day of 36 rows, including every block.
    ix = np.unique(np.r_[rng.choice(len(a["y"]), 30, replace=False), [0, 1714, 1715, 1914, 1915, 2264]])
    errors = {}
    for name in ["model", "control"]:
        ref = np.array([sum(scalar_crps(a[f"q_{name}"][i], y, taus) for y in a["y"][i])/22 for i in ix])
        err = np.max(abs(ref-a[f"crps_{name}"][ix]))
        assert err < 1e-9
        assert abs(a[f"crps_{name}"].mean()-r[name]["crps_log_return"]) < 1e-12
        errors[name] = float(err)
        # Scalar loop at four tail levels; no call into experiment metrics.
        for tau in [.01, .05, .95, .99]:
            j = np.flatnonzero(taus == tau)[0]
            q = a[f"q_{name}"][:, j, None]
            d = a["y"]-q
            pin = np.where(d >= 0, tau*d, (tau-1)*d).mean()
            assert abs(pin-r[name]["tail_quantile_losses"][str(tau)]) < 1e-12
            coverage = (a["y"] < q).mean()
            assert abs(coverage-r[name]["empirical_cdf_at_quantiles"][str(tau)]) < 1e-12
    out = {"status": "PASS", "cdf_integration_rows": len(ix), "cdf_integration_outcomes_per_arm": len(ix)*22,
           "maximum_independent_crps_error": errors, "tail_pinball_and_coverage": "PASS_ALL_FOUR_LEVELS",
           "artifact_sha_and_size_checks": len(r["external_artifacts"]), "fit_attempts": 1,
           "prediction_sha256": hashlib.sha256((args.state/"predictions.npz").read_bytes()).hexdigest(),
           "classification": "READ_ONLY_VERIFICATION_OF_SEEN_HISTORY"}
    args.output.write_text(json.dumps(out, indent=2)+"\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
