"""Reuse sealed monthly minute QA for only July--November 2025; no price rows read."""
from datetime import UTC,date,datetime,timedelta
import calendar,hashlib,json,sqlite3,subprocess,sys,time
from pathlib import Path
import pyarrow.parquet as pq

root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state');sys.path.insert(0,str(root))
from scripts.research_v8.registry import FIELDS,append_event,canonical
from scripts.research_v8.funding_price_source_v2 import progress_writer
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
run=state/'v8-existing-spot-minute-frozen-qa-reuse-20261002-v1';assert not run.exists();run.mkdir()
lock_path=root/'state/dataset_lock.json';lock=json.loads(lock_path.read_bytes())
quality_path=root/'reports/generated/DATA_QUALITY_REPORT.json'
assert sha(quality_path)==lock['quality_report_sha256'],'Existing sealed QA report changed'
policy_path=root/'configs/dataset_policy.json';assert sha(policy_path)==lock['dataset_policy_sha256']
meta_path=root/'reports/fast_research/V8_EXISTING_SPOT_MINUTE_SOURCE_METADATA_20261002_V1.json';meta=json.loads(meta_path.read_bytes())
previous={(r['symbol'],r['month']):r for r in meta['archives']}
spec={'scope':'Reuse old frozen source QA; only ten allowed July-Nov monthly minute files, no aggregate bars/locked price rows',
      'source_sha256':sha(Path(__file__)),'sealed_lock_sha256':sha(lock_path),'sealed_qa_report_sha256':sha(quality_path),
      'policy_sha256':sha(policy_path),'prior8zip_sha256':sha(meta_path),'source_calendar':['2025-07','2025-08','2025-09','2025-10','2025-11'],
      'symbols':['BTCUSDT','ETHUSDT'],'data_py_source_sha256':sha(root/'src/quant/data.py')}
event=dict.fromkeys(FIELDS)
event.update(event_id='v8-existing-spot-minute-qa-reuse-20261002-v1:start',event_type='OPERATIONAL_SOURCE_METADATA_REUSE_START',
 experiment_id='V8-EXISTING-SPOT-MINUTE-QA-REUSE-20261002-V1',git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 data_manifest_hash=sha(lock_path),protocol_hash=hashlib.sha256(canonical(spec)).hexdigest(),feature_set='NONE_SOURCE_ONLY',labels='NONE',model_family='NONE',
 hyperparameters=spec,seed=None,thresholds={'allowed_months':5,'files':10},cost_assumptions='UNCHANGED_NOT_EVALUATED',all_folds='WARMUP_PLUS_SOURCE_MONTHS_ONLY',
 success_failure='START_BEFORE_SELECTED_SOURCE_BINDING_VERIFICATION',reason_for_next_experiment='Existing sealed Spot1m source supports new simple-strategy comparison without new ingestion',
 result_influenced_later_choice='EXISTING_SOURCE_QA_ONLY',fits=0)
binding={'command':[sys.executable,*sys.argv],'spec':spec,'source_sha256':sha(Path(__file__))}
with (run/'RUN_BINDING.json').open('x') as f:json.dump(binding,f,indent=2)
start=append_event(root/'reports/experiment_registry.jsonl',event)
report={'status':'FAILED_EXISTING_FROZEN_SPOT_MINUTE_SOURCE_REUSE','registration_start':start,'binding':binding,'sources':[],
 'price_rows_or_model_results_read':False,'locked_consumed':False,'aggregated_bars_read':False,'source_modified':False,'new_source_downloaded':False,
 'live_collector_pid540_not_assumed_to_use_default_db':True,'scope':'Only July-Nov 2025 old source manifests and actual file hashes/Parquet metadata',
 'economic_state':'NOT_EVALUATED_OHLC_PROXY_NOT_BBO_FILL'}
progress=progress_writer(10);started=time.monotonic()
try:
    with sqlite3.connect(f'file:{state}/archive_manifest.sqlite3?mode=ro',uri=True,timeout=5) as db:
        db.row_factory=sqlite3.Row
        for symbol in spec['symbols']:
            for month in spec['source_calendar']:
                name=f'{symbol}-1m-{month}.zip';raw=root/'data/raw/spot'/symbol/'1m'/name
                check=raw.with_name(name+'.CHECKSUM');normalized=root/'data/normalized/spot'/symbol/'1m'/f'{month}.parquet'
                row=db.execute('SELECT * FROM archives WHERE name=? AND symbol=? AND month=?',(name,symbol,month)).fetchone()
                assert row is not None,'No existing qualified manifest for '+name
                manifest=dict(row);quality=json.loads(manifest['quality_json']);relative=str(normalized.relative_to(root))
                assert manifest['status']=='ingested' and sha(raw)==manifest['sha256']
                fields=check.read_text().split();assert len(fields)==2 and fields[0].lower()==manifest['sha256'] and fields[1].lstrip('*')==name
                assert sha(normalized)==manifest['normalized_sha256']==lock['minute_files'][relative]
                expected=calendar.monthrange(2025,int(month[-2:]))[1]*1440
                assert manifest['rows']==quality['rows']==quality['expected_rows']==expected
                assert manifest['timestamp_unit']==quality['timestamp_unit']=='microseconds'
                assert quality['missing_rows']==quality['bad_timestamps']==quality['bad_values']==quality['duplicate_rows']==quality['quarantined_rows']==0
                assert not quality['incomplete_days'] and not quality['quarantined_days'] and not quality.get('missing_start') and not quality.get('missing_end')
                opened=int(datetime(2025,int(month[-2:]),1,tzinfo=UTC).timestamp()*1_000_000)
                assert quality['first_open_us']==opened and quality['last_open_us']==opened+(expected-1)*60_000_000
                parquet_metadata=pq.read_metadata(normalized);schema=pq.read_schema(normalized)
                assert parquet_metadata.num_rows==expected and str(schema.field('open_us').type)=='int64'
                if (symbol,month) in previous:
                    old=previous[(symbol,month)];assert old['zip_sha256']==manifest['sha256'] and old['checksum_matches'] and old['crc_full_read']
                    crc='REUSED_PRIOR_EXACT_ZIP_CRC_REPORT'
                else:
                    import zipfile
                    with zipfile.ZipFile(raw) as archive:assert archive.testzip() is None
                    crc='NEW_READ_ONLY_JULY_ZIP_CRC_PASS'
                report['sources'].append({'symbol':symbol,'month':month,'zip_path':str(raw),'zip_sha256':manifest['sha256'],
                    'checksum_sha256':sha(check),'normalized_path':str(normalized),'normalized_sha256':manifest['normalized_sha256'],
                    'rows':expected,'timestamp_unit':'microseconds','old_quality':quality,'actual_parquet_schema':str(schema),
                    'crc':crc,'calendar_qa':'REUSED_EXACT_SEALED_ORIGINAL_QA_BINDING_NO_MARKET_PRICE_READ'})
                progress.update('已冻结Spot分钟源逐档复用核对',len(report['sources']),10,'文件')
    report.update(status='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_153D_CALENDAR',source_files=10,days_per_symbol=153,
                  actual_minute_rows=440640,complete_days_across_symbols=306,old_qualified_calendar_evidence_reused=True)
except Exception as error:report.update(error_type=type(error).__name__,reason=str(error)[:1024]);raise
finally:
    report['elapsed_seconds']=time.monotonic()-started
    out=root/'reports/fast_research/V8_EXISTING_FROZEN_SPOT_MINUTE_SOURCE_REUSE_20261002_V1.json'
    with out.open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    append_event(root/'reports/experiment_registry.jsonl',dict(event,event_id='v8-existing-spot-minute-qa-reuse-20261002-v1:result',
       event_type='OPERATIONAL_SOURCE_METADATA_REUSE_RESULT',success_failure=report['status'],output_path=str(out),output_sha256=sha(out)))
    progress.stop.set();progress.thread.join(timeout=3)
print(json.dumps({'status':report['status'],'sha256':sha(out),'source_files':report.get('source_files'),'rows':report.get('actual_minute_rows'),'elapsed_seconds':report['elapsed_seconds']}))
