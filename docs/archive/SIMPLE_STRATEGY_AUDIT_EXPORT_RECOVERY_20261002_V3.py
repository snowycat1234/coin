"""Recover already verified72 ledger results; no ledger/source Parquet reads."""
from pathlib import Path
from datetime import UTC,datetime
import json,hashlib,sys,math
import xml.etree.ElementTree as ET
ROOT=Path("/mnt/d/codex/coin")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
partial=ROOT/"reports/fast_research/SIMPLE_STRATEGY_COMPARISON_INDEPENDENT_ACTUAL_AUDIT_20261002_V3_R3.json"
text=partial.read_text()
cut=text.index('  "aggregate":')
prefix=text[:cut].rstrip()
assert prefix.endswith(",")
audit=json.loads(prefix[:-1]+chr(10)+"}")
assert audit["status"]=="PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE"
assert len(audit["ledgers"])==72
calc_path=Path("/home/xflops/coin-state/task-progress")/("task-"+audit["independent_task_id"]+".json")
calc=read(calc_path)
assert calc["status"]=="failed" and calc["exit_code"]==1
assert sha(audit["independent_source"])==audit["independent_source_sha256"]
actual=read(audit["actual_report_path"])
assert sha(audit["actual_report_path"])==audit["actual_report_sha256"]
assert {p:sha(ROOT/p) for p in audit["verified_source_hashes"]}==audit["verified_source_hashes"]
assert actual["completed_ledgers"]==72 and actual["all_planned_ledgers_complete"]
profiles=[]
for strategy in actual["binding"]["strategies"]:
    for spread in (2,4,8):
        rows=[x for x in audit["ledgers"] if x["strategy"]==strategy and x["spread_bps"]==spread]
        assert len(rows)==4
        gross_positive=[max(0.,float(x["gross_PnL_same_quantities"])) for x in rows]
        total_positive=sum(gross_positive)
        profiles.append({"strategy":strategy,"spread_bps":spread,
            "mean7day_net_return":sum(float(x["net_return"]) for x in rows)/4,
            "worst7day_net_return":min(float(x["net_return"]) for x in rows),
            "worst_observed_minute_MDD":max(float(x["minute_MDD"]) for x in rows),
            "max_realized_7day_annualized_vol":max(float(x["descriptive_7day_daily_annual_vol"]) for x in rows),
            "max_minute_gross_weight":max(float(x["max_minute_gross_weight"]) for x in rows),
            "net_positive_folds":sum(float(x["net_return"])>0 for x in rows),
            "total_fee_and_execution_cost":sum(float(x["fees"])+float(x["execution_costs"]) for x in rows),
            "top1_positive_gross_fold_share":max(gross_positive)/total_positive if total_positive else None})
v2=read(ROOT/"reports/fast_research/SIMPLE_STRATEGY_COMPARISON_TINY_20261002_V2.json")
xml=ET.parse(Path(v2["run_dir"])/"junit.xml").getroot()
public_case=[t for t in xml.iter("testcase") if t.attrib["name"]=="test_public_null_guard_valid_snapshot_equivalence"]
assert len(public_case)==1 and not list(public_case[0])
execution_receipt_path=ROOT/"reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_EXIT_20261002_V3.json"
if execution_receipt_path.exists():
    audit["root_actual_execution_receipt"]={"path":str(execution_receipt_path),"sha256":sha(execution_receipt_path)}
differences=[float(x["day_concentration_absolute_difference"]) for x in audit["ledgers"] if x["day_concentration_absolute_difference"] is not None]
owned=sum(p.stat().st_size for p in Path(actual["run_dir"]).rglob("*") if p.is_file())
assert owned==actual["owned_bytes"] and owned<=512000000
audit.update(version="SIMPLE_STRATEGY_COMPARISON_INDEPENDENT_ACTUAL_AUDIT_20261002_V3_R4",
 status="PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE_EXPORT_RECOVERED",
 created_utc=datetime.now(UTC).isoformat(),aggregate=profiles,completed_ledgers_verified=72,
 common_parameters_unchanged=True,resource_owned_bytes=owned,
 market_model_fits=0,original_market_source_files_read=False,allowed_derivative_market_outputs_read=True,
 locked_consumed=False,orders_sent=0,candidate_status="NO_QUALIFIED_CANDIDATE",
 economic_qualification="NOT_EVALUATED_NO_LONG_TERM_OR_UNSEEN_EVIDENCE",
 concentration_ratio_max_absolute_difference=max(differences),concentration_ratio_absolute_tolerance=1e-10,
 public_NULL_guard_closed={"source_path":"scripts/research_v8/public_donchian_adapter.py",
  "source_sha256":audit["verified_source_hashes"]["scripts/research_v8/public_donchian_adapter.py"],
  "actual_V2_public_case_passed":True,"V2_overall_FAIL_retained":True,"old_standalone_FAIL_retained":True},
 export_recovery={"cause":"Final json.dump failed on NumPy int64 profile count after all72 accounting/aggregate/source/resource checks and status assignment.",
  "original_partial_report_path":str(partial),"original_partial_report_sha256":sha(partial),
  "original_partial_report_is_valid_JSON":False,"original_partial_is_not_accepted_PASS_evidence":True,
  "complete_ledgers_array_recovered":72,"calculation_task_path":str(calc_path),"calculation_task_sha256":sha(calc_path),"calculation_task":calc,
  "calculation_task_actual_exit_code":1,"recovery_source":str(Path(__file__)),"recovery_source_sha256":sha(__file__),
  "scope":"Recover complete72 verified ledger records and rebuild18 derived profile aggregates from those records; never reopen Parquets or rerun market strategies, green tests, or21fill precheck.",
  "recovered_arrays_sha256":hashlib.sha256(json.dumps(audit["ledgers"],sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()},
 limits=["Accounting, causal proxy timing, common funding/cost/periods and complete output grid PASS; not profit or alpha qualification.",
  "Same actual quantities gross-cost identity is not a reoptimized zero-cost strategy.",
  "Minute open and previous-minute quote-volume are proxies; no BBO, queue, historical account-tier or executable-fill proof.",
  "Intent-event risk scaling permits passive drift; realized volatility/exposure differ across strategies and are disclosed per ledger.",
  "Daily/minute observed marks and only four already inspected7day windows do not establish long-term risk-constrained net CAGR.",
  "Five-rule96-endpoint equality/future perturbation use bound V3 one-case output; old six cases and21fills not rerun.",
  "Original market-source QA/model training not repeated; only permitted derivative minute source and actual output ledgers were read.",
  "All failed/import/chunk-layout/strictfloat/export attempts preserved; final recovery task confirms export, not a second market replay."],
 registry_appended_by_auditor=False)
out=ROOT/"reports/fast_research/SIMPLE_STRATEGY_COMPARISON_INDEPENDENT_ACTUAL_AUDIT_20261002_V3_R4.json"
with out.open("x") as f:
    json.dump(audit,f,indent=2,ensure_ascii=False,allow_nan=False)
    f.write(chr(10))
print(json.dumps({"status":audit["status"],"path":str(out),"sha256":sha(out),"verified_ledgers":72,
 "max_concentration_ratio_error":max(differences),"spread4_profiles":[p for p in profiles if p["spread_bps"]==4]}))