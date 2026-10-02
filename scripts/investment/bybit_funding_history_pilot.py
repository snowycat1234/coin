"""Two fixed native Bybit history requests; no income, price or account IO."""
from __future__ import annotations
import argparse
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shlex
import subprocess
import sys
import time
from urllib.parse import urlencode

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
WORK = STATE/'bybit-funding-history-pilot-20261003-v1'
OUTPUT = ROOT/'reports/fast_research/BYBIT_FUNDING_HISTORY_PILOT_ACTUAL_20261003_V1.json'
TRANSPORT = ROOT/'scripts/investment/bybit_funding_windows_transport_v1.ps1'
BASE = ROOT/'scripts/investment/funding_semantics_probe.py'
BASE_SHA = 'c433703b696e67b7a279756cee0891cf686111fed24f808e6f0c1992ce5bdf74'
START, END = 1754006400000, 1754092800000
ENDPOINT = 'https://api.bybit.com/v5/market/funding/history'
module_spec = importlib.util.spec_from_file_location('_coin_funding_metadata_primitives', BASE)
base = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(base)
need, sha, write, load = base.need, base.sha, base.write, base.load
need(sha(BASE) == BASE_SHA, 'Preserved metadata primitives source changed')


def progress(phase, completed):
    path = STATE/'task-progress'/('task-'+os.environ['COIN_TASK_ID']+'.json')
    value = load(path)
    value.update(phase=phase, completed=completed, total=2, unit='固定历史请求', last_activity_at=time.time())
    temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(value, ensure_ascii=False)); os.replace(temp,path)


def request_once(symbol, destination, spec):
    url = ENDPOINT+'?'+urlencode(dict(category='linear',symbol=symbol,startTime=START,endTime=END-1,limit=200))
    need(sha(TRANSPORT) == spec['windows_transport_sha256'], 'Transport changed after freeze')
    native_script = subprocess.check_output(['wslpath','-w',str(TRANSPORT)],text=True).strip()
    native_output = subprocess.check_output(['wslpath','-w',str(destination)],text=True).strip()
    quoted = lambda v: "'"+v.replace("'","''")+"'"
    expression = "& ([ScriptBlock]::Create([IO.File]::ReadAllText("+quoted(native_script)+"))) -Url "+quoted(url)+" -OutputPath "+quoted(native_output)
    command = ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-Command',expression]
    info = dict(url=url,retries=0,requested_at_utc=datetime.now(UTC).isoformat(),exact_transport_command=shlex.join(command))
    try:
        result = subprocess.run(command,capture_output=True,timeout=25,check=False,text=True,encoding='utf-8',errors='replace')
        info.update(json.loads(result.stdout.strip().lstrip('\ufeff')),native_exit_code=result.returncode)
        if destination.exists():
            info.update(raw_path=str(destination),raw_sha256=sha(destination),bytes=destination.stat().st_size)
        payload = destination.read_bytes() if info['status']=='RETRIEVED' and result.returncode==0 else None
    except Exception as error:
        info.update(status='NATIVE_TRANSPORT_FAILURE',error_type=type(error).__name__,reason=str(error)); payload=None
    write(destination.with_suffix('.http.json'),info)
    return payload,info


def validate_response(payload, symbol):
    response = decoded(payload)
    need(isinstance(response,dict) and type(response.get('retCode')) is int, 'Integer retCode required')
    need(response['retCode']==0, 'Nonzero Bybit retCode; stop without another request or bypass: '+str(response['retCode']))
    result = response.get('result')
    need(isinstance(result,dict) and result.get('category')=='linear', 'Native linear result required')
    records = result.get('list')
    need(isinstance(records,list) and 0<len(records)<200, 'Nonempty pilot response below page cap; no full-page coverage assumption')
    seen=set(); stamps=[]
    for row in records:
        need(isinstance(row,dict) and row.get('symbol')==symbol, 'Wrong native funding symbol')
        timestamp,rate=row.get('fundingRateTimestamp'),row.get('fundingRate')
        need(isinstance(timestamp,str) and timestamp.isascii() and timestamp.isdigit() and str(int(timestamp))==timestamp,
             'Canonical millisecond fundingRateTimestamp string required')
        stamp=int(timestamp)
        need(START<=stamp<END and stamp not in seen, 'Out-of-window or duplicate event')
        need(isinstance(rate,str), 'Published fundingRate string required')
        number=Decimal(rate)
        need(number.is_finite() and abs(number)<=1, 'Finite bounded raw rate required; no rescaling')
        seen.add(stamp); stamps.append(stamp)
    return dict(retCode=0,category='linear',symbol=symbol,row_count=len(records),
        fundingRateTimestamp_ms=stamps,minimum_event_ms=min(stamps),maximum_event_ms=max(stamps),
        observed_order='ASCENDING' if stamps==sorted(stamps) else 'DESCENDING' if stamps==sorted(stamps,reverse=True) else 'UNORDERED',
        rate_encoding='PUBLISHED_DECIMAL_STRING_NOT_RESCALED',
        interval_inferred=False,full_day_event_completeness_certified=False,
        coverage='NOT_CERTIFIED_HISTORICAL_COMPLETENESS',page_cap_touched=False,
        publication_or_account_cash_timestamp_certified=False,charge_mark_available=False)


def decoded(payload):
    def unique_fields(pairs):
        result={}
        for key,value in pairs:
            need(key not in result, 'Duplicate JSON key rejected: '+key)
            result[key]=value
        return result
    def invalid_constant(value):
        raise ValueError('Nonfinite JSON constant rejected: '+value)
    return json.loads(payload,object_pairs_hook=unique_fields,parse_constant=invalid_constant)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--run-dir',type=Path,required=True)
    args=parser.parse_args()
    args.protocol=args.protocol.resolve()
    need(args.run_dir.resolve()==WORK and not WORK.exists() and not OUTPUT.exists(), 'Exclusive predetermined STATE/report required')
    need(args.protocol.resolve().parent==ROOT/'protocols', 'Project protocol required')
    need(sys.prefix==str(STATE/'v8-clean-env-20261002-v2'), 'Frozen clean interpreter required')
    spec=load(args.protocol)
    need(spec['source_sha256']==sha(__file__) and spec['windows_transport_sha256']==sha(TRANSPORT), 'Pilot code changed after freeze')
    need(sha(ROOT/'environments/v8/uv.lock')==spec['environment_lock_sha256'], 'Frozen environment changed')
    need(spec['endpoint']==ENDPOINT and spec['category']=='linear' and spec['symbols']==['BTCUSDT','ETHUSDT'] and
         spec['startTime_ms']==START and spec['endTime_exclusive_ms']==END and spec['limit']==200 and
         spec['timeout_seconds']==20 and spec['max_response_bytes']==64000, 'Only fixed one-day native history scope')
    need(spec['run_dir']==str(WORK) and spec['output']==str(OUTPUT.relative_to(ROOT)), 'Frozen output identities required')
    frozen={path:sha(ROOT/path) for path in spec['frozen_sources']}
    need(frozen==spec['frozen_sources'], 'Frozen prior/source proof changed')
    need(sha(ROOT/spec['fee_reference_path'])==spec['fee_reference_sha256'], 'Fee profile identity changed')
    WORK.mkdir()
    binding=dict(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        task_id=os.environ['COIN_TASK_ID'],protocol_path=str(args.protocol.relative_to(ROOT)),protocol_sha256=sha(args.protocol),
        source_sha256=sha(__file__),source_hashes=frozen,environment_lock_sha256=spec['environment_lock_sha256'],sys_prefix=sys.prefix,
        exact_command=shlex.join([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]),
        market='BYBIT_USDT_LINEAR_NATIVE_PUBLIC_FUNDING_HISTORY',data_scope='2025-08-01_UTC_ONLY',seed='NOT_APPLICABLE',models_fit=0,GPU=0,
        fee_reference_path=spec['fee_reference_path'],fee_reference_sha256=spec['fee_reference_sha256'])
    write(WORK/'RUN_BINDING.json',binding)
    sys.path.insert(0,str(ROOT))
    from scripts.research_v8.registry import FIELDS,append_event
    event=dict.fromkeys(FIELDS)
    event.update(experiment_id=spec['experiment_id'],git_commit=binding['git_commit'],data_manifest_hash=None,
        data_manifest_status='NONE_NO_PRIOR_NATIVE_BYBIT_DATA_RAW_SHA_RECORDED_AFTER_RETRIEVAL',
        protocol_hash=binding['protocol_sha256'],feature_set='NONE',labels='NONE',model_family='NONE',hyperparameters='FIXED_TWO_PUBLIC_ONE_DAY_REQUESTS_LIMIT200',
        seed='NOT_APPLICABLE',thresholds={'response_bytes':64000,'page_cap_rejected':200},cost_assumptions='NO_ECONOMIC_CALCULATION_FEE_PROFILE_REFERENCE_ONLY',
        all_folds='BTC_ETH_2025_08_01_ONLY',result_influenced_later_choice=False,reason_for_next_experiment='Native venue history coverage before any full source or funding income study')
    write(WORK/'START.json',append_event(ROOT/'reports/experiment_registry.jsonl',{**event,'event_id':spec['experiment_id']+':START',
        'event_type':'OPERATIONAL_SOURCE_PILOT_START','success_failure':'START_BEFORE_NATIVE_REQUESTS','binding':binding}))
    report=dict(status='FAIL_BYBIT_NATIVE_FUNDING_HISTORY_PILOT_UNCONFIRMED',binding=binding,run_dir=str(WORK),requests=[],samples=[],
        funding_rate_unit='NOT_YET_INTERPRETED',publication_or_cash_certified=False,full_history_coverage_certified=False,
        locked_consumed=False,orders_sent=0,price_arrays_read=False,funding_income_calculated=False,models_fit=0,GPU=0,
        candidate_status='NO_QUALIFIED_CANDIDATE',carry_economics='NOT_EVALUABLE')
    started=time.monotonic();exit_code=1
    try:
        write(WORK/'DOCUMENTARY_PRIMARY_EVIDENCE.json',spec['official_documentary_sources'])
        progress('固定Bybit历史小窗口',0)
        for completed,symbol in enumerate(spec['symbols'],1):
            payload,receipt=request_once(symbol,WORK/(symbol+'-official-response.json'),spec);report['requests'].append(receipt)
            progress('固定历史请求已处理',completed)
            need(receipt.get('http_status') not in (403,451,418,429), 'Official access/rate restriction; stop without bypass')
            need(payload is not None, 'Official transport failed; no retry or another request')
            response=decoded(payload);report['requests'][-1]['retCode']=response.get('retCode') if isinstance(response,dict) else None
            report['samples'].append(validate_response(payload,symbol))
        need(len(report['samples'])==2 and sha(__file__)==binding['source_sha256'] and sha(args.protocol)==binding['protocol_sha256'] and
             all(sha(ROOT/path)==digest for path,digest in frozen.items()), 'Both native samples and unchanged frozen sources required')
        need(time.monotonic()-started<=180 and sum(p.stat().st_size for p in WORK.rglob('*') if p.is_file())<=2000000,
             'Fixed 180s/2MB pilot budget exceeded')
        report.update(status='PASS_BYBIT_NATIVE_FUNDING_HISTORY_SMALL_WINDOW_FORMAT_AND_DOCUMENTARY_INTERPRETATION',
            funding_rate_unit='FRACTION_DOCUMENTARY_API_CONVENTION',bp_multiplier=10000,
            unit_qualification='OFFICIAL_DOCUMENTARY_INTERPRETATION_NOT_EMPIRICAL_ACCOUNT_SETTLEMENT_CERTIFICATION')
        exit_code=0
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error))
    finally:
        from quant import resources
        report.update(created_utc=datetime.now(UTC).isoformat(),actual_operation_exit_code=exit_code,elapsed_seconds=time.monotonic()-started,
            WSL_python_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources=resources.status(),
            WindowsPeakWorkingSet64_max=max((r.get('WindowsPeakWorkingSet64',0) for r in report['requests']),default=0),
            shared_simultaneous_peak_measured=False,Windows_transport_outside_WSL_cgroup=True,
            response_body_bytes_total=sum(r.get('response_body_bytes',0) for r in report['requests']),
            network_bytes_scope='BODY_ONLY_HEADERS_TLS_WIRE_UNKNOWN',owned_bytes=sum(p.stat().st_size for p in WORK.rglob('*') if p.is_file()))
        write(OUTPUT,report)
        write(WORK/'RESULT.json',append_event(ROOT/'reports/experiment_registry.jsonl',{**event,'event_id':spec['experiment_id']+':RESULT',
            'event_type':'OPERATIONAL_SOURCE_PILOT_RESULT','success_failure':report['status'],'artifact_path':str(OUTPUT.relative_to(ROOT)),
            'artifact_sha256':sha(OUTPUT),'actual_operation_exit_code':exit_code,'actual_task_id':binding['task_id']}))
        print(json.dumps(dict(status=report['status'],output=str(OUTPUT),sha256=sha(OUTPUT),actual_exit=exit_code)))
    return exit_code


if __name__=='__main__':
    raise SystemExit(main())
