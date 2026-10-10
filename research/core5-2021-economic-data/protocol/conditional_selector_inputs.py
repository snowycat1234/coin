"""Deterministic existing-expert/quantity-reference bridge; never fit a model.

The full calendar is retained. Unknown feedback/labels remain NaN. Independent
expert references are teacher inputs, never summed into a portfolio result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

from modules.collector_research.pipeline.economics import interval_arrays, proxy_step, replay
from scripts.research.conditional_selector_core import (
    DAY_US,
    RankProvenance,
    chronological_training_mask,
    nonoverlap_indices,
)

ROOT = Path(__file__).resolve().parents[2]
CORE = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
LATENCY_US = 120_000_001
PAST_FEATURES = ("log_growth7", "log_growth30", "downside_rms30", "drawdown30")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def reference_utility(metrics):
    require(
        metrics["final_positions"] == 0 and metrics["terminal_fee"] >= 0,
        "Paid reference terminal closure required",
    )
    return float(np.log1p(metrics["net_return"]) - 0.5 * metrics["mdd"])


def teacher_arrays(frames, decisions, targets, eligible, *, cash_index, funding_scale=1.0):
    """Return seven-day utilities and strictly-clocked continuous shadow feedback.

    Gaps terminate an unclosed/unknown reference segment. The next complete
    segment starts from cash and has a different ID; no full-wallet claim is
    made across a gap. Rolling feedback features cannot cross such a boundary.
    Seven-day teachers each start from cash and pay their own terminal exit.
    """
    d = np.asarray(decisions, dtype=np.int64)
    w = np.asarray(targets, float)
    ok = np.asarray(eligible)
    n, experts, assets = w.shape
    require(
        len(d) == n and np.all(np.diff(d) == DAY_US)
        and ok.shape == (n, experts) and ok.dtype == bool
        and len(frames) == assets and 0 <= cash_index < experts,
        "Explicit full teacher calendar and expert/asset order required",
    )
    require(funding_scale in (1.0, 0.01), "Only original two conditional funding scales")
    first = next(iter(frames.values()))
    available = first.available_us.to_numpy(np.int64)
    for frame in frames.values():
        require(np.array_equal(frame.available_us, available), "Economics clocks differ")
    indices = np.searchsorted(available, d)
    require(
        np.all(indices < len(available)) and np.array_equal(available[indices], d),
        "Every decision must map to its exact economics row",
    )
    require(np.all(np.diff(indices) == 1), "Economics cannot compress calendar gaps")
    arrays = [interval_arrays(frame, indices, funding_scale) for frame in frames.values()]
    p0, p1, fp, good = [np.stack([v[k] for v in arrays], axis=1) for k in range(4)]
    common_economics = (
        good.all(1) & np.isfinite(p0).all(1) & np.isfinite(p1).all(1)
        & np.isfinite(fp).all(1) & (p0 > 0).all(1) & (p1 > 0).all(1)
    )
    utility = np.full((n, experts), np.nan)
    net_return = np.full_like(utility, np.nan)
    mdd = np.full_like(utility, np.nan)
    fees = np.full_like(utility, np.nan)
    funding = np.full_like(utility, np.nan)
    feedback = np.full_like(utility, np.nan)
    segments = np.full((n, experts), -1, dtype=np.int64)
    segment_resets = np.zeros(experts, dtype=np.int64)
    exclusion = np.full((n, experts), "OUTSIDE_COMPLETE_7DAY_HORIZON", dtype="U40")
    for e in range(experts):
        nav, q, segment, active = 10000.0, np.zeros(assets), -1, False
        for i in range(n):
            finite = np.isfinite(w[i, e]).all()
            require(not ok[i, e] or finite, "Eligible expert has unknown target")
            # CASH is analytically executable without fictitious missing marks.
            valid = ok[i, e] and finite and (e == cash_index or common_economics[i])
            if not valid:
                active = False
                continue
            if not active:
                nav, q = 10000.0, np.zeros(assets)
                segment += 1
                segment_resets[e] += int(segment > 0)
                active = True
            before = nav
            if e != cash_index:
                nav, q, *_ = proxy_step(
                    nav, q, w[i, e], p0[i], p1[i], fp[i], good[i], 0.00135
                )
            feedback[i, e] = nav / before - 1
            segments[i, e] = segment
        for i in range(max(0, n - 6)):
            if not ok[i:i + 7, e].all() or not np.isfinite(w[i:i + 7, e]).all():
                exclusion[i, e] = "TARGET_NOT_AVAILABLE"
                continue
            if e == cash_index:
                utility[i, e] = net_return[i, e] = mdd[i, e] = 0.0
                fees[i, e] = funding[i, e] = 0.0
            elif common_economics[i:i + 7].all():
                metrics, _ = replay(
                    frames, indices[i:i + 7], w[i:i + 7, e], funding_scale,
                    0.00135, 10000.0,
                )
                utility[i, e] = reference_utility(metrics)
                net_return[i, e], mdd[i, e] = metrics["net_return"], metrics["mdd"]
                fees[i, e], funding[i, e] = metrics["fees"], metrics["funding"]
            else:
                exclusion[i, e] = "UNKNOWN_ECONOMIC_INTERVAL"
            if np.isfinite(utility[i, e]):
                exclusion[i, e] = "COMPLETE"
    complete = np.isfinite(utility)
    feedback_available = d[:, None] + DAY_US + LATENCY_US
    feedback_available = np.broadcast_to(feedback_available, feedback.shape).copy()
    past = np.full((n, experts, len(PAST_FEATURES)), np.nan)
    past_available = np.zeros((n, experts), dtype=np.int64)
    for i, decision in enumerate(d):
        for e in range(experts):
            matured = np.flatnonzero(feedback_available[:, e] < decision)
            if len(matured) < 30:
                continue
            own = matured[-30:]
            r = feedback[own, e]
            if not np.isfinite(r).all() or segments[own[0], e] < 0:
                continue
            if not np.all(segments[own, e] == segments[own[0], e]):
                continue
            values = np.r_[1.0, np.exp(np.cumsum(np.log1p(r)))]
            past[i, e] = (
                np.log1p(r[-7:]).sum(), np.log1p(r).sum(),
                np.sqrt(np.mean(np.minimum(r, 0.0) ** 2)),
                np.max(1.0 - values / np.maximum.accumulate(values)),
            )
            past_available[i, e] = feedback_available[own[-1], e]
    return dict(
        utility=utility, label_complete=complete,
        label_available_us=d + 7 * DAY_US + LATENCY_US,
        label_net_return=net_return, label_daily_mdd=mdd,
        label_fees_USDT=fees, label_funding_USDT=funding,
        net_feedback=feedback, feedback_available_us=feedback_available,
        feedback_segment_id=segments, past_feedback=past,
        past_feedback_available_us=past_available,
        past_feedback_complete=np.isfinite(past).all(2),
        common_economic_complete=common_economics,
        reference_segment_resets=segment_resets,
        label_exclusion_reason=exclusion,
    )


def bar_frame(recovery, symbols):
    parts = []
    for symbol in symbols:
        f = pl.read_parquet(recovery / "daily_features" / (symbol + ".parquet"))
        f = f.filter(
            pl.col("complete_kline") & pl.all_horizontal(
                [pl.col(k).is_finite() for k in ("open", "high", "low", "close", "volume")]
            )
        ).with_columns(
            pl.lit(symbol).alias("symbol"),
            pl.col("dt").dt.epoch("us").alias("open_us"),
        ).with_columns(
            (pl.col("open_us") + DAY_US).alias("close_us"),
            (pl.col("open_us") + DAY_US).alias("available_us"),
        )
        parts.append(f.select(
            "symbol", "open_us", "close_us", "available_us", "open", "high", "low",
            "close", "volume",
        ))
    return pl.concat(parts)


def frame_arrays(frame, decisions, symbols):
    lookup = {(int(r["available_us"]), r["symbol"]): r
              for r in frame.iter_rows(named=True)}
    require(len(lookup) == len(decisions) * len(symbols), "Duplicate/incomplete target keys")
    rows = [[lookup[int(t), s] for s in symbols] for t in decisions]
    targets = np.array([[r["target_weight"] for r in row] for row in rows])
    raw = np.array([[r["raw_signed_target"] for r in row] for row in rows])
    reasons = np.array([[r["eligibility_reason"] for r in row] for row in rows])
    # A recipe's known zero for an unavailable asset is preserved. Whole-expert
    # eligibility requires at least one actually ready member, never warmup cash.
    eligible = (reasons == "ELIGIBLE").any(1)
    return targets, raw, eligible, reasons == "ELIGIBLE"


def existing_targets(expert, bars, decisions, close, available, symbols):
    recipe = expert["recipe"]
    if recipe == "CASH":
        require(expert["mechanism"] == "CASH", "CASH mechanism identity")
        shape = (len(decisions), len(symbols))
        return np.zeros(shape), np.zeros(shape), np.ones(len(decisions), bool), np.ones(shape, bool)
    if recipe == "EXTERNAL_NPZ":
        path = Path(expert["target_path"])
        require(sha(path) == expert["target_sha256"], "External target identity changed")
        with np.load(path, allow_pickle=False) as f:
            require(np.array_equal(f["decision_us"], decisions), "External full target calendar")
            require(f["symbol_order"].tolist() == list(symbols), "External symbol order")
            eligible = f["eligible"].copy()
            require(eligible.shape == decisions.shape and eligible.dtype == bool,
                    "Boolean external expert eligibility")
            target_clock = f["target_available_us"]
            require(target_clock.shape == decisions.shape, "One source clock per external target")
            require(np.all(target_clock[eligible] <= decisions[eligible]), "Future external target")
            if expert.get("learned", False):
                names = (
                    "fit_completed_us", "train_cutoff_us", "maximum_training_label_available_us",
                    "maximum_scaler_source_available_us", "model_sha256", "scaler_sha256",
                )
                arrays = [f[name][eligible] for name in names]
                RankProvenance(*arrays[:4], tuple(arrays[4]), tuple(arrays[5])).validate(
                    decisions[eligible]
                )
            return (
                f["weights"].copy(), f["raw_weights"].copy(), eligible,
                f["asset_eligible"].copy(),
            )
    if recipe == "CSMOM21":
        from scripts.research.public_cross_section_momentum import public_targets

        weights, diagnostics = public_targets(close, available, decisions, symbols, symbols)
        assets = np.asarray(diagnostics["current_eligible"], bool)
        # Raw weekly weights are reconstructed from the original rank events.
        events = {r["rank_us"]: np.asarray(r["raw_weights"]) for r in diagnostics["rank_events"]}
        raw = np.zeros_like(weights)
        previous_rank = None
        held = np.zeros(len(symbols))
        for i, rank in enumerate(diagnostics["rank_us"]):
            if rank != previous_rank:
                held = events[rank].copy()
                previous_rank = rank
            held[~assets[i]] = 0.0
            raw[i] = held
        return weights, raw, assets.sum(1) >= 4, assets
    from scripts.investment import public_sma_perpetual, vol_managed_perpetual_target

    if recipe == "VOL_MANAGED_HOLD":
        frame, _ = vol_managed_perpetual_target.fixed_targets(bars, decisions, symbols=symbols)
    elif recipe == "PUBLIC_SMA50_200_SIGNED":
        frame, _ = public_sma_perpetual.fixed_targets(
            bars, decisions, "LONG_SHORT", symbols=symbols
        )
    elif recipe in ("DONCHIAN20", "DONCHIAN_EXIT10"):
        from scripts.investment import donchian_daily_pool_target

        frame, _ = donchian_daily_pool_target.fixed_targets(
            bars, decisions, symbols=symbols, exit_period=10 if recipe.endswith("EXIT10") else 20
        )
    else:
        raise ValueError("Not an implemented registered target recipe: " + recipe)
    return frame_arrays(frame, decisions, symbols)


def fold_admission(decisions, teacher, starts, *, selected=None):
    chosen = np.arange(teacher["utility"].shape[1]) if selected is None else np.asarray(selected)
    complete = teacher["label_complete"][:, chosen].all(1)
    complete &= teacher["past_feedback_complete"][:, chosen].all(1)
    records = []
    for start in starts:
        validation = int(pd.Timestamp(start).value // 1000)
        mask = chronological_training_mask(
            decisions, teacher["label_available_us"], complete, validation, 7
        )
        independent = nonoverlap_indices(decisions, teacher["label_available_us"], mask)
        per_expert = []
        for e in range(teacher["utility"].shape[1]):
            own = chronological_training_mask(
                decisions, teacher["label_available_us"],
                teacher["label_complete"][:, e] & teacher["past_feedback_complete"][:, e],
                validation, 7,
            )
            disjoint = nonoverlap_indices(decisions, teacher["label_available_us"], own)
            per_expert.append(dict(
                expert_index=e, mature_complete_rows=int(own.sum()),
                disjoint_intervals=len(disjoint), ridge_admissible=len(disjoint) >= 40,
                hist_gb_admissible=len(disjoint) >= 80,
                masked_output_training_not_implemented_or_approved=True,
            ))
        records.append(dict(
            validation_start=start, validation_start_us=validation,
            mature_complete_rows=int(mask.sum()), disjoint_intervals=len(independent),
            train_indices=independent.tolist(),
            ridge_admissible=len(independent) >= 40,
            hist_gb_admissible=len(independent) >= 80,
            selected_expert_indices=chosen.tolist(),
            support_before_actual_rank_OOF_and_pool_screen=True,
            per_expert_support=per_expert,
            per_expert_mature_label_rows=(teacher["label_complete"] &
                                         (teacher["label_available_us"][:, None]
                                          < validation - 7 * DAY_US)).sum(0).tolist(),
            per_expert_missing_past_feedback_rows=(
                ~teacher["past_feedback_complete"] &
                (teacher["label_available_us"][:, None]
                 < validation - 7 * DAY_US)).sum(0).tolist(),
            per_expert_label_exclusions=[
                {str(reason): int(count) for reason, count in zip(
                    *np.unique(teacher["label_exclusion_reason"][
                        teacher["label_available_us"] < validation - 7 * DAY_US, e
                    ], return_counts=True), strict=True)}
                for e in range(teacher["utility"].shape[1])
            ],
        ))
    return records


def build(spec, output):
    recovery = Path(spec["recovery_root"])
    coverage_path = recovery / "COVERAGE.json"
    require(sha(coverage_path) == spec["coverage_sha256"], "Recovery coverage identity changed")
    coverage = json.loads(coverage_path.read_text())
    require(sha(recovery / "PROTOCOL.json") == coverage["protocol_sha256"], "Recovery protocol")
    require(sha(recovery / "INPUTS.npz") == coverage["inputs_sha256"], "Ranker input identity")
    for ref in coverage["files"]:
        path = recovery / ref["path"]
        require(path.stat().st_size == ref["bytes"] and sha(path) == ref["sha256"],
                "Recovery member")
    for name, digest in spec["source_hashes"].items():
        require(sha(ROOT / name) == digest, "Registered teacher source changed: " + name)
    require(spec["horizon_days"] == 7 and spec["side_cost"] == 0.00135,
            "Original seven-day BASE27 teacher rules")
    symbols = tuple(spec["symbols"])
    experts = spec["experts"]
    require(len(symbols) == len(set(symbols)) and symbols == CORE, "Registered CORE5 order")
    names = [e["name"] for e in experts]
    require(len(names) == len(set(names)) and names.count("CASH") == 1,
            "Unique expert identities/CASH")
    frames = {s: pd.read_parquet(recovery / "economics" / (s + "_daily.parquet"))
              for s in symbols}
    available = frames[symbols[0]].available_us.to_numpy(np.int64)
    start = int(pd.Timestamp(spec["start"]).value // 1000)
    end = int(pd.Timestamp(spec["end_exclusive"]).value // 1000)
    decisions = np.arange(start, end, DAY_US, dtype=np.int64)
    require(len(decisions) > 0 and decisions[-1] <= available[-3], "Complete future endpoint rows")
    with np.load(recovery / "INPUTS.npz", allow_pickle=False) as f:
        input_order = f["symbol_order"].tolist()
        columns = [input_order.index(s) for s in symbols]
        rank_decisions = f["dates_us"] + DAY_US
        close = f["close"][:, columns].copy()
        index = np.searchsorted(rank_decisions, decisions)
        require(np.array_equal(rank_decisions[index], decisions), "Exact market feature mapping")
        x = f["x"][index][:, columns].copy()
        feature_order = f["feature_order"].copy()
    bars = bar_frame(recovery, symbols)
    generated = [existing_targets(e, bars, decisions, close, rank_decisions, symbols)
                 for e in experts]
    targets, raw = [np.stack([v[k] for v in generated], axis=1) for k in (0, 1)]
    eligible = np.stack([v[2] for v in generated], axis=1)
    asset_eligible = np.stack([v[3] for v in generated], axis=1)
    require(targets.shape == (len(decisions), len(experts), len(symbols)), "Ordered target cube")
    finite = np.isfinite(targets).all(2)
    require(np.all(finite | ~eligible), "Eligible targets must be finite")
    require(np.max(np.abs(targets[finite])) <= 0.3 + 1e-12
            and np.max(np.abs(targets[finite]).sum(1)) <= 0.6 + 1e-12, "Expert target caps")
    teacher = teacher_arrays(frames, decisions, targets, eligible,
                             cash_index=names.index("CASH"), funding_scale=spec["funding_scale"])
    folds = fold_admission(decisions, teacher, spec["validation_starts"])
    full_market_complete = np.isfinite(x).all((1, 2))
    btc_market_complete = np.isfinite(x[:, 0]).all(1)
    feature_support = {}
    for description, feature_mask in (
        ("ALL_CORE5_X24_FIELDS", full_market_complete),
        ("BTC_X24_FIELDS_ONLY", btc_market_complete),
    ):
        own_teacher = dict(teacher)
        own_teacher["label_complete"] = teacher["label_complete"] & feature_mask[:, None]
        feature_support[description] = fold_admission(
            decisions, own_teacher, spec["validation_starts"]
        )
    partial_pools = {
        name: fold_admission(decisions, teacher, spec["validation_starts"], selected=indices)
        for name, indices in spec.get("partial_pool_diagnostics", {}).items()
    }
    with np.load(recovery / "INPUTS.npz", allow_pickle=False) as f:
        candidates = f["eligible_ranker_indices"]
        maturity = f["label_end_us"]
        snapshot_admission = []
        for snapshot in spec.get("rank_snapshots_proposed", []):
            available_at = int(pd.Timestamp(snapshot).value // 1000)
            cutoff = available_at - 60 * DAY_US
            count = int((maturity[candidates] < cutoff).sum())
            snapshot_admission.append(dict(
                logical_fit_available=snapshot, training_cutoff_us=cutoff,
                mature_CORE5_dates=count, minimum_180_met=count >= 180,
                original_60day_extra_embargo_retained=True,
                rank_predictions_available=False, model_or_scaler_restored=False,
            ))
    output.mkdir(parents=True, exist_ok=False)
    path = output / "SELECTOR_INPUTS.npz"
    np.savez_compressed(
        path, decision_us=decisions, symbol_order=np.array(symbols), expert_order=np.array(names),
        mechanism_order=np.array([e["mechanism"] for e in experts]), targets=targets,
        raw_targets=raw, target_eligible=eligible, asset_eligible=asset_eligible,
        target_available_us=np.broadcast_to(decisions[:, None], eligible.shape),
        market_features=x, market_feature_order=feature_order,
        market_feature_available_us=decisions,
        market_feature_complete_by_asset=np.isfinite(x).all(2),
        all_market_features_complete=full_market_complete,
        past_feedback_order=np.array(PAST_FEATURES), **teacher,
    )
    binding = dict(
        status="COMPLETE_NO_FIT_UNSCREENED_EXISTING_EXPERT_REFERENCE_INPUTS",
        selector_inputs_sha256=sha(path), selector_inputs_bytes=path.stat().st_size,
        recovery_inputs_sha256=coverage["inputs_sha256"],
        coverage_sha256=spec["coverage_sha256"], protocol=spec,
        models_fit=0, native_wallets=0, pool_selected=False,
        funding_unit_certified=False, source_is_Binance_Bybit_fee_cross_venue_proxy=True,
        qualification="NONE_CASH", folds=folds,
        market_feature_support_diagnostics=feature_support,
        market_feature_columns_selected=False,
        model_fit_admission_requires_actual_selected_feature_completeness=True,
        partial_pool_support=partial_pools, rank_snapshot_admission=snapshot_admission,
        full_pool_with_learned_experts_admitted=False,
        supplied_learned_target_experts=[e["name"] for e in experts if e.get("learned", False)],
        missing_full_pool_inputs=("Other historical learned checkpoints/OOF, multi-product carry "
                                  "bridge and final mechanism screen remain unavailable"),
        label_counts_per_expert=teacher["label_complete"].sum(0).tolist(),
        reference_segment_resets=teacher["reference_segment_resets"].tolist(),
        feedback_is_segmented_reference_not_full_wallet=True,
        common_portfolio_increment="NOT_COMPUTED_DO_NOT_SUM_EXPERT_RETURNS",
        minute_liquidation_or_MDD_available=False,
        unsupported_inventory=spec["unsupported_inventory"],
        future_label_arrays_must_be_masked_by_each_fold=True,
    )
    (output / "BINDING.json").write_text(json.dumps(binding, indent=2) + "\n")
    return binding


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocol", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    result = build(json.loads(a.protocol.read_text()), a.output)
    print(json.dumps({k: result[k] for k in ("status", "label_counts_per_expert", "folds")}))


if __name__ == "__main__":
    main()
