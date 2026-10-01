"""Bounded, lossless candidate journal encoding; no account or execution changes."""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import re
import zlib

from .holdout import HoldoutDenied

CODEC = "candidate_zlib_json_v1"
CHECKPOINT = "financial_checkpoint"
FEATURE_SNAPSHOT = "feature_provider_snapshot"
RESTORE_FIELDS = ("last_tick_ms", "observed_seconds", "healthy_seconds", "last_healthy")
_EXPOSED = {CHECKPOINT: RESTORE_FIELDS, FEATURE_SNAPSHOT: ()}
_RAW_LIMITS = {CHECKPOINT: 1_048_576, FEATURE_SNAPSHOT: 2_097_152}
_HEADER = {"storage_codec", "storage_kind", "raw_bytes", "raw_sha256", "compressed_json"}


def _json_bytes(value: dict) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate candidate JSON key")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ValueError("non-finite candidate JSON number")


def _limit(kind: str) -> int:
    if kind not in _RAW_LIMITS:
        raise HoldoutDenied("未知候选存储记录类型")
    return _RAW_LIMITS[kind]


def encode_record(value: dict, kind: str) -> dict:
    """Store the complete JSON object and expose only parent recovery fields."""
    limit = _limit(kind)
    try:
        if not isinstance(value, dict) or "storage_codec" in value:
            raise ValueError("invalid candidate object")
        raw = _json_bytes(value)
        if not 0 < len(raw) <= limit:
            raise ValueError("candidate object exceeds fixed bound")
        exposed = {key: copy.deepcopy(value[key]) for key in _EXPOSED[kind]}
        return {
            "storage_codec": CODEC,
            "storage_kind": kind,
            "raw_bytes": len(raw),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "compressed_json": base64.b64encode(zlib.compress(raw, level=9)).decode("ascii"),
            **exposed,
        }
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        raise HoldoutDenied("候选完整状态不能按固定存储合同编码") from error


def decode_record(envelope: dict, kind: str) -> dict:
    """Authenticate and expand once, with fixed input/output bounds and no tails."""
    limit = _limit(kind)
    if not isinstance(envelope, dict):
        raise HoldoutDenied("候选存储记录必须是JSON对象")
    # Parent initialization and explicitly preserved legacy/plain anchors are JSON.
    if "storage_codec" not in envelope:
        try:
            if not 0 < len(_json_bytes(envelope)) <= limit:
                raise ValueError("plain candidate object exceeds fixed bound")
            return copy.deepcopy(envelope)
        except (ValueError, TypeError, RecursionError) as error:
            raise HoldoutDenied("候选旧JSON状态越过固定存储边界") from error
    try:
        if (
            set(envelope) != _HEADER | set(_EXPOSED[kind])
            or envelope["storage_codec"] != CODEC
            or envelope["storage_kind"] != kind
        ):
            raise ValueError("candidate codec/header contract differs")
        size, digest, encoded = (
            envelope["raw_bytes"],
            envelope["raw_sha256"],
            envelope["compressed_json"],
        )
        # zlib's finite overhead is smaller than one byte per 1000 plus 64 bytes.
        encoded_limit = 4 * ((limit + limit // 1000 + 66) // 3)
        if (
            type(size) is not int
            or not 0 < size <= limit
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or not isinstance(encoded, str)
            or not 0 < len(encoded) <= encoded_limit
        ):
            raise ValueError("candidate codec size/hash bound differs")
        compressed = base64.b64decode(encoded, validate=True)
        if base64.b64encode(compressed).decode("ascii") != encoded:
            raise ValueError("candidate base64 is not canonical")
        decoder = zlib.decompressobj()
        raw = decoder.decompress(compressed, size + 1)
        if (
            len(raw) != size
            or not decoder.eof
            or decoder.unconsumed_tail
            or decoder.unused_data
            or hashlib.sha256(raw).hexdigest() != digest
        ):
            raise ValueError("candidate compressed state is incomplete or corrupt")
        result = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_object, parse_constant=_invalid_constant
        )
        if not isinstance(result, dict) or "storage_codec" in result:
            raise ValueError("candidate decoded object is invalid")
        if _json_bytes(result) != raw:
            raise ValueError("candidate decoded JSON is not canonical")
        if any(
            key not in result
            or type(result[key]) is not type(envelope[key])
            or result[key] != envelope[key]
            for key in _EXPOSED[kind]
        ):
            raise ValueError("candidate recovery fields differ from complete state")
        return result
    except (ValueError, TypeError, KeyError, RecursionError, binascii.Error, zlib.error) as error:
        raise HoldoutDenied("候选压缩状态合同/边界/完整性无效，禁止推测恢复") from error
