"""Single-stream bounded/resumable official daily metrics GETs, input-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import inputs
import requests

HERE = Path(__file__).resolve().parent
STATE = HERE.parent.parent.parent / "coin_single_state"
STORE = STATE / "oi-daily-inputs-20261010"


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def atomic_json(path: Path, value):
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)


def main(quarter: str, max_jobs: int):
    plan = json.loads((HERE / "PLAN.json").read_text())
    jobs = [r for r in plan["rows"] if r["quarter"] == quarter]
    assert jobs
    STORE.mkdir(exist_ok=True)
    for sub in ("raw", "records", "receipts", "quarters", "packs"):
        (STORE / sub).mkdir(exist_ok=True)
    stop_path = STORE / "NETWORK_STOP.json"
    assert not stop_path.exists(), f"Network requires review after {stop_path}"
    total_path = STORE / "NETWORK_TOTAL.json"
    totals = (
        json.loads(total_path.read_text())
        if total_path.exists()
        else dict(body_bytes=0, attempts=0)
    )
    session = requests.Session()
    session.headers["User-Agent"] = "coin-bounded-official-daily-oi-inputs/1.0"
    start = time.monotonic()
    completed_now = 0
    requests_now = 0
    log = STORE / "receipts" / f"{quarter}.jsonl"
    attempted = {}
    if log.exists():
        for line in log.read_text().splitlines():
            receipt = json.loads(line)
            attempted[receipt["url"]] = attempted.get(receipt["url"], 0) + 1

    def fetch(url, limit):
        nonlocal requests_now
        assert url.startswith(inputs.audit.BASE + "/")
        prior_attempts = attempted.get(url, 0)
        if prior_attempts >= 3:
            return dict(url=url, error="PRIOR_THREE_ATTEMPTS_EXHAUSTED"), None
        for attempt in range(prior_attempts + 1, 4):
            response = None
            body = b""
            began = time.monotonic()
            rec = dict(
                url=url,
                method="GET",
                attempt=attempt,
                retrieved_at_UTC=datetime.now(timezone.utc).isoformat(),
            )
            error = None
            try:
                response = session.get(url, timeout=(10, 20), allow_redirects=False, stream=True)
                rec.update(
                    http_status=response.status_code, response_headers=dict(response.headers)
                )
                for chunk in response.iter_content(65536):
                    body += chunk
                    totals["body_bytes"] += len(chunk)
                    assert len(body) <= limit, "OBJECT_BODY_LIMIT"
                    assert totals["body_bytes"] <= plan["max_total_new_network_body_bytes"], (
                        "TOTAL_BODY_LIMIT"
                    )
            except (requests.Timeout, requests.ConnectionError) as exc:
                error = type(exc).__name__
                rec["error"] = error
            finally:
                totals["attempts"] += 1
                attempted[url] = attempted.get(url, 0) + 1
                requests_now += 1
                rec.update(
                    response_body_bytes=len(body),
                    response_body_sha256=sha(body),
                    elapsed_seconds=time.monotonic() - began,
                    publication_status=(
                        "Current metadata; original historical first release UNKNOWN"
                    ),
                )
                with log.open("a") as handle:
                    handle.write(json.dumps(rec, sort_keys=True) + "\n")
                atomic_json(total_path, totals)
                if response is not None:
                    response.close()
            status = rec.get("http_status")
            if status in (401, 403, 451):
                atomic_json(stop_path, dict(reason=f"ACCESS_DENIED_{status}", receipt=rec))
                raise PermissionError(f"STOP_NO_BYPASS_{status}:{url}")
            if not error and status in (200, 404):
                return rec, body
            transient = error or status in (408, 425, 429, 500, 502, 503, 504)
            if transient and attempt < 3:
                time.sleep(1 if attempt == 1 else 3)
                continue
            if transient:
                return rec, None
            atomic_json(stop_path, dict(reason=f"UNEXPECTED_STATUS_{status}", receipt=rec))
            raise RuntimeError(f"UNEXPECTED_STATUS_{status}:{url}")

    def verify_file(path, side, expected_sha=None, expected_side_sha=None):
        raw, checksum = path.read_bytes(), side.read_bytes()
        digest, filename = checksum.decode().strip().split(maxsplit=1)
        assert filename.lstrip("*") == path.name.removesuffix(".pending")
        assert digest == sha(raw)
        assert expected_sha is None or digest == expected_sha
        assert expected_side_sha is None or sha(checksum) == expected_side_sha
        return raw, checksum

    try:
        for job in jobs:
            key = job["ZIP"].removesuffix(".zip")
            record_path = STORE / "records" / f"{key}.json"
            if record_path.exists():
                record = json.loads(record_path.read_text())
                if record["status"] == "VERIFIED_CURRENT_ARCHIVE":
                    verify_file(
                        Path(record["raw_zip_path"]),
                        Path(record["raw_checksum_path"]),
                        record["zip_sha256"],
                        record["checksum_sha256"],
                    )
                continue
            if completed_now >= max_jobs or time.monotonic() - start >= 1100:
                break
            old = job["reused_manifest"]
            if old:
                path = STATE / "oi-feasibility-retry/raw" / job["ZIP"]
                side = path.with_name(path.name + ".CHECKSUM")
                raw, checksum = verify_file(path, side, old["ZIP_SHA256"], old["CHECKSUM_SHA256"])
                origin = "REUSED_VERIFIED_RAW45_SAMPLE"
            else:
                path = STORE / "raw" / job["ZIP"]
                side = path.with_name(path.name + ".CHECKSUM")
                pending = path.with_name(path.name + ".pending")
                if path.exists() and side.exists():
                    raw, checksum = verify_file(path, side)
                else:
                    if pending.exists():
                        raw = pending.read_bytes()
                    else:
                        rec, raw = fetch(job["official_URL"], plan["max_ZIP_body_bytes"])
                        if raw is None:
                            record = inputs.missing(
                                job["symbol"], job["day"], "UNRESOLVED_TRANSIENT_GET"
                            )
                            record.update(
                                official_URL=job["official_URL"],
                                quarter=quarter,
                                archive_origin="BOUNDED_TRANSIENT_RETRIES_EXHAUSTED",
                                failure_receipt=rec,
                            )
                            atomic_json(record_path, record)
                            completed_now += 1
                            continue
                        if rec["http_status"] == 404:
                            record = inputs.missing(
                                job["symbol"], job["day"], "MISSING_ARCHIVE_404"
                            )
                            record.update(
                                official_URL=job["official_URL"],
                                quarter=quarter,
                                archive_origin="OFFICIAL_GET_404",
                            )
                            atomic_json(record_path, record)
                            completed_now += 1
                            continue
                        pending.write_bytes(raw)
                    rec, checksum = fetch(job["CHECKSUM_URL"], plan["max_CHECKSUM_body_bytes"])
                    if checksum is None or rec["http_status"] != 200:
                        record = inputs.missing(
                            job["symbol"], job["day"], "UNVERIFIED_CHECKSUM_UNAVAILABLE"
                        )
                        record.update(
                            official_URL=job["official_URL"],
                            quarter=quarter,
                            archive_origin="OFFICIAL_GET_UNVERIFIED",
                            pending_zip_sha256=sha(raw),
                            failure_receipt=rec,
                        )
                        atomic_json(record_path, record)
                        completed_now += 1
                        continue
                    digest, filename = checksum.decode().strip().split(maxsplit=1)
                    assert filename.lstrip("*") == path.name and digest == sha(raw)
                    assert not path.exists() and not side.exists(), "Do not overwrite raw objects"
                    pending.replace(path)
                    side.write_bytes(checksum)
                origin = "NEW_OFFICIAL_GET"
            record = inputs.normalize(raw, job["symbol"], job["day"])
            record.update(
                official_URL=job["official_URL"],
                CHECKSUM_URL=job["CHECKSUM_URL"],
                zip_bytes=len(raw),
                checksum_bytes=len(checksum),
                checksum_sha256=sha(checksum),
                raw_zip_path=str(path),
                raw_checksum_path=str(side),
                quarter=quarter,
                archive_origin=origin,
            )
            atomic_json(record_path, record)
            completed_now += 1
            if completed_now % 25 == 0:
                print(
                    json.dumps(
                        dict(
                            quarter=quarter,
                            completed_now=completed_now,
                            requests_now=requests_now,
                            total_network_bytes=totals["body_bytes"],
                            elapsed_seconds=round(time.monotonic() - start, 2),
                        )
                    ),
                    flush=True,
                )
            atomic_json(
                STORE / "CHECKPOINT.json",
                dict(quarter=quarter, status="RUNNING", last_completed=job["ZIP"], network=totals),
            )
    except Exception as exc:
        if not stop_path.exists():
            atomic_json(
                stop_path,
                dict(reason="INTEGRITY_OR_SCHEMA_STOP", type=type(exc).__name__, detail=str(exc)),
            )
        raise
    finally:
        session.close()
    complete = sum(
        (STORE / "records" / (r["ZIP"].removesuffix(".zip") + ".json")).exists() for r in jobs
    )
    checkpoint = dict(
        quarter=quarter,
        status="QUARTER_COMPLETE" if complete == len(jobs) else "BATCH_CHECKPOINT",
        quarter_completed=complete,
        quarter_total=len(jobs),
        completed_now=completed_now,
        requests_now=requests_now,
        network=totals,
        elapsed_seconds=time.monotonic() - start,
    )
    atomic_json(STORE / "CHECKPOINT.json", checkpoint)
    print(json.dumps(checkpoint), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("quarter")
    parser.add_argument("--max-jobs", type=int, default=500)
    args = parser.parse_args()
    main(args.quarter, args.max_jobs)
