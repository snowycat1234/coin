"""Frozen five-arm CORE5 target builder; no price PnL or wallets.

The regression mode must reproduce the two original saved-year target packets
before the 366-day 2024 mode is admitted. Run from a checkout that contains the
public compatibility imports and risk_budget.py named below.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

DAY = 86_400_000_000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
ARMS = ("CS_MATCHED", "VOL_MATCHED", "STATIC50", "SMA200_10PCT", "EXACTHALF")
INPUT_SHA = {2023: "1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f",
             2024: "88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add",
             2025: "88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add"}
SAVED_SHA = {2023: ("e81bf92d3599a6d3059ab462ac984ed9cc066647b1ea839d6147d2e10c40359f",
                    "2047463e7be0ea4f086de744018d65924568dbd2e37f5960e75951c32746abf7"),
             2025: ("5e525cf65a5519a739d7ce2baf9c83809af44a1b9722f37fcf9891ede79bbf4e",
                    "595425c86df274c6c6105d058d478d772c75ae75cb9c6d2c3ca8c5b9b4c1d968")}
MODULE_SHA = {
    "scripts/research/public_cross_section_momentum_compat.py": "9ce46e0eecbf7891a28f5ae072eb735d0eea15a41b331ccf37fd637709404599",
    "scripts/research/cs_numpy_risk_compat.py": "edabc1283330db0dcc2cb9da1fc1f569110f2e02921592ed824597bfa580e7d0",
    "research/portfolio-risk-budget-20261012/risk_budget.py": "69de58ac83536dfbf1ec3715aadfa65da741c970c4cb5b417bb4c1e8062b19a6",
    "modules/transformer_v2/portfolio.py": "e4e02b0204e2861bb44eb78c8069b13a09edf6ca9390f3c86490d6e6f8a5e68b",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def us(year: int) -> int:
    return int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp() * 1_000_000)


def load_modules(repo: Path):
    # These import-only compatibility copies preserve the original signal/risk
    # equations while omitting an unused Polars API from the local target step.
    for path, expected in MODULE_SHA.items():
        if sha(repo / path) != expected:
            raise ValueError(f"Frozen original module SHA mismatch: {path}")
    sys.path.insert(0, str(repo))
    from scripts.research.public_cross_section_momentum_compat import public_targets
    from scripts.research.cs_numpy_risk_compat import signed_risk_weights
    p = repo / "research/portfolio-risk-budget-20261012/risk_budget.py"
    spec = importlib.util.spec_from_file_location("frozen_original_portfolio_risk_budget", p)
    risk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(risk)
    return public_targets, signed_risk_weights, risk.scale


def build(repo: Path, input_path: Path, year: int):
    if sha(input_path) != INPUT_SHA[year]:
        raise ValueError("Daily-close source SHA mismatch")
    with np.load(input_path, allow_pickle=False) as z:
        t = z["close_available_us"].copy()
        p = z["close"].copy()
        names = tuple(z["symbol_order"])
        if year in (2023, 2025):
            saved_decisions = z["decision_us"].copy()
        else:
            saved_decisions = None
    if names != SYMBOLS or p.shape != (len(t), 5) or np.any(np.diff(t) != DAY):
        raise ValueError("Original ordered, contiguous daily CORE5 history required")
    d = np.arange(us(year), us(year + 1), DAY, dtype=np.int64)
    if len(d) != (366 if year == 2024 else 365):
        raise ValueError("Gregorian full-year calendar mismatch")
    if saved_decisions is not None and not np.array_equal(d, saved_decisions):
        raise ValueError("Original saved-year decision calendar differs")
    public_targets, signed_risk_weights, risk_scale = load_modules(repo)
    cs, diagnostic = public_targets(p, t, d, SYMBOLS, SYMBOLS)
    eligible = np.asarray(diagnostic["current_eligible"], dtype=bool)
    means = pd.DataFrame(p).rolling(200, min_periods=200).mean().to_numpy()
    out = {arm: np.empty((len(d), 5), dtype=np.float64) for arm in ARMS}
    covs = np.empty((len(d), 5, 5), dtype=np.float64)
    proofs = []
    for i, at in enumerate(d):
        k = int(np.searchsorted(t, at))
        if (k < 199 or k >= len(t) or t[k] != at or not eligible[i].all()
                or np.any(np.diff(t[k-199:k+1]) != DAY)
                or not np.isfinite(p[k-199:k+1]).all()
                or np.any(p[k-199:k+1] <= 0)):
            raise ValueError(f"Original full-five 200-close admission failed: {at}")
        past = p[k-30:k+1]
        returns = np.diff(past, axis=0) / past[:-1]
        covariance = np.cov(returns, rowvar=False, ddof=1) * 365
        covs[i] = covariance
        sigma = lambda w: float(np.sqrt(max(0., w @ covariance @ w)))
        # Original unconditionally long VOL_MANAGED_HOLD is .6/K eligible
        # before its original risk downscale; full-five K=5 in this episode.
        hold, _ = signed_risk_weights(np.full(5, .6 / 5), returns)
        sc, sh = sigma(cs[i]), sigma(hold)
        if min(sc, sh) <= 0:
            raise ValueError(f"Nonzero full-five control covariance required: {at}")
        common = min(.10, sc, sh)
        old_cs = cs[i] * (common / sc)
        old_hold = hold * (common / sh)
        raw = {"CS_MATCHED": old_cs, "VOL_MATCHED": old_hold,
               "STATIC50": .5 * old_cs + .5 * old_hold}
        scale_proof = {}
        for arm in ("CS_MATCHED", "VOL_MATCHED", "STATIC50"):
            out[arm][i], scale_proof[arm] = risk_scale(raw[arm], covariance)
        # Exact original main signed_intents SMA column zero: use the number
        # of all eligible assets, including zero-direction members, in .6/K.
        columns = np.flatnonzero(np.all(np.isfinite(p[k-199:k+1]) & (p[k-199:k+1] > 0), axis=0))
        direction = np.sign(p[k, columns] - means[k, columns])
        sma = np.zeros(5, dtype=np.float64)
        sma[columns], _ = signed_risk_weights((.6 / len(columns)) * direction,
                                               returns[:, columns])
        out["SMA200_10PCT"][i] = sma
        out["EXACTHALF"][i] = .5 * out["STATIC50"][i] + .5 * sma
        for arm in ARMS:
            row = out[arm][i]
            if (not np.isfinite(row).all() or np.abs(row).max() > .30 + 1e-12
                    or np.abs(row).sum() > .60 + 1e-12):
                raise ValueError(f"Original target cap/finite failure: {arm}, {at}")
        if not np.allclose(covariance, covariance.T, atol=1e-12, rtol=0):
            raise ValueError("Asymmetric original covariance")
        proofs.append({"decision_us": int(at), "oldest_sma_close_available_us": int(t[k-199]),
                       "last_completed_close_available_us": int(t[k]),
                       "oldest_risk_close_available_us": int(t[k-30]),
                       "CS_original_sigma": sc, "HOLD_original_sigma": sh,
                       "common_matched_sigma": common,
                       "sized": scale_proof,
                       "estimated_sigma": {arm: sigma(out[arm][i]) for arm in ARMS}})
    return d, out, covs, proofs


def verify_history(repo: Path, inputs: Path, saved: Path):
    result = {}
    for year in (2023, 2025):
        d, arms, cov, _ = build(repo, inputs / f"Y{year}.npz", year)
        static_path = saved / f"STATIC50_Y{year}.npz"
        sma_path = saved / f"SMA200_Y{year}.npz"
        if (sha(static_path), sha(sma_path)) != SAVED_SHA[year]:
            raise ValueError("Original saved target packet hash mismatch")
        with np.load(static_path, allow_pickle=False) as s, np.load(sma_path, allow_pickle=False) as m:
            for arm in ("CS_MATCHED", "VOL_MATCHED", "STATIC50"):
                if not np.array_equal(arms[arm], s[arm]):
                    raise ValueError(f"{year} {arm} original target parity failed")
            if not np.array_equal(cov, s["annual_covariance"]):
                raise ValueError(f"{year} original covariance parity failed")
            if not np.array_equal(arms["SMA200_10PCT"], m["SMA200_10PCT"]):
                raise ValueError(f"{year} SMA200 original target parity failed")
        result[str(year)] = {"days": len(d), "arms": list(ARMS[:4]),
                             "status": "BIT_EXACT_ORIGINAL_TARGET_AND_COVARIANCE_PARITY"}
    return result


def prepare_2024(repo: Path, input_path: Path, output: Path):
    if output.exists():
        raise FileExistsError(output)
    d, arms, cov, proof = build(repo, input_path, 2024)
    output.mkdir(parents=True)
    np.savez_compressed(output / "Y2024_TARGETS.npz", decision_us=d,
                        symbol_order=np.asarray(SYMBOLS), annual_covariance=cov, **arms)
    (output / "Y2024_TARGET_PROOF.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
    summary = {"status": "PREPARED_NOT_ECONOMICALLY_SCORED", "year": 2024,
               "days": len(d), "arms": list(ARMS), "input_SHA256": INPUT_SHA[2024],
               "target_SHA256": sha(output / "Y2024_TARGETS.npz"),
               "proof_SHA256": sha(output / "Y2024_TARGET_PROOF.json"),
               "last_day": int(d[-1]), "first_day": int(d[0])}
    (output / "Y2024_TARGET_MANIFEST.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--saved", type=Path, required=True)
    parser.add_argument("--verify-history", action="store_true")
    parser.add_argument("--prepare-2024", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify_history:
        print(json.dumps(verify_history(args.repo, args.inputs, args.saved)))
    if args.prepare_2024:
        if args.output is None:
            parser.error("--output required for --prepare-2024")
        print(json.dumps(prepare_2024(args.repo, args.inputs / "Y2025.npz", args.output)))
