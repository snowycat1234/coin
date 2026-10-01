"""Read-only preservation audit for A03 integration; not alpha or module admission."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from quant.paths import ROOT
from quant.resources import status

LEGACY_SHA = "e01f836c9640a9fafd648600024237c7cd26e32e048d0a7ff8632e5cb7d5de2a"
STUDY_FILES = {
    "state/research_nonlinear_v2.json":
        "0ae0d1543e2b1516549226b6b83540a4933f7149c1024f72a56611120220f562",
    "reports/generated/A05_NONLINEAR_V2/summary.json":
        "ab173f29f5d0bf17a491cb9d5d23f795e63ce9acee050ccac8d8de7944dc14e6",
    "reports/A06_NONLINEAR_RESEARCH_ACCEPTANCE.json":
        "9f1c3df3dfd1bec98b4140bfaf9e9caa1199d0dafd2e9e7305ea1e5f35227c0d",
    "reports/A07_QUALITY_DIAGNOSTIC_ACCEPTANCE.json":
        "737264a53bacd2c78e33c971a6931fb411d54766da0d498f0588f46a7579c926",
}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def local(path):
    path = Path(path).resolve()
    check(path.is_relative_to(ROOT), "Audit paths must remain in D project")
    return path


def sha(path):
    digest = hashlib.sha256()
    with local(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1_048_576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    path = local(path)
    check(path.stat().st_size <= 2_000_000, "Oversize audit metadata")
    return json.loads(path.read_text(encoding="utf-8"))


def methods(path):
    tree = ast.parse(local(path).read_text(encoding="utf-8"))
    node = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                and node.name == "CandidatePaperEngine")
    return {node.name: ast.dump(node, include_attributes=False)
            for node in node.body if isinstance(node, ast.FunctionDef)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    check(len(args.xml) <= 4, "At most four actual test receipts")
    resources = status()  # Requires the shared bounded WSL scope.
    verified = {}
    for name, expected in STUDY_FILES.items():
        actual = sha(ROOT / name)
        check(actual == expected, f"Prior frozen study/receipt changed: {name}")
        verified[name] = actual
    registration = read_json(ROOT / "reports/generated/A05_NONLINEAR_V2/REGISTRATION.json")
    receipts = [registration, read_json(ROOT / "reports/PUBLIC_COLLECTOR_V3_ACCEPTANCE.json"),
                read_json(ROOT / "reports/A07_MICROSTRUCTURE_ACCEPTANCE.json"),
                read_json(ROOT / "reports/A07_QUALITY_DIAGNOSTIC_ACCEPTANCE.json")]
    for receipt in receipts:
        for name, expected in receipt["source_hashes"].items():
            actual = sha(ROOT / name)
            check(actual == expected, f"Unrelated frozen source changed: {name}")
            verified[name] = actual
    qa = receipts[-1]["actual_report"]
    check(sha(ROOT / qa["path"]) == qa["sha256"], "Actual QA evidence changed")
    old = ROOT / "legacy/a03_candidate_original" / LEGACY_SHA / "candidate_paper.py"
    check(sha(old) == LEGACY_SHA, "Legacy candidate archive changed")
    previous, current = methods(old), methods(ROOT / "src/quant/candidate_paper.py")
    unchanged = ["_append", "_fill", "_seal_days", "_cancel_pending"]
    for name in unchanged:
        check(previous[name] == current[name], f"Financial method AST changed: {name}")
    tests = []
    for path in args.xml:
        path = local(path)
        check(path.stat().st_size <= 1_000_000, "Oversize XML receipt")
        node = ET.parse(path).getroot()
        cases = list(node.iter("testcase"))
        check(bool(cases), "No actual test cases in XML")
        check(not any(list(case.iter(tag)) for case in cases
                      for tag in ("failure", "error", "skipped")), "Test gate not passed")
        tests.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path),
                      "cases": [{"class": case.get("classname"), "name": case.get("name")}
                                for case in cases]})
    report = {"status": "ANCILLARY_PRESERVATION_PASS", "verified_prior_files": verified,
              "legacy_source_sha256": LEGACY_SHA, "unchanged_financial_methods": unchanged,
              "test_receipts": tests, "resources": resources,
              "scope": "Unchanged old evidence/source/financial methods and actual XML only; "
                       "generic behavior, capacity and completeness need separate review.",
              "module_acceptance_granted": False, "alpha_eligible": False,
              "fits_executed": 0, "network_used": False, "orders_sent": 0,
              "audit_source_sha256": sha(Path(__file__))}
    if args.output:
        path = local(args.output)
        check(path.is_relative_to(ROOT / "reports") and path.suffix == ".json",
              "New evidence must remain in reports")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": report["status"], "prior_files": len(verified),
                      "unchanged_financial_methods": unchanged,
                      "test_cases": sum(len(item["cases"]) for item in tests)}))


if __name__ == "__main__":
    main()
