"""Public-API boundary fixture; synthetic funding, no historical wallet replay."""
import argparse
import hashlib
import json
from pathlib import Path

from quant.bybit_isolated_account import BybitIsolatedAccount
from quant.perpetual_account import USDTLinearPerpetualAccount

MINUTE = 60_000_000


def funding_deficit(account_type):
    account = account_type(symbols=("BTCUSDT", "ETHUSDT"))
    account.update_marks(0, {s: {"price": "100", "close_us": 0, "available_us": 0}
                             for s in account.symbols})
    for i, symbol in enumerate(account.symbols):
        receipt = account.execute_fill(symbol, "BUY", "20", MINUTE + 1 + i, 0,
            f"synthetic-open-{symbol}", execution_mid_price="100", quote_available_us=MINUTE)
        assert receipt["status"] == "FILLED"
    # Deliberately extreme synthetic boundary rate, NOT observed market funding.
    # The debit exhausts free cash + BTC collateral, leaving ETH collateral intact.
    receipt = account.apply_funding("BTCUSDT", "synthetic-deficit", 2 * MINUTE,
                                   "4.5", 2 * MINUTE)
    assert account.unpaid_liability > 0 and account.nav() > 0
    return account, receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect", choices=("bug", "fixed"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base, base_receipt = funding_deficit(USDTLinearPerpetualAccount)
    account, receipt = funding_deficit(BybitIsolatedAccount)
    assert base.status == "BANKRUPT_HALT"
    assert (account.status != "BANKRUPT_HALT") if args.expect == "bug" else (account.status == "BANKRUPT_HALT")
    source = Path(__file__).resolve().parents[2] / "src/quant/bybit_isolated_account.py"
    evidence = {"scope": "SYNTHETIC_PUBLIC_API_BOUNDARY_FIXTURE_NOT_HISTORICAL_RESULT",
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "expected": args.expect, "base_funding": base_receipt,
                "bybit_funding": receipt, "base_summary": base.summary(),
                "bybit_summary": account.summary(), "old_market_wallets_rerun": 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "status": account.status,
                      "nav": str(account.nav()), "unpaid_liability": str(account.unpaid_liability)}))


if __name__ == "__main__":
    main()
