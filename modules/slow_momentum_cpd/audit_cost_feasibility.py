"""Independent scalar Decimal audit from saved rows, without using the scorer."""
import argparse
import csv
import hashlib
import json
import math
from decimal import Decimal as D, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {2048: "slow-momentum-cpd-sharpe-continuation-20261011",
           1024: "slow-momentum-cpd-sharpe-20261011"}


def audit(output):
    worst, checks, row_counts = 0., 0, {}
    with localcontext() as context:
        context.prec = 40
        rate = D(str(.15 / math.sqrt(365)))
        for checkpoint, name in SOURCES.items():
            evidence = json.loads((output / ("RESULT.json" if checkpoint == 2048 else "HISTORY_REFERENCE.json")).read_text())
            source = ROOT / "research" / name / "results/POSITIONS.csv"
            assert hashlib.sha256(source.read_bytes()).hexdigest() == evidence["positions_sha256"]
            rows = list(csv.DictReader(source.open()))
            row_counts[checkpoint] = len(rows)
            for arm in ("trend", "trend_cpd"):
                for suffix in ("seed2001", "seed2002", "seed2003", "ensemble"):
                    policy, total = arm + "_" + suffix, {}
                    for block in evidence["blocks"]:
                        carry, gross, turnover, fee, spread, slip = [D(0)] * 5, D(0), D(0), D(0), D(0), D(0)
                        simple, previous = D(0), [D(0)] * 5
                        selected = [r for r in rows if r["block"] == block["start"]]
                        for i, row in enumerate(selected):
                            a = i % 5
                            if row["eligible"] == "0":
                                w, profit = D(0), D(0)
                            else:
                                vol = D(row["daily_vol"])
                                pos = (sum(D(row[f"{arm}_seed{s}"]) for s in (2001, 2002, 2003)) / 3
                                       if suffix == "ensemble" else D(row[policy]))
                                w = rate * pos / (vol * 5)
                                realized = D(row["scaled_next_return"]) * vol / rate
                                profit = w * realized
                            delta = w - carry[a]
                            amount, sign = abs(delta), D(1) if delta > 0 else D(-1) if delta < 0 else D(0)
                            turnover += amount
                            fee += D('.00055') * amount * (1 + sign * D('.0008'))
                            spread += D('.0004') * amount
                            slip += D('.0004') * amount
                            simple += abs(w - previous[a])
                            previous[a], carry[a] = w, w + profit
                            gross += profit
                        for a in range(5):
                            delta = -carry[a]
                            amount, sign = abs(delta), D(1) if delta > 0 else D(-1) if delta < 0 else D(0)
                            turnover += amount
                            fee += D('.00055') * amount * (1 + sign * D('.0008'))
                            spread += D('.0004') * amount
                            slip += D('.0004') * amount
                            simple += abs(previous[a])
                        cost = fee + spread + slip
                        actual = dict(gross_price_proxy=gross, drift_trade_turnover=turnover,
                                      fee=fee, half_spread=spread, slippage=slip, fixed_cost_total=cost,
                                      fixed_cost_adjusted_price_proxy=gross - cost, descriptive_target_turnover=simple,
                                      break_even_nominal_per_side_bps=gross / turnover * 10000)
                        for key, value in actual.items():
                            residual = abs(float(value) - block["policies"][policy][key])
                            worst = max(worst, residual)
                            assert residual < 1e-11, (checkpoint, block["start"], policy, key, residual)
                            checks += 1
                            if key != "break_even_nominal_per_side_bps":
                                total[key] = total.get(key, D(0)) + value
                    for key, value in total.items():
                        residual = abs(float(value) - evidence["aggregate"][policy][key])
                        worst = max(worst, residual)
                        assert residual < 1e-11
                        checks += 1
            original = json.loads((ROOT / "research" / name / "results/RESULT.json").read_text())
            for arm in ("trend", "trend_cpd"):
                expected = original["aggregate"][arm]["mean_daily_proxy_return"] * 483
                assert abs(expected - evidence["aggregate"][arm + "_ensemble"]["gross_price_proxy"]) < 1e-12
                checks += 1
    with (output / "DAILY.csv").open() as handle:
        daily = list(csv.DictReader(handle))
    assert len(daily) == 483 * 8
    primary = json.loads((output / "RESULT.json").read_text())
    for policy in primary["aggregate"]:
        for key in ("gross_price_proxy", "fixed_cost_adjusted_price_proxy"):
            value = sum(float(r[key]) for r in daily if r["policy"] == policy)
            residual = abs(value - primary["aggregate"][policy][key])
            worst = max(worst, residual)
            assert residual < 1e-11
            checks += 1
    return {"status": "PASS", "arithmetic": "INDEPENDENT_DECIMAL_SCALAR_LOOP_NO_SCORER_IMPORT",
            "checks": checks, "saved_rows_per_checkpoint": row_counts,
            "daily_rows": len(daily), "maximum_numeric_residual": worst,
            "new_model_inferences": 0, "training_updates": 0, "wallets": 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    value = audit(args.output)
    with (args.output / "AUDIT.json").open("x") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps(value))


if __name__ == "__main__":
    main()
