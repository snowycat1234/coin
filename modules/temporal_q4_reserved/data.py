"""Real Q4 causal windows using the original builder and expert producers."""

import importlib.util
import json
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from modules.temporal_april_transfer.data import SHORT_SOURCE_SHA
from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_july_transfer.data import RISK_SOURCES, build_features, recipe
from modules.temporal_short_expansion.adapter import append_episode
from modules.temporal_two_expert.exact import Episode, load_prototype, sha
from modules.temporal_two_expert.inputs import (
    CORE5,
    DAY_US,
    FEATURE_NAMES,
    MARKET_CONTEXT,
    FeatureTimeline,
    digest,
    require_sha,
)
from modules.temporal_two_expert.training_packet import named_context

ROOT = Path(__file__).resolve().parents[2]
START = 1727740800000000  # Oct1
END = 1735689600000000  # Jan1 exclusive; Dec31 is paid-close decision
EXECUTION_DELAY_US = 60000001


@dataclass(frozen=True)
class TerminalEpisode(Episode):
    """Same context representation, with an explicit real terminal ABI."""

    def __post_init__(self):
        n = len(self.contexts)
        decisions = self.windows.decision_us
        if (
            self.role != "SEEN_VALIDATION"
            or self.start_us != START
            or self.end_us != END
            or self.split_cutoff_us != END + DAY_US
            or n != 92
            or not np.array_equal(decisions, np.arange(START, END, DAY_US))
            or any(c.decision_us != int(t) for c, t in zip(self.contexts, decisions, strict=True))
        ):
            raise ValueError("Exactly one complete92-decision Q4 wallet required")
        if (
            self.prices.shape != (92, 5)
            or self.funding_coeff.shape != (91, 5)
            or np.any(self.prices <= 0)
            or not np.isfinite(self.prices).all()
            or not np.isfinite(self.funding_coeff).all()
            or not np.array_equal(
                self.label_available_us,
                np.r_[decisions[1:] + EXECUTION_DELAY_US, decisions[-1] + EXECUTION_DELAY_US],
            )
        ):
            raise ValueError("92 real prices91 real funding intervals; no padding")
        require_sha(self.producer_sha256)
        frozen = []
        for c in self.contexts:
            c.validate()
            arrays = {}
            for name in (
                "expert_targets",
                "eligible",
                "past_returns30",
                "market13",
                "target_available_us",
            ):
                a = np.array(getattr(c, name), copy=True)
                a.flags.writeable = False
                arrays[name] = a
            frozen.append(replace(c, **arrays))
        object.__setattr__(self, "contexts", tuple(frozen))
        for name in ("prices", "funding_coeff", "label_available_us"):
            a = np.array(getattr(self, name), copy=True)
            a.flags.writeable = False
            object.__setattr__(self, name, a)

    @property
    def identity(self):
        return digest(dict(real_terminal_ABI=True, original=super().identity))


def load_features(state):
    directory = Path(state) / "feature-input/verified"
    members = json.loads((directory / "MEMBERS.json").read_text())["files"]
    frames, source_hashes = {}, {}
    for symbol in MARKET_CONTEXT:
        name = f"source_tables_not_model_inputs/daily_features/{symbol}.parquet"
        if sha(directory / name) != members[name]["SHA256"]:
            raise ValueError("Original primitive source changed")
        source_hashes[name] = sha(directory / name)
        frames[symbol] = pq.read_table(directory / name).to_pandas()
    clocks, values, valid, observed, close = build_features(frames, end_us=END - DAY_US)
    overlap = 0
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
        path = Path(state) / name
        if sha(path) != expected:
            raise ValueError("Frozen feature parity reference changed")
        with np.load(path, allow_pickle=False) as z:
            ix = np.searchsorted(clocks, z["completed_day_available_us"])
            np.testing.assert_array_equal(clocks[ix], z["completed_day_available_us"])
            np.testing.assert_array_equal(values[ix], z["x"])
            np.testing.assert_array_equal(observed[ix], z["close_observed_mask"])
            np.testing.assert_array_equal(
                valid[ix], z["feature_observed_mask"] & z["close_observed_mask"][..., None]
            )
            overlap += len(ix)
    decisions = np.arange(START, END, DAY_US, dtype=np.int64)
    selected = (clocks >= START - 63 * DAY_US) & (clocks < END)
    if selected.sum() != 155:
        raise ValueError("155 real completed feature rows required; no padding")
    timeline = FeatureTimeline(
        values[selected],
        valid[selected],
        observed[selected],
        clocks[selected],
        np.broadcast_to(clocks[selected, None, None], values[selected].shape).copy(),
        digest(source_hashes),
    )
    return timeline.windows(decisions), close, clocks, source_hashes, overlap, directory


def load(state, economic_directory, scaler, terminal):
    if terminal["status"] != "FIXED256_COMPLETE" or terminal["completed_updates"] != 256:
        raise ValueError("Freeze exact256 before opening reserved inputs")
    from .economics import economics

    windows, close, clocks, source_hashes, overlap, directory = load_features(state)
    decisions = windows.decision_us
    for name, expected in RISK_SOURCES.items():
        if sha(ROOT / name) != expected:
            raise ValueError("Original expert producer source changed")
    original = recipe()
    bars = original.bar_frame(directory / "source_tables_not_model_inputs", CORE5)
    bars = bars.filter(__import__("polars").col("available_us") <= decisions[-1])
    # Restore prior scheduled weekly rank from the same Apr1 history used by July;
    # no fresh rerank at Oct1.
    check = np.arange(1711929600000000, END, DAY_US, dtype=np.int64)
    results = [
        original.existing_targets(
            dict(recipe=name, mechanism=name), bars, check, close, clocks, CORE5
        )
        for name in ("CASH", "VOL_MANAGED_HOLD", "CSMOM21")
    ]
    targets = np.stack([r[0] for r in results], axis=1)
    eligible = np.stack([r[2] for r in results], axis=1)
    rows = np.searchsorted(clocks, check)
    past = np.stack([np.diff(close[i - 30 : i + 1], axis=0) / close[i - 30 : i] for i in rows])
    source = ROOT / "modules/temporal_april_transfer/upstream/momentum_short_pool_target.py"
    if sha(source) != SHORT_SOURCE_SHA:
        raise ValueError("Original signed short producer changed")
    spec = importlib.util.spec_from_file_location("_q4_original_short", source)
    short = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(short)
    frame, _ = short.fixed_targets(bars, check, symbols=CORE5)
    short_targets = frame["target_weight"].to_numpy().reshape(len(check), 1, 5)
    short_eligible = (
        frame["eligibility_reason"].to_numpy().reshape(len(check), 1, 5) == "ELIGIBLE"
    ).any(2)
    prices, funding, economic_receipt = economics(economic_directory, decisions)
    prototype = load_prototype(Path(state) / "recovery/source/modules/direct_path/prototype.py")
    ix = np.searchsorted(check, decisions)
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
        risk_sources=RISK_SOURCES,
        short_producer_SHA256=SHORT_SOURCE_SHA,
        economics=economic_receipt,
    )
    episode = TerminalEpisode(
        "FIXED_Q4_SELECTED256",
        windows,
        contexts,
        prices,
        funding,
        np.r_[decisions[1:] + EXECUTION_DELAY_US, decisions[-1] + EXECUTION_DELAY_US],
        START,
        END,
        END + DAY_US,
        "SEEN_VALIDATION",
        digest(provenance),
    )
    forward = expose_episode(
        append_episode(
            episode,
            short_targets[ix],
            short_eligible[ix],
            decisions[:, None],
            prototype,
            digest(dict(recipe=SHORT_SOURCE_SHA, source=source_hashes)),
        )
    )
    receipt = dict(
        provenance,
        classification="PROJECT_SEEN_BUT_UNTOUCHED_BY_THIS_TUNING_STUDY",
        feature_order=list(FEATURE_NAMES),
        aggregate_order=list(MARKET_CONTEXT),
        source_feature_parity_rows=overlap,
        completed_input_rows=155,
        windows_shape=list(windows.values.shape),
        valid_features=int(windows.valid.sum()),
        valid_steps=int(windows.step_valid.sum()),
        all64_steps_observed=bool(windows.step_valid.all()),
        expert_eligibility_counts=forward.eligible.sum(0).tolist(),
        episode_identity=forward.identity,
        scaler_identity=scaler.identity,
        scaler_training_rows=907,
        normalization_refitted=False,
        synthetic_input_rows=0,
        training_after_reserve_binding=0,
    )
    return forward, prototype, receipt
