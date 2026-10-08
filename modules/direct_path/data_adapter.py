"""Producer-compatible, byte-snapshot loader; no fits or market reads.

Adapted from the authorized coin producer source member SHA256
8c031a14360428b2c9ca1f6a97d7f8c09753f879db3353a1fef729d6d3e4be95.
Field names, clocks, feature order and outcomes are kept.
Only bounded snapshot parsing and receipt consistency checks are added.
"""
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np

from .pack import MAX_MANIFEST_BYTES, MAX_NPZ_BYTES, bounded_bytes, checked_npz_bytes, integer, is_sha
from .prototype import Context, CORE5, DAY_US, E5, finite
from .training import WINDOWS, stamp, validate_fragment, validate_training

SCHEMA = "BYTE_BOUND_DIRECT_PATH_FRAGMENTS_V1"
MARKET13 = ("BTC_mom1", "BTC_mom5", "BTC_mom20", "BTC_mom60", "BTC_mom200",
            "BTC_vol30", "BTC_vol200", "BTC_dist50", "BTC_dist200", "BTC_funding",
            "breadth20", "dispersion20", "market_vol20")
FEATURE_NAMES = (["market." + n for n in MARKET13]
                 + ["expert." + e + "." + s for e in E5 for s in CORE5]
                 + ["eligible." + e for e in E5])


def delivered_bytes(root, name, expected_sha, maximum, expected_size=None):
    if not isinstance(name, str) or Path(name).name != name:
        raise ValueError("Flat producer file path required")
    root = Path(root).resolve()
    path = (root / name).resolve()
    if path.parent != root:
        raise ValueError("Producer path escapes approved pack")
    raw = bounded_bytes(path, maximum)
    if (not is_sha(expected_sha) or hashlib.sha256(raw).hexdigest() != expected_sha
            or expected_size is not None and len(raw) != expected_size):
        raise ValueError("Exact delivered producer bytes required")
    return raw


def load_fragment(root, entry):
    raw = delivered_bytes(root, entry["file"], entry["sha256"], MAX_NPZ_BYTES, entry["bytes"])
    proof = delivered_bytes(root, entry["receipt_file"], entry["receipt_sha256"], 1000000)
    with gzip.GzipFile(fileobj=io.BytesIO(proof)) as stream:
        decoded = stream.read(2000001)
    if len(decoded) > 2000000:
        raise ValueError("Bounded producer receipt required")
    receipt = json.loads(decoded)
    if receipt["binding"] != entry["binding"] or receipt["window_id"] != entry["window_id"]:
        raise ValueError("Source recipe/data/teacher identity")
    if entry["market13_order"] != list(MARKET13) or entry["feature_names"] != FEATURE_NAMES:
        raise ValueError("Exact named43 feature contract")
    a = checked_npz_bytes(raw)
    if tuple(a["symbol_order"]) != CORE5 or tuple(a["expert_order"]) != E5:
        raise ValueError("Frozen bank and asset order")
    tag = entry["window_id"]
    start, end = map(stamp, WINDOWS[tag])
    t = (end - start) // DAY_US
    d = integer(a["decision_us"], (t,), "decision_us")
    av = integer(a["market_state13_available_us"], (t,), "market_state13_available_us")
    targets_at = integer(a["target_available_us"], (t, 5), "target_available_us")
    targets = finite(a["expert_targets"], (t, 5, 5), "expert_targets")
    past = finite(a["past_returns30"], (t, 30, 5), "past_returns30")
    market = finite(a["market_state13"], (t, 13), "market_state13")
    eligible = a["expert_eligible"]
    if eligible.shape != (t, 5) or eligible.dtype != bool:
        raise ValueError("Original bool expert_eligible required")
    contexts = [Context(int(d[i]), int(av[i]), targets[i], eligible[i], past[i], market[i], targets_at[i])
                for i in range(t)]
    prices = finite(a["prices"], (t + 1, 5), "prices")
    coeff = finite(a["funding_coeff"], (t, 5), "funding_coeff")
    price_close = integer(a["price_close_us"], (t + 1,), "price_close_us")
    price_av = integer(a["price_available_us"], (t + 1,), "price_available_us")
    if (np.any(prices <= 0) or not np.array_equal(price_close, np.r_[d, end])
            or np.any(price_av > price_close)):
        raise ValueError("Full positive completed closes and original availability clocks required")
    if not np.array_equal(a["global_forced_terminal_day"], np.arange(t) == t - 1):
        raise ValueError("Per-fragment common paid finalcash")
    request = finite(a["greedy_request"], (t, 5), "greedy_request")
    if not all(np.array_equal(v, np.eye(5)[int(np.argmax(v))]) for v in request):
        raise ValueError("Actual candidate requests, not ramped budgets")
    labels = integer(a["label_available_us"], (t,), "label_available_us")
    # Keep original full-source input SHA under its existing name. Delivered
    # fragment SHA is recorded separately, never silently relabeled as source.
    binding = dict(entry["binding"])
    f = dict(window_id=tag, contexts=contexts, prices=prices, funding_coeff=coeff,
             greedy_request=request, label_available_us=labels, binding=binding,
             delivered_input_npz_sha256=entry["sha256"],
             receipt_sha256=entry["receipt_sha256"])
    validate_fragment(f, tag)
    if receipt["calendar"] != dict(start_us=start, end_exclusive_us=end, days=t):
        raise ValueError("Exact separate-wallet receipt calendar required")
    rows = receipt["teacher_row_receipts"]
    if len(rows) != t:
        raise ValueError("Complete winning-request source receipts required")
    for i, row in enumerate(rows):
        if (row["decision_us"] != int(d[i]) or row["source_label_available_us"] != int(labels[i])
                or not np.array_equal(row["candidate_request"], request[i])
                or not is_sha(row["source_row_SHA256"])
                or i < t - 1 and row["source_optimization_allowed"] is not True):
            raise ValueError("Original winner/maturity receipt disagrees with input")
    rebuilt = np.zeros((t, 5))
    events = receipt["funding_events"]
    if not isinstance(events, list) or not 0 < len(events) <= 10000:
        raise ValueError("Complete bounded producer funding event receipts required")
    identities = set()
    for event in events:
        event_us, symbol = event["event_us"], event["symbol"]
        identity = (event_us, symbol)
        rate = float(event["raw_rate"])
        if (type(event_us) is not int or not start <= event_us < end or symbol not in CORE5
                or identity in identities or not np.isfinite(rate)):
            raise ValueError("Unique complete in-period funding receipts required")
        identities.add(identity)
        if event_us == start:
            if (event["coefficient_included"] is not False
                    or event["reason"] != "KNOWN_FRESH_CASH_INITIAL_OWNERSHIP_ZERO"):
                raise ValueError("Initial event must use declared zero cash ownership")
            continue
        mark_at, mark = event["mark_close_us"], float(event["strictly_past_mark_price"])
        day = (event_us - start - 1) // DAY_US
        value = float(Decimal(str(mark)) * Decimal(str(rate)))
        if (type(mark_at) is not int or not 0 <= mark_at < event_us
                or event_us - mark_at > 60000000 or not np.isfinite(mark) or mark <= 0
                or event["coefficient_included"] is not True or event["day_index"] != day
                or not np.isclose(event["coefficient_USDT_per_contract"], value, rtol=1e-12, atol=1e-12)):
            raise ValueError("Real strictly-past signed funding marks required")
        rebuilt[day, CORE5.index(symbol)] += value
    if not np.allclose(rebuilt, coeff, rtol=1e-12, atol=1e-12):
        raise ValueError("Complete funding receipt recomputation differs from coeff")
    for value in a.values():
        value.flags.writeable = False
    for value in (targets, eligible, past, market, targets_at, prices, coeff, request, labels):
        value.flags.writeable = False
    return f


def load_training_and_validation(root, expected_index_sha256):
    root = Path(root).resolve()
    raw = delivered_bytes(root, "INDEX.json", expected_index_sha256, MAX_MANIFEST_BYTES)
    manifest = json.loads(raw)
    if manifest["schema"] != SCHEMA:
        raise ValueError("Exact producer fragment protocol")
    entries = manifest["fragments"]
    if [e["window_id"] for e in entries] != list(WINDOWS):
        raise ValueError("Predeclared separate calendar roles")
    if (manifest["market13_order"] != list(MARKET13) or manifest["feature_names"] != FEATURE_NAMES
            or manifest["feature_schema_SHA256"] != hashlib.sha256(
                json.dumps(FEATURE_NAMES, sort_keys=True).encode()).hexdigest()
            or manifest["separate_fresh_10k_wallets"] is not True):
        raise ValueError("Identical named feature schema and separate fresh wallets required")
    train = [load_fragment(root, e) for e in entries[:3]]
    validation = load_fragment(root, entries[3])
    validate_training(train)
    for key in ("mapper_sha256", "expert_identity_sha256"):
        if len({f["binding"][key] for f in train + [validation]}) != 1:
            raise ValueError("Same frozen expert/mapper identities across roles")
    return train, validation, manifest
