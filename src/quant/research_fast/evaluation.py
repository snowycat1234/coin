"""FR70 shared prediction statistics and conditional trade-price research accounting.

SciPy owns IC/rank statistics; quant.metrics owns daily Sharpe/MDD. This adapter
never submits orders. Future-valid dataset endpoints imply a CONDITIONAL replay,
not an implementable strategy, even though accounting itself respects chronology.
"""

from __future__ import annotations

import hashlib
import heapq
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping, Sequence

import numpy as np
import polars as pl
from scipy.stats import pearsonr, spearmanr

from quant.metrics import daily_metrics

from .dataset import DAY_US, LOCKED, PAST_BARS, START, Fold, day_us, make_folds, protocol
from .labels import BAR_US, LABEL_COLUMNS, LABEL_LAG_US, TARGET_STREAMS, label_table

CONDITIONAL = "CONDITIONAL_FUTURE_VALID_ENDPOINT_TRADE_PRICE_PROXY"
METRICS = ("flow_IC", "return_Pearson_IC", "return_Spearman_IC", "RV_rank_IC")


def sample_id(dataset_sha256: str, decision_us: int) -> str:
    """Identical canonical ID to FR64; never align by positional truncation."""
    value = json.dumps((dataset_sha256, int(decision_us)), separators=(",", ":"))
    return hashlib.sha256(value.encode()).hexdigest()


def _array(value, dtype, shape=None):
    result = np.array(value, dtype=dtype, copy=True)
    if shape is not None and result.shape != shape:
        raise ValueError(f"Wrong common array shape: expected {shape}")
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite common evaluation data")
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class ObservedPrices:
    """Closed-bar close prices, with bar availability rather than future trade time."""

    available_us: np.ndarray
    close: np.ndarray

    def __post_init__(self):
        times = _array(self.available_us, np.int64)
        prices = _array(self.close, np.float64, times.shape)
        if times.ndim != 1 or (np.diff(times) <= 0).any() or (prices <= 0).any():
            raise ValueError("Observed prices require strictly ordered positive observations")
        object.__setattr__(self, "available_us", times)
        object.__setattr__(self, "close", prices)

    def asof(self, timestamp: int):
        index = int(np.searchsorted(self.available_us, timestamp, side="right")) - 1
        return None if index < 0 else (int(self.available_us[index]), float(self.close[index]))


@dataclass(frozen=True)
class EvaluationBatch:
    """One frozen truth/QA/valuation batch shared by every configuration in a fold."""

    dataset_sha256: str
    fold_name: str
    start_us: int
    end_us: int
    sample_ids: tuple[str, ...]
    decision_us: np.ndarray
    truth: np.ndarray
    entry_us: np.ndarray
    exit_us: np.ndarray
    entry_price: np.ndarray
    exit_price: np.ndarray
    label_available_us: np.ndarray
    observed: tuple[ObservedPrices, ObservedPrices]
    status: str = "SMOKE_ONLY"

    def __post_init__(self):
        if (
            len(self.dataset_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.dataset_sha256)
            or not day_us(START) <= self.start_us < self.end_us <= day_us(LOCKED)
            or self.status not in {"SMOKE_ONLY", "FORMAL_DATA_READY"}
        ):
            raise ValueError("Require a bound development dataset/fold, never locked history")
        decisions = _array(self.decision_us, np.int64)
        n = len(decisions)
        if decisions.ndim != 1 or not n or (np.diff(decisions) <= 0).any():
            raise ValueError("Nonempty strictly chronological common endpoints required")
        expected = tuple(sample_id(self.dataset_sha256, t) for t in decisions)
        if tuple(self.sample_ids) != expected:
            raise ValueError("Sample ID/time/dataset binding mismatch")
        object.__setattr__(self, "sample_ids", expected)
        object.__setattr__(self, "decision_us", decisions)
        for field, dtype, shape in (
            # Match FR64 y_raw values exactly before float64 statistical arithmetic.
            ("truth", np.float32, (n, 2, 4)),
            ("entry_us", np.int64, (n, 2)),
            ("exit_us", np.int64, (n, 2)),
            ("entry_price", np.float64, (n, 2)),
            ("exit_price", np.float64, (n, 2)),
            ("label_available_us", np.int64, (n,)),
        ):
            object.__setattr__(self, field, _array(getattr(self, field), dtype, shape))
        if (
            (decisions < self.start_us).any()
            or (self.label_available_us != decisions + LABEL_LAG_US).any()
            or (self.label_available_us > self.end_us).any()
            or (self.entry_price <= 0).any()
            or (self.exit_price <= 0).any()
            or (self.entry_us < decisions[:, None] + BAR_US).any()
            or (self.entry_us > decisions[:, None] + BAR_US + 2_000_000).any()
            or (self.exit_us < decisions[:, None] + 305_000_000).any()
            or (self.exit_us > decisions[:, None] + 307_000_000).any()
            or len(self.observed) != 2
            or any((prices.available_us > self.end_us).any() for prices in self.observed)
            or not np.allclose(
                self.truth[:, :, 1], self.exit_price / self.entry_price - 1,
                rtol=1e-5, atol=1e-7,
            )
        ):
            raise ValueError("Invalid common label/QA maturity or trade-price proxy binding")

    @property
    def fingerprint(self):
        digest = hashlib.sha256()
        digest.update(json.dumps(
            [self.dataset_sha256, self.fold_name, self.start_us, self.end_us, self.status,
             self.sample_ids], separators=(",", ":"),
        ).encode())
        for values in (
            self.decision_us, self.truth, self.entry_us, self.exit_us, self.entry_price,
            self.exit_price, self.label_available_us,
            *(x for price in self.observed for x in (price.available_us, price.close)),
        ):
            digest.update(values.tobytes())
        return digest.hexdigest()

    @classmethod
    def from_dataset(cls, dataset, indices, *, fold: Fold):
        """Read daily bounded joint blocks; no windows or future price imputations.

        Exact full shared test indices are mandatory. Valuation history is independent
        of future-valid endpoint selection, and only closed observations can mark NAV.
        """
        indices = np.asarray(indices)
        expected = dataset.split_indices(fold, "test")
        if not np.array_equal(indices, expected) or not len(expected):
            raise ValueError("Require the exact complete common test indices")
        decisions = np.asarray(dataset.index[expected], dtype=np.int64)
        truth, entry_us, exit_us, entries, exits, maturity = [], [], [], [], [], []
        observations = [[] for _ in TARGET_STREAMS]
        history_start = max(day_us(START), fold.test_start_us - PAST_BARS * BAR_US)
        for day in range(history_start // DAY_US, (fold.test_end_us - 1) // DAY_US + 1):
            lower, upper = max(history_start, day * DAY_US), min(
                fold.test_end_us, (day + 1) * DAY_US
            )
            joint = dataset.joint_rows(lower, upper)
            for s, stream in enumerate(TARGET_STREAMS):
                closed = joint.select(
                    pl.col(f"{stream}__available_us").alias("available_us"),
                    pl.col(f"{stream}__close").alias("close"),
                ).filter(pl.col("close").is_not_null())
                observations[s].append(closed)
            selected = decisions[(decisions >= lower) & (decisions < upper)]
            if not len(selected):
                continue
            label_rows = label_table(dataset.joint_rows(
                int(selected[0]) - BAR_US, int(selected[-1]) + LABEL_LAG_US
            )).filter(pl.col("decision_us").is_in(selected.tolist()))
            if (
                label_rows.height != len(selected)
                or not label_rows["label_valid"].all()
                or not np.array_equal(label_rows["decision_us"].to_numpy(), selected)
            ):
                raise ValueError("Frozen common test labels changed")
            truth.append(label_rows.select(LABEL_COLUMNS).to_numpy().reshape(-1, 2, 4))
            maturity.extend(label_rows["label_available_us"].to_list())
            for field, destination in (
                ("entry_trade_us", entry_us), ("exit_trade_us", exit_us),
                ("entry_price_proxy", entries), ("exit_price_proxy", exits),
            ):
                destination.extend(label_rows.select(
                    [f"{stream}__{field}" for stream in TARGET_STREAMS]
                ).rows())
        observed = []
        for pieces in observations:
            frame = pl.concat(pieces)
            observed.append(ObservedPrices(frame["available_us"].to_numpy(),
                                           frame["close"].to_numpy()))
        return cls(
            dataset.contract_sha256, fold.name, fold.test_start_us, fold.test_end_us,
            tuple(sample_id(dataset.contract_sha256, t) for t in decisions), decisions,
            np.concatenate(truth), entry_us, exit_us, entries, exits, maturity,
            tuple(observed), "FORMAL_DATA_READY" if dataset.mode == "formal" else "SMOKE_ONLY",
        )


def original_predictions(batch, values, sample_ids, *, units="original", normalizer=None):
    if tuple(sample_ids) != batch.sample_ids:
        raise ValueError("Prediction sample IDs must exactly match the shared batch in order")
    prediction = _array(values, np.float64, batch.truth.shape)
    if units == "standardized":
        if (
            normalizer is None or normalizer.dataset_sha256 != batch.dataset_sha256
            or normalizer.fold_name != batch.fold_name
            or normalizer.fit_last_label_available_us >= batch.start_us
        ):
            raise ValueError("Require the common frozen fitting-only target normalizer")
        prediction = _array(normalizer.inverse_transform(prediction), np.float64, batch.truth.shape)
    elif units != "original":
        raise ValueError("Explicit original or standardized prediction units required")
    return prediction


def _ic(predicted, truth, *, rank=False):
    # Undefined constant/short IC remains null; no model can silently drop rows.
    if len(truth) < 3 or np.ptp(truth) == 0 or np.ptp(predicted) == 0:
        return None
    value = (spearmanr if rank else pearsonr)(predicted, truth).statistic
    return float(value) if np.isfinite(value) else None


def prediction_metrics(batch, prediction):
    prediction = _array(prediction, np.float64, batch.truth.shape)
    result = {}
    for s, stream in enumerate(TARGET_STREAMS):
        truth, pred = batch.truth[:, s].astype(np.float64), prediction[:, s]
        result[stream] = {
            "samples": len(truth),
            "flow_IC": _ic(pred[:, 0], truth[:, 0]),
            "flow_sign_accuracy": float(np.mean(np.sign(pred[:, 0]) == np.sign(truth[:, 0]))),
            "return_Pearson_IC": _ic(pred[:, 1], truth[:, 1]),
            "return_Spearman_IC": _ic(pred[:, 1], truth[:, 1], rank=True),
            "RV_rank_IC": _ic(pred[:, 3], truth[:, 3], rank=True),
            "flow_30s_IC": _ic(pred[:, 2], truth[:, 2]),
        }
    return result


@dataclass(frozen=True)
class EconomicsResult:
    daily_nav: pl.DataFrame
    trades: pl.DataFrame
    summary: dict


def economics(batch, prediction, *, assumed_spread_bps=2, initial_cash=10_000.0):
    """Fixed return-only long/flat policy with identical quantities in cost identity.

    At decision, fix the quote-notional budget from observed NAV and reserve costs.
    At the historical entry event it may only shrink for available-price risk/cash.
    Costs are separately charged on reference notionals (not embedded twice in price).
    """
    if assumed_spread_bps not in (2, 4, 8) or not np.isfinite(initial_cash) or initial_cash <= 0:
        raise ValueError("Require fixed 2/4/8bp spread scenarios and positive initial cash")
    prediction = _array(prediction, np.float64, batch.truth.shape)
    fee_rate, execution_rate = .001, (8 + assumed_spread_bps) / 20_000
    cost_rate = fee_rate + execution_rate
    queue = [(int(t), 2, i, -1) for i, t in enumerate(batch.decision_us)]
    boundaries = [min((day + 1) * DAY_US, batch.end_us)
                  for day in range(batch.start_us // DAY_US, (batch.end_us - 1) // DAY_US + 1)]
    queue.extend((t, 0, -1, -1) for t in boundaries)
    heapq.heapify(queue)
    cash, quantity, reserved = initial_cash, np.zeros(2), {}
    last_fill_mark = [None, None]
    daily, trades = [], []
    fees = costs = notional_day = total_cost = gross_pnl = 0.0
    previous_nav = initial_cash
    overlaps = missing_marks = risk_blocks = 0
    max_weight = max_gross = 0.0

    def observations_at(timestamp):
        marks = []
        for s in range(2):
            available = batch.observed[s].asof(timestamp)
            fill = last_fill_mark[s]
            if fill is not None and (available is None or fill[0] > available[0]):
                available = fill
            marks.append(available)
        return marks

    def valuation(timestamp):
        prices = [None if mark is None else mark[1] for mark in observations_at(timestamp)]
        if any(q > 0 and p is None for q, p in zip(quantity, prices, strict=True)):
            raise ValueError("Missing observed valuation for an open position")
        values = np.array([q * p if p is not None else 0.0
                           for q, p in zip(quantity, prices, strict=True)])
        return cash + values.sum(), values, prices

    while queue:
        timestamp, kind, i, s = heapq.heappop(queue)
        nav, values, observed = valuation(timestamp)
        if kind == 0:  # Mark preceding UTC day before any boundary-time new-day activity.
            marks = observations_at(timestamp)
            daily.append({
                "date": datetime.fromtimestamp((timestamp - 1) / 1_000_000, UTC).date(),
                "valuation_us": timestamp, "nav": nav, "cash": cash,
                "fees": fees, "execution_costs": costs, "turnover": notional_day / previous_nav,
                "gross_pnl": nav - initial_cash + total_cost, "cumulative_cost": total_cost,
                "BTC_quantity": quantity[0], "ETH_quantity": quantity[1],
                "BTC_mark_available_us": None if marks[0] is None else marks[0][0],
                "ETH_mark_available_us": None if marks[1] is None else marks[1][0],
                "BTC_mark_price": None if marks[0] is None else marks[0][1],
                "ETH_mark_price": None if marks[1] is None else marks[1][1],
                "partial_day": timestamp == batch.end_us and timestamp % DAY_US != 0,
            })
            previous_nav, fees, costs, notional_day = nav, 0.0, 0.0, 0.0
        elif kind == 2:
            # Neither truth nor future entry/exit price participates in a signal/budget.
            for s in range(2):
                if prediction[i, s, 1] < .0035:
                    continue
                if quantity[s] > 0 or s in reserved:
                    overlaps += 1
                    continue
                if observed[s] is None:
                    missing_marks += 1
                    continue
                outstanding = sum(item["budget"] for item in reserved.values())
                budget = min(
                    .3 * nav / (1 + .6 * cost_rate),
                    max(0., .6 * nav - values.sum() - outstanding) / (1 + .6 * cost_rate),
                    max(0., cash - outstanding * (1 + cost_rate)) / (1 + cost_rate),
                )
                if budget <= 0:
                    risk_blocks += 1
                    continue
                reserved[s] = {"budget": budget, "decision_nav": nav,
                               "decision_price": observed[s]}
                heapq.heappush(queue, (int(batch.entry_us[i, s]), 3, i, s))
        else:
            price = float(batch.entry_price[i, s] if kind == 3 else batch.exit_price[i, s])
            last_fill_mark[s] = (timestamp, price)  # This event is now historically observed.
            nav, values, _ = valuation(timestamp)
            if kind == 3:
                intent = reserved[s]
                budget = min(
                    intent["budget"], cash / (1 + cost_rate),
                    max(0., .3 * nav - values[s]) / (1 + .3 * cost_rate),
                    max(0., .6 * nav - values.sum()) / (1 + .6 * cost_rate),
                    max(0., nav - values[1 - s] / .3) / cost_rate,
                )
                if budget <= 0:
                    risk_blocks += 1
                    del reserved[s]
                    continue
                quantity[s] = budget / price
                cash -= budget * (1 + cost_rate)
                reference_notional = budget
                heapq.heappush(queue, (int(batch.exit_us[i, s]), 1, i, s))
            else:
                intent = reserved.pop(s)
                reference_notional = quantity[s] * price
                gross_pnl += quantity[s] * (price - float(batch.entry_price[i, s]))
                cash += reference_notional * (1 - cost_rate)
            fee, extra = reference_notional * fee_rate, reference_notional * execution_rate
            fees, costs = fees + fee, costs + extra
            total_cost += fee + extra
            notional_day += reference_notional
            traded_quantity = quantity[s]
            if kind == 1:
                quantity[s] = 0.
            nav, values, _ = valuation(timestamp)
            trades.append({
                "sample_id": batch.sample_ids[i], "symbol": TARGET_STREAMS[s],
                "decision_us": int(batch.decision_us[i]), "event_us": timestamp,
                "side": "buy" if kind == 3 else "sell", "price_proxy": price,
                "quantity": traded_quantity, "reference_notional": reference_notional,
                "fee": fee, "execution_cost": extra, "cash_after": cash, "nav_after": nav,
                "decision_nav": intent["decision_nav"],
                "decision_observed_price": intent["decision_price"],
                "decision_quote_budget": intent["budget"],
                "gross_weight_after": float(values.sum() / nav),
                "symbol_weight_after": float(values[s] / nav),
            })
            if cash < -1e-8 or (kind == 3 and (
                values.max() > .3 * nav + 1e-7 or values.sum() > .6 * nav + 1e-7
            )):
                raise AssertionError("Causal allocation violates cash or post-cost buy caps")
        current_nav, current_values, _ = valuation(timestamp)
        max_weight = max(max_weight, float(current_values.max() / current_nav))
        max_gross = max(max_gross, float(current_values.sum() / current_nav))
    frame = pl.DataFrame(daily)
    summary = daily_metrics(frame, initial_cash)
    # Same traded quantities/cash flows: gross minus cost equals net exactly.
    summary.update({
        "basis": CONDITIONAL, "real_bbo": False, "implementable_strategy": False,
        "production_or_candidate_qualification": False,
        "gross_proxy_return": (summary["final_nav"] - initial_cash + total_cost) / initial_cash,
        "estimated_cost": total_cost / initial_cash,
        "net_proxy_return": summary["total_return"],
        "gross_pnl": gross_pnl, "cost": total_cost,
        "net_pnl": summary["final_nav"] - initial_cash,
        "roundtrip_fee_bps": 20, "roundtrip_extra_slippage_bps": 8,
        "roundtrip_assumed_spread_bps": assumed_spread_bps,
        "prediction_threshold_bps": 35, "trade_count": len(trades),
        "closed_roundtrips": len(trades) // 2,
        "overlap_signals_blocked": overlaps, "missing_observed_price_signals": missing_marks,
        "risk_blocks": risk_blocks, "max_observed_symbol_weight": max_weight,
        "max_observed_gross_weight": max_gross,
        "risk_caps_basis": "NEW_BUY_POST_COST_NAV; passive price drift reported separately",
        "drawdown_basis": "UTC_daily_observed_NAV; partial first/last day count as observations",
    })
    trade_schema = {
        "sample_id": pl.String, "symbol": pl.String, "decision_us": pl.Int64,
        "event_us": pl.Int64, "side": pl.String, "price_proxy": pl.Float64,
        "quantity": pl.Float64, "reference_notional": pl.Float64, "fee": pl.Float64,
        "execution_cost": pl.Float64, "cash_after": pl.Float64, "nav_after": pl.Float64,
        "decision_nav": pl.Float64, "decision_observed_price": pl.Float64,
        "decision_quote_budget": pl.Float64, "gross_weight_after": pl.Float64,
        "symbol_weight_after": pl.Float64,
    }
    return EconomicsResult(frame, pl.DataFrame(trades, schema=trade_schema), summary)


@dataclass(frozen=True)
class FoldEvaluation:
    metadata: dict
    metrics: dict
    economics: Mapping[int, EconomicsResult]

    def receipt(self):
        """Small JSON-compatible summaries; raw prediction/trade artifacts stay on D."""
        return {"metadata": self.metadata, "metrics": self.metrics,
                "economics": {str(spread): result.summary
                              for spread, result in self.economics.items()}}


def evaluate_fold(batch, values, sample_ids, *, units="original", normalizer=None, resources=None):
    prediction = original_predictions(batch, values, sample_ids, units=units, normalizer=normalizer)
    formal_fold = any(
        f.name == batch.fold_name and f.test_start_us == batch.start_us
        and f.test_end_us == batch.end_us for f in make_folds()
    )
    return FoldEvaluation(
        {"dataset_sha256": batch.dataset_sha256, "batch_sha256": batch.fingerprint,
         "fold": batch.fold_name, "samples": len(batch.sample_ids), "status": batch.status,
         "formal_fold": formal_fold, "prediction_units": "original",
         "prediction_sha256": hashlib.sha256(prediction.tobytes()).hexdigest(),
         "eligibility_basis": CONDITIONAL, "resources": resources or {},
         "production_or_candidate_qualification": False},
        prediction_metrics(batch, prediction),
        {spread: economics(batch, prediction, assumed_spread_bps=spread) for spread in (2, 4, 8)},
    )


def sprint_screen(folds: Sequence[FoldEvaluation]):
    """Equal-weight fold IC mean, positive fold fraction, positive IC concentration.

    Concentration is max positive fold IC / sum positive fold IC, never pooled
    samples or PnL. All six fixed complete OOS folds are required for a screen pass.
    """
    names = [f.metadata["fold"] for f in folds]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate OOS fold")
    if len({f.metadata["dataset_sha256"] for f in folds}) > 1:
        raise ValueError("All OOS folds must share one dataset contract")
    complete = set(names) == {f.name for f in make_folds()} and all(
        f.metadata["formal_fold"] and f.metadata["status"] == "FORMAL_DATA_READY"
        and f.metadata["samples"] >= 3 for f in folds
    )
    diagnostics = {}
    for stream in TARGET_STREAMS:
        diagnostics[stream] = {}
        for metric, threshold in (("flow_IC", .03), ("return_Spearman_IC", .02)):
            values = [f.metrics[stream][metric] for f in folds]
            defined = bool(values) and all(value is not None and np.isfinite(value)
                                           for value in values)
            mean = float(np.mean(values)) if defined else None
            positive = np.maximum(values, 0) if defined else np.array([])
            concentration = float(positive.max() / positive.sum()) if positive.sum() else None
            fraction = float(np.mean(np.asarray(values) > 0)) if defined else None
            passed = bool(complete and defined and mean >= threshold and fraction >= .6
                          and concentration is not None and concentration <= .6)
            diagnostics[stream][metric] = {
                "fold_values": values, "equal_fold_mean": mean, "positive_fold_fraction": fraction,
                "largest_positive_fold_IC_fraction": concentration, "threshold": threshold,
                "passed": passed,
            }
    passed = any(item["passed"] for tasks in diagnostics.values() for item in tasks.values())
    gross = np.array([f.economics[2].summary["gross_proxy_return"] for f in folds])
    net = np.array([f.economics[2].summary["net_proxy_return"] for f in folds])
    positive_gross = np.maximum(gross, 0)
    gross_concentration = (float(positive_gross.max() / positive_gross.sum())
                           if positive_gross.sum() else None)
    gross_fraction = float(np.mean(gross > 0)) if len(gross) else None
    stable_gross = bool(len(gross) and gross.mean() > 0 and gross_fraction >= .6
                        and gross_concentration is not None and gross_concentration <= .6)
    status = "INSUFFICIENT_EVIDENCE" if not complete else (
        "PREDICTIVE_BUT_COST_LIMITED" if passed and stable_gross and net.mean() < 0 else
        "SPRINT_SCREEN_PASS" if passed else "NO_SCREEN_SIGNAL"
    )
    return {"status": status, "passed": passed, "diagnostics": diagnostics,
            "economic_diagnostics": {"equal_fold_mean_gross": float(gross.mean()) if len(gross)
                                     else None, "equal_fold_mean_net": float(net.mean())
                                     if len(net) else None, "positive_gross_fold_fraction":
                                     gross_fraction, "largest_positive_gross_fold_fraction":
                                     gross_concentration, "stable_gross": stable_gross},
            "production_or_candidate_qualification": False, "economics_basis": CONDITIONAL}


def first_round_screen(models: Mapping[str, Sequence[FoldEvaluation]]):
    """No partial leaderboard; ten fixed configs share every fold truth/QA batch."""
    expected = {config["id"] for config in protocol()["configs"]}
    if set(models) - expected:
        raise ValueError("Unregistered first-round config")
    screens = {name: sprint_screen(folds) for name, folds in models.items()}
    bindings = {}
    for folds in models.values():
        for fold in folds:
            name, digest = fold.metadata["fold"], fold.metadata["batch_sha256"]
            if name in bindings and bindings[name] != digest:
                raise ValueError("All models must share identical sample IDs/truth/QA/valuation")
            bindings[name] = digest
    if set(models) != expected or any(s["status"] == "INSUFFICIENT_EVIDENCE"
                                      for s in screens.values()):
        return {"status": "INCOMPLETE_NO_LEADERBOARD", "screens": screens,
                "leaderboard": [], "top_directions": [],
                "production_or_candidate_qualification": False}
    rows = []
    directions = {
        "RIDGE-1": "RIDGE", "XGB-S": "XGB", "XGB-M": "XGB",
        "TCN-S": "TCN", "TCN-M": "TCN", "MLPLOB-1": "MLPLOB", "TLOB-1": "TLOB",
        "TS2VEC-LINEAR-1": "TS2Vec", "TS2VEC-LGB-1": "TS2Vec", "RIVER-1": "RIVER",
    }
    for name, screen in screens.items():
        score = max(
            (item["equal_fold_mean"] / item["threshold"] for tasks in screen["diagnostics"].values()
             for item in tasks.values() if item["passed"]), default=0.,
        )
        rows.append({"config": name, "direction": directions[name],
                     "screen": screen, "score": score,
                     "fold_metrics": [f.metrics for f in models[name]],
                     "fold_economics": [{spread: r.summary for spread, r in f.economics.items()}
                                        for f in models[name]],
                     "resources": [f.metadata["resources"] for f in models[name]]})
    rows.sort(key=lambda row: (-row["score"], row["config"]))
    top_directions = []
    for row in rows:
        if row["screen"]["passed"] and row["direction"] not in {
            item["direction"] for item in top_directions
        }:
            top_directions.append({"direction": row["direction"], "best_config": row["config"],
                                   "score": row["score"]})
        if len(top_directions) == 3:
            break
    return {"status": "SPRINT_SCREEN_ONLY", "leaderboard": rows,
            "top_directions": top_directions,
            "ranking_basis": "max passing equal-fold primary IC / preregistered threshold",
            "production_or_candidate_qualification": False, "economics_basis": CONDITIONAL}
