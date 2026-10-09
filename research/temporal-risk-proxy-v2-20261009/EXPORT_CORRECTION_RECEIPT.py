"""Export read-only correction evidence; no models, wallets or optimizer updates."""

import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = Path("/workspace/coin-state/work/temporal-two-expert-20261009")
TESTS = Path("/workspace/coin-state/tests/temporal-two-expert-20261009")
DEST = Path(__file__).resolve().parent
PARENT = "a6a0b03fb7993e10304ffdbe3b678f2f50e30f2b"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (DEST / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def test_summary(path):
    node = ET.parse(path).getroot()
    suites = list(node.iter("testsuite"))
    return dict(
        tests=sum(int(s.get("tests", 0)) for s in suites),
        failed=sum(int(s.get("failures", 0)) for s in suites),
        errors=sum(int(s.get("errors", 0)) for s in suites),
        skipped=sum(int(s.get("skipped", 0)) for s in suites),
        pytest_seconds=sum(float(s.get("time", 0)) for s in suites),
        junit_SHA256=sha(path),
    )


def main():
    original_sources = sorted((ROOT / "modules/temporal_two_expert").glob("*.py")) + [
        ROOT / "modules/collector_research/pipeline/make_labels.py",
        ROOT / "modules/collector_research/pipeline/train.py",
        ROOT / "src/quant/perpetual_account.py",
        ROOT / "src/quant/bybit_isolated_account.py",
        ROOT / "scripts/investment/resumable_perpetual.py",
        ROOT / "scripts/investment/perpetual_directional.py",
    ]
    old_hashes = {}
    for path in original_sources:
        name = str(path.relative_to(ROOT))
        old = subprocess.check_output(["git", "show", PARENT + ":" + name], cwd=ROOT)
        assert old == path.read_bytes(), name
        old_hashes[name] = sha(path)
    archive = ROOT / "research/temporal-four-fit-20261009/results/TERMINAL_MODELS_ADAM_RNG.zip"
    members = {}
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for member in z.namelist():
            payload = z.read(member)
            local = STATE / "four-fit" / member
            assert local.read_bytes() == payload, member
            members[member] = hashlib.sha256(payload).hexdigest()
    write(
        "ORIGINAL_PRESERVATION.json",
        dict(
            parent_commit=PARENT,
            original_source_SHA256=old_hashes,
            original_sources_unchanged=True,
            all_archived_terminal_files_match_live_bytes=True,
            original_archive_SHA256=sha(archive),
            original_member_SHA256=members,
            optimizer_updates=0,
            checkpoint_rewrites=0,
            original_arm_steps=[132, 143, 349, 522],
        ),
    )
    transfers = {
        "NUMERICAL_RECEIPT.json": STATE / "CHARGED_WITNESS_PUBLISHED.json",
        "EXECUTION_AVAILABILITY.json": STATE / "EXECUTION_AVAILABILITY.json",
        "CORRECTION_TEST_RESOURCES.json": TESTS / "CHARGED_CORRECTION_FINAL_RESOURCES.json",
        "ORIGINAL_TEST_RESOURCES.json": TESTS / "ORIGINAL_REGRESSION_RESOURCES.json",
        "WITNESS_RESOURCES.json": TESTS / "CHARGED_WITNESS_PUBLISHED_RESOURCES.json",
        "AVAILABILITY_RESOURCES.json": TESTS / "EXECUTION_AVAILABILITY_RESOURCES.json",
    }
    for name, source in transfers.items():
        shutil.copyfile(source, DEST / name)
    sources = sorted(p for p in (ROOT / "modules/temporal_risk_proxy_v2").iterdir() if p.is_file())
    new = test_summary(TESTS / "charged-correction-final.xml")
    old = test_summary(TESTS / "original-regression.xml")
    assert new["tests"] == 15 and old["tests"] == 62
    assert new["failed"] + new["errors"] + old["failed"] + old["errors"] == 0
    write(
        "TEST_RECEIPT.json",
        dict(
            schema="CHARGED_RISK_PROXY_TEST_RECEIPT_V1",
            status="PASS_SURROGATE_NATIVE_RESUME_BLOCKED",
            tests=dict(correction=new, original_regression=old, total_passed=77),
            source_SHA256={str(p.relative_to(ROOT)): sha(p) for p in sources},
            exporter_SHA256=sha(Path(__file__)),
            no_dependency_installation=True,
            prototype_unchanged=True,
            original_checkpoints_unchanged=True,
            parameter_counts=dict(
                GRU64_NO_CASH=13057,
                GRU64_WITH_CASH=13090,
                LATEST_MLP_NO_CASH=12993,
                LATEST_MLP_WITH_CASH=13026,
            ),
            reference_parity=dict(
                dates=182,
                NAV_atol=1e-9,
                utility_atol=2e-14,
                target_and_request_gradient_rtol=5e-11,
                target_and_request_gradient_atol=5e-13,
                scope="Unchanged fixed VOL/CS requests; no mandatory reduction",
            ),
            tested=[
                "gross and asset active-branch finite differences",
                "explicit cap equality/violation",
                "partial capacity costs, frozen intent and unresolved expiry",
                "actual native latency, partial closes, funding ties and priority",
                "same endpoint/different intraday native order counterexample",
                "182 original reference NAV/utility/request-gradient parity",
                "saved failed stochastic path, charged reduction and request/neural VJP",
                "original causal/mask/scaler/serialization/Adam/RNG/atomic tests",
            ],
            native_synthetic_scope=(
                "Actual unchanged scheduler methods and BybitIsolatedAccount; "
                "no historical minute replay"
            ),
            gradient_scope=(
                "Exact for declared continuous daily-boundary surrogate, away from "
                "discontinuities; not minute-native gradients"
            ),
            initial_test_failure=(
                "1GB address-space could not map the full native PyArrow dependency stack; "
                "full unchanged imports passed under the already authorized 2GB comparison launcher"
            ),
            fresh_corrected_fits=0,
            resumed_optimizer_updates=0,
            historical_native_wallets=0,
            missing_for_native_resume=[
                "source-bound minute trade opens, minute marks and preceding-minute quote volumes",
                "implemented native-time differentiated contract and parity tests",
            ],
        ),
    )
    print(
        json.dumps(
            dict(
                status="EXPORTED_READ_ONLY", files=len(transfers) + 2, tests=77, optimizer_updates=0
            )
        )
    )


if __name__ == "__main__":
    main()
