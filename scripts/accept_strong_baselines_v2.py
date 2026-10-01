"""Read-only acceptance of the already completed A02 reports and run-time bindings."""

import hashlib
import json

from quant.paths import ROOT


def main():
    folder = ROOT / "reports/generated/P03_STRONG_BASELINES_V2"
    summary_file = folder / "summary.json"
    actual = json.loads(summary_file.read_text())
    original = json.loads((ROOT / "reports/generated/P03_EXECUTION_V2/summary.json").read_text())
    resources = json.loads((folder / "RUN_RESOURCES.json").read_text())
    assert actual["A01"]["status"] == "PASS"
    assert actual["A01"]["source_hashes"]["src/quant/backtest.py"] == (
        "18b6defffbf6248c156695102aab80302ec146b0d1d8fb338b272588b319f89d"
    )
    identical = {}
    for name in ("B0", "B1", "B2"):
        identical[name] = all(
            actual["scenarios"][scenario]["baselines"][name]
            == original["baselines"][name][scenario]
            for scenario in ("base", "fee_x2", "slippage_x2")
        )
    assert all(identical.values())
    artifacts = sorted(folder.glob("*"))
    assert len([file for file in artifacts if file.name.endswith("_daily_nav.parquet")]) == 15
    metrics = [value for result in actual["scenarios"].values()
               for value in result["baselines"].values()]
    assert len(metrics) == 15
    assert all(value["canonical_latency"] and value["days"] == 1489 for value in metrics)
    assert all(value["execution_contract_version"] == "execution_v2" for value in metrics)
    assert resources["locked_month_file_reads"] == 0
    assert len(resources["minute_files"]) == 100
    assert all(file.split("/")[-1] < "2026-03.parquet" for file in resources["minute_files"])
    assert resources["resources"]["swap_bytes"] == 0
    evidence = {
        "module": "A02", "status": "PASS", "evidence_scope": "DEVELOPMENT_HISTORY",
        "output": str(folder.relative_to(ROOT)), "baseline_scenarios": 15,
        "days": 1489, "start_us": actual["config"]["start_us"],
        "end_us": actual["config"]["end_us"], "dataset_id": actual["dataset_id"],
        "summary_sha256": hashlib.sha256(summary_file.read_bytes()).hexdigest(),
        "baseline_implementation_sha256": actual["implementation_sha256"],
        "execution_contract_sha256": actual["A01"]["execution_contract_sha256"],
        "actual_execution_source_hashes": actual["A01"]["source_hashes"],
        "execution_binding_source": "A02 run summary embedded A01 receipt; not later disk source",
        "B0_B1_B2_same_as_A01_all_metrics": identical,
        "artifact_bytes": sum(file.stat().st_size for file in artifacts if file.is_file()),
        "seconds": resources["seconds"], "shared_resources": resources["resources"],
        "locked_month_file_reads": 0, "locked_historical_test_read": False,
        "alpha_candidate": False, "model_fits": 0, "true_forward_days": 0,
        "risk_limitation": "B1..B4 each have one exposed stale valuation day; observed daily MDD "
                           "cannot certify complete risk across the quarantined 2023 day",
    }
    destination = ROOT / "reports/A02_CANONICAL_ACCEPTANCE.json"
    if destination.exists():
        raise RuntimeError("Acceptance evidence already exists; do not overwrite")
    destination.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
