"""Accept actual engineering results and current prerequisites, without a study fit."""

import json
import time
import xml.etree.ElementTree as ET

from quant.disk import check
from quant.paths import ROOT
from quant.research_v2 import load_protocol_v2, make_folds_v2, registration_binding, sha
from quant.resources import status


def main():
    destination = ROOT / "reports/A05_RESEARCH_PREFLIGHT_ACCEPTANCE.json"
    if destination.exists():
        raise RuntimeError("Preflight evidence exists; preserve original acceptance")
    test_files = ("A05_RESEARCH_PREFLIGHT_FINAL.xml", "A05_SOURCE_FREEZE_TEST.xml")
    results = []
    for name in test_files:
        path = ROOT / "reports" / name
        xml = ET.parse(path).getroot()
        if any(node.tag in {"failure", "error", "skipped"} for node in xml.iter()):
            raise RuntimeError("Engineering acceptance contains failure/error/skip")
        count = sum(1 for _ in xml.iter("testcase"))
        results.append({"file": name, "sha256": sha(path), "passed": count})
    if [result["passed"] for result in results] != [14, 1]:
        raise RuntimeError("Expected 14 core plus one actual source-freeze test")
    protocol = load_protocol_v2(ROOT / "configs/experiments/nonlinear_v2.json")
    lock = json.loads((ROOT / "state/dataset_lock.json").read_text())
    binding = registration_binding(protocol, lock["dataset_id"], input_frames={})
    if (ROOT / protocol["state_path"]).exists():
        raise RuntimeError("Preflight must be accepted before study registration")
    report = {
        "status": "ENGINEERING_PREFLIGHT_PASS", "created_us": time.time_ns() // 1000,
        "formal_market_model_fits": 0, "synthetic_native_engineering_fits": True,
        "formal_strategy_performance_evaluated": False,
        "locked_historical_test_read": False, "true_forward_days": 0,
        "tests": results, "folds": make_folds_v2(protocol), "maximum_cv_fits": 54,
        "source_hashes": binding["source_hashes"],
        "predecessor_receipts": binding["receipts"],
        "native_versions": binding["native_versions"],
        "protocol_sha256": binding["protocol_sha256"],
        "execution_lineage": binding["execution_lineage"],
        "resources": status(), "disk": check(),
    }
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "maximum_cv_fits": 54}), flush=True)


if __name__ == "__main__":
    main()
