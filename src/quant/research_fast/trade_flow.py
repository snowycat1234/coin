"""Stream official Binance aggTrades ZIP rows into the one common 5s schema."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import os
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

VERSION = "trade_flow_5s_v1"
START, LOCKED = date(2025, 7, 1), date(2026, 3, 1)
STEP = 5_000_000
FLOAT_COLUMNS = (
    "open",
    "high",
    "low",
    "close",
    "vwap",
    "base_volume",
    "quote_notional",
    "aggressive_buy_notional",
    "aggressive_sell_notional",
    "flow_imbalance",
    "mean_trade_size",
    "max_trade_size",
    "large_trade_share",
    "mean_interarrival",
    "std_interarrival",
    "return_5s",
    "signed_price_impact",
)
SCHEMA = pa.schema(
    [
        *[
            pa.field(name, pa.string(), nullable=False)
            for name in ("version", "market", "symbol", "date")
        ],
        *[
            pa.field(name, pa.int64(), nullable=False)
            for name in (
                "timestamp",
                "close_us",
                "available_us",
                "trade_count",
                "buy_count",
                "sell_count",
                "raw_trade_count",
                "agg_count",
                "interarrival_count",
            )
        ],
        *[pa.field(name, pa.int64()) for name in ("first_trade_us", "last_trade_us")],
        *[pa.field(name, pa.float64()) for name in FLOAT_COLUMNS],
        pa.field("empty_bin", pa.bool_(), nullable=False),
        pa.field("quality", pa.uint16(), nullable=False),
    ]
)
CONTRACT = {
    "version": VERSION,
    "interval_us": STEP,
    "market": ["spot", "perp"],
    "trade_count": "sum(last_trade_id-first_trade_id+1); buy/sell counts partition raw executions",
    "raw_trade_count": "same as trade_count, explicit raw-count compatibility alias",
    "agg_count": "aggregate CSV rows (size/interarrival observations)",
    "trade_size_unit": "aggregate quote USD notional (price*base quantity)",
    "large_trade_threshold_usd": 10000,
    "large_trade_share": "quote notional from aggregate rows >=10000 USD / all quote notional",
    "interarrival_unit": "seconds between consecutive aggregate timestamps, includes prior bin",
    "interarrival_std": "population standard deviation; first daily row has no prior-day interval",
    "return_5s": "log(close/previous_bin_close), null when this or preceding bin is empty",
    "signed_price_impact": "mean signed log(price/previous_trade_price); buyer-aggressor +1, "
    "seller-aggressor -1; first daily row has no preceding-price contribution",
    "empty_bin": "known empty archive bin, counts/volumes zero; OHLC/VWAP/return/impact null",
    "quality": "0 means the published archive passed checksum and within-day ordering/raw IDs; "
    "not realtime qualification or executable-price evidence",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate_request(market, symbol, day):
    require(
        market in {"spot", "perp"} and symbol in {"BTCUSDT", "ETHUSDT"}, "Invalid market/symbol"
    )
    require(
        type(day) is date and START <= day < LOCKED,
        "Development date outside seal; locked date denied",
    )


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1_048_576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_trade(row, market, opened, closed):
    require(len(row) == (8 if market == "spot" else 7), "Unexpected official aggTrades columns")
    ints = []
    for index in (0, 3, 4, 5):
        require(row[index].isascii() and row[index].isdecimal(), "Invalid original integer field")
        ints.append(int(row[index]))
    agg, first, last, timestamp = ints
    timestamp *= 1 if market == "spot" else 1000
    price, quantity = float(row[1]), float(row[2])
    require(
        first <= last and opened <= timestamp < closed,
        "Raw IDs/timestamp outside requested UTC day",
    )
    require(
        all(math.isfinite(value) and value > 0 for value in (price, quantity, price * quantity)),
        "Nonfinite/nonpositive original price/quantity",
    )
    maker = row[6].lower()
    require(maker in {"true", "false"}, "Invalid maker boolean")
    if market == "spot":
        require(row[7].lower() in {"true", "false"}, "Invalid best-match boolean")
    return agg, first, last, timestamp, price, quantity, maker == "true"


def empty_state():
    return {
        "n": 0,
        "buy_n": 0,
        "raw_n": 0,
        "base": 0.0,
        "notional": 0.0,
        "buy": 0.0,
        "large": 0.0,
        "maximum": 0.0,
        "open": None,
        "close": None,
        "high": None,
        "low": None,
        "ia_n": 0,
        "ia_mean": 0.0,
        "ia_m2": 0.0,
        "impact_n": 0,
        "impact": 0.0,
        "buy_raw_n": 0,
        "first_trade_us": None,
        "last_trade_us": None,
    }


def convert_zip(
    zip_path,
    output_path,
    *,
    market,
    symbol,
    day,
    previous_day_last_raw_id=None,
    max_csv_bytes=4_000_000_000,
):
    """Bounded one-bin +512-row Arrow batch. No raw extraction or silent gap repairs."""
    validate_request(market, symbol, day)
    require(
        previous_day_last_raw_id is None
        or type(previous_day_last_raw_id) is int
        and previous_day_last_raw_id >= 0,
        "Invalid preceding raw high water",
    )
    zip_path, output_path = Path(zip_path), Path(output_path)
    require(
        not output_path.exists() and output_path.parent.is_dir(), "New exclusive Parquet required"
    )
    opened = int(datetime.combine(day, datetime.min.time(), tzinfo=UTC).timestamp()) * 1_000_000
    closed, bin_open, state = opened + 86_400_000_000, opened, empty_state()
    expected_member = f"{symbol}-aggTrades-{day.isoformat()}.csv"
    batch, rows, empty_bins, count, raw_count = [], 0, 0, 0, 0
    previous, first_trade, last_trade, previous_close = None, None, None, None
    output_path.touch(exist_ok=False)
    writer = pq.ParquetWriter(output_path, SCHEMA, compression="zstd", compression_level=3)

    def emit():
        nonlocal state, bin_open, batch, rows, empty_bins, previous_close
        n, notional = state["n"], state["notional"]
        row = {
            "version": VERSION,
            "market": market,
            "symbol": symbol,
            "date": day.isoformat(),
            "timestamp": bin_open,
            "close_us": bin_open + STEP,
            "available_us": bin_open + STEP,
            "trade_count": state["raw_n"],
            "buy_count": state["buy_raw_n"],
            "sell_count": state["raw_n"] - state["buy_raw_n"],
            "agg_count": n,
            "raw_trade_count": state["raw_n"],
            "interarrival_count": state["ia_n"],
            "first_trade_us": state["first_trade_us"],
            "last_trade_us": state["last_trade_us"],
            "open": state["open"],
            "high": state["high"],
            "low": state["low"],
            "close": state["close"],
            "vwap": notional / state["base"] if n else None,
            "base_volume": state["base"],
            "quote_notional": notional,
            "aggressive_buy_notional": state["buy"],
            "aggressive_sell_notional": notional - state["buy"],
            "flow_imbalance": (2 * state["buy"] / notional - 1) if n else None,
            "mean_trade_size": notional / n if n else None,
            "max_trade_size": state["maximum"] if n else None,
            "large_trade_share": state["large"] / notional if n else None,
            "mean_interarrival": state["ia_mean"] if state["ia_n"] else None,
            "std_interarrival": math.sqrt(max(0, state["ia_m2"] / state["ia_n"]))
            if state["ia_n"]
            else None,
            "return_5s": math.log(state["close"] / previous_close)
            if n and previous_close
            else None,
            "signed_price_impact": state["impact"] / state["impact_n"]
            if state["impact_n"]
            else None,
            "empty_bin": n == 0,
            "quality": 0,
        }
        require(
            all(
                value is None or math.isfinite(value)
                for key, value in row.items()
                if key in FLOAT_COLUMNS
            ),
            "Nonfinite derived bar",
        )
        batch.append(row)
        rows += 1
        empty_bins += n == 0
        if len(batch) == 512:
            writer.write_table(pa.Table.from_pylist(batch, schema=SCHEMA), row_group_size=512)
            batch.clear()
        previous_close = state["close"]
        state, bin_open = empty_state(), bin_open + STEP

    try:
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.infolist()
            require(
                len(members) == 1
                and members[0].filename == expected_member
                and members[0].file_size <= max_csv_bytes
                and not members[0].flag_bits & 1,
                "Unexpected/multiple/encrypted/oversize official ZIP member",
            )
            with archive.open(members[0]) as binary:
                consumed, header = 0, False
                while line := binary.readline(16_385):
                    consumed += len(line)
                    require(
                        len(line) <= 16_384 and consumed <= max_csv_bytes,
                        "CSV stream byte/line bound",
                    )
                    row = next(csv.reader(io.StringIO(line.decode("utf-8-sig"))))
                    if not row[0].isdecimal() and count == 0 and not header:
                        require(
                            [part.strip().lower() for part in row[:7]]
                            == [
                                "agg_trade_id",
                                "price",
                                "quantity",
                                "first_trade_id",
                                "last_trade_id",
                                "transact_time",
                                "is_buyer_maker",
                            ],
                            "Unexpected CSV header",
                        )
                        header = True
                        continue
                    current = parse_trade(row, market, opened, closed)
                    agg, first, last, timestamp, price, quantity, maker = current
                    if previous is not None:
                        require(
                            timestamp >= previous[3] and agg > previous[0],
                            "Duplicate/nonordered aggregate rows",
                        )
                        require(first == previous[2] + 1, "RAW_TRADE_ID_GAP_OR_OVERLAP")
                    elif previous_day_last_raw_id is not None:
                        require(
                            first == previous_day_last_raw_id + 1,
                            "CROSS_DAY_RAW_TRADE_ID_GAP_OR_OVERLAP",
                        )
                    first_trade = current if first_trade is None else first_trade
                    last_trade = current
                    while timestamp >= bin_open + STEP:
                        emit()
                    notional = price * quantity
                    state["n"] += 1
                    state["buy_n"] += not maker
                    state["raw_n"] += last - first + 1
                    state["buy_raw_n"] += 0 if maker else last - first + 1
                    state["first_trade_us"] = (
                        timestamp if state["first_trade_us"] is None else state["first_trade_us"]
                    )
                    state["last_trade_us"] = timestamp
                    state["base"] += quantity
                    state["notional"] += notional
                    state["buy"] += 0 if maker else notional
                    state["large"] += (
                        notional if notional >= CONTRACT["large_trade_threshold_usd"] else 0
                    )
                    state["maximum"] = max(state["maximum"], notional)
                    state["open"] = price if state["open"] is None else state["open"]
                    state["close"] = price
                    state["high"] = price if state["high"] is None else max(state["high"], price)
                    state["low"] = price if state["low"] is None else min(state["low"], price)
                    if previous is not None:
                        arrival = (timestamp - previous[3]) / 1_000_000
                        state["ia_n"] += 1
                        difference = arrival - state["ia_mean"]
                        state["ia_mean"] += difference / state["ia_n"]
                        state["ia_m2"] += difference * (arrival - state["ia_mean"])
                        state["impact_n"] += 1
                        state["impact"] += (-1 if maker else 1) * math.log(price / previous[4])
                    previous = current
                    count, raw_count = count + 1, raw_count + last - first + 1
        require(count > 0, "Empty archive day is unknown, not a complete no-trade day")
        while bin_open < closed:
            emit()
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=SCHEMA), row_group_size=512)
    finally:
        writer.close()
    with output_path.open("rb") as synced:
        os.fsync(synced.fileno())
    return {
        "status": "OFFICIAL_ARCHIVE_CONVERSION_COMPLETE",
        "version": VERSION,
        "market": market,
        "symbol": symbol,
        "date": day.isoformat(),
        "rows": rows,
        "empty_bins": empty_bins,
        "aggregate_rows": count,
        "raw_trade_count": raw_count,
        "first_a": first_trade[0],
        "first_f": first_trade[1],
        "first_l": first_trade[2],
        "first_timestamp_us": first_trade[3],
        "last_a": last_trade[0],
        "last_l": last_trade[2],
        "last_timestamp_us": last_trade[3],
        "cross_day_raw_boundary_verified": previous_day_last_raw_id is not None,
        "parquet_bytes": output_path.stat().st_size,
        "parquet_sha256": checksum(output_path),
        "schema_sha256": hashlib.sha256(str(SCHEMA).encode()).hexdigest(),
        "contract": CONTRACT,
    }
