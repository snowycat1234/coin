"""Independent actual output accounting; no raw source read or strategy rerun."""
from pathlib import Path
from datetime import UTC, date, datetime
import hashlib, json, os, sys, resource, traceback
import xml.etree.ElementTree as ET
import numpy as np
import polars as pl
ROOT=Path("/mnt/d/codex/coin")
STATE=Path("/home/xflops/coin-state/test-simple-strategy-continuous-90d-audit-20261002-v2")
MIN=60_000_000
DAY=86_400_000_000
SYMS=("BTCUSDT","ETHUSDT")
actual_path=ROOT/"reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json"
out_path=ROOT/"reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_INDEPENDENT_ACTUAL_AUDIT_20261002_V2.json"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def need(ok,msg):
    if not bool(ok): raise ValueError(msg)
def close(a,b,atol=1e-6): return np.allclose(a,b,rtol=0,atol=atol,equal_nan=False)
def json_scalar(x):
    if isinstance(x,np.generic): return x.item()
    raise TypeError('Unsupported audit JSON type: '+type(x).__name__)

def frame_sha(frame): return hashlib.sha256(json.dumps(frame.to_dicts(),sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def stamp(text): return int(datetime.combine(date.fromisoformat(text),datetime.min.time(),UTC).timestamp())*1_000_000
def task_for(binding):
    p=Path("/home/xflops/coin-state/task-progress")/("task-"+binding["task_id"]+".json")
    t=read(p)
    need(t["id"]==binding["task_id"] and t["status"]=="completed" and t["exit_code"]==0 and t["pid"]>0 and t["start_ticks"]>0,"Actual task not completed0")
    return {"path":str(p),"sha256":sha(p),"task":t}
r=read(actual_path)
binding=read(Path(r["run_dir"])/"RUN_BINDING.json")
spec=read(ROOT/"protocols/PUBLIC_STRATEGY_CONTINUOUS_90D_V2.json")
hashes=binding["source_hashes"]
audit={"version":"PUBLIC_STRATEGY_CONTINUOUS_90D_INDEPENDENT_ACTUAL_AUDIT_20261002_V2",
       "status":"FAIL_ACTUAL_PROXY_LEDGER_AUDIT","created_utc":None,"actual_report_path":str(actual_path),
       "actual_report_sha256":sha(actual_path),"actual_host_session_id":4852,
       "verified_source_hashes":hashes,"independent_task_id":os.environ.get("COIN_TASK_ID"),
       "independent_source":str(Path(__file__)),"independent_source_sha256":sha(__file__),
       "reused_checker_source":"docs/archive/SIMPLE_STRATEGY_CONTINUOUS_122D_AUDIT_CHECKER_20261002_V1.py",
       "reused_checker_sha256":"6c11e6a651fdab6faa79e94edb435e8d81faa7f99bbb49dea876e14a99db259b",
       "checker_adjustments":["15 continuous90day accounts; same accounting math; oldpublic/engine causality and oldledgers not rerun", "IPC canonical rechunk", "Explicit money/qty/ratio tolerances retained", "NumPy scalar JSON normalization", "Monthly ongoing-position MTM; no account resets"],
       "python":sys.executable,"sys_prefix":sys.prefix,"ledgers":[]}
try:
    need(sha(actual_path)=="7e47d20fb71a8c6f87cc5b1adc26a2e031bb9bdbd8cf1a64d61ab6b4ac25642c", "Frozen reported actual bytes")
    need(sha(ROOT/audit["reused_checker_source"])==audit["reused_checker_sha256"], "Reuse checker bytes")
    need(binding==r["binding"] and sha(Path(r["run_dir"])/"RUN_BINDING.json")==r["run_binding_sha256"],"Actual binding bytes")
    need(r["status"]=="COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING" and r["completed_ledgers"]==15 and r["all_planned_ledgers_complete"],"Actual report incomplete")
    need(binding["planned_ledgers"]==15 and binding["strategies"]==spec["strategy_ids"] and binding["all_folds"]==spec["folds"], "Bound continuous fixed recipes")
    need(binding["fits"]==0 and r["market_models_fit"]==0 and r["locked_consumed"] is False and r["orders_sent"]==0
        and r["candidate_status"]=="NO_QUALIFIED_CANDIDATE" and r["account_continuity"]=="SINGLE_CONTINUOUS_PERIOD_BY_STRATEGY_AND_COST", "Qualification/continuous account scope")
    need(spec["planned_ledgers"]==15 and spec["warmup_days"]==31 and len(spec["folds"])==1
        and spec["folds"][0]=={"id":"CONT90","period_start":"2025-12-01","period_end_exclusive":"2026-03-01"}, "Exact frozen90day dates")
    audit["actual_task"]=task_for(binding)
    need({p:sha(ROOT/p) for p in hashes}==hashes,"Current dependency bytes changed")
    need(all(sha(Path(r["run_dir"])/"source-snapshot"/p)==d for p,d in hashes.items()),"Actual snapshot mismatch")
    need(all(hashes.get(p)==d for p,d in spec["frozen_sources"].items()),"Contract hashes not exact")
    need(binding["protocol_sha256"]==sha(ROOT/"protocols/PUBLIC_STRATEGY_CONTINUOUS_90D_V2.json")
        and "--protocol /mnt/d/codex/coin/protocols/PUBLIC_STRATEGY_CONTINUOUS_90D_V2.json" in binding["exact_command"],"Exact90day protocol")
    tiny_path=ROOT/spec["required_smoke_receipt"]
    tiny=read(tiny_path)
    tb=read(Path(tiny["run_dir"])/"RUN_BINDING.json")
    need(tb==tiny["binding"] and tb["source_hashes"]==hashes and sha(tiny_path)==r["accepted_smoke_sha256"],"Actual/tiny exact source pairing")
    audit["actual_tiny_task"]=task_for(tb)
    x=ET.parse(Path(tiny["run_dir"])/"junit.xml").getroot()
    counts={k:sum(int(s.get(k,0)) for s in x.iter("testsuite")) for k in ("tests","failures","errors","skipped")}
    need(counts=={"tests":1,"failures":0,"errors":0,"skipped":0}
        and sha(Path(tiny["run_dir"])/"junit.xml")==tiny["junit_sha256"],"One new bound terminal-close signal-view test")
    case_names=sorted(c.attrib["name"] for c in x.iter("testcase"))
    need(case_names==["test_final_close_metadata_only_after_last_decision_and_marks_preserved"], "Exact targeted smoke output cases")
    audit["checked_existing_smoke_output_cases"]=case_names
    audit["actual_tiny"]={"path":str(tiny_path),"sha256":sha(tiny_path),"counts":counts,"scope":"One new terminal-close signal-view boundary/equivalence case; prior source-scope test remains bound separately and is not rerun."}
    old_source_tiny_path=ROOT/"reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_TINY_20261002_V1.json"
    old_source_tiny=read(old_source_tiny_path)
    need(sha(old_source_tiny_path)=="7dab6b867c9e1fb9efbc8b5a11c6bd3c7b1d296819b6de59003072002c13caa6"
        and old_source_tiny["status"]=="PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT", "Preserved passing source-scope output")
    old_st_binding_path=Path(old_source_tiny["run_dir"])/"RUN_BINDING.json"
    old_st_binding=read(old_st_binding_path)
    need(old_st_binding==old_source_tiny["binding"] and sha(old_st_binding_path)==old_source_tiny["run_binding_sha256"], "Preserved source tiny binding")
    audit["preserved_source_scope_tiny_actual_task"]=task_for(old_st_binding)
    old_xml=Path(old_source_tiny["run_dir"])/"junit.xml"
    old_x=ET.parse(old_xml).getroot()
    old_counts={k:sum(int(s.get(k,0)) for s in old_x.iter("testsuite")) for k in ("tests","failures","errors","skipped")}
    need(old_counts=={"tests":1,"failures":0,"errors":0,"skipped":0}
        and [c.attrib["name"] for c in old_x.iter("testcase")]==["test_two_fixed_source_scopes_and_exclusive_locked_boundary"]
        and sha(old_xml)==old_source_tiny["junit_sha256"],"Original source-case output, not rerun")
    repair=spec["failure_compatibility_repair"]
    old_fail_path=ROOT/repair["failed_actual_path"]
    old_fail=read(old_fail_path)
    need(sha(old_fail_path)==repair["failed_actual_sha256"]=="87b3612321539b6fe8c408270efd8c8dee09ccae15489bef94fc5a751a7a6491"
        and old_fail["status"]=="FAIL_SIMPLE_STRATEGY_COMPARISON"
        and old_fail["reason"]=="close_us: development dates only; locked timestamps forbidden"
        and len(old_fail["folds"])==1 and len(old_fail["folds"][0]["results"])==3,"Original real V1 failure retained")
    old_fail_binding_path=Path(old_fail["run_dir"])/"RUN_BINDING.json"
    old_fail_binding=read(old_fail_binding_path)
    need(old_fail_binding==old_fail["binding"] and sha(old_fail_binding_path)==old_fail["run_binding_sha256"],"Original failed actual binding")
    old_fail_task_path=Path("/home/xflops/coin-state/task-progress")/("task-"+old_fail_binding["task_id"]+".json")
    old_fail_task=read(old_fail_task_path)
    need(old_fail_task["id"]=="dff742017bd64a09929b3e801bf05100" and old_fail_task["status"]=="failed"
        and old_fail_task["exit_code"]==1 and old_fail_task["pid"]>0 and old_fail_task["start_ticks"]>0,"Actual V1 failed1 evidence")
    need(sha(Path(old_fail["run_dir"])/"source-snapshot/scripts/investment/compare_simple_strategies.py")
        ==repair["original_code_source_sha256"]=="2ae031d4601833203d9709c0a29da0a603cf3a54a072fa24cd12cc3754bcfd09", "Frozen failed V1 source")
    audit["preserved_V1_failure"]={"path":str(old_fail_path),"sha256":sha(old_fail_path),"status":old_fail["status"],
        "reason":old_fail["reason"],"task_path":str(old_fail_task_path),"task_sha256":sha(old_fail_task_path),
        "actual_task":old_fail_task,"partial_cash_artifact_records":3,"market_return_classification":"NOT_AN_ECONOMIC_NEGATIVE_RESULT_ENGINEERING_COMPATIBILITY_FAILURE",
        "partial_ledger_arrays_read_or_recomputed":0}
    audit["preserved_source_scope_tiny"]={"path":str(old_source_tiny_path),"sha256":sha(old_source_tiny_path),"counts":old_counts,"rerun":False}
    audit["new_compatibility_repair_static_scope"]={"status":"PASS_THIN_SIGNAL_CLOSE_VIEW_DIFF_ONLY",
        "changed":"Only bulk signal close view clips close_us<=lastdecision; prior values/complete execution bars/minute grids/NAV marks remain unchanged",
        "new_target_parameters_or_fees":False,"public_adapter_engine_benchmark_bulk_bytes_changed":False,
        "last_February_source_open":"2026-02-28T23:59:00Z","exclusive_close_and_valuation":"2026-03-01T00:00:00Z",
        "last_signal_decision":"2026-02-28T23:59:00Z","signal_does_not_include_after_last_decision_close":True,
        "additional_independent_probe":False,"bound_new_tiny_case":"test_final_close_metadata_only_after_last_decision_and_marks_preserved"}
    source_receipt_path=ROOT/spec["source_receipt"]
    source_receipt=read(source_receipt_path)
    need(sha(source_receipt_path)==spec["source_receipt_sha256"]=="388d3be0611c038df2f955a88c5be822e17d6cbda5f265fdef101f6abe23d8a2", "Accepted source metadata bytes")
    months=["2025-10","2025-11","2025-12","2026-01","2026-02"]
    need(spec["source_scope"]=="OCT2025_FEB2026" and spec["source_calendar"]==months and spec["source_days_per_symbol"]==151
        and r["source_scope"]==spec["source_scope"] and r["source_calendar"]==months and r["source_days_per_symbol"]==151
        and r["source_month_files"]==10,"Real source scope fields")
    need(source_receipt["status"]=="PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_151D_CALENDAR"
        and source_receipt["source_files"]==10 and source_receipt["days_per_symbol"]==151
        and source_receipt["actual_minute_rows"]==434880
        and source_receipt["binding"]["spec"]["source_scope"]==spec["source_scope"]
        and source_receipt["binding"]["spec"]["source_calendar"]==months,"Accepted metadata calendar")
    need(all(source_receipt[p] is False for p in ("market_price_rows_or_model_results_read","locked_consumed","aggregated_bars_read",
        "source_modified","new_source_downloaded","original_CSV_or_ZIP_body_decompressed")),"Metadata-only source receipt scope")
    source_binding_path=Path(source_receipt["run_binding_path"])
    need(sha(source_binding_path)==source_receipt["run_binding_sha256"] and read(source_binding_path)==source_receipt["binding"],"Source metadata RUN_BINDING")
    records=source_receipt["sources"]
    need(len(records)==10 and {(x["symbol"],x["month"]) for x in records}=={(s,m) for s in SYMS for m in months},"Ten exact normalized inputs; noMarch")
    for record in records:
        expected_path=ROOT/"data/normalized/spot"/record["symbol"]/"1m"/(record["month"]+".parquet")
        need(Path(record["normalized_path"]).resolve()==expected_path.resolve()
            and expected_path.resolve().is_relative_to(ROOT.resolve()),"Canonical normalized path metadata")
        first=stamp(record["month"]+"-01")
        y,m=map(int,record["month"].split("-"))
        last=stamp(str(y+m//12)+"-"+str(m%12+1).zfill(2)+"-01")
        rows=(last-first)//MIN
        quality=record["old_quality"]
        need(record["rows"]==rows and quality["rows"]==rows and quality["expected_rows"]==rows
            and quality["first_open_us"]==first and quality["last_open_us"]==last-MIN
            and all(quality[p]==0 for p in ("missing_rows","duplicate_rows","bad_timestamps","bad_values","gaps","quarantined_rows"))
            and not quality["incomplete_days"] and not quality["quarantined_days"],"Frozen prior QA coverage metadata")
    boundary_path=ROOT/"reports/fast_research/PUBLIC_DONCHIAN_2H_INDEPENDENT_BOUNDARY_AUDIT_20261002_V1.json"
    boundary=read(boundary_path)
    need(sha(boundary_path)=="3ddce1e4858b67c837d64533f45ca6cff77b404c5ff83c28c24af352d4a68114"
        and boundary["status"]=="PASS_2H_STATIC_AND_EXACT_WARMUP_BOUNDARY_ONLY"
        and hashes["scripts/research_v8/public_donchian_adapter.py"]==boundary["verified_source_hashes"]["scripts/research_v8/public_donchian_adapter.py"]
        =="169d7ba6ebde24be5ce4730c5e741ed281a0155e4cadc22f1bb2bedccb4093c2", "Existing2h causal guard implementation reused")
    audit["reused_public_boundary"]={"path":str(boundary_path),"sha256":sha(boundary_path),"rerun":False}
    audit["source_guard_static_scope"]={"status":"PASS_FROZEN_PROTOCOL_AND_NEW_TINY_OUTPUT_SCOPE",
        "source_scope":"OCT2025_FEB2026","source_calendar":months,"accepted_month_files":10,"accepted_source_days_per_symbol":151,
        "source_receipt_sha256":sha(source_receipt_path),"source_metadata_binding_sha256":sha(source_binding_path),
        "guard_order":"Fixed scope/exactsymbol-month/path/receiptcoverage/warmup verified before original market-file hash or Parquetread. Frozen protocol dependencies contain no raw/Marchinputs.",
        "source_metadata_execution_task_id":"NOT_CAPTURED_IN_ACCEPTED_SOURCE_RECEIPT; no task fabricated",
        "raw_source_hash_or_price_QA_repeated_by_auditor":False,"new_independent_source_probes":0,
        "reason_no_extra_probe":"PreservedV1 source-scope output and newV2 terminal-close view case cover changed boundaries; no concrete additional gap found statically."}
    source_path=Path(r["minute_source"]["path"])
    need(source_path==Path(r["run_dir"])/"shared_source_minutes.parquet" and sha(source_path)==r["minute_source"]["sha256"],"Derivative source SHA")
    minutes=pl.read_parquet(source_path)
    need(np.all((minutes["open_us"].to_numpy()>=stamp("2025-10-31")) & (minutes["open_us"].to_numpy()<stamp("2026-03-01"))),"No locked Marchminute in derivative")
    need(minutes.height==r["minute_source"]["rows"] and r["minute_source"]["invalid_minutes"]==0,"Derivative source row counts")
    need(set(minutes["symbol"].unique().to_list())==set(SYMS) and minutes["minute_valid"].null_count()==0 and minutes["minute_valid"].all(),"Unknown/invalid minute admitted")
    need(all(minutes[p].null_count()==0 and minutes.schema[p]==pl.Int64 for p in ("open_us","close_us","available_us")),"Unknown integer availability source")
    need(np.array_equal(minutes["available_us"].to_numpy(),minutes["close_us"].to_numpy()) and np.array_equal(minutes["close_us"].to_numpy(),minutes["open_us"].to_numpy()+MIN),"Availability not exclusive source close")
    need(minutes["valid_day"].null_count()==0 and minutes["valid_day"].all() and minutes["missing_reason"].null_count()==minutes.height,"Invalid source flags")
    audit["derivative_source"]={"path":str(source_path),"sha256":sha(source_path),"rows":minutes.height,"known_availability_rows":minutes.height,"invalid_minutes":0,"original_market_source_files_read":False}
    seen=set()
    profiles=[]
    for fold in r["folds"]:
        fc=next(f for f in spec["folds"] if f["id"]==fold["fold"])
        start,end=stamp(fc["period_start"]),stamp(fc["period_end_exclusive"])
        need(fold["start_us"]==start and fold["end_us"]==end and fold["status"]=="COMPLETE_PROXY_COMPARISON" and len(fold["results"])==15,"Fold/calendar scope")
        fm=minutes.filter(pl.col("open_us").is_between(start-31*DAY,end,closed="left"))
        need(hashlib.sha256(fm.rechunk().write_ipc(None).getvalue()).hexdigest()==fold["minute_input_sha256"],"Fold input bytes")
        per={}
        for symbol in SYMS:
            m=fm.filter(pl.col("symbol")==symbol)
            need(np.array_equal(m["open_us"].to_numpy(),np.arange(start-31*DAY,end,MIN,dtype=np.int64)),"Incomplete warmup/evaluation minute grid")
            per[symbol]=m.filter(pl.col("open_us")>=start)
        close_times=per[SYMS[0]]["close_us"].to_numpy()
        target_bound={}
        for strategy in spec["strategy_ids"]:
            d=Path(r["run_dir"])/(fold["fold"]+"-"+strategy)
            targets=pl.read_parquet(d/"targets.parquet")
            intent=pl.read_parquet(d/"intent_calendar.parquet")
            target_receipt=read(d/"target_receipt.json")
            need(target_receipt["paired_comparison_allowed"] and not target_receipt["warmup_failed"],"Target status")
            need(target_receipt["targets_sha256"]==frame_sha(targets),"Target receipt values")
            expected=[]
            for symbol in SYMS:
                one=intent.filter(pl.col("symbol")==symbol).sort("decision_us")
                times=one["decision_us"].to_numpy()
                w=one["target_weight"].to_numpy()
                need(np.array_equal(times,np.arange(start,end,MIN,dtype=np.int64))
                    and np.array_equal(one["available_us"].to_numpy(),times)
                    and np.array_equal(one["comparison_order_eligible_us"].to_numpy(),times+MIN),"Same complete intent calendar")
                need(np.isfinite(w).all() and np.all((w>=0)&(w<=.3)) and w[-1]==0,"Target sizing")
                changed=np.r_[True,np.diff(w)!=0]
                expected.extend({"available_us":int(t),"symbol":symbol,"target_weight":float(v)} for t,v in zip(times[changed],w[changed]))
            reconstructed=pl.DataFrame(expected).sort(["available_us","symbol"])
            need(targets.sort(["available_us","symbol"]).equals(reconstructed),"Compressed targets differ from intent")
            target_bound[strategy]={"target_sha256":sha(d/"targets.parquet"),"intent_sha256":sha(d/"intent_calendar.parquet"),"receipt_sha256":sha(d/"target_receipt.json")}
        for item in fold["results"]:
            strategy,spread=item["strategy"],item["spread_bps"]
            key=(fold["fold"],strategy,spread)
            need(key not in seen and strategy in spec["strategy_ids"] and spread in (2,4,8),"Missing/duplicate recipe")
            seen.add(key)
            d=Path(item["directory"])
            need(d==Path(r["run_dir"])/(fold["fold"]+"-"+strategy)/("spread"+str(spread)),"Explicit ledger path")
            need(set(item["artifacts"])=={"daily_nav.parquet","trades.parquet","orders.parquet","round_trips.parquet","minute_nav_inventory.parquet","config_and_summary.json"},"Complete ledger artifacts")
            for name,b in item["artifacts"].items():
                need(sha(d/name)==b["sha256"] and (d/name).stat().st_size==b["bytes"],"Ledger artifact changed")
            book=read(d/"config_and_summary.json")
            cfg=book["config"]
            summary=book["summary"]
            published=item["summary"]
            expected_cfg={"initial_cash":10000.,"fee_bps":10.,"half_spread_bps":spread/2,"slippage_bps":4.,
                "fee_multiplier":1.,"slippage_multiplier":1.,"latency_minutes":1,"start_us":start,"end_us":end,
                "max_weight":.3,"max_gross":.6,"target_annual_vol":.1,"vol_window_days":30,"min_vol_days":20,
                "participation_rate":.001,"max_order_wait_minutes":5,"liquidate_at_end":True,"min_notional":10.,
                "lot_step_by_symbol":{"BTCUSDT":.00001,"ETHUSDT":.0001}}
            need(cfg==expected_cfg,"Actual parameters changed")
            need(all(published[k]==v for k,v in summary.items()),"Published base summary differs")
            fills=pl.read_parquet(d/"trades.parquet").sort("execution_us",maintain_order=True)
            inventory=pl.read_parquet(d/"minute_nav_inventory.parquet")
            daily=pl.read_parquet(d/"daily_nav.parquet")
            orders=pl.read_parquet(d/"orders.parquet")
            need(np.array_equal(inventory["close_us"].to_numpy(),close_times) and inventory.height==90*1440,"Full minute inventory")
            t=fills["execution_us"].to_numpy()
            sign=np.where(fills["side"].to_numpy()=="buy",1.,-1.)
            need(fills["side"].is_in(["buy","sell"]).all() and fills["symbol"].is_in(SYMS).all(),"Illegal fill identity")
            q=fills["quantity"].to_numpy()
            mid=fills["mid_price"].to_numpy()
            fill_price=fills["fill_price"].to_numpy()
            notionals=fills["notional"].to_numpy()
            fees=notionals*.001
            extra=q*np.abs(fill_price-mid)
            need(np.isfinite(q).all() and np.all(q>0) and close(notionals,q*fill_price)
                and close(fills["fee"].to_numpy(),fees) and close(fills["execution_cost"].to_numpy(),extra),"Actual fill costs")
            need(close(fill_price,mid*(1+sign*(spread/2+4)/10000)),"Cost scenario fill proxy")
            if len(t):
                sig=fills["signal_us"].to_numpy()
                eligible=((sig+MIN-1)//MIN+1)*MIN+1
                need(np.all(t>=eligible)&np.all(t%MIN==1)&np.all(t<end),"Future/period fill")
                cash_steps=10000.-np.cumsum(sign*notionals+fees)
                need(close(cash_steps,fills["cash_after"].to_numpy(),1e-7),"Sequential cash identity")
            else:
                cash_steps=np.empty(0)
            counts=np.searchsorted(t,close_times,side="right")
            def acc(v): return np.r_[0.,np.cumsum(v)][counts]
            cash=10000.-acc(sign*notionals+fees)
            gross_cash=10000.-acc(sign*q*mid)
            nav=cash.copy()
            gross_nav=gross_cash.copy()
            quantities={}
            symbol_values=[]
            fill_nav=10000.-np.cumsum(sign*notionals+fees)
            fill_after_positions=[]
            for symbol in SYMS:
                mask=fills["symbol"].to_numpy()==symbol
                qty=acc(sign*q*mask)
                values=qty*per[symbol]["close"].to_numpy()
                quantities[symbol]=qty
                symbol_values.append(values)
                nav+=values
                gross_nav+=values
                need(np.all(qty>=-1e-9) and close(qty,inventory[symbol+"_quantity"].to_numpy(),1e-8)
                    and close(values,inventory[symbol+"_marked_notional"].to_numpy()),"Quantity/mark identity")
                need(abs(qty[-1]-summary["open_positions"][symbol])<1e-8,"Terminal quantity omitted")
                if len(t):
                    index=(t-1-start)//MIN
                    opens=per[symbol]["open"].to_numpy()
                    prequotes=fm.filter(pl.col("symbol")==symbol)["quote_volume"].to_numpy()
                    fill_nav+=np.cumsum(sign*q*mask)*opens[index]
                    own=np.flatnonzero(mask)
                    need(close(mid[mask],opens[index[mask]],1e-8),"Fill not actual minute-open proxy")
                    capacities=prequotes[index[mask]+31*1440-1]*.001
                    need(close(capacities,fills["capacity"].to_numpy()[mask])
                        and np.all(notionals[mask]<=capacities+1e-7)
                        and np.all(notionals[mask]>=10-1e-7),"Zero/future capacity or minnotional")
                    need(np.all(np.abs(q[mask]/cfg["lot_step_by_symbol"][symbol]-np.round(q[mask]/cfg["lot_step_by_symbol"][symbol]))<1e-5),"Lot filter")
                    need(np.array_equal(fills["capacity_open_us"].to_numpy()[mask],t[mask]//MIN*MIN-MIN),"Capacity minute identity")
            need(close(nav,inventory["nav"].to_numpy()) and close(cash,inventory["cash"].to_numpy())
                and close(gross_nav,inventory["gross_marked_nav_same_quantities"].to_numpy())
                and close(gross_nav-acc(fees+extra),nav) and np.all(cash>=-1e-7),"Minute NAV cash/gross-cost identity")
            need(close(acc(fees),inventory["cumulative_fee"].to_numpy()) and close(acc(extra),inventory["cumulative_execution_cost"].to_numpy()),"Minute cost accumulation")
            need(close(fill_nav,fills["nav_after"].to_numpy()),"Per-fill NAV at both symbol open marks")
            daily_mask=close_times%DAY==0
            dn=nav[daily_mask]
            dr=dn/np.r_[10000.,dn[:-1]]-1
            need(len(dn)==90 and close(dn,daily["nav"].to_numpy()) and close(dr,daily["return"].to_numpy()),"UTC daily NAV/returns")
            fee_day=np.bincount((t//DAY-start//DAY).astype(int),weights=fees,minlength=90)
            cost_day=np.bincount((t//DAY-start//DAY).astype(int),weights=extra,minlength=90)
            notional_day=np.bincount((t//DAY-start//DAY).astype(int),weights=notionals,minlength=90)
            need(close(fee_day,daily["fees"].to_numpy()) and close(cost_day,daily["execution_costs"].to_numpy())
                and close(notional_day/np.r_[10000.,dn[:-1]],daily["turnover"].to_numpy()),"Daily fees/cost/turnover")
            normalized_turnover=float((notional_day/np.r_[10000.,dn[:-1]]).sum())
            need(close(summary["turnover"],normalized_turnover,1e-10),"Total daily-normalized turnover")
            net=nav[-1]-10000.
            gross=net+fees.sum()+extra.sum()
            mdd=float(-np.min(np.r_[10000.,nav]/np.maximum.accumulate(np.r_[10000.,nav])-1))
            dmdd=float(-np.min(np.r_[10000.,dn]/np.maximum.accumulate(np.r_[10000.,dn])-1))
            vol=float(np.std(dr,ddof=1)*np.sqrt(365))
            gw=np.sum(symbol_values,axis=0)/nav
            weights={s:symbol_values[i]/nav for i,s in enumerate(SYMS)}
            positive=np.maximum(dn-np.r_[10000.,dn[:-1]]+fee_day+cost_day,0)
            concentration=float(positive.max()/positive.sum()) if positive.sum() else None
            need(abs(nav[-1]-summary["final_nav"])<1e-6 and abs(net-published["net_cash_PnL"])<1e-6
                and abs(gross-published["gross_cash_PnL_same_quantities"])<1e-6
                and abs(mdd-published["max_observed_minute_MDD"])<1e-12
                and abs(dmdd-summary["max_drawdown"])<1e-12
                and abs(vol-summary["annual_volatility"])<1e-12
                and abs(gw.max()-published["max_minute_marked_gross_weight"])<1e-12,"Published PnL/risk differs")
            need((concentration is None and published["top1_day_positive_gross_PnL_share"] is None) or (concentration is not None and published["top1_day_positive_gross_PnL_share"] is not None and abs(concentration-published["top1_day_positive_gross_PnL_share"])<=1e-10),"Positive gross day concentration")
            need(np.all(fills.filter(pl.col("side")=="buy")["asset_weight_after"].to_numpy()<=.3+1e-9)
                and np.all(fills.filter(pl.col("side")=="buy")["gross_weight_after"].to_numpy()<=.6+1e-9),"New buy exceeds actual postcost caps")
            need(published["candidate_qualification_allowed"] is False and published["real_BBO"] is False
                and published["capacity_proven"] is False and published["net_long_term_CAGR_proven"] is False,"Proxy scope overstated")
            annual=float((nav[-1]/10000.)**(365/90)-1)
            need(summary["days"]==90 and abs(summary["total_return"]-net/10000.)<1e-12
                and abs(summary["annual_return"]-annual)<1e-12 and published["period_days"]==90
                and close(published["period_net_return"],net/10000.,1e-12)
                and close(published["period_descriptive_net_CAGR"],annual,1e-12)
                and published["annualized_return_is_descriptive_only"] is True, "122day descriptive return fields")
            month_rows=[]
            previous_nav=10000.
            previous_gross_nav=10000.
            for month,lower,upper in (("2025-12",stamp("2025-12-01"),stamp("2026-01-01")),
                    ("2026-01",stamp("2026-01-01"),stamp("2026-02-01")),
                    ("2026-02",stamp("2026-02-01"),stamp("2026-03-01"))):
                day_indices=np.flatnonzero((close_times[daily_mask]>lower)&(close_times[daily_mask]<=upper))
                indices=np.flatnonzero((close_times>lower)&(close_times<=upper))
                fill_indices=(t>=lower)&(t<upper)
                last=int(indices[-1])
                mn=float(nav[last])
                mg=float(gross_nav[last])
                mf=float(fees[fill_indices].sum())
                mc=float(extra[fill_indices].sum())
                mp=float(mn-previous_nav)
                gp=float(mg-previous_gross_nav)
                need(close(gp-mp,mf+mc), "Monthly ongoing positions gross-cost identity")
                mv=float(np.std(dr[day_indices],ddof=1)*np.sqrt(365))
                mnav=np.r_[previous_nav,nav[indices]]
                mmdd=float(-np.min(mnav/np.maximum.accumulate(mnav)-1))
                end_quantities={s:float(quantities[s][last]) for s in SYMS}
                month_rows.append({"month":month,"days":int(len(day_indices)),"start_NAV":float(previous_nav),
                    "end_NAV":mn,"marked_net_return":float(mn/previous_nav-1),"net_PnL":mp,
                    "gross_PnL_same_quantities":gp,"fee":mf,"execution_cost":mc,
                    "trade_count":int(np.sum(fill_indices)),"turnover_notional_USDT":float(notionals[fill_indices].sum()),
                    "normalized_daily_turnover":float((notional_day/np.r_[10000.,dn[:-1]])[day_indices].sum()),"within_month_minute_MDD":mmdd,
                    "descriptive_daily_annual_vol":mv,"month_end_quantities":end_quantities,
                    "month_end_marked_notional":float(sum(v[last] for v in symbol_values)),
                    "cash_reset":False,"monthly_liquidation_assumed":False})
                previous_nav,previous_gross_nav=mn,mg
            need([m["days"] for m in month_rows]==[31,31,28] and close(sum(m["net_PnL"] for m in month_rows),net)
                and close(sum(m["fee"] for m in month_rows),fees.sum()) and close(sum(m["execution_cost"] for m in month_rows),extra.sum()), "Month totals do not close")
            positive_months=np.maximum([m["gross_PnL_same_quantities"] for m in month_rows],0.)
            positive_net_months=np.maximum([m["net_PnL"] for m in month_rows],0.)
            entry={"fold":fold["fold"],"strategy":strategy,"spread_bps":spread,
                "net_return":float(net/10000.),"net_PnL":float(net),"gross_PnL_same_quantities":float(gross),
                "fees":float(fees.sum()),"execution_costs":float(extra.sum()),"trade_count":fills.height,
                "turnover_notional_USDT":float(notionals.sum()),"normalized_daily_turnover":normalized_turnover,
                "minute_MDD":mdd,"daily_MDD":dmdd,"period_days":90,"descriptive_net_CAGR":annual,
                "months":month_rows,"net_positive_months":int(np.sum([m["net_PnL"]>0 for m in month_rows])),
                "top1_positive_gross_month_share":float(positive_months.max()/positive_months.sum()) if positive_months.sum() else None,
                "top1_positive_net_month_share":float(positive_net_months.max()/positive_net_months.sum()) if positive_net_months.sum() else None,"descriptive_90day_daily_annual_vol":vol,
                "max_minute_gross_weight":float(gw.max()),
                "max_minute_BTC_weight":float(weights["BTCUSDT"].max()),"max_minute_ETH_weight":float(weights["ETHUSDT"].max()),
                "passive_drift_symbol_cap_excess_minutes":int(np.sum((weights["BTCUSDT"]>.3+1e-9)|(weights["ETHUSDT"]>.3+1e-9))),
                "passive_drift_gross_cap_excess_minutes":int(np.sum(gw>.6+1e-9)),
                "day_concentration_absolute_difference":abs(concentration-published["top1_day_positive_gross_PnL_share"]) if concentration is not None else None,"day_concentration_absolute_tolerance":1e-10,"top1_positive_gross_day_share":concentration,
                "terminal_marked_notional":float(sum(v[-1] for v in symbol_values)),
                "cash_min":float(cash.min()),"target_bindings":target_bound[strategy],
                "ledger_artifact_hashes":{n:b["sha256"] for n,b in item["artifacts"].items()}}
            audit["ledgers"].append(entry)
    need(len(seen)==15 and seen=={(f["id"],s,b) for f in spec["folds"] for s in spec["strategy_ids"] for b in (2,4,8)},"Missing paired grids")
    aggregate=[]
    for strategy in spec["strategy_ids"]:
        for spread in (2,4,8):
            rows=[x for x in audit["ledgers"] if x["strategy"]==strategy and x["spread_bps"]==spread]
            need(len(rows)==1,"Continuous account must not stitch independent periods")
            one=rows[0]
            published=next(a for a in r["aggregate"] if a["strategy"]==strategy and a["spread_bps"]==spread)
            need(published["complete_periods"]==1 and published["period_lengths_days"]==[90]
                and close(published["period_net_return"],one["net_return"],1e-12)
                and close(published["mean_period_net_return"],one["net_return"],1e-12)
                and close(published["worst_period_net_return"],one["net_return"],1e-12)
                and close(published["fees_USDT_across_period_accounts"],one["fees"])
                and close(published["execution_cost_USDT_across_period_accounts"],one["execution_costs"])
                and close(published["max_observed_daily_MDD"],one["daily_MDD"],1e-12)
                and close(published["max_observed_minute_MDD"],one["minute_MDD"],1e-12)
                and published["trade_count"]==one["trade_count"],"Continuous aggregate mismatch")
            aggregate.append({k:one[k] for k in ("strategy","spread_bps","net_return","net_PnL","gross_PnL_same_quantities",
                "fees","execution_costs","trade_count","turnover_notional_USDT","normalized_daily_turnover","period_days","descriptive_net_CAGR","minute_MDD","daily_MDD",
                "descriptive_90day_daily_annual_vol","max_minute_gross_weight","max_minute_BTC_weight","max_minute_ETH_weight",
                "passive_drift_symbol_cap_excess_minutes","passive_drift_gross_cap_excess_minutes","top1_positive_gross_day_share",
                "net_positive_months","top1_positive_gross_month_share","top1_positive_net_month_share","terminal_marked_notional","cash_min")})
    comparisons=[]
    for spread in (2,4,8):
        one=next(x for x in audit["ledgers"] if x["strategy"]=="COIN_JESSE_DONCHIAN_1H_SPOT_ADAPTER" and x["spread_bps"]==spread)
        two=next(x for x in audit["ledgers"] if x["strategy"]=="COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER" and x["spread_bps"]==spread)
        comparisons.append({"spread_bps":spread,"nominal_roundtrip_bps":28+spread,
            "delta_net_PnL_2h_minus1h":float(two["net_PnL"]-one["net_PnL"]),
            "gross_retention_vs1h_actual_quantity_paths":float(two["gross_PnL_same_quantities"]/one["gross_PnL_same_quantities"]) if one["gross_PnL_same_quantities"]>0 else None,
            "normalized_turnover_ratio_2h_vs1h":float(two["normalized_daily_turnover"]/one["normalized_daily_turnover"]) if one["normalized_daily_turnover"]>0 else None,
            "cost_ratio_2h_vs1h":float((two["fees"]+two["execution_costs"])/(one["fees"]+one["execution_costs"])) if one["fees"]+one["execution_costs"]>0 else None,
            "trade_count_1h":one["trade_count"],"trade_count_2h":two["trade_count"],
            "risk":"Shared fixed mechanism/config; realized volatility/exposure differ. Not matched-risk alpha or unseen evidence."})
    audit["new90d_public1h_2h_comparisons"]=comparisons
    need({p:sha(ROOT/p) for p in hashes}==hashes and sha(actual_path)==audit["actual_report_sha256"],"Frozen outputs changed")
    owned=sum(p.stat().st_size for p in Path(r["run_dir"]).rglob("*") if p.is_file())
    need(r["owned_bytes"]<=owned<=spec["maximum_new_owned_bytes"],"Current total owned budget including additive post-run receipts")
    audit["resource_owned_bytes_at_actual_completion"]=r["owned_bytes"]
    audit["additional_owned_bytes_observed_after_actual_report"]=owned-r["owned_bytes"]
    need(r["resources"]["swap_bytes"]==0 and r["resources"]["gpu_used"] is False and r["resources"]["ram_limit_bytes"]<=5_000_000_000,"Shared budget")
    audit.update(status="PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE",aggregate=aggregate,
        completed_ledgers_verified=15,common_parameters_unchanged=True,resource_owned_bytes=owned,
        market_model_fits=0,original_market_source_files_read=False,allowed_derivative_market_outputs_read=True,
        locked_consumed=False,orders_sent=0,candidate_status="NO_QUALIFIED_CANDIDATE",
        proxy_economic_accounting="PASS_WITH_MINUTE_OPEN_AND_QUOTE_VOLUME_PROXY_LIMITS",
        economic_qualification="NOT_EVALUATED_NO_LONG_TERM_OR_UNSEEN_EVIDENCE",
        current_public_NULL_guard="CLOSED_BY_NEW_null_count_GUARD_AND_EXISTING_V2_PUBLIC_CASE; old standalone FAIL retained.",
        limits=["Accounting, causal proxy timing, common funding/cost/periods and complete output grid PASS; not profit/alpha qualification.",
          "Same actual quantities gross-cost identity is not a reoptimized zero-cost strategy.",
          "Minute open and previous-minute quote-volume are proxies; no BBO, queue, historical account-tier or actual executable-fill proof.",
          "Intent-event risk scaling permits passive drift; realized volatility/exposure differ across strategies and are disclosed per ledger.",
          "Continuous90days were previously consumed by A05/A06; later development chronology screening, not unseen or long-term qualification.",
          "Frozen public169d/engine retained; original source-scope output and one new terminal-close compatibility case bound; oldpublic/engine causality and oldmarket ledgers not rerun.",
          "No market model or original market-source QA rerun; only permitted derivative source/calendar and actual output ledgers read."],
        registry_appended_by_auditor=False)
except Exception as e:
    audit.update(error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc(),completed_ledgers_before_failure=len(audit["ledgers"]))
    raise
finally:
    audit.update(created_utc=datetime.now(UTC).isoformat(),peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    with out_path.open("x") as f:
        json.dump(audit,f,indent=2,ensure_ascii=False,allow_nan=False,default=json_scalar)
        f.write(chr(10))
    print(json.dumps({"status":audit["status"],"path":str(out_path),"sha256":sha(out_path),"verified_ledgers":len(audit["ledgers"]),"task_id":os.environ.get("COIN_TASK_ID")}))