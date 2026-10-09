"""Continue independent OKX dates while preserving quarantined source observations."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from .common import DAY_MS, dump, sha256
from .okx_minute_intake import (
    ASSETS,
    END,
    MINUTE,
    VALIDATION_START,
    BulkBudget,
    collect_shard,
    enhanced_rows,
    gzip_jsonl,
    publish,
    read_gzip,
    request_for,
    verify_shard,
)
from .public_supplement import Budget, Failure, Job, _read, coverage, fingerprint


@dataclass(frozen=True)
class BoundaryJob(Job):
    def __post_init__(self):
        if (
            self.provider != "okx"
            or self.market != "perpetual"
            or self.kind != "mark"
            or self.interval != "1m"
            or self.reference_symbol.removesuffix("USDT") not in ASSETS
            or self.instrument_id != self.reference_symbol.removesuffix("USDT") + "-USDT-SWAP"
            or self.start_ms != VALIDATION_START - 2 * MINUTE
            or self.end_ms != VALIDATION_START
            or self.retention_start_ms is not None
            or self.retention_evidence is not None
        ):
            raise ValueError("Only the five explicitly authorized two-minute boundary requests")


@dataclass
class BoundaryBudget(Budget):
    def __post_init__(self):
        if (
            not 1 <= self.max_requests <= 14000
            or not 0 < self.max_bytes <= 160000000
            or not 0 < self.max_response_bytes <= 1000000
            or self.max_attempts != 1
            or self.min_interval_seconds < 0.25
            or not 0 <= self.requests_used <= self.max_requests
            or not 0 <= self.bytes_used <= self.max_bytes
        ):
            raise ValueError("One boundary attempt within original shared acquisition caps")


def refresh(index):
    index["verified_minute_rows"] = sum(
        s["coverage"][k]["observed_bars"]
        for s in index["shards"]
        if s["status"] == "COMPLETE"
        for k in ("trade", "mark")
    )
    known = {(s["instrument_id"], s["start_ms"]): s for s in index["shards"]}
    missing = []
    for start in range(VALIDATION_START, END, DAY_MS):
        for asset in ASSETS:
            shard = known.get((asset + "-USDT-SWAP", start))
            for kind in ("trade", "mark"):
                ranges = (
                    shard["coverage"][kind]["missing_ranges_ms_exclusive"]
                    if shard
                    else [[start, start + DAY_MS]]
                )
                missing.extend(
                    dict(
                        instrument_id=asset + "-USDT-SWAP",
                        kind=kind,
                        start_ms=a,
                        end_ms_exclusive=b,
                        reason="INCOMPLETE_SOURCE_OR_QUARANTINED" if shard else "NOT_REQUESTED",
                    )
                    for a, b in ranges
                )
    index["missing_or_unconfirmed_intervals"] = missing
    index["full_window_ready"] = not missing


def inventory(artifacts):
    (artifacts / "SHA256SUMS").write_text(
        "".join(
            f"{sha256(path)}  {path.relative_to(artifacts).as_posix()}\n"
            for path in sorted(artifacts.rglob("*"))
            if path.is_file() and path.name != "SHA256SUMS"
        )
    )


def boundary(asset, cache, parent, index, budget, session, stage):
    artifacts = cache / "artifacts"
    instrument = asset + "-USDT-SWAP"
    work = cache / "work" / instrument / "strict-start-witness"
    work.mkdir(parents=True, exist_ok=True)
    state_path = work / "manifest.json"
    receipt = (
        json.loads(state_path.read_text())
        if state_path.exists()
        else dict(binding=index["binding"], resume_stage=stage, requests=[])
    )
    if receipt["binding"] != index["binding"]:
        raise ValueError("Boundary source binding changed")
    for r in receipt["requests"]:
        if sha256(work / r["raw_file"]) != r["raw_sha256"]:
            raise ValueError("Boundary raw bytes changed")
    job = BoundaryJob(
        "okx",
        asset + "USDT",
        instrument,
        "perpetual",
        "mark",
        "1m",
        VALIDATION_START - 2 * MINUTE,
        VALIDATION_START,
    )
    # Explicit authorization is one new attempt per asset, without an HTTP retry.
    one = BoundaryBudget(
        max_requests=budget.max_requests,
        max_bytes=budget.max_bytes,
        max_response_bytes=budget.max_response_bytes,
        max_attempts=1,
        min_interval_seconds=budget.min_interval_seconds,
        requests_used=budget.requests_used,
        bytes_used=budget.bytes_used,
        last_request=budget.last_request,
        denied_providers=budget.denied_providers,
    )
    try:
        raw, record = _read(
            job, *request_for(job, job.start_ms, job.end_ms), work, receipt, one, session
        )
    finally:
        budget.requests_used, budget.bytes_used = one.requests_used, one.bytes_used
        budget.last_request = one.last_request
        if "okx" in one.denied_providers:
            dump(dict(status="PERMISSION_DENIED", scope="BOUNDARY"), cache / "access-stop.json")
    identity = json.loads((parent / instrument / "manifest.json").read_text())["identity"]
    rows = enhanced_rows(job, raw, identity, record, job.start_ms, job.end_ms)
    bars_file = instrument + "/strict-start-witness.mark.jsonl.gz"
    responses_file = instrument + "/strict-start-witness.responses.jsonl.gz"
    gzip_jsonl(artifacts / bars_file, rows)
    gzip_jsonl(
        artifacts / responses_file,
        [
            dict(
                request={k: v for k, v in record.items() if k != "raw_file"}, body_utf8=raw.decode()
            )
        ],
    )
    cov = coverage(job, rows)
    proof = dict(
        binding=index["binding"],
        resume_stage=stage,
        instrument_id=instrument,
        identity=identity,
        status=cov["status"],
        start_ms=job.start_ms,
        end_ms_exclusive=job.end_ms,
        coverage={"mark": cov},
        bars_files={"mark": bars_file},
        bars_sha256={"mark": sha256(artifacts / bars_file)},
        responses_file=responses_file,
        responses_sha256=sha256(artifacts / responses_file),
    )
    if proof["status"] == "COMPLETE":
        verify_shard(artifacts, proof)
    name = instrument + "/strict-start-witness.manifest.json"
    dump(proof, artifacts / name)
    return dict(
        instrument_id=instrument,
        manifest=name,
        bars_file=bars_file,
        bars_sha256=proof["bars_sha256"]["mark"],
        status=proof["status"],
        strict_prior_open_ms=VALIDATION_START - 2 * MINUTE,
        strict_prior_close_ms_exclusive=VALIDATION_START - MINUTE,
    )


def clock_proof(artifacts, parent, shard):
    instrument, start, end = shard["instrument_id"], shard["start_ms"], shard["end_ms_exclusive"]
    events = [
        json.loads(line)
        for line in (parent / instrument / "funding.jsonl").read_text().splitlines()
    ]
    events = [event for event in events if start <= event["funding_time_ms"] < end]
    marks = {r["open_ms"]: r for r in read_gzip(artifacts / shard["bars_files"]["mark"])}
    previous = [
        p
        for p in (artifacts / instrument).glob("*.manifest.json")
        if json.loads(p.read_text()).get("end_ms_exclusive") == start
    ]
    for path in previous:
        proof = json.loads(path.read_text())
        if "mark" in proof["bars_files"]:
            marks.update(
                {r["open_ms"]: r for r in read_gzip(artifacts / proof["bars_files"]["mark"])}
            )
    clocks = []
    for event in events:
        clock = event["funding_time_ms"]
        row = marks.get(clock - 2 * MINUTE)
        clocks.append(
            dict(
                funding_time_ms=clock,
                status="VERIFIED_STRICT_PRIOR_MARK" if row else "MISSING_STRICT_PRIOR_MARK",
                required_open_ms=clock - 2 * MINUTE,
                mark_close_ms_exclusive=row["close_ms_exclusive"] if row else None,
                mark_raw_sha256=row["raw_sha256"] if row else None,
                funding_raw_sha256=event["raw_sha256"],
                actual_rate_field="realizedRate",
                predicted_rate_field="fundingRate",
                publication_time_certified=False,
            )
        )
    return dict(native_rule="CLOSE_MS_EXCLUSIVE_STRICTLY_BEFORE_FUNDING_TIME", clocks=clocks)


def run(cache, parent, source_commit, repo=None):
    cache, parent = Path(cache), Path(parent)
    artifacts, path = cache / "artifacts", cache / "artifacts/COVERAGE.json"
    index = json.loads(path.read_text())
    if (
        sha256(Path(__file__).with_name("okx_minute_intake.py"))
        != index["binding"]["source_sha256"]
    ):
        raise ValueError("Original collector source changed; cannot reuse its bound checkpoints")
    stage = dict(
        version="okx-minute-quarantine-resume-1",
        source_commit=source_commit,
        source_sha256=sha256(Path(__file__)),
        started_ms=time.time_ns() // 1_000_000,
        original_limits_unchanged=True,
    )
    if index.get("resume_stage"):
        previous = index["resume_stage"]
        if previous["source_sha256"] != stage["source_sha256"]:
            raise ValueError("Continuation source changed")
        stage = previous
    index["resume_stage"] = stage
    if "final_audit" in index:
        index["prior_audit"] = index.pop("final_audit")
    index["status"] = "RUNNING_WITH_QUARANTINE"
    records = [
        r
        for p in (cache / "work").glob("*/*/manifest.json")
        for r in json.loads(p.read_text())["requests"]
        if "reused_source_commit" not in r
    ]
    budget = BulkBudget(
        requests_used=len(records), bytes_used=sum(r.get("body_bytes", 1000000) for r in records)
    )
    stage.setdefault("starting_requests", budget.requests_used)
    if (cache / "access-stop.json").exists():
        raise Failure("PERMISSION_DENIED", "Persisted provider denial; continuation stopped")
    quarantines = {
        (s["instrument_id"], s["start_ms"]) for s in index["shards"] if s["status"] != "COMPLETE"
    }
    refresh(index)
    dump(index, path)
    with requests.Session() as session:
        try:
            for asset in ASSETS:
                if time.time_ns() // 1_000_000 - index["started_ms"] >= 14380000:
                    raise Failure("WALL_BUDGET_EXHAUSTED", "Original four-hour cap")
                witness = boundary(asset, cache, parent, index, budget, session, stage)
                index["strict_start_witnesses"] = [
                    w
                    for w in index.get("strict_start_witnesses", [])
                    if w["instrument_id"] != witness["instrument_id"]
                ] + [witness]
                dump(index, path)
            for start in range(VALIDATION_START, END, DAY_MS):
                changed = False
                for asset in ASSETS:
                    key = (asset + "-USDT-SWAP", start)
                    existing = next(
                        (s for s in index["shards"] if (s["instrument_id"], s["start_ms"]) == key),
                        None,
                    )
                    if key in quarantines:
                        continue
                    shard = collect_shard(
                        asset,
                        start,
                        start + DAY_MS,
                        cache,
                        parent,
                        index["binding"],
                        budget,
                        session,
                        index,
                    )
                    if existing:
                        continue  # collect_shard verified completed cached bytes without a request.
                    shard["resume_stage"] = stage
                    if shard["status"] == "COMPLETE":
                        shard["native_strict_funding_clock_proof"] = clock_proof(
                            artifacts, parent, shard
                        )
                    name = key[0] + "/" + shard["date"] + ".manifest.json"
                    dump(shard, artifacts / name)
                    index["shards"].append(
                        dict(
                            instrument_id=key[0],
                            date=shard["date"],
                            status=shard["status"],
                            start_ms=start,
                            end_ms_exclusive=start + DAY_MS,
                            manifest=name,
                            manifest_sha256=sha256(artifacts / name),
                            bars_files=shard["bars_files"],
                            bars_sha256=shard["bars_sha256"],
                            responses_file=shard["responses_file"],
                            responses_sha256=shard["responses_sha256"],
                            coverage=shard["coverage"],
                            identity_sha256=fingerprint(shard["identity"]),
                            contract_value=shard["identity"]["contract_value"],
                            contract_multiplier=shard["identity"]["contract_multiplier"],
                        )
                    )
                    changed = True
                    if shard["status"] == "INCOMPLETE_COVERAGE":
                        quarantines.add(key)
                    elif shard["status"] != "COMPLETE":
                        raise Failure(shard["status"], str(shard["failure"]))
                    refresh(index)
                    dump(index, path)
                if changed:
                    index.update(
                        new_requests=budget.requests_used, new_response_body_bytes=budget.bytes_used
                    )
                    stage["elapsed_seconds"] = (
                        time.time_ns() // 1_000_000 - stage["started_ms"]
                    ) / 1000
                    dump(index, path)
                    inventory(artifacts)
                    head = publish(cache, repo) if repo else None
                    print(
                        json.dumps(
                            dict(
                                stage="INDEPENDENT_DATE_VERIFIED",
                                start_ms=start,
                                complete_shards=sum(
                                    s["status"] == "COMPLETE" for s in index["shards"]
                                ),
                                requests=budget.requests_used,
                                body_bytes=budget.bytes_used,
                                continuation_elapsed_seconds=stage["elapsed_seconds"],
                                sha=head,
                            )
                        ),
                        flush=True,
                    )
            index["status"] = "FINISHED_WITH_QUARANTINE" if quarantines else "COMPLETE"
            index["all_independent_dates_processed"] = True
        except Failure as exc:
            index.update(
                status=exc.status, continuation_failure=dict(status=exc.status, detail=str(exc))
            )
        finally:
            refresh(index)
            index.update(
                new_requests=budget.requests_used, new_response_body_bytes=budget.bytes_used
            )
            stage["elapsed_seconds"] = (time.time_ns() // 1_000_000 - stage["started_ms"]) / 1000
            index["quarantined_instrument_dates"] = [
                dict(instrument_id=instrument, start_ms=start, end_ms_exclusive=start + DAY_MS)
                for instrument, start in sorted(quarantines)
            ]
            dump(index, path)
            inventory(artifacts)
    if repo:
        print(
            json.dumps(dict(stage="CONTINUATION_FINAL_PUBLISHED", sha=publish(cache, repo))),
            flush=True,
        )
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args()
    result = run(args.cache, args.parent, args.source_commit, args.repo)
    print(json.dumps(dict(status=result["status"], full_window_ready=result["full_window_ready"])))


if __name__ == "__main__":
    main()
