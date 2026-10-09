"""One continuous April63 input adapter; unchanged pre-April natural prefixes."""

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from modules.temporal_prequential_transfer.data import EXECUTION_DELAY_US, close_slice, load_source
from modules.temporal_short_expansion.adapter import PAYLOADS, append_episode
from modules.temporal_two_expert.development_inputs import load_development_inputs
from modules.temporal_two_expert.exact import Episode, sha
from modules.temporal_two_expert.feature_windows import load_feature_inputs
from modules.temporal_two_expert.inputs import CORE5, DAY_US, digest, fit_standardizer
from modules.temporal_two_expert.training_packet import named_context

FOLD = "FOLD_20240401"
START = int(datetime(2024, 4, 1, tzinfo=timezone.utc).timestamp()) * 1000000
END = START + 63 * DAY_US
SHORT_SOURCE_SHA = "943b9df49e6c7c0cb19983281c794ee738985aa889c8fde09e6109895c7808ca"
INDEX_SHA = "e4fecc49cd1bb05f72dc0f8d24e793a5d7e4d2436c89a18bd9d7c625a7849be8"
NORMALIZER_SHA = "ee394086066c96bc23e83b45bf0bc2777264ab4eb57128886394fee47fecd4ff"


def prefixes(source, clocks):
    episodes, proofs = [], []
    for e in source:
        n = int((e.windows.decision_us < START).sum())
        if n >= 2:
            episode, proof = close_slice(
                e,
                0,
                n,
                cutoff_us=START,
                role="TRAIN",
                wallet_id=e.wallet_id + "__PREFIX_" + FOLD,
                execution_clocks=clocks,
            )
            episodes.append(episode)
            proofs.append(proof)
    scaler = fit_standardizer([e.windows for e in episodes], training_cutoff_us=START)
    if [len(e.contexts) for e in episodes] != [54, 88, 62, 144, 401] or (
        scaler.provenance["real_row_count"] != 878
        or any(np.any(e.label_available_us >= START) for e in episodes)
    ):
        raise ValueError(
            "Exact749 original prefix dates/878 unique scaler rows before April1 required"
        )
    return tuple(episodes), scaler, proofs


def _h1_contexts(state, source):
    root = state / "recovery/direct_path_fragments"
    if sha(root / "INDEX.json") != INDEX_SHA:
        raise ValueError("Exact recovered original H1 context index required")
    index = json.loads((root / "INDEX.json").read_text())
    fields = [
        "decision_us",
        "expert_targets",
        "expert_eligible",
        "past_returns30",
        "target_available_us",
        "symbol_order",
        "expert_order",
    ]
    parts, provenance = [], {}
    for name in ["H1_TRAIN", "H1_VALIDATE"]:
        entry = next(r for r in index["fragments"] if r["window_id"] == name)
        path = root / entry["file"]
        if sha(path) != entry["sha256"]:
            raise ValueError("Exact public H1 input bytes required")
        with np.load(path, allow_pickle=False) as z:
            parts.append({k: z[k].copy() for k in fields})
        provenance[name] = sha(path)
    if any(tuple(a["symbol_order"]) != CORE5 for a in parts):
        raise ValueError("Original H1 CORE5 context order required")
    data = {k: np.concatenate([a[k] for a in parts]) for k in fields[:5]}
    if not np.all(np.diff(data["decision_us"]) == DAY_US):
        raise ValueError(
            "Actual H1 observations must be continuous across administrative May split"
        )
    original = source[-1]
    rows = np.flatnonzero(original.windows.decision_us >= data["decision_us"][0])
    ix = np.searchsorted(data["decision_us"], original.windows.decision_us[rows])
    np.testing.assert_array_equal(
        original.expert_targets[rows][:, [0, 1, 4]], data["expert_targets"][ix][:, [0, 1, 4]]
    )
    np.testing.assert_array_equal(
        np.stack([original.contexts[i].past_returns30 for i in rows]), data["past_returns30"][ix]
    )
    return data, provenance


def _short_targets(state, source, decisions, members):
    import polars as pl

    recipe_path = Path(__file__).parent / "upstream/momentum_short_pool_target.py"
    if sha(recipe_path) != SHORT_SOURCE_SHA:
        raise ValueError("Exact unchanged public momentum30 SHORT producer required")
    parts, source_hashes = [], {}
    directory = state / "feature-input/verified"
    for symbol in CORE5:
        name = "source_tables_not_model_inputs/daily_features/" + symbol + ".parquet"
        path = directory / name
        if sha(path) != members[name]["SHA256"]:
            raise ValueError("Exact original daily source required for April30 SHORT context")
        source_hashes[name] = sha(path)
        frame = pl.read_parquet(path).filter(
            pl.col("complete_kline")
            & pl.all_horizontal(
                [pl.col(k).is_finite() for k in ("open", "high", "low", "close", "volume")]
            )
        )
        frame = frame.with_columns(
            pl.lit(symbol).alias("symbol"), pl.col("dt").dt.epoch("us").alias("open_us")
        )
        frame = frame.with_columns(
            (pl.col("open_us") + DAY_US).alias("close_us"),
            (pl.col("open_us") + DAY_US).alias("available_us"),
        )
        parts.append(
            frame.filter(pl.col("close_us") <= START + 29 * DAY_US).select(
                "symbol",
                "open_us",
                "close_us",
                "available_us",
                "open",
                "high",
                "low",
                "close",
                "volume",
            )
        )
    spec = importlib.util.spec_from_file_location("_exact_public_april_short_producer", recipe_path)
    recipe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recipe)
    # Reuse the frozen producer, not an independently invented momentum formula.
    april = np.arange(START, START + 30 * DAY_US, DAY_US, dtype=np.int64)
    frame, _ = recipe.fixed_targets(pl.concat(parts), april, symbols=CORE5)
    generated = frame["target_weight"].to_numpy().reshape(30, 5)
    masks = (frame["eligibility_reason"].to_numpy().reshape(30, 5) == "ELIGIBLE").any(1)
    prior = source[-1]
    ix = np.searchsorted(prior.windows.decision_us, april[:-1])
    np.testing.assert_array_equal(prior.windows.decision_us[ix], april[:-1])
    np.testing.assert_array_equal(generated[:-1], prior.expert_targets[ix, 5])
    with np.load(state / "short-source/DEV61_MOMENTUM_SHORT_CONTEXTS.npz", allow_pickle=False) as z:
        if (
            sha(state / "short-source/DEV61_MOMENTUM_SHORT_CONTEXTS.npz")
            != PAYLOADS["DEV61_MOMENTUM_SHORT_CONTEXTS.npz"]
        ):
            raise ValueError("Exact existing MayJune SHORT inputs required")
        n = len(decisions) - len(april)
        np.testing.assert_array_equal(z["decision_us"][:n], decisions[len(april) :])
        targets = np.concatenate([generated, z["expert_targets"][:n, 0]])
        eligible = np.concatenate([masks, z["expert_eligible"][:n, 0]])
    source_hashes["momentum_short_pool_target.py"] = SHORT_SOURCE_SHA
    source_hashes["DEV61_MOMENTUM_SHORT_CONTEXTS.npz"] = PAYLOADS[
        "DEV61_MOMENTUM_SHORT_CONTEXTS.npz"
    ]
    return targets[:, None], eligible[:, None], source_hashes


def _outcomes(state, source, decisions, members):
    import pandas as pd
    import pyarrow.parquet as pq

    from modules.collector_research.pipeline.normalize import funding_windows

    repo = Path(__file__).resolve().parents[2]
    if sha(repo / "modules/collector_research/pipeline/normalize.py") != NORMALIZER_SHA:
        raise ValueError("Exact unchanged event/mark funding normalizer required")
    directory = state / "feature-input/verified"
    prices, funding, hashes = [], [], {}
    for symbol in CORE5:
        paths = [
            "source_tables_not_model_inputs/economics/" + symbol + suffix
            for suffix in ["_daily.parquet", "_funding_events.parquet"]
        ]
        for name in paths:
            if sha(directory / name) != members[name]["SHA256"]:
                raise ValueError("Exact transferred execution-price/event funding source required")
            hashes[name] = sha(directory / name)
        daily, events = [pq.read_table(directory / name).to_pandas() for name in paths]
        event_us = events.calc_time_ms.to_numpy(np.int64) * 1000
        held = (event_us > decisions[0] + EXECUTION_DELAY_US) & (
            event_us <= decisions[-1] + EXECUTION_DELAY_US
        )
        marks = events.past_mark_price.to_numpy(float)[held]
        available = events.past_mark_available_us.to_numpy(float)[held]
        if (
            not np.all(np.diff(event_us) > 0)
            or not np.isfinite(marks).all()
            or (
                np.any(marks <= 0)
                or not np.isfinite(available).all()
                or np.any(available != np.floor((event_us[held] - 1) / 60000000) * 60000000)
            )
        ):
            raise ValueError(
                "Held funding requires unique actual events and strictly prior completed marks"
            )
        times = pd.DatetimeIndex(daily.dt).as_unit("us").asi8
        ix = np.searchsorted(times, decisions)
        np.testing.assert_array_equal(times[ix], decisions)
        if (
            not daily.complete_kline.iloc[ix].all()
            or not (daily.unique_minutes.iloc[ix] == 1440).all()
        ):
            raise ValueError("Every forward execution day requires actual complete source coverage")
        price = daily.exec_price.iloc[ix].to_numpy(float)
        if not np.isfinite(price).all() or np.any(price <= 0):
            raise ValueError("Actual00:01 execution prices required; never substitute daily closes")
        recomputed = funding_windows(events, pd.DatetimeIndex(daily.dt.iloc[ix[:-1]]))
        if not recomputed.funding_interval_complete.all():
            raise ValueError(
                "All62 active funding intervals require event brackets and strictly prior marks"
            )
        coefficient = recomputed.mark_funding_per_unit.to_numpy(float)
        if not np.isfinite(coefficient).all():
            raise ValueError("Missing actual funding cannot be filled")
        # Cross-check all29 overlapping days against the exact old financial packet.
        prior = source[-1]
        rows = np.searchsorted(prior.windows.decision_us, decisions[:29])
        j = CORE5.index(symbol)
        np.testing.assert_array_equal(price[:29], prior.prices[rows, j])
        np.testing.assert_array_equal(coefficient[:29], prior.funding_coeff[rows, j])
        prices.append(np.concatenate([price, price[-1:]]))
        funding.append(np.concatenate([coefficient, [0.0]]))
    return np.column_stack(prices), np.column_stack(funding), hashes


def load_fold(state):
    state = Path(state)
    source, prototype, clocks = load_source(state)
    train, scaler, proofs = prefixes(source, clocks)
    packet = json.loads((state / "FROZEN_PACKET.json").read_text())
    base = load_feature_inputs(
        state / packet["files"]["feature_npz"]["path"],
        state / packet["files"]["feature_manifest"]["path"],
    )
    features = load_development_inputs(
        base,
        state / "development-features/FEATURES.npz",
        state / "development-features/MANIFEST.json",
    )
    decisions = np.arange(START, END, DAY_US, dtype=np.int64)
    # The append's public enumeration names MayJune only; its actual timeline
    # also retains the byte-bound real pre-May history. This fixed forward block
    # deliberately spans April and May without changing TRAIN admissions.
    windows = features.timeline.windows(decisions)
    if not np.all(windows.step_valid) or np.any(np.diff(windows.completed_us, axis=1) != DAY_US):
        raise ValueError("Every April63 window requires64 real contiguous completed daily steps")
    data, h1_hashes = _h1_contexts(state, source)
    ix = np.searchsorted(data["decision_us"], decisions)
    np.testing.assert_array_equal(data["decision_us"][ix], decisions)
    members = json.loads((state / "feature-input/verified/MEMBERS.json").read_text())["files"]
    short, eligible, short_hashes = _short_targets(state, source, decisions, members)
    prices, funding, outcome_hashes = _outcomes(state, source, decisions, members)
    provenance = dict(
        H1=h1_hashes,
        short=short_hashes,
        economic=outcome_hashes,
        feature_append=features.identity,
        normalizer=NORMALIZER_SHA,
        observation_join="contiguous_H1_input_rows;one_fresh_April_wallet;no_May_reset",
    )
    contexts = tuple(
        named_context(
            prototype,
            int(t),
            data["expert_targets"][i, [0, 1, 4]],
            data["expert_eligible"][i, [0, 1, 4]],
            data["past_returns30"][i],
            np.zeros(13),
            data["target_available_us"][i, [0, 1, 4]],
        )
        for t, i in zip(decisions, ix, strict=True)
    )
    labels = np.concatenate(
        [decisions[1:] + EXECUTION_DELAY_US, decisions[-1:] + EXECUTION_DELAY_US]
    )
    original = Episode(
        "FORWARD63_" + FOLD,
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
    from modules.temporal_expert_input.inputs import expose_episode

    forward = expose_episode(
        append_episode(
            original, short, eligible, decisions[:, None], prototype, digest(short_hashes)
        )
    )
    receipt = dict(
        fold_id=FOLD,
        first_forward_decision_us=START,
        forward_end_exclusive_us=END,
        training_decisions=749,
        training_wallets=proofs,
        scaler_identity=scaler.identity,
        scaler_provenance=scaler.provenance,
        additional_embargo_days=0,
        maturity="all_active_outcomes_and_paid_prefix_close_strictly_before_April1",
        forward=dict(
            decisions=63,
            active_intervals=62,
            first_decision_us=START,
            last_decision_us=int(decisions[-1]),
            cutoff_us=END + DAY_US,
            paid_terminal_close_available_us=int(labels[-1]),
            terminal_price_equals_last_active_end=True,
            no_future_suffix_consumed=True,
            identity=forward.identity,
        ),
        forward_provenance=provenance,
        warmup="all63_windows_have64_real_steps",
        boundary_prices_funding_29_overlap="BIT_IDENTICAL_ORIGINAL_FROZEN_PACKET",
    )
    binding = dict(
        packet_SHA256=sha(state / "FROZEN_PACKET.json"),
        economic_SHA256=packet["files"]["economic_npz"]["SHA256"],
        train=[e.identity for e in train],
        forward=forward.identity,
        fold=receipt,
    )
    return train, forward, prototype, scaler, dict(binding, identity=digest(binding)), receipt
