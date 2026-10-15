"""Strict portable wire/byte helpers. No market I/O on import."""
from collections.abc import Mapping
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import stat
from types import MappingProxyType

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def sha(raw):
    if type(raw) is not bytes:
        raise ValueError('EXACT_BYTES_REQUIRED')
    return sha256(raw).hexdigest()


def digest(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('LOWERCASE_SHA256_REQUIRED')
    return value


def plain(value):
    if isinstance(value, Mapping):
        return {key: plain(v) for key, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def immutable(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: immutable(v) for key, v in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(immutable(v) for v in value)
    return value


def canonical(value):
    return json.dumps(plain(value), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def jsha(value):
    return sha(canonical(value))


def object_json(raw):
    if type(raw) is not bytes:
        raise ValueError('EXACT_JSON_BYTES_REQUIRED')
    def pairs(rows):
        out = {}
        for key, value in rows:
            if key in out:
                raise ValueError('DUPLICATE_JSON_KEY')
            out[key] = value
        return out
    try:
        return json.loads(raw, object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('STRICT_JSON_REQUIRED') from exc


def exact_object(raw):
    value = object_json(raw)
    if type(value) is not dict:
        raise ValueError('EXACT_JSON_OBJECT_REQUIRED')
    return value


def relative(name):
    if type(name) is not str:
        raise ValueError('PORTABLE_RELATIVE_PATH_REQUIRED')
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or str(path) != name or '\\' in name or not path.parts:
        raise ValueError('PORTABLE_RELATIVE_PATH_REQUIRED')
    return name


def exact(path, expected_sha, expected_bytes=None):
    digest(expected_sha)
    path = Path(os.path.abspath(path))
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('ORDINARY_NOFOLLOW_FILE_REQUIRED')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or expected_bytes is not None
                and (type(expected_bytes) is not int or info.st_size != expected_bytes)):
            raise ValueError('EXACT_SOURCE_BYTES_REQUIRED')
        raw = stream.read()
    if sha(raw) != expected_sha or expected_bytes is not None and len(raw) != expected_bytes:
        raise ValueError('EXACT_SOURCE_HASH_REQUIRED')
    return raw


def checked_external(raw, expected):
    digest(expected)
    if type(raw) is not bytes or sha(raw) != expected:
        raise ValueError('INDEPENDENT_EXTERNAL_EXPECTED_DIGEST_REQUIRED')
    return exact_object(raw)
