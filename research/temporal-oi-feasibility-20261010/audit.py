"""Bounded official-archive availability and input-quality sampling, never features."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import statistics
import time
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ASSETS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
BASE = "https://data.binance.vision/data/futures/um/daily/metrics"
MAX_BODY = 512_000
MAX_TOTAL = 15_000_000
EXPECTED_FIELDS = (
    "create_time",
    "symbol",
    "sum_open_interest",
    "sum_open_interest_value",
    "count_toptrader_long_short_ratio",
    "sum_toptrader_long_short_ratio",
    "count_long_short_ratio",
    "sum_taker_long_short_vol_ratio",
)


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def url(symbol: str, day: str) -> str:
    assert symbol in ASSETS and "2020-08-31" <= day <= "2024-04-30"
    assert datetime.strptime(day, "%Y-%m-%d").strftime("%Y-%m-%d") == day
    return f"{BASE}/{symbol}/{symbol}-metrics-{day}.zip"


def quality(raw: bytes, symbol: str, day: str) -> dict:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        assert len(members) == 1 and not members[0].is_dir()
        member = members[0]
        assert member.filename == f"{symbol}-metrics-{day}.csv"
        assert member.file_size <= 2_000_000
        assert archive.testzip() is None
        body = archive.read(member)
    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    fields = tuple(reader.fieldnames or ())
    assert fields == EXPECTED_FIELDS
    rows = list(reader)
    times = []
    invalid = []
    ratios = []
    oi_values = []
    notional_values = []
    for i, row in enumerate(rows):
        timestamp = datetime.fromisoformat(row["create_time"])
        # Naive archive labels are interpreted in UTC for diagnostics only.
        assert timestamp.tzinfo is None
        timestamp = timestamp.replace(tzinfo=timezone.utc)
        times.append(timestamp)
        reasons = []
        if row["symbol"] != symbol:
            reasons.append("SYMBOL_MISMATCH")
        if timestamp.strftime("%Y-%m-%d") != day:
            reasons.append("DATE_OUTSIDE_FILENAME_DAY")
        parsed = []
        for field in ("sum_open_interest", "sum_open_interest_value"):
            try:
                value = float(row[field])
            except (TypeError, ValueError):
                value = math.nan
            parsed.append(value)
            if not math.isfinite(value):
                reasons.append(f"NONFINITE_{field}")
            elif value <= 0:
                reasons.append(f"NONPOSITIVE_{field}")
        if reasons:
            invalid.append({"row": i, "create_time": row["create_time"], "reasons": reasons})
        else:
            ratios.append(parsed[1] / parsed[0])
            oi_values.append(parsed[0])
            notional_values.append(parsed[1])
    counts = Counter(times)
    duplicates = [{"time": t.isoformat(), "rows": n} for t, n in sorted(counts.items()) if n > 1]
    origin = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    expected = [origin + timedelta(minutes=5 * i) for i in range(288)]
    absent = [t.isoformat() for t in expected if t not in counts]
    offgrid = [t.isoformat() for t in times if (t - origin).total_seconds() % 300 != 0]
    ordered = all(a < b for a, b in zip(times, times[1:], strict=False))
    valid_grid = not (invalid or duplicates or absent or offgrid) and ordered and len(rows) == 288
    return {
        "symbol": symbol,
        "day": day,
        "member": member.filename,
        "zip_sha256": sha(raw),
        "csv_sha256": sha(body),
        "csv_bytes": len(body),
        "fields": fields,
        "rows": len(rows),
        "unique_timestamps": len(counts),
        "first_label": times[0].isoformat() if times else None,
        "last_label": times[-1].isoformat() if times else None,
        "strictly_increasing": ordered,
        "duplicate_timestamps": duplicates,
        "offgrid_timestamps": offgrid,
        "missing_5m_slots": absent,
        "invalid_oi_rows": invalid,
        "positive_oi_rows": len(ratios),
        "value_over_quantity_median": statistics.median(ratios) if ratios else None,
        "value_over_quantity_min": min(ratios) if ratios else None,
        "value_over_quantity_max": max(ratios) if ratios else None,
        "first_oi": rows[0]["sum_open_interest"] if rows else None,
        "last_oi": rows[-1]["sum_open_interest"] if rows else None,
        "first_value": rows[0]["sum_open_interest_value"] if rows else None,
        "last_value": rows[-1]["sum_open_interest_value"] if rows else None,
        "complete_positive_unique_288_grid": valid_grid,
        "last_label_positive_unique": bool(times)
        and times[-1] == expected[-1]
        and counts[expected[-1]] == 1
        and not any(x["row"] == len(rows) - 1 for x in invalid),
        "clock_status": "UTC_LABEL_INTERPRETATION; HISTORICAL_PUBLICATION_UNKNOWN",
        "unit_status": "QUANTITY_AND_VALUE_FIELD_NAMES; HISTORICAL_NATIVE_UNITS_NOT_CERTIFIED",
        "first_row": rows[0] if rows else None,
        "last_row": rows[-1] if rows else None,
    }


def heads() -> list[tuple[str, str]]:
    # Monthly HEAD enumeration was narrowed before sample inspection because
    # measured network latency would exhaust the guard. Retain earlier receipts.
    jobs = [(symbol, day) for symbol in ASSETS for day in ("2020-10-15", "2021-11-30")]
    jobs += [(symbol, day) for symbol in ASSETS[1:] for day in ("2021-01-01", "2021-07-01")]
    jobs += [("BTCUSDT", day) for day in ("2020-08-31", "2020-09-01")]
    assert len(jobs) == 20
    return jobs


def samples() -> list[tuple[str, str]]:
    base = ("2021-12-01", "2022-01-01", "2022-12-31", "2023-01-01", "2023-12-31", "2024-04-30")
    jobs = [(symbol, day) for day in base for symbol in ASSETS]
    jobs += [("BTCUSDT", day) for day in ("2020-09-01", "2021-01-01", "2024-02-16")]
    jobs += [(symbol, day) for symbol in ASSETS for day in ("2022-03-07", "2022-03-08")]
    jobs += [("SOLUSDT", day) for day in ("2023-12-08", "2023-12-12")]
    assert len(jobs) <= 45 and len(set(jobs)) == len(jobs)
    return jobs


def run(stage: str, out: Path) -> None:
    assert not (out / f"{stage}.json").exists()
    out.mkdir(parents=True, exist_ok=True)
    rawdir = out / "raw"
    rawdir.mkdir(exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "coin-bounded-official-archive-feasibility/1.0"
    receipts = []
    findings = []
    total = 0
    t = time.monotonic()
    jobs = heads() if stage == "heads" else samples()
    requests_count = 0

    def fetch(target: str, method: str) -> tuple[dict, bytes]:
        nonlocal total, requests_count
        assert target.startswith(BASE + "/")
        started = time.monotonic()
        response = session.request(
            method, target, timeout=(30, 30), allow_redirects=False, stream=True
        )
        requests_count += 1
        body = b""
        if method == "GET":
            for chunk in response.iter_content(65_536):
                body += chunk
                assert len(body) <= MAX_BODY
                total += len(chunk)
                assert total <= MAX_TOTAL
        rec = {
            "url": target,
            "method": method,
            "http_status": response.status_code,
            "retrieved_at_UTC": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": time.monotonic() - started,
            "response_headers": dict(response.headers),
            "response_body_bytes": len(body),
            "response_body_sha256": sha(body),
            "publication_status": (
                "Last-Modified is current object metadata, not original first-release proof"
            ),
        }
        receipts.append(rec)
        with (out / f"{stage}_requests.jsonl").open("a") as handle:
            handle.write(json.dumps(rec, sort_keys=True) + "\n")
        response.close()
        if response.status_code in (401, 403, 451) or response.status_code >= 500:
            raise PermissionError(f"STOP_NO_BYPASS_HTTP_{response.status_code}:{target}")
        assert response.status_code in (200, 404), f"HTTP_NO_ALTERNATE:{response.status_code}"
        return rec, body

    error = None
    try:
        for i, (symbol, day) in enumerate(jobs):
            target = url(symbol, day)
            if stage == "heads":
                rec, _ = fetch(target, "HEAD")
                findings.append(
                    {"symbol": symbol, "day": day, "available_now": rec["http_status"] == 200}
                )
            else:
                rec, body = fetch(target, "GET")
                if rec["http_status"] == 404:
                    findings.append({"symbol": symbol, "day": day, "status": "MISSING_OBJECT_404"})
                else:
                    checksum_rec, checksum = fetch(target + ".CHECKSUM", "GET")
                    assert checksum_rec["http_status"] == 200
                    expected_sha, filename = checksum.decode().strip().split(maxsplit=1)
                    assert filename.lstrip("*") == target.rsplit("/", 1)[1]
                    assert expected_sha == sha(body)
                    name = target.rsplit("/", 1)[1]
                    (rawdir / name).write_bytes(body)
                    (rawdir / (name + ".CHECKSUM")).write_bytes(checksum)
                    q = quality(body, symbol, day)
                    q.update(
                        status="CHECKSUM_VERIFIED_CURRENT_ARCHIVE_SAMPLE",
                        raw_zip_path=str(rawdir / name),
                        checksum_body_sha256=sha(checksum),
                    )
                    findings.append(q)
            print(
                json.dumps(
                    {
                        "stage": stage,
                        "completed": i + 1,
                        "total": len(jobs),
                        "body_bytes": total,
                        "elapsed_seconds": time.monotonic() - t,
                    }
                ),
                flush=True,
            )
    except Exception as exc:
        error = {"type": type(exc).__name__, "error": str(exc)}
    result = {
        "schema": "BOUNDED_OI_INPUT_SAMPLE_V1",
        "stage": stage,
        "started_wall_monotonic": t,
        "elapsed_seconds": time.monotonic() - t,
        "planned_jobs": len(jobs),
        "completed_jobs": len(findings),
        "network_requests": requests_count,
        "downloaded_body_bytes": total,
        "error": error,
        "findings": findings,
        "all_history_completeness_certified": False,
        "historical_asof_availability_certified": False,
        "historical_native_units_certified": False,
        "status": "COMPLETE_BOUNDED_SAMPLE"
        if error is None
        else "STOPPED_WITH_INDEPENDENT_EVIDENCE",
    }
    (out / f"{stage}.json").write_text(json.dumps(result, indent=2) + "\n")
    if error:
        raise RuntimeError(error)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("heads", "samples"))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    run(args.stage, args.output)
