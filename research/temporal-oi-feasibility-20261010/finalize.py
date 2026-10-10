"""Package bounded public-source evidence without changing research semantics."""

import csv
import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = Path("/workspace/scratch/68ef1b82bcac/coin_single_state")
spec = importlib.util.spec_from_file_location("oi_verify", HERE / "verify.py")
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


raw_sample = json.loads((STATE / "oi-feasibility-retry/samples.json").read_text())
normalized = json.loads((HERE / "NORMALIZATION_DIAGNOSTIC.json").read_text())
for row, expected in zip(raw_sample["findings"], normalized, strict=True):
    raw = Path(row["raw_zip_path"]).read_bytes()
    assert verify.normalize_diagnostic(raw, row["symbol"], row["day"]) == expected
bundle_receipt = json.loads((HERE / "VERIFY.json").read_text())["raw_bundle"]
bundle = Path(bundle_receipt["path"])
assert sha(bundle) == bundle_receipt["SHA256"]
assert bundle_receipt["SHA256"] in (HERE / "RESULTS.md").read_text()
with zipfile.ZipFile(bundle) as archived:
    for row in raw_sample["findings"]:
        path = Path(row["raw_zip_path"])
        assert archived.read("raw/" + path.name) == path.read_bytes()
        assert (
            archived.read("raw/" + path.name + ".CHECKSUM")
            == path.with_name(path.name + ".CHECKSUM").read_bytes()
        )

feature_manifest = STATE / "feature-input/verified/FEATURE_MANIFEST.json"
features = json.loads(feature_manifest.read_text())["feature_schema"]["feature_order"]
assert len(features) == 24 and not any(
    "interest" in x.lower() or x.lower() == "oi" for x in features
)
train_rows = HERE.parent / "temporal-short-input-diagnosis-20261010/ROWS.csv"
with train_rows.open() as f:
    n = sum(row["role"] == "TRAIN" for row in csv.DictReader(f))
assert n == 744

sources = {
    "public_data_README.md": "https://github.com/binance/binance-public-data/blob/f446ce3812bd4e5521f21faecd4ae3c6460e49fc/README.md",
    "issue211_primary_comment.json": "https://github.com/binance/binance-public-data/issues/211#issuecomment-1430648564",
    "issue335_primary_comment.json": "https://github.com/binance/binance-public-data/issues/335#issuecomment-6020310934",
    "issue_258_comments.json": "https://github.com/binance/binance-public-data/issues/258#issuecomment-1766068768",
    "issue509_provenance_receipt.json": "https://github.com/binance/binance-public-data/issues/509",
    "API_AND_UNITS_RECEIPT.json": "https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data",
}
source_manifest = [
    {
        "file": name,
        "bytes": (HERE / "sources" / name).stat().st_size,
        "SHA256": sha(HERE / "sources" / name),
        "primary_URL": url,
        "capture": "GitHub connector UTF-8 payload capture; summaries labelled in receipt"
        if name.endswith(".json")
        else "Exact Git blob e01e34a0b0cd91d62386a5a237190a3167138bae",
    }
    for name, url in sources.items()
]
(HERE / "SOURCE_MANIFEST.json").write_text(json.dumps(source_manifest, indent=2) + "\n")
(HERE / "INPUT_METADATA_RECEIPT.json").write_text(
    json.dumps(
        {
            "feature_manifest_SHA256": sha(feature_manifest),
            "named24": features,
            "OI_present_in_named24": False,
            "existing_decision_rows_SHA256": sha(train_rows),
            "existing_mature_TRAIN_count": n,
            "consumed_for_WINDOW_TRADEOFF": ["role", "decision_us"],
            "outcome_conditioned_input_choice": False,
            "2025_market_model_outcome_score_files_consumed": False,
        },
        indent=2,
    )
    + "\n"
)

resources = []
for path in sorted(STATE.glob("OI_*RESOURCE_20261010.json")):
    resources.append(
        {"name": path.name, "SHA256": sha(path), "receipt": json.loads(path.read_text())}
    )
(HERE / "ALL_RESOURCE_RECEIPTS.json").write_text(json.dumps(resources, indent=2) + "\n")
files = sorted(
    p
    for p in HERE.rglob("*")
    if p.is_file() and "__pycache__" not in p.parts and p.name != "DELIVERY_MANIFEST.json"
)
manifest = [
    {"path": str(p.relative_to(HERE)), "bytes": p.stat().st_size, "SHA256": sha(p)} for p in files
]
(HERE / "DELIVERY_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
delivery = STATE / "oi-feasibility-evidence-final-20261010.zip"
assert not delivery.exists()
with zipfile.ZipFile(delivery, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in files + [HERE / "DELIVERY_MANIFEST.json"]:
        archive.write(path, "research/" + str(path.relative_to(HERE)))
    archive.write(bundle, "raw-evidence/" + bundle.name)
receipt = {
    "status": "PASS_FINAL_OFFLINE_RECOMPUTATION_AND_PACKAGE",
    "files": len(files) + 1,
    "path": str(delivery),
    "bytes": delivery.stat().st_size,
    "SHA256": sha(delivery),
    "raw_bundle_SHA256": sha(bundle),
    "all45_recomputed_after_final_source_format": True,
    "training_features_models_thresholds_wallets_changed": False,
    "GitHub_publication": "PARENT_OWNS_NOT_RUN_BY_WORKER",
}
(STATE / "OI_DELIVERY_RECEIPT_20261010.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
