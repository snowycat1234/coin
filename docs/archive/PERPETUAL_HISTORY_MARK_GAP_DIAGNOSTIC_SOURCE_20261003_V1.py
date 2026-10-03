"""Only the failed BTC August2024 mark archive: clock/CRC diagnostic, no prices.

No download, producer parser, old83 QA, accepted source claim or economics.
Read CSV columns0/6 only and the partial Parquet footer; do not read its rows.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, importlib.util, io, json, os, resource, shlex, subprocess, sys, time, zipfile
from datetime import UTC, datetime
from pathlib import Path
import pyarrow.parquet as pq
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
STATUS='COMPLETE_D042_INDEPENDENT_RAW_MARK_CLOCK_GAP_DIAGNOSTIC_SOURCE_REJECTED_NO_ECONOMICS'
FAIL='FAIL_D042_INDEPENDENT_MARK_GAP_DIAGNOSTIC'
BUDGET=dict(peak_RSS_bytes=512_000_000,wall_seconds=120,new_owned_bytes=5_000_000,report_bytes=2_000_000)
HEADER=['open_time','open','high','low','close','volume','close_time','quote_volume','count','taker_buy_volume','taker_buy_quote_volume','ignore']
JOB=STATE/'d042-perpetual-history-source-20261003-v1/markPriceKlines-BTCUSDT-2024-08'
FIRST=int(datetime(2024,8,1,tzinfo=UTC).timestamp())*1000
END=int(datetime(2024,9,1,tzinfo=UTC).timestamp())*1000

def need(ok,reason):
    if not bool(ok):raise ValueError(reason)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def utc(value):return datetime.fromtimestamp(value/1000,UTC).isoformat()

def guards():
    p=ROOT/GUARD;need(not p.is_symlink() and sha(p)==GUARD_SHA,'Exact accepted metadata/task guards')
    s=importlib.util.spec_from_file_location('d042_gap_metadata_guards',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def payload(item):
    p=Path(item['path']);need(p.is_file() and p.is_relative_to(JOB) and '..' not in p.parts,'Only failed month payload')
    for parent in (p,*p.parents):
        need(not parent.is_symlink(),'No failed source symlink')
        if parent==STATE:break
    need(p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],'Frozen failed payload size/SHA');return p

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','run-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();g=guards();own=sha(__file__);plan,plan_sha=g.small(a.protocol)
    need(os.getenv('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2'),'Actual bounded clean/progress runtime')
    need(plan['ready_to_execute'] is True and plan['contract_id']=='D042_ONE_FAILED_MARK_MONTH_CLOCK_DIAGNOSTIC_V1'
        and plan['checker_sha256']==own and plan['budgets']==BUDGET and plan['job']==str(JOB)
        and plan['run_dir']==str(a.run_dir) and plan['output']==str(a.output),'Fixed one-month preregistered scope')
    need(a.run_dir==STATE/'d042-mark-gap-independent-20261003-v1' and not a.run_dir.exists()
        and a.output==ROOT/'reports/fast_research/PERPETUAL_HISTORY_MARK_GAP_DIAGNOSTIC_20261003_V1.json'
        and not a.output.exists(),'Exclusive diagnostic artifacts')
    a.run_dir.mkdir();began=time.monotonic();before=resources.status()
    binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=own,protocol_sha256=plan_sha,
        source_hashes=plan['source_hashes'],exact_command=shlex.join([sys.executable,*sys.argv]),
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    g.write(a.run_dir/'RUN_BINDING.json',binding)
    report=dict(status=FAIL,binding=binding,run_dir=str(a.run_dir),run_binding_sha256=sha(a.run_dir/'RUN_BINDING.json'),
        independent_source_sha256=own,failed_producer_report_sha256=plan['failed_report']['sha256'],
        original_source_accepted=False,source_gap_repaired=False,price_values_parsed_or_analyzed=False,partial_Parquet_rows_read=False,
        old83_QA_repeated=False,HTTP_requests=0,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,
        economics='NOT_COMPUTED',funding_rate_unit='UNCONFIRMED',candidate_status='NO_QUALIFIED_CANDIDATE')
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D042-ONE-MARK-GAP-DIAGNOSTIC-20261003-V1',event_id=binding['task_id']+':START',
        event_type='INDEPENDENT_SOURCE_DIAGNOSTIC_START',git_commit=binding['git_commit'],data_manifest_hash=plan['failed_report']['sha256'],
        protocol_hash=plan_sha,feature_set='ONE_FAILED_BTC_2024AUG_MARK_CLOCK_ONLY',labels='NONE',model_family='NONE',seed=None,
        thresholds=BUDGET,cost_assumptions='NOT_COMPUTED',all_folds='ONE_FAILED_OFFICIAL_MONTH',success_failure='START_BEFORE_RAW_CLOCK_READ',
        reason_for_next_experiment='Determine actual source gap without filtering, filling or economic calculation',
        result_influenced_later_choice=False,source_hashes=plan['source_hashes'],exact_command=binding['exact_command'])
    report['registration_start']=append_event(ROOT/'reports/experiment_registry.jsonl',event);error=None
    try:
        g.bounded(before);failed,failed_sha=g.small(ROOT/plan['failed_report']['path'],plan['failed_report']['sha256'])
        report['failed_producer_actual_task']=g.closed(plan['failed_task_id'],1)
        need(failed['binding']['task_id']==plan['failed_task_id'] and failed['status']=='FAIL_D042_HISTORY_SOURCE'
            and failed['completed_files']==83 and failed['archive_bodies_downloaded']==84 and failed['reason']=='Missing/shifted minute',
            'Exact failed producer task/scope; not accepted source')
        for name,digest in plan['source_hashes'].items():g.small(g.project(name),digest,False)
        receipt,_=g.small(JOB/'receipt.json',plan['receipt_sha256']);entry=receipt['entry']
        need(receipt['status']=='FAIL_D042_ARCHIVE' and receipt['reason']=='Missing/shifted minute'
            and (entry['kind'],entry['symbol'],entry['interval'],entry['month'])==('markPriceKlines','BTCUSDT','1m','2024-08'),
            'Exact one failed official month receipt')
        archive=payload(plan['archive']);checksum=payload(plan['checksum']);partial=payload(plan['partial_Parquet'])
        name='BTCUSDT-1m-2024-08.zip';fields=checksum.read_text().split()
        need(archive.name==name and len(fields)==2 and fields[1].lstrip('*')==name
            and fields[0].lower()==plan['archive']['sha256']==entry['checksum']['announced_zip_sha256']
            and archive.stat().st_size==entry['announced_zip_bytes'],'Actual official CHECKSUM and HEAD byte identity')
        report['official_archive_identity']=dict(**plan['archive'],checksum=plan['checksum'],announced_SHA_matches=True)
        meta=pq.ParquetFile(partial).metadata
        report['partial_Parquet_footer_only']=dict(**plan['partial_Parquet'],rows=meta.num_rows,row_groups=meta.num_row_groups,
            columns=meta.num_columns,serialized_footer_bytes=meta.serialized_size,not_accepted=True)
        clocks=[];header=None;bad=[];width_bad=[]
        with zipfile.ZipFile(archive) as z:
            members=z.infolist();need(len(members)==1 and members[0].filename==name[:-4]+'.csv' and not members[0].flag_bits&1,'One original unencrypted CSV')
            need(0<members[0].file_size<=128_000_000,'Bounded original CSV')
            with z.open(members[0]) as stream,io.TextIOWrapper(stream,encoding='utf-8-sig',newline='') as text:
                for line,raw in enumerate(csv.reader(text),1):
                    if line==1 and raw and raw[0]=='open_time':need(raw==HEADER,'Original optional header');header=raw;continue
                    if len(raw)!=12:width_bad.append(line);continue
                    if not all(raw[i].isascii() and raw[i].isdecimal() for i in (0,6)):bad.append(line);continue
                    clocks.append((int(raw[0]),int(raw[6])))
            need(z.testzip() is None,'Actual full independent ZIP CRC')
            report['raw_CSV']=dict(header=header,all_data_rows=len(clocks)+len(bad)+len(width_bad),parsed_clock_rows=len(clocks),
                invalid_clock_rows=len(bad),invalid_width_rows=len(width_bad),invalid_clock_row_witnesses=bad[:64],
                invalid_width_row_witnesses=width_bad[:64],CSV_declared_bytes=members[0].file_size,full_EOF_and_CRC=True)
        opens=[r[0] for r in clocks];counter=collections.Counter(opens);expected=set(range(FIRST,END,60_000))
        missing=sorted(expected-set(opens));duplicates=sorted((t,n) for t,n in counter.items() if n>1)
        backward=[dict(row=i+1,previous=a,current=b) for i,(a,b) in enumerate(zip(opens,opens[1:]),1) if b<a]
        outside=[t for t in opens if not FIRST<=t<END];shifted=[t for t in opens if t%60_000]
        wrong_closes=[(i+1,o,c) for i,(o,c) in enumerate(clocks) if c!=o+59_999]
        clock_bytes=(json.dumps(clocks,separators=(',',':'))+'\n').encode();clock_path=a.run_dir/'ALL_RAW_CLOCK_PAIRS.json'
        need(len(clock_bytes)<=4_000_000,'Full clock-only metadata bound')
        with clock_path.open('xb') as stream:stream.write(clock_bytes)
        report['clock_evidence']=dict(path=str(clock_path),sha256=sha(clock_path),bytes=len(clock_bytes),columns=['raw_open_ms','raw_inclusive_close_ms'],contains_prices=False)
        report['raw_clock_diagnostic']=dict(expected_UTC_minutes=44_640,missing_minutes=len(missing),missing_UTC_minutes=[utc(t) for t in missing],
            missing_UTC_minutes_count=len(missing),missing_utc_days=sorted({utc(t)[:10] for t in missing}),first_gapUTC=utc(missing[0]) if missing else None,
            duplicate_extra_rows=sum(n-1 for _,n in duplicates),duplicate_unique_timestamps=len(duplicates),duplicate_witnesses=[dict(UTC=utc(t),rows=n) for t,n in duplicates[:64]],
            backward_rows=len(backward),backward_witnesses=backward[:64],out_of_month_rows=len(outside),out_of_month_witnesses=outside[:64],
            shifted_open_rows=len(shifted),shifted_open_witnesses=shifted[:64],wrong_inclusive_close_rows=len(wrong_closes),wrong_close_witnesses=wrong_closes[:64],
            first_raw_open_UTC=utc(opens[0]) if opens else None,last_raw_open_UTC=utc(opens[-1]) if opens else None,
            defect_witness_limit=64,all_clock_values_preserved_in_STATE=True,raw_timestamp_unit='EPOCH_MILLISECONDS')
        need(missing or duplicates or backward or outside or shifted or wrong_closes or bad or width_bad,'Actual clock defect must explain source rejection')
        for item in (plan['archive'],plan['checksum'],plan['partial_Parquet']):payload(item)
        g.small(JOB/'receipt.json',plan['receipt_sha256']);g.small(ROOT/plan['failed_report']['path'],failed_sha)
        report.update(status=STATUS,verified_source_hashes=plan['source_hashes'],independently_diagnosed_archives=1,source_qualification='REJECTED_GAP_NOT_REPAIRED')
    except Exception as caught:error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        report.update(elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            resources_before=before,resources_after=resources.status(),own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
        try:g.bounded(report['resources_after'])
        except Exception as caught:error=error or caught;report['budget_error']=str(caught)
        if report['elapsed_seconds']>120 or report['peak_RSS_bytes']>512_000_000:error=error or RuntimeError('Fixed diagnostic wall/RSS bound')
        if error:report['status']=FAIL
        digest,size=g.write(a.output,report)
        need(sum(p.stat().st_size for p in a.run_dir.iterdir() if p.is_file())+size<=5_000_000,'Clock-only STATE/report5MB budget')
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=binding['task_id']+':RESULT',event_type='INDEPENDENT_SOURCE_DIAGNOSTIC_RESULT',
            success_failure=report['status'],artifact_path=a.output.relative_to(ROOT).as_posix(),artifact_sha256=digest))
        print(json.dumps(dict(status=report['status'],report=str(a.output),sha256=digest,task_id=binding['task_id'])),flush=True)
    if error:raise error

if __name__=='__main__':main()
