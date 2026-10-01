"""Lossless bounded journal codecs; no market, model, or trading evaluation."""

import base64
import copy
import hashlib
import json
import zlib

import pytest

from quant.candidate_storage import (
    CHECKPOINT,
    CODEC,
    FEATURE_SNAPSHOT,
    decode_record,
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
