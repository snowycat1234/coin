"""Bounded older-cycle orchestration of existing official download/QA APIs."""
import argparse, gc, hashlib, json, os, resource, time
from datetime import UTC, datetime
from pathlib import Path
import httpx
import polars as pl
from quant import disk, resources
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_trade_source as trade
from scripts.investment import perpetual_history_source as history
from scripts.investment import audit_perpetual_trade_source as trade_audit
from scripts.investment.official_carry_chronology_source import metadata_inspector
from scripts.research_v8 import funding_price_source_v2 as source
from scripts.research_v8 import audit_funding_price_source as price_audit
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v8.registry import FIELDS, append_event


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')


def main():
    ap=argparse.ArgumentParser()
    for key in ('protocol','run-dir','output'):ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--mode',choices=['metadata','source'],required=True);a=ap.parse_args()
    spec=json.loads(a.protocol.read_bytes());run=a.run_dir.resolve();out=a.output.resolve()
    assert os.getenv('COIN_TASK_ID') and run.parent==STATE and not run.exists()
    assert out.parent==ROOT/'reports/fast_research' and not out.exists()
    assert sha(__file__)==spec['source_hashes']['scripts/investment/cta_cycle_source.py']
    for p,h in spec['source_hashes'].items():assert sha(ROOT/p)==h,p
    assert sha(ROOT/'state/dataset_lock.json')==spec['locked_sha256']
    entries=spec['entries'];assert len(entries)==len({v['url'] for v in entries}) and entries
    for e in entries:
        assert e['symbol'] in ('BTCUSDT','ETHUSDT') and '2021-01'<=e['month']<='2023-12'
        assert e['kind'] in ('klines','markPriceKlines','fundingRate')
        interval=e.get('interval')
        assert interval in ('1m','1d') if e['kind']=='klines' else interval=='1m' if e['kind']=='markPriceKlines' else interval is None
        suffix=f"{e['symbol']}-fundingRate-{e['month']}.zip" if e['kind']=='fundingRate' else f"{interval}/{e['symbol']}-{interval}-{e['month']}.zip"
        assert e['url']==f"https://data.binance.vision/data/futures/um/monthly/{e['kind']}/{e['symbol']}/{suffix}"
        assert e['checksum_url']==e['url']+'.CHECKSUM'
    run.mkdir();progress=Progress();started=time.monotonic();peak=0
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),source_hashes=spec['source_hashes'],
        protocol_sha256=sha(a.protocol),git_commit=spec['parent_commit'],mode=a.mode)
    r=dict(status='FAILED_CYCLE_SOURCE',binding=binding,protocol=spec,run_dir=str(run),objects=[],sources=[],
        new_accounts=0,fits=0,locked_body_read=False,native_Bybit_certified=False,funding_unit_certified=False,economics='NOT_RUN')
    event=dict.fromkeys(FIELDS);event.update(experiment_id=spec['experiment_id'],event_id=spec['experiment_id']+':'+run.name+':'+a.mode+':START',
        event_type='OPERATIONAL_SOURCE_START',git_commit=spec['parent_commit'],protocol_hash=sha(a.protocol),
        feature_set='NONE_SOURCE_ONLY',labels='NONE',model_family='NONE',models_fit=0,hyperparameters=spec['scope'],
        success_failure='START_BEFORE_NEW_NETWORK',reason_for_next_experiment=spec['question'],result_influenced_later_choice=False)
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    def guard():
        nonlocal peak
        peak=max(peak,resources.status()['ram_current_bytes'])
        assert time.monotonic()-started<spec['budget']['wall_seconds']
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<spec['budget']['RSS_bytes']
        assert sum(p.stat().st_size for p in run.rglob('*') if p.is_file())<spec['budget']['owned_bytes']
    try:
        if a.mode=='metadata':
            with httpx.Client(timeout=httpx.Timeout(12,connect=10),follow_redirects=False) as client:
                inspect=metadata_inspector(client)
                for i,e in enumerate(entries):
                    guard();v=inspect(e);r['objects'].append(v);save(run/f'METADATA-{i}.json',v)
                    progress.update('旧周期官方HEAD与CHECKSUM可用性',i+1,len(entries),'文件')
            r['status']='PASS_CYCLE_METADATA_ONLY_NO_ARCHIVE_BODIES'
            r['all_objects_available']=all(v['metadata_object_available'] and isinstance(v['announced_zip_bytes'],int) and 0<v['announced_zip_bytes']<=16_000_000 for v in r['objects'])
            r['announced_zip_bytes']=sum(v['announced_zip_bytes'] or 0 for v in r['objects'])
        else:
            meta_path=ROOT/spec['metadata']['path'];assert sha(meta_path)==spec['metadata']['sha256']
            metadata=json.loads(meta_path.read_bytes());assert metadata['status']=='PASS_CYCLE_METADATA_ONLY_NO_ARCHIVE_BODIES' and metadata['all_objects_available']
            tid=metadata['binding']['task_id'];t=json.loads((STATE/'task-progress'/('task-'+tid+'.json')).read_bytes())
            assert t['status']=='completed' and t['exit_code']==0
            assert [{k:v[k] for k in e} for v,e in zip(metadata['objects'],entries)]==entries
            assert metadata['announced_zip_bytes']<spec['budget']['max_announced_zip_sum']
            r['objects']=metadata['objects']
            progress.update('旧周期新增来源前磁盘实扫；总量未知',None,None,'扫描')
            r['disk_before']=dict(disk.check(spec['budget']['owned_bytes']),measured_utc=datetime.now(UTC).isoformat())
            component=ROOT/spec['component']['path'];assert sha(component)==spec['component']['sha256']
            upstream=source.official_module(json.loads(component.read_bytes()))
            download,parsers,_,_,_=history.adapted_functions();g=trade_audit.guards()
            reused={}
            for ref in spec.get('reuse_completed_sources',[]):
                prior_path=ROOT/ref['path'];assert sha(prior_path)==ref['sha256']
                prior=json.loads(prior_path.read_bytes())
                task=json.loads((STATE/'task-progress'/('task-'+prior['binding']['task_id']+'.json')).read_bytes())
                assert task['status'] in ('completed','failed') and task['ended_at']
                for row in prior['sources']:
                    url=row['entry']['url'];assert url not in reused
                    receipt_path=Path(row['receipt_path']);assert receipt_path.is_relative_to(STATE) and sha(receipt_path)==row['receipt_sha256']
                    receipt=json.loads(receipt_path.read_bytes())
                    proof=json.loads((receipt_path.parent/'INDEPENDENT_RAW_REFERENCE.json').read_bytes())
                    assert proof==row['independent_reference']
                    if row['entry']['kind']=='klines':assert proof['all_raw_normalized_values_equal'] and proof['full_CSV_EOF_and_CRC_read']
                    else:assert proof['status']=='PASS_SOURCE_FORMAT_ONLY' and proof['all_published_values_equal_raw'] and proof['zip_crc_full_read']
                    for path_key,hash_key in [('zip_path','zip_sha256'),('checksum_path','checksum_sha256'),
                            ('normalized_path','normalized_sha256') if row['entry']['kind']=='klines' else ('parquet_path','parquet_sha256')]:
                        p=Path(receipt[path_key]);assert p.is_relative_to(STATE) and sha(p)==receipt[hash_key]
                    reused[url]=dict(row,reuse_report=ref)
                    reused[url].setdefault('acquisition','REUSED_COMPLETED_INDEPENDENT_RAW_REFERENCE_NO_DOWNLOAD_OR_QA')
            extra_daily=sum(len(row.get('official_archive_parents',[]))-1 for row in reused.values() if row.get('official_archive_parents'))
            extra_daily+=sum(row.get('source_composition',{}).get('extra_official_daily_archives',0) for row in reused.values())
            for i,e in enumerate(r['objects']):
                guard()
                if e['url'] in reused:
                    row=reused[e['url']];assert row['entry']==e
                    r['sources'].append(row);progress.update('旧周期官方档下载与独立原CSV核对',i+1,len(entries),'文件');continue
                name=f"{e['symbol']}-{e.get('interval','fundingRate')}-{e['month']}"
                if e['kind']!='klines':name=e['kind']+'-'+name
                job=run/name;job.mkdir()
                with trade.file_deadline():
                    archive,checksum,csv_bytes=download(e,job,upstream)
                    if e['kind']=='klines':
                        frame,quality=trade.convert(archive,e,parsers);parquet=job/'source.parquet';frame.write_parquet(parquet,compression='zstd');rows=frame.height;schema={k:str(v) for k,v in frame.schema.items()};del frame
                        receipt=dict(status='PASS_USDM_TRADE_ARCHIVE_FORMAT_CALENDAR_ONLY',entry=e,zip_path=str(archive),zip_sha256=sha(archive),
                            checksum_path=str(checksum),checksum_sha256=sha(checksum),uncompressed_csv_bytes=csv_bytes,
                            normalized_path=str(parquet),normalized_sha256=sha(parquet),normalized_bytes=parquet.stat().st_size,
                            rows=rows,quality=quality,normalized_schema=schema)
                        save(job/'receipt.json',receipt);item=dict(receipt,receipt_path=str(job/'receipt.json'),receipt_sha256=sha(job/'receipt.json'))
                        bare={k:e[k] for k in ('market','partition','kind','symbol','month','url','checksum_url','interval')}
                        proof=trade_audit.audit_one(g,item,bare,run,dict(budgets=trade.BOUNDS))
                    else:
                        parquet=job/'source.parquet';receipt_entry=e;derivation=None
                        try:stats=source.convert_source(archive,e,spec['format_rules'],parquet)
                        except ValueError as error:
                            assert e['kind']=='markPriceKlines' and str(error) in ('Complete fixed-1m calendar required','Missing/shifted minute') and spec.get('official_mark_daily_completion_max',0)>extra_daily
                            from scripts.investment.official_mark_day_completion import complete
                            if parquet.exists():parquet.rename(job/'incomplete-monthly-source.parquet')
                            archive,checksum,csv_bytes,receipt_entry,derivation=complete(archive,e,job,upstream,
                                spec['format_rules']['price_header'],spec['official_mark_daily_completion_max']-extra_daily)
                            extra_daily+=derivation['extra_official_daily_archives']
                            stats=source.convert_source(archive,receipt_entry,spec['format_rules'],parquet)
                        receipt=dict(status='SOURCE_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA',entry=receipt_entry,zip_path=str(archive),zip_sha256=sha(archive),
                            checksum_path=str(checksum),checksum_sha256=sha(checksum),uncompressed_csv_bytes=csv_bytes,
                            parquet_path=str(parquet),parquet_sha256=sha(parquet),parquet_bytes=parquet.stat().st_size,stats=stats)
                        if derivation:receipt['derivation']=derivation
                        save(job/'receipt.json',receipt);proof=price_audit.audit_one(receipt,spec['format_rules'])
                    save(job/'INDEPENDENT_RAW_REFERENCE.json',proof)
                    completed_row=dict(entry=e,receipt_path=str(job/'receipt.json'),receipt_sha256=sha(job/'receipt.json'),independent_reference=proof)
                    if e['kind']!='klines' and derivation:completed_row['source_composition']=derivation
                    r['sources'].append(completed_row)
                save(run/f'CHECKPOINT-{i}.json',dict(completed=len(r['sources']),required=len(entries)))
                progress.update('旧周期官方档下载与独立原CSV核对',i+1,len(entries),'文件');gc.collect();guard()
            r['extra_official_daily_archives']=extra_daily
            r['status']='PASS_CYCLE_OFFICIAL_RAW_REFERENCE_FORMAT_NOT_ECONOMICS'
    except Exception as e:r.update(error_type=type(e).__name__,error=str(e));raise
    finally:
        r.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,shared_sampled_peak=peak,
            owned_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()))
        save(out,r);append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=spec['experiment_id']+':'+run.name+':'+a.mode+':RESULT',
            event_type='OPERATIONAL_SOURCE_RESULT',success_failure=r['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=r['status'],available=r.get('all_objects_available'),sources=len(r['sources']))))


if __name__=='__main__':main()
