"""Audit cached training dates and emit a six-fit plan; never fit or score."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

DAY = 86400000000
CORE = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
CONTEXT_SHA = "66c5fdb2317689ed1d084c3f8eeb6e1781fa04ccc15e6243784a03a3555e7676"
SHORT_SHA = "64accfc82f78034af0da48561ef7e2fabfc8712760066860194e3d2bce9e382d"
FEATURE_SHA = "f164dc8986727e12446f4a807aed72382e8fd665ad7eda9ba14590811ebc680c"
PACKET_SHA = "0bd135091a913d67fec6af6da1f51a8cda80a09eca1da5a64582ebe68302ddea"
FOLDS = (("FOLD_20240101", "2024-01-01", 658, 653), ("FOLD_20240401", "2024-04-01", 749, 744))
REGIMES = (
    ("2022_early_bear", "2022-01-01", "2022-05-01"),
    ("2022_midyear_crisis_bear", "2022-05-01", "2022-08-01"),
    ("2022_sideways_and_autumn_crisis", "2022-08-01", "2023-01-01"),
    ("2023_rebound", "2023-01-01", "2023-04-01"),
    ("2023_midyear_sideways", "2023-04-01", "2023-10-01"),
    ("late2023_early2024_bull_calendar", "2023-10-01", "2024-05-01"),
)


def clock(date):
    return int(np.datetime64(date, "us").astype(np.int64))


def date(value):
    return str(np.datetime64(int(value), "us").astype("datetime64[D]"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_training_dates(audit):
    if audit["actual_distinct_eligible_active_training_dates"] < 600:
        raise ValueError("Every fit requires>=600 actual distinct eligible active dates")


def source_inventory(repo):
    """Read accepted-source identities, never strategy results or market bodies."""
    paths = (
        (
            "docs/archive/MULTI_ASSET_CONTINUOUS_RELEASE_METADATA_20261004_V1/ACCEPTED-CONTINUOUS-INPUT_MANIFEST.json",
            "847d8a6e561d782ae641d492697ee03fd7b3ba2eda65298e5d0f02cb0c7b1e50",
        ),
        (
            "docs/archive/MULTI_ASSET_WINTER_RELEASE_METADATA_20261004_V1/ACCEPTED-WINTER-INPUT_MANIFEST.json",
            "56f1eb1b768e14d4c67198156732c1d4a22e6a901e980c24ebee9f20bbf86193",
        ),
    )
    records, manifests = {}, {}
    for name, expected in paths:
        if sha(repo / name) != expected:
            raise ValueError("Exact original accepted-source manifest required")
        source = json.loads((repo / name).read_text())
        if source["source_only"] is not True:
            raise ValueError("Source-only manifest required")
        manifests[name] = sha(repo / name)
        for record in source["market_records"]:
            key = (record["symbol"], record["kind"], record["month"])
            if key[0] not in CORE or key[2] not in ("2024-10", "2024-11", "2024-12"):
                continue
            identity = {
                k: record[k]
                for k in (
                    "symbol",
                    "kind",
                    "month",
                    "interval",
                    "normalized_sha256",
                    "receipt_sha256",
                )
            }
            identity["zip_sha256_if_recorded_at_top_level"] = record.get("zip_sha256")
            if key in records and records[key] != identity:
                raise ValueError("Conflicting accepted source identities")
            records[key] = identity
    expected = {
        (s, k, m)
        for s in CORE
        for k in ("klines", "markPriceKlines", "fundingRate")
        for m in ("2024-10", "2024-11", "2024-12")
    }
    if set(records) != expected:
        raise ValueError("All45 CORE5 trade/mark/funding monthly source records required")
    return dict(
        manifest_SHA256=manifests,
        source_main_commit="ef67d636a51fd3fa9e804f651aab5775f6bae5f8",
        records=[records[k] for k in sorted(records)],
        monthly_records=len(records),
        scope="source identities only; not restored execution economics or minute/funding/publication certification",
    )


def eligible_prefix(data, short, features, cutoff):
    times = data["decision_us"]
    selected = times < cutoff
    rows, lengths, wallets = [], [], []
    for episode in np.unique(data["episode_id"]):
        ix = np.flatnonzero(selected & (data["episode_id"] == episode))
        if len(ix) < 2:
            continue
        if np.any(np.diff(times[ix]) != DAY):
            raise ValueError("Never splice original date gaps")
        active = ix[:-1]
        if (
            np.any(data["end_execution_us"][active] >= cutoff)
            or data["start_execution_us"][ix[-1]] >= cutoff
        ):
            raise ValueError(
                "Active outcomes and paid prefix close must mature strictly before validation"
            )
        lengths.append(len(ix))
        rows.extend(active.tolist())
        wallets.append(
            dict(
                episode=int(episode),
                first=date(times[ix[0]]),
                last_paid_close=date(times[ix[-1]]),
                decisions=len(ix),
                active_dates=len(active),
            )
        )
    active = np.asarray(rows, dtype=int)
    ix = np.flatnonzero(selected)
    end = np.searchsorted(features["completed_day_available_us"], times[ix])
    np.testing.assert_array_equal(features["completed_day_available_us"][end], times[ix])
    if end.min() < 63 or np.any(np.diff(features["completed_day_available_us"]) != DAY):
        raise ValueError("Real contiguous64-day calendar rows required")
    windows = end[:, None] - np.arange(63, -1, -1)[None, :]
    finite = np.isfinite(data["past_returns30"]).all((1, 2))
    risky = data["expert_eligible"][:, 1:].any(1) | short["expert_eligible"].any(1)
    current = features["close_observed_mask"][end].any(1)
    current_features = (
        features["feature_observed_mask"][end] & features["close_observed_mask"][end, :, None]
    ).any((1, 2))
    usable = finite[ix] & risky[ix] & current & current_features
    by_global = np.zeros(len(times), dtype=bool)
    by_global[ix] = usable
    eligible = active[by_global[active]]
    if len(np.unique(times[eligible])) != len(eligible):
        raise ValueError("Distinct actual dates required")
    regime_counts = {
        name: int(((times[eligible] >= clock(a)) & (times[eligible] < clock(b))).sum())
        for name, a, b in REGIMES
    }
    return dict(
        decision_rows=len(ix),
        active_dates=len(active),
        actual_distinct_eligible_active_training_dates=len(eligible),
        paid_close_rows=len(lengths),
        wallet_lengths=lengths,
        natural_wallets=wallets,
        first_training_date=date(times[ix[0]]),
        last_context_date=date(times[ix[-1]]),
        unique_prefix_normalization_feature_rows=int(len(np.unique(windows))),
        all64_steps_all5_assets_observed_windows=int(
            features["close_observed_mask"][windows].all((1, 2)).sum()
        ),
        feature_mask_observations=int(
            (
                features["feature_observed_mask"][windows]
                & features["close_observed_mask"][windows][..., None]
            ).sum()
        ),
        per_CORE5_expert_asset_eligible_counts=data["expert_asset_eligible"][eligible, 1:]
        .sum(0)
        .tolist(),
        per_CORE5_SHORT_asset_eligible_counts=short["expert_asset_eligible"][eligible, 0]
        .sum(0)
        .tolist(),
        original_regime_calendar_counts=regime_counts,
        eligible_training_decision_us_SHA256=hashlib.sha256(times[eligible].tobytes()).hexdigest(),
        independent_effective_information="UNKNOWN; overlapping64-step windows and dependent prices are not independent observations",
    )


def build(state, repo, output, tail_metadata):
    state, repo, output = Path(state), Path(repo), Path(output)
    if output.exists():
        raise FileExistsError("Exclusive proposed-plan artifact required")
    packet_path = state / "FROZEN_PACKET.json"
    if sha(packet_path) != PACKET_SHA:
        raise ValueError("Exact frozen packet identity required")
    packet = json.loads(packet_path.read_text())
    bindings = {"FROZEN_PACKET.json": PACKET_SHA}
    for entry in packet["files"].values():
        p = state / entry["path"]
        if sha(p) != entry["SHA256"]:
            raise ValueError("Original packet input changed")
        bindings[entry["path"]] = sha(p)
    paths = [
        ("economic-contexts/CONTEXTS.npz", CONTEXT_SHA),
        ("short-source/TRAIN778_MOMENTUM_SHORT_CONTEXTS.npz", SHORT_SHA),
        ("feature-input/verified/features/CORE5_PRE_MAY2024.npz", FEATURE_SHA),
    ]
    packs = []
    fields = (
        "decision_us",
        "episode_id",
        "past_returns30",
        "expert_eligible",
        "expert_asset_eligible",
        "target_available_us",
        "start_execution_us",
        "end_execution_us",
    )
    for name, expected in paths:
        path = state / name
        if sha(path) != expected:
            raise ValueError("Exact original training source required")
        bindings[name] = expected
        with np.load(path, allow_pickle=False) as z:
            keys = (
                fields
                if len(packs) < 2
                else ("completed_day_available_us", "feature_observed_mask", "close_observed_mask")
            )
            packs.append({k: z[k].copy() for k in keys if k in z.files})
    data, short, features = packs
    np.testing.assert_array_equal(data["decision_us"], short["decision_us"])
    if len(data["decision_us"]) != 778 or len(np.unique(data["decision_us"])) != 778:
        raise ValueError("Original distinct778 date contract required")
    if np.any(data["target_available_us"] > data["decision_us"][:, None]) or np.any(
        short["target_available_us"] > data["decision_us"][:, None]
    ):
        raise ValueError("Causal expert target clocks required")
    full = eligible_prefix(data, short, features, clock("2024-05-01"))
    require_training_dates(full)
    calendar = np.arange(data["decision_us"].min(), data["decision_us"].max() + DAY, DAY)
    absent = calendar[~np.isin(calendar, data["decision_us"])]
    groups = np.split(absent, np.flatnonzero(np.diff(absent) != DAY) + 1)
    readiness_path = state / "economic-contexts/TRAIN_CONTEXT_READY.json"
    readiness = json.loads(readiness_path.read_text())
    before600 = eligible_prefix(data, short, features, clock("2023-11-08"))
    first600 = eligible_prefix(data, short, features, clock("2023-11-09"))
    if (
        before600["actual_distinct_eligible_active_training_dates"] != 599
        or first600["actual_distinct_eligible_active_training_dates"] != 600
    ):
        raise ValueError("Actual first600-date cutoff changed")
    source_coverage = dict(
        calendar_missing_decision_dates=len(absent),
        missing_ranges=[dict(first=date(g[0]), last=date(g[-1]), days=len(g)) for g in groups],
        producer_economic_candidate_dates=readiness["economic_dates"],
        producer_covariance_excluded_dates=readiness["excluded_incomplete_past_covariance_dates"],
        exclusion_note="71 dates missing inside retained calendar;61 covariance exclusions at another admission stage; categories overlap, never add them",
        first600_cutoff_exclusive="2023-11-09",
        first600_active_dates=600,
        previous_day_cutoff_active_dates=599,
        insufficient_early_prefixes={
            day: eligible_prefix(data, short, features, clock(day))[
                "actual_distinct_eligible_active_training_dates"
            ]
            for day in ("2023-07-01", "2023-10-01")
        },
        feature_calendar_first=date(features["completed_day_available_us"][0]),
        feature_calendar_last=date(features["completed_day_available_us"][-1]),
        feature_only_history="2020-2021 feature context supplies no economic training dates in this packet",
    )
    folds, curves, timings = {}, {}, []
    source_paths = []
    for fold, start, expected_rows, expected_active in FOLDS:
        audit = eligible_prefix(data, short, features, clock(start))
        require_training_dates(audit)
        if (
            audit["decision_rows"] != expected_rows
            or audit["actual_distinct_eligible_active_training_dates"] != expected_active
        ):
            raise ValueError("Every planned fit needs>=600 verified active eligible distinct dates")
        audit.update(
            validation_start=start,
            validation_end_exclusive=date(clock(start) + 63 * DAY),
            validation_role="PROJECT_SEEN_DEVELOPMENT",
        )
        folder = (
            repo
            / (
                "research/temporal-april-transfer-20261009/forward/"
                if fold == "FOLD_20240401"
                else "research/temporal-prequential-transfer-20261009/forward/"
            )
            / fold
        )
        manifest = json.loads((folder / "MANIFEST.json").read_text())
        for name, entry in manifest["files"].items():
            if sha(folder / name) != entry["SHA256"]:
                raise ValueError("Saved model/curve/forward input changed")
        terminal = json.loads((folder / "TERMINAL.json").read_text())
        source_paths.extend(
            [folder / n for n in ("MANIFEST.json", "TERMINAL.json", "RUN.json", "SCALER.json")]
        )
        curve = [
            dict(
                update=r["snapshot_step"],
                training_date_mean_loss=r["date_mean_loss"],
                gradient_norm=r["trained_objective_summary"]["gradient_norm"],
                signed_episode_gradient_projection=r["trained_objective_summary"][
                    "signed_projection_shares"
                ],
            )
            for r in terminal["diagnostics"]
        ]
        curves[fold] = curve
        timings.append(terminal["elapsed_seconds"] / terminal["completed_updates"])
        folds[fold] = audit
    # Reserve a later decision interval; inspect availability, never its return/result.
    final_start, final_end = clock("2024-10-01"), clock("2025-01-01")
    final_dates = np.arange(final_start, final_end, DAY, dtype=np.int64)
    needed = np.arange(final_start - 63 * DAY, final_end, DAY, dtype=np.int64)
    member_root = state / "feature-input/verified"
    members = json.loads((member_root / "MEMBERS.json").read_text())["files"]
    final_coverage = {}
    all_market = (
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "1000PEPEUSDT",
        "XRPUSDT",
        "WIFUSDT",
        "WLDUSDT",
        "DOGEUSDT",
        "1000SATSUSDT",
        "ORDIUSDT",
    )
    for symbol in all_market:
        name = f"source_tables_not_model_inputs/daily_features/{symbol}.parquet"
        p = member_root / name
        if sha(p) != members[name]["SHA256"]:
            raise ValueError("Original primitive bytes changed")
        frame = pq.read_table(p).to_pandas()
        completed = pd.DatetimeIndex(frame.dt).as_unit("us").asi8 + DAY
        selected = np.isin(completed, needed)
        final_coverage[symbol] = dict(
            required_completed_steps=155,
            present=int(selected.sum()),
            observed_close=int(
                (
                    selected
                    & frame.complete_kline.to_numpy(bool)
                    & np.isfinite(frame.close)
                    & (frame.close > 0)
                ).sum()
            ),
            premium_complete=int((selected & frame.complete_premium.to_numpy(bool)).sum()),
            feature_funding_complete=int((selected & frame.complete_funding.to_numpy(bool)).sum()),
        )
        bindings[name] = sha(p)
        if symbol in CORE:
            name = f"source_tables_not_model_inputs/economics/{symbol}_daily.parquet"
            p = member_root / name
            if sha(p) != members[name]["SHA256"]:
                raise ValueError("Original execution economics changed")
            table = pq.read_table(p).to_pandas()
            clocks = pd.DatetimeIndex(table.dt).as_unit("us").asi8
            good = (
                table.complete_kline.to_numpy(bool)
                & np.isfinite(table.exec_price)
                & (table.exec_price > 0)
            )
            final_coverage[symbol]["actual_execution_prices_present"] = int(
                np.isin(final_dates, clocks[good]).sum()
            )
            bindings[name] = sha(p)
    candidates = {
        "BASE_DATE_LR1E3": dict(
            lr=0.001,
            wallet_equal_mix=0.0,
            change="baseline; fresh initialization with1024-update cap",
        ),
        "LOW_LR3E4": dict(
            lr=0.0003,
            wallet_equal_mix=0.0,
            change="only learning rate; test slower movement/less saturated or abrupt requests",
        ),
        "MIXED_WALLET_HALF": dict(
            lr=0.001,
            wallet_equal_mix=0.5,
            change="only episode weighting;0.5*n/N+0.5/K; retain every eligible date",
        ),
    }
    tasks = [
        dict(
            task_id=fold + "__" + name,
            fold=fold,
            candidate=name,
            eligible_dates=counts["actual_distinct_eligible_active_training_dates"],
            objective_decision_rows=counts["decision_rows"],
            complete_wallet_lengths=counts["wallet_lengths"],
            episode_coefficients=[
                (1.0 - settings["wallet_equal_mix"]) * n / counts["decision_rows"]
                + settings["wallet_equal_mix"] / len(counts["wallet_lengths"])
                for n in counts["wallet_lengths"]
            ],
            **settings,
        )
        for fold, counts in folds.items()
        for name, settings in candidates.items()
    ]
    for path in source_paths:
        bindings[str(path.relative_to(repo))] = sha(path)
    metadata_path = Path(tail_metadata)
    if sha(metadata_path) != "2af208be38c5f9031e0fe03d4636e7ebd1ef45912d32d596bba7cd5b9ddd3551":
        raise ValueError("Known project-seen tail metadata required")
    tail = json.loads(metadata_path.read_text())
    assert (
        tail["calendar"]["start_us"] <= final_start
        and tail["calendar"]["end_exclusive_us"] >= final_end
    )
    inventory = source_inventory(repo)
    bindings.update(inventory["manifest_SHA256"])
    plan = dict(
        schema="PROPOSED_SIX_FIT_600_ACTIVE_DATE_TEMPORAL_TUNING_PLAN_V1",
        status="READY_FOR_REVIEW_NO_FITS_STARTED",
        executable_scope="cached-input audit and proposed task/settings emitter only; training adapter not implemented and no fitting entrypoint provided",
        original_training_packet=full,
        source_coverage_audit=source_coverage,
        folds=folds,
        actual_fit_tasks=tasks,
        candidate_settings=candidates,
        original_curves=curves,
        common=dict(
            parameters=13699,
            architecture="unchanged_GRU64_CORE5_24values24masks_GRU32_joint160to32_plus18expertinputs_E6fouractiveactions",
            seed=20261009,
            initialization="fresh model/empty Adam/allRNG; same initial trainable bytes withinfold; no warm checkpoint",
            optimizer="Adam",
            betas=[0.9, 0.999],
            epsilon=1e-8,
            weight_decay=0.0,
            foreach=False,
            dropout=0.1,
            gradient_norm_clip=1.0,
            max_completed_full_path_updates=1024,
            neural_window_batch_size=32,
            full_dataset_gradient_pass_per_update=True,
            checkpoint_every_completed_update=True,
            normalization="unique prefix feature rows valid-only; cutoff strict; no development or reserve observations",
            checkpoint_retention="atomic latest resume plus initial/best-development/matched512/terminal snapshots; retain every scheduled metric, not1024 separate frozen files",
            objective="same charged-boundary economic own-path v2; only declared episode coefficients vary",
            episode_coefficient_definition="n_i is original decision count including paid-close row; N=sum(n_i); K=5; objective loss already mean-normalized by each complete wallet's decision count",
            epoch_definition="one completed optimizer update uses a full gradient pass through all five complete chronological wallets;1024 epochs reuse the same actual653/744dates, not new independent observations",
            determinism="same withinfold initial model/Python/NumPy/Torch RNG and emptyAdam; train dropout.1 with exact chunk RNG replay; eval dropout off and inference deterministic; snapshot binds model/scaler/source/run recipe/Adam/RNG",
            restore_strategy="original strict contracts remain unchanged; new study bindings must explicitly declare candidate recipe before fit",
            controls=dict(
                primary="frozen prefix-static VOL both selectedfolds",
                supplementary=["Static50", "Cash50"],
            ),
            economics="continuous original natural wallets, separate10k; no batch reset/splicing; same costs/funding/risk/caps/L1.1/paidclose; no observed wallet features",
        ),
        selection=dict(
            checkpoints=[256, 384, 512, 640, 768, 896, 1024],
            criterion="validation own-path utility minus frozenVOL; deterministic eval; no gradient into validation",
            min_updates_before_stop=512,
            patience=3,
            improvement_threshold=1e-5,
            stop_rule="After>=512, stop after3 consecutive scheduled checks without utility_excess improvement>1e-5; save best development checkpoint; never resume to rescue result",
            checkpoint_tie="earlier completed update",
            budget_note="same max1024 and rule; report actual updates and best checkpoint; preserve matched512 diagnostic when reached",
            candidate_rank="highest arithmetic mean best-checkpoint utility_excess across the two fixed development folds; tie within1e-5 uses best worst-fold utility, then baseline/LOW_LR/MIXED fixed order",
            record_all_results=True,
            promotion="none; no ROI-dependent relaxation; numeric failure stops thatfit without recipe retry",
        ),
        reserved_final=dict(
            start="2024-10-01",
            end_exclusive="2025-01-01",
            decisions=92,
            active_intervals=91,
            paid_close="2024-12-31T00:01:00.000001Z",
            status="PROJECT_SEEN_HISTORICAL_RESERVED_FOR_THIS_STUDY_NOT_UNTOUCHED",
            prior_use="native HGB/teacher/student tail Aug13,2024-Jan2,2025; all92 dates overlap known project development",
            tail_manifest_SHA256=sha(metadata_path),
            primitive_coverage=final_coverage,
            tail_metadata_public_source=dict(
                commit="d69e9ac94478c5be54cb46c622afec7aaf3c61f7",
                index="research_artifacts/native_20261008/INDEX.json",
                member="original_inputs/TAIL_MANIFEST.json",
            ),
            accepted_monthly_source_inventory=inventory,
            final_refit="One later selected-recipe fresh fit on cached full778 decisions/773 activeeligible dates; step budget = rounded-down median of two selected development best updates, minimum256; no reserve-based stopping",
            final_selection_step_tie="median of two integers rounded down; freeze before final inference",
            final_controls=["frozen prefix-static VOL", "Static50", "Cash50"],
            reserve_results_read=False,
            reserve_market_returns_computed=False,
        ),
        compute=dict(
            measured_seconds_per_full_update=timings,
            estimated_cpu_seconds_for6x1024=[min(timings) * 6144, max(timings) * 6144],
            maximum_concurrent_fits=2,
            per_fit_threads=1,
            resident_per_fit_bytes=2000000000,
            shared_bytes=8000000000,
            swap=0,
            GPU=0,
            cumulative_fit_wall_stop_seconds=3600,
            maximum_six_fit_wall_hours_at2workers=3.0,
            exact_resume="atomic model/Adam/RNG;1200second slices count completed updates once; no restart of failed updates",
            estimate_scope="history-based~3.6-4.2CPUhours/~1.8-2.1hours at2workers plusvalidation; earlystop may reduce; no synthetic benchmark fit",
        ),
        missing_inputs=[
            "Six-fit candidate adapter/new source/run/checkpoint bindings must admit only these lr and mixing overrides; old strict loader/contracts remain unchanged",
            "Reserved92 actual00:01 prices and91 strict-prior event-funding coefficients not cached here; restore small derived packet from existing public accepted-source/native-tail sources, no provider redownload",
            "Rebuild missing reserved serialized feature rows with original10-asset builder and source/mask parity; do not fit scaler on them",
            "Confirm exact reserved execution/funding clocks/completeness in immutable input receipt before any final economic score; no fallback date or mark filling",
        ],
        source_SHA256=bindings,
        original_gap_policy="retain5 independent natural episodes and their missing calendars; do not concatenate calendars or wallets",
        effective_information="600+actual active dates perfit; overlapping64day windows do not create independent days; statistical effective N unknown",
        planned_initial_fits=6,
        later_selected_final_refits=1,
        performed_fits=0,
        model_inferences=0,
        economic_wallets=0,
        provider_downloads=0,
        hypothesis_evidence=dict(
            learning_rate="April loss still decreases256->512 and gradient~.001<clip1; current gates often near-extreme and request changes can jump>1; lowerlr is a controlled hypothesis, not established cure",
            weighting="April longest401-date episode53.54% date weight; atinitialization91.44% signed gradient projection; shorter crisis episodes receive less date mass. Earlier warm mixed512 lost18.69USDT vsdate on seen MayJune; not evidence of guaranteed improvement; fresh chronological test resolves this hypothesis",
        ),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(
        json.dumps(
            dict(
                status=plan["status"],
                full_active_dates=full["actual_distinct_eligible_active_training_dates"],
                fold_active_dates={
                    k: v["actual_distinct_eligible_active_training_dates"] for k, v in folds.items()
                },
                tasks=len(tasks),
                fits=0,
                wallets=0,
                downloads=0,
            )
        )
    )
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--tail-metadata",
        type=Path,
        required=True,
        help="Already-cached byte-bound original TAIL_MANIFEST.json; no downloads",
    )
    args = parser.parse_args()
    build(args.state, args.repo, args.output, args.tail_metadata)
