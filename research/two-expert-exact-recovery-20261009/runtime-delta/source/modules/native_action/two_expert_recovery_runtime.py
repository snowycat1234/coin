"""Explicit provenance portability for the unchanged exact two-expert runtime.

Only direct.source_hashes is temporarily adapted. Its historical flat identity
is accompanied by a separate current-byte manifest, never represented as proof
that unavailable auxiliary source bytes were checked. No fit runs on import.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys

CORE_SHA256 = {
    "modules/native_action/two_expert_direct.py": "f4797892c07c73a7516676c060aeef9f89168b4ee60c0ad34f36bfa51a6f0442",
    "modules/direct_path/prototype.py": "46a0ca0b76bf29d50133bdd85b5730f4fd029f05378ce2ef086752b869a8fcab",
    "modules/direct_path/training.py": "35a3673f4bc5cbf1ff8ebe5ac1575b2236ab09744253720d27844cc2150ded7b",
    "modules/direct_path/data_adapter.py": "8c031a14360428b2c9ca1f6a97d7f8c09753f879db3353a1fef729d6d3e4be95",
}
AUXILIARY_SHA256 = {
    "modules/native_action/e5_inputs.py": "adbca6a18ff9f4709eb7f3ccb2fedb331cd1f6f2d96100d8778efba979b713f2",
    "scripts/research/conditional_selector_core.py": "c0a086ba583dfe4f059b8942988ec2209ac767e4cfe59699f06e804b94890533",
    "scripts/investment/regime_ranking_screen.py": "b53242077d36b6542a1c2c5684f39f2dce6574841e20b7787fdd06c9b84aebf2",
}
ADEQUACY_PATH = "modules/native_action/two_expert_adequacy.py"
ADEQUACY_SHA256 = "03ce8a450b1775f931a360394656a78accd153bb4553cccade15bfff8b7c2b93"
HISTORICAL_SHA256 = dict(CORE_SHA256, **AUXILIARY_SHA256)
IMPORTED_SHA256 = dict(CORE_SHA256, **{ADEQUACY_PATH: ADEQUACY_SHA256})
MODULE_PATHS = {path[:-3].replace("/", "."): path for path in IMPORTED_SHA256}
AUXILIARY_MODULES = {path[:-3].replace("/", ".") for path in AUXILIARY_SHA256}
ROOT = Path(__file__).resolve().parents[2]
STANDARD_IMPORTS = {"__future__", "argparse", "hashlib", "json", "os", "pathlib",
                    "resource", "time", "numpy", "datetime", "dataclasses", "gzip"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_hash(record):
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _relative(path, root):
    return Path(os.path.relpath(Path(path).resolve(), Path(root).resolve())).as_posix()


def current_source_manifest(root=ROOT, auxiliary_root=None):
    """Verify every present source; label missing historical helpers explicitly."""
    root = Path(root).resolve()
    auxiliary_root = root.parent / "auxiliary" if auxiliary_root is None else Path(auxiliary_root).resolve()
    entries = {}
    for path, expected in IMPORTED_SHA256.items():
        actual = root / path
        if not actual.is_file() or sha(actual) != expected:
            raise ValueError("Exact imported computational source required: " + path)
        entries[path] = dict(status="VERIFIED_PRESENT", role="IMPORTED_COMPUTATIONAL_SOURCE",
            expected_SHA256=expected, verified_SHA256=expected, bytes_verified=True,
            source_locations=[path], imported_for_runtime=True)
    for path, expected in AUXILIARY_SHA256.items():
        candidates = list(dict.fromkeys((root / path, auxiliary_root / path)))
        found = []
        for candidate in candidates:
            if candidate.exists():
                if not candidate.is_file() or sha(candidate) != expected:
                    raise ValueError("Present historical auxiliary source has wrong bytes: " + path)
                found.append(_relative(candidate, root))
        entry = dict(role="HISTORICAL_PROVENANCE_ONLY", expected_SHA256=expected,
                     imported_for_runtime=False, bytes_verified=bool(found),
                     source_locations=found)
        if found:
            entry.update(status="VERIFIED_PRESENT", verified_SHA256=expected)
        else:
            entry.update(status="UNAVAILABLE_HISTORICAL_PROVENANCE_ONLY",
                         unavailable_bytes_verified=False,
                         searched_locations=[_relative(candidate, root) for candidate in candidates])
        entries[path] = entry
    return dict(schema="TWO_EXPERT_CURRENT_SOURCE_MANIFEST_V1", sources=entries,
        historical_flat_identity=HISTORICAL_SHA256,
        historical_identity_is_not_current_byte_verification=True,
        auxiliary_sources_are_not_computational_imports=True,
        optimizer_source_SHA256=ADEQUACY_SHA256)


def _verify_import_graph(root):
    """The pinned sources may import only their declared core and standard dependencies."""
    allowed_modules = set(MODULE_PATHS)
    for module, relative in MODULE_PATHS.items():
        tree = ast.parse((root / relative).read_text(), filename=relative)
        package = module.rsplit(".", 1)[0]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    base = importlib.util.resolve_name("." * node.level + base, package)
                if base == "modules.native_action":
                    imported = [base + "." + alias.name for alias in node.names]
                else:
                    imported = [base]
            else:
                continue
            for name in imported:
                if name not in allowed_modules and name.split(".", 1)[0] not in STANDARD_IMPORTS:
                    raise ValueError("Unexpected computational import in " + relative + ": " + name)
    # These namespace-package parents must not execute an unbound initializer.
    for relative in ("modules/__init__.py", "modules/native_action/__init__.py",
                     "modules/direct_path/__init__.py"):
        path = root / relative
        if path.is_file():
            body = ast.parse(path.read_text(), filename=relative).body
            if any(not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)) for node in body):
                raise ValueError("Unexpected executable package initializer: " + relative)


def _verify_loaded_modules(root):
    for name, module in tuple(sys.modules.items()):
        if name in AUXILIARY_MODULES:
            raise ValueError("Historical auxiliary must not be imported for fitting: " + name)
        if not name.startswith("modules.") or name in ("modules.native_action", "modules.direct_path"):
            continue
        path = getattr(module, "__file__", None)
        if name == "modules.native_action.two_expert_recovery_runtime":
            expected = root / "modules/native_action/two_expert_recovery_runtime.py"
            if path is None or Path(path).resolve() != expected or sha(path) != sha(__file__):
                raise ValueError("Imported recovery wrapper source identity differs from current wrapper")
            continue
        if name in MODULE_PATHS:
            if path is None or Path(path).resolve() != root / MODULE_PATHS[name]:
                raise ValueError("Imported computational module came from another source: " + name)
        elif path is not None and Path(path).resolve().is_relative_to(root):
            raise ValueError("Unexpected imported computational source module: " + name)


def _snapshot_callables(modules):
    return {(name, key): value for name, module in modules.items()
            for key, value in vars(module).items() if callable(value) and key != "source_hashes"}


def _assert_callables_unchanged(modules, snapshot):
    current = _snapshot_callables(modules)
    if current.keys() != snapshot.keys() or any(current[key] is not value for key, value in snapshot.items()):
        raise ValueError("Computational function/class objects changed during recovery binding")


@contextmanager
def bound_runtime(root=ROOT, auxiliary_root=None):
    """Temporarily adapt only source_hashes; preserve all computational objects."""
    root = Path(root).resolve()
    manifest = current_source_manifest(root, auxiliary_root)
    _verify_import_graph(root)
    _verify_loaded_modules(root)
    modules = {name: importlib.import_module(name) for name in MODULE_PATHS}
    _verify_loaded_modules(root)
    direct = modules["modules.native_action.two_expert_direct"]
    adequacy = modules["modules.native_action.two_expert_adequacy"]
    snapshot = _snapshot_callables(modules)
    original = direct.source_hashes
    wrapper_sha = sha(__file__)

    def verified_historical_source_hashes():
        if sha(__file__) != wrapper_sha or current_source_manifest(root, auxiliary_root) != manifest:
            raise ValueError("Recovery runtime/source manifest changed during execution")
        _verify_loaded_modules(root)
        _assert_callables_unchanged(modules, snapshot)
        return dict(HISTORICAL_SHA256)

    direct.source_hashes = verified_historical_source_hashes
    try:
        yield dict(direct=direct, adequacy=adequacy, manifest=manifest,
                   manifest_SHA256=canonical_hash(manifest), wrapper_SHA256=wrapper_sha,
                   root=root, verify=verified_historical_source_hashes)
        verified_historical_source_hashes()
    finally:
        direct.source_hashes = original
        _assert_callables_unchanged(modules, snapshot)


def binding_record(runtime):
    return dict(schema="TWO_EXPERT_RECOVERY_RUNTIME_V1",
        wrapper_source_SHA256=runtime["wrapper_SHA256"],
        current_source_manifest_SHA256=runtime["manifest_SHA256"],
        current_source_manifest=runtime["manifest"],
        sole_runtime_override="modules.native_action.two_expert_direct.source_hashes",
        original_computational_function_objects_preserved=True,
        missing_auxiliary_bytes_claimed_verified=False,
        original_source_and_output_metadata_unchanged=True)


def _exclusive_json(path, record):
    with Path(path).open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _original_output_files(output):
    return {path.name: sha(path) for path in sorted(Path(output).iterdir())
            if path.is_file() and not path.name.startswith("RECOVERY_RUNTIME")
            and not path.name.endswith(".RECOVERY_BINDING.json")}


def _write_post_bindings(output, pre_receipt, runtime, *, success):
    output = Path(output)
    files = _original_output_files(output)
    record = binding_record(runtime)
    record.update(status="PASS_UNCHANGED_CONTINUATION_AND_PROXY_BOUND" if success else "FAILED_NO_NATIVE",
                  pre_fit_receipt=pre_receipt.name, pre_fit_receipt_SHA256=sha(pre_receipt),
                  original_output_file_SHA256=files)
    for name, original_sha in files.items():
        _exclusive_json(output / (name + ".RECOVERY_BINDING.json"), dict(
            schema="TWO_EXPERT_RECOVERY_OUTPUT_BINDING_V1", status=record["status"],
            original_file=name, original_file_SHA256=original_sha,
            current_source_manifest_SHA256=runtime["manifest_SHA256"],
            wrapper_source_SHA256=runtime["wrapper_SHA256"],
            pre_fit_receipt_SHA256=record["pre_fit_receipt_SHA256"]))
    target = output / ("RECOVERY_RUNTIME.json" if success else "RECOVERY_RUNTIME_FAILED.json")
    _exclusive_json(target, record)
    return record


def verify_completed_output(output, *, root=ROOT, auxiliary_root=None):
    """Read-only gate for consumers; FIT_READY alone is insufficient in recovery mode."""
    output = Path(output).resolve()
    if (output / "FIT_FAILED.json").exists() or (output / "RECOVERY_RUNTIME_FAILED.json").exists():
        raise ValueError("Failed continuation/proxy run cannot reach native validation")
    record = json.loads((output / "RECOVERY_RUNTIME.json").read_text())
    pre = output.parent / (output.name + "_RECOVERY_RUNTIME.json")
    manifest = current_source_manifest(root, auxiliary_root)
    if (record.get("status") != "PASS_UNCHANGED_CONTINUATION_AND_PROXY_BOUND"
            or record.get("wrapper_source_SHA256") != sha(__file__)
            or record.get("current_source_manifest") != manifest
            or record.get("current_source_manifest_SHA256") != canonical_hash(manifest)
            or record.get("pre_fit_receipt_SHA256") != sha(pre)):
        raise ValueError("Exact successful recovery pre/post manifest binding required")
    pre_record = json.loads(pre.read_text())
    if (pre_record.get("wrapper_source_SHA256") != record["wrapper_source_SHA256"]
            or pre_record.get("current_source_manifest") != manifest):
        raise ValueError("Pre-fit runtime binding differs from terminal runtime binding")
    files = _original_output_files(output)
    if files != record.get("original_output_file_SHA256"):
        raise ValueError("Original continuation outputs changed after recovery binding")
    required = {"FIT_STARTED.json", "FIT_READY.json", "OPTIMIZER_RECOVERY.json", "VALIDATION_RESULTS.json"}
    for arm in ("NO_CASH", "WITH_CASH"):
        required.update({arm + suffix for suffix in (".npz", "_MODEL.json", "_ADAM.npz",
                         "_RECOVERED_ADAM64.npz", "_TRAINING.jsonl", "_VALIDATION_REQUESTS.npz")})
    if not required.issubset(files):
        raise ValueError("Complete unchanged continuation and proxy output files required")
    for name, original_sha in files.items():
        bound = json.loads((output / (name + ".RECOVERY_BINDING.json")).read_text())
        if (bound.get("original_file_SHA256") != original_sha
                or bound.get("status") != record["status"]
                or bound.get("wrapper_source_SHA256") != record["wrapper_source_SHA256"]
                or bound.get("current_source_manifest_SHA256") != record["current_source_manifest_SHA256"]
                or bound.get("pre_fit_receipt_SHA256") != record["pre_fit_receipt_SHA256"]):
            raise ValueError("Exact recovery binding sidecar required: " + name)
    validation = json.loads((output / "VALIDATION_RESULTS.json").read_text())
    if validation.get("status") != "PASS_FIXED_TWO_CONTINUATIONS_PROXY_VALIDATION_ONLY":
        raise ValueError("Successful unchanged proxy receipt required")
    return record


def check(pack, expected_index_sha256, frozen_fit, *, root=ROOT, auxiliary_root=None):
    with bound_runtime(root, auxiliary_root) as runtime:
        result = runtime["adequacy"].check(pack, expected_index_sha256, frozen_fit)
        result["recovery_runtime"] = binding_record(runtime)
        return result


def continue_fixed_pair(pack, expected_index_sha256, frozen_fit, output, *, root=ROOT, auxiliary_root=None):
    output, pack = Path(output).resolve(), Path(pack).resolve()
    if output != pack.parent / "two_expert_direct_adequacy_fit" or output.exists():
        raise ValueError("Exclusive nonexistent sibling continuation output required")
    with bound_runtime(root, auxiliary_root) as runtime:
        pre = output.parent / (output.name + "_RECOVERY_RUNTIME.json")
        _exclusive_json(pre, dict(binding_record(runtime), status="PRE_FIT_SOURCE_MANIFEST_BOUND"))
        try:
            result = runtime["adequacy"].continue_fixed_pair(pack, expected_index_sha256, frozen_fit, output)
            runtime["verify"]()
            _write_post_bindings(output, pre, runtime, success=True)
            verify_completed_output(output, root=root, auxiliary_root=auxiliary_root)
            result["recovery_runtime"] = binding_record(runtime)
            result["recovery_runtime_receipt_SHA256"] = sha(output / "RECOVERY_RUNTIME.json")
            return result
        except Exception:
            if output.is_dir() and not (output / "RECOVERY_RUNTIME.json").exists():
                _write_post_bindings(output, pre, runtime, success=False)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "continue"))
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--index-sha256", required=True)
    parser.add_argument("--frozen-fit", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--auxiliary-root", type=Path)
    args = parser.parse_args()
    if args.mode == "check":
        if args.output is not None:
            parser.error("check is read-only and takes no output directory")
        result = check(args.pack, args.index_sha256, args.frozen_fit, auxiliary_root=args.auxiliary_root)
    else:
        if args.output is None:
            parser.error("continue requires the exclusive continuation output directory")
        result = continue_fixed_pair(args.pack, args.index_sha256, args.frozen_fit, args.output,
                                     auxiliary_root=args.auxiliary_root)
    print(json.dumps(result, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
