"""Preregistered, causal Logistic research. This module never evaluates the holdout."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MINUTE_US = 60_000_000
INTERVAL_US = {"15m": 15 * MINUTE_US, "1h": 60 * MINUTE_US}
FEATURE_NAMES = (
    "log_return_1", "log_return_4", "log_return_16", "volatility_24",
    "volatility_96", "volume_z96", "range_fraction", "body_fraction",
    "ema_gap", "taker_fraction",
)


class InsufficientDataError(ValueError):
    """No valid statistical test can be performed with the available observations."""


def date_us(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp() * 1e6)


def month_add(value: str, months: int) -> str:
    date = datetime.fromisoformat(value)
    index = date.year * 12 + date.month - 1 + months
    return f"{index // 12:04d}-{index % 12 + 1:02d}-01"


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


def load_protocol(path: str | Path) -> dict[str, Any]:
    protocol = json.loads(Path(path).read_text())
    configurations = protocol["configurations"]
    if not 0 < len(configurations) <= min(5, protocol["max_configurations"]):
        raise ValueError("Preregistered configuration budget exceeded")
    if len({config["id"] for config in configurations}) != len(configurations):
        raise ValueError("Duplicate configuration IDs")
    if tuple(protocol["feature_names"]) != FEATURE_NAMES:
        raise ValueError("Feature definitions require a new implementation/protocol version")
    if protocol["primary_baseline"] != "B2":
        raise ValueError("Primary comparator must remain B2")
    if protocol["fit_policy"] != "training_only_no_refit_on_validation":
        raise ValueError("Unsupported fit policy")
    if protocol["label_cost_bps_per_side"] < 15:
        raise ValueError("Cost cannot be reduced below the preregistered conservative proxy")
    for config in configurations:
        if config["interval"] not in INTERVAL_US or config["C"] <= 0:
            raise ValueError("Invalid model configuration")
        if not 0.5 <= config["threshold"] < 1:
            raise ValueError("Invalid probability threshold")
    return protocol


def register_protocol(protocol: dict[str, Any], state_path: str | Path,
                      resume_reason: str | None = None) -> dict[str, Any]:
    """Register before fitting and reject edits, repeats, or abandoned OOS attempts."""
    state_path = Path(state_path)
    fingerprint = canonical_hash(protocol)
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state.get("holdout_revealed"):
            raise ValueError("A revealed holdout cannot be reused by development research")
        if state["protocol_sha256"] != fingerprint:
            raise ValueError("Registered protocol changed; new versions cannot reuse the tests")
        if state["status"] != "registered":
            if state["status"] not in {"oos_started", "invalid_run"} or not resume_reason:
                raise ValueError("OOS was already started; results cannot be rerun or overwritten")
            state.setdefault("audit", []).append({"event": "explicit_technical_resume",
                                                  "reason": resume_reason})
            _write_json(state_path, state)
        return state
    state = {"version": protocol["version"], "protocol_sha256": fingerprint,
             "status": "registered", "holdout_revealed": False,
             "configurations": [config["id"] for config in protocol["configurations"]]}
    _write_json(state_path, state)
    return state


@dataclass(frozen=True)
class Fold:
    index: int
    train_start_us: int
    train_end_us: int
    validation_end_us: int
    test_end_us: int

    @property
    def test_start_us(self) -> int:
        return self.validation_end_us


def make_folds(protocol: dict[str, Any]) -> list[Fold]:
    folds = []
    start = protocol["research_start"]
    cutoff = date_us(protocol["holdout_start"])
    while True:
        train_end = month_add(start, protocol["train_months"])
        validation_end = month_add(train_end, protocol["validation_months"])
        test_end = month_add(validation_end, protocol["test_months"])
        if date_us(test_end) > cutoff:
            break
        folds.append(Fold(len(folds), date_us(start), date_us(train_end),
                          date_us(validation_end), date_us(test_end)))
        start = month_add(start, protocol["stride_months"])
    return folds


def development_only(frame: pl.DataFrame, protocol: dict[str, Any]) -> pl.DataFrame:
    """Filter before features, labels, model fitting, or performance calculation."""
    return frame.filter((pl.col("open_us") >= date_us(protocol["research_start"])) &
                        (pl.col("open_us") < date_us(protocol["holdout_start"])) &
                        (pl.col("available_us") <= date_us(protocol["holdout_start"])))


def build_features(bars: pl.DataFrame) -> pl.DataFrame:
    """All rolling windows are trailing and reset after any missing decision bar."""
    parts = []
    for group in bars.sort(["symbol", "interval", "open_us"]).partition_by(
        ["symbol", "interval"], maintain_order=True
    ):
        interval = group["interval"][0]
        step = INTERVAL_US[interval]
        group = group.with_columns(
            (pl.col("open_us").diff().fill_null(step) != step).cast(pl.Int64)
            .cum_sum().alias("_segment")
        )
        for segment in group.partition_by("_segment", maintain_order=True):
            segment = segment.with_columns(
                pl.col("close").log().diff().alias("log_return_1"),
                (pl.col("close") / pl.col("close").shift(4)).log().alias("log_return_4"),
                (pl.col("close") / pl.col("close").shift(16)).log().alias("log_return_16"),
                (pl.col("high") - pl.col("low")).truediv(pl.col("close"))
                .alias("range_fraction"),
                (pl.col("close") - pl.col("open")).truediv(pl.col("open"))
                .alias("body_fraction"),
                (pl.col("close").ewm_mean(span=20, adjust=False, min_samples=100) /
                 pl.col("close").ewm_mean(span=100, adjust=False, min_samples=100) - 1)
                .alias("ema_gap"),
                pl.when(pl.col("volume") > 0)
                .then(pl.col("taker_buy_base") / pl.col("volume")).otherwise(0.5)
                .alias("taker_fraction"),
            ).with_columns(
                pl.col("log_return_1").rolling_std(window_size=24, min_samples=24)
                .alias("volatility_24"),
                pl.col("log_return_1").rolling_std(window_size=96, min_samples=96)
                .alias("volatility_96"),
                ((pl.col("volume") - pl.col("volume").rolling_mean(96)) /
                 (pl.col("volume").rolling_std(96) + 1e-12)).alias("volume_z96"),
            )
            parts.append(segment.drop("_segment"))
    if not parts:
        raise ValueError("No development bars")
    features = pl.concat(parts).sort(["available_us", "symbol"])
    return features.with_columns([
        pl.when(pl.col(name).is_finite()).then(pl.col(name)).otherwise(None).alias(name)
        for name in FEATURE_NAMES
    ])


def build_labels(features: pl.DataFrame, minute_bars: pl.DataFrame,
                 horizon_minutes: int = 240, cost_bps_per_side: float = 15) -> pl.DataFrame:
    """Executable-minute opens, a fixed horizon, and a complete intervening minute path."""
    if horizon_minutes <= 0 or cost_bps_per_side < 0:
        raise ValueError("Invalid label horizon/cost")
    labels = []
    for group in features.partition_by("symbol", maintain_order=True):
        symbol = group["symbol"][0]
        minutes = minute_bars.filter(pl.col("symbol") == symbol).sort("open_us")
        if minutes.height == 0:
            continue
        timestamps = minutes["open_us"].to_numpy()
        prices = minutes["open"].to_numpy()
        if np.any(np.diff(timestamps) <= 0):
            raise ValueError("Minute keys must be unique and increasing")
        available = group["available_us"].to_numpy()
        expected_entry = ((available + MINUTE_US - 1) // MINUTE_US) * MINUTE_US
        entry = np.searchsorted(timestamps, expected_entry, side="left")
        exits = entry + horizon_minutes
        safe_entry = np.minimum(entry, len(timestamps) - 1)
        safe_exit = np.minimum(exits, len(timestamps) - 1)
        valid = ((entry < len(timestamps)) & (exits < len(timestamps)) &
                 (timestamps[safe_entry] == expected_entry) &
                 (timestamps[safe_exit] - timestamps[safe_entry] ==
                  horizon_minutes * MINUTE_US) &
                 (prices[safe_entry] > 0) & (prices[safe_exit] > 0))
        gross = prices[safe_exit] / prices[safe_entry] - 1
        cost = cost_bps_per_side / 10_000
        net = (prices[safe_exit] / prices[safe_entry]) * (1 - cost) / (1 + cost) - 1
        labels.append(group.with_columns(
            pl.Series("entry_us", np.where(valid, timestamps[safe_entry] + 1, 0)),
            pl.Series("label_end_us", np.where(valid, timestamps[safe_exit] + 1, 0)),
            pl.Series("gross_return", gross), pl.Series("net_return", net),
            pl.Series("label", (net > 0).astype(np.int8)),
            pl.Series("label_valid", valid),
        ))
    if not labels:
        raise ValueError("No minute labels available")
    return pl.concat(labels).sort(["available_us", "symbol"])


def split_samples(samples: pl.DataFrame, start_us: int, end_us: int,
                  interval: str, embargo_bars: int = 1) -> pl.DataFrame:
    step = INTERVAL_US[interval]
    return samples.filter(
        (pl.col("available_us") >= start_us + embargo_bars * step) &
        (pl.col("available_us") < end_us) &
        (pl.col("label_end_us") < end_us - embargo_bars * step) &
        pl.col("label_valid") &
        pl.all_horizontal([pl.col(name).is_not_null() & pl.col(name).is_finite()
                           for name in FEATURE_NAMES])
    )


def fit_model(train: pl.DataFrame, config: dict[str, Any], minimum_rows: int = 1000) -> Pipeline:
    if train.height < minimum_rows or train["label"].n_unique() != 2:
        raise InsufficientDataError("Insufficient training observations or one-class labels")
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(C=config["C"], max_iter=1000,
                                          solver="lbfgs", random_state=20260930)),
    ])
    model.fit(train.select(FEATURE_NAMES).to_numpy(), train["label"].to_numpy())
    return model


def probability_targets(model: Pipeline, samples: pl.DataFrame,
                        config: dict[str, Any], maximum_weight: float = 0.3) -> pl.DataFrame:
    probability = model.predict_proba(samples.select(FEATURE_NAMES).to_numpy())[:, 1]
    return samples.select(["available_us", "symbol"]).with_columns(
        pl.Series("target_weight", np.where(probability >= config["threshold"],
                                            maximum_weight, 0.0)),
        pl.Series("probability", probability),
    )


def export_model(model: Pipeline, train: pl.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    scaler = model.named_steps["scaler"]
    classifier = model.named_steps["classifier"]
    return {"configuration": config, "features": list(FEATURE_NAMES),
            "training_rows": train.height,
            "training_start_us": train["available_us"].min(),
            "training_last_available_us": train["available_us"].max(),
            "training_last_label_end_us": train["label_end_us"].max(),
            "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(),
            "coefficients": classifier.coef_[0].tolist(),
            "intercept": float(classifier.intercept_[0]),
            "classes": classifier.classes_.tolist(),
            "iterations": classifier.n_iter_.tolist()}


def predict_exported_model(model: dict[str, Any], samples: pl.DataFrame,
                           maximum_weight: float = 0.3) -> pl.DataFrame:
    """Portable frozen JSON inference for a separately qualified shadow process."""
    if tuple(model["features"]) != FEATURE_NAMES or model["classes"] != [0, 1]:
        raise ValueError("Unexpected model feature/class contract")
    matrix = samples.select(FEATURE_NAMES).to_numpy()
    if not np.isfinite(matrix).all():
        raise ValueError("Invalid or insufficient feature history; freeze signals")
    standardized = (matrix - np.asarray(model["scaler_mean"])) / np.asarray(model["scaler_scale"])
    score = standardized @ np.asarray(model["coefficients"]) + model["intercept"]
    probability = 1 / (1 + np.exp(-np.clip(score, -700, 700)))
    return samples.select(["available_us", "symbol"]).with_columns(
        pl.Series("probability", probability),
        pl.Series("target_weight", np.where(probability >= model["configuration"]["threshold"],
                                            maximum_weight, 0.0)),
    )


def excess_bootstrap(candidate: pl.DataFrame, baseline: pl.DataFrame,
                     block_days: int = 7, replicates: int = 2000,
                     seed: int = 20260930) -> dict[str, Any]:
    paired = candidate.select("date", pl.col("return").alias("candidate")).join(
        baseline.select("date", pl.col("return").alias("baseline")), on="date", how="inner"
    ).sort("date")
    if paired.height != candidate.height or paired.height != baseline.height:
        raise ValueError("Candidate and B2 daily observations must cover identical UTC dates")
    returns = paired["candidate"].to_numpy() - paired["baseline"].to_numpy()
    if len(returns) < block_days:
        return {"days": len(returns), "annual_mean_excess": None, "ci_95": None}
    rng = np.random.default_rng(seed)
    blocks = math.ceil(len(returns) / block_days)
    estimates = np.empty(replicates)
    offsets = np.arange(block_days)
    for index in range(replicates):
        starts = rng.integers(0, len(returns), size=blocks)
        indices = ((starts[:, None] + offsets) % len(returns)).ravel()[:len(returns)]
        estimates[index] = returns[indices].mean() * 365
    return {"days": len(returns), "annual_mean_excess": float(returns.mean() * 365),
            "ci_95": np.quantile(estimates, [.025, .975]).tolist(),
            "method": f"paired circular {block_days}-day block bootstrap; annualized mean excess",
            "seed": seed, "replicates": replicates}


def quarter_profit_fraction(daily_nav: pl.DataFrame, initial_nav: float) -> float | None:
    if daily_nav.height == 0:
        return None
    nav = daily_nav["nav"].to_numpy()
    profit = np.diff(np.concatenate(([initial_nav], nav)))
    by_quarter: dict[str, float] = {}
    for date, amount in zip(daily_nav["date"].to_list(), profit, strict=True):
        date_value = str(date)
        key = f"{date_value[:4]}Q{(int(date_value[5:7]) - 1) // 3 + 1}"
        by_quarter[key] = by_quarter.get(key, 0.0) + float(amount)
    total = float(profit.sum())
    return max(by_quarter.values()) / total if total > 0 else None


def calendar_performance(daily_nav: pl.DataFrame, initial_nav: float) -> dict[str, list[dict]]:
    """Consecutive calendar periods include costs and begin from the prior NAV."""
    periods: dict[str, dict[str, dict]] = {"monthly": {}, "yearly": {}}
    previous = initial_nav
    for date, nav in daily_nav.select("date", "nav").iter_rows():
        for kind, size in [("monthly", 7), ("yearly", 4)]:
            key = str(date)[:size]
            row = periods[kind].setdefault(key, {"period": key, "start_nav": previous,
                                                "end_nav": nav, "days": 0})
            row["end_nav"] = nav
            row["days"] += 1
        previous = nav
    return {kind: [{**row, "return": row["end_nav"] / row["start_nav"] - 1,
                    "pnl": row["end_nav"] - row["start_nav"]}
                   for row in mapping.values()] for kind, mapping in periods.items()}


def evaluate_gates(summary: dict[str, Any], baseline: dict[str, Any],
                   stress: dict[str, dict[str, Any]], quarter_fraction: float | None,
                   gates: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "positive_net_return": summary["total_return"] > 0,
        "daily_sharpe": summary["sharpe"] >= gates["minimum_sharpe"],
        "exceed_B2": summary["total_return"] > baseline["total_return"],
        "daily_risk_observable": summary.get("daily_risk_observable", False) is True and
        summary.get("exposed_valuation_gap_days", 1) == 0,
        "drawdown": abs(summary["max_drawdown"]) <= gates["maximum_drawdown"],
        "independent_round_trips": summary["round_trip_count"] >= gates["minimum_round_trips"],
        "quarter_concentration": quarter_fraction is not None and
        quarter_fraction <= gates["maximum_quarter_profit_fraction"],
        "fee_x2_nonnegative": stress["fee_x2"]["total_return"] >= 0,
        "slippage_x2_nonnegative": stress["slippage_x2"]["total_return"] >= 0,
    }
    passed = all(checks.values())
    return {"status": "HOLDOUT_REQUIRED" if passed else "STOP",
            "development_passed": passed, "checks": checks,
            "failed_checks": [name for name, passed in checks.items() if not passed],
            "risk_evidence": ("observed_UTC_daily_NAV_only" if checks["daily_risk_observable"]
                              else "cannot_verify_daily_drawdown_with_stale_open_exposure"),
            "holdout": "locked, untested; passing development is not full research GO"}


def _flat_targets(when: int, symbols: list[str]) -> pl.DataFrame:
    return pl.DataFrame({"available_us": [when] * len(symbols), "symbol": symbols,
                         "target_weight": [0.0] * len(symbols),
                         "probability": [None] * len(symbols)},
                        schema_overrides={"available_us": pl.Int64, "probability": pl.Float64})


def _period_minutes(minutes: pl.DataFrame, start_us: int, end_us: int) -> pl.DataFrame:
    # Common covariance uses a 30-day lookback plus the preceding daily close.
    # Keep 32 complete days, so repeated validations never scan all four years.
    return minutes.filter((pl.col("open_us") >= start_us - 32 * 1440 * MINUTE_US) &
                          (pl.col("open_us") < end_us))


def run_research(bars: pl.DataFrame, minute_bars: pl.DataFrame,
                 protocol_path: str | Path, output_dir: str | Path,
                 state_path: str | Path,
                 source_hashes: dict[str, str] | None = None,
                 resume_reason: str | None = None) -> dict[str, Any]:
    """One immutable outer-test attempt. Root alone may authorize the separate holdout."""
    from .backtest import BacktestConfig, baseline_targets, run_backtest
    from .data import verify_dataset_lock
    from .disk import check

    protocol = load_protocol(protocol_path)
    # Seven reports are capped at 50 MB each by the backtest writer; targets/models
    # fit in the remaining 50 MB. One batch reservation avoids repeated full scans.
    check(reserve=400_000_000)
    dataset_lock = verify_dataset_lock()
    if (dataset_lock["holdout_start_utc"][:10] != protocol["holdout_start"] or
            dataset_lock["holdout_end_exclusive_utc"][:10] != protocol["holdout_end"]):
        raise ValueError("Dataset and protocol holdout dates differ")
    output_dir = Path(output_dir).resolve()
    if not str(output_dir).startswith("/mnt/d/"):
        raise ValueError("Research outputs must stay on D: via /mnt/d")
    state_path = Path(state_path)
    state = register_protocol(protocol, state_path, resume_reason)
    if state.get("dataset_id", dataset_lock["dataset_id"]) != dataset_lock["dataset_id"]:
        raise ValueError("Technical resume cannot change the locked dataset")
    if "source_hashes" in state and state["source_hashes"] != (source_hashes or {}):
        raise ValueError("Technical resume cannot change input source hashes")
    folds = make_folds(protocol)
    if not folds:
        raise InsufficientDataError("No complete 24/3/3-month folds; cannot shorten the protocol")
    bars = development_only(bars, protocol)
    minute_bars = development_only(minute_bars, protocol)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "protocol.json", protocol)
    _write_json(output_dir / "data_hashes.json", {
        "dataset_lock": dataset_lock, "source_hashes": source_hashes or {}})
    _write_json(output_dir / "folds.json", [asdict(fold) for fold in folds])
    state.update(status="oos_started", source_hashes=source_hashes or {},
                 dataset_id=dataset_lock["dataset_id"])
    state.setdefault("audit", []).append({
        "event": "attempt_started", "resume_reason": resume_reason,
        "research_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    })
    _write_json(state_path, state)
    baseline_bars = bars.filter(pl.col("interval") == protocol["baseline_interval"])
    baseline_signals = baseline_targets(baseline_bars, "B2")
    reset_times = sorted({time for fold in folds for time in (
        fold.test_start_us, fold.test_end_us - INTERVAL_US["1h"])})
    baseline_resets = pl.concat([_flat_targets(time, protocol["symbols"]).select(
        ["available_us", "symbol", "target_weight"]) for time in reset_times])
    baseline_signals = pl.concat([
        baseline_signals.join(baseline_resets.select("available_us", "symbol"),
                              on=["available_us", "symbol"], how="anti"),
        baseline_resets,
    ]).sort(["available_us", "symbol"])
    base = BacktestConfig(start_us=folds[0].test_start_us, end_us=folds[-1].test_end_us,
                          liquidate_at_end=True)
    oos_minutes = _period_minutes(minute_bars, folds[0].test_start_us, folds[-1].test_end_us)
    baseline_result = run_backtest(baseline_bars, oos_minutes, baseline_signals, base)
    baseline_result.write_report(output_dir / "B2", disk_checked=True)
    reports = {}
    for interval in protocol["final_selection_priority"]:
        candidate_report = output_dir / interval / "candidate_summary.json"
        if resume_reason and candidate_report.exists():
            completed_candidate = json.loads(candidate_report.read_text())
            if completed_candidate["gates"]["status"] != "INVALID_RUN":
                reports[interval] = completed_candidate
                continue
        configs = [config for config in protocol["configurations"]
                   if config["interval"] == interval]
        selected_bars = bars.filter(pl.col("interval") == interval)
        all_targets = []
        fold_reports = []
        try:
            if selected_bars.is_empty():
                raise InsufficientDataError(f"No {interval} development bars")
            labeled = build_labels(build_features(selected_bars), minute_bars,
                                   protocol["label_horizon_minutes"],
                                   protocol["label_cost_bps_per_side"])
            for fold in folds:
                train = split_samples(labeled, fold.train_start_us, fold.train_end_us,
                                      interval, protocol["embargo_bars"])
                validation = split_samples(labeled, fold.train_end_us, fold.validation_end_us,
                                           interval, protocol["embargo_bars"])
                test = split_samples(labeled, fold.validation_end_us, fold.test_end_us,
                                     interval, protocol["embargo_bars"])
                if validation.is_empty() or test.is_empty():
                    raise InsufficientDataError("Empty validation/test split after purge")
                validation_minutes = _period_minutes(
                    minute_bars, fold.train_end_us, fold.validation_end_us)
                ranking = []
                for config in configs:
                    model = fit_model(train, config, protocol["minimum_training_rows"])
                    targets = probability_targets(model, validation, config,
                                                  protocol["risk"]["single_asset_max"])
                    targets = pl.concat([targets, _flat_targets(
                        fold.validation_end_us - INTERVAL_US[interval], protocol["symbols"])])
                    validation_result = run_backtest(selected_bars, validation_minutes, targets,
                                                    BacktestConfig(
                                                        start_us=fold.train_end_us,
                                                        end_us=fold.validation_end_us,
                                                        liquidate_at_end=True))
                    ranking.append((validation_result.summary["sharpe"], -config["C"],
                                    config, model, validation_result.summary))
                _, _, config, model, validation_summary = max(ranking, key=lambda row: row[:2])
                fold_dir = output_dir / interval / f"fold_{fold.index:02d}"
                _write_json(fold_dir / "model.json", export_model(model, train, config))
                selection = {"fold": fold.index, "selected": config["id"],
                             "selection_source": "validation_only",
                             "validation_results": {item[2]["id"]: item[4] for item in ranking},
                             "train_rows": train.height, "validation_rows": validation.height,
                             "test_rows": test.height}
                _write_json(fold_dir / "selection.json", selection)
                fold_reports.append(selection)
                targets = probability_targets(model, test, config,
                                              protocol["risk"]["single_asset_max"])
                all_targets.extend([_flat_targets(fold.test_start_us, protocol["symbols"]),
                                    targets, _flat_targets(
                                        fold.test_end_us - INTERVAL_US["1h"],
                                        protocol["symbols"])])
            targets = pl.concat(all_targets).sort(["available_us", "symbol"])
            targets.write_parquet(output_dir / interval / "oos_targets.parquet")
            result = run_backtest(selected_bars, oos_minutes, targets, base)
            result.write_report(output_dir / interval / "base", disk_checked=True)
            stress = {}
            for name, cost_args in [("fee_x2", {"fee_multiplier": 2}),
                                    ("slippage_x2", {"slippage_multiplier": 2})]:
                stress_result = run_backtest(selected_bars, oos_minutes, targets, BacktestConfig(
                    start_us=folds[0].test_start_us, end_us=folds[-1].test_end_us,
                    liquidate_at_end=True, **cost_args))
                stress_result.write_report(output_dir / interval / name, disk_checked=True)
                stress[name] = stress_result.summary
            fraction = quarter_profit_fraction(result.daily_nav, base.initial_cash)
            gates = evaluate_gates(result.summary, baseline_result.summary, stress,
                                   fraction, protocol["gates"])
            reports[interval] = {"gates": gates, "summary": result.summary, "stress": stress,
                                 "quarter_profit_fraction": fraction, "folds": fold_reports,
                                 "B2": baseline_result.summary,
                                 "excess_total_return": result.summary["total_return"] -
                                 baseline_result.summary["total_return"],
                                 "calendar_performance": calendar_performance(
                                     result.daily_nav, base.initial_cash),
                                 "excess_confidence": excess_bootstrap(
                                     result.daily_nav, baseline_result.daily_nav,
                                     **protocol["bootstrap"])}
        except InsufficientDataError as error:
            reports[interval] = {"gates": {"status": "INSUFFICIENT_DATA",
                                          "development_passed": False},
                                 "reason": str(error), "folds": fold_reports}
        except Exception as error:
            reports[interval] = {"gates": {"status": "INVALID_RUN", "development_passed": False},
                                 "reason": f"{type(error).__name__}: {error}",
                                 "folds": fold_reports}
            state.setdefault("audit", []).append({"event": "technical_error",
                                                  "interval": interval,
                                                  "reason": reports[interval]["reason"]})
            _write_json(state_path, state)
        _write_json(candidate_report, reports[interval])
    winners = [interval for interval in protocol["final_selection_priority"]
               if reports[interval]["gates"]["development_passed"]]
    invalid = any(candidate["gates"]["status"] == "INVALID_RUN"
                  for candidate in reports.values())
    insufficient = any(candidate["gates"]["status"] == "INSUFFICIENT_DATA"
                       for candidate in reports.values())
    status = ("INVALID_RUN" if invalid else "HOLDOUT_REQUIRED" if winners
              else "INSUFFICIENT_DATA" if insufficient else "STOP")
    frozen_model = None
    if winners and not invalid:
        frozen_model = freeze_final_model(
            bars, minute_bars, protocol, winners[0], output_dir / "selected_model.json")
    report = {"version": protocol["version"], "protocol_sha256": canonical_hash(protocol),
              "dataset_id": dataset_lock["dataset_id"],
              "status": status,
              "selected_interval": winners[0] if winners else None,
              "selection_rule": "first passing interval in preregistered priority, no OOS ranking",
              "holdout_revealed": False, "holdout_start": protocol["holdout_start"],
              "holdout_end": protocol["holdout_end"], "candidates": reports,
              "incomplete_fold_policy": "skipped; no shortened final fold",
              "bootstrap_is_proof": False,
              "frozen_model_sha256": canonical_hash(frozen_model) if frozen_model else None}
    _write_json(output_dir / "summary.json", report)
    _write_research_markdown(output_dir / "REPORT.md", report)
    state.update(status="invalid_run" if invalid else "completed", result_status=report["status"],
                 selected_interval=report["selected_interval"])
    _write_json(state_path, state)
    return report


def freeze_final_model(bars: pl.DataFrame, minute_bars: pl.DataFrame,
                       protocol: dict[str, Any], interval: str, path: Path) -> dict[str, Any]:
    """Apply the same registered training/validation rule at the holdout boundary."""
    from .backtest import BacktestConfig, run_backtest

    end = protocol["holdout_start"]
    validation_start = month_add(end, -protocol["validation_months"])
    training_start = month_add(validation_start, -protocol["train_months"])
    bars = development_only(bars, protocol).filter(pl.col("interval") == interval)
    minute_bars = development_only(minute_bars, protocol)
    labeled = build_labels(build_features(bars), minute_bars,
                           protocol["label_horizon_minutes"],
                           protocol["label_cost_bps_per_side"])
    train = split_samples(labeled, date_us(training_start), date_us(validation_start),
                          interval, protocol["embargo_bars"])
    validation = split_samples(labeled, date_us(validation_start), date_us(end),
                               interval, protocol["embargo_bars"])
    ranking = []
    for config in protocol["configurations"]:
        if config["interval"] != interval:
            continue
        model = fit_model(train, config, protocol["minimum_training_rows"])
        targets = probability_targets(model, validation, config)
        result = run_backtest(bars, _period_minutes(
            minute_bars, date_us(validation_start), date_us(end)), targets, BacktestConfig(
            start_us=date_us(validation_start), end_us=date_us(end), liquidate_at_end=True))
        ranking.append((result.summary["sharpe"], -config["C"], config, model, result.summary))
    _, _, configuration, model, _ = max(ranking, key=lambda item: item[:2])
    exported = export_model(model, train, configuration)
    exported.update(protocol_sha256=canonical_hash(protocol), interval=interval,
                    validation_start_us=date_us(validation_start),
                    validation_end_us=date_us(end),
                    validation_selection="highest_net_sharpe_then_lower_C",
                    validation_results={item[2]["id"]: item[4] for item in ranking},
                    holdout_revealed=False)
    _write_json(path, exported)
    return exported


def _write_research_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = ["# P04 预登记 Logistic 外层研究结果", "",
             f"状态：**{report['status']}**。最终六个月仍锁定，未计算绩效。", "",
             "训练 24 个月、验证 3 个月、测试 3 个月、步长 3 个月；不完整 fold 跳过。",
             "C 仅根据当轮验证集选择，scaler 和模型仅拟合训练集。", "",
             "| 候选 | 状态 | OOS 净收益 | 日度 Sharpe | B2 净收益 | 未过门槛 |",
             "|---|---|---:|---:|---:|---|"]
    for interval, candidate in report["candidates"].items():
        summary = candidate.get("summary", {})
        baseline = candidate.get("B2", {})
        failed = ", ".join(candidate["gates"].get("failed_checks", []))
        failed = failed or candidate.get("reason", "—")
        values = [summary.get("total_return"), summary.get("sharpe"),
                  baseline.get("total_return")]
        rendered = [f"{value:.6f}" if value is not None else "—" for value in values]
        lines.append(f"| {interval} | {candidate['gates']['status']} | " +
                     " | ".join(rendered) + f" | {failed} |")
    lines.extend(["", "详见 summary.json、各 fold 的 selection.json/model.json 和三种成本报告。",
                  "未通过时保留失败记录，停止模型升级；门槛和成本不降低。",
                  "INSUFFICIENT_DATA 表示无法形成有效检验；INVALID_RUN 表示技术或数据合同异常。",
                  "技术修复须保持协议、配置、锁定数据相同，并记录显式恢复原因；完成结果不重跑。",
                  "HOLDOUT_REQUIRED 仅表示开发集通过，须冻结一项策略后单次揭晓留出。",
                  "置信区间为配对日度收益差的 7 日区块自助法，不能保证未来盈利。", ""])
    path.write_text("\n".join(lines))
