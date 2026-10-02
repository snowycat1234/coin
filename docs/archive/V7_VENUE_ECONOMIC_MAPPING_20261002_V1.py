"""July-only venue evidence and scenarios; never converts Spot PnL into perp PnL."""
import csv
import datetime as dt
import hashlib
import io
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
import zipfile
from decimal import Decimal
from pathlib import Path

from quant.paths import ROOT, STATE
from quant.resources import status

sys.path.insert(0, str(ROOT / "scripts/research_v7"))
from oracle_flow_ceiling import Progress

OUT = STATE / "v7-venue-economic-mapping-20261002-v1"
OUT.mkdir(exist_ok=False)
progress = Progress()
received = 0

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def get(url, name):
    global received
    start = time.monotonic()
    rec = {"url": url, "method": "GET", "credentials_used": False,
           "requested_utc": dt.datetime.now(dt.UTC).isoformat()}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "coin-v7-public-availability-research/1.0"}), timeout=15) as response:
            body = response.read(4097)
            assert len(body) <= 4096
            rec.update(http_status=response.status, final_url=response.url)
    except urllib.error.HTTPError as error:
        body = error.read(4096)
        rec.update(http_status=error.code, error="HTTPError")
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        body = str(error).encode()
        rec.update(http_status=None, error=type(error).__name__)
    path = OUT / name
    path.write_bytes(body)
    received += len(body)
    assert received <= 20_000
    rec.update(saved_path=str(path), sha256=digest(path), bytes=len(body), elapsed_seconds=time.monotonic()-start)
    return rec

try:
    metadata_path = ROOT / "reports/fast_research/V7_VENUE_METADATA_AVAILABILITY_20261002_V1.json"
    oof_path = ROOT / "reports/fast_research/V7_OOF_FLOW_IMPACT_20261002_V2.json"
    metadata = json.loads(metadata_path.read_text())
    oof = json.loads(oof_path.read_text())
    assert metadata["registered_commit"] == "f446ce3812bd4e5521f21faecd4ae3c6460e49fc"
    assert metadata["unseen_or_locked_labels_read"] is False
    bindings = {str(metadata_path.relative_to(ROOT)): digest(metadata_path), str(oof_path.relative_to(ROOT)): digest(oof_path), "docs/OPEN_SOURCE_REGISTRY.md": digest(ROOT/"docs/OPEN_SOURCE_REGISTRY.md")}
    for name, expected in oof["binding"]["source_hashes"].items():
        assert digest(ROOT/name) == expected, name
        bindings[name] = expected
    archives = []
    scenarios = []
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        prior = next(a for a in metadata["archives"] if a["symbol"] == symbol and a["data_type"] == "fundingRate")
        path = Path(metadata["run_dir"]) / f"{symbol}-fundingRate-2025-07.zip"
        checksum_path = path.with_name(path.name+".CHECKSUM")
        words = checksum_path.read_text().strip().split()
        assert words[1].lstrip("*") == path.name
        assert digest(path) == prior["zip_sha256"] == words[0]
        with zipfile.ZipFile(path) as z:
            assert z.namelist() == [path.name[:-4]+".csv"]
            rows = list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8-sig")))
        assert len(rows) == 93
        stamps = [int(r["calc_time"]) for r in rows]
        assert stamps == sorted(set(stamps))
        assert all(1751328000000 <= t < 1754006400000 for t in stamps)
        rates = [Decimal(r["last_funding_rate"])*10000 for r in rows]
        intervals = sorted(set(int(r["funding_interval_hours"]) for r in rows))
        assert intervals == [8]
        hours = [(b-a)/3_600_000 for a,b in zip(stamps,stamps[1:])]
        offsets = [t % (8*3_600_000) for t in stamps]
        avg = sum(rates)/Decimal(len(rates))
        item = {"symbol":symbol, "archive_url":prior["zip_url"], "checksum_url":prior["checksum_url"], "zip_sha256":digest(path), "checksum_sha256":digest(checksum_path), "rows":len(rows), "published_timestamp_field":"calc_time; not account-level actual funding transaction timestamp", "timestamp_unit":"milliseconds", "first_timestamp_ms":stamps[0], "last_timestamp_ms":stamps[-1], "declared_funding_intervals_hours":intervals, "actual_event_spacing_hours_min":min(hours), "actual_event_spacing_hours_max":max(hours), "published_8h_boundary_offset_ms_min":min(offsets), "published_8h_boundary_offset_ms_max":max(offsets), "positive_events":sum(r>0 for r in rates), "negative_events":sum(r<0 for r in rates), "zero_events":sum(r==0 for r in rates), "rate_bps_min":float(min(rates)), "rate_bps_max":float(max(rates)), "rate_bps_mean":float(avg), "rate_bps_median":float(statistics.median(rates)), "long_cashflow_per_event_notional_bps_min":float(-max(rates)), "long_cashflow_per_event_notional_bps_max":float(-min(rates)), "short_cashflow_per_event_notional_bps_min":float(min(rates)), "short_cashflow_per_event_notional_bps_max":float(max(rates)), "mark_price_available_in_funding_archive":False}
        archives.append(item)
        for h in [5,15,30,60]:
            assert h*60_000 < min(b-a for a,b in zip(stamps,stamps[1:]))
            probability = Decimal(h)/Decimal(480)
            scenarios.append({"symbol":symbol, "holding_minutes":h, "status":"ILLUSTRATIVE_UNIFORM_ENTRY_PHASE_AND_CONSTANT_MARK_NOTIONAL_ONLY", "period_minutes":480, "cross_event_probability":float(probability), "cross_event_probability_percent":float(probability*100), "maximum_nominal_events_for_fixed_horizon_in_observed_July_schedule":1, "event_crossing_is_required_for_nonzero_cashflow":True, "conditional_event_cashflow_range_long_bps":[float(-max(rates)),float(-min(rates))], "conditional_event_cashflow_range_short_bps":[float(min(rates)),float(max(rates))], "illustrative_expected_long_cashflow_bps":float(-probability*avg), "illustrative_expected_short_cashflow_bps":float(probability*avg), "realized_strategy_funding_or_APR":False, "assumptions":["entry phase uniform and independent of rate/event; event rates sampled uniformly from observed July", "mark notional constant; bps denominated by event mark notional, not collateral equity", "fixed holding duration equals target horizon; actual strategy can hold longer and must use real entry/exit", "ignore month edge and transaction-time ambiguity for this illustration; 15-second transaction deviation requires conservative boundary treatment in real replay"]})
        progress.update("已有官方 funding 事件与经济边界",len(archives),2,"币种",真实资金费事件=len(rows))
    checks=[]
    for symbol in ["BTCUSDT","ETHUSDT"]:
        for kind in ["markPriceKlines","indexPriceKlines"]:
            name=f"{symbol}-{kind}-1m-2025-07-01.zip.CHECKSUM"
            url=f"https://data.binance.vision/data/futures/um/daily/{kind}/{symbol}/1m/{name}"
            checks.append({"symbol":symbol,"data_type":kind,"scope":"this exact daily July01 1m CHECKSUM key only",**get(url,name)})
            progress.update("官方价格日档 CHECKSUM 可用性",len(checks),4,"公开请求",实际新增下载字节=received)
    economics=[]
    for block in oof["horizons"]:
        h=block["horizon_minutes"]
        for branch in block["direct_two_stage_comparison"]:
            s=branch["economics"]["2"]
            assert s["roundtrip_fee_bps"]==20 and s["roundtrip_extra_slippage_bps"]==8 and s["prediction_threshold_bps"]==35
            economics.append({"horizon_minutes":h,"policy":branch["policy"],"observed_spot_closed_roundtrips":s["closed_roundtrips"],"observed_spot_7d_net_return":s["net_proxy_return"],"observed_spot_break_even_roundtrip_cost_bps":s["break_even_roundtrip_cost_bps"],"conditional_future_valid_filter":True,"perp_result":False})
    evidence={"status":"V7_SPOT_USDM_ECONOMIC_MAPPING_READ_ONLY_COMPLETE_WITH_EXPLICIT_INPUT_GAPS", "created_utc":dt.datetime.now(dt.UTC).isoformat(), "run_dir":str(OUT), "analysis_script_sha256":digest(Path(__file__)), "input_hashes":bindings, "only_market_sample_read":"Existing registered July2025 development funding archives and aggregate prior OOF report; no new target labels", "funding_archives":archives, "holding_horizon_scenarios":scenarios, "small_daily_price_checksum_probe":checks, "actual_new_downloaded_bytes":received, "prior_metadata_downloaded_bytes":metadata["actual_downloaded_response_bytes"], "total_venue_branch_downloaded_bytes":received+metadata["actual_downloaded_response_bytes"], "new_request_bound_bytes":20_000, "prior_monthly_price_checksum_status":"All four exact July2025 monthly 1m mark/index CHECKSUM keys HTTP404; no conclusion about all archival directories", "public_usdm_REST_status":"Prior credential-free fundingRate/fundingInfo/exchangeInfo HTTP451 restricted location; not retried on alternate hosts or bypassed", "current_fee_verification":{"spot_standard_regular_user_no_discount":{"status":"official public table verified by web text extract 2026-10-02; WSL direct HTML was HTTP202 empty", "maker_oneway_bps":10,"taker_oneway_bps":10,"url":"https://www.binance.com/en/fee/trading"}, "usdm_regular_user_no_discount":{"status":"current public table extract has No records found; current user applicability unverified", "url":"https://www.binance.com/en/fee/futureFee", "hypothetical_official_FAQ_only":{"maker_oneway_bps":2,"taker_oneway_bps":5,"taker_roundtrip_bps":10,"maker_roundtrip_bps":4,"url":"https://www.binance.com/en/support/faq/detail/360033544231","FAQ_updated":"2026-05-01","applicable_current_or_historical_fee_verified":False}}, "historical_2025_2026_account_fee_tier_and_pair_specific_promotions":"UNKNOWN; no account keys, BNB/referral/VIP discount or promotion assumed"}, "preserved_spot_policy":{"roundtrip_fee_bps":20,"roundtrip_slippage_bps":8,"roundtrip_assumed_spread_bps":[2,4,8],"prediction_threshold_bps":35,"per_symbol_new_allocation_nav_fraction":0.3,"aggregate_new_allocation_nav_fraction":0.6,"leverage_added":False}, "observed_spot_mechanism_comparison":economics, "economic_identity_required_for_perp":{"realized_trade_gross":"direction * quantity * (actual perp exit fill - actual perp entry fill)","funding_cashflow":"-direction * abs(quantity_at_event) * mark_price_at_event * actual_event_rate; only when the position is actually liable at that settlement event", "fee":"actual fill notional * applicable maker/taker rate on each side", "valuation":"mark-based unrealized PnL and margin constraints; liquidation and clearance cost when applicable", "basis":"Spot return differs from perp return by changing venue basis; must build separate perp target and fill ledger", "price_kline_is_BBO_or_guaranteed_fill":False, "uniform_risk_comparison":"Predeclare notional/collateral caps matching existing risk; no extra leverage to increase APR"}, "documented_current_rules":[{"url":"https://www.binance.com/en/support/faq/detail/360033525031","updated":"2026-03-06","facts":["positive funding long pays short; negative funding short pays long", "funding uses mark notional and discrete settlement; not prorated by holding minutes", "default8h can change; actual transaction has a15-second deviation; published calc_time is not proof of exact account charge timestamp", "funding can reduce available balance or position margin"]},{"url":"https://www.binance.com/en/support/faq/detail/360033525271","updated":"2026-01-04","facts":["mark determines unrealized PnL/liquidation rather than executable fill", "maintenance margin depends on exposure tier; exact historical brackets/clearance fees unverified", "fully collateralized short not guaranteed liquidation-free because upside exposure is unbounded"]}], "primary_scientific_conclusion":"Existing 30m DIRECT5.34bp/60m DIRECT8.31bp and OOF1.65/5.43bp observed Spot gross break-even are below even hypothetical USD-M10bp roundtrip taker fee alone. This does not prove perp impossibility: perp/short targets and fills were not evaluated. Funding in this July sample is small relative to fees, discrete and signed; borrowing a low fee cannot solve missing venue target/fill evidence.", "current_long_term_net_APR_candidate":None, "long_term_net_APR_proven":False, "next_experiment_priority":"Root-owned three genuinely unseen folds under matched fixed Spot cost/risk: lower-turnover direct15m/control and calibration/residual diagnostics before more infrastructure; preserve >=20pct frontier for venue-specific perp/short target if input gaps close", "paused_routes":[{"route":"USD-M economic replay / short extension","reopen_condition":"Verified independent perp execution-price inputs, actual event funding mark series, predeclared conservative historical fee assumptions or verified fee schedule, causal BBO/slippage treatment and historical margin/clearance constraints; immutable unseen risk/cost protocol"},{"route":"Maker fee-based edge rescue","reopen_condition":"Actual BBO/queue/fill and adverse-selection evidence, verified applicable fees, after original required gates; not currently implemented"}], "unseen_or_locked_labels_read":False,"account_keys_used":False,"orders_sent":0,"models_fit":0,"original_sources_or_evidence_modified":False,"gpu_used":False,"shared_resources":status()}
    report_path=ROOT/"reports/fast_research/V7_SPOT_USDM_ECONOMIC_MAPPING_20261002_V1.json"
    with report_path.open("x") as f:
        json.dump(evidence,f,indent=2,ensure_ascii=False,allow_nan=False)
    (OUT/"ANALYSIS_SOURCE.py").write_bytes(Path(__file__).read_bytes())
    print(json.dumps({"status":evidence["status"],"report":str(report_path),"report_sha256":digest(report_path),"funding_stats":archives,"daily_probes":[{"symbol":r["symbol"],"kind":r["data_type"],"http_status":r["http_status"]} for r in checks],"new_downloaded_bytes":received,"total_venue_branch_downloaded_bytes":evidence["total_venue_branch_downloaded_bytes"]},ensure_ascii=False),flush=True)
finally:
    progress.stop.set()
    progress.thread.join(timeout=3)
