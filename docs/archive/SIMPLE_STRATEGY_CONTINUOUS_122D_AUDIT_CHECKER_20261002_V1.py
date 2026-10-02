"""Independent actual output accounting; no raw source read or strategy rerun."""
from pathlib import Path
from datetime import UTC, date, datetime
import hashlib, json, os, sys, resource, traceback
import xml.etree.ElementTree as ET
import numpy as np
import polars as pl
ROOT=Path("/mnt/d/codex/coin")
STATE=Path("/home/xflops/coin-state/test-simple-strategy-continuous-122d-audit-20261002-v1")
MIN=60_000_000
DAY=86_400_000_000
SYMS=("BTCUSDT","ETHUSDT")
actual_path=ROOT/"reports/fast_research/SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_20261002_V1.json"
out_path=ROOT/"reports/fast_research/SIMPLE_STRATEGY_CONTINUOUS_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json"
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
spec=read(ROOT/"protocols/SIMPLE_STRATEGY_CONTINUOUS_122D_V1.json")
hashes=binding["source_hashes"]
audit={"version":"SIMPLE_STRATEGY_CONTINUOUS_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1",
       "status":"FAIL_ACTUAL_PROXY_LEDGER_AUDIT","created_utc":None,"actual_report_path":str(actual_path),
       "actual_report_sha256":sha(actual_path),"actual_host_session_id":33281,
       "verified_source_hashes":hashes,"independent_task_id":os.environ.get("COIN_TASK_ID"),
       "independent_source":str(Path(__file__)),"independent_source_sha256":sha(__file__),
       "reused_checker_source":"docs/archive/SIMPLE_STRATEGY_AUDIT_CHECKER_20261002_V3_R4.py",
       "reused_checker_sha256":"f63c8e9a66a19ae275a5f6685f3e8401d0b1f2c94603683b763f9e7ab2b9c314",
       "checker_adjustments":["12 continuous122day accounts; same accounting math", "IPC canonical rechunk", "Explicit money/qty/ratio tolerances retained", "NumPy scalar JSON normalization", "Monthly ongoing-position MTM; no account resets"],
       "python":sys.executable,"sys_prefix":sys.prefix,"ledgers":[]}
try:
    need(sha(actual_path)=="62cb5604580e3af8de3bcf7d1db5f76343581ef44f656ba89f927ba4bdb24e94", "Frozen reported actual bytes")
    need(sha(ROOT/audit["reused_checker_source"])==audit["reused_checker_sha256"], "Reuse checker bytes")
    need(binding==r["binding"] and sha(Path(r["run_dir"])/"RUN_BINDING.json")==r["run_binding_sha256"],"Actual binding bytes")
    need(r["status"]=="COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING" and r["completed_ledgers"]==12 and r["all_planned_ledgers_complete"],"Actual report incomplete")
    need(binding["planned_ledgers"]==12 and binding["strategies"]==spec["strategy_ids"] and binding["all_folds"]==spec["folds"], "Bound continuous fixed recipes")
    need(binding["fits"]==0 and r["market_models_fit"]==0 and r["locked_consumed"] is False and r["orders_sent"]==0
        and r["candidate_status"]=="NO_QUALIFIED_CANDIDATE" and r["account_continuity"]=="SINGLE_CONTINUOUS_PERIOD_BY_STRATEGY_AND_COST", "Qualification/continuous account scope")
    need(spec["planned_ledgers"]==12 and spec["warmup_days"]==31 and len(spec["folds"])==1
        and spec["folds"][0]=={"id":"CONT122","period_start":"2025-08-01","period_end_exclusive":"2025-12-01"}, "Exact frozen122day dates")
    audit["actual_task"]=task_for(binding)
    need({p:sha(ROOT/p) for p in hashes}==hashes,"Current dependency bytes changed")
    need(all(sha(Path(r["run_dir"])/"source-snapshot"/p)==d for p,d in hashes.items()),"Actual snapshot mismatch")
    need(all(hashes.get(p)==d for p,d in spec["frozen_sources"].items()),"Contract hashes not exact")
    need(binding["protocol_sha256"]==sha(ROOT/"protocols/SIMPLE_STRATEGY_CONTINUOUS_122D_V1.json")
        and "--protocol /mnt/d/codex/coin/protocols/SIMPLE_STRATEGY_CONTINUOUS_122D_V1.json" in binding["exact_command"],"Exact122day protocol")
    tiny_path=ROOT/spec["required_smoke_receipt"]
    tiny=read(tiny_path)
    tb=read(Path(tiny["run_dir"])/"RUN_BINDING.json")
    need(tb==tiny["binding"] and tb["source_hashes"]==hashes and sha(tiny_path)==r["accepted_smoke_sha256"],"Actual/tiny exact source pairing")
    audit["actual_tiny_task"]=task_for(tb)
    x=ET.parse(Path(tiny["run_dir"])/"junit.xml").getroot()
    counts={k:sum(int(s.get(k,0)) for s in x.iter("testsuite")) for k in ("tests","failures","errors","skipped")}
    need(counts=={"tests":2,"failures":0,"errors":0,"skipped":0}
        and sha(Path(tiny["run_dir"])/"junit.xml")==tiny["junit_sha256"],"Two bound targeted continuous-plan/public-guard tests")
    case_names=sorted(c.attrib["name"] for c in x.iter("testcase"))
    need(case_names==["test_continuous_protocol_subset_generic_reports","test_public_null_guard_valid_snapshot_equivalence"], "Exact targeted smoke output cases")
    audit["checked_existing_smoke_output_cases"]=case_names
    audit["actual_tiny"]={"path":str(tiny_path),"sha256":sha(tiny_path),"counts":counts,"scope":"Protocol subset/generic period reporting and old public NULL/equivalence fixture; no old accounting/target green suite rerun by auditor."}
    source_path=Path(r["minute_source"]["path"])
    need(source_path==Path(r["run_dir"])/"shared_source_minutes.parquet" and sha(source_path)==r["minute_source"]["sha256"],"Derivative source SHA")
    minutes=pl.read_parquet(source_path)
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
        need(fold["start_us"]==start and fold["end_us"]==end and fold["status"]=="COMPLETE_PROXY_COMPARISON" and len(fold["results"])==12,"Fold/calendar scope")
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
            need(np.array_equal(inventory["close_us"].to_numpy(),close_times) and inventory.height==122*1440,"Full minute inventory")
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
            need(len(dn)==122 and close(dn,daily["nav"].to_numpy()) and close(dr,daily["return"].to_numpy()),"UTC daily NAV/returns")
            fee_day=np.bincount((t//DAY-start//DAY).astype(int),weights=fees,minlength=122)
            cost_day=np.bincount((t//DAY-start//DAY).astype(int),weights=extra,minlength=122)
            notional_day=np.bincount((t//DAY-start//DAY).astype(int),weights=notionals,minlength=122)
            need(close(fee_day,daily["fees"].to_numpy()) and close(cost_day,daily["execution_costs"].to_numpy())
                and close(notional_day/np.r_[10000.,dn[:-1]],daily["turnover"].to_numpy()),"Daily fees/cost/turnover")
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
            annual=float((nav[-1]/10000.)**(365/122)-1)
            need(summary["days"]==122 and abs(summary["total_return"]-net/10000.)<1e-12
                and abs(summary["annual_return"]-annual)<1e-12 and published["period_days"]==122
                and close(published["period_net_return"],net/10000.,1e-12)
                and close(published["period_descriptive_net_CAGR"],annual,1e-12)
                and published["annualized_return_is_descriptive_only"] is True, "122day descriptive return fields")
            month_rows=[]
            previous_nav=10000.
            previous_gross_nav=10000.
            for month,lower,upper in (("2025-08",stamp("2025-08-01"),stamp("2025-09-01")),
                    ("2025-09",stamp("2025-09-01"),stamp("2025-10-01")),
                    ("2025-10",stamp("2025-10-01"),stamp("2025-11-01")),
                    ("2025-11",stamp("2025-11-01"),stamp("2025-12-01"))):
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
                    "trade_count":int(np.sum(fill_indices)),"within_month_minute_MDD":mmdd,
                    "descriptive_daily_annual_vol":mv,"month_end_quantities":end_quantities,
                    "month_end_marked_notional":float(sum(v[last] for v in symbol_values)),
                    "cash_reset":False,"monthly_liquidation_assumed":False})
                previous_nav,previous_gross_nav=mn,mg
            need([m["days"] for m in month_rows]==[31,30,31,30] and close(sum(m["net_PnL"] for m in month_rows),net)
                and close(sum(m["fee"] for m in month_rows),fees.sum()) and close(sum(m["execution_cost"] for m in month_rows),extra.sum()), "Month totals do not close")
            positive_months=np.maximum([m["gross_PnL_same_quantities"] for m in month_rows],0.)
            positive_net_months=np.maximum([m["net_PnL"] for m in month_rows],0.)
            entry={"fold":fold["fold"],"strategy":strategy,"spread_bps":spread,
                "net_return":float(net/10000.),"net_PnL":float(net),"gross_PnL_same_quantities":float(gross),
                "fees":float(fees.sum()),"execution_costs":float(extra.sum()),"trade_count":fills.height,
                "minute_MDD":mdd,"daily_MDD":dmdd,"period_days":122,"descriptive_net_CAGR":annual,
                "months":month_rows,"net_positive_months":int(np.sum([m["net_PnL"]>0 for m in month_rows])),
                "top1_positive_gross_month_share":float(positive_months.max()/positive_months.sum()) if positive_months.sum() else None,
                "top1_positive_net_month_share":float(positive_net_months.max()/positive_net_months.sum()) if positive_net_months.sum() else None,"descriptive_122day_daily_annual_vol":vol,
                "max_minute_gross_weight":float(gw.max()),
                "max_minute_BTC_weight":float(weights["BTCUSDT"].max()),"max_minute_ETH_weight":float(weights["ETHUSDT"].max()),
                "passive_drift_symbol_cap_excess_minutes":int(np.sum((weights["BTCUSDT"]>.3+1e-9)|(weights["ETHUSDT"]>.3+1e-9))),
                "passive_drift_gross_cap_excess_minutes":int(np.sum(gw>.6+1e-9)),
                "day_concentration_absolute_difference":abs(concentration-published["top1_day_positive_gross_PnL_share"]) if concentration is not None else None,"day_concentration_absolute_tolerance":1e-10,"top1_positive_gross_day_share":concentration,
                "terminal_marked_notional":float(sum(v[-1] for v in symbol_values)),
                "cash_min":float(cash.min()),"target_bindings":target_bound[strategy],
                "ledger_artifact_hashes":{n:b["sha256"] for n,b in item["artifacts"].items()}}
            audit["ledgers"].append(entry)
    need(len(seen)==12 and seen=={(f["id"],s,b) for f in spec["folds"] for s in spec["strategy_ids"] for b in (2,4,8)},"Missing paired grids")
    aggregate=[]
    for strategy in spec["strategy_ids"]:
        for spread in (2,4,8):
            rows=[x for x in audit["ledgers"] if x["strategy"]==strategy and x["spread_bps"]==spread]
            need(len(rows)==1,"Continuous account must not stitch independent periods")
            one=rows[0]
            published=next(a for a in r["aggregate"] if a["strategy"]==strategy and a["spread_bps"]==spread)
            need(published["complete_periods"]==1 and published["period_lengths_days"]==[122]
                and close(published["period_net_return"],one["net_return"],1e-12)
                and close(published["mean_period_net_return"],one["net_return"],1e-12)
                and close(published["worst_period_net_return"],one["net_return"],1e-12)
                and close(published["fees_USDT_across_period_accounts"],one["fees"])
                and close(published["execution_cost_USDT_across_period_accounts"],one["execution_costs"])
                and close(published["max_observed_daily_MDD"],one["daily_MDD"],1e-12)
                and close(published["max_observed_minute_MDD"],one["minute_MDD"],1e-12)
                and published["trade_count"]==one["trade_count"],"Continuous aggregate mismatch")
            aggregate.append({k:one[k] for k in ("strategy","spread_bps","net_return","net_PnL","gross_PnL_same_quantities",
                "fees","execution_costs","trade_count","period_days","descriptive_net_CAGR","minute_MDD","daily_MDD",
                "descriptive_122day_daily_annual_vol","max_minute_gross_weight","max_minute_BTC_weight","max_minute_ETH_weight",
                "passive_drift_symbol_cap_excess_minutes","passive_drift_gross_cap_excess_minutes","top1_positive_gross_day_share",
                "net_positive_months","top1_positive_gross_month_share","top1_positive_net_month_share","terminal_marked_notional","cash_min")})
    need({p:sha(ROOT/p) for p in hashes}==hashes and sha(actual_path)==audit["actual_report_sha256"],"Frozen outputs changed")
    owned=sum(p.stat().st_size for p in Path(r["run_dir"]).rglob("*") if p.is_file())
    need(owned==r["owned_bytes"] and owned<=spec["maximum_new_owned_bytes"],"Actual owned resource budget")
    need(r["resources"]["swap_bytes"]==0 and r["resources"]["gpu_used"] is False and r["resources"]["ram_limit_bytes"]<=5_000_000_000,"Shared budget")
    audit.update(status="PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE",aggregate=aggregate,
        completed_ledgers_verified=12,common_parameters_unchanged=True,resource_owned_bytes=owned,
        market_model_fits=0,original_market_source_files_read=False,allowed_derivative_market_outputs_read=True,
        locked_consumed=False,orders_sent=0,candidate_status="NO_QUALIFIED_CANDIDATE",
        proxy_economic_accounting="PASS_WITH_MINUTE_OPEN_AND_QUOTE_VOLUME_PROXY_LIMITS",
        economic_qualification="NOT_EVALUATED_NO_LONG_TERM_OR_UNSEEN_EVIDENCE",
        current_public_NULL_guard="CLOSED_BY_NEW_null_count_GUARD_AND_EXISTING_V2_PUBLIC_CASE; old standalone FAIL retained.",
        limits=["Accounting, causal proxy timing, common funding/cost/periods and complete output grid PASS; not profit/alpha qualification.",
          "Same actual quantities gross-cost identity is not a reoptimized zero-cost strategy.",
          "Minute open and previous-minute quote-volume are proxies; no BBO, queue, historical account-tier or actual executable-fill proof.",
          "Intent-event risk scaling permits passive drift; realized volatility/exposure differ across strategies and are disclosed per ledger.",
          "Continuous122days include already inspected windows; historical screening, not unseen or long-term qualification.",
          "Frozen target/engine implementation retained; two existing targeted tiny tests bound, no previous green suite or raw-source QA rerun.",
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