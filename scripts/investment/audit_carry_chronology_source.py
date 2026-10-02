"""Prepared thin D031 independent source QA; no invocation until producer actual0.
Only audit_one is reused: no old24 QA/main, download, economics or fixture replay.
"""
import argparse,hashlib,importlib.util,json,os,resource,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
MONTHS=('2025-12','2026-01','2026-02');SYMBOLS=('BTCUSDT','ETHUSDT')
KINDS=('fundingRate','markPriceKlines','indexPriceKlines');LIMIT=200000000

def check(ok,message):
    if not ok:raise AssertionError(message)
def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):digest.update(block)
    return digest.hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def project(path):
    path=Path(path);return path if path.is_absolute() else ROOT/path

def safe(path,owner):
    path=Path(path);owner=Path(owner)
    check(path.is_relative_to(owner) and path.resolve().is_relative_to(owner.resolve()),'Exact new owned source subtree only')
    cursor=path
    while cursor!=owner:
        check(not cursor.is_symlink(),'Source symlink forbidden');cursor=cursor.parent
    check(not owner.is_symlink(),'Source owner symlink forbidden');return path

def task(identity):
    path=STATE/'task-progress'/('task-'+identity+'.json');row=load(path)
    check(row['id']==identity and row['status']=='completed' and row['exit_code']==0
          and type(row['pid']) is int and type(row['start_ticks']) is int,'Actual producer not completed0')
    return dict(path=str(path),sha256=sha(path),**{k:row[k] for k in ('id','status','exit_code','pid','start_ticks')})

def url(entry):
    kind,symbol,month=(entry[k] for k in ('kind','symbol','month'))
    tail=symbol+'-fundingRate-'+month+'.zip' if kind=='fundingRate' else symbol+'-1m-'+month+'.zip'
    folder='data/futures/um/monthly/'+kind+'/'+symbol+('/' if kind=='fundingRate' else '/1m/')
    return 'https://data.binance.vision/'+folder+tail

def main():
    parser=argparse.ArgumentParser()
    for name in ('protocol','receipt','run-dir','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--binding',type=Path)
    args=parser.parse_args();work=args.run_dir.resolve();out=project(args.output).resolve()
    check(work.is_relative_to(STATE) and out.is_relative_to(ROOT/'reports') and not out.exists()
          and os.environ.get('COIN_TASK_ID'),'Exclusive bounded independent audit output')
    binding_path=args.binding.resolve() if args.binding else work/'ACTUAL_BINDING.json'
    bound=load(binding_path)
    check(sha(__file__)==bound['checker_sha256'] and sys.prefix==str(STATE/'v8-clean-env-20261002-v2'),'Frozen checker/clean runtime')
    report=dict(status='FAIL_D031_OFFICIAL_SOURCE18_INDEPENDENT_QA',source_only=True,sources=[],
        binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),ACTUAL_BINDING_sha256=sha(binding_path)),
        funding_rate_unit='UNCONFIRMED',charge_publication_availability_certified=False,
        carry_economics='NOT_EVALUABLE',net_NAV_APR='NOT_EVALUABLE',models_fit=0,orders_sent=0,
        locked_consumed=False,actual_HTTP_requests=0,old_QA_or_green_replayed=False,CSV_extracted_to_disk=False)
    started=time.monotonic();event=None;append_event=None
    def progress(done,phase):
        value=dict(pid=os.getpid(),task_id=os.environ['COIN_TASK_ID'],phase=phase,completed=done,total=18,unit='档案',metrics={},
                   start_ticks=int(Path('/proc/self/stat').read_text().split(') ',1)[1].split()[19]))
        (work/'progress.json').write_text(json.dumps(value),encoding='utf-8')
    try:
        for path,digest in bound['small_input_hashes'].items():check(sha(path)==digest,'Bound input changed:'+path)
        protocol=load(project(args.protocol));source=load(project(args.receipt))
        check(sha(project(args.protocol))==bound['protocol_sha256'] and sha(project(args.receipt))==bound['producer_report_sha256'],
              'Exact source protocol/actual report')
        check(source['status']==bound['producer_complete_status'] and source['completed_files']==source['required_files']==18,
              'All18 producer outputs required, never accept a partial source run')
        producer_binding=source[bound['producer_binding_key']]
        check(producer_binding==load(bound['producer_run_binding_path']),'Actual producer RUN_BINDING bytes')
        report['producer_actual_task']=task(bound['producer_task_id'])
        check(producer_binding['task_id']==bound['producer_task_id'],'Exact producer identity')
        manifest=load(bound['manifest_path']);entries=manifest[bound['manifest_objects_key']]
        scope={(k,s,m) for k in KINDS for s in SYMBOLS for m in MONTHS}
        lookup={(e['kind'],e['symbol'],e['month']):e for e in entries}
        check(len(entries)==len(lookup)==18 and set(lookup)==scope,'Only fixed Dec-Feb BTCETH funding/mark/index scope')
        for e in entries:
            check(e['market']=='futures/um' and e['partition']=='monthly' and e['url']==url(e)
                  and e['metadata_object_available'] is True and type(e['announced_zip_bytes']) is int
                  and 0<e['announced_zip_bytes']<=2000000,'Exact canonical announced official source, no March input')
        module_path=Path(bound['audit_one_module_path'])
        check(sha(module_path)==bound['audit_one_module_sha256'],'Accepted audit_one source bytes')
        sys.path.insert(0,str(ROOT))
        spec=importlib.util.spec_from_file_location('frozen_source_audit_one',module_path)
        auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
        owner=Path(bound['producer_run_dir']);check(owner.is_relative_to(STATE),'Explicit new source owner')
        from scripts.research_v8.registry import FIELDS,append_event
        run_binding=dict(command=[sys.executable,*sys.argv],task_id=os.environ['COIN_TASK_ID'],
            git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            checker_sha256=sha(__file__),auditor_module_sha256=sha(module_path),
            actual_binding_sha256=sha(binding_path),source_hashes=bound['small_input_hashes'],
            producer_report_sha256=sha(project(args.receipt)),protocol_sha256=sha(project(args.protocol)))
        run_binding_path=work/'RUN_BINDING.json'
        with run_binding_path.open('x',encoding='utf-8') as f:json.dump(run_binding,f,indent=2);f.write('\n')
        identity='D031-CHRONOLOGY-SOURCE18-INDEPENDENT-QA-20261003-V1'
        event=dict.fromkeys(FIELDS)
        event.update(event_id=identity+':START',event_type='OPERATIONAL_SOURCE_AUDIT_START',experiment_id=identity,
            git_commit=run_binding['git_commit'],data_manifest_hash=sha(bound['manifest_path']),protocol_hash=run_binding['protocol_sha256'],
            feature_set='NONE_SOURCE_ONLY',labels='NONE',model_family='NONE',hyperparameters={'archives':18,'auditor_sha256':sha(module_path)},
            seed=None,thresholds={'declared_CSV_bytes':LIMIT,'source_owned_bytes':LIMIT},cost_assumptions='NOT_EVALUATED_UNCHANGED',
            all_folds='FIXED2025DEC2026JANFEB_SOURCE_ONLY',success_failure='START_BEFORE_NEW18_INDEPENDENT_RAW_QA',
            reason_for_next_experiment='Accept raw/archive/Parquet identity and reported calendars, no carry economics or unit promotion',
            result_influenced_later_choice='NO_ECONOMIC_RESULT',fits=0,source_hashes=bound['small_input_hashes'],
            exact_command=' '.join(run_binding['command']),run_binding_sha256=sha(run_binding_path))
        report['registration_start']=append_event(ROOT/'reports/experiment_registry.jsonl',event)
        report['run_binding_sha256']=sha(run_binding_path);progress(0,'独立新18档来源QA')
        completed=set();declared=0
        for item in source['sources']:
            receipt_path=safe(item['path'],owner);check(sha(receipt_path)==item['sha256'],'Per-file receipt bytes')
            receipt=load(receipt_path);entry=receipt['entry'];key=(entry['kind'],entry['symbol'],entry['month'])
            check(key in scope and key not in completed and entry==lookup[key],'All18 unique manifest-bound entries')
            job=owner/('-'.join(key));check(receipt_path==job/'receipt.json','Exact newly owned source receipt path')
            relative=entry['url'].removeprefix('https://data.binance.vision/')
            paths=(safe(receipt['zip_path'],job),safe(receipt['checksum_path'],job),safe(receipt['parquet_path'],job))
            check(paths==(job/'raw'/relative,job/'raw'/(relative+'.CHECKSUM'),job/'source.parquet'),'Exact published archive/checksum/Parquet paths')
            declared+=receipt['uncompressed_csv_bytes'];check(0<declared<=LIMIT,'Declared CSV aggregate exceeds200MB')
            with zipfile.ZipFile(paths[0]) as archive:
                members=archive.infolist()
                check(len(members)==1 and members[0].filename==paths[0].name.removesuffix('.zip')+'.csv'
                      and not members[0].flag_bits&1,'Canonical one unencrypted CSV member')
            result=auditor.audit_one(receipt,protocol)  # Exactly once per NEW archive; old main never called.
            for p,digest in zip(paths,(receipt['zip_sha256'],receipt['checksum_sha256'],receipt['parquet_sha256']),strict=True):
                check(sha(p)==digest,'New source bytes changed during independent raw/parquet QA')
            result.update(receipt_path=str(receipt_path),receipt_sha256=item['sha256'])
            report['sources'].append(result);completed.add(key)
            check(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=512000000,'Independent512MB RSS bound')
            progress(len(completed),'独立新18档来源QA')
            print(json.dumps(dict(completed_files=len(completed),required_files=18)),flush=True)
        check(completed==scope,'All18 sources independently verified')
        for symbol in SYMBOLS:
            rows=sorted((r for r in report['sources'] if r['kind']=='fundingRate' and r['symbol']==symbol),key=lambda r:r['month'])
            for a,b in zip(rows,rows[1:]):
                gap=b['first_timestamp_ms']-a['last_timestamp_ms'];tolerance=protocol['funding_nominal_interval_tolerance_ms']
                check(any(abs(gap-h*3600000)<=tolerance for h in (a['last_interval_hours'],b['first_interval_hours'])),
                      'Actual adjacent-month funding gap, no assumed8h/event count')
        owned=sum(p.stat().st_size for p in owner.rglob('*') if p.is_file())
        check(owned<=LIMIT and time.monotonic()-started<=600,'Source owned200MB/audit wall600 budget')
        for path,digest in bound['small_input_hashes'].items():check(sha(path)==digest,'Bound input changed during QA')
        report.update(status='PASS_D031_OFFICIAL_SOURCE18_FORMAT_ONLY_INDEPENDENT_QA',actual_archives=18,
            funding_archives=6,price_proxy_archives=12,actual_rows=sum(r['rows'] for r in report['sources']),
            actual_funding_events=sum(r['rows'] for r in report['sources'] if r['kind']=='fundingRate'),
            declared_uncompressed_csv_bytes=declared,actual_source_owned_bytes=owned,
            cross_month_funding_gaps='PASS_ADJACENT_REPORTED_INTERVALS_WITH_FROZEN_JITTER',
            economics_or_unit_gate_passed=False,verified_source_hashes=bound['small_input_hashes'])
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        with out.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
        if event is not None:
            append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=event['experiment_id']+':RESULT',
                event_type='OPERATIONAL_SOURCE_AUDIT_RESULT',success_failure=report['status'],output_path=str(out),output_sha256=sha(out)))
    print(json.dumps(dict(status=report['status'],report_sha256=sha(out))))
if __name__=='__main__':main()