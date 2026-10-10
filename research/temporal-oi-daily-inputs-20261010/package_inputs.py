"""Quarter raw/receipt checkpoints and one small deterministic consumer delivery."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import inputs
from ingest import HERE, STATE, STORE, atomic_json, sha


def records_in_plan_order(plan):
    return [
        json.loads(path.read_text())
        for job in plan["rows"]
        if (path := STORE / "records" / (job["ZIP"].removesuffix(".zip") + ".json")).exists()
    ]


def portable_record(row):
    return {
        key: value for key, value in row.items() if key not in ("raw_zip_path", "raw_checksum_path")
    }


def raw_manifest(records):
    rows = []
    for r in records:
        row = dict(
            symbol=r["symbol"],
            source_day=r["source_day"],
            quarter=r["quarter"],
            status=r["status"],
            official_URL=r["official_URL"],
            archive_origin=r["archive_origin"],
        )
        if r["status"] == "VERIFIED_CURRENT_ARCHIVE":
            path = Path(r["raw_zip_path"])
            side = Path(r["raw_checksum_path"])
            assert sha(path.read_bytes()) == r["zip_sha256"]
            assert sha(side.read_bytes()) == r["checksum_sha256"]
            row.update(
                ZIP=path.name,
                ZIP_bytes=r["zip_bytes"],
                ZIP_SHA256=r["zip_sha256"],
                CSV_SHA256=r["csv_sha256"],
                CHECKSUM_bytes=r["checksum_bytes"],
                CHECKSUM_SHA256=r["checksum_sha256"],
                CHECKSUM_URL=r["CHECKSUM_URL"],
            )
            if r["archive_origin"] == "REUSED_VERIFIED_RAW45_SAMPLE":
                row["raw_location"] = (
                    "published temporal-oi-feasibility-20261010 raw45 bundle/raw/" + path.name
                )
                row["reuse_bundle_SHA256"] = (
                    "43718a5239205de9a2fc0f3a93a68cf2991cafb09bc4cefe3106117a6e810358"
                )
            else:
                row["raw_location"] = f"oi-daily-{r['quarter']}-raw.zip:raw/{path.name}"
        rows.append(row)
    return rows


def add(bundle, name, body, *, raw=False):
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 10, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED if raw else zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    bundle.writestr(info, body)


def build_quarter(quarter):
    plan = json.loads((HERE / "PLAN.json").read_text())
    all_records = records_in_plan_order(plan)
    selected = [r for r in all_records if r["quarter"] == quarter]
    assert len(selected) == sum(r["quarter"] == quarter for r in plan["rows"]), (
        "Quarter not complete"
    )
    keys = {(r["symbol"], r["source_day"]) for r in selected}
    consumers = [
        r for r in inputs.consumer_rows(all_records) if (r["symbol"], r["source_day"]) in keys
    ]
    quarterdir = STORE / "quarters" / quarter
    quarterdir.mkdir(exist_ok=True)
    output = STORE / "packs" / f"oi-daily-{quarter}-raw.zip"
    assert not output.exists(), "Preserve previously published quarter packs"
    manifest = raw_manifest(selected)
    summary = inputs.summary(selected, consumers)
    inputs.write_csv(quarterdir / "DAILY_OI_INPUTS.csv", consumers)
    atomic_json(quarterdir / "RAW_ARCHIVE_MANIFEST.json", manifest)
    atomic_json(quarterdir / "COVERAGE.json", summary)
    with (quarterdir / "QUALITY.jsonl").open("w") as handle:
        for row in selected:
            handle.write(json.dumps(portable_record(row), sort_keys=True) + "\n")
    with zipfile.ZipFile(output, "w") as bundle:
        for row in selected:
            if row["archive_origin"] == "NEW_OFFICIAL_GET":
                for key in ("raw_zip_path", "raw_checksum_path"):
                    path = Path(row[key])
                    add(bundle, "raw/" + path.name, path.read_bytes(), raw=True)
        for path in sorted(quarterdir.iterdir()):
            add(bundle, path.name, path.read_bytes())
        receipt = STORE / "receipts" / f"{quarter}.jsonl"
        if receipt.exists():
            add(bundle, "receipts/GET_REQUESTS.jsonl", receipt.read_bytes())
        old_receipts = STATE / "oi-feasibility-retry/samples_requests.jsonl"
        reused_urls = {
            r["official_URL"]
            for r in selected
            if r["archive_origin"] == "REUSED_VERIFIED_RAW45_SAMPLE"
        }
        reused_receipts = [
            line
            for line in old_receipts.read_text().splitlines()
            if json.loads(line)["url"].removesuffix(".CHECKSUM") in reused_urls
        ]
        if reused_receipts:
            add(
                bundle,
                "receipts/REUSED_SAMPLE_GET_REQUESTS.jsonl",
                ("\n".join(reused_receipts) + "\n").encode(),
            )
    assert output.stat().st_size <= 10_000_000, (
        "Split required before publication; oversized pack not deliverable"
    )
    receipt = dict(
        quarter=quarter,
        path=str(output),
        bytes=output.stat().st_size,
        SHA256=sha(output.read_bytes()),
        coverage=summary,
        newly_archived_objects=sum(r["archive_origin"] == "NEW_OFFICIAL_GET" for r in selected),
        reused_raw45_objects=sum(
            r["archive_origin"] == "REUSED_VERIFIED_RAW45_SAMPLE" for r in selected
        ),
        NOTE=(
            "Current-vintage retrospective inputs, D+2 availability assumed; native "
            "units/original publication uncertified"
        ),
    )
    atomic_json(STORE / "packs" / f"oi-daily-{quarter}-RECEIPT.json", receipt)
    print(json.dumps(receipt, indent=2))


def finalize():
    plan = json.loads((HERE / "PLAN.json").read_text())
    records = records_in_plan_order(plan)
    assert len(records) == len(plan["rows"]) == 4410
    recomputed = []
    for row in records:
        if row["status"] == "VERIFIED_CURRENT_ARCHIVE":
            raw = Path(row["raw_zip_path"]).read_bytes()
            side = Path(row["raw_checksum_path"]).read_bytes()
            digest, name = side.decode().strip().split(maxsplit=1)
            assert digest == sha(raw) == row["zip_sha256"]
            assert sha(side) == row["checksum_sha256"]
            assert name.lstrip("*") == Path(row["raw_zip_path"]).name
            recheck = inputs.normalize(raw, row["symbol"], row["source_day"])
            assert all(recheck[k] == row[k] for k in recheck), "Normalized record mismatch"
            recomputed.append(row)
    consumers = inputs.consumer_rows(records)
    inputs.write_csv(HERE / "DAILY_OI_INPUTS.csv", consumers)
    atomic_json(HERE / "RAW_ARCHIVE_MANIFEST.json", raw_manifest(records))
    with (HERE / "QUALITY.jsonl").open("w") as handle:
        for row in records:
            handle.write(json.dumps(portable_record(row), sort_keys=True) + "\n")
    quarter_receipts = [
        json.loads(p.read_text()) for p in sorted((STORE / "packs").glob("*-RECEIPT.json"))
    ]
    for receipt in quarter_receipts:
        path = Path(receipt["path"])
        assert (
            path.stat().st_size == receipt["bytes"] and sha(path.read_bytes()) == receipt["SHA256"]
        )
    totals = json.loads((STORE / "NETWORK_TOTAL.json").read_text())
    coverage = dict(
        overall=inputs.summary(records, consumers),
        by_asset={
            asset: inputs.summary(
                [r for r in records if r["symbol"] == asset],
                [r for r in consumers if r["symbol"] == asset],
            )
            for asset in inputs.audit.ASSETS
        },
        by_quarter={q["quarter"]: q["coverage"] for q in quarter_receipts},
        terminal_masked_asset_days=[
            dict(symbol=r["symbol"], source_day=r["source_day"], reasons=r["terminal_mask_reasons"])
            for r in records
            if not r["terminal_valid"]
        ],
        network=totals,
    )
    atomic_json(HERE / "COVERAGE.json", coverage)
    atomic_json(HERE / "RAW_PACK_MANIFEST.json", quarter_receipts)
    verified = dict(
        status="PASS_FULL_CALENDAR_INPUT_RECOMPUTATION",
        asset_days=4410,
        calendar_days=882,
        verified_archive_recomputations=len(recomputed),
        dataset_rows=len(consumers),
        source_day_first=consumers[0]["source_day"],
        source_day_last=consumers[-1]["source_day"],
        last_ASSUMED_available_UTC=consumers[-1]["assumed_available_UTC"],
        prior_sample_reuse_count=sum(
            r["archive_origin"] == "REUSED_VERIFIED_RAW45_SAMPLE" for r in records
        ),
        PLAN_SHA256=sha((HERE / "PLAN.json").read_bytes()),
        reused_audit_SHA256=sha(inputs.AUDIT_PATH.read_bytes()),
        dataset_SHA256=sha((HERE / "DAILY_OI_INPUTS.csv").read_bytes()),
        dataset_bytes=(HERE / "DAILY_OI_INPUTS.csv").stat().st_size,
        no_training_evaluation_model_price_or_outcome_IO=True,
        historical_asof_availability_certified=False,
        historical_native_units_certified=False,
        coverage=coverage["overall"],
    )
    atomic_json(HERE / "VERIFY.json", verified)
    print(json.dumps(verified, indent=2))


def delivery():
    output = STATE / "oi-daily-inputs-consumer-20261010.zip"
    assert not output.exists()
    names = (
        "inputs.py",
        "ingest.py",
        "prepare.py",
        "package_inputs.py",
        "test_inputs.py",
        "PLAN.json",
        "INPUT_CONTRACT.md",
        "RESULTS.md",
        "DAILY_OI_INPUTS.csv",
        "COVERAGE.json",
        "RAW_ARCHIVE_MANIFEST.json",
        "QUALITY.jsonl",
        "RAW_PACK_MANIFEST.json",
        "VERIFY.json",
        "TEST_RESULTS.txt",
        "RESOURCE_RECEIPTS.json",
    )
    with zipfile.ZipFile(output, "w") as bundle:
        for name in names:
            add(bundle, name, (HERE / name).read_bytes())
        for name in ("audit.py", "verify.py", "test_audit.py"):
            add(
                bundle,
                "reused_feasibility/" + name,
                (HERE.parent / "temporal-oi-feasibility-20261010" / name).read_bytes(),
            )
    assert output.stat().st_size <= 10_000_000
    receipt = dict(
        path=str(output),
        bytes=output.stat().st_size,
        SHA256=sha(output.read_bytes()),
        NOTE=(
            "Raw source bodies are separate quarter packs plus already-published "
            "raw45; this archive contains masked consumer input, provenance, code and"
            " focused checks"
        ),
    )
    atomic_json(HERE / "DELIVERY_RECEIPT.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("quarter", "finalize", "delivery"))
    parser.add_argument("--quarter")
    args = parser.parse_args()
    if args.stage == "quarter":
        build_quarter(args.quarter)
    elif args.stage == "finalize":
        finalize()
    else:
        delivery()
