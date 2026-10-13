"""Zero-financial-advance cold restore of one finished fine-grid wallet."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODULE = ROOT / "coin_quantity_resolution_20261013"
STATE = MODULE / "state_20261013"
sys.path.insert(0, str(MODULE))
from provenance import verify_completed_run


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def same(a, b, label):
    if a != b:
        raise ValueError(f"Fine-grid cold audit mismatch: {label}")


def main(case_id: str) -> None:
    if sys.flags.optimize:
        raise RuntimeError("Assertions must remain enabled during cold restore")
    import numpy as np
    from run_cases import guard, preflight

    plan = preflight.bindings()
    expected = {f"{c['case_id']}_FINE_{mode}": (c, mode)
                for c in plan["cases"] for mode in plan["modes"]}
    if case_id not in expected:
        raise ValueError("Case outside fixed twelve-cell plan")
    if set(verify_completed_run(STATE, MODULE, plan)) != set(expected):
        raise ValueError("Fixed audit case set differs from completed run")
    case, mode = expected[case_id]
    # The verified transport installs the frozen repository import root before
    # importing the reviewed fine account, exactly as the historical worker did.
    port, source, GuardSimulator = guard.load_port(case["year"])
    from fine_account import FineGridAccount, profile_sha
    state = STATE / case_id
    binding = json.loads((state / "BINDING.json").read_text())
    saved = json.loads((state / "ACCOUNT.json").read_text())
    result = json.loads((state / "RESULT.json").read_text())
    minute_numeric = json.loads((state / "MINUTE_NUMERIC.json").read_text())
    same(binding["case_id"], case_id, "case binding")
    same(binding["mode"], mode, "mode binding")
    same(binding["source_index_SHA256"], case["source_index_SHA256"], "source binding")
    same(binding["target_archive_SHA256"], case["target_archive_SHA256"], "archive binding")
    same(binding["target_array_SHA256"], case["target_array_SHA256"], "target binding")
    same(binding["fine_profile_SHA256"], profile_sha(), "fine profile binding")
    same(binding["fine_account_SHA256"], sha(MODULE / "fine_account.py"), "account code binding")
    same(binding["freeze_manifest_SHA256"], sha(MODULE / "FROZEN_CODE.json"), "reviewed freeze binding")
    same(binding["fine_account_class"], FineGridAccount.VERSION, "account class")
    same(binding["calendar"], case["calendar"], "calendar binding")
    same(result["case_id"], case_id, "result identity")
    Simulator = GuardSimulator if mode == "GUARD50" else port.native.NativeDailySimulator
    same([source["start"], source["end"]], case["calendar"], "source calendar")
    snapshot, pointer = port.restore_snapshot(state / "recovery", binding)
    same(pointer["binding"], binding, "pointer binding")
    same(sha(state / "recovery" / pointer["snapshot_path"]), pointer["snapshot_SHA256"],
         "snapshot SHA")
    same(sum(row["rows"] for row in pointer["chunks"]), pointer["completed_minutes"],
         "lossless day count")

    original_advance = Simulator.advance_day
    def forbidden_advance(*_args, **_kwargs):
        raise RuntimeError("Cold audit cannot advance financial history")
    Simulator.advance_day = forbidden_advance
    try:
        sim = Simulator.from_snapshot(snapshot, source, account_class=FineGridAccount)
        same(sim.state_hash(), pointer["state_hash"], "restored state hash")
        same(sim.state_hash(), result["genuine_state_hash"], "result state hash")
        same(sim.cursor, pointer["cursor"], "cursor")
        same(sim.stop, pointer["stop"], "stop")
        same(sim.rows_written, pointer["completed_minutes"], "minute rows")
        output = sim.result()
    finally:
        Simulator.advance_day = original_advance
    same(output["summary"], saved["summary"], "account summary")
    same(output.get("protective_policy"), saved["protective_policy"], "protective journal")
    same(output.get("protective_policy"), result["protective_policy"], "result protective journal")
    for key in ("trades", "funding", "rejections", "breaches", "extrema", "target_meta"):
        same(output[key], saved[key], f"account {key}")
    same(output["targets"].to_dicts(), saved["targets"], "executed targets")
    same(output.get("liquidations", []), saved["liquidations"], "liquidation journal")
    same(port.fingerprint(output["minute"]), minute_numeric["columns"], "all numeric minute bytes")
    same(output["minute"].height, result["completed_minutes"], "result minute count")
    summary = output["summary"]
    expected_minutes = (source["end"] - source["start"]) // 60_000_000
    full = summary["completed_minutes"] == expected_minutes
    paid = (full and summary["completion"] == "COMPLETE_CONDITIONAL_ACCOUNT"
            and bool(summary["terminal_cash_realized"]))
    same(result["full_calendar"], full, "full-calendar classification")
    same(result["paid_flat"], paid, "paid-flat classification")
    same(result["mode"], mode, "reported mode")
    same(result["year"], case["year"], "reported year")
    same(result["arm"], case["arm"], "reported arm")
    same(result["status"], "COMPLETE_PAID_FLAT" if paid else
         "FULL_NOT_PAID_OR_NOT_EVALUABLE" if full else "STOP_PARTIAL",
         "reported completion class")
    same(result["paid_cash_PnL_USDT"], summary["net_PnL"] if paid else None,
         "paid PnL classification")
    same(result["marked_PnL_USDT"], summary["net_PnL"], "marked PnL")
    same(result["marked_return"], summary["net_PnL"] / 10000, "marked return")
    same(result["minute_drawdown"], summary["all_observation_max_drawdown"], "drawdown")
    same(result["mean_actual_gross"], float(output["minute"]["gross_weight"].mean())
         if output["minute"].height else None, "mean actual gross")
    same(result["max_actual_gross"], float(output["minute"]["gross_weight"].max())
         if output["minute"].height else None, "max actual gross")
    same(result["terminal_residual_gross_notional_USDT"], summary["terminal_marked_notional"],
         "terminal residue")
    same(result["terminal_residual_marked_notional_USDT"],
         summary["terminal_signed_marked_notional"], "terminal signed marks")
    same(result["rejection_counts"], port.native.rejection_counts(output["rejections"]),
         "rejection reasons")
    same(result["trade_legs"], summary["trade_legs"], "trade legs")
    same(result["halt_count"], int(summary["account_status"] in
         ("BANKRUPT_HALT", "LIQUIDATION_REQUIRED_HALT")), "halt count")
    same(result["liquidation_event_count"], len(output.get("liquidations", [])),
         "liquidation events")
    same(result["completion"], summary["completion"], "account completion")
    same(result["account_status"], summary["account_status"], "account status")
    same(result["completed_minutes"], summary["completed_minutes"], "completed minutes")
    same(result["required_minutes"], expected_minutes, "required minutes")
    same(result["stop_us"], summary["stop_us"], "stop timestamp")
    same(result["daily_observed_days"], output["minute"].filter(
         port.native.pl.col("close_us") % 86_400_000_000 == 0).height,
         "daily observation count")
    _, inventory = port.native.episodes(output["trades"], tuple(source["symbols"]))
    for symbol in source["symbols"]:
        same(inventory[symbol], sim.account.positions[symbol].quantity, f"signed inventory {symbol}")
    same(result["terminal_residual_quantity"],
         {symbol: str(sim.account.positions[symbol].quantity) for symbol in source["symbols"]},
         "terminal signed quantities")
    bridge = port.native.nav_bridge(output["trades"], output["funding"], inventory,
                                    summary["terminal_mark_prices"], sim.account.nav())
    same(bridge, result["independent_decimal_NAV_bridge"], "independent Decimal NAV bridge")
    with np.errstate(all="raise"):
        output["minute"]["nav"].to_numpy().astype(float)
    receipt = {"case_id": case_id, "status": "PASS_COLD_RESTORE_ZERO_ADVANCE",
               "financial_advances": 0, "day_chunks_sha_verified": len(pointer["chunks"]),
               "minute_rows_sha_verified": output["minute"].height,
               "minute_columns_sha_verified": len(minute_numeric["columns"]),
               "all_journals_equal": True, "all_targets_equal": True,
               "state_hash": sim.state_hash(), "result_SHA256": sha(state / "RESULT.json"),
               "account_SHA256": sha(state / "ACCOUNT.json"),
               "binding_SHA256": sha(state / "BINDING.json"),
               "pointer_SHA256": sha(state / "recovery/POINTER.json"),
               "runner_SHA256": sha(MODULE / "run_cases.py"),
               "fine_account_SHA256": sha(MODULE / "fine_account.py")}
    path = HERE / "receipts" / f"{case_id}.json"
    path.parent.mkdir(exist_ok=True)
    with path.open("x") as file:
        json.dump(receipt, file, indent=2, sort_keys=True, allow_nan=False)
        file.write("\n")
    print(receipt["status"], case_id, "minutes", receipt["minute_rows_sha_verified"],
          "chunks", receipt["day_chunks_sha_verified"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id")
    main(parser.parse_args().case_id)
