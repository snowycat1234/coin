"""Portable journal-only independent financial reconciliation and hash checks."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "verification_helpers"))
from modules.transformer_v3.isolated_audit import verify

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
POLICIES = ("FIXED_VOL_HOLD", "FIXED_CSMOM21", "STATIC50")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconcile(root, policy):
    directory = root / policy
    account = directory / "account"
    summary = json.loads((account / "summary.json").read_bytes())
    execution = json.loads((directory / "EXECUTION.json").read_bytes())
    audit = verify(account, SYMBOLS, 1)
    if not (audit["minutes"] == summary["completed_minutes"] == summary["required_minutes"] == 123840
            and summary["terminal_cash_realized"] and summary["terminal_not_forced_free_fill"]
            and summary["completion"] == "COMPLETE_CONDITIONAL_ACCOUNT"
            and execution["status"] == "COMPLETE_CONDITIONAL_ACCOUNT"):
        raise ValueError("Full independent continuous 86-day paid-flat account required")
    trades = json.loads((account / "trades.json").read_bytes())
    funding = json.loads((account / "funding.json").read_bytes())
    liquidations = json.loads((account / "liquidations.json").read_bytes())
    if summary["liquidation_count"] != len(liquidations):
        raise ValueError("Liquidation witness count differs")
    if len(funding) != 1290 or summary["funding_original_events"] != 1290:
        raise ValueError("Complete actual signed funding events required")
    if not all(p["quantity"] == 0 for p in summary["positions"].values()):
        raise ValueError("Actual terminal inventory remains")
    if not trades or not any(t["leg"] == "CLOSE" and t["fee_amount"] > 0 for t in trades):
        raise ValueError("Paid actual closing fills required")
    if not all(not f["owned"] and f["quantity"] == 0 and f["signed_funding_USDT"] == 0
               for f in funding if f["event_us"] == 1784073600000000):
        raise ValueError("Fresh first funding must have no owned position")
    if execution["elapsed_seconds"] > 600 or execution["peak_RSS_bytes"] > 6_000_000_000:
        raise ValueError("Frozen wallet resource bound exceeded")
    audit.update(policy=policy, liquidation_count=len(liquidations), fresh_first_funding_flat=True,
                 full_capital_USDT=10000, continuous_days=86, prior_accounts_stitched=False,
                 terminal_paid_flat=True)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE / "results86")
    parser.add_argument("--policy", choices=POLICIES)
    parser.add_argument("--write-audit", action="store_true")
    args = parser.parse_args()
    manifest_path = args.root.parent / "RESULT_MEMBER_HASHES.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_bytes())
        for f in manifest["files"]:
            path = args.root.parent / f["path"]
            if path.stat().st_size != f["bytes"] or sha(path) != f["sha256"]:
                raise ValueError("Published result byte identity differs: " + f["path"])
    for policy in (args.policy,) if args.policy else POLICIES:
        audit = reconcile(args.root, policy)
        if args.write_audit:
            with (args.root / policy / "INDEPENDENT_AUDIT.json").open("x") as stream:
                json.dump(audit, stream, indent=2)
                stream.write("\n")
        print(json.dumps(dict(policy=policy, status=audit["status"], minutes=audit["minutes"],
            maximum_NAV_error_USDT=audit["maximum_NAV_error_USDT"],
            maximum_wallet_error_USDT=audit["maximum_wallet_error_USDT"],
            terminal_paid_flat=audit["terminal_paid_flat"], liquidations=audit["liquidation_count"])), flush=True)


if __name__ == "__main__":
    main()
