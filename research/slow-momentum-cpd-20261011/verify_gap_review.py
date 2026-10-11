import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

root = Path("/workspace/coin-slow-momentum")
exp = root / "research/slow-momentum-cpd-20261011"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = json.loads((exp / "DELIVERY_MANIFEST.json").read_text())
assert all(
    digest(root / path) == item["sha256"] and (root / path).stat().st_size == item["bytes"]
    for path, item in manifest["files"].items()
)
result = json.loads((exp / "results/RESULT.json").read_text())
assert all(digest(root / path) == expected for path, expected in result["source_files"].items())
state = Path("/workspace/slow-momentum-state")
for fit in result["fits"]:
    cp = state / (fit["arm"] + "-seed" + str(fit["seed"]) + ".pt")
    assert digest(cp) == fit["checkpoint_sha256"]
proposal = json.loads((exp / "SHARPE_CORRECTION_PROPOSAL.json").read_text())
assert proposal["status"] == "NOT_RUN" and proposal["executable_runner"] == "NOT_IMPLEMENTED"
assert proposal["predecessor"]["original_protocol_sha256"] == digest(exp / "PROTOCOL.json")
assert proposal["predecessor"]["frozen_training_sha256"] == digest(
    exp / "results/FROZEN_TRAINING.json"
)
assert (
    proposal["frozen_inputs"]["archive_sha256"]
    == json.loads((exp / "PROTOCOL.json").read_text())["source"]["archive_sha256"]
)
assert proposal["frozen_inputs"]["source_commit"] == result["source_commit"]
training = proposal["training"]
assert training["seeds"] == [2001, 2002, 2003]
assert training["fits"] == 2 * len(training["seeds"]) == 6
assert training["total_updates"] == training["fits"] * training["updates_per_fit"] == 6144
assert training["gp_fits"] == training["scaler_fits"] == 0
assert (
    training["cumulative_if_executed"]["lstm_fits"] == result["lstm_fits"] + training["fits"] == 12
)
assert (
    training["cumulative_if_executed"]["total_updates"]
    == sum(f["updates"] for f in result["fits"]) + training["total_updates"]
    == 7680
)
assert len(proposal["scoring"]["gates_all_required"]) == 4
assert all(
    "MSE" not in gate and "rank" not in gate for gate in proposal["scoring"]["gates_all_required"]
)
assert "decision_mask_not_sample_index" in proposal["frozen_inputs"]
assert proposal["economics"]["status"] == "NOT_RUN_NOT_INCLUDED_IN_THIS_PROPOSAL"
text = (exp / "REPRODUCTION_GAPS.md").read_text()
anchor_pattern = r"https://github.com/([^/]+/[^/]+)/blob/([0-9a-f]{40})/([^\s)]+?)#L(\d+)"
anchors = re.findall(anchor_pattern, text)
assert len(anchors) >= 20
anchor_records = []
upstream_root = Path("/workspace/research-sources/trading-momentum-transformer")
for repo, commit, path, line in anchors:
    if repo == "snowycat1234/coin":
        source = subprocess.check_output(["git", "show", commit + ":" + path], cwd=root)
    else:
        assert repo == "kieranjwood/trading-momentum-transformer"
        assert commit == json.loads((exp / "UPSTREAM.json").read_text())["commit"]
        source = subprocess.check_output(["git", "show", commit + ":" + path], cwd=upstream_root)
    lines = source.decode().splitlines()
    assert 1 <= int(line) <= len(lines), (repo, path, line)
    anchor_records.append(
        {
            "repository": repo,
            "commit": commit,
            "path": path,
            "line": int(line),
            "source_line": lines[int(line) - 1],
        }
    )
upstream = json.loads((exp / "UPSTREAM.json").read_text())
assert all(
    digest(upstream_root / path) == expected
    for path, expected in upstream["read_source_sha256"].items()
)
assert (
    digest(Path("/workspace/research-sources/slow_momentum_v3.pdf")) == upstream["paper_pdf_sha256"]
)
assert math.isclose(0.5 / math.sqrt(1.25), 1 / math.sqrt(5))
assert math.isclose(0.3 / math.sqrt(0.21), 0.6546536707079771)
before = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
changed = subprocess.check_output(["git", "diff", "--name-only"], cwd=root, text=True).splitlines()
assert set(changed) <= {"docs/RESEARCH_DECISION_LOG.md", "docs/RESEARCH_STATUS.md"}
receipt = {
    "schema": "SLOW_MOMENTUM_CPD_GAP_REVIEW_RECEIPT_V1",
    "status": "PASS",
    "base_commit": before,
    "new_lstm_fits": 0,
    "new_gp_fits": 0,
    "new_model_inference_sets": 0,
    "new_wallets": 0,
    "preserved_delivery_manifest_files": len(manifest["files"]),
    "preserved_fit_source_files": len(result["source_files"]),
    "preserved_external_checkpoint_bytes": len(result["fits"]),
    "paper_and_upstream_hashes": "PASS",
    "proposal_counts_and_not_run_status": "PASS",
    "decision_time_mask_caveat": "PASS",
    "original_prediction_gates_preserved": "PASS",
    "nonlinear_sharpe_gate_not_mse": "PASS",
    "closed_form_counterexample": "CHECKED_ARITHMETIC_ONLY_NO_SIMULATION",
    "code_anchors": anchor_records,
    "new_artifact_sha256": {
        "REPRODUCTION_GAPS.md": digest(exp / "REPRODUCTION_GAPS.md"),
        "SHARPE_CORRECTION_PROPOSAL.json": digest(exp / "SHARPE_CORRECTION_PROPOSAL.json"),
    },
    "independent_read_only_review": (
        "paper_mechanism_review; completed without Python/training/writes"
    ),
    "validator_script_sha256": digest(Path(__file__)),
    "verification_command": (
        "bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python "
        "research/slow-momentum-cpd-20261011/verify_gap_review.py"
    ),
    "limits": (
        "Content/hash/count/anchor verification; no new model/unit/finance tests. "
        "Paths intentionally refer to this existing workspace."
    ),
    "prior_content_check": (
        "Initial content check passed, then five Ruff style findings were fixed. "
        "The initial verifier and receipt remain in independent state as "
        "gap-review-verifier-before-lintfix.py and gap-review-receipt-before-lintfix.json. "
        "These were documentation checks, zero scientific attempts or fits."
    ),
}
out = exp / "GAP_REVIEW_RECEIPT.json"
if out.exists():
    existing = json.loads(out.read_text())
    assert existing["new_artifact_sha256"] == receipt["new_artifact_sha256"]
    assert existing["validator_script_sha256"] == receipt["validator_script_sha256"]
    assert existing["code_anchors"] == receipt["code_anchors"]
else:
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
print(
    json.dumps(
        {
            key: receipt[key]
            for key in (
                "status",
                "preserved_delivery_manifest_files",
                "preserved_fit_source_files",
                "preserved_external_checkpoint_bytes",
                "new_lstm_fits",
                "new_wallets",
            )
        }
    )
)
