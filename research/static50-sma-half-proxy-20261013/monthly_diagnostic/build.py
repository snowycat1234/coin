#!/usr/bin/env python3
"""Read-only calendar-month decomposition of four saved daily wallet traces.

No target construction, wallet scoring, resampling, hypothesis selection, or data fetch.
Writes only into this monthly_diagnostic directory, never into frozen results.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
EXPECTED = {
    "Y2023_STATIC50_ROWS.json": "ecc6257a2632d5870de6ff9bab749a294da4956ef8ce25280840491a500f7703",
    "Y2023_SMA200_ROWS.json": "292bea56c1101ba17a9d45866a8857095e7f78415fc1821fec7d3b2501256812",
    "Y2025_STATIC50_ROWS.json": "5d3974dd871079acb363acfd0d082c9a6f43328e08b44706db98618f13adcc61",
    "Y2025_SMA200_ROWS.json": "bc740ae1acbcd6bdbc6834af9966f867144b8a9816a11661a765bec497381b0b",
}


def get_rows(name: str) -> list[dict]:
    raw = (RESULTS / name).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == EXPECTED[name], (name, digest)
    rows = json.loads(raw)
    assert len(rows) == 365, name
    for i, row in enumerate(rows):
        day = dt.datetime.fromtimestamp(row["decision_us"] / 1_000_000, dt.timezone.utc)
        assert day == dt.datetime(int(name[1:5]), 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(days=i)
        assert row["nav_before"] > 0 and row["nav_after"] > 0
        if i:
            assert abs(row["nav_before"] - rows[i-1]["nav_after"]) < 1e-7
    return rows


def month_returns(rows: list[dict]) -> dict[str, dict]:
    by_month: dict[str, list[dict]] = {}
    for row in rows:
        # Attribute the 24-hour held interval to its decision/start UTC month.
        stamp = dt.datetime.fromtimestamp(row["decision_us"] / 1_000_000, dt.timezone.utc)
        by_month.setdefault(stamp.strftime("%Y-%m"), []).append(row)
    assert len(by_month) == 12
    return {
        month: {
            "decision_days": len(segment),
            "start_NAV_USDT": segment[0]["nav_before"],
            "end_NAV_USDT": segment[-1]["nav_after"],
            "within_wallet_return": segment[-1]["nav_after"] / segment[0]["nav_before"] - 1,
        }
        for month, segment in by_month.items()
    }


def main() -> None:
    summary = json.loads((RESULTS / "RESULTS.json").read_text())
    tables = {}
    for year in (2023, 2025):
        arms = {}
        for arm in ("STATIC50", "SMA200"):
            name = f"Y{year}_{arm}_ROWS.json"
            assert summary["years"][str(year)]["arms"][arm]["quantity_rows_SHA256"] == EXPECTED[name]
            rows = get_rows(name)
            assert abs(rows[-1]["nav_after"] - summary["years"][str(year)]["arms"][arm]["metrics"]["marked_NAV"]) < 1e-7
            arms[arm] = month_returns(rows)
        for month in arms["STATIC50"]:
            cs = arms["STATIC50"][month]
            sma = arms["SMA200"][month]
            assert cs["decision_days"] == sma["decision_days"]
            tables[month] = {
                "decision_days": cs["decision_days"],
                "CS_HOLD_within_wallet_return": cs["within_wallet_return"],
                "SMA200_within_wallet_return": sma["within_wallet_return"],
                "SMA_minus_CS_HOLD_percentage_points": 100 * (sma["within_wallet_return"] - cs["within_wallet_return"]),
                "both_negative": cs["within_wallet_return"] < 0 and sma["within_wallet_return"] < 0,
            }
    assert len(tables) == 24
    both = [m for m, row in tables.items() if row["both_negative"]]
    ahead = sorted(tables, key=lambda m: tables[m]["SMA_minus_CS_HOLD_percentage_points"], reverse=True)
    output = {
        "status": "DESCRIPTIVE_READ_ONLY_SAVED_TRACE_DECOMPOSITION",
        "source_experiment": "static50-sma-half-proxy-20261013",
        "source_published_commit": "b9b31228143530e6904b08e9937525b36663e309",
        "source_trace_SHA256": EXPECTED,
        "period_assignment": "UTC decision/start month of each 24-hour held interval; final next-January-1 paid exit assigned to December",
        "formula": "last daily nav_after / first daily nav_before - 1 within each month of an ongoing annual wallet",
        "warnings": [
            "Not standalone monthly strategy returns or independent monthly wallets",
            "Month-wise largest difference is selected after observing results; no significance test, p-value, or confidence interval",
            "Only the available full 2023 and 2025 same-horizon daily-proxy years; no 2024 annual result or 2021/2022 annual comparison",
            "Conditional historical quantity proxy, not native account execution or future returns",
        ],
        "months": tables,
        "summary": {
            "months_total": 24,
            "both_negative_count": len(both),
            "both_negative_months": both,
            "SMA_ahead_months_sorted_by_difference": [m for m in ahead if tables[m]["SMA_minus_CS_HOLD_percentage_points"] > 0],
        },
    }
    (HERE / "MONTHLY_RESULTS.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    lines = [
        "# CS+HOLD versus SMA200: saved-trace monthly diagnostic",
        "",
        "This is a descriptive decomposition of the existing full-year 2023 and 2025 same-horizon daily-quantity-proxy wallets. It reads the four frozen original row traces and RESULTS.json, verifies the trace SHA-256 hashes, and does not rerun targets, wallet economics or random inference. The script writes only to this directory.",
        "",
        "Each 24-hour held interval is assigned to the UTC month of its decision/start timestamp. A month return is its last saved daily NAV after divided by its first saved daily NAV before, minus one. December includes the saved paid exit at the next January 1 boundary. These are adjacent portions of ongoing annual wallets, not independent monthly start/stop backtests.",
        "",
        "| Month (UTC decision) | CS+HOLD | SMA200 | SMA−CS+HOLD | Both lost? |",
        "|---|---:|---:|---:|:---:|",
    ]
    for month, row in tables.items():
        lines.append(f"| {month} | {row['CS_HOLD_within_wallet_return']:+.3%} | {row['SMA200_within_wallet_return']:+.3%} | {row['SMA_minus_CS_HOLD_percentage_points']:+.3f} pp | {'Yes' if row['both_negative'] else ''} |")
    lines += [
        "",
        f"Both negative: {len(both)} of 24 months ({', '.join(both)}).",
        f"Largest observed SMA lead: {ahead[0]}, +{tables[ahead[0]]['SMA_minus_CS_HOLD_percentage_points']:.3f} percentage points. This is an after-the-fact maximum, not a prespecified hypothesis or a statistically significant result.",
        "",
        "No verified complete calendar year in this saved same-horizon comparison shows SMA outperforming CS+HOLD or both strategies losing. A separate 2024 SMA-versus-plain-CS observation must not be described as SMA-versus-CS+HOLD; full-year 2024 CS+HOLD comparison is unavailable here. No 2021/2022 full-year comparison or protected 2026 holdout was used.",
        "",
        "Source: https://github.com/snowycat1234/coin/blob/b9b31228143530e6904b08e9937525b36663e309/research/static50-sma-half-proxy-20261013/REPORT.md",
        "The exact source trace SHA-256 values are in MONTHLY_RESULTS.json. This diagnostic introduces no selection rule or future trading recommendation.",
        "",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
