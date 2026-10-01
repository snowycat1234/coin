"""Read-only finite checkpoint encoding diagnostic, never a capacity acceptance."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sqlite3
import time
import zlib
from datetime import UTC, datetime
from pathlib import Path

from quant.paths import ROOT, STATE
from quant.resources import status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    journal, output = args.journal.resolve(), args.output.resolve()
    if (not journal.is_relative_to(STATE.resolve())
            or not journal.parent.name.startswith("a03-capacity-")
            or not output.is_relative_to((ROOT / "reports").resolve())
            or output.exists()):
        raise ValueError("Use an independent engineering journal and new D receipt")
    ram = status()
    conn = sqlite3.connect(f"file:{journal}?mode=ro", uri=True, timeout=1)
    started = time.monotonic()
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.set_progress_handler(lambda: int(time.monotonic() - started > 5), 1000)
        rows = conn.execute(
            "SELECT seq,hash,payload FROM records WHERE kind='checkpoint' "
            "ORDER BY seq DESC LIMIT 1024"
        ).fetchall()
    finally:
        conn.close()
    samples = []
    for seq, record_hash, payload in rows:
        if len(payload.encode()) > 500_000:
            raise ValueError("Oversize diagnostic input")
        financial = json.loads(payload)
        if "candidate_binding_sha256" not in financial:
            continue
        raw = json.dumps(financial, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode()
        # The parent constructor reads these fields before the subclass can
        # decode state, so any future envelope must expose all four unchanged.
        header = {name: financial[name] for name in (
            "last_tick_ms", "observed_seconds", "healthy_seconds", "last_healthy"
        )}
        begin = time.monotonic()
        packed = zlib.compress(raw, level=6)
        candidate_envelope = {
            **header, "checkpoint_schema": "diagnostic_zlib_json_v1",
            "raw_bytes": len(raw), "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "financial_zlib_base64": base64.b64encode(packed).decode("ascii"),
        }
        encoded = json.dumps(candidate_envelope, sort_keys=True,
                             separators=(",", ":")).encode()
        assert zlib.decompress(packed) == raw
        assert json.loads(zlib.decompress(packed)) == financial
        samples.append({"seq": seq, "record_hash": record_hash,
                        "raw_bytes": len(raw), "envelope_bytes": len(encoded),
                        "compression_seconds": time.monotonic() - begin})
    if not samples:
        raise ValueError("No candidate financial checkpoints measured")
    result = {
        "status": "READONLY_ENCODING_DIAGNOSTIC_ONLY",
        "created_at_utc": datetime.now(UTC).isoformat(), "journal": str(journal),
        "checkpoints_checked": len(samples), "roundtrip_exact": True,
        "raw_peak_bytes": max(row["raw_bytes"] for row in samples),
        "envelope_peak_bytes": max(row["envelope_bytes"] for row in samples),
        "raw_total_bytes": sum(row["raw_bytes"] for row in samples),
        "envelope_total_bytes": sum(row["envelope_bytes"] for row in samples),
        "elapsed_seconds": time.monotonic() - started,
        "resources": ram, "first_seq": samples[0]["seq"], "last_seq": samples[-1]["seq"],
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "financial_rows_rewritten": 0, "engine_sources_changed": False,
        "capacity_accepted": False, "production_authorized": False,
        "limitations": "Existing journal snapshot, up to 1024 finite checkpoints. "
                       "Encoding is a diagnostic only. Any implementation needs a new "
                       "bound source version, bounded decoder, exact restart/rollback "
                       "tests and actual disk capacity measurement.",
        "samples": samples,
    }
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in (
        "status", "checkpoints_checked", "raw_peak_bytes", "envelope_peak_bytes",
        "raw_total_bytes", "envelope_total_bytes", "roundtrip_exact"
    )}))


if __name__ == "__main__":
    main()
