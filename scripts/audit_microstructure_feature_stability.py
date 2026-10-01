"""Descriptive A07 QA on the frozen auditor's exact usable paired seconds."""

from __future__ import annotations

import argparse
import importlib.util
import math
import resource
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from quant.paths import ROOT

SPEC = importlib.util.spec_from_file_location(
    "a07_stability_isolated_quality", ROOT / "scripts/audit_microstructure_quality.py"
)
qa = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qa
SPEC.loader.exec_module(qa)

NONNEGATIVE = {
    "spread_bps", "bid_qty_mean", "ask_qty_mean", "aggressive_buy_notional",
    "aggressive_sell_notional", "quote_update_count", "bid_price_change_count",
    "ask_price_change_count", "agg_trade_count",
}
IMBALANCES = {"L1_imbalance_mean", "L1_imbalance_last", "trade_flow_imbalance"}


@dataclass
class Moment:
    """Constant-memory Welford moments; legal nulls are counted separately."""

    count: int = 0
    nulls: int = 0
    nonzero: int = 0
    mean: float = 0.0
    m2: float = 0.0
    total: float = 0.0
    minimum: float | None = None
    maximum: float | None = None

    def add(self, value):
        if value is None:
            self.nulls += 1
            return
        qa.require(isinstance(value, (float, int)) and not isinstance(value, bool)
                   and math.isfinite(value), "Nonfinite/nonnumeric descriptive feature")
        self.count += 1
        self.nonzero += value != 0
        delta = value - self.mean
        self.mean += delta / self.count
        self.m2 += delta * (value - self.mean)
        self.total += value
        qa.require(all(math.isfinite(x) for x in (self.mean, self.m2, self.total)),
                   "Descriptive moment overflow")
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)

    def report(self):
        return {"finite_count": self.count, "legal_null_count": self.nulls,
                "nonzero_count": self.nonzero, "sum_of_observed_values": self.total,
                "mean": self.mean if self.count else None,
                "population_std": math.sqrt(max(0, self.m2 / self.count)) if self.count else None,
                "min": self.minimum, "max": self.maximum}


@dataclass
class Hour:
    paired_seconds: int = 0
    moments: dict = field(default_factory=lambda: {name: Moment() for name in qa.FEATURES})
    alerts: dict = field(default_factory=dict)

    def add(self, row):
        self.paired_seconds += 1
        for name, moment in self.moments.items():
            value = row[name]
            moment.add(value)
            if value is None:
                continue
            invalid = (
                name in NONNEGATIVE and value < 0
                or name in {"mid", "trade_vwap"} and value <= 0
                or name in IMBALANCES and abs(value) > 1.00001
                or name.endswith("_count") and (type(value) is not int or value < 0)
            )
            if invalid:
                self.alerts[name] = self.alerts.get(name, 0) + 1
        for name in ("bid_price_change_count", "ask_price_change_count"):
            if row[name] > row["quote_update_count"]:
                key = name + "_exceeds_quote_updates"
                self.alerts[key] = self.alerts.get(key, 0) + 1

    def report(self):
        return {"paired_usable_seconds": self.paired_seconds, "range_alert_counts": self.alerts,
                "features": {name: value.report() for name, value in self.moments.items()}}


class FeatureCommonSeconds(qa.CommonSeconds):
    """Add observations after the unchanged parent has certified this exact pair."""

    def __init__(self, uncertain_ranges, limits):
        super().__init__(uncertain_ranges, limits)
        self.rows = {}
        self.hours = {}
        self.accepted_pairs = 0

    def add(self, row):
        super().add(row)
        self.rows[row["symbol"]] = row

    def flush(self):
        if self.opened is None or not self.pending:
            return
        day = self.opened // qa.DAY
        before = self.days.get(day, {}).get("usable_seconds", 0)
        super().flush()
        if self.days[day].get("usable_seconds", 0) > before:
            self.accepted_pairs += 1
            hour = self.opened // (3600 * qa.SECOND)
            for symbol, row in self.rows.items():
                key = (symbol, hour)
                qa.require(key in self.hours or len(self.hours) < 1440,
                           "720 two-symbol descriptive hour bound exceeded")
                if key not in self.hours:
                    self.hours[key] = Hour()
                self.hours[key].add(row)
        self.rows.clear()

    def descriptive_report(self):
        qa.require(self.accepted_pairs == self.report()["totals"].get("usable_seconds", 0),
                   "Descriptive pair counts differ from frozen quality accounting")
        return {
            "paired_usable_seconds": self.accepted_pairs,
            "hour_groups": {
                symbol + "/" + datetime.fromtimestamp(hour * 3600, UTC).isoformat(): stats.report()
                for (symbol, hour), stats in sorted(self.hours.items())
            },
            "range_alerts_present": any(stats.alerts for stats in self.hours.values()),
            "maximum_pending_feature_rows": 2,
            "maximum_hour_groups": 1440,
            "statistics": "Finite nonnull values only; population std via Welford. No quantiles "
                          "or full-row accumulation. Nulls remain explicitly missing, not zero.",
        }


def diagnose(*args, **kwargs):
    """Only this isolated analysis module observes the immutable auditor's consumer."""
    consumers = []
    original = qa.CommonSeconds

    def factory(*values):
        consumer = FeatureCommonSeconds(*values)
        consumers.append(consumer)
        return consumer

    qa.CommonSeconds = factory
    try:
        quality = qa.audit_quality(*args, **kwargs)
    finally:
        qa.CommonSeconds = original
    result = {"status": "FAIL_CLOSED", "created_at_utc": datetime.now(UTC).isoformat(),
              "read_only": True, "evidence_stage": "QA_ONLY", "training_authorized": False,
              "alpha_eligible": False, "actual_24h_capacity_accepted": False,
              "actual_24h_quality_accepted": False, "predictive_diagnostics_authorized": False,
              "source_hashes": {
                  "scripts/audit_microstructure_quality.py": qa.digest(Path(SPEC.origin)),
                  "scripts/audit_microstructure_feature_stability.py": qa.digest(Path(__file__)),
              }, "quality_snapshot": quality, "fits_executed": 0, "network_requests": 0,
              "limits": "Same frozen schema/hash/session/audit/uncertainty/short SQL snapshot "
                        "checks. Statistics only on exact paired usable seconds. At most 720 "
                        "hours, two retained feature rows and bounded streaming Arrow batches.",
              "interpretation": "Descriptive ranges and UTC hour distributions are short "
                                "data QA, not stable predictive signal or trading profitability. "
                                "Sums of means/states are numerical, not physical totals; "
                                "only count/notional/OFI fields are additive by their schema."}
    if quality.get("integrity") == "PASS" and len(consumers) == 1:
        result.update(status="DESCRIPTIVE_FEATURE_QA_ONLY",
                      descriptive=consumers[0].descriptive_report())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    accepted = qa.read_json(ROOT / "reports/A07_QUALITY_DIAGNOSTIC_ACCEPTANCE.json", 1_000_000)
    expected = accepted["source_hashes"]["scripts/audit_microstructure_quality.py"]
    qa.require(qa.digest(Path(SPEC.origin)) == expected, "Frozen quality auditor source changed")
    started_hash = qa.digest(Path(__file__))
    result = diagnose(limits=qa.Limits(max_days=30))
    qa.require(qa.digest(Path(SPEC.origin)) == expected
               and qa.digest(Path(__file__)) == started_hash,
               "Bound analysis source changed while scanning")
    result["process_max_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    result["prior_quality_acceptance_sha256"] = qa.digest(
        ROOT / "reports/A07_QUALITY_DIAGNOSTIC_ACCEPTANCE.json"
    )
    qa.save_report(result, args.output)
    print(qa.canonical({"status": result["status"], "report": str(args.output),
                        "paired_usable_seconds": result.get("descriptive", {}).get(
                            "paired_usable_seconds", 0),
                        "range_alerts_present": result.get("descriptive", {}).get(
                            "range_alerts_present"),
                        "process_max_rss_bytes": result["process_max_rss_bytes"]}).decode())
    if result["status"] == "FAIL_CLOSED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
