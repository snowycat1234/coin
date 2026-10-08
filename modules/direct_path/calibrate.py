"""Read-only calibration on the preregistered, existing 2024H1 E5 family path.

Inputs are selected members of the user-authorized 7b5b9f7 reproduction bundle.
This command verifies member hashes and never downloads, trains or sends orders.
The archive can be reconstructed sparsely: byteparts 000,009,010 suffice here.
They do NOT verify the full reassembled ZIP SHA; selected member hashes do.
"""
from __future__ import annotations

import argparse
from decimal import Decimal as D, localcontext
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from .prototype import (
    CORE5, DAY_US, E5, Context, ProxyExposureBreach, daily_proxy, map_budget, mapped_path,
)

SOURCE_COMMIT = "7b5b9f702f5f04d25fc8d12fa8b928fa3e604d93"
MEMBER_MANIFEST_SHA256 = "b29686555f9691252f832af373ad71b1c0d11fc70639589cf9ada1ad9786d6df"
PANEL_COMMIT = "19e81198380656713cbf8f5ecdebaa0c21e9ebc8"
PANEL_INDEX_SHA256 = "5b6edb92ede1eba6122a628b70d16c3a290d86415577577df87d61bf6eacd370"


def exact(row, key):
    return D(str(row.get("decimal_strings", {}).get(key, row.get(key))))


def fixed_ledger(trades, funding, summary):
    """Independent net-unit carry, event funding and two equivalent PnL bridges.

    Liquidation takeover is a ledger close whose loss is already in its cash
    flow. Never subtract summary liquidation_loss a second time. This bridge
    explains recorded fills; it does not predict pending/capacity execution.
    """
    with localcontext() as ctx:
        ctx.prec = 50
        quantities = dict.fromkeys(CORE5, D(0))
        mid_cash, fill_cash, fees, execution, coupons = [D(0)] * 5
        max_fee_error = max_execution_error = max_funding_error = D(0)
        events = [(int(r["event_us"]), 1, i, r) for i, r in enumerate(trades)]
        events += [(int(r["event_us"]), 0, i, r) for i, r in enumerate(funding)]
        ids = set()
        takeover_count = 0
        for stamp, kind, _, row in sorted(events, key=lambda e: e[:3]):
            s = row["symbol"]
            if s not in CORE5:
                raise ValueError("Unexpected ledger symbol identity")
            if kind == 1:
                identity = ("FILL", s, row["fill_id"], row["leg"])
                if identity in ids:
                    raise ValueError("Duplicate recorded fill would double cost")
                # A legal native flip has CLOSE and OPEN with the SAME fill_id.
                ids.add(identity)
                quantity = exact(row, "quantity")
                delta = quantity * (1 if row["side"] == "BUY" else -1)
                if (delta != exact(row, "position_delta")
                        or quantities[s] != exact(row, "quantity_before")
                        or quantities[s] + delta != exact(row, "quantity_after")):
                    raise ValueError("Broken signed quantity continuation")
                mid, fill = exact(row, "mid_price"), exact(row, "fill_price")
                takeover = bool(row.get("liquidation_takeover"))
                if takeover:
                    takeover_count += 1
                    if row.get("price_role") != "BANKRUPTCY_TAKEOVER_NOT_MARKET_FILL":
                        raise ValueError("Explicit takeover identity required")
                    expected_fee = expected_execution = D(0)
                else:
                    expected_fill = mid * (1 + (D(".0008") if delta > 0 else -D(".0008")))
                    if fill != expected_fill:
                        raise ValueError("BASE27 adverse fill price mismatch")
                    expected_fee = quantity * fill * D(".00055")
                    expected_execution = quantity * abs(fill - mid)
                max_fee_error = max(max_fee_error, abs(expected_fee - exact(row, "fee_amount")))
                max_execution_error = max(max_execution_error,
                                          abs(expected_execution - exact(row, "execution_cost")))
                mid_cash -= delta * mid
                fill_cash -= delta * fill
                quantities[s] += delta
                fees += exact(row, "fee_amount")
                execution += exact(row, "execution_cost")
            else:
                identity = ("FUNDING", s, row["event_id"])
                if identity in ids:
                    raise ValueError("Duplicate funding event would double debit")
                ids.add(identity)
                if quantities[s] != exact(row, "quantity"):
                    raise ValueError("Funding quantity must be owned before same-time fill")
                if row.get("mark_price") is None:
                    if quantities[s] or row.get("owned"):
                        raise ValueError("Unknown mark with owned position cannot be imputed")
                    expected = D(0)
                else:
                    if int(row["mark_close_us"]) >= stamp:
                        raise ValueError("Funding mark must be strictly past")
                    rate = D(row["assumed_fraction_decimal"])
                    expected = -quantities[s] * exact(row, "mark_price") * rate
                max_funding_error = max(max_funding_error,
                                        abs(expected - exact(row, "signed_funding_USDT")))
                coupons += exact(row, "signed_funding_USDT")
        if any(quantities.values()) or not summary["terminal_cash_realized"]:
            raise ValueError("Recorded path needs a paid, fully flat terminal")
        mid_net = mid_cash - execution - fees + coupons
        fill_net = fill_cash - fees + coupons  # NO extra execution debit here
        native = exact(summary, "net_PnL")
        return dict(trade_legs=len(trades), funding_rows=len(funding), takeover_count=takeover_count,
                    midpoint_bridge_error_USDT=float(abs(mid_net - native)),
                    fill_cashflow_bridge_error_USDT=float(abs(fill_net - native)),
                    maximum_fee_error_USDT=float(max_fee_error),
                    maximum_execution_error_USDT=float(max_execution_error),
                    maximum_funding_error_USDT=float(max_funding_error),
                    gross_midpoint_USDT=float(mid_cash), fees_USDT=float(fees),
                    execution_USDT=float(execution), funding_USDT=float(coupons),
                    terminal_paid_close=True, liquidation_loss_debited_again=False)


def calibrate(root, member_manifest):
    root = Path(root)
    manifest_bytes = Path(member_manifest).read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != MEMBER_MANIFEST_SHA256:
        raise ValueError("Fixed commit's member manifest identity changed")
    entries = {r["name"]: r for r in json.loads(manifest_bytes)["members"]}
    account = "results/e5_h1/family/account/"
    chosen = ["h1_market/inputs/H1_E5_INPUTS.npz", "results/e5_h1/family/PROPOSALS.json"]
    chosen += [account + name + ".json" for name in ("summary", "trades", "funding")]
    identities = {}
    for name in chosen:
        data = (root / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != entries[name]["bytes"] or digest != entries[name]["sha256"]:
            raise ValueError("Selected immutable input member changed: " + name)
        identities[name] = digest
    with np.load(root / chosen[0], allow_pickle=False) as z:
        arrays = {k: z[k].copy() for k in z.files}
    if tuple(arrays["expert_order"]) != E5 or tuple(arrays["symbol_order"]) != CORE5:
        raise ValueError("Frozen E5 and CORE5 identity mismatch")
    decisions = arrays["decision_us"]
    if (len(decisions) != 182 or int(decisions[0]) != 1704067200000000
            or int(decisions[-1]) + DAY_US != 1719792000000000):
        raise ValueError("Only the existing 2024H1 fixed family calibration path")
    if (np.any(arrays["target_available_us"] > decisions[:, None])
            or not np.array_equal(arrays["expert_eligible"], arrays["expert_asset_eligible"].all(2))):
        raise ValueError("Late target or inconsistent eligibility source")
    contexts = [Context(int(d), int(arrays["market_state13_available_us"][i]),
                        arrays["expert_targets"][i], arrays["expert_eligible"][i],
                        arrays["past_returns30"][i], arrays["market_state13"][i],
                        arrays["target_available_us"][i])
                for i, d in enumerate(decisions)]
    proposals = json.loads((root / chosen[1]).read_bytes())
    if len(proposals) != len(contexts):
        raise ValueError("Full saved fixed budget path required")
    request = np.array([0., .25, .25, .25, .25])
    prior = np.eye(5)[0]
    budget_error = target_error = 0.
    for c, saved in zip(contexts, proposals, strict=True):
        if c.decision_us != saved["decision_us"]:
            raise ValueError("Saved mapper path clock mismatch")
        p = map_budget(prior, request, c)
        prior = p["budget"]
        budget_error = max(budget_error, float(np.max(np.abs(prior - saved["budget"]))))
        target_error = max(target_error, float(np.max(np.abs(p["targets"] - saved["targets"]))))
    summary = json.loads((root / (account + "summary.json")).read_bytes())
    trades = json.loads((root / (account + "trades.json")).read_bytes())
    funding = json.loads((root / (account + "funding.json")).read_bytes())
    ledger = fixed_ledger(trades, funding, summary)
    targets, records = mapped_path(np.tile(request, (len(contexts), 1)), contexts)
    # Last endpoint uses the actual recorded terminal marks. Last-day quantity
    # is zero, so this endpoint's price has exactly zero objective effect.
    prices = np.vstack([arrays["market_close"],
                        [summary["terminal_mark_prices"][s] for s in CORE5]])
    coeff = np.zeros((len(contexts), 5))
    start, end = int(decisions[0]), int(decisions[-1]) + DAY_US
    for row in funding:
        stamp = int(row["event_us"])
        if not start <= stamp <= end:
            raise ValueError("Funding event outside this independent fragment")
        if stamp == start:
            if row["owned"]:
                raise ValueError("Fragment initial ownership must be cash")
            continue
        t = (stamp - start - 1) // DAY_US  # event at next midnight belongs to previous units
        if row.get("mark_price") is None:
            raise ValueError("Missing event mark; do not zero fill future funding")
        coeff[t, CORE5.index(row["symbol"])] += float(exact(row, "mark_price") *
                                                     D(row["assumed_fraction_decimal"]))
    proxy = daily_proxy(targets, prices, coeff)
    metrics = dict(net_PnL="net_PnL", fees="fees_USDT", funding="funding_USDT",
                   gross="gross_PnL_same_quantities")
    comparison = {key: dict(proxy_USDT=proxy[key], native_USDT=float(summary[native]),
                            proxy_minus_native_USDT=proxy[key] - float(summary[native]))
                  for key, native in metrics.items()}
    comparison["execution"] = dict(proxy_USDT=proxy["spread"] + proxy["slippage"],
        native_USDT=summary["execution_cost_USDT"],
        proxy_minus_native_USDT=proxy["spread"] + proxy["slippage"] - summary["execution_cost_USDT"])
    return dict(status="FIXED_PATH_CALIBRATION_ONLY_ZERO_FITS_NOT_NATIVE_POLICY_ACCEPTANCE",
                source_commit=SOURCE_COMMIT, selected_member_sha256=identities,
                selection="PREDECLARED_H1_E5_FAMILY_NOT_PICKED_BY_PROXY_PROFIT",
                source_archive_full_reassembly_sha_verified=False,
                fragment_days=len(contexts), mapper_max_budget_error=budget_error,
                mapper_max_target_error=target_error,
                maximum_mapper_covariance_annual_vol=max(r["annual_vol"] for r in records),
                fixed_actual_fill_ledger=ledger, daily_proxy_vs_native=comparison,
                net_error_basis_points_of_initial_capital=(proxy["net_PnL"] - summary["net_PnL"]),
                proxy_exposure_observations="DAILY_BOUNDARIES_ONLY_INTRADAY_UNREPRESENTED",
                final_day_cash=True, terminal_endpoint="RECORDED_MARK_UNUSED_ZERO_OWNERSHIP",
                fits=0, orders=0, gpu=0)


def calibrate_panel(root):
    """Preferred 1.2MB parent-exported fixed panel; tail is failure witness only."""
    root = Path(root)
    index_bytes = (root / "PANEL_INDEX.json").read_bytes()
    if hashlib.sha256(index_bytes).hexdigest() != PANEL_INDEX_SHA256:
        raise ValueError("Fixed parent panel index changed")
    index = json.loads(index_bytes)
    entries = {e["name"]: e for e in index["files"]}
    verified = {}

    def read(name):
        raw = (root / name).read_bytes()
        entry = entries[name]
        if len(raw) != entry["bytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("Fixed panel delivery bytes changed: " + name)
        verified[name] = entry["sha256"]
        if name.endswith(".gz"):
            raw = gzip.decompress(raw)
        if (len(raw) != entry["decoded_bytes"]
                or hashlib.sha256(raw).hexdigest() != entry["decoded_sha256"]):
            raise ValueError("Fixed panel decoded bytes changed: " + name)
        return raw

    cases = []
    for spec in index["cases"]:
        tag = spec["tag"]
        journal = json.loads(read(tag + ".json.gz"))
        read(spec["array_file"])  # bind bytes before NumPy opens this local file
        with np.load(root / spec["array_file"], allow_pickle=False) as z:
            a = {k: z[k].copy() for k in z.files}
        if tuple(a["symbol_order"]) != CORE5:
            raise ValueError("Fixed panel CORE5 order mismatch")
        if (not np.array_equal(a["interval_end_us"], a["decision_us"] + DAY_US)
                or not np.all(np.diff(a["decision_us"]) == DAY_US)
                or not np.array_equal(a["causal_trade_close_before"][1:],
                                      a["observed_trade_close_after"][:-1])):
            raise ValueError("Panel daily price/time continuity mismatch")
        if (np.any(a["actually_applied_targets"][-1])
                or not np.array_equal(a["global_forced_terminal_day"],
                                      np.arange(len(a["decision_us"])) == len(a["decision_us"]) - 1)):
            raise ValueError("Common forced final cash day required")
        summary = journal["native_summary"]
        ledger = fixed_ledger(journal["full_signed_trade_journal"],
                              journal["full_funding_event_journal"], summary)
        t_count = len(a["decision_us"])
        coeff = np.zeros((t_count, 5))
        start = int(a["decision_us"][0])
        for row in journal["full_funding_event_journal"]:
            stamp = int(row["event_us"])
            if stamp == start:
                if row["owned"]:
                    raise ValueError("Initial wallet is cash")
                continue
            t = (stamp - start - 1) // DAY_US
            if (not 0 <= t < t_count or row.get("mark_price") is None
                    or int(row["mark_close_us"]) >= stamp):
                raise ValueError("Complete strictly-past event funding marks required")
            coeff[t, CORE5.index(row["symbol"])] += float(exact(row, "mark_price") *
                                                         D(row["assumed_fraction_decimal"]))
        prices = np.vstack([a["causal_trade_close_before"], a["observed_trade_close_after"][-1]])
        case = dict(tag=tag, role=spec["role"], fixed_actual_fill_ledger=ledger,
                    native_net_PnL=summary["net_PnL"], native_liquidations=spec["liquidations"])
        try:
            proxy = daily_proxy(a["actually_applied_targets"], prices, coeff)
        except ProxyExposureBreach as error:
            case["daily_proxy"] = dict(status="STOP_NO_FULL_PATH_PROFIT_CLAIM",
                day_index=error.day_index,
                decision_us=int(a["decision_us"][error.day_index]),
                boundary_us=start + error.boundary_index * DAY_US,
                boundary_NAV=error.equity, gross_weight=float(error.exposure.sum() / error.equity),
                maximum_asset_weight=float(error.exposure.max() / error.equity),
                missing_mechanisms="INTRADAY_RISK_CAP_REDUCTION_PENDING_CAPACITY_MARGIN_TAKEOVER")
        else:
            delta = np.diff(proxy["nav"]) - a["observed_native_net_increment_USDT"]
            case["daily_proxy"] = dict(status=proxy["status"], net_PnL=proxy["net_PnL"],
                proxy_minus_native_USDT=proxy["net_PnL"] - summary["net_PnL"],
                mean_absolute_daily_increment_error_USDT=float(np.abs(delta).mean()),
                maximum_absolute_daily_increment_error_USDT=float(np.abs(delta).max()),
                maximum_absolute_endpoint_NAV_error_USDT=float(np.max(np.abs(
                    proxy["nav"][1:] - a["observed_native_NAV_after"]))),
                fee_error_USDT=proxy["fees"] - summary["fees_USDT"],
                execution_error_USDT=proxy["spread"] + proxy["slippage"] - summary["execution_cost_USDT"],
                funding_error_USDT=proxy["funding"] - summary["funding_USDT"])
        cases.append(case)
    name = "TAIL_INTRADAY_LIQUIDATION_WITNESS.npz"
    read(name)
    with np.load(root / name, allow_pickle=False) as z:
        columns, values = z["columns"].tolist(), z["values"]
        quantities = values[:, columns.index("DOGEUSDT_quantity")]
        times = values[:, columns.index("close_us")]
        # Original explicit witness event, never selected by proxy results.
        event = 1731199500000000
        ix = np.flatnonzero(times == event)
        if len(ix) != 1 or ix[0] == 0:
            raise ValueError("Original predetermined takeover minute missing")
        t = int(ix[0])
        witness = dict(rows=len(values), liquidation_us=event,
            DOGE_quantity_before=float(quantities[t - 1]), DOGE_quantity_after=float(quantities[t]),
            NAV_before=float(values[t - 1, columns.index("nav")]),
            NAV_after=float(values[t, columns.index("nav")]),
            role="EXECUTION_FAILURE_ONLY_NOT_TRAIN_VALIDATION_OR_MODEL_SELECTION")
    return dict(status="PREFERRED_FIXED_PANEL_CALIBRATION_ZERO_FITS", panel_commit=PANEL_COMMIT,
                selected_member_sha256=verified, cases=cases, intraday_witness=witness,
                fits=0, orders=0, gpu=0, tail_used_to_select_training_recipe=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--source-root", type=Path)
    mode.add_argument("--panel-root", type=Path)
    parser.add_argument("--member-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.source_root and not args.member_manifest:
        parser.error("--source-root requires --member-manifest")
    report = (calibrate_panel(args.panel_root) if args.panel_root else
              calibrate(args.source_root, args.member_manifest))
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
