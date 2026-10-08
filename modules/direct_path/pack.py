"""Read only an explicitly SHA-approved, small native-producer input pack.

No market access, source execution, imputations, or fitting. Manifest identities
are producer provenance bound by the parent's approved SHA; this adapter does
not pretend to reverify absent full source/teacher files.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np

from .prototype import CORE5, DAY_US, E5, Context, finite
from .training import WINDOWS, stamp, validate_fragment, validate_training

SCHEMA = "DIRECT_PATH_TRAINING_PACK_V1"
FIELDS = ("decision_us", "available_us", "target_available_us", "expert_targets",
          "eligible", "past_returns30", "market13", "prices", "funding_coeff",
          "greedy_request", "label_available_us", "funding_event_us",
          "funding_symbol_index", "funding_mark_close_us", "funding_mark_price",
          "funding_rate_fraction")
MAX_MANIFEST_BYTES = 131072
MAX_NPZ_BYTES = 4000000
MAX_EXPANDED_BYTES = 8000000


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_sha(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def integer(array, shape, name):
    a = np.asarray(array)
    if a.shape != shape or a.dtype.kind not in "iu" or np.any(a < 0):
        raise ValueError("Nonnegative integer clocks/indices required: " + name)
    # Reject uint64 clocks that overflow the adapter's signed UTC microseconds.
    if np.any(a > np.iinfo(np.int64).max):
        raise ValueError("UTC clock exceeds int64: " + name)
    return a.astype(np.int64, copy=False)


def bounded_bytes(path, maximum):
    """Read once, cap allocation, then hash and parse this exact byte snapshot."""
    with Path(path).open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("Input exceeds its fixed byte bound")
    return data


def checked_npz_bytes(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        info = z.infolist()
        if (len(info) > 32 or len({i.filename for i in info}) != len(info)
                or sum(i.file_size for i in info) > MAX_EXPANDED_BYTES
                or any(not i.filename.endswith(".npy") or "/" in i.filename
                       or "\\" in i.filename or i.flag_bits & 1 for i in info)):
            raise ValueError("Small flat nonencrypted NPZ required")
    with np.load(io.BytesIO(data), allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def checked_npz(path):
    return checked_npz_bytes(bounded_bytes(path, MAX_NPZ_BYTES))


def fragment_from_arrays(a, entry, input_sha):
    tag = entry["window_id"]
    if tag not in WINDOWS:
        raise ValueError("Only the four preregistered periods are allowed")
    start, end = map(stamp, WINDOWS[tag])
    t = (end - start) // DAY_US
    d = integer(a["decision_us"], (t,), "decision_us")
    av = integer(a["available_us"], (t,), "available_us")
    ta = integer(a["target_available_us"], (t, 5), "target_available_us")
    targets = finite(a["expert_targets"], (t, 5, 5), "expert_targets")
    past = finite(a["past_returns30"], (t, 30, 5), "past_returns30")
    market = finite(a["market13"], (t, 13), "market13")
    mask = np.asarray(a["eligible"])
    if mask.shape != (t, 5) or mask.dtype != bool:
        raise ValueError("eligible must be bool[T,5]")
    p = finite(a["prices"], (t + 1, 5), "prices")
    if np.any(p <= 0):
        raise ValueError("Positive completed daily closes required")
    coeff = finite(a["funding_coeff"], (t, 5), "funding_coeff")
    teacher = finite(a["greedy_request"], (t, 5), "greedy_request")
    if not all(np.array_equal(row, np.eye(5)[np.argmax(row)]) for row in teacher[:-1]):
        raise ValueError("Original one-hot winner REQUEST required")
    labels = integer(a["label_available_us"], (t,), "label_available_us")
    contexts = [Context(int(d[i]), int(av[i]), targets[i], mask[i], past[i], market[i], ta[i])
                for i in range(t)]
    binding = dict(entry["binding"], input_npz_sha256=input_sha)
    f = dict(window_id=tag, contexts=contexts, prices=p, funding_coeff=coeff,
             greedy_request=teacher, label_available_us=labels, binding=binding)
    validate_fragment(f, tag)
    if entry.get("funding_events_complete") is not True:
        raise ValueError("Native producer must attest complete funding coverage")
    events = np.asarray(a["funding_event_us"])
    if events.ndim != 1 or len(events) > 10000:
        raise ValueError("Bounded complete funding event list required")
    n = len(events)
    events = integer(events, (n,), "funding_event_us")
    symbols = integer(a["funding_symbol_index"], (n,), "funding_symbol_index")
    marks_at = integer(a["funding_mark_close_us"], (n,), "funding_mark_close_us")
    marks = finite(a["funding_mark_price"], (n,), "funding_mark_price")
    rates = finite(a["funding_rate_fraction"], (n,), "funding_rate_fraction")
    if (np.any(symbols >= 5) or np.any(marks <= 0) or np.any(marks_at >= events)
            or np.any(events < start) or np.any(events > end)
            or len(set(zip(events.tolist(), symbols.tolist()))) != n):
        raise ValueError("Unique, in-period funding with strictly past positive marks required")
    rebuilt = np.zeros((t, 5))
    owned = events > start  # start event sees declared zero initial quantity
    np.add.at(rebuilt, ((events[owned] - start - 1) // DAY_US, symbols[owned]),
              marks[owned] * rates[owned])
    if not np.allclose(coeff, rebuilt, rtol=1e-12, atol=1e-12):
        raise ValueError("funding_coeff disagrees with complete signed strict-past events")
    if "features43" in a:
        supplied = finite(a["features43"], (t, 43), "features43")
        if not np.array_equal(supplied, np.array([c.features() for c in contexts])):
            raise ValueError("features43 differs from the frozen 13+25+5 feature construction")
    return f


def load_pack(manifest_path, approved_sha256):
    """Actual byte checks precede array parsing; return existing fragment dicts."""
    path = Path(manifest_path).resolve()
    raw = bounded_bytes(path, MAX_MANIFEST_BYTES)
    if not is_sha(approved_sha256) or hashlib.sha256(raw).hexdigest() != approved_sha256:
        raise ValueError("Exact parent-approved manifest SHA256 required")
    manifest = json.loads(raw.decode("utf-8"))
    if (manifest.get("schema") != SCHEMA or manifest.get("symbol_order") != list(CORE5)
            or manifest.get("expert_order") != list(E5)):
        raise ValueError("Exact input schema and E5/CORE5 order required")
    commit = manifest.get("source_commit")
    if (not isinstance(commit, str) or len(commit) != 40
            or any(c not in "0123456789abcdef" for c in commit)):
        raise ValueError("Immutable producer source_commit required")
    entries = manifest.get("fragments", [])
    if [e.get("window_id") for e in entries] != list(WINDOWS):
        raise ValueError("Exactly three training fragments then independent H1 validation")
    fragments, files = [], set()
    for entry in entries:
        name = entry.get("file")
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".npz"):
            raise ValueError("Flat relative NPZ filenames required")
        file = (path.parent / name).resolve()
        size = entry.get("bytes")
        if (file.parent != path.parent or file in files or type(size) is not int
                or not 0 < size <= MAX_NPZ_BYTES or not is_sha(entry.get("sha256"))):
            raise ValueError("Input bytes/size/path binding failed: " + name)
        raw = bounded_bytes(file, MAX_NPZ_BYTES)
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("Input bytes/size/path binding failed: " + name)
        files.add(file)
        arrays = checked_npz_bytes(raw)
        fmap = entry.get("field_map", {})
        if (not isinstance(fmap, dict) or any(k not in FIELDS + ("features43",) for k in fmap)
                or any(not isinstance(v, str) for v in fmap.values())):
            raise ValueError("Explicit canonical-to-producer field_map required")
        names = [fmap.get(k, k) for k in FIELDS]
        if len(set(names)) != len(names) or any(k not in arrays for k in names):
            raise ValueError("Missing or aliased required input fields")
        selected = {k: arrays[fmap.get(k, k)] for k in FIELDS}
        feature_name = fmap.get("features43", "features43")
        if feature_name in arrays:
            selected["features43"] = arrays[feature_name]
        fragments.append(fragment_from_arrays(selected, entry, entry["sha256"]))
    validate_training(fragments[:3])
    for key in ("expert_identity_sha256", "mapper_sha256"):
        if len({f["binding"][key] for f in fragments}) != 1:
            raise ValueError("Training and validation require identical frozen identities")
    return manifest, fragments
