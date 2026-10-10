"""Consume a reviewed official-source packet locally; never acquire data."""

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from modules.collector_research.pipeline.normalize import funding_windows
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import CORE5, DAY_US, array_digest, digest, require_sha

ROOT = Path(__file__).resolve().parents[2]
START, END = 1609459200000000, 1640995200000000
DELAY = 60000001
FIELDS = {
    "symbol_order",
    "decision_us",
    "execution_us",
    "funding_interval_start_us",
    "funding_interval_end_us",
    "prices",
    "funding_coeff",
}


@dataclass(frozen=True)
class EconomicPacket:
    decision_us: np.ndarray
    prices: np.ndarray
    funding_coeff: np.ndarray
    price_known: np.ndarray
    funding_known: np.ndarray
    receipt: dict

    def __post_init__(self):
        d = np.asarray(self.decision_us)
        n = len(d)
        if (
            d.dtype != np.int64
            or d.ndim != 1
            or n < 2
            or not np.array_equal(d, np.arange(int(d[0]), int(d[-1]) + DAY_US, DAY_US))
            or d[0] < START
            or d[-1] >= END
        ):
            raise ValueError("Consecutive real 2021 decision calendar required")
        for name, shape, mask_name in (
            ("prices", (n, 5), "price_known"),
            ("funding_coeff", (n - 1, 5), "funding_known"),
        ):
            a, mask = np.asarray(getattr(self, name)), np.asarray(getattr(self, mask_name))
            if (
                a.dtype != np.float64
                or a.shape != shape
                or mask.shape != shape
                or mask.dtype != bool
                or not np.isfinite(a[mask]).all()
                or not np.isnan(a[~mask]).all()
                or (name == "prices" and np.any(a[mask] <= 0))
            ):
                raise ValueError("Known real economics; unknown entries must remain NaN")
        for name in ("decision_us", "prices", "funding_coeff", "price_known", "funding_known"):
            a = np.array(getattr(self, name), copy=True)
            a.flags.writeable = False
            object.__setattr__(self, name, a)

    @property
    def identity(self):
        return digest(
            dict(
                receipt=self.receipt,
                **{
                    k: array_digest(getattr(self, k))
                    for k in (
                        "decision_us",
                        "prices",
                        "funding_coeff",
                        "price_known",
                        "funding_known",
                    )
                },
            )
        )


def load_packet(directory, *, source_commit, consumer_sha256):
    """Required index additions: completed acquisition and verified archive receipts.

    The caller supplies an immutable, reviewed commit and exact consumer hash.
    Gaps are allowed only as explicit NaN/mask entries, never filled values.
    Standard source task's five daily/event/interval tables are independently
    checked against prices and signed strictly-prior-mark funding coefficients.
    """
    directory = Path(directory).resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("Immutable source commit required")
    require_sha(consumer_sha256)
    if sha(directory / "CONSUMER_INDEX.json") != consumer_sha256:
        raise ValueError("Reviewed source consumer bytes required")
    index = json.loads((directory / "CONSUMER_INDEX.json").read_text())
    if (
        index.get("symbols_order") != list(CORE5)
        or index.get("source_download_complete") is not True
        or index.get("official_archive_receipts_verified") is not True
    ):
        raise ValueError("Complete source-bound acquisition and archive receipts required")
    sources = index.get("normalization_source_SHA256", {})
    if not sources:
        raise ValueError("Bound inherited economic normalization sources required")
    for name, expected in sources.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or sha(path) != expected:
            raise ValueError("Economic normalization source changed")
    expected = index.get("economic_SHA256", index.get("economic_array", {}).get("SHA256"))
    require_sha(expected)
    if index.get("economic_array", {}).get("SHA256", expected) != expected:
        raise ValueError("Conflicting source economic identities")
    if sha(directory / "ECONOMICS.npz") != expected:
        raise ValueError("Source-bound economic array bytes required")
    artifacts = index.get("economic_table_artifacts", [])
    names = set()
    for row in artifacts:
        path = (directory / row["path"]).resolve()
        if (
            not path.is_relative_to(directory)
            or row["path"] in names
            or path.stat().st_size != row["bytes"]
            or sha(path) != row["SHA256"]
        ):
            raise ValueError("Unique exact supplied economic table bytes required")
        names.add(row["path"])
    with np.load(directory / "ECONOMICS.npz", allow_pickle=False) as z:
        if set(z.files) not in (FIELDS, FIELDS | {"price_known", "funding_known"}):
            raise ValueError(
                "Named real economic clocks/values and optional explicit masks required"
            )
        a = {k: z[k].copy() for k in z.files}
    d = a["decision_us"]
    if tuple(a["symbol_order"]) != CORE5 or not np.array_equal(d, np.arange(START, END, DAY_US)):
        raise ValueError("Exactly 365 source calendar decisions in frozen CORE5 order required")
    for name, clocks in (
        ("execution_us", d + DELAY),
        ("funding_interval_start_us", d[:-1] + DELAY),
        ("funding_interval_end_us", d[1:] + DELAY),
    ):
        if a[name].dtype != np.int64 or not np.array_equal(a[name], clocks):
            raise ValueError("Actual 00:01 open execution and held interval clocks required")
    if "price_known" not in a:
        if index.get("execution_and_held_funding_ready") is not True:
            raise ValueError("Incomplete packets must retain explicit known masks")
        a["price_known"] = np.ones((365, 5), bool)
        a["funding_known"] = np.ones((364, 5), bool)
    receipt = dict(
        source_commit=source_commit,
        consumer_SHA256=consumer_sha256,
        economic_SHA256=expected,
        economic_artifacts=artifacts,
        normalization_sources=sources,
        execution="actual_trade_1m_OPEN_00:01;available_00:01:00.000001UTC",
        funding="-quantity*sum(signed_rate*actual_strict_prior_mark);(start,end]",
        provider_downloads=0,
        synthetic_economic_rows=0,
    )
    packet = EconomicPacket(
        d, a["prices"], a["funding_coeff"], a["price_known"], a["funding_known"], receipt
    )
    errors = {}
    for j, symbol in enumerate(CORE5):
        prefix = "normalized/data/normalized/" + symbol
        required = (
            prefix + "_daily.parquet",
            prefix + "_funding_events.parquet",
            "normalized/economics/" + symbol + "_funding_intervals.parquet",
        )
        if not set(required).issubset(names):
            raise ValueError("Bound daily/event/held-interval tables required for every asset")
        daily, events, intervals = [
            pq.read_table(directory / name).to_pandas() for name in required
        ]
        if (
            not np.array_equal(pd.DatetimeIndex(daily.dt).as_unit("us").asi8, d)
            or len(intervals) != 364
        ):
            raise ValueError("Real source daily and interval calendars required")
        known = packet.price_known[:, j]
        np.testing.assert_array_equal(daily.exec_price.to_numpy(float), packet.prices[:, j])
        if not (
            daily.complete_kline.to_numpy(bool)[known]
            & (daily.unique_minutes.to_numpy(int)[known] == 1440)
        ).all():
            raise ValueError("Observed execution days require complete actual minute bars")
        np.testing.assert_array_equal(
            intervals.funding_interval_complete.to_numpy(bool), packet.funding_known[:, j]
        )
        np.testing.assert_array_equal(
            intervals.mark_funding_per_unit.to_numpy(float), packet.funding_coeff[:, j]
        )
        times = events.calc_time_ms.to_numpy(np.int64) * 1000
        marks = events.past_mark_price.to_numpy(float)
        available = events.past_mark_available_us.to_numpy(np.int64)
        rates = events.last_funding_rate.to_numpy(float)
        if np.any(np.diff(times) <= 0):
            raise ValueError("Unique chronological funding events required")
        actual_intervals = funding_windows(events, pd.to_datetime(d[:-1], unit="us", utc=True))
        if not np.array_equal(
            actual_intervals.funding_interval_complete.to_numpy(bool), packet.funding_known[:, j]
        ):
            raise ValueError(
                "Original both-sided funding coverage must match source-known intervals"
            )
        np.testing.assert_allclose(
            actual_intervals.mark_funding_per_unit.to_numpy(float),
            packet.funding_coeff[:, j],
            rtol=2e-15,
            atol=1e-10,
            equal_nan=True,
        )
        differences = []
        for i in np.flatnonzero(packet.funding_known[:, j]):
            selected = (times > d[i] + DELAY) & (times <= d[i + 1] + DELAY)
            if selected.sum() != 3:
                raise ValueError("Three real held funding events per known daily interval required")
            if (
                not np.isfinite(rates[selected]).all()
                or not np.isfinite(marks[selected]).all()
                or np.any(marks[selected] <= 0)
                or not np.array_equal(
                    available[selected], (times[selected] - 1) // 60000000 * 60000000
                )
            ):
                raise ValueError(
                    "Known funding intervals require actual strictly-prior event marks"
                )
            actual = math.fsum(
                float(r) * float(m) for r, m in zip(rates[selected], marks[selected], strict=True)
            )
            np.testing.assert_allclose(actual, packet.funding_coeff[i, j], rtol=2e-15, atol=1e-10)
            differences.append(abs(actual - packet.funding_coeff[i, j]))
        errors[symbol] = max(differences, default=0.0)
    return EconomicPacket(
        packet.decision_us,
        packet.prices,
        packet.funding_coeff,
        packet.price_known,
        packet.funding_known,
        dict(receipt, independent_funding_max_error=errors),
    )
