"""Bounded, lossless candidate journal encoding; no account or execution changes."""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import re
import zlib
from collections.abc import Callable
from dataclasses import dataclass

from .holdout import HoldoutDenied

CODEC = "candidate_zlib_json_v1"
ANCHOR_CODEC = "candidate_minute_anchor_json_v2"
CHECKPOINT = "financial_checkpoint"
FEATURE_SNAPSHOT = "feature_provider_snapshot"
RESTORE_FIELDS = ("last_tick_ms", "observed_seconds", "healthy_seconds", "last_healthy")
_EXPOSED = {CHECKPOINT: RESTORE_FIELDS, FEATURE_SNAPSHOT: ()}
_RAW_LIMITS = {CHECKPOINT: 1_048_576, FEATURE_SNAPSHOT: 2_097_152}
_HEADER = {"storage_codec", "storage_kind", "raw_bytes", "raw_sha256", "compressed_json"}
_ANCHOR_HEADER = {"anchor_seq", "anchor_raw_sha256"}
_MINUTE_US = 60_000_000


@dataclass(frozen=True)
class CheckpointContext:
    """Authenticated journal metadata, supplied by the owning engine."""

    seq: int
    received_us: int
    version: str
    binding_sha256: str


AnchorLoader = Callable[[int], tuple[dict, CheckpointContext] | None]


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


def _valid_context(context: CheckpointContext) -> None:
    if (
        not isinstance(context, CheckpointContext)
        or type(context.seq) is not int
        or context.seq <= 0
        or type(context.received_us) is not int
        or context.received_us < 0
        or not isinstance(context.version, str)
        or not context.version
        or not isinstance(context.binding_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", context.binding_sha256) is None
    ):
        raise HoldoutDenied("候选分钟锚认证上下文无效")


def _anchor_bytes(
    value: dict, anchor_context: CheckpointContext, context: CheckpointContext
) -> bytes:
    _valid_context(context)
    _valid_context(anchor_context)
    if (
        anchor_context.seq >= context.seq
        or anchor_context.received_us > context.received_us
        or anchor_context.received_us // _MINUTE_US != context.received_us // _MINUTE_US
        or anchor_context.version != context.version
        or anchor_context.binding_sha256 != context.binding_sha256
        or value.get("candidate_binding_sha256") != context.binding_sha256
    ):
        raise HoldoutDenied("候选分钟锚序号/时间/版本/immutable binding无效")
    raw = _json_bytes(value)
    if not 0 < len(raw) <= _limit(CHECKPOINT):
        raise HoldoutDenied("候选分钟锚完整状态越过固定存储边界")
    return raw


def encode_checkpoint(
    value: dict,
    context: CheckpointContext,
    *,
    anchor: tuple[dict, CheckpointContext] | None = None,
) -> dict:
    """Compress complete financial JSON against one same-minute independent anchor."""
    _valid_context(context)
    if value.get("candidate_binding_sha256") != context.binding_sha256:
        raise HoldoutDenied("候选完整金融状态immutable binding无效")
    envelope = encode_record(value, CHECKPOINT)
    if anchor is None:
        return envelope
    anchor_value, anchor_context = anchor
    anchor_raw = _anchor_bytes(anchor_value, anchor_context, context)
    raw = _json_bytes(value)
    compressor = zlib.compressobj(level=9, zdict=anchor_raw[-32768:])
    envelope.update(
        storage_codec=ANCHOR_CODEC,
        anchor_seq=anchor_context.seq,
        anchor_raw_sha256=hashlib.sha256(anchor_raw).hexdigest(),
        compressed_json=base64.b64encode(
            compressor.compress(raw) + compressor.flush()
        ).decode("ascii"),
    )
    return envelope


def decode_record(
    envelope: dict,
    kind: str,
    *,
    context: CheckpointContext | None = None,
    anchor_loader: AnchorLoader | None = None,
) -> dict:
    """Expand bounded JSON; a dependent CP requires one authenticated anchor lookup."""
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
        dependent = envelope.get("storage_codec") == ANCHOR_CODEC
        dictionary = None
        if dependent:
            if kind != CHECKPOINT or context is None or anchor_loader is None:
                raise ValueError("dependent checkpoint needs authenticated journal context")
            _valid_context(context)
            anchor_seq = envelope.get("anchor_seq")
            anchor_digest = envelope.get("anchor_raw_sha256")
            if (
                type(anchor_seq) is not int
                or not 0 < anchor_seq < context.seq
                or not isinstance(anchor_digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", anchor_digest) is None
            ):
                raise ValueError("dependent checkpoint anchor header differs")
            # No recursive call with a loader: this permits exactly one independent
            # anchor expansion plus this complete checkpoint expansion.
            anchor = anchor_loader(anchor_seq)
            if anchor is None:
                raise ValueError("dependent checkpoint anchor is missing")
            anchor_envelope, anchor_context = anchor
            _valid_context(anchor_context)
            if (
                anchor_context.seq != anchor_seq
                or not isinstance(anchor_envelope, dict)
                or anchor_envelope.get("storage_codec") not in (None, CODEC)
            ):
                raise ValueError("dependent checkpoint anchor is not independent")
            anchor_value = decode_record(anchor_envelope, CHECKPOINT)
            anchor_raw = _anchor_bytes(anchor_value, anchor_context, context)
            if hashlib.sha256(anchor_raw).hexdigest() != anchor_digest:
                raise ValueError("dependent checkpoint anchor hash differs")
            dictionary = anchor_raw[-32768:]
        if (
            set(envelope) != (
                _HEADER | set(_EXPOSED[kind]) | (_ANCHOR_HEADER if dependent else set())
            )
            or envelope["storage_codec"] != (ANCHOR_CODEC if dependent else CODEC)
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
        decoder = zlib.decompressobj(zdict=dictionary) if dependent else zlib.decompressobj()
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
        if dependent and result.get("candidate_binding_sha256") != context.binding_sha256:
            raise ValueError("dependent checkpoint immutable binding differs")
        return result
    except (ValueError, TypeError, KeyError, RecursionError, binascii.Error, zlib.error) as error:
        raise HoldoutDenied("候选压缩状态合同/边界/完整性无效，禁止推测恢复") from error
