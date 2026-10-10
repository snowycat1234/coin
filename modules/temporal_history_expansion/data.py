"""Same cached causal producers, fixed-five covariance and real paid closures."""

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
from modules.temporal_two_expert.exact import Episode, sha
from modules.temporal_two_expert.feature_windows import TRAINING_CUTOFF_US, load_feature_inputs
from modules.temporal_two_expert.inputs import (
    CORE5,
    DAY_US,
    MARKET_CONTEXT,
    array_digest,
    digest,
    fit_standardizer,
    require_sha,
)
from modules.temporal_two_expert.training_packet import named_context

from .packet import DELAY, END, ROOT, START


@dataclass(frozen=True)
class EarlyEpisode(Episode):
    """N real prices, N-1 real active intervals; final CASH charged immediately."""

    real_terminal_ABI = True

    def __post_init__(self):
        decisions = self.windows.decision_us
        n = len(decisions)
        if (
            not self.wallet_id
            or self.role != "TRAIN"
            or n < 2
            or self.start_us < START
            or self.end_us > END
            or self.split_cutoff_us != TRAINING_CUTOFF_US
            or not np.array_equal(decisions, np.arange(self.start_us, self.end_us, DAY_US))
            or len(self.contexts) != n
            or self.prices.shape != (n, 5)
            or self.funding_coeff.shape != (n - 1, 5)
            or not np.isfinite(self.prices).all()
            or np.any(self.prices <= 0)
            or not np.isfinite(self.funding_coeff).all()
            or not np.array_equal(
                self.label_available_us, np.r_[decisions[1:] + DELAY, decisions[-1] + DELAY]
            )
            or np.any(self.label_available_us >= self.split_cutoff_us)
        ):
            raise ValueError("Complete mature real 2021 wallet and paid terminal required")
        require_sha(self.producer_sha256)
        contexts = []
        for t, c in zip(decisions, self.contexts, strict=True):
            c.validate()
            if c.decision_us != t or c.available_us > t:
                raise ValueError("Causal matching contexts required")
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
            contexts.append(replace(c, **arrays))
        object.__setattr__(self, "contexts", tuple(contexts))
        for name in ("prices", "funding_coeff", "label_available_us"):
            a = np.array(getattr(self, name), copy=True)
            a.flags.writeable = False
            object.__setattr__(self, name, a)

    @property
    def identity(self):
        return digest(dict(real_terminal_ABI=True, original=super().identity))


@dataclass(frozen=True)
class CausalInputs:
    windows: object
    contexts: tuple  # None marks unavailable complete-five covariance
    short_targets: np.ndarray
    short_eligible: np.ndarray
    receipt: dict


def cached_inputs(state, prototype):
    """Feature/expert construction only; no prices, outcomes, wallets or model."""
    directory = Path(state) / "feature-input/verified"
    features = load_feature_inputs(
        directory / "features/CORE5_PRE_MAY2024.npz", directory / "FEATURE_MANIFEST.json"
    )
    members = json.loads((directory / "MEMBERS.json").read_text())["files"]
    frames, hashes = {}, {}
    for symbol in MARKET_CONTEXT:
        name = f"source_tables_not_model_inputs/daily_features/{symbol}.parquet"
        if sha(directory / name) != members[name]["SHA256"]:
            raise ValueError("Cached original primitive bytes changed")
        hashes[name] = sha(directory / name)
        frames[symbol] = pq.read_table(directory / name).to_pandas()
    clocks, values, valid, observed, close = build_features(frames, end_us=END - DAY_US)
    # Recompute original 10-asset aggregates and compare every cached early row.
    ix = np.searchsorted(features.timeline.completed_us, clocks)
    np.testing.assert_array_equal(features.timeline.completed_us[ix], clocks)
    np.testing.assert_array_equal(features.timeline.values[ix], values)
    np.testing.assert_array_equal(features.timeline.valid[ix], valid)
    np.testing.assert_array_equal(features.timeline.step_valid[ix], observed)
    decisions = np.arange(START, END, DAY_US, dtype=np.int64)
    windows = features.windows(decisions)
    for name, expected in RISK_SOURCES.items():
        if sha(ROOT / name) != expected:
            raise ValueError("Original expert producer changed")
    original = recipe()
    bars = original.bar_frame(directory / "source_tables_not_model_inputs", CORE5)
    bars = bars.filter(__import__("polars").col("available_us") <= decisions[-1])
    # Replay real preceding weekly schedule, independent of admitted economics.
    check = np.arange(1602720000000000, END, DAY_US, dtype=np.int64)  # Oct15,2020
    outputs = [
        original.existing_targets(
            dict(recipe=name, mechanism=name), bars, check, close, clocks, CORE5
        )
        for name in ("CASH", "VOL_MANAGED_HOLD", "CSMOM21")
    ]
    targets = np.stack([o[0] for o in outputs], axis=1)
    eligible = np.stack([o[2] for o in outputs], axis=1)
    asset_masks = np.stack([o[3] for o in outputs], axis=1)
    short_source = ROOT / "modules/temporal_april_transfer/upstream/momentum_short_pool_target.py"
    if sha(short_source) != SHORT_SOURCE_SHA:
        raise ValueError("Original signed short producer changed")
    spec = importlib.util.spec_from_file_location("_early_original_short", short_source)
    short = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(short)
    frame, _ = short.fixed_targets(bars, check, symbols=CORE5)
    short_targets = frame["target_weight"].to_numpy().reshape(len(check), 1, 5)
    short_eligible = (
        frame["eligibility_reason"].to_numpy().reshape(len(check), 1, 5) == "ELIGIBLE"
    ).any(2)
    contexts = []
    selected = np.searchsorted(check, decisions)
    for t, k in zip(decisions, selected, strict=True):
        i = np.searchsorted(clocks, t)
        history = close[i - 30 : i + 1]
        complete = (
            i >= 30
            and clocks[i] == t
            and history.shape == (31, 5)
            and np.all(np.diff(clocks[i - 30 : i + 1]) == DAY_US)
            and np.isfinite(history).all()
            and np.all(history > 0)
        )
        contexts.append(
            named_context(
                prototype,
                int(t),
                targets[k],
                eligible[k],
                np.diff(history, axis=0) / history[:-1],
                np.zeros(13),
                np.full(3, t, dtype=np.int64),
            )
            if complete
            else None
        )
    mask = asset_masks[selected]
    receipt = dict(
        primitive_SHA256=hashes,
        risk_sources=RISK_SOURCES,
        short_producer_SHA256=SHORT_SOURCE_SHA,
        feature_identity=features.identity,
        cached_builder_parity_rows=len(clocks),
        real_calendar_decisions=365,
        feature_window_shape=list(windows.values.shape),
        valid_features=int(windows.valid.sum()),
        all64_steps_observed=bool(windows.step_valid.all()),
        fixed5_covariance_ready=sum(c is not None for c in contexts),
        expert_asset_eligible_counts=mask.sum(0).tolist(),
        VOL_first_eligible_2021={
            s: int(decisions[np.flatnonzero(mask[:, 1, j])[0]]) if mask[:, 1, j].any() else None
            for j, s in enumerate(CORE5)
        },
        weekly_rank_replayed_from_UTC="2020-10-15",
        synthetic_feature_rows=0,
        normalization_fit=False,
        economic_wallets_run=0,
        optimizer_updates=0,
        provider_downloads=0,
    )
    return CausalInputs(
        windows, tuple(contexts), short_targets[selected], short_eligible[selected], receipt
    )


def admitted_runs(packet, causal):
    """Maximal complete intervals only: never splice a gap or add cash padding."""
    d = packet.decision_us
    if not np.array_equal(d, causal.windows.decision_us) or len(causal.contexts) != len(d):
        raise ValueError("Matching source/feature real calendars required")
    covariance = np.array([c is not None for c in causal.contexts])
    noncash = np.array([c is not None and c.eligible[1:].any() for c in causal.contexts])
    noncash |= causal.short_eligible[:, 0]
    masks = dict(
        real_endpoint_prices=packet.price_known[:-1].all(1) & packet.price_known[1:].all(1),
        signed_held_funding=packet.funding_known.all(1),
        fixed5_covariance=covariance[:-1] & covariance[1:],
        mature_label=d[1:] + DELAY < TRAINING_CUTOFF_US,
    )
    admitted = np.logical_and.reduce(list(masks.values()))
    edges = np.diff(np.r_[False, admitted, False].astype(int))
    source_runs = tuple(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True))
    runs = []
    cash_only_excluded = 0
    for start, stop in source_runs:
        if noncash[start:stop].any():
            runs.append((start, stop))
        else:
            cash_only_excluded += int(stop - start)
            admitted[start:stop] = False
    return tuple(runs), dict(
        candidate_active_intervals=len(d) - 1,
        admitted_active_intervals=int(admitted.sum()),
        rejected_active_intervals=int((~admitted).sum()),
        rejection_counts_may_overlap={k: int((~v).sum()) for k, v in masks.items()},
        wholly_cash_only_source_intervals_excluded=cash_only_excluded,
        admitted_noncash_opportunity_dates=int((admitted & noncash[:-1]).sum()),
        admitted_real_interior_cash_dates=int((admitted & ~noncash[:-1]).sum()),
        interior_cash_days_preserve_wallet_chronology=True,
        rejected_decision_us=d[:-1][~admitted].tolist(),
    )


def new_episodes(packet, causal, prototype):
    runs, audit = admitted_runs(packet, causal)
    output = []
    for start, stop in runs:  # active [start,stop), then actual close at stop
        selection = slice(int(start), int(stop) + 1)
        d = packet.decision_us[selection]
        windows = replace(
            causal.windows,
            **{
                k: getattr(causal.windows, k)[selection]
                for k in (
                    "values",
                    "valid",
                    "step_valid",
                    "completed_us",
                    "available_us",
                    "decision_us",
                )
            },
        )
        source = digest(
            dict(packet=packet.identity, causal=causal.receipt, start=int(d[0]), close=int(d[-1]))
        )
        episode = EarlyEpisode(
            "EARLY2021_" + str(int(d[0])),
            windows,
            causal.contexts[selection],
            packet.prices[selection],
            packet.funding_coeff[start:stop],
            np.r_[d[1:] + DELAY, d[-1] + DELAY],
            int(d[0]),
            int(d[-1]) + DAY_US,
            TRAINING_CUTOFF_US,
            "TRAIN",
            source,
        )
        output.append(
            expose_episode(
                append_episode(
                    episode,
                    causal.short_targets[selection],
                    causal.short_eligible[selection],
                    d[:, None],
                    prototype,
                    digest(dict(short=SHORT_SOURCE_SHA, causal=causal.receipt)),
                )
            )
        )
    return tuple(output), audit


def assemble(original, added, old_scaler):
    """Preserve all original objects/identities; count active history separately."""
    original, added = tuple(original), tuple(added)
    if [len(e.contexts) for e in original] != [54, 88, 62, 144, 430]:
        raise ValueError("Exactly the five original 778-decision wallets required")
    if not added:
        raise ValueError("No genuine complete additional history available")
    combined = added + original
    for a, b in zip(combined, combined[1:], strict=False):
        if a.end_us > b.start_us:
            raise ValueError(
                "Original boundaries and independent chronological wallets cannot overlap"
            )
    active = [e.windows.decision_us[:-1] for e in combined]
    dates = np.concatenate(active)
    if len(np.unique(dates)) != len(dates):
        raise ValueError("Duplicate economic intervals cannot increase training dates")
    before = {int(t) for e in original for t in e.windows.completed_us.ravel()}
    after = {int(t) for e in combined for t in e.windows.completed_us.ravel()}
    scaler = fit_standardizer([e.windows for e in combined], training_cutoff_us=TRAINING_CUTOFF_US)
    receipt = dict(
        original_episode_identities=[e.identity for e in original],
        original_boundaries=[[e.start_us, e.end_us] for e in original],
        original_objects_retained=all(a is b for a, b in zip(combined[-5:], original, strict=True)),
        before=dict(
            active_dates=773,
            decisions=778,
            wallets=5,
            unique_normalization_rows=len(before),
            scaler_identity=old_scaler.identity,
        ),
        after=dict(
            active_dates=len(dates),
            decisions=sum(len(e.contexts) for e in combined),
            wallets=len(combined),
            unique_normalization_rows=len(after),
            scaler_identity=scaler.identity,
        ),
        additional_active_dates=sum(len(e.contexts) - 1 for e in added),
        duplicate_active_dates=0,
        additional_paid_closures=len(added),
        added_unique_feature_rows=len(after - before),
        added_feature_rows_overlapping_old_warmup=len(
            {int(t) for e in added for t in e.windows.completed_us.ravel()} & before
        ),
        warmup_and_close_rows_counted_as_active_dates=False,
        date_weight_lengths=[len(e.contexts) for e in combined],
        date_weight_coefficients=[
            len(e.contexts) / sum(len(x.contexts) for x in combined) for e in combined
        ],
        active_date_SHA256=array_digest(dates),
        expanded_episode_identities=[e.identity for e in combined],
        comparator_scaler_unchanged=True,
    )
    if len(before) != 907 or scaler.provenance["real_row_count"] != len(after):
        raise ValueError("Original907-row and expanded unique-row normalization contract required")
    return combined, scaler, receipt
