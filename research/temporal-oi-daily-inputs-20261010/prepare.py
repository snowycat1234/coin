"""Prepare fixed, input-only official OI calendar before any bulk network IO."""

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STATE = REPO.parent / "coin_single_state"
START, END = date(2021, 12, 1), date(2024, 4, 30)
ASSETS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
BASE = "https://data.binance.vision/data/futures/um/daily/metrics"


def main():
    previous = json.loads(
        (HERE.parent / "temporal-oi-feasibility-20261010/RAW_ARCHIVE_MANIFEST.json").read_text()
    )
    reuse = {}
    for row in previous:
        path = STATE / "oi-feasibility-retry/raw" / row["ZIP"]
        side = path.with_name(path.name + ".CHECKSUM")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["ZIP_SHA256"]
        assert hashlib.sha256(side.read_bytes()).hexdigest() == row["CHECKSUM_SHA256"]
        reuse[(row["symbol"], row["day"])] = row
    rows = []
    day = START
    while day <= END:
        quarter = f"{day.year}Q{(day.month - 1) // 3 + 1}"
        for symbol in ASSETS:
            name = f"{symbol}-metrics-{day}.zip"
            target = f"{BASE}/{symbol}/{name}"
            old = reuse.get((symbol, str(day)))
            rows.append(
                dict(
                    symbol=symbol,
                    day=str(day),
                    quarter=quarter,
                    ZIP=name,
                    official_URL=target,
                    CHECKSUM_URL=target + ".CHECKSUM",
                    cached_verified_sample=old is not None,
                    reused_manifest=old,
                )
            )
        day += timedelta(days=1)
    mean = sum(r["ZIP_bytes"] + r["CHECKSUM_bytes"] for r in previous) / len(previous)
    plan = dict(
        schema="CORE5_DAILY_OI_FIXED_INPUT_PLAN_V1",
        start=str(START),
        end=str(END),
        assets=ASSETS,
        calendar_days=(END - START).days + 1,
        asset_days=len(rows),
        reused_verified_asset_days=sum(r["cached_verified_sample"] for r in rows),
        initial_GET_count=2 * sum(not r["cached_verified_sample"] for r in rows),
        estimated_total_body_bytes=round(mean * len(rows)),
        estimate_basis="45 verified prior ZIP+CHECKSUM byte mean; estimate only",
        max_total_new_network_body_bytes=100_000_000,
        max_ZIP_body_bytes=512_000,
        max_CHECKSUM_body_bytes=4096,
        request_policy=(
            "One sequential IO stream, GET only, no HEAD/LIST/API/mirror; no "
            "redirects. At most 3 total attempts for transient "
            "timeout/connection/408/425/429/500/502/503/504, 1s then 3s backoff. Stop"
            " all network on 401/403/451 or other unrecognized status. 404 retained "
            "as missing, never invented."
        ),
        resume_policy=(
            "Fixed calendar keyed by asset/day. Recompute ZIP and sidecar SHA for "
            "cache hit; never GET verified objects again. Preserve verified 43 in-"
            "scope previous samples by reference and omit their bodies from new "
            "packs. Persist receipt per request and checkpoint per asset-day; pending"
            " downloaded ZIP reused for sidecar retry. Each guarded quarter batch "
            "<=1200s with cooperative stop before 1100s; resumable without calendar "
            "expansion."
        ),
        storage_policy=(
            "Raw provider ZIP and CHECKSUM immutable. Quarter packs <=10,000,000 "
            "bytes with provider request receipts, manifest, coverage and derived "
            "daily input rows; split only if necessary. Reuse published raw45 archive"
            " for cached sample bytes."
        ),
        clock_contract=(
            "Archive naive labels interpreted UTC, historical native units and actual"
            " publication UNKNOWN. Source day D exact positive unambiguous 23:55 "
            "stock only; ASSUMED availability at UTC midnight D+2. Current-vintage "
            "retrospective development input, not as-of proof. Consumer joining by "
            "assumed availability must keep all preexisting price rows and mask "
            "unavailable OI."
        ),
        quality_contract=(
            "Existing audit schema/safety validation reused. Sort actual timestamps; "
            "remove byte-identical duplicate CSV rows only. Distinct bytes at the "
            "same actual timestamp conflict and mask that timestamp. "
            "Nonfinite/nonpositive quantity or value invalid; missing terminal "
            "masked, no forward fill. Intraday coverage separate from terminal mask; "
            "terminal may be valid without all 288 slots."
        ),
        relative_change_contract=(
            "quantity ratio OI(D)/OI(D-k)-1 for k=1,7 only when every calendar-day "
            "terminal from D-k through D exists, unambiguous and positive. For 7d, "
            "endpoints alone do not bridge missing intermediate days. Changes share "
            "D+2 ASSUMED availability. Raw notional stock recorded, no price-derived "
            "inference."
        ),
        no_IO_or_execution=(
            "No price histories, outcomes, 2025 data, models, training, evaluation, "
            "threshold, portfolio or wallet IO; no prefix scaler/model work. Input "
            "calendar through 2024-04-30 only."
        ),
        rows=rows,
    )
    output = HERE / "PLAN.json"
    assert not output.exists()
    output.write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps({k: v for k, v in plan.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
