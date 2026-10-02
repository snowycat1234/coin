"""Read-only source acceptance for the explicit Jul--Oct daily/monthly logical view."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, date, datetime
import json
from pathlib import Path
import resource
import time

from quant.paths import ROOT, STATE
from quant.research_fast.trade_flow_v2 import checksum, require, source_hashes
from source_view import build_shards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-task", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "reports") and not output.exists(), "Exclusive source acceptance")
    prior_path = ROOT / "reports/fast_research/V7_SHARED_SOURCE_VIEW_92D_20261002_V1.json"
    recovery_run = STATE / "v7-monthly-perp-ethusdt-202510-recovery-v3"
    producer_path = args.producer_task.resolve()
    require(producer_path.is_relative_to(STATE / "task-progress") and producer_path.is_file(), "Explicit actual producer task proof")
    producer = json.loads(producer_path.read_text())
    require(producer["status"] == "completed" and producer["exit_code"] == 0 and producer["pid"] == 560 and producer["start_ticks"] == 30443 and producer["run_dir"] == str(recovery_run), "Recovery producer has not actually exited successfully")
    prior = json.loads(prior_path.read_text())
    require(prior["status"] == "PASS_SHARED_V7_SOURCE_VIEW_92D" and prior["actual_common_days"] == 92 and prior["actual_unique_stream_days"] == 368, "Existing accepted 92-day view required")
    pairs = [(ROOT / proof["receipt_path"], ROOT / proof["qa_path"]) for proof in prior["binding"]["monthly_proofs"]]
    for label in ("SPOT_BTCUSDT", "SPOT_ETHUSDT", "PERP_BTCUSDT"):
        base = ROOT / "reports/fast_research" / f"V7_MONTHLY_{label}_202510"
        pairs.append((base.with_name(base.name + "_V2.json"), base.with_name(base.name + "_INDEPENDENT_QA_V2.json")))
    pairs.append((ROOT / "reports/fast_research/V7_MONTHLY_PERP_ETHUSDT_202510_RECOVERY_V3.json", ROOT / "reports/fast_research/V7_MONTHLY_PERP_ETHUSDT_202510_RECOVERY_INDEPENDENT_QA_V3.json"))
    excluded_path = ROOT / "reports/fast_research/V7_MONTHLY_PERP_ETHUSDT_202510_V2.json"
    excluded = json.loads(excluded_path.read_text())
    require(excluded["status"] != "OFFICIAL_MONTHLY_V7_COMPLETE_PENDING_INDEPENDENT_QA" and excluded["completed_days"] == 30 and excluded["required_days"] == 31, "Original partial month must remain unaccepted")
    result = {
        "status": "FAILED_SHARED_V7_SOURCE_VIEW_123D", "created_utc": datetime.now(UTC).isoformat(),
        "source_hashes": {**source_hashes(), "scripts/research_v7/source_view.py": checksum(ROOT / "scripts/research_v7/source_view.py"), "scripts/research_v7/verify_source_view_123d.py": checksum(Path(__file__))},
        "prior_92d_report": {"path": str(prior_path), "sha256": checksum(prior_path)},
        "recovery_actual_producer": {"path": str(producer_path), "sha256": checksum(producer_path), "pid": producer["pid"], "start_ticks": producer["start_ticks"], "exit_code": producer["exit_code"]},
        "excluded_partial_october_v2": {"path": str(excluded_path), "sha256": checksum(excluded_path), "completed_days": excluded["completed_days"], "accepted": False, "owned_temporary_directory": excluded["owned_temporary_directory"]},
        "labels_or_model_results_read": False, "alpha_eligible": False, "real_time_quality_eligible": False,
        "limits": "Source SHA/schema/ID verification; no repeat 4-stream full row QA or market/model outcome reads",
    }
    started = time.monotonic()
    try:
        shards, binding = build_shards(date(2025, 7, 1), date(2025, 11, 1), monthly_pairs=pairs)
        require(len(shards) == 492 and len({(s.market, s.symbol, s.day) for s in shards}) == 492 and sum(s.rows for s in shards) == 8_501_760, "Complete unique 123-day view")
        counts = Counter(row["source_kind"] for row in binding["selected"])
        require(counts == {"original_daily": 266, "independently_audited_monthly": 226}, "Daily-first original source selection")
        require(binding["selected"][:368] == prior["binding"]["selected"], "Original 92-day accepted selected bytes changed")
        recovered = [row for row in binding["selected"] if row["market"] == "perp" and row["symbol"] == "ETHUSDT" and row["day"].startswith("2025-10")]
        require(len(recovered) == 31 and all("/recovery_20261002_v3/" in row["manifest_path"] for row in recovered), "Recovered independent whole month only; no partial month splice")
        require(checksum(excluded_path) == result["excluded_partial_october_v2"]["sha256"] and checksum(prior_path) == result["prior_92d_report"]["sha256"], "Previous evidence remains unchanged")
        result.update(status="PASS_SHARED_V7_SOURCE_VIEW_123D", actual_common_days=123, actual_unique_stream_days=492, actual_rows=8_501_760, source_counts=dict(counts), recovery_month_whole_source_days=31, original_92d_exact_prefix_preserved=True, binding=binding)
    except Exception as error:
        result.update(error_type=type(error).__name__, reason=str(error)[:2048])
        raise
    finally:
        result["elapsed_seconds"] = time.monotonic() - started
        result["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        with output.open("x", encoding="utf8") as writer:
            writer.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "actual_common_days", "actual_unique_stream_days", "source_counts", "elapsed_seconds", "peak_rss_bytes")}))


if __name__ == "__main__":
    main()
