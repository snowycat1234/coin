"""Lossless bounded journal codecs; no market, model, or trading evaluation."""

import base64
import copy
import hashlib
import json
import zlib
from dataclasses import replace

import pytest

from quant.candidate_storage import (
    ANCHOR_CODEC,
    CHECKPOINT,
    CODEC,
    FEATURE_SNAPSHOT,
    CheckpointContext,
    decode_record,
    encode_checkpoint,
    encode_record,
)
from quant.holdout import HoldoutDenied


def financial():
    return {
        "last_tick_ms": 1_735_689_600_000,
        "observed_seconds": 17.25,
        "healthy_seconds": 8.125,
        "last_healthy": True,
        "candidate_binding_sha256": "a" * 64,
        "accounts": {
            "candidate": {
                "cash": 9876.54321,
                "positions": {"BTCUSDT": 0.125},
                "pending": {"unicode": "完整金融状态"},
            }
        },
        "attempt_counts": list(range(300)),
    }


@pytest.mark.parametrize("kind", [CHECKPOINT, FEATURE_SNAPSHOT])
def test_complete_json_roundtrip_is_exact_and_inputs_remain_unchanged(kind):
    value = financial()
    before = copy.deepcopy(value)
    envelope = encode_record(value, kind)
    assert decode_record(envelope, kind) == before
    assert value == before
    assert len(json.dumps(envelope).encode()) < len(json.dumps(before).encode())
    if kind == CHECKPOINT:
        assert envelope["last_healthy"] is True
        assert "candidate_binding_sha256" not in envelope
    else:
        assert "accounts" not in envelope


@pytest.mark.parametrize(
    "change",
    [
        {"raw_bytes": True},
        {"raw_bytes": 0},
        {"raw_bytes": 1_048_577},
        {"raw_sha256": "0" * 64},
        {"storage_codec": "unknown"},
        {"storage_kind": FEATURE_SNAPSHOT},
        {"last_healthy": 1},
        {"healthy_seconds": 999.0},
        {"extra": "not declared"},
        {"compressed_json": "!"},
        {"compressed_json": "A" * 1_400_000},
    ],
)
def test_corrupt_header_data_or_recovery_fields_are_refused(change):
    envelope = encode_record(financial(), CHECKPOINT)
    envelope.update(change)
    with pytest.raises(HoldoutDenied):
        decode_record(envelope, CHECKPOINT)


@pytest.mark.parametrize("mutation", ["truncated", "tail", "second_stream", "bomb"])
def test_decompressor_refuses_incomplete_tails_and_declared_size_overrun(mutation):
    envelope = encode_record(financial(), CHECKPOINT)
    compressed = base64.b64decode(envelope["compressed_json"])
    if mutation == "truncated":
        compressed = compressed[:-1]
    elif mutation == "tail":
        compressed += b"tail"
    elif mutation == "second_stream":
        compressed += zlib.compress(b"{}")
    else:
        compressed = zlib.compress(b"x" * 500_000)
        envelope["raw_bytes"] = 1024
    envelope["compressed_json"] = base64.b64encode(compressed).decode()
    with pytest.raises(HoldoutDenied):
        decode_record(envelope, CHECKPOINT)


@pytest.mark.parametrize("raw", [b'{"same":1,"same":2}', b'{"x":NaN}', b"[]", b"\xff", b'{"x": 1}'])
def test_noncanonical_invalid_or_duplicate_json_is_refused(raw):
    envelope = {
        "storage_codec": CODEC,
        "storage_kind": FEATURE_SNAPSHOT,
        "raw_bytes": len(raw),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "compressed_json": base64.b64encode(zlib.compress(raw)).decode(),
    }
    with pytest.raises(HoldoutDenied):
        decode_record(envelope, FEATURE_SNAPSHOT)


def test_plain_initial_checkpoint_and_legacy_anchor_are_supported_with_bounds():
    value = financial()
    restored = decode_record(value, CHECKPOINT)
    assert restored == value and restored is not value
    with pytest.raises(HoldoutDenied):
        decode_record({"oversized": "x" * 1_048_576}, CHECKPOINT)
    with pytest.raises(HoldoutDenied):
        encode_record({"nonfinite": float("nan")}, FEATURE_SNAPSHOT)
    with pytest.raises(HoldoutDenied):
        encode_record({"oversized": "x" * 2_097_152}, FEATURE_SNAPSHOT)


def minute_anchor():
    value = financial()
    context = CheckpointContext(10, value["last_tick_ms"] * 1000, "bound-version", "a" * 64)
    current = copy.deepcopy(value)
    current["accounts"]["candidate"]["cash"] -= 0.125
    current["attempt_counts"].append(300)
    target = replace(context, seq=11)
    envelope = encode_checkpoint(current, target, anchor=(value, context))
    return value, context, current, target, envelope


def test_minute_anchor_complete_roundtrip_uses_one_lookup_and_allows_equal_timestamp():
    value, context, current, target, envelope = minute_anchor()
    lookups = []

    def loader(seq):
        lookups.append(seq)
        return encode_record(value, CHECKPOINT), context

    assert envelope["storage_codec"] == ANCHOR_CODEC
    assert decode_record(envelope, CHECKPOINT, context=target, anchor_loader=loader) == current
    assert lookups == [context.seq]
    assert len(json.dumps(envelope)) < len(json.dumps(encode_record(current, CHECKPOINT)))
    assert current != value
    with pytest.raises(HoldoutDenied):
        decode_record(envelope, CHECKPOINT)
    # An independent first checkpoint and the existing feature codec remain v1.
    assert encode_checkpoint(value, context)["storage_codec"] == CODEC
    assert encode_record(value, FEATURE_SNAPSHOT)["storage_codec"] == CODEC


@pytest.mark.parametrize(
    "mutation",
    [
        "missing", "future_seq", "bool_seq", "wrong_seq", "later_time", "other_minute",
        "other_version", "other_binding", "wrong_anchor_hash", "damaged_anchor", "chain",
        "wrong_current_binding", "truncated", "tail", "second_stream", "bomb",
    ],
)
def test_minute_anchor_rejects_invalid_references_and_bounded_streams(mutation):
    value, context, _current, target, envelope = minute_anchor()
    anchor = encode_record(value, CHECKPOINT)
    if mutation == "future_seq":
        envelope["anchor_seq"] = target.seq
    elif mutation == "bool_seq":
        envelope["anchor_seq"] = True
    elif mutation == "wrong_seq":
        context = replace(context, seq=9)
    elif mutation == "later_time":
        context = replace(context, received_us=context.received_us + 1)
    elif mutation == "other_minute":
        context = replace(context, received_us=context.received_us - 60_000_000)
    elif mutation == "other_version":
        context = replace(context, version="other-version")
    elif mutation == "other_binding":
        context = replace(context, binding_sha256="b" * 64)
    elif mutation == "wrong_anchor_hash":
        envelope["anchor_raw_sha256"] = "0" * 64
    elif mutation == "damaged_anchor":
        anchor["raw_sha256"] = "0" * 64
    elif mutation == "chain":
        anchor = copy.deepcopy(envelope)
    elif mutation == "wrong_current_binding":
        changed = copy.deepcopy(financial())
        changed["candidate_binding_sha256"] = "b" * 64
        with pytest.raises(HoldoutDenied):
            encode_checkpoint(changed, target, anchor=(value, context))
        return
    elif mutation in {"truncated", "tail", "second_stream", "bomb"}:
        compressed = base64.b64decode(envelope["compressed_json"])
        if mutation == "truncated":
            compressed = compressed[:-1]
        elif mutation == "tail":
            compressed += b"tail"
        elif mutation == "second_stream":
            compressed += zlib.compress(b"{}")
        else:
            compressor = zlib.compressobj(zdict=b"unused")
            compressed = compressor.compress(b"x" * 500_000) + compressor.flush()
            envelope["raw_bytes"] = 1024
        envelope["compressed_json"] = base64.b64encode(compressed).decode()
    lookups = []

    def loader(seq):
        lookups.append(seq)
        return None if mutation == "missing" else (anchor, context)

    with pytest.raises(HoldoutDenied):
        decode_record(envelope, CHECKPOINT, context=target, anchor_loader=loader)
    assert len(lookups) <= 1
