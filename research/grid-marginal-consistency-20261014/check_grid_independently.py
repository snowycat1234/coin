#!/usr/bin/env python3
"""Independent, offline arithmetic check. Uses no main-analysis imports.

Money is exact Fraction arithmetic from the published JSON number text.
Monthly deltas use differences of month-end spread levels; drawdown is an
exhaustive ordered peak/trough search. Correlation uses math.fsum raw moments
on daily simple returns independently derived from exact portfolio balances.
"""
import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

BASE = Path(__file__).resolve().parent
INITIAL = Fraction(10000)
TOL = Fraction("0.00000001")
CORR_TOL = 5e-15
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
DAY_US = 86400000000


def read_json(relative):
    return json.loads((BASE / relative).read_text(), parse_float=Fraction)


def number(value):
    return Fraction(value)


def decimal_text(value):
    value = Fraction(value)
    with localcontext() as ctx:
        ctx.prec = 100
        return format(Decimal(value.numerator) / Decimal(value.denominator), "f")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sign_counts(values):
    p = sum(v > 0 for v in values)
    n = sum(v < 0 for v in values)
    z = sum(v == 0 for v in values)
    return {"count": len(values), "positive": p, "negative": n, "zero": z,
            "positive_fraction_all": decimal_text(Fraction(p, len(values))),
            "positive_fraction_nonzero": decimal_text(Fraction(p, p + n)) if p + n else None}


def correlate(x, y):
    n = len(x)
    sx, sy = math.fsum(x), math.fsum(y)
    cov = n * math.fsum(a * b for a, b in zip(x, y)) - sx * sy
    vx = n * math.fsum(a * a for a in x) - sx * sx
    vy = n * math.fsum(b * b for b in y) - sy * sy
    check(vx > 0 and vy > 0, "Zero return variance")
    return cov / math.sqrt(vx * vy)


def main():
    catalog = read_json("SOURCE_CATALOG.json")
    check(number(catalog["initial_NAV_USDT"]) == INITIAL, "Catalog initial balance")
    sources = {s["id"]: s for s in catalog["sources"]}
    check(set(sources) == {f"{y}_{a}" for y in (2023, 2025) for a in ("cash", "grid")},
          "Unexpected input scope")
    recorded = {r["year"]: r for r in read_json("results/RESULTS.json")["years"]}
    monthly_csv = list(csv.DictReader((BASE / "results/MONTHLY_INCREMENT.csv").open()))
    verified_files, outcomes = [], []
    for year in (2023, 2025):
        daily, summaries = {}, {}
        nav = {arm: [INITIAL] for arm in ("cash", "grid")}
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        elapsed = start - EPOCH
        first_us = elapsed.days * DAY_US + elapsed.seconds * 1000000 + elapsed.microseconds
        expected_days = (date(year + 1, 1, 1) - date(year, 1, 1)).days
        check(expected_days == 365, "Year length outside scope")
        dates = [(date(year, 1, 1) + timedelta(days=i)).isoformat() for i in range(365)]
        residuals, inferred, terminal = {}, {}, {}
        for arm in ("cash", "grid"):
            src = sources[f"{year}_{arm}"]
            for field, hash_field in (("daily_file", "daily_sha256"),
                                      ("summary_financial_file", "summary_financial_sha256")):
                rel = src[field]
                check(not Path(rel).is_absolute() and ".." not in Path(rel).parts, "Input path")
                body = (BASE / rel).read_bytes()
                check(hashlib.sha256(body).hexdigest() == src[hash_field], "Public input checksum")
                if field == "daily_file":
                    check(hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
                          == src["daily_git_blob_sha"], "Public daily blob checksum")
                verified_files.append(rel)
            daily[arm] = read_json(src["daily_file"])
            s = summaries[arm] = read_json(src["summary_financial_file"])
            check(len(daily[arm]) == 365, "Daily count")
            for i, row in enumerate(daily[arm]):
                check(type(row["start_us"]) is int and type(row["end_us"]) is int, "Timestamp type")
                check(row["start_us"] == first_us + i * DAY_US and
                      row["end_us"] == first_us + (i + 1) * DAY_US, "UTC calendar coverage/order")
                check(row["completed"] is True and row["completion"] == "COMPLETE_CONDITIONAL_ACCOUNT"
                      and row["stop_us"] is None, "Daily completion")
                nav[arm].append(nav[arm][-1] + number(row["net_increment_USDT"]))
            check(all(v > 0 for v in nav[arm]), "Positive NAV denominators")
            check(s["complete_calendar"] is True and s["completed_minutes"] == 365 * 1440
                  and s["required_minutes"] == 365 * 1440, "Summary calendar coverage")
            check(s["completion"] == "COMPLETE_CONDITIONAL_ACCOUNT", "Summary completion")
            check(s["terminal_cash_realized"] is True and number(s["unpaid_liability"]) == 0,
                  "Paid terminal accounting")
            inferred[arm] = number(s["paid_NAV_decimal"]) - number(s["decimal_strings"]["net_PnL"])
            check(abs(inferred[arm] - INITIAL) <= TOL, "Inferred starting capital")
            check(number(s["decimal_strings"]["NAV"]) == number(s["paid_NAV_decimal"]), "Summary NAV agreement")
            residuals[arm] = nav[arm][-1] - number(s["paid_NAV_decimal"])
            check(abs(residuals[arm]) <= TOL, "Reconstructed terminal balance")
            terminal[arm] = nav[arm][-1]
        check(summaries["cash"]["cost_scenario"] == summaries["grid"]["cost_scenario"], "Paired cost scenario")
        levels = [g - c for c, g in zip(nav["cash"], nav["grid"])]
        labels = ["INITIAL_ZERO"] + dates
        increments = [b - a for a, b in zip(levels, levels[1:])]
        months, last = [], 0
        for m in range(1, 13):
            boundary = (date(year + 1, 1, 1) if m == 12 else date(year, m + 1, 1))
            end = (boundary - date(year, 1, 1)).days
            months.append({"month": f"{year}-{m:02}", "days": end - last,
                           "cash_increment_USDT": decimal_text(nav["cash"][end] - nav["cash"][last]),
                           "grid_increment_USDT": decimal_text(nav["grid"][end] - nav["grid"][last]),
                           "paired_increment_USDT": decimal_text(levels[end] - levels[last])})
            last = end
        monthly_deltas = [number(m["paired_increment_USDT"]) for m in months]
        check(sum(monthly_deltas) == sum(increments) == levels[-1], "Exact telescoping")
        # Independent exhaustive search, earliest trough then earliest peak on ties.
        drawdown, peak_i, trough_i = Fraction(0), 0, 0
        for j in range(1, len(levels)):
            for i in range(j):
                candidate = levels[i] - levels[j]
                if candidate > drawdown:
                    drawdown, peak_i, trough_i = candidate, i, j
        low_i = min(range(len(levels)), key=levels.__getitem__)
        high_i = max(range(len(levels)), key=levels.__getitem__)
        path = {"final_difference_USDT": decimal_text(levels[-1]),
                "minimum_difference_USDT": decimal_text(levels[low_i]), "minimum_date": labels[low_i],
                "maximum_difference_USDT": decimal_text(levels[high_i]), "maximum_date": labels[high_i],
                "maximum_drawdown_USDT": decimal_text(drawdown), "drawdown_peak_date": labels[peak_i],
                "drawdown_trough_date": labels[trough_i],
                "drawdown_peak_difference_USDT": decimal_text(levels[peak_i]),
                "drawdown_trough_difference_USDT": decimal_text(levels[trough_i])}
        best_i = max(range(12), key=monthly_deltas.__getitem__)
        sensitivity = {"month": months[best_i]["month"],
                       "removed_contribution_USDT": decimal_text(monthly_deltas[best_i]),
                       "remaining_dollar_contribution_USDT": decimal_text(levels[-1] - monthly_deltas[best_i])}
        returns = {a: [float(end / begin - 1) for begin, end in zip(nav[a], nav[a][1:])]
                   for a in ("cash", "grid")}
        correlation = correlate(returns["cash"], returns["grid"])
        day_signs, month_signs = sign_counts(increments), sign_counts(monthly_deltas)
        r = recorded[year]
        check(number(r["annual_increment_USDT"]) == levels[-1], "Reported annual delta")
        summary_delta = number(summaries["grid"]["paid_NAV_decimal"]) - number(summaries["cash"]["paid_NAV_decimal"])
        check(number(r["summary_terminal_increment_USDT"]) == summary_delta, "Reported summary delta")
        for actual, expected in ((path, r["difference_path"]), (sensitivity, r["remove_best_month_sensitivity"])):
            for k, v in actual.items():
                check(number(v) == number(expected[k]) if k.endswith("USDT") else v == expected[k], k)
        for actual, expected in ((day_signs, r["daily_increment_signs"]), (month_signs, r["monthly_increment_signs"])):
            for k, v in actual.items():
                check(abs(number(v) - number(expected[k])) < Fraction(1, 10**58)
                      if k.startswith("positive_fraction") else v == expected[k], "Reported signs/fractions")
        for actual, expected in zip(months, r["months"]):
            for k, v in actual.items():
                check(number(v) == number(expected[k]) if k.endswith("USDT") else v == expected[k], "Reported month")
        yearly_csv = [m for m in monthly_csv if m["month"].startswith(str(year))]
        check(len(yearly_csv) == len(r["months"]) == 12, "Monthly output count")
        for actual, expected in zip(months, yearly_csv):
            for k, v in actual.items():
                check(str(v) == expected[k] if k == "month" else number(v) == number(expected[k]), "Monthly CSV")
        daily_csv = list(csv.DictReader((BASE / f"results/{year}_PAIRED_DAILY.csv").open()))
        check(len(daily_csv) == 365, "Daily output count")
        for i, row in enumerate(daily_csv):
            check(row["date"] == dates[i], "Daily output date")
            for a in ("cash", "grid"):
                check(number(row[f"{a}_increment_USDT"]) == nav[a][i + 1] - nav[a][i], "Daily increment")
                check(number(row[f"{a}_NAV_USDT"]) == nav[a][i + 1], "Daily NAV")
                check(abs(number(row[f"{a}_simple_return"]) - (nav[a][i + 1] / nav[a][i] - 1))
                      < Fraction(1, 10**58), "Daily simple return")
            check(number(row["paired_increment_USDT"]) == increments[i], "Daily paired increment")
            check(number(row["cumulative_difference_USDT"]) == levels[i + 1], "Daily spread level")
        corr_difference = abs(correlation - float(r["lag_zero_daily_simple_return_correlation"]))
        check(corr_difference <= CORR_TOL, "Return correlation")
        outcomes.append({"year": year, "days": 365, "annual_increment_USDT": decimal_text(levels[-1]),
                         "summary_terminal_increment_USDT": decimal_text(summary_delta), "months": months,
                         "daily_increment_signs": day_signs, "monthly_increment_signs": month_signs,
                         "difference_path": path, "remove_best_month_sensitivity": sensitivity,
                         "lag_zero_daily_simple_return_correlation": correlation,
                         "correlation_absolute_difference_from_reported": corr_difference,
                         "inferred_initial_NAV_USDT": {k: decimal_text(v) for k, v in inferred.items()},
                         "reconstructed_terminal_NAV_USDT": {k: decimal_text(v) for k, v in terminal.items()},
                         "daily_minus_summary_terminal_NAV_USDT": {k: decimal_text(v) for k, v in residuals.items()},
                         "daily_sum_minus_summary_difference_USDT": decimal_text(levels[-1] - summary_delta),
                         "all_comparisons_passed": True})
    output = {"status": "PASS", "checker": "check_grid_independently.py",
              "method": "Independent exact rational dollar arithmetic; month-end boundary subtraction; exhaustive ordered drawdown; float raw-moment Pearson correlation using math.fsum.",
              "scope": "Only 2023 and 2025 public saved daily increments and allowlisted financial summaries, source catalog, predeclared plan, reproduction script and outputs.",
              "verified_input_files": verified_files, "compared_result_files": ["results/RESULTS.json", "results/MONTHLY_INCREMENT.csv", "results/2023_PAIRED_DAILY.csv", "results/2025_PAIRED_DAILY.csv"],
              "terminal_reconciliation_tolerance_USDT": decimal_text(TOL), "correlation_absolute_tolerance": CORR_TOL,
              "calendar_and_capital": "365 unique ordered complete UTC calendar days per arm per year; exact 10000 USDT inferred initial capital in every arm; day-one return denominator is 10000; initial zero included in spread extrema and drawdown.",
              "years": outcomes,
              "claim_assessment": {"supportable": ["Annual incremental contribution reverses sign between these two observed development years.", "Both years have seven positive and five negative months, with no exact-zero months; positive month counts alone do not imply positive annual contribution.", "Removing the best 2023 month leaves a positive 16.95977501688749963 USDT contribution; removing the best 2025 month leaves a negative 49.4580978634655691506 USDT contribution.", "The two whole-portfolio daily simple-return paths are highly correlated."],
                                   "not_established": ["Statistical noise, sampling confidence or future expected alpha.", "Independent funded spread returns, strict same-actual-risk dominance or future/live performance.", "The 2023 annual gain vanishes when its best month is removed.", "An implementable month-selection strategy from contribution subtraction."]}}
    (BASE / "INDEPENDENT_CHECK.json").write_text(json.dumps(output, indent=2) + "\n")
    for o in outcomes:
        print(o["year"], "PASS", "annual", o["annual_increment_USDT"], "positive/negative/zero days",
              o["daily_increment_signs"]["positive"], o["daily_increment_signs"]["negative"], o["daily_increment_signs"]["zero"],
              "spread drawdown", o["difference_path"]["maximum_drawdown_USDT"], "correlation", o["lag_zero_daily_simple_return_correlation"])


if __name__ == "__main__":
    main()
