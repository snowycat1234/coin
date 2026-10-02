"""Bind completed new source-only artifacts; preserve preflight and failed software fetch."""
from datetime import UTC,datetime
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path('/mnt/d/codex/coin');sys.path.insert(0,str(root))
from scripts.research_v8.registry import FIELDS,append_event
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
reports=root/'reports/fast_research'
producer_path=reports/'V8_FUNDING_MARK_INDEX_SOURCE_20261002_V1.json';qa_path=reports/'V8_FUNDING_MARK_INDEX_INDEPENDENT_QA_20261002_V1.json'
producer=json.loads(producer_path.read_bytes());qa=json.loads(qa_path.read_bytes())
assert producer['status']=='OFFICIAL_CARRY_INPUT_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA' and producer['completed_files']==24
assert qa['status']=='PASS_OFFICIAL_CARRY_INPUT_FORMAT_ONLY_INDEPENDENT_QA' and qa['actual_archives']==24 and qa['actual_rows']==703452
assert qa['source_receipt_sha256']==sha(producer_path)
binding=producer['run_binding'];protocol_path=Path(binding['protocol_path']);protocol=json.loads(protocol_path.read_bytes())
assert sha(protocol_path)==binding['protocol_sha256'] and sha(binding['source_path'])==binding['source_sha256']
assert sha(root/'scripts/research_v8/audit_funding_price_source.py')==qa['auditor_sha256']==protocol['auditor_sha256']
preflight=json.loads(Path(protocol['preflight_report']).read_bytes())
assert sha(protocol['preflight_report'])==protocol['preflight_sha256'] and sha(root/'scripts/research_v8/funding_price_source.py')==preflight['run_binding']['source_sha256']
source_rows=[]
for item,checked in zip(producer['sources'],qa['sources']):
    assert item['path']==checked['receipt_path'] and item['sha256']==sha(item['path'])==checked['receipt_sha256']
    receipt=json.loads(Path(item['path']).read_bytes());entry=receipt['entry']
    assert sha(receipt['zip_path'])==receipt['zip_sha256'] and sha(receipt['parquet_path'])==receipt['parquet_sha256']
    source_rows.append({'kind':entry['kind'],'symbol':entry['symbol'],'month':entry['month'],
        'receipt_path':item['path'],'receipt_sha256':item['sha256'],'zip_path':receipt['zip_path'],'zip_sha256':receipt['zip_sha256'],
        'zip_bytes':entry['announced_zip_bytes'],'parquet_path':receipt['parquet_path'],'parquet_sha256':receipt['parquet_sha256'],
        'parquet_bytes':receipt['parquet_bytes'],'rows':checked['rows'],'observed_header':checked['header'],
        'first_timestamp_ms':checked['first_timestamp_ms'],'last_timestamp_ms':checked['last_timestamp_ms']})
assert len({(i['kind'],i['symbol'],i['month']) for i in source_rows})==24
component_path=reports/'V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V2.json';assert sha(component_path)==binding['component_receipt_sha256']
assert sum(i['zip_bytes'] for i in source_rows)==16_260_808
result={'status':'PASS_NEW_OFFICIAL_INPUT_SOURCE_FORMAT_ONLY_INDEPENDENT_QA','created_utc':datetime.now(UTC).isoformat(),
 'scope':'2025-08-01 through 2025-12-01 exclusive; BTCUSDT/ETHUSDT, fundingRate + 1m mark/index proxies; independent STATE',
 'producer_path':str(producer_path),'producer_sha256':sha(producer_path),'independent_qa_path':str(qa_path),'independent_qa_sha256':sha(qa_path),
 'protocol_path':str(protocol_path),'protocol_sha256':sha(protocol_path),'producer_source_sha256':binding['source_sha256'],'auditor_source_sha256':qa['auditor_sha256'],
 'official_component_receipt_sha256':sha(component_path),'official_component_sources':binding['official_files'],
 'accepted_format':{'archives':24,'actual_rows':703452,'funding_event_rows':732,'price_proxy_rows':702720,'price_proxy_stream_months':16,
   'funding_months':8,'timestamp_unit':'epoch milliseconds, month bounds verified; fixed 1m grid for proxies',
   'funding_header':['calc_time','funding_interval_hours','last_funding_rate'],'price_proxy_headers':'Absent in actual 16 official CSVs; 12-column API order preserved',
   'actual_interval_observation':'Each of 732 observed funding rows reports 8 nominal hours; real calc_time ms/deltas and jitter retained. No universal 8h assumption.',
   'nominal_interval_qa_tolerance_ms':1000,'raw_and_published_every_value_equal':True,'independent_zip_crc_full_read':True},
 'execution':{'preflight_session':48974,'preflight_exit_code':0,'source_session':68971,'source_exit_code':0,'qa_session':98615,'qa_exit_code':0,
    'source_elapsed_seconds':producer['elapsed_seconds'],'source_peak_rss_bytes':producer['peak_rss_bytes'],
    'qa_elapsed_seconds':qa['elapsed_seconds'],'qa_peak_rss_bytes':qa['peak_rss_bytes'],
    'raw_zip_bytes':16_260_808,'declared_csv_bytes':producer['declared_uncompressed_csv_bytes'],'owned_source_state_bytes_at_completion':producer['owned_bytes'],
    'initial_actual_disk_scan':producer['initial_disk'],'no_final_scan_claimed':True,'reserved_working_capacity_bytes':1_000_000_000,'resources_at_producer_completion':producer['resources']},
 'capabilities_preserved':{'aggtrades_153d_view_modified':False,'original_preflight_v1_source_and_receipt_sha_verified':True,
   'failed_raw_host_component_stage_preserved':True,'upstream_official_software_modified':False,'locked_consumed':False,'fits':0,'orders_sent':0,'gpu_used':False,'paid_services_or_keys_used':False},
 'remaining_requirements':{'carry_economic_state':'NOT_EVALUABLE','BBO_or_true_L5':False,'price_proxy_executable':False,'charge_mark_price_from_ohlc':False,
   'funding_calc_time_exact_charge_or_publication_semantics':'NOT_CERTIFIED_NO_API_EVENT_MATCH',
   'funding_rate_economic_encoding':'Raw numeric last_funding_rate retained without rescale; fraction interpretation requires contract/API-event mapping before economics',
   'risk_and_fees':['Both-leg historical BBO/depth/latency/size; mark/index cannot fill Spot or perp orders',
     'Applicable historical fees and account tier/discount policy; existing cost scenarios unchanged',
     'Initial/maintenance margin, liquidation/ADL, collateral and both-leg capital denominator over time',
     'Funding charge exposure and publication timing; event-associated mark not 1m candle price',
     'Borrow availability/interest if borrowed or short Spot; cash financing and transfer friction'],
   'benchmark_comparability':'Carry is not a feasible comparable benchmark until both-leg risk/capital/cost mapping exists; source QA does not change frozen benchmark/P1 states'},
 'sources':source_rows,'source_acceptance_does_not_pass_P1':True,'apr_or_candidate_claimed':False,'accepter_source_sha256':sha(Path(__file__))}
out=reports/'V8_FUNDING_MARK_INDEX_SOURCE_ACCEPTANCE_20261002_V1.json'
with out.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
event=dict.fromkeys(FIELDS)
event.update(event_id='v8-funding-mark-index-source-format-20261002-v1:acceptance',event_type='OPERATIONAL_SOURCE_ACCEPTANCE_RESULT',
 experiment_id='V8-FUNDING-MARK-INDEX-SOURCE-20261002-V1',git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 data_manifest_hash=sha(producer_path),protocol_hash=sha(protocol_path),feature_set='NONE_SOURCE_FORMAT_ONLY',labels='NONE',model_family='NONE',
 hyperparameters={'producer_sha256':sha(producer_path),'qa_sha256':sha(qa_path),'accepter_source_sha256':sha(Path(__file__))},seed=None,
 thresholds={'files':24,'rows':703452,'max_added_bytes':1_000_000_000},cost_assumptions='UNCHANGED_NOT_EVALUATED',all_folds='SOURCE_CALENDAR_ONLY',
 success_failure=result['status'],reason_for_next_experiment='Accepted raw source format can support later explicitly comparable research; current primary simple-strategy comparison not blocked',
 result_influenced_later_choice='SOURCE_READINESS_ONLY_NO_MODEL_RESULTS',fits=0,output_path=str(out),output_sha256=sha(out))
registered=append_event(root/'reports/experiment_registry.jsonl',event)
print(json.dumps({'status':result['status'],'sha256':sha(out),'registration_record_sha256':registered['record_sha256'],'raw_zip_bytes':16_260_808,'rows':703452}))
