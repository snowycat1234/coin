"""Bounded readonly preset-dictionary encoding diagnostic, never production admission."""

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

from quant.candidate_storage import (
    CHECKPOINT,
    FEATURE_SNAPSHOT,
    RESTORE_FIELDS,
    decode_record,
    encode_record,
)
from quant.features_v2 import FEATURE_NAMES_V2
from quant.paths import ROOT, STATE
from quant.resources import status

# Fixed key names are declared before reading any journal. No market/account
# values, inferred frequent substrings, fitted dictionary, or research choices.
KEY_NAMES = tuple(
    sorted(
        set(
            """
accounts account_controls B0 B2 candidate fee_x2 slippage_x2 BTCUSDT ETHUSDT
cash positions pending cycles entry_ms cost proceeds fees order_id account symbol
target_weight decision_ms decision_us signal_received_ms not_before_ms expires_ms
execution_contract_version minimum_hold_minutes risk_forced_exit capacity_used
consumed_quotes alpha_holding decision_policy last_raw awaiting_first_fill
first_fill_ms long entry_execution_us last_us started_ms last_tick_ms last_healthy
last_checkpoint_ms last_heartbeat_ms observed_seconds healthy_seconds last_day
last_signal_hour strategy_state freeze_reasons trend last_hour fast slow count
last_valid last_evidence hour_open_ms minutes last_received_ms source_hash ema_count
candidate_binding_sha256 feature_anchors provider last_candidate_end candidate_fault
features implementation_sha256 model_sha256 release_sha256 dependencies strategy
source interval prediction_horizon prediction_semantics schema_version model_type
contract state state_sha256 _hourly symbols pending_minutes last_open_us latest
last_minute_open_us last_boundary_us last_boundary_complete last_available_us ema
rows last_asof_us last_emitted_end_us unpaired_hours_discarded bar values ready
returns24 name dtype definition version schema_sha256 definition_sha256
symbol interval open_us close_us available_us received_us open high low close
volume quote_volume taker_buy_base taker_buy_quote emitted_asof_us local_available_us
other_available_us local_received_us other_received_us feature_ready configuration
feature_schema execution_contract cost_contract risk_contract binding
""".split()
        )
        | set(FEATURE_NAMES_V2)
    )
)
FRAGMENTS = ('":null,', '":true,', '":false,', '":{},', '":[],', "},{", "]}", "}}", '":[{')
DIAGNOSTIC_CODEC = "candidate_zdict_json_diagnostic_v1"
LIMITS = {CHECKPOINT: 1_048_576, FEATURE_SNAPSHOT: 2_097_152}


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


def fixed_dictionary():
    raw = b"".join(json.dumps(name).encode() + b":" for name in KEY_NAMES)
    raw += "".join(FRAGMENTS).encode()
    if not 0 < len(raw) <= 32768:
        raise RuntimeError("Fixed dictionary exceeds 32 KB bound")
    return raw


DICTIONARY = fixed_dictionary()
DICTIONARY_SHA = hashlib.sha256(DICTIONARY).hexdigest()


def dictionary_envelope(existing, raw):
    compressor = zlib.compressobj(level=9, zdict=DICTIONARY)
    compressed = compressor.compress(raw) + compressor.flush()
    return {
        **existing,
        "storage_codec": DIAGNOSTIC_CODEC,
        "dictionary_sha256": DICTIONARY_SHA,
        "compressed_json": base64.b64encode(compressed).decode("ascii"),
    }


def bounded_expand(envelope):
    kind = envelope["storage_kind"]
    size = envelope["raw_bytes"]
    limit = LIMITS[kind]
    fields = {
        "storage_codec",
        "storage_kind",
        "raw_bytes",
        "raw_sha256",
        "compressed_json",
        "dictionary_sha256",
    }
    fields |= set(RESTORE_FIELDS) if kind == CHECKPOINT else set()
    if (
        set(envelope) != fields
        or envelope["storage_codec"] != DIAGNOSTIC_CODEC
        or envelope["dictionary_sha256"] != DICTIONARY_SHA
        or type(size) is not int
        or not 0 < size <= limit
        or len(envelope["compressed_json"]) > 4 * ((limit + limit // 1000 + 66) // 3)
    ):
        raise ValueError("Fixed diagnostic dictionary/header/size differs")
    compressed = base64.b64decode(envelope["compressed_json"], validate=True)
    decoder = zlib.decompressobj(zdict=DICTIONARY)
    raw = decoder.decompress(compressed, size + 1)
    if (
        len(raw) != size
        or not decoder.eof
        or decoder.unused_data
        or decoder.unconsumed_tail
        or hashlib.sha256(raw).hexdigest() != envelope["raw_sha256"]
    ):
        raise ValueError("Bounded dictionary stream/hash differs")
    return raw


def boundary_checks():
    value = {"state": {"pending": {}}, "contract": {}}
    original = encode_record(value, FEATURE_SNAPSHOT)
    envelope = dictionary_envelope(original, canonical(value))
    assert bounded_expand(envelope) == canonical(value)
    mutations = []
    wrong = {**envelope, "dictionary_sha256": "0" * 64}
    mutations.append(wrong)
    data = base64.b64decode(envelope["compressed_json"])
    for changed in (data[:-1], data + b"tail", data + zlib.compress(b"{}")):
        mutations.append({**envelope, "compressed_json": base64.b64encode(changed).decode()})
    mutations.append({**envelope, "raw_bytes": 1})
    mutations.append({**envelope, "raw_bytes": 2_097_153})
    mutations.append({**envelope, "raw_bytes": True})
    for invalid in mutations:
        try:
            bounded_expand(invalid)
        except (ValueError, zlib.error):
            continue
        raise RuntimeError("Dictionary boundary fixture was incorrectly accepted")
    return {"exact_roundtrip": True, "invalid_inputs_refused": len(mutations)}


def measure_journal(path):
    if (
        not path.is_relative_to(STATE.resolve())
        or path.stat().st_size > 32_000_000
        or (
            path.with_name(path.name + "-wal").exists()
            and path.with_name(path.name + "-wal").stat().st_size != 0
        )
    ):
        raise ValueError("Small closed synthetic journal without WAL content required")
    before = digest(path)
    result = {"path": str(path), "sha256": before, "classes": {}}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        count = db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        if count > 50_000:
            raise ValueError("Journal row bound exceeded")
        result["journal_records"] = count
        result["head"] = db.execute(
            "SELECT seq,hash FROM records ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        for seq, kind, payload in db.execute(
            "SELECT seq,kind,payload FROM records WHERE kind IN "
            "('checkpoint','feature_provider_snapshot') ORDER BY seq"
        ):
            if len(payload.encode()) > 3_000_000:
                raise ValueError("Single record exceeds fixed input bound")
            codec_kind = CHECKPOINT if kind == "checkpoint" else FEATURE_SNAPSHOT
            stored = json.loads(payload)
            value = decode_record(stored, codec_kind)
            raw = canonical(value)
            existing = encode_record(value, codec_kind)
            proposed = dictionary_envelope(existing, raw)
            expanded = bounded_expand(proposed)
            if expanded != raw or json.loads(expanded) != value:
                raise RuntimeError("Dictionary did not preserve all original JSON bytes")
            if stored.get("storage_codec") and canonical(existing) != payload.encode():
                raise RuntimeError("Current zlib9 envelope cannot exactly reproduce actual record")
            old_size, new_size = len(canonical(existing)), len(canonical(proposed))
            item = result["classes"].setdefault(
                kind,
                {
                    "records": 0,
                    "stored_codec_records": 0,
                    "original_stored_bytes": 0,
                    "decoded_bytes": 0,
                    "existing_zlib9_envelope_bytes": 0,
                    "fixed_dict_envelope_bytes": 0,
                    "decoded_peak_bytes": 0,
                    "existing_envelope_peak_bytes": 0,
                    "dict_envelope_peak_bytes": 0,
                    "dictionary_larger_records": 0,
                    "all_roundtrip_bytes_exact": True,
                    "expanded_record_stream_sha256": hashlib.sha256(),
                },
            )
            item["records"] += 1
            item["stored_codec_records"] += int("storage_codec" in stored)
            item["original_stored_bytes"] += len(payload.encode())
            item["decoded_bytes"] += len(raw)
            item["existing_zlib9_envelope_bytes"] += old_size
            item["fixed_dict_envelope_bytes"] += new_size
            item["decoded_peak_bytes"] = max(item["decoded_peak_bytes"], len(raw))
            item["existing_envelope_peak_bytes"] = max(
                item["existing_envelope_peak_bytes"], old_size
            )
            item["dict_envelope_peak_bytes"] = max(item["dict_envelope_peak_bytes"], new_size)
            item["dictionary_larger_records"] += int(new_size > old_size)
            item["expanded_record_stream_sha256"].update(seq.to_bytes(8, "big"))
            item["expanded_record_stream_sha256"].update(len(raw).to_bytes(8, "big") + raw)
    if digest(path) != before:
        raise RuntimeError("Readonly journal changed during diagnostic")
    for item in result["classes"].values():
        item["expanded_record_stream_sha256"] = item["expanded_record_stream_sha256"].hexdigest()
        item["complete_envelope_bytes_saved"] = (
            item["existing_zlib9_envelope_bytes"] - item["fixed_dict_envelope_bytes"]
        )
    result["journal_unchanged"] = True
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
        raise ValueError("Only the actual explicit synthetic source receipts are in scope")
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
        raise RuntimeError("Frozen closed journal source digest differs")
    bound = {
        str(path.relative_to(ROOT)): digest(path)
        for path in (
            *receipts.values(),
            Path(__file__),
            ROOT / "src/quant/candidate_storage.py",
            ROOT / "src/quant/features_v2.py",
        )
    }
    started = time.monotonic()
    document = {
        "status": "READONLY_FIXED_DICTIONARY_ENCODING_DIAGNOSTIC_ONLY",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_hashes": bound,
        "dictionary": {
            "bytes": len(DICTIONARY),
            "sha256": DICTIONARY_SHA,
            "key_names": list(KEY_NAMES),
            "json_fragments": list(FRAGMENTS),
            "contains_market_or_account_values": False,
            "learned_from_journals": False,
        },
        "boundary_checks": boundary_checks(),
        "journals": {},
        "resources_before": status(),
        "capacity_accepted": False,
        "production_authorized": False,
        "source_rows_or_codec_changed": False,
        "training_fits": 0,
        "network_requests": 0,
        "actual_qualification_days": 0,
        "limitations": (
            "Existing closed JSON objects only; no live writer, capacity or alpha proof."
        ),
    }
    failure = None
    try:
        for name, path in paths.items():
            document["journals"][name] = measure_journal(path)
        if bound != {
            str(path.relative_to(ROOT)): digest(path)
            for path in (
                *receipts.values(),
                Path(__file__),
                ROOT / "src/quant/candidate_storage.py",
                ROOT / "src/quant/features_v2.py",
            )
        }:
            raise RuntimeError("Bound diagnostic source changed")
    except Exception as error:
        failure = error
        document.update(
            status="FIXED_DICTIONARY_DIAGNOSTIC_FAILED_NOT_ACCEPTED",
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
                "dictionary_bytes": len(DICTIONARY),
                "classes": {name: row["classes"] for name, row in document["journals"].items()},
            }
        )
    )
    if failure is not None:
        raise failure


if __name__ == "__main__":
    main()
