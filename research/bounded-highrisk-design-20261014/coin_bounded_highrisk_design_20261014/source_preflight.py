"""Code identities only; no market path, transport, or historical loader."""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import sys
import types

HERE = Path(__file__).resolve().parent
FROZEN_FILES = {
    "ACCOUNT_EXTENSION.diff", "SOURCE_PINS.json", "PROTOCOL.json", "NATIVE_HARDCODE_MAP.json",
    "README.md", "bounded_policy.py", "toy_fixtures.py", "source_preflight.py", "run_toy.py",
    "run_bounded_checks.py", "test_bounded_highrisk.py", "vendor_quant/__init__.py",
    "vendor_quant/perpetual_account.py", "vendor_quant/execution_contract.py",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    freeze_path = HERE / "SOURCE_FREEZE.json"
    if not freeze_path.is_file():
        raise ValueError("The exact source freeze is required; unfrozen toy launch is forbidden")
    freeze = json.loads(freeze_path.read_text())
    hashes = freeze.get("source_files_SHA256") if isinstance(freeze, dict) else None
    if (not isinstance(hashes, dict) or set(hashes) != FROZEN_FILES
            or freeze.get("version") != "H090_SYNTHETIC_FREEZE_V2"
            or any(not isinstance(v, str) or len(v) != 64
                   or any(c not in "0123456789abcdef" for c in v) for v in hashes.values())):
        raise ValueError("Complete valid V2 freeze schema and exact source hash set required")
    for name, expected in hashes.items():
        if sha(HERE / name) != expected:
            raise ValueError("Frozen higher-risk source changed: " + name)
    pins = json.loads((HERE / "SOURCE_PINS.json").read_text())
    for name, pin in pins.items():
        original = HERE.parent / pin["source_path"]
        copy = HERE / "vendor_quant" / name
        if sha(original) != pin["original_sha256"] or sha(copy) != pin["prototype_sha256"]:
            raise ValueError("Source or prototype hash mismatch: " + name)
    original = HERE.parent / pins["perpetual_account.py"]["source_path"]
    before = original.read_text()
    after = (HERE / "vendor_quant" / "perpetual_account.py").read_text()
    needle = 'or not 0 < self.max_gross_weight <= D("0.6")'
    if before.count(needle) != 1 or before.replace(needle, needle.replace('"0.6"', '"0.9"')) != after:
        raise ValueError("The only permitted account diff is the gross validation bound")
    diff = "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                    fromfile="original/perpetual_account.py", tofile="vendor_quant/perpetual_account.py"))
    if diff != (HERE / "ACCOUNT_EXTENSION.diff").read_text():
        raise ValueError("Reviewable diff mismatch")
    protocol = json.loads((HERE / "PROTOCOL.json").read_text())
    from bounded_policy import FiniteAddsPlan
    plan = FiniteAddsPlan()
    declared = protocol["finite_program"]
    if (declared["symbol"] != plan.symbol or declared["direction"] != "LONG"
            or declared["initial_order_margin_USDT"] != str(plan.initial_order_margin)
            or declared["margin_multiplier"] != str(plan.margin_multiplier)
            or declared["maximum_adds"] != plan.maximum_adds
            or declared["total_original_sleeve_investment_USDT"] != str(plan.total_sleeve_investment)
            or declared["planned_order_margins_USDT"] != [str(v) for v in plan.margins()]):
        raise ValueError("Fixed candidate parameters differ from protocol")
    return dict(status="SYNTHETIC_CODE_ONLY", historical_runs=0, market_reads=0,
                original_finance_methods_unchanged=True,
                gross_validation_extension=".60 -> .90, separate vendor namespace",
                source_freeze_SHA256=sha(freeze_path),
                pins=pins)


def original_account_module():
    """Load the pinned original under a distinct namespace for parity tests."""
    verify()
    pins = json.loads((HERE / "SOURCE_PINS.json").read_text())
    root = (HERE.parent / pins["perpetual_account.py"]["source_path"]).parent
    package = "_bounded_highrisk_original_quant"
    if package + ".perpetual_account" in sys.modules:
        return sys.modules[package + ".perpetual_account"]
    namespace = types.ModuleType(package)
    namespace.__path__ = [str(root)]
    sys.modules[package] = namespace
    for name in ("execution_contract", "perpetual_account"):
        spec = importlib.util.spec_from_file_location(package + "." + name, root / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return sys.modules[package + ".perpetual_account"]


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
