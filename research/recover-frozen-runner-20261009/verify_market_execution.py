"""Read-only actual-input checks for recorded fills/funding, without an account."""
import argparse
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal as D, localcontext
from functools import lru_cache
import gzip
import json
import os
from pathlib import Path
import resource

MINUTE = 60_000_000
START = 1784073600000000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
INSTRUMENTS = ("BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "XRP-USDT-SWAP", "DOGE-USDT-SWAP")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify(state, directory):
    root = state / "okx86/selected"
    intake = root / "minute-intake"
    coverage = json.loads((intake / "COVERAGE.json").read_bytes())
    require(coverage["full_window_ready"] and not coverage["original_API_only_window_ready"], "Explicit resolved/API-only distinction required")
    index = {(r["instrument_id"], r["date"]): r for r in coverage["shards"]}
    instruments = dict(zip(SYMBOLS, INSTRUMENTS, strict=True))
    @lru_cache(maxsize=6)
    def day(instrument, date, kind):
        path = intake / index[instrument, date]["bars_files"][kind]
        with gzip.open(path, "rt") as stream:
            return {r["open_ms"] * 1000: r for r in map(json.loads, stream)}
    def row(symbol, stamp, kind):
        date = datetime.fromtimestamp(stamp / 1_000_000, UTC).date().isoformat()
        return day(instruments[symbol], date, kind)[stamp]
    trades = json.loads((directory / "account/trades.json").read_bytes())
    funds = json.loads((directory / "account/funding.json").read_bytes())
    actual_rates = {}
    for symbol in SYMBOLS:
        with (root / instruments[symbol] / "funding.jsonl").open() as stream:
            for r in map(json.loads, stream):
                actual_rates[symbol, r["funding_time_ms"] * 1000] = float(r["realizedRate"])
    quantity_used = defaultdict(lambda: D(0))
    max_fee_error = max_fill_error = max_mark_error = D(0)
    ordinary = 0
    with localcontext() as ctx:
        ctx.prec = 50
        for trade in trades:
            if trade.get("liquidation_takeover") or trade.get("exchange_liquidation_instruction"):
                continue  # separate original liquidation witness auditor handles these
            s, t = trade["symbol"], trade["event_us"]
            e = trade["decimal_strings"]
            q, delta, mid, fill = (D(e[k]) for k in ("quantity", "position_delta", "execution_mid_price", "fill_price"))
            require(t % MINUTE == 1 and t >= START + MINUTE + 1, "Delayed observed minute-open fill required")
            open_us = t - 1
            source = row(s, open_us, "trade")
            previous = row(s, open_us - MINUTE, "trade")
            require(mid == D(str(float(source["open"]))), "Observed trade-open fill mid required")
            require(q > 0 and q % D('1e-8') == 0 and abs(delta) == q, "Original lot and signed quantity required")
            require(trade["side"] == ("BUY" if delta > 0 else "SELL"), "Recorded side must match signed quantity")
            sign = D(1) if delta > 0 else D(-1)
            expected = mid * (1 + sign * D('0.0008'))
            max_fill_error = max(max_fill_error, abs(fill - expected))
            fee_error = abs(D(e["fee_amount"]) - q * fill * D('0.00055'))
            max_fee_error = max(max_fee_error, fee_error)
            require(trade["leg"] != "OPEN" or q * fill >= 10, "Opening minimum notional required")
            require(trade["fee_asset"] == "USDT", "No base-inventory fee substitution")
            quantity_used[s, t] += q
            # Raw quote strings remain preserved. Float conversion is the exact
            # published runner's numerical-input convention, never base volume.
            capacity = D(str(float(previous["quote_turnover_USDT"]))) * D('.001') / mid
            require(quantity_used[s, t] <= capacity + D('1e-12'), "Shared prior-minute quote capacity exceeded")
            past_mark = row(s, open_us - MINUTE, "mark")
            max_mark_error = max(max_mark_error, abs(D(e["mark_price"]) - D(str(float(past_mark["close"])))))
            earliest = ((trade["signal_us"] + MINUTE - 1) // MINUTE + 1) * MINUTE + 1
            require(t >= earliest, "Original signal latency required")
            ordinary += 1
        require(max_fee_error <= D('1e-18') and max_fill_error <= D('1e-18') and max_mark_error <= D('1e-18'), "Declared fee/friction/mark identity differs")
        for t in sorted(set(r["event_us"] for r in trades)):
            ordinary_at_t = [r["leg"] for r in trades if r["event_us"] == t and not r.get("liquidation_takeover")]
            require(ordinary_at_t == sorted(ordinary_at_t, key=lambda leg: leg != "CLOSE"), "All reductions must precede increases")
        require(len(funds) == len(actual_rates) == 1290, "All original signed events required")
        seen = set()
        for f in funds:
            s, t = f["symbol"], f["event_us"]
            require((s, t) not in seen and f["raw_rate"] == actual_rates[s, t], "Exact-once actual signed funding rate required")
            seen.add((s, t))
            require(f["conditional_rate_scale"] == 1, "Original unscaled actual funding required")
            if t == START:
                require(not f["owned"] and f["quantity"] == 0 and f["signed_funding_USDT"] == 0 and f["mark_price"] is None, "Fresh first funding has no held position")
            elif f["mark_price"] is not None:
                source = row(s, t - 2 * MINUTE, "mark")
                require(f["mark_close_us"] == t - MINUTE < t and f["mark_price"] == float(source["close"]), "Strictly prior actual completed mark required")
    return dict(status="PASS_ACTUAL_TRADE_OPEN_PREVIOUS_QUOTE_SHARED_CAPACITY_FEES_FRICTION_MARK_AND_SIGNED_FUNDING",
                ordinary_fill_legs=ordinary, funding_events=len(funds),
                maximum_fee_error_USDT=float(max_fee_error), maximum_fill_price_error=float(max_fill_error),
                maximum_mark_error=float(max_mark_error), original_API_only_window_ready=False,
                archive_precedence="PRESERVED_PINNED_SOL_ONE_ROW_OFFICIAL_ARCHIVE", independent_order_intents_reconstructed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (6_000_000_000, 6_000_000_000))
    report = verify(args.state, args.directory)
    with (args.directory / "ACTUAL_INPUT_AUDIT.json").open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
