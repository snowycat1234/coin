"""Faithful extension of causal inputs and source-bound July daily economics."""

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from modules.collector_research.pipeline.make_labels import BASE_FEATURES, feature_frame
from modules.collector_research.pipeline.normalize import funding_windows
from modules.collector_research.pipeline.train import market_features
from modules.temporal_april_transfer.data import SHORT_SOURCE_SHA
from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_short_expansion.adapter import PAYLOADS, append_episode
from modules.temporal_two_expert.exact import Episode, load_prototype, sha
from modules.temporal_two_expert.inputs import (
    CORE5,
    DAY_US,
    FEATURE_NAMES,
    MARKET_CONTEXT,
    FeatureTimeline,
    Standardizer,
    digest,
)
from modules.temporal_two_expert.training_packet import named_context

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "research/temporal-april-transfer-20261009/forward/FOLD_20240401"
PROTOCOL_PATH = REPO / "research/temporal-july-frozen-transfer-20261010/PROTOCOL.json"
PROTOCOL_SHA = "8269d474867248c16aee0b6509d53cf2e88acf7a0f985c499becb09006d16aa1"
CONSUMER_SHA = "8590d616a350804262a2a5bc9a4d542eb0787638d83574da93b7172e003081aa"
ECONOMICS_SHA = "9c503a8dd01be93dd1b7e0ddeb267a4f6bf38daec20db5ac026b0ea20af774a9"
EXECUTION_DELAY_US = 60000001
START, END = 1719792000000000, 1725235200000000
RECIPE_HASHES = {
    "upstream/conditional_selector_core.py": "c0a086ba583dfe4f059b8942988ec2209ac767e4cfe59699f06e804b94890533",
    "upstream/conditional_selector_inputs.py": "9c6658cd7682b6c5470585cbe927c20893e98a3e071cd52e56c5de280e86f207",
}
RISK_SOURCES = {
    "scripts/investment/public_sma_perpetual.py": "c9fe8a916f300e91396dba70948ab44348b947ec333d7c82b8429db36e064e18",
    "scripts/investment/vol_managed_perpetual_target.py": "6d6c563885accfe47258580a658a43054e94307bbec85b6dc0c06f96b88b9307",
    "scripts/research/public_cross_section_momentum.py": "7d6f1794c0ade6e2c2d951a325e4e68ca45be0e87c84c68f05061442fad8a38f",
    "modules/transformer_v2/portfolio.py": "e4e02b0204e2861bb44eb78c8069b13a09edf6ca9390f3c86490d6e6f8a5e68b",
}


def protocol():
    if sha(PROTOCOL_PATH) != PROTOCOL_SHA:
        raise ValueError("Fixed July protocol required")
    result = json.loads(PROTOCOL_PATH.read_text())
    for name, expected in result["frozen_artifacts"].items():
        if sha(REPO / name) != expected:
            raise ValueError("Frozen artifact changed: " + name)
    manifest = json.loads((FROZEN / "MANIFEST.json").read_text())
    if any(
        sha(REPO / name) != expected for name, expected in manifest["versioned_sources"].items()
    ):
        raise ValueError("Original68 versioned sources changed")
    for name, expected in RISK_SOURCES.items():
        if sha(REPO / name) != expected:
            raise ValueError("Original expert risk/source identity changed")
    return result


def recipe():
    for name, expected in RECIPE_HASHES.items():
        if sha(Path(__file__).parent / name) != expected:
            raise ValueError("Exact archived target adapter required")
    alias = "scripts.research.conditional_selector_core"
    if alias in sys.modules:
        raise ValueError("Unexpected preloaded target dependency")
    spec = importlib.util.spec_from_file_location(
        alias, Path(__file__).parent / "upstream/conditional_selector_core.py"
    )
    core = importlib.util.module_from_spec(spec)
    sys.modules[alias] = core
    try:
        spec.loader.exec_module(core)
        spec = importlib.util.spec_from_file_location(
            "_july_exact_original_target_adapter",
            Path(__file__).parent / "upstream/conditional_selector_inputs.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        del sys.modules[alias]
    return module


def build_features(frames, *, end_us=END - DAY_US):
    """Original18+6 formulas on real preceding history; no economic reads."""
    labels = {}
    for symbol in MARKET_CONTEXT:
        frame = frames[symbol]
        raw = pd.DatetimeIndex(frame.dt).as_unit("us").asi8
        frame = frame[raw + DAY_US <= end_us].reset_index(drop=True)
        labels[symbol] = feature_frame(frame, 256)
    clocks = pd.DatetimeIndex(labels[CORE5[0]].dt).as_unit("us").asi8 + DAY_US
    if any(
        not np.array_equal(pd.DatetimeIndex(f.dt).as_unit("us").asi8 + DAY_US, clocks)
        for f in labels.values()
    ):
        raise ValueError("Original10 market context requires identical real calendars")
    market = market_features(labels).to_numpy(float)
    values = np.stack(
        [np.column_stack((labels[s][BASE_FEATURES].to_numpy(float), market)) for s in CORE5], axis=1
    ).astype(np.float32)
    close = np.column_stack([labels[s].close.to_numpy(float) for s in CORE5])
    observed = np.isfinite(close) & (close > 0)
    valid = np.isfinite(values) & observed[..., None]
    return clocks, values, valid, observed, close


def economics(directory, decisions):
    directory = Path(directory)
    if (
        sha(directory / "CONSUMER_INDEX.json") != CONSUMER_SHA
        or sha(directory / "ECONOMICS.npz") != ECONOMICS_SHA
    ):
        raise ValueError("Exact supplied consumer index/array required")
    consumer = json.loads((directory / "CONSUMER_INDEX.json").read_text())
    if (
        consumer["protocol_SHA256"] != PROTOCOL_SHA
        or consumer["symbols_order"] != list(CORE5)
        or not consumer["execution_and_held_funding_ready"]
    ):
        raise ValueError("Economic packet must bind fixed protocol and symbol order")
    with np.load(directory / "ECONOMICS.npz", allow_pickle=False) as z:
        arrays = {name: z[name].copy() for name in z.files}
    np.testing.assert_array_equal(arrays["symbol_order"], CORE5)
    for name, expected in (
        ("decision_us", decisions),
        ("execution_us", decisions + EXECUTION_DELAY_US),
        ("funding_interval_start_us", decisions[:-1] + EXECUTION_DELAY_US),
        ("funding_interval_end_us", decisions[1:] + EXECUTION_DELAY_US),
    ):
        np.testing.assert_array_equal(arrays[name], expected)
    prices, coeff = arrays["prices"], arrays["funding_coeff"]
    if (
        prices.shape != (63, 5)
        or coeff.shape != (62, 5)
        or not np.isfinite(prices).all()
        or np.any(prices <= 0)
        or not np.isfinite(coeff).all()
    ):
        raise ValueError("63 real prices/62 complete funding intervals required, no padding")
    for row in consumer["economic_table_artifacts"]:
        path = directory / row["path"]
        if path.stat().st_size != row["bytes"] or sha(path) != row["SHA256"]:
            raise ValueError("Exact supplied economic table bytes required")
    independent_errors = {}
    for j, symbol in enumerate(CORE5):
        events = pq.read_table(
            directory / f"normalized/data/normalized/{symbol}_funding_events.parquet"
        ).to_pandas()
        daily = pq.read_table(
            directory / f"normalized/data/normalized/{symbol}_daily.parquet"
        ).to_pandas()
        intervals = pq.read_table(
            directory / f"normalized/economics/{symbol}_funding_intervals.parquet"
        ).to_pandas()
        times = events.calc_time_ms.to_numpy(np.int64) * 1000
        marks = events.past_mark_price.to_numpy(float)
        available = events.past_mark_available_us.to_numpy(np.int64)
        np.testing.assert_array_equal(available, (times - 1) // 60000000 * 60000000)
        if (
            len(events) != 189
            or np.any(np.diff(times) <= 0)
            or not np.isfinite(marks).all()
            or np.any(marks <= 0)
            or np.any(times - available > 60000000)
        ):
            raise ValueError("Actual strictly-prior marked events required")
        actual = funding_windows(events, pd.to_datetime(decisions[:-1], unit="us", utc=True))
        if (
            not actual.funding_interval_complete.all()
            or not intervals.funding_interval_complete.all()
        ):
            raise ValueError("Both-sided held event coverage required")
        np.testing.assert_array_equal(actual.mark_funding_per_unit, coeff[:, j])
        np.testing.assert_array_equal(intervals.mark_funding_per_unit, coeff[:, j])
        np.testing.assert_array_equal(pd.DatetimeIndex(daily.dt).as_unit("us").asi8, decisions)
        np.testing.assert_array_equal(daily.exec_price, prices[:, j])
        if not daily.complete_kline.all() or not (daily.unique_minutes == 1440).all():
            raise ValueError("Actual complete execution days required")
        references = []
        for start in decisions[:-1] + EXECUTION_DELAY_US:
            selected = (times > start) & (times <= start + DAY_US)
            if selected.sum() != 3:
                raise ValueError("Expected actual held funding event count")
            references.append(
                math.fsum(
                    float(a) * float(b)
                    for a, b in zip(
                        events.last_funding_rate.to_numpy(float)[selected],
                        marks[selected],
                        strict=True,
                    )
                )
            )
        np.testing.assert_allclose(references, coeff[:, j], atol=1e-10, rtol=2e-15)
        independent_errors[symbol] = float(np.max(np.abs(np.asarray(references) - coeff[:, j])))
    # Only ABI padding: forced cash earns no suffix return/funding.
    return (
        np.vstack((prices, prices[-1:])),
        np.vstack((coeff, np.zeros((1, 5)))),
        dict(
            source_commit="5109edcaa5a790a023a11828cfd1452b5705ba1a",
            economic_SHA256=ECONOMICS_SHA,
            consumer_SHA256=CONSUMER_SHA,
            independent_funding_max_error=independent_errors,
            native_minute_grid_complete=False,
            missing_mark_open_UTC=["2024-08-12T10:02:00Z", "2024-08-12T10:03:00Z"],
            original_minute_mark_values_verified_by_source_task=True,
            minute_tape_replayed_here=False,
        ),
    )


def load(state, economic_directory):
    state = Path(state)
    frozen_protocol = protocol()
    directory = state / "feature-input/verified"
    members = json.loads((directory / "MEMBERS.json").read_text())["files"]
    frames, source_hashes = {}, {}
    for symbol in MARKET_CONTEXT:
        name = f"source_tables_not_model_inputs/daily_features/{symbol}.parquet"
        if sha(directory / name) != members[name]["SHA256"]:
            raise ValueError("Original primitive source changed")
        source_hashes[name] = sha(directory / name)
        frames[symbol] = pq.read_table(directory / name).to_pandas()
    clocks, values, valid, observed, close = build_features(frames)
    overlap_count = 0
    for name, expected in (
        (
            "feature-input/verified/features/CORE5_PRE_MAY2024.npz",
            "f164dc8986727e12446f4a807aed72382e8fd665ad7eda9ba14590811ebc680c",
        ),
        (
            "development-features/FEATURES.npz",
            "800e39e53170fc87a279322b61f0f7f7b7a7812759267c58b1d4db948ab3aa8f",
        ),
    ):
        path = state / name
        if sha(path) != expected:
            raise ValueError("Frozen feature parity reference changed")
        with np.load(path, allow_pickle=False) as z:
            saved_clock = z["completed_day_available_us"]
            ix = np.searchsorted(clocks, saved_clock)
            np.testing.assert_array_equal(clocks[ix], saved_clock)
            np.testing.assert_array_equal(values[ix], z["x"])
            np.testing.assert_array_equal(observed[ix], z["close_observed_mask"])
            np.testing.assert_array_equal(
                valid[ix], z["feature_observed_mask"] & z["close_observed_mask"][..., None]
            )
            overlap_count += len(ix)
    decisions = np.arange(START, END, DAY_US, dtype=np.int64)
    selected = (clocks >= START - 63 * DAY_US) & (clocks < END)
    if selected.sum() != 126:
        raise ValueError("126 actual completed input rows required")
    timeline = FeatureTimeline(
        values[selected],
        valid[selected],
        observed[selected],
        clocks[selected],
        np.broadcast_to(clocks[selected, None, None], values[selected].shape).copy(),
        digest(source_hashes),
    )
    windows = timeline.windows(decisions)
    original = recipe()
    bars = original.bar_frame(directory / "source_tables_not_model_inputs", CORE5)
    bars = bars.filter(__import__("polars").col("available_us") <= decisions[-1])
    # Real history restores weekly rank state; do not rerank on July1.
    check_decisions = np.arange(1711929600000000, END, DAY_US, dtype=np.int64)
    results = [
        original.existing_targets(
            dict(recipe=name, mechanism=name), bars, check_decisions, close, clocks, CORE5
        )
        for name in ("CASH", "VOL_MANAGED_HOLD", "CSMOM21")
    ]
    targets = np.stack([r[0] for r in results], axis=1)
    eligible = np.stack([r[2] for r in results], axis=1)
    rows = np.searchsorted(clocks, check_decisions)
    past = np.stack([np.diff(close[i - 30 : i + 1], axis=0) / close[i - 30 : i] for i in rows])
    for name in ("H1_TRAIN", "H1_VALIDATE"):
        path = state / "recovery/direct_path_fragments" / (name + ".npz")
        entry = next(
            r
            for r in json.loads((path.parent / "INDEX.json").read_text())["fragments"]
            if r["window_id"] == name
        )
        if sha(path) != entry["sha256"]:
            raise ValueError("Original H1 context parity bytes changed")
        with np.load(path, allow_pickle=False) as z:
            mask = (z["decision_us"] >= check_decisions[0]) & (
                z["decision_us"] <= check_decisions[-1]
            )
            ix = np.searchsorted(check_decisions, z["decision_us"][mask])
            np.testing.assert_array_equal(targets[ix], z["expert_targets"][mask][:, [0, 1, 4]])
            np.testing.assert_array_equal(eligible[ix], z["expert_eligible"][mask][:, [0, 1, 4]])
            np.testing.assert_array_equal(past[ix], z["past_returns30"][mask])
    recipe_path = REPO / "modules/temporal_april_transfer/upstream/momentum_short_pool_target.py"
    if sha(recipe_path) != SHORT_SOURCE_SHA:
        raise ValueError("Unchanged momentum30 SHORT producer required")
    spec = importlib.util.spec_from_file_location("_july_frozen_short", recipe_path)
    short = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(short)
    frame, _ = short.fixed_targets(bars, check_decisions, symbols=CORE5)
    short_targets = frame["target_weight"].to_numpy().reshape(len(check_decisions), 1, 5)
    short_eligible = (
        frame["eligibility_reason"].to_numpy().reshape(len(check_decisions), 1, 5) == "ELIGIBLE"
    ).any(2)
    path = state / "short-source/DEV61_MOMENTUM_SHORT_CONTEXTS.npz"
    if sha(path) != PAYLOADS[path.name]:
        raise ValueError("Original SHORT parity source changed")
    with np.load(path, allow_pickle=False) as z:
        ix = np.searchsorted(check_decisions, z["decision_us"])
        np.testing.assert_array_equal(short_targets[ix], z["expert_targets"])
        np.testing.assert_array_equal(short_eligible[ix], z["expert_eligible"])
    prices, funding, economic_receipt = economics(economic_directory, decisions)
    prototype = load_prototype(state / "recovery/source/modules/direct_path/prototype.py")
    ix = np.searchsorted(check_decisions, decisions)
    contexts = tuple(
        named_context(
            prototype,
            int(t),
            targets[i],
            eligible[i],
            past[i],
            np.zeros(13),
            np.full(3, t, dtype=np.int64),
        )
        for t, i in zip(decisions, ix, strict=True)
    )
    provenance = dict(
        primitive_SHA256=source_hashes,
        target_adapter_SHA256=RECIPE_HASHES,
        risk_sources=RISK_SOURCES,
        short_producer_SHA256=SHORT_SOURCE_SHA,
        economics=economic_receipt,
    )
    labels = np.r_[decisions[1:] + EXECUTION_DELAY_US, decisions[-1] + EXECUTION_DELAY_US]
    episode = Episode(
        "FIXED_JULY2024_TRANSFER",
        windows,
        contexts,
        prices,
        funding,
        labels,
        START,
        END,
        END + DAY_US,
        "SEEN_VALIDATION",
        digest(provenance),
    )
    expanded = append_episode(
        episode,
        short_targets[ix],
        short_eligible[ix],
        decisions[:, None],
        prototype,
        digest(dict(recipe=SHORT_SOURCE_SHA, source=source_hashes)),
    )
    forward = expose_episode(expanded)
    scaler_meta = json.loads((FROZEN / "SCALER.json").read_text())
    with np.load(FROZEN / "SCALER.npz", allow_pickle=False) as z:
        scaler = Standardizer(z["mean"], z["scale"], z["count"], scaler_meta["provenance"])
    if scaler.identity != frozen_protocol["policies"]["APRIL_PREFIX_GRU512"]["scaler_identity"]:
        raise ValueError("Frozen pre-April normalization required")
    receipt = dict(
        provenance,
        protocol_SHA256=PROTOCOL_SHA,
        source_feature_parity_rows=overlap_count,
        H1_CASH_VOL_CS_covariance_parity="BIT_IDENTICAL_APRIL1_JUNE30_91_ROWS",
        SHORT_parity="BIT_IDENTICAL_MAY1_JUNE30_61_ROWS",
        feature_order=list(FEATURE_NAMES),
        aggregate_order=list(MARKET_CONTEXT),
        newly_serialized_rows=63,
        completed_input_rows=126,
        windows_shape=list(windows.values.shape),
        valid_features=int(windows.valid.sum()),
        valid_steps=int(windows.step_valid.sum()),
        all64_steps_observed=bool(windows.step_valid.all()),
        expert_eligibility_counts=forward.eligible.sum(0).tolist(),
        episode_identity=forward.identity,
        scaler_identity=scaler.identity,
        model_refitted=False,
        normalization_refitted=False,
    )
    return forward, prototype, scaler, receipt
