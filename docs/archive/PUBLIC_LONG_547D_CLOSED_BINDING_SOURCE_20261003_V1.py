"""Close D033 small task/code evidence only; never read market artifacts."""
from datetime import UTC, datetime
import argparse, hashlib, json, os, sys
from pathlib import Path
ROOT = Path("/mnt/d/codex/coin")
STATE = Path("/home/xflops/coin-state")
LIMIT = 2_000_000
OUTPUT = "reports/GITHUB_PUBLIC_LONG_547D_SOURCE_BINDING_20261003_V1.json"
ARCHIVE = "docs/archive/PUBLIC_LONG_547D_CLOSED_BINDING_SOURCE_20261003_V1.py"
META = "docs/archive/PUBLIC_LONG_547D_USED_ACTUAL_METADATA_20261003_V1"
ROLES = ("SOURCE", "TINY", "RESEARCH", "INDEPENDENT", "ROOT")
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ordinary(path):
    path = Path(path)
    assert path.is_file() and not path.is_symlink() and path.stat().st_size <= LIMIT, str(path)
    return path


def project(relative):
    path = ROOT / relative
    assert not Path(relative).is_absolute() and path.resolve().is_relative_to(ROOT)
    assert relative in ("state/dataset_lock.json", "configs/dataset_policy.json") or relative.startswith(
        ("scripts/", "src/", "tests/", "protocols/", "environments/", "third_party/", "docs/archive/", "reports/"))
    assert path.suffix in (".py", ".ps1", ".json", ".xml", ".md", ".toml", ".lock", ".sh") or path.name.endswith("LICENSE")
    return ordinary(path)


def small(path):
    return json.loads(ordinary(path).read_bytes())


def field(value, keys):
    for key in keys:
        value = value[key]
    return value


def closed(identity, expected=0):
    assert isinstance(identity, str) and len(identity) == 32 and all(c in "0123456789abcdef" for c in identity)
    path = STATE / "task-progress" / ("task-" + identity + ".json")
    value = small(path)
    assert value["id"] == identity and type(value["exit_code"]) is int and value["exit_code"] == expected
    assert value["status"] == ("completed" if expected == 0 else "failed")
    return path, value


def exact(origin, relative, digest):
    origin = ordinary(origin)
    assert origin.resolve().is_relative_to(STATE) or origin.resolve().is_relative_to(ROOT)
    assert sha(origin) == digest
    target = ROOT / relative
    assert relative.startswith(META + "/") and target.resolve().is_relative_to(ROOT / META)
    assert origin.suffix in (".py", ".ps1", ".json", ".xml", ".md", ".toml", ".lock", ".sh") or origin.name.endswith("LICENSE")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(origin.read_bytes())
    assert sha(target) == digest
    return digest


def owned_sizes(plan):
    paths = [Path(value) for value in plan["owned_STATE_directories"]]
    assert paths and len(paths) == len(set(paths)) and plan["maximum_owned_STATE_bytes"] == 400_000_000
    records = []
    for path in paths:
        assert path.parent == STATE and path.is_dir() and not path.is_symlink()
        count = total = 0
        for current, directories, files in os.walk(path, followlinks=False):
            for name in directories:
                assert not (Path(current) / name).is_symlink()
            for name in files:
                item = Path(current) / name
                assert item.is_file() and not item.is_symlink()
                total += item.stat().st_size
                count += 1
        records.append(dict(path=str(path), bytes=total, files=count))
    total = sum(value["bytes"] for value in records)
    assert total <= plan["maximum_owned_STATE_bytes"], total
    return dict(scope="EXPLICIT_D033_OWNED_DIRECTORIES_FILE_STAT_ONLY_NO_ARRAYS_OR_ROOT_SCAN", directories=records,
        total_owned_bytes=total, maximum_owned_bytes=plan["maximum_owned_STATE_bytes"])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    args = parser.parse_args()
    plan_path = args.binding.resolve()
    assert plan_path.parent == ROOT / "protocols" and not (ROOT / OUTPUT).exists()
    plan = small(plan_path)
    assert plan["classification"] == "CLOSED_SMALL_METADATA_ONLY_NOT_MARKET_REPLAY" and plan["ready_to_execute"] is True
    assert sha(__file__) == plan["exporter_sha256"] == sha(project(ARCHIVE))
    assert plan["metadata_archive_dir"] == META and plan["output"] == OUTPUT
    assert tuple(plan["roles"]) == ROLES and os.environ.get("COIN_TASK_ID")
    assert Path(sys.prefix).resolve() == STATE / "v8-clean-env-20261002-v2"
    from quant import resources
    resource_before = resources.status()
    assert resource_before["ram_limit_bytes"] <= 5_000_000_000 and resource_before["swap_bytes"] == 0 and not resource_before["gpu_used"]
    ownership_before = owned_sizes(plan)
    hashes = {str(plan_path.relative_to(ROOT)): sha(plan_path), ARCHIVE: sha(project(ARCHIVE))}
    assert tuple(item["role"] for item in plan["contracts"]) == ("SOURCE", "RESEARCH")
    contracts = {}
    for contract in plan["contracts"]:
        path = project(contract["path"])
        assert sha(path) == contract["sha256"]
        spec = small(path)
        contracts[contract["role"]] = (contract, spec)
        if contract["role"] == "SOURCE":
            assert len(spec["frozen_sources"]) == 11 and spec["source_files"] == 38
        for relative, digest in spec["frozen_sources"].items():
            assert sha(project(relative)) == digest
            assert relative not in hashes or hashes[relative] == digest
            hashes[relative] = digest
        hashes[contract["path"]] = contract["sha256"]
    receipts, tasks, copies = {}, [], []
    for role in ROLES:
        item = plan["roles"][role]
        path = project(item["report"])
        assert sha(path) == item["report_sha256"]
        receipt = small(path)
        assert receipt["status"] == item["required_status"]
        identity = field(receipt, item["task_id_field"])
        assert identity == item["expected_task_id"]
        task_path, task = closed(identity)
        tasks.append(dict(role=role, task_id=identity, actual_exit_code=0,
            archived_task=META + "/" + role + "_TASK_ACTUAL.json", task_sha256=sha(task_path)))
        copies.append((task_path, tasks[-1]["archived_task"], sha(task_path)))
        hashes[item["report"]] = item["report_sha256"]
        if item.get("run_binding"):
            path = ordinary(item["run_binding"])
            assert path.resolve().is_relative_to(STATE) and sha(path) == item["run_binding_sha256"]
            binding = small(path)
            assert binding["task_id"] == identity
            if "run_binding_sha256" in receipt:
                assert receipt["run_binding_sha256"] == item["run_binding_sha256"]
            copies.append((path, META + "/" + role + "_RUN_BINDING.json", item["run_binding_sha256"]))
        receipts[role] = receipt
    assert len({t["task_id"] for t in tasks}) == 5
    source_contract, source_spec = contracts["SOURCE"]
    research_contract, research_spec = contracts["RESEARCH"]
    assert plan["source_receipt_sha256"] == plan["roles"]["SOURCE"]["report_sha256"] == research_spec["source_receipt_sha256"]
    assert plan["research_protocol_sha256"] == research_contract["sha256"]
    assert receipts["SOURCE"]["binding"]["protocol_sha256"] == source_contract["sha256"]
    assert receipts["SOURCE"]["binding"]["source_sha256"] == source_spec["source_sha256"]
    for role in ("TINY", "RESEARCH"):
        binding = receipts[role]["binding"]
        expected = {**research_spec["frozen_sources"], research_contract["path"]: research_contract["sha256"]}
        assert binding["protocol_sha256"] == research_contract["sha256"] and binding["source_hashes"] == expected
    assert receipts["INDEPENDENT"]["actual_report_sha256"] == plan["roles"]["RESEARCH"]["report_sha256"]
    assert receipts["INDEPENDENT"]["verified_source_hashes"] == expected
    assert receipts["ROOT"]["source_hashes"] == expected
    assert receipts["SOURCE"]["source_files"] == 38 and receipts["SOURCE"]["actual_minute_rows"] == 1_664_640
    assert receipts["RESEARCH"]["completed_ledgers"] == receipts["RESEARCH"]["planned_ledgers"] == 3
    assert receipts["RESEARCH"]["all_planned_ledgers_complete"] and receipts["RESEARCH"]["source_bytes_unchanged"]
    assert receipts["INDEPENDENT"]["completed_ledgers_verified"] == 3
    assert receipts["ROOT"]["candidate_status"] == "NO_QUALIFIED_CANDIDATE"
    for item in plan.get("preserved_operational_tasks", []):
        path, task = closed(item["task_id"], item["exit_code"])
        relative = META + "/" + item["label"] + "_TASK_ACTUAL.json"
        copies.append((path, relative, sha(path)))
        tasks.append(dict(role=item["label"], task_id=task["id"], actual_exit_code=task["exit_code"],
            archived_task=relative, task_sha256=sha(path)))
    for item in plan.get("project_files", []):
        assert sha(project(item["path"])) == item["sha256"]
        hashes[item["path"]] = item["sha256"]
    for item in plan.get("small_source_snapshots", []):
        origin = ordinary(item["origin"])
        assert origin.resolve().is_relative_to(STATE) and sha(origin) == item["sha256"]
        assert item["expected_frozen_path"] in hashes and hashes[item["expected_frozen_path"]] == item["sha256"]
        copies.append((origin, META + "/source-snapshots/" + item["name"], item["sha256"]))
    assert len({relative for _, relative, _ in copies}) == len(copies)
    archive_bytes = sum(origin.stat().st_size for origin, _, _ in copies)
    assert archive_bytes <= LIMIT
    assert not (ROOT / META).exists()
    (ROOT / META).mkdir()
    for origin, relative, digest in copies:
        hashes[relative] = exact(origin, relative, digest)
    for relative, digest in hashes.items():
        assert sha(project(relative)) == digest, relative
    from scripts.research_v8.registry import FIELDS, append_event, read_verified
    history = read_verified((ROOT / "reports/experiment_registry.jsonl").read_bytes())
    independent = plan["roles"]["INDEPENDENT"]
    audit_task = next(t for t in tasks if t["role"] == "INDEPENDENT")
    already = any(item.get("actual_task_id") == audit_task["task_id"] and
        (item.get("artifact_sha256") or item.get("output_sha256")) == independent["report_sha256"] for item in history)
    imported = None
    if not already:
        event = dict.fromkeys(FIELDS)
        event.update(experiment_id=plan["independent_experiment_id"], event_id=plan["independent_experiment_id"] + ":RESULT",
            event_type="RESULT_IMPORTED", git_commit=receipts["RESEARCH"]["binding"]["git_commit"],
            data_manifest_hash=plan["source_receipt_sha256"], protocol_hash=plan["research_protocol_sha256"],
            feature_set="SAVED_FIXED_PUBLIC_TARGETS_AND_ACCOUNT_LEDGERS", labels="NONE", model_family="NONE",
            hyperparameters="FROZEN2H_HYBRID_CASH_SINGLE36BP_NO_HPO", seed="NOT_APPLICABLE",
            thresholds="UNCHANGED_ACCEPTED_COMMON_CAPS_AND_VOLATILITY_RULES", cost_assumptions="BYBIT_VIP0_SPOT36BP_RECEIVED_ASSET",
            all_folds="SINGLE_PREVIOUSLY_SEEN547D_FULL_PERIOD", success_failure=receipts["INDEPENDENT"]["status"],
            reason_for_next_experiment="NEXT_CHOICE_BY_ROOT_AFTER_FULL_PERIOD_EVIDENCE",
            result_influenced_later_choice=True, post_completion_registration=True, preregistered_start_record_created=False,
            artifact_path=independent["report"], artifact_sha256=independent["report_sha256"],
            actual_task_id=audit_task["task_id"], actual_exit_code=0, economic_candidate_qualified=False)
        imported = append_event(ROOT / "reports/experiment_registry.jsonl", event)
    value = dict(status="PASS_CLOSED_PUBLIC_LONG_547D_SOURCE_BINDING_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR",
        created_utc=datetime.now(UTC).isoformat(), source_hashes=hashes, actual_task_bindings=tasks,
        binding=dict(task_id=os.environ["COIN_TASK_ID"], exporter_sha256=plan["exporter_sha256"], closure_protocol_sha256=sha(plan_path)),
        ownership_before=ownership_before, ownership_after=owned_sizes(plan),
        resources_before=resource_before, resources_after=resources.status(),
        independent_result_imported=imported, independent_already_registered=already,
        metadata_only=True, new_market_arrays_QA_models_or_old_green_repeated=False,
        raw38_market_sources_or_binaries_archived=False, locked_consumed=False,
        candidate_status="NO_QUALIFIED_CANDIDATE", sustainable_net_APR="NOT_ESTABLISHED")
    payload = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    assert archive_bytes + len(payload) <= LIMIT
    with (ROOT / OUTPUT).open("xb") as stream:
        stream.write(payload)
    print(json.dumps(dict(status=value["status"], sha256=sha(ROOT / OUTPUT), task_count=len(tasks), frozen_files=len(hashes))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())