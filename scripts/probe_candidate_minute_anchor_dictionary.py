"""Readonly full-state minute-anchor compression diagnostic, with no chained dictionary."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sqlite3
import time
import zlib
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from quant.candidate_storage import CHECKPOINT, RESTORE_FIELDS, decode_record, encode_record
from quant.paths import ROOT, STATE
from quant.resources import status

MINUTE_US = 60_000_000
RAW_LIMIT = 1_048_576
DICT_LIMIT = 32768
CODEC = "candidate_minute_anchor_diagnostic_v1"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1_048_576), b""):
            result.update(block)
    return result.hexdigest()


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode()


def envelope(existing, raw, anchor):
    dictionary = anchor["raw"][-DICT_LIMIT:]
    compressor = zlib.compressobj(level=9, zdict=dictionary)
    compressed = compressor.compress(raw) + compressor.flush()
    return {
        **existing,
        "storage_codec": CODEC,
        "anchor_seq": anchor["seq"],
        "anchor_raw_sha256": hashlib.sha256(anchor["raw"]).hexdigest(),
        "compressed_json": base64.b64encode(compressed).decode("ascii"),
    }


def bounded_expand(value, *, seq, received_us, version, loader):
    keys = {
        "storage_codec",
        "storage_kind",
        "raw_bytes",
        "raw_sha256",
        "compressed_json",
        "anchor_seq",
        "anchor_raw_sha256",
    } | set(RESTORE_FIELDS)
    size, anchor_seq = value["raw_bytes"], value["anchor_seq"]
    if (
        set(value) != keys
        or value["storage_codec"] != CODEC
        or value["storage_kind"] != CHECKPOINT
        or type(size) is not int
        or not 0 < size <= RAW_LIMIT
        or type(anchor_seq) is not int
        or not 0 < anchor_seq < seq
        or len(value["compressed_json"]) > 4 * ((RAW_LIMIT + RAW_LIMIT // 1000 + 66) // 3)
    ):
        raise ValueError("Invalid bounded complete-state anchor envelope")
    row = loader(anchor_seq)  # Exactly one direct lookup. Never a recursive decode.
    if (
        row is None
        or row["seq"] != anchor_seq
        or row["kind"] != "checkpoint"
        or row["version"] != version
        or row["received_us"] // MINUTE_US != received_us // MINUTE_US
        or row["payload"].get("storage_codec") == CODEC
        or "anchor_seq" in row["payload"]
        or "anchor_raw_sha256" in row["payload"]
    ):
        raise ValueError("Missing, future-minute, different-version or chained anchor")
    anchor_raw = canonical(decode_record(row["payload"], CHECKPOINT))
    if hashlib.sha256(anchor_raw).hexdigest() != value["anchor_raw_sha256"]:
        raise ValueError("Independent complete anchor raw hash differs")
    compressed = base64.b64decode(value["compressed_json"], validate=True)
    decoder = zlib.decompressobj(zdict=anchor_raw[-DICT_LIMIT:])
    raw = decoder.decompress(compressed, size + 1)
    if (
        len(raw) != size
        or not decoder.eof
        or decoder.unused_data
        or decoder.unconsumed_tail
        or hashlib.sha256(raw).hexdigest() != value["raw_sha256"]
    ):
        raise ValueError("Truncated, trailing, oversized or corrupt full-state stream")
    result = json.loads(raw)
    if canonical(result) != raw or any(
        key not in result or type(result[key]) is not type(value[key]) or result[key] != value[key]
        for key in RESTORE_FIELDS
    ):
        raise ValueError("Complete-state bytes/recovery fields differ")
    return raw


def boundary_checks():
    first = {
        "last_tick_ms": 120_000,
        "observed_seconds": 1.0,
        "healthy_seconds": 0.0,
        "last_healthy": False,
        "accounts": {"candidate": {"pending": {}}},
    }
    second = {**first, "last_tick_ms": 121_000, "observed_seconds": 2.0}
    anchor = {
        "seq": 1,
        "received_us": 120_000_000,
        "version": "explicit_diagnostic",
        "kind": "checkpoint",
        "payload": encode_record(first, CHECKPOINT),
        "raw": canonical(first),
    }
    value = envelope(encode_record(second, CHECKPOINT), canonical(second), anchor)
    context = {"seq": 2, "received_us": 121_000_000, "version": anchor["version"]}
    calls = []

    def loader(seq):
        calls.append(seq)
        return anchor

    assert bounded_expand(value, **context, loader=loader) == canonical(second)
    assert calls == [1]
    bad_values = [
        {**value, "anchor_seq": 2},
        {**value, "anchor_seq": True},
        {**value, "anchor_raw_sha256": "0" * 64},
        {**value, "raw_bytes": RAW_LIMIT + 1},
        {**value, "raw_bytes": 1},
        {**value, "raw_sha256": "0" * 64},
        {**value, "last_healthy": 0},
    ]
    data = base64.b64decode(value["compressed_json"])
    for changed in (data[:-1], data + b"tail", data + zlib.compress(b"{}")):
        bad_values.append({**value, "compressed_json": base64.b64encode(changed).decode()})
    refused = 0
    for bad in bad_values:
        try:
            bounded_expand(bad, **context, loader=lambda _seq: anchor)
        except (ValueError, zlib.error):
            refused += 1
        else:
            raise RuntimeError("Invalid anchor stream was accepted")
    bad_anchors = [
        None,
        {**anchor, "received_us": 60_000_000},
        {**anchor, "version": "other"},
        {**anchor, "kind": "heartbeat"},
        {**anchor, "payload": value},
    ]
    for bad in bad_anchors:
        try:
            bounded_expand(value, **context, loader=lambda _seq, bad=bad: bad)
        except (ValueError, zlib.error):
            refused += 1
        else:
            raise RuntimeError("Missing or chained anchor was accepted")
    return {
        "exact_complete_raw_roundtrip": True,
        "valid_lookup_count": 1,
        "invalid_inputs_refused": refused,
        "recursive_lookup_count": 0,
    }


def measure(path):
    if (
        not path.is_relative_to(STATE.resolve())
        or path.stat().st_size > 32_000_000
        or (
            path.with_name(path.name + "-wal").exists()
            and path.with_name(path.name + "-wal").stat().st_size != 0
        )
    ):
        raise ValueError("Small closed synthetic journal required")
    before = digest(path)
    result = {
        "path": str(path),
        "sha256": before,
        "checkpoints": 0,
        "independent_anchors": 0,
        "dependent_full_states": 0,
        "existing_envelope_total_bytes": 0,
        "anchor_envelope_total_bytes": 0,
        "existing_peak_bytes": 0,
        "independent_peak_bytes": 0,
        "dependent_peak_bytes": 0,
        "decoded_peak_bytes": 0,
        "dictionary_peak_bytes": 0,
        "anchors": [],
        "all_roundtrip_bytes_exact": True,
        "maximum_anchor_lookup_per_record": 0,
    }
    anchor = None
    stream = hashlib.sha256()
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("SELECT COUNT(*) FROM records").fetchone()[0] > 50_000:
            raise ValueError("Row bound exceeded")
        for row in db.execute("SELECT * FROM records WHERE kind='checkpoint' ORDER BY seq"):
            if len(row["payload"].encode()) > 3_000_000:
                raise ValueError("Single record input exceeds bound")
            stored = json.loads(row["payload"])
            original = decode_record(stored, CHECKPOINT)
            raw = canonical(original)
            existing = encode_record(original, CHECKPOINT)
            old_size = len(canonical(existing))
            minute = row["received_us"] // MINUTE_US
            if anchor is None or anchor["received_us"] // MINUTE_US != minute:
                anchor = {
                    "seq": row["seq"],
                    "received_us": row["received_us"],
                    "kind": "checkpoint",
                    "version": row["version"],
                    "payload": existing,
                    "raw": raw,
                }
                proposed = existing
                restored = canonical(decode_record(proposed, CHECKPOINT))
                result["independent_anchors"] += 1
                result["independent_peak_bytes"] = max(result["independent_peak_bytes"], old_size)
                result["anchors"].append(
                    {
                        "seq": row["seq"],
                        "minute_us": minute * MINUTE_US,
                        "raw_bytes": len(raw),
                        "raw_sha256": hashlib.sha256(raw).hexdigest(),
                        "dictionary_bytes": min(len(raw), DICT_LIMIT),
                    }
                )
            else:
                proposed = envelope(existing, raw, anchor)
                calls = []

                def loader(seq, lookup_calls=calls, independent_anchor=anchor):
                    lookup_calls.append(seq)
                    return independent_anchor

                restored = bounded_expand(
                    proposed,
                    seq=row["seq"],
                    received_us=row["received_us"],
                    version=row["version"],
                    loader=loader,
                )
                if calls != [anchor["seq"]]:
                    raise RuntimeError("More than one direct independent anchor was read")
                result["maximum_anchor_lookup_per_record"] = 1
                result["dependent_full_states"] += 1
                result["dependent_peak_bytes"] = max(
                    result["dependent_peak_bytes"], len(canonical(proposed))
                )
            if restored != raw:
                raise RuntimeError("Minute dictionary did not preserve complete state bytes")
            result["checkpoints"] += 1
            result["existing_envelope_total_bytes"] += old_size
            result["anchor_envelope_total_bytes"] += len(canonical(proposed))
            result["existing_peak_bytes"] = max(result["existing_peak_bytes"], old_size)
            result["decoded_peak_bytes"] = max(result["decoded_peak_bytes"], len(raw))
            result["dictionary_peak_bytes"] = max(
                result["dictionary_peak_bytes"], min(len(anchor["raw"]), DICT_LIMIT)
            )
            stream.update(row["seq"].to_bytes(8, "big") + len(raw).to_bytes(8, "big") + raw)
    if digest(path) != before:
        raise RuntimeError("Original journal changed during readonly compression diagnostic")
    result.update(
        expanded_checkpoint_stream_sha256=stream.hexdigest(),
        journal_unchanged=True,
        complete_envelope_bytes_saved=result["existing_envelope_total_bytes"]
        - result["anchor_envelope_total_bytes"],
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--funded", type=Path, required=True)
    parser.add_argument("--empty", type=Path, required=True)
    parser.add_argument("--normal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipts = {name: getattr(args, name).resolve() for name in ("funded", "empty", "normal")}
    output = args.output.resolve()
    if (
        output.exists()
        or not output.is_relative_to((ROOT / "reports").resolve())
        or any(
            not path.is_relative_to((ROOT / "reports").resolve()) or path.stat().st_size > 2_000_000
            for path in receipts.values()
        )
    ):
        raise ValueError("Bounded D receipts and exclusive output required")
    documents = {name: json.loads(path.read_text()) for name, path in receipts.items()}
    if (
        documents["funded"]["status"] != "FUNDED_CONGESTION_ENGINEERING_DIAGNOSTIC_ONLY"
        or documents["empty"]["status"] != "SHORT_CONGESTION_ENGINEERING_DIAGNOSTIC_ONLY"
        or documents["normal"]["status"] != "COMPLETE_NORMAL_SYNTHETIC_PATH_ONLY"
    ):
        raise ValueError("Only actual explicit synthetic receipts are allowed")
    paths = {
        name: Path(row["probe"]["database_paths"]["journal"]).resolve()
        for name, row in documents.items()
        if name != "normal"
    }
    paths["normal"] = Path(documents["normal"]["database_paths"]["journal"]).resolve()
    if (
        digest(paths["funded"])
        != documents["funded"]["probe"]["final_database_sha256"]["journal.sqlite3"]
        or digest(paths["normal"]) != documents["normal"]["file_sha256"]["journal.sqlite3"]
    ):
        raise RuntimeError("Frozen closed journal digest differs")
    bound = {
        str(path.relative_to(ROOT)): digest(path)
        for path in (*receipts.values(), Path(__file__), ROOT / "src/quant/candidate_storage.py")
    }
    started = time.monotonic()
    document = {
        "status": "READONLY_MINUTE_ANCHOR_FULL_STATE_DIAGNOSTIC_ONLY",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_hashes": bound,
        "policy": {
            "one_independent_first_checkpoint_per_received_minute": True,
            "every_dependent_body_is_complete_raw_not_semantic_delta": True,
            "max_dictionary_bytes": DICT_LIMIT,
            "dictionary": "tail of complete independent raw",
            "anchor_must_be_earlier_same_minute_same_version_checkpoint": True,
            "dependent_metadata": ["anchor_seq", "anchor_raw_sha256"],
            "maximum_direct_anchor_reads": 1,
            "recursive_dictionary": False,
        },
        "boundary_checks": boundary_checks(),
        "journals": {},
        "resources_before": status(),
        "source_rows_or_codec_changed": False,
        "capacity_accepted": False,
        "production_authorized": False,
        "actual_qualification_days": 0,
        "network_requests": 0,
        "training_fits": 0,
        "limitations": (
            "Closed JSON encoding only. No actual database append-growth or capacity proof."
        ),
    }
    failure = None
    try:
        for name, path in paths.items():
            document["journals"][name] = measure(path)
        if bound != {
            str(path.relative_to(ROOT)): digest(path)
            for path in (
                *receipts.values(),
                Path(__file__),
                ROOT / "src/quant/candidate_storage.py",
            )
        }:
            raise RuntimeError("Bound source or receipts changed during diagnostic")
    except Exception as error:
        failure = error
        document.update(
            status="MINUTE_ANCHOR_DIAGNOSTIC_FAILED_NOT_ACCEPTED",
            error_type=type(error).__name__,
            error=str(error),
        )
    document.update(elapsed_seconds=time.monotonic() - started, resources_after=status())
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(document, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "status": document["status"],
                "journals": {
                    name: {key: value for key, value in row.items() if key != "anchors"}
                    for name, row in document["journals"].items()
                },
            }
        )
    )
    if failure is not None:
        raise failure


if __name__ == "__main__":
    main()
