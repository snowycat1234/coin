"""Independent six new fee ledgers; adapt accepted checker math, no replay."""
from pathlib import Path
from datetime import UTC,date,datetime
import hashlib,json,os,sys,resource,traceback,math
import xml.etree.ElementTree as ET
import numpy as np
import polars as pl
ROOT=Path("/mnt/d/codex/coin")
STATE=Path(__file__).parent.resolve()
MIN=60_000_000;DAY=86_400_000_000;SYMS=("BTCUSDT","ETHUSDT")
REUSE="docs/archive/PUBLIC_STRATEGY_90D_AUDIT_CHECKER_20261002_V2_R2.py"
REUSE_SHA="262f753dc0d383ebccc8ecdf67f84e383e6dfcd0eba82315ddf43732c0dc4c52"
OUT=ROOT/"reports/fast_research/BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json"
CASES=[
("90","BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2.json","329f9f923ed4fd8223e2e267a200c2e67036c8ce4f82a7fef0027efdd3b7960a","BYBIT_SPOT_2H_90D_V2.json",97035)]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def need(ok,msg):
    if not bool(ok):raise ValueError(msg)
def close(a,b,atol=1e-6):return np.allclose(a,b,rtol=0,atol=atol,equal_nan=False)
def json_scalar(x):
    if isinstance(x,np.generic):return x.item()
    raise TypeError(type(x).__name__)
def frame_sha(frame):return hashlib.sha256(json.dumps(frame.to_dicts(),sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def stamp(text):return int(datetime.combine(date.fromisoformat(text),datetime.min.time(),UTC).timestamp())*1_000_000
def task_for(binding):
    p=Path("/home/xflops/coin-state/task-progress")/("task-"+binding["task_id"]+".json")
    t=read(p);need(t["id"]==binding["task_id"] and t["status"]=="completed" and t["exit_code"]==0
        and t["pid"]>0 and t["start_ticks"]>0,"Actual completed0 task binding")
    return {"path":str(p),"sha256":sha(p),"task":t}
def monthly_intervals(start,end):
    cursor=datetime.fromtimestamp(start/1_000_000,UTC)
    rows=[]
    while int(cursor.timestamp())*1_000_000<end:
        after=datetime(cursor.year+(cursor.month==12),cursor.month%12+1,1,tzinfo=UTC)
        lower=max(start,int(cursor.timestamp())*1_000_000);upper=min(end,int(after.timestamp())*1_000_000)
        rows.append((cursor.strftime("%Y-%m"),lower,upper));cursor=after
    return rows
def shared(d):
    return {k:v for k,v in d.items() if k.startswith(("src/","scripts/","tests/","environments/","third_party/"))
        or k in ("protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json","protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json")}
def check_period(label,name,expected_sha,protocol,session,audit):
    actual_path=ROOT/"reports/fast_research"/name;need(sha(actual_path)==expected_sha,"Frozen actual report SHA")
    r=read(actual_path);binding=read(Path(r["run_dir"])/"RUN_BINDING.json")
    actual_task=task_for(binding)
    spec=read(ROOT/"protocols"/protocol);hashes=binding["source_hashes"];days=int(label)
    need(binding==r["binding"] and sha(Path(r["run_dir"])/"RUN_BINDING.json")==r["run_binding_sha256"],"Actual RUN_BINDING")
    need(r["status"]=="COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING" and r["source_bytes_unchanged"]
        and r["completed_ledgers"]==3 and r["all_planned_ledgers_complete"],"Complete actual three accounts")
    need(binding["fits"]==r["market_models_fit"]==0 and not r["locked_consumed"] and r["orders_sent"]==0
        and r["candidate_status"]=="NO_QUALIFIED_CANDIDATE","Scope exceeds fee-accounting screening")
    need(binding["planned_ledgers"]==spec["planned_ledgers"]==3 and binding["all_folds"]==spec["folds"]
        and binding["strategies"]==spec["strategy_ids"]==["COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER"],"Fixed three recipes")
    need(len(r["folds"])==len(spec["folds"])==1 and spec["warmup_days"]==31,"One complete period")
    need(binding["protocol_sha256"]==sha(ROOT/"protocols"/protocol),"Actual protocol binding")
    need({p:sha(ROOT/p) for p in hashes}==hashes
        and all(sha(Path(r["run_dir"])/"source-snapshot"/p)==d for p,d in hashes.items())
        and all(hashes.get(p)==d for p,d in spec["frozen_sources"].items()),"Current/snapshot frozen sources")
    tiny_path=ROOT/spec["required_smoke_receipt"];tiny=read(tiny_path);tb=read(Path(tiny["run_dir"])/"RUN_BINDING.json")
    need(tb==tiny["binding"] and sha(Path(tiny["run_dir"])/"RUN_BINDING.json")==tiny["run_binding_sha256"]
        and sha(tiny_path)==r["accepted_smoke_sha256"],"Accepted common synthetic input")
    need(tiny["status"]=="PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT" and shared(tb["source_hashes"])==shared(hashes)
        and len(shared(hashes))==33 and tiny["registration_start"]["hyperparameters"]==spec["common_config"]
        and tiny["registration_start"]["cost_assumptions"]==spec["costs"]
        and tiny["registration_start"]["thresholds"]==spec["strategy_rules"],"Exact shared code/cost/risk synthetic reuse")
    x=ET.parse(Path(tiny["run_dir"])/"junit.xml").getroot()
    counts={k:sum(int(s.get(k,0)) for s in x.iter("testsuite")) for k in ("tests","failures","errors","skipped")}
    need(counts=={"tests":4,"failures":0,"errors":0,"skipped":0}
        and sha(Path(tiny["run_dir"])/"junit.xml")==tiny["junit_sha256"],"Four actual new integration tests")
    deriv=r["fee_derivation"]
    need(deriv["derived_AST_SHA256"]=="39ffd9142be81285b3a6b460c73b1c7799c7621a1c34a2f1faa845d290608b73"
        and sha(deriv["derived_source_path"])==deriv["derived_source_file_sha256"]
        =="a33c4f392c033d44224be5f64a42456b529e973d9af0925c8a454043f2762a8f"
        and sha(deriv["receipt_path"])==deriv["receipt_sha256"],"Actual sixteen-change fee derivation")
    need(r["fee_settlement"]==spec["fee_settlement"]=="BYBIT_SPOT_RECEIVED_ASSET_V1"
        and r["fee_profile_sha256"]==spec["fee_profile_sha256"]
        =="d6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f","Fixed fee profile")
    source_path=Path(r["minute_source"]["path"])
    need(source_path==Path(r["run_dir"])/"shared_source_minutes.parquet"
        and sha(source_path)==r["minute_source"]["sha256"],"Exact derivative Parquet")
    minutes=pl.read_parquet(source_path)
    need(minutes.height==r["minute_source"]["rows"]==2*(days+31)*1440 and r["minute_source"]["invalid_minutes"]==0,"Complete source row count")
    need(set(minutes["symbol"].unique().to_list())==set(SYMS)
        and minutes["minute_valid"].null_count()==0 and minutes["minute_valid"].all()
        and minutes["valid_day"].null_count()==0 and minutes["valid_day"].all()
        and minutes["missing_reason"].null_count()==minutes.height,"Invalid/unknown source")
    need(all(minutes[p].null_count()==0 and minutes.schema[p]==pl.Int64 for p in ("open_us","close_us","available_us"))
        and np.array_equal(minutes["close_us"].to_numpy(),minutes["open_us"].to_numpy()+MIN)
        and np.array_equal(minutes["available_us"].to_numpy(),minutes["close_us"].to_numpy()),"Past-only complete availability")
    reference=spec["reused_minute_input"];parent=read(ROOT/reference["report_path"])
    old_source=Path(reference["path"])
    need(sha(ROOT/reference["report_path"])==reference["report_sha256"] and parent["status"]=="COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING"
        and parent["source_bytes_unchanged"] and parent["all_planned_ledgers_complete"]
        and sha(old_source)==reference["sha256"]==parent["minute_source"]["sha256"]
        and parent["source_receipt_sha256"]==spec["source_receipt_sha256"],"Accepted reused source binding")
    original=pl.read_parquet(old_source)
    need(original.equals(minutes) and original.schema==minutes.schema,"Exact old source logical values retained")
    del original
    audit["period_bindings"].append({"label":label,"report_path":str(actual_path),"report_sha256":expected_sha,
        "actual_host_session_id":session,"actual_task":task_for(binding),"actual_smoke_task":task_for(tb),
        "smoke_path":str(tiny_path),"smoke_sha256":sha(tiny_path),"synthetic_cases":counts,
        "verified_source_hashes":hashes,"original_derivative_parquet_sha256":reference["sha256"],
        "current_derivative_parquet_sha256":sha(source_path),"logical_original_values_and_schema_preserved":True,
        "protocol_sha256":binding["protocol_sha256"],"source_receipt_sha256":spec["source_receipt_sha256"],
        "derivation_AST_sha256":deriv["derived_AST_SHA256"],"derivation_source_sha256":deriv["derived_source_file_sha256"]})
    seen=set()

    for fold in r["folds"]:
        fc=next(f for f in spec["folds"] if f["id"]==fold["fold"])
        start,end=stamp(fc["period_start"]),stamp(fc["period_end_exclusive"])
        need(fold["start_us"]==start and fold["end_us"]==end and fold["status"]=="COMPLETE_PROXY_COMPARISON" and len(fold["results"])==3,"Fold/calendar scope")
        fm=minutes.filter(pl.col("open_us").is_between(start-31*DAY,end,closed="left"))
        input_path=Path(fold["minute_input_path"])
        need(input_path==Path(r["run_dir"])/(fold["fold"]+"-minute-input.arrow")
            and sha(input_path)==fold["minute_input_sha256"]
            and fold["minute_input_format"]=="IMMUTABLE_ARROW_IPC_FILE_READ_BEFORE_SIGNALS_AND_EXECUTION",
            "Exact runtime Arrow input file binding")
        actual_fm=pl.read_ipc(input_path,memory_map=False)
        need(fm.equals(minutes) and actual_fm.equals(fm) and actual_fm.schema==fm.schema
            and fm.height==2*(days+31)*1440,"Same complete input values/schema/calendar")
        fm=actual_fm
        audit["runtime_inputs"].append({"fold":fold["fold"],"arrow_path":str(input_path),
            "arrow_sha256":sha(input_path),"parquet_sha256":sha(source_path),
            "logical_values_and_schema_equal":True,"physical_file_hash_checked":True})
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
            need(np.array_equal(inventory["close_us"].to_numpy(),close_times) and inventory.height==days*1440,"Full minute inventory")
            t=fills["execution_us"].to_numpy()
            sign=np.where(fills["side"].to_numpy()=="buy",1.,-1.)
            need(fills["side"].is_in(["buy","sell"]).all() and fills["symbol"].is_in(SYMS).all(),"Illegal fill identity")
            q=fills["quantity"].to_numpy()
            mid=fills["mid_price"].to_numpy()
            fill_price=fills["fill_price"].to_numpy()
            notionals=fills["notional"].to_numpy()
            buy=sign>0
            expected_fee_units=np.where(buy,q*.001,notionals*.001)
            fees=np.where(buy,expected_fee_units*mid,expected_fee_units)
            position_delta=np.where(buy,q-q*.001,-q)
            cash_delta=np.where(buy,-notionals,notionals-notionals*.001)
            need(close(fills["gross_quantity"].to_numpy(),q,1e-12)
                and np.array_equal(fills["fee_asset"].to_numpy(),np.where(buy,np.char.replace(fills["symbol"].to_numpy().astype(str),"USDT",""),"USDT"))
                and close(fills["fee_amount"].to_numpy(),expected_fee_units,1e-10)
                and close(fills["fee_USDT_mid"].to_numpy(),fees,1e-8)
                and close(fills["position_delta"].to_numpy(),position_delta,1e-12)
                and close(fills["cash_delta"].to_numpy(),cash_delta,1e-8),"Native asset settlement formula")
            extra=q*np.abs(fill_price-mid)
            need(np.isfinite(q).all() and np.all(q>0) and close(notionals,q*fill_price)
                and close(fills["fee"].to_numpy(),fees) and close(fills["execution_cost"].to_numpy(),extra),"Actual fill costs")
            need(close(fill_price,mid*(1+sign*(spread/2+4)/10000)),"Cost scenario fill proxy")
            if len(t):
                sig=fills["signal_us"].to_numpy()
                eligible=((sig+MIN-1)//MIN+1)*MIN+1
                need(np.all(t>=eligible)&np.all(t%MIN==1)&np.all(t<end),"Future/period fill")
                cash_steps=10000.+np.cumsum(cash_delta)
                need(close(cash_steps,fills["cash_after"].to_numpy(),1e-7),"Sequential cash identity")
            else:
                cash_steps=np.empty(0)
            counts=np.searchsorted(t,close_times,side="right")
            def acc(v): return np.r_[0.,np.cumsum(v)][counts]
            cash=10000.+acc(cash_delta)
            gross_cash=10000.-acc(position_delta*mid)
            nav=cash.copy()
            gross_nav=gross_cash.copy()
            quantities={}
            symbol_values=[]
            fill_nav=10000.+np.cumsum(cash_delta)
            fill_after_positions=[]
            for symbol in SYMS:
                mask=fills["symbol"].to_numpy()==symbol
                qty=acc(position_delta*mask)
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
                    fill_nav+=np.cumsum(position_delta*mask)*opens[index]
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
            need(len(dn)==days and close(dn,daily["nav"].to_numpy()) and close(dr,daily["return"].to_numpy()),"UTC daily NAV/returns")
            fee_day=np.bincount((t//DAY-start//DAY).astype(int),weights=fees,minlength=days)
            cost_day=np.bincount((t//DAY-start//DAY).astype(int),weights=extra,minlength=days)
            notional_day=np.bincount((t//DAY-start//DAY).astype(int),weights=notionals,minlength=days)
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
            annual=float((nav[-1]/10000.)**(365/days)-1)
            need(summary["days"]==days and abs(summary["total_return"]-net/10000.)<1e-12
                and abs(summary["annual_return"]-annual)<1e-12 and published["period_days"]==days
                and close(published["period_net_return"],net/10000.,1e-12)
                and close(published["period_descriptive_net_CAGR"],annual,1e-12)
                and published["annualized_return_is_descriptive_only"] is True, "122day descriptive return fields")
            month_rows=[]
            previous_nav=10000.
            previous_gross_nav=10000.
            for month,lower,upper in monthly_intervals(start,end):
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
            need([m["days"] for m in month_rows]==[int((b-a)//DAY) for _,a,b in monthly_intervals(start,end)] and close(sum(m["net_PnL"] for m in month_rows),net)
                and close(sum(m["fee"] for m in month_rows),fees.sum()) and close(sum(m["execution_cost"] for m in month_rows),extra.sum()), "Month totals do not close")
            positive_months=np.maximum([m["gross_PnL_same_quantities"] for m in month_rows],0.)
            positive_net_months=np.maximum([m["net_PnL"] for m in month_rows],0.)
            entry={"fold":fold["fold"],"strategy":strategy,"spread_bps":spread,
                "net_return":float(net/10000.),"net_PnL":float(net),"gross_PnL_same_quantities":float(gross),
                "fees":float(fees.sum()),"execution_costs":float(extra.sum()),"trade_count":fills.height,
                "turnover_notional_USDT":float(notionals.sum()),"normalized_daily_turnover":normalized_turnover,
                "minute_MDD":mdd,"daily_MDD":dmdd,"period_days":days,"descriptive_net_CAGR":annual,
                "months":month_rows,"net_positive_months":int(np.sum([m["net_PnL"]>0 for m in month_rows])),
                "top1_positive_gross_month_share":float(positive_months.max()/positive_months.sum()) if positive_months.sum() else None,
                "top1_positive_net_month_share":float(positive_net_months.max()/positive_net_months.sum()) if positive_net_months.sum() else None,"descriptive_period_daily_annual_vol":vol,
                "max_minute_gross_weight":float(gw.max()),
                "max_minute_BTC_weight":float(weights["BTCUSDT"].max()),"max_minute_ETH_weight":float(weights["ETHUSDT"].max()),
                "passive_drift_symbol_cap_excess_minutes":int(np.sum((weights["BTCUSDT"]>.3+1e-9)|(weights["ETHUSDT"]>.3+1e-9))),
                "passive_drift_gross_cap_excess_minutes":int(np.sum(gw>.6+1e-9)),
                "day_concentration_absolute_difference":abs(concentration-published["top1_day_positive_gross_PnL_share"]) if concentration is not None else None,"day_concentration_absolute_tolerance":1e-10,"top1_positive_gross_day_share":concentration,
                "terminal_marked_notional":float(sum(v[-1] for v in symbol_values)),
                "cash_min":float(cash.min()),"target_bindings":target_bound[strategy],
                "ledger_artifact_hashes":{n:b["sha256"] for n,b in item["artifacts"].items()}}
            rt=pl.read_parquet(d/"round_trips.parquet")
            held=dict.fromkeys(SYMS,0.);cycles=dict.fromkeys(SYMS,None);expected_cycles=[]
            check_cash=10000.
            for rowindex,row in enumerate(fills.iter_rows(named=True)):
                s=row["symbol"];g=row["quantity"];F=row["fill_price"];M=row["mid_price"];w=row["target_weight"]
                i=(row["execution_us"]-1-start)//MIN
                marks={z:float(per[z]["open"][i]) for z in SYMS}
                before=check_cash+sum(held[z]*marks[z] for z in SYMS)
                desired=w*before-held[s]*M
                is_buy=row["side"]=="buy"
                need((desired>0)==is_buy and 0<=w<=.3,"Fill side/target weight")
                loss=F-.999*M if is_buy else M-F+F*.001
                target=abs(desired)/(.999*M+w*loss if is_buy else M-w*loss)
                upper=min(target,row["capacity"]/F)
                if is_buy:
                    gross_before=sum(held[z]*marks[z] for z in SYMS)
                    upper=min(upper,check_cash/F,
                        max(0.,(.3*before-held[s]*M)/(.999*M+.3*loss)),
                        max(0.,(.6*before-gross_before)/(.999*M+.6*loss)))
                    for z in SYMS:
                        if z!=s:upper=min(upper,max(0.,(before-held[z]*marks[z]/.3)/loss))
                else:upper=min(upper,held[s])
                step=cfg["lot_step_by_symbol"][s]
                expected_g=math.floor(upper/step+1e-9)*step
                if not is_buy and expected_g>held[s]:expected_g=max(0.,expected_g-step)
                need(abs(g-expected_g)<1e-12,"Native target/cash/net-base/capacity/cap sizing")
                check_cash+=row["cash_delta"]
                if row["side"]=="buy" and held[s]<=1e-12:
                    cycles[s]={"entry_us":row["execution_us"],"cost":0.,"proceeds":0.,"fees":0.}
                if row["side"]=="sell":
                    need(g<=held[s]+1e-12,"Sold unavailable net base")
                held[s]+=row["position_delta"]
                after=check_cash+sum(held[z]*marks[z] for z in SYMS)
                if is_buy:
                    need(max(held[z]*marks[z]/after for z in SYMS)<=.3+1e-9
                        and sum(held[z]*marks[z] for z in SYMS)/after<=.6+1e-9,"All-symbol postcost buy cap")
                need(held[s]>=-1e-12,"Negative net inventory")
                cyc=cycles[s];need(cyc is not None,"Sell without purchased inventory")
                cyc["fees"]+=row["fee"]
                if row["side"]=="buy":cyc["cost"]+=g*F
                else:cyc["proceeds"]+=g*F-g*F*.001
                if row["side"]=="sell" and held[s]==0:
                    expected_cycles.append({"symbol":s,"entry_us":cyc["entry_us"],
                        "exit_us":row["execution_us"],"pnl":cyc["proceeds"]-cyc["cost"],"fees":cyc["fees"]})
            need(rt.height==len(expected_cycles)==summary["round_trip_count"],"Closed cycle count")
            for observed,expected in zip(rt.iter_rows(named=True),expected_cycles):
                need(all(observed[k]==expected[k] for k in ("symbol","entry_us","exit_us"))
                    and close(observed["pnl"],expected["pnl"]) and close(observed["fees"],expected["fees"]),
                    "Cycle cost double fee or incorrect proceeds")
            need(orders["quantity"].sum()==fills["quantity"].sum()
                or close(orders["quantity"].sum(),fills["quantity"].sum(),1e-10),"Order/trade gross quantity")
            need(orders.filter(pl.col("filled_notional")==0)["quantity"].sum()==0,"Fee or quantity on unfilled order")
            entry.update(native_asset_fee_verified=True,closed_cycle_count_verified=rt.height,
                fee_settlement_version=summary["fee_settlement_version"],
                positive_terminal_dust_preserved=any(0<held[s]<cfg["lot_step_by_symbol"][s] for s in SYMS))
            audit["ledgers"].append(entry)

    need(len(seen)==3 and seen=={(f["id"],s,b) for f in spec["folds"] for s in spec["strategy_ids"] for b in (2,4,8)},"Missing fixed cost account")
    for spread in (2,4,8):
        one=next(z for z in audit["ledgers"] if z["fold"]==spec["folds"][0]["id"] and z["spread_bps"]==spread)
        published=next(z for z in r["aggregate"] if z["spread_bps"]==spread)
        need(published["complete_periods"]==1 and published["period_lengths_days"]==[days]
            and close(published["period_net_return"],one["net_return"],1e-12)
            and close(published["fees_USDT_across_period_accounts"],one["fees"])
            and close(published["execution_cost_USDT_across_period_accounts"],one["execution_costs"])
            and close(published["max_observed_minute_MDD"],one["minute_MDD"],1e-12),"Aggregate versus actual account")
    reference=next(iter(spec["reused_target_inputs"].values()))
    audit_path=ROOT/reference["accepted_audit"]["path"];old=read(audit_path)
    need(sha(audit_path)==reference["accepted_audit"]["sha256"] and old["status"] in (
        "PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE","PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE_WITH_NONPORTABLE_IPC_LIMIT"),
        "Old accepted public target audit")
    for spread in (2,4,8):
        current=next(z for z in audit["ledgers"] if z["fold"]==spec["folds"][0]["id"] and z["spread_bps"]==spread)
        prior=next(z for z in old["ledgers"] if z["fold"]==current["fold"] and z["strategy"]==current["strategy"] and z["spread_bps"]==spread)
        wanted={k:reference[n]["sha256"] for k,n in (("target_sha256","targets.parquet"),("intent_sha256","intent_calendar.parquet"),("receipt_sha256","target_receipt.json"))}
        need(prior["target_bindings"]==wanted,"Old target digest audit binding")
        newdir=Path(r["run_dir"])/(current["fold"]+"-"+current["strategy"])
        for n in ("targets.parquet","intent_calendar.parquet","target_receipt.json"):
            oldpath=Path(reference[n]["path"]);need(sha(oldpath)==reference[n]["sha256"],"Exact reused target file")
            if n.endswith(".parquet"):
                before=pl.read_parquet(oldpath);after=pl.read_parquet(newdir/n)
                need(before.equals(after) and before.schema==after.schema,"Old/new target logical values")
            else:need(read(oldpath)==read(newdir/n),"Old/new causal target receipt")
        current["old_quote_fee_reference"]={"audit_path":str(audit_path),"audit_sha256":sha(audit_path),
            "prior_net_PnL":prior["net_PnL"],"prior_gross_PnL":prior["gross_PnL_same_quantities"],
            "prior_fee":prior["fees"],"prior_execution_cost":prior["execution_costs"],
            "prior_minute_MDD":prior["minute_MDD"],"prior_turnover":prior["turnover_notional_USDT"],
            "prior_terminal_marked_notional":prior["terminal_marked_notional"],
            "new_minus_old_net_PnL":current["net_PnL"]-prior["net_PnL"],
            "new_minus_old_gross_PnL":current["gross_PnL_same_quantities"]-prior["gross_PnL_same_quantities"],
            "same_signal_values":True,"old_ledger_arrays_read":False,
            "gross_quantity_paths_changed_after_native_fees":True}
    need({p:sha(ROOT/p) for p in hashes}==hashes and sha(actual_path)==expected_sha,"Frozen actual bytes changed")

def main():
    need(os.environ.get("COIN_TASK_ID") and not OUT.exists() and not (STATE/"RUN_BINDING.json").exists(),"Exclusive audit run")
    need(str(Path(sys.prefix))=="/home/xflops/coin-state/v8-clean-env-20261002-v2" and pl.thread_pool_size()<=2,"Clean bounded audit environment")
    need(sha(ROOT/REUSE)==REUSE_SHA,"Reused checker byte pin")
    binding={"task_id":os.environ["COIN_TASK_ID"],"exact_command":" ".join(sys.argv),
        "python":sys.executable,"sys_prefix":sys.prefix,"checker_sha256":sha(__file__),"reused_checker":REUSE,"reused_checker_sha256":REUSE_SHA,
        "actual_reports":{n:d for _,n,d,_,_ in CASES},
        "environment_lock_sha256":sha(ROOT/"environments/v8/uv.lock"),
        "data_scope":"THREE_NEW_CONT90_LEDGER_READS_PLUS_THREE_PRIOR_CONT122_BLOCKS_METADATA_REUSE"}
    (STATE/"RUN_BINDING.json").write_text(json.dumps(binding,indent=2,allow_nan=False))
    audit={"version":"BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1",
        "status":"FAIL_NATIVE_FEE_SIX_LEDGER_AUDIT","binding":binding,"independent_task_id":os.environ["COIN_TASK_ID"],
        "independent_source":str(Path(__file__)),"independent_source_sha256":sha(__file__),
        "run_binding_sha256":sha(STATE/"RUN_BINDING.json"),"period_bindings":[],"runtime_inputs":[],"ledgers":[],
        "candidate_status":"NO_QUALIFIED_CANDIDATE","registry_appended_by_auditor":False,
        "original_market_source_files_read":False,"models_fit":0,"orders_sent":0,"locked_consumed":False}
    try:
        failed_path=ROOT/"reports/fast_research/BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json"
        failed=read(failed_path)
        need(sha(failed_path)=="bcba15e8df42270870c49a4f1aefa902fc69b037400a87dbe1e957b47643bb4f"
            and failed["status"]=="FAIL_NATIVE_FEE_SIX_LEDGER_AUDIT"
            and failed["error"]=="Frozen actual bytes changed"
            and failed["completed_ledgers_before_failure"]==3
            and {(z["fold"],z["spread_bps"]) for z in failed["ledgers"]}=={("CONT122",b) for b in (2,4,8)},
            "Preserved original partial audit scope")
        old_checker=Path(failed["independent_source"])
        need(sha(old_checker)==failed["independent_source_sha256"]
            =="9f07de697a14cbd8fd5dd775cb78cfe1f92c96d7d192be07799ac282959c37da","Original failed checker preserved")
        old_task_path=Path("/home/xflops/coin-state/task-progress")/("task-"+failed["independent_task_id"]+".json")
        old_task=read(old_task_path)
        need(old_task["id"]==failed["independent_task_id"] and old_task["status"]=="failed"
            and old_task["exit_code"]==1 and old_task["pid"]>0 and old_task["start_ticks"]>0,"Actual original auditor exit1")
        before=old_checker.read_text(encoding="utf-8-sig")
        after=Path(__file__).read_text(encoding="utf-8-sig")
        old_function=before[before.index("def check_period("):before.index("\ndef main():")]
        new_function=after[after.index("def check_period("):after.index("\ndef main():")]
        expected_function=old_function.replace("label,name,expected,protocol","label,name,expected_sha,protocol").replace(
            "sha(actual_path)==expected,","sha(actual_path)==expected_sha,").replace('"report_sha256":expected,','"report_sha256":expected_sha,')
        need(expected_function==new_function,"Only argument rename in financial checker; math unchanged")
        prior_binding=failed["period_bindings"][0]
        actual_path=Path(prior_binding["report_path"]);actual=read(actual_path);old_binding=actual["binding"]
        need(sha(actual_path)==prior_binding["report_sha256"]
            =="53447ac3722829cb5c4db12f5b469b100edb20c05bbb6e9c83f29bce5138bee3"
            and {p:sha(ROOT/p) for p in old_binding["source_hashes"]}==old_binding["source_hashes"]
            and all(sha(Path(actual["run_dir"])/"source-snapshot"/p)==d for p,d in old_binding["source_hashes"].items())
            and sha(Path(actual["run_dir"])/"RUN_BINDING.json")==actual["run_binding_sha256"]
            and read(Path(actual["run_dir"])/"RUN_BINDING.json")==old_binding,"122D source/SHA guard recovered metadata only")
        task_for(old_binding)
        audit["ledgers"]=failed["ledgers"]
        audit["period_bindings"]=failed["period_bindings"]
        audit["runtime_inputs"]=failed["runtime_inputs"]
        audit["preserved_failed_auditor"]={"report_path":str(failed_path),"report_sha256":sha(failed_path),
            "status":failed["status"],"actual_host_session_id":56548,"actual_task_path":str(old_task_path),
            "actual_task_sha256":sha(old_task_path),"actual_task":old_task,
            "checker_path":str(old_checker),"checker_sha256":sha(old_checker),
            "financial_blocks_completed":3,"folds_completed":["CONT122"],"financial_ledger_arrays_reread":False,
            "source_mismatch_count_after_independent_metadata_verification":0,
            "cause":"expected actual SHA argument overwritten by old target reconstruction expected=[]; false comparison after three completed financial blocks",
            "overwritten_parameter_line":43,"target_reconstruction_overwrite_line":140,"false_sha_compare_line":426,
            "original_whole_run_pass_claimed":False}
        audit["composite_scope"]="NOT_SINGLE_FRESH_SIX_SUITE; 3 CONT122 financial blocks from retained exit1 + 3 new CONT90 blocks from recovery"
        audit["fresh_financial_selector"]={"period":"CONT90","spreads":[2,4,8],"planned_fresh_ledgers":3,"122D_ledgers_replayed_or_reread":0}
        audit["financial_checker_prefix_repair"]="Only expected→expected_sha parameter/reference rename; source comparison logic and every financial assertion otherwise byte-equivalent"
        for case in CASES:check_period(*case,audit)
        need(len(audit["ledgers"])==6,"All six newly executed ledgers")
        audit.update(status="PASS_COMPOSITE_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_NOT_SINGLE_FRESH_SIX_SUITE",
            completed_ledgers_verified=6,economic_qualification="NOT_PROVEN_SCREENING_ONLY",
            limits=["Previously seen historical Binance minute proxy with current Bybit ordinary Spot Non-VIP fee rule.",
                "No Bybit BBO/queue/prices/account fee tiers/filters qualification; lots and capacity remain COIN proxy assumptions.",
                "Same net received inventory gross shadow; not a fee-free gross order strategy.",
                "Risk mechanism inherited at intent events, passive drift disclosed; realized risks need not match.",
                "Old two-hour evidence preserved; only old saved summaries and target/input artifacts reused, old ledger arrays not reread."])
    except Exception as error:
        audit.update(error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),
            completed_ledgers_before_failure=len(audit["ledgers"]));raise
    finally:
        audit.update(created_utc=datetime.now(UTC).isoformat(),peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        with OUT.open("x") as stream:json.dump(audit,stream,indent=2,allow_nan=False,default=json_scalar)
        print(json.dumps({"status":audit["status"],"report":str(OUT),"sha256":sha(OUT),"completed_ledgers":len(audit["ledgers"])}))
if __name__=="__main__":main()





