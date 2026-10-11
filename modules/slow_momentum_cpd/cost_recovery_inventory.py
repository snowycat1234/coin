"""Read-only Git metadata inventory. No large blob extraction or provider calls."""
import argparse
import json
import subprocess
import zipfile
from pathlib import Path

from .cost_feasibility import ROOT, git, sha, write_json

ARCHIVES = (
    ("2024_H1", "d69e9ac94478c5be54cb46c622afec7aaf3c61f7",
     "research_artifacts/e5_h1_tail_coverage_pair_20261008/INDEX.json"),
    ("2023_JULY_FOLD", "88d6ff788dad5ce68efee1a200605f506c067339",
     "research/core5-binance-native-2023-data/JULY2023/INDEX.json"),
    ("2023_OCTOBER_FOLD", "03ab52320a3271caabb67caab4a395ad2f922653",
     "research/core5-binance-native-2023-data/OCTOBER2023/INDEX.json"),
    ("DAILY_FUNDING_FEATURES", "e0d3400b23842f11f167a63e7d80856d76501de8",
     "research/temporal-feature-data-20261009/INDEX.json"),
)
ADAPTERS = (
    "scripts/investment/resumable_perpetual.py",
    "scripts/investment/bybit_cost_inputs.py",
    "src/quant/execution_contract.py",
    "modules/collector_research/validation/data.py",
    "research/recover-frozen-runner-20261009/recover_h1.py",
    "research/recover-frozen-runner-20261009/native61.py",
)


def inventory():
    archives = []
    for name, commit, path in ARCHIVES:
        raw = git("show", f"{commit}:{path}")
        index = json.loads(raw)
        parts = []
        for part in index["parts"]:
            filename = part.get("file_name", part.get("name", part.get("file")))
            spec = f"{commit}:{str(Path(path).parent / filename)}"
            oid = git("rev-parse", spec).decode().strip()
            # Batch metadata only: no content read/decompression.
            fields = subprocess.check_output(["git", "cat-file", "--batch-check"],
                                             input=(oid + "\n").encode(), cwd=ROOT).decode().split()
            assert fields[0] == oid and fields[1] == "blob" and int(fields[2]) == part["bytes"]
            if "git_blob_sha1" in part:
                assert oid == part["git_blob_sha1"]
            parts.append({"name": filename, "git_blob": oid, "bytes": int(fields[2]),
                          "declared_sha256": part.get("sha256", part.get("SHA256")),
                          "local_object_metadata": "PRESENT_SIZE_MATCH", "body_sha256_rechecked": False})
        archives.append({"name": name, "commit": commit, "index": path,
                         "index_sha256": sha(raw), "parts": parts,
                         "total_part_bytes": sum(p["bytes"] for p in parts),
                         "published_archive_sha256": index.get("original_sha256", index.get("package_SHA256", index.get("SHA256"))),
                         "published_validated_start": index.get("interval_UTC_start_inclusive"),
                         "published_validated_end_exclusive": index.get("interval_UTC_end_exclusive"),
                         "current_body_crc_grid_validation": "NOT_RUN_METADATA_ONLY"})
    feature_zip = Path("/workspace/slow-momentum-state/source/features.zip")
    assert sha(feature_zip.read_bytes()) == "bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30"
    with zipfile.ZipFile(feature_zip) as archive:
        members = [{"name": p.filename, "bytes": p.file_size} for p in archive.infolist()]
    identities_path = ROOT / "research/recover-frozen-runner-20261009/NATIVE61_INPUT_IDENTITIES.json"
    identities = json.loads(identities_path.read_text())
    files = identities["registered_normalized_inputs"]
    adapters = {path: sha((ROOT / path).read_bytes()) for path in ADAPTERS}
    return {"schema": "SAVED_POLICY_NATIVE_RECOVERY_METADATA_V1", "checkout_head": git("rev-parse", "HEAD").decode().strip(),
            "executing_inventory_source_sha256": sha(Path(__file__).read_bytes()),
            "status": "PARTS_RECOVERABLE_NOT_COMPLETE_REPLAY_INPUT_CERTIFICATION", "archives": archives,
            "features_zip_members": members, "features_zip_sha256": sha(feature_zip.read_bytes()),
            "h1_registered_normalized_inputs": files, "h1_identity_sha256": sha(identities_path.read_bytes()),
            "adapters": adapters,
            "coverage": {"2023_H1": "MINUTE_TRADE_MARK_NOT_LOCATED_IN_PINNED_ARCHIVES; daily saved policies exist",
                         "2023_H2": "July-Dec original monthly trade/mark archives recoverable; previously grid-validated July3-Sep4 and Oct2-Dec4 folds only; normalized Parquets not published",
                         "2024_JAN_APR": "Registered normalized trade/mark months in Jan-Jun package; prior executed engine grid proof only May-Jun native61, current Jan-Apr full-grid binding NOT_RUN",
                         "funding": "Public funding member identities recoverable; current six-wallet interval row coverage, event clocks and raw-unit assertion NOT_BOUND; historical publication clock and native fee certification remain assumptions",
                         "full_483_day_native_replay": "NOT_READY; no complete 2023H1 minute input identity/coverage, no CPD target adapter certification"},
            "native_adapter_gap": ["Bind saved target time/symbol/mask to completed decision inputs and ExecutionContractV2 first eligible minute",
                                   "Use same BASE27 and complete10k shared wallet, .99 sizing, abs.30/gross.60, isolated1x, lot/min10USDT, prior-minute capacity .001, bounded partial fills and real reduce-only protection",
                                   "Bind strict-prior completed mark and actual signed funding; equal-time funding before fill",
                                   "Prove no missing held mark/grid and terminal paid flat; no alternative E5 mapper or synthetic fills"],
            "conditional_minimal_replay_scope": {"role": "READINESS_SCOPE_ONLY_NOT_WALLET_EXECUTION_PLAN_OR_AUTHORIZATION",
                                                 "selection": "Earliest existing published validated2023 fold, chosen from source chronology before cost screen, not policy outcome",
                                                 "available_UTC": ["2023-07-03", "2023-07-10"],
                                                 "all_pairs": "Six separate10000USDT shared wallets, trend/trend_cpd x seeds2001/2002/2003, same2048 policies, one BASE27, no combination grid",
                                                 "initial": "Independent flat; recover prior completed minute and daily decision context",
                                                 "terminal": "Bind final label-end handling and charged native flat; no free or earlier forced cash treatment",
                                                 "prospective_budget_for_review": {"cpu_threads": 1, "GPU": 0, "swap": 0,
                                                                                   "address_space_bytes": 4000000000, "RSS_stop_bytes": 2000000000,
                                                                                   "host_used_stop_bytes": 8000000000, "wall_seconds_total": 1200,
                                                                                   "wallets_max": 6, "days_each": 7, "provider_downloads": 0,
                                                                                   "raw_package_bytes_max": 37957161, "normalized_work_bytes_max": 209715200,
                                                                                   "ledger_output_bytes_max": 67108864, "disk_reserve_bytes": 16106127360},
                                                 "activation": "Only after economic screen warrants, input/adapter gaps closed and parent reviews one frozen plan; current wallets0"},
            "current_operations": {"large_blob_bodies_read": 0, "provider_requests": 0, "source_archive_extractions": 0,
                                   "wallets": 0, "training_updates": 0, "collector_lock_opened": False},
            "lost_2026_Q1_Q2_ledgers": "UNAVAILABLE_NOT_RECOVERED_NOT_REPLACED"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = inventory()
    write_json(args.output, value)
    print(json.dumps({"status": value["status"], "archives": len(value["archives"]),
                      "local_parts_present": sum(len(x["parts"]) for x in value["archives"]),
                      "features_members": len(value["features_zip_members"]), "wallets": 0}))


if __name__ == "__main__":
    main()
