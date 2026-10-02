"""Prepared independent 90d audit of both fixed controls; no execution yet.
Imports accepted independent Decimal checks, never the production simulator.
Actual reports/tasks and all new source bindings must be frozen before execution.
"""
import hashlib, importlib.util, json, os, resource, sys, time
from array import array
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
WORK=STATE/'test-carry-90d-two-controls-independent-audit-20261003-v3'
OUT=ROOT/'reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V3.json'
SYMBOLS=('BTCUSDT','ETHUSDT');MONTHS=('2025-12','2026-01','2026-02')
START=1764547200000000;END=1772323200000000;COUNT=129600

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def need(ok,message):
    if not ok:raise AssertionError(message)
def write_new(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
def one(rows,key):
    selected=[r for r in rows if (r['kind'],r['symbol'],r['month'])==key]
    need(len(selected)==1,'One exact accepted source metadata row');return selected[0]

def metadata_source_view(spec):
    path=ROOT/spec['source_view_path'];need(sha(path)==spec['source_view_sha256'],'Frozen new source view')
    view=load(path)
    need(view['period_start']=='2025-12-01' and view['period_end_exclusive']=='2026-03-01'
         and view['source_calendar']==list(MONTHS) and view['symbols']==list(SYMBOLS)
         and view['funding_unit_certified'] is False and view['economic_gate_passed'] is False,'New source scope only')
    owner=Path(view['accepted_new_source_state_root'])
    need(owner==STATE/'carry-chronology-source-actual-20261003-v1','Exact new accepted futures root')
    universe={(k,s,m) for k in ('spot1m','markPriceKlines','indexPriceKlines','fundingRate') for s in SYMBOLS for m in MONTHS}
    rows=view['sources'];need(len(rows)==24 and {(r['kind'],r['symbol'],r['month']) for r in rows}==universe,'Exact24 inputs')
    proofs={}
    for proof in view['acceptance_proofs']:
        path=ROOT/proof['path'];need(sha(path)==proof['sha256']==spec['frozen_sources'][proof['path']],'Accepted small proof bytes')
        result=load(path);need(result['status']==proof['required_status'],'Actual accepted source proof status')
        need(proof['role'] not in proofs,'Unique accepted provenance role');proofs[proof['role']]=result
    need(set(proofs)=={'REUSED_SPOT','NEW_SOURCE_PRODUCER','NEW_SOURCE_QA','NEW_SOURCE_ROOT_ACCEPTANCE'},'Four exact provenance roles')
    root=proofs['NEW_SOURCE_ROOT_ACCEPTANCE'];qa=proofs['NEW_SOURCE_QA'];producer=proofs['NEW_SOURCE_PRODUCER']
    need(root['accepted_format']['funding_events']==qa['actual_funding_events']==spec['expected_funding_events']==540
         and view['funding_event_total']==540 and view['funding_counts_by_symbol']==spec['expected_funding_events_by_symbol']==dict.fromkeys(SYMBOLS,270),
         'Observed540/270 counts, not an assumed cadence')
    for row in rows:
        k,s,m=(row[n] for n in ('kind','symbol','month'))
        if k=='spot1m':
            accepted=[r for r in proofs['REUSED_SPOT']['sources'] if (r['symbol'],r['month'])==(s,m)]
            need(len(accepted)==1 and row['provenance_role']=='REUSED_SPOT','One reused Spot provenance')
            accepted=accepted[0]
            need((row['rows'],row['parquet_path'],row['parquet_sha256'])==
                 (accepted['rows'],accepted['normalized_path'],accepted['normalized_sha256']),'Direct accepted Spot record equality')
        else:
            rr=one(root['source_receipt_proofs'],(k,s,m));qr=one(qa['sources'],(k,s,m));pr=one(producer['sources'],(k,s,m))
            need(row['provenance_role']=='NEW_SOURCE_ROOT_ACCEPTANCE' and
                 (row['rows'],row['parquet_path'],row['parquet_sha256'],row['receipt_path'],row['receipt_sha256'])==
                 (rr['rows'],rr['parquet']['path'],rr['parquet']['sha256'],rr['receipt_path'],rr['receipt_sha256']),
                 'Direct accepted new source record equality')
            need(qr['status']=='PASS_SOURCE_FORMAT_ONLY' and qr['all_published_values_equal_raw'] is True
                 and (qr['rows'],qr['receipt_path'],qr['receipt_sha256'])==(row['rows'],row['receipt_path'],row['receipt_sha256'])
                 and (pr['path'],pr['sha256'])==(row['receipt_path'],row['receipt_sha256']), 'Producer/independent QA receipt linkage')
    return view,owner

def original_inputs(view,reader,core):
    """Only new necessary Parquet columns; no ZIP/CSV/CRC/source QA repeat."""
    import pyarrow.parquet as pq
    rows=view['sources'];lookup={(r['kind'],r['symbol'],r['month']):r for r in rows}
    expected=[{k:r[k] for k in ('kind','symbol','month','parquet_path','parquet_sha256','rows')} for r in rows]
    prices={s:{key:array('d') for key in ('spot','mark')} for s in SYMBOLS}
    for s in SYMBOLS:
        for m in MONTHS:
            streams=[reader.source_rows(lookup[k,s,m]) for k in ('spot1m','markPriceKlines','indexPriceKlines')]
            for spot,mark,index in zip(*streams,strict=True):
                need(spot[:2]==mark[:2]==index[:2],'Original same-minute clocks, no fill/drop/rebase')
                prices[s]['spot'].append(spot[2]);prices[s]['mark'].append(mark[2])
        need(len(prices[s]['spot'])==len(prices[s]['mark'])==COUNT,'All129600 source minutes')
    events=[];owner=Path(view['accepted_new_source_state_root'])
    for row in rows:
        if row['kind']!='fundingRate':continue
        path=Path(row['parquet_path']);expected_path=owner/('fundingRate-'+row['symbol']+'-'+row['month'])/'source.parquet'
        need(path==expected_path and path.resolve()==expected_path and not path.is_symlink() and sha(path)==row['parquet_sha256'],'Exact new funding source')
        parquet=pq.ParquetFile(path);need(parquet.metadata.num_rows==row['rows'],'All original funding rows')
        data=parquet.read(columns=['calc_time_ms','last_funding_rate'],use_threads=False).to_pylist()
        lo,hi=reader.bounds(row['month'])
        for item in data:
            stamp=item['calc_time_ms'];rate=item['last_funding_rate']
            need(type(stamp) is int and lo<=stamp*1000<hi and START<=stamp*1000<END,'Original millisecond bounds')
            core.number(rate);events.append(dict(symbol=row['symbol'],event_us=stamp*1000,rate=rate))
        need(sha(path)==row['parquet_sha256'],'Funding unchanged during read')
    events.sort(key=lambda r:(r['event_us'],r['symbol']))
    need(len(events)==len({(r['symbol'],r['event_us']) for r in events})==540
         and all(sum(r['symbol']==s for r in events)==270 for s in SYMBOLS),'Every original540 event retained once')
    return prices,events,expected
def main():
    started=time.monotonic();bound=load(WORK/'ACTUAL_BINDING.json')
    need(sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and os.environ.get('COIN_TASK_ID')
         and sha(__file__)==bound['checker_sha256'] and not OUT.exists(),'Actual closed0, clean bounded environment and new frozen audit')
    report=dict(status='FAIL_CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT',
        binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),ACTUAL_BINDING_sha256=sha(WORK/'ACTUAL_BINDING.json')),
        independent_source=str(Path(__file__)),independent_source_sha256=sha(__file__),cases=[],completed_cases_verified=0,
        cash_absolute_tolerance_USDT='1e-7',ratio_absolute_tolerance='1e-10',financial_scope='CONDITIONAL_RAW_FRACTION_CLOSE_PROXY_ONLY',
        old_122d_financial_replayed=False,raw_ZIP_or_CRC_read=False,old_QA_or_green_tests_repeated=False,
        simulate_account_called=False,actual_HTTP_requests=0,models_fit=0,orders_sent=0,
        funding_unit_certified=False,native_Bybit_settlement_proven=False,candidate_status='NO_QUALIFIED_CANDIDATE')
    try:
        import pyarrow.parquet as pq
        for path,digest in bound['small_inputs'].items():need(sha(path)==digest,'Prebound small source changed:'+path)
        spec=load(ROOT/bound['protocol_path'])
        need(spec['contract_id']=='CONDITIONAL_CARRY_90D_FIXED_PERIOD_V1' and spec['period_start']=='2025-12-01'
             and spec['period_end_exclusive']=='2026-03-01' and spec['source_calendar']==list(MONTHS)
             and spec['symbols']==list(SYMBOLS) and spec['expected_minutes_per_asset']==COUNT
             and spec['expected_price_files']==18 and spec['expected_funding_files']==6,'Fixed full90d contract')
        need(str(spec['independent_cash_absolute_tolerance_USDT'])=='1e-07'
             and str(spec['independent_ratio_absolute_tolerance'])=='1e-10','Preregistered unchanged tolerances')
        need(sha(WORK/'reused_blocks.py')==bound['reused_blocks_sha256'],'Frozen thin independent adapter before import')
        rb_spec=importlib.util.spec_from_file_location('reused_90d_independent_blocks',WORK/'reused_blocks.py')
        rb=importlib.util.module_from_spec(rb_spec);rb_spec.loader.exec_module(rb)
        need(sha(WORK/'reused_blocks.py')==bound['reused_blocks_sha256'],'Frozen thin independent adapter')
        core=rb.imported('accepted_carry_core90',bound['core_path'],bound['core_sha256'])
        trim=rb.imported('accepted_pair_audit90',bound['pair_audit_path'],bound['pair_audit_sha256'])
        delta=rb.imported('accepted_pair_delta90',bound['pair_delta_path'],bound['pair_delta_sha256'])
        reader=rb.imported('accepted_clock_reader90',bound['price_reader_path'],bound['price_reader_sha256'])
        need(core.USDT_TOL==core.D('1e-7') and core.RATIO_TOL==core.D('1e-10'),'Accepted financial tolerances unchanged')
        expected_hashes=dict(spec['frozen_sources']);expected_hashes[bound['protocol_path']]=sha(ROOT/bound['protocol_path'])
        need(spec['policies']['ALL_FLAT']==load(ROOT/'protocols/CONDITIONAL_CARRY_ACCOUNT_122D_20261003_V1.json')['rules']
             and spec['policies']['PAIR_TRIM']==load(ROOT/'protocols/CONDITIONAL_CARRY_PAIR_TRIM_122D_20261003_V1.json')['rules'],
             'Original accepted capital/cost/risk policies remain exact')
        view,owner=metadata_source_view(spec);reader,read_proof=rb.reader_for_new_owner(reader,owner)
        report['independent_reader_derivation']=read_proof
        need([c['policy'] for c in bound['actuals']]==['ALL_FLAT','PAIR_TRIM'],'Two explicit independent selectors')
        actuals=[]
        smoke=load(ROOT/spec['required_smoke_receipt']);report['smoke_actual_task']=reader.task(smoke['binding']['task_id'])
        need(smoke['status']=='PASS_CARRY_90D_PERIOD_SOURCE_ENDPOINT_SYNTHETIC_ONLY' and smoke['test_exit_code']==0
             and smoke['junit_counts']==dict(tests=1,errors=0,failures=0,skipped=0)
             and smoke['source_bytes_unchanged'] is True and smoke['price_arrays_read'] is False and smoke['funding_arrays_read'] is False,
             'New closed synthetic case only; no repeat suite')
        fundspec=load(ROOT/spec['funding_contract_path']);probe=load(ROOT/fundspec['unit_probe']['path'])
        failed_path=STATE/'task-progress'/('task-'+probe['binding']['task_id']+'.json');failed=load(failed_path)
        need(failed['id']==probe['binding']['task_id'] and failed['status']=='failed' and failed['exit_code']==1
             and probe['unit_evidence']['matched_records']==0,'Real HTTP451 failed1/zero-match evidence remains')
        report['unit_failure_task']={k:failed[k] for k in ('id','status','exit_code','pid','start_ticks')}
        report['unit_failure_task'].update(path=str(failed_path),sha256=sha(failed_path))
        for selector in bound['actuals']:
            policy=selector['policy'];path=ROOT/selector['actual_report_path'];need(sha(path)==selector['actual_report_sha256'],'Exact new actual report')
            actual=load(path);task=reader.task(selector['actual_task_id'])
            need(actual['binding']['task_id']==task['id'] and actual['policy']==policy
                 and actual['status']=='COMPLETE_CARRY_90D_DEVELOPMENT_EXTRAPOLATION_CONDITIONAL_NOT_LONG_TERM_APR'
                 and actual['source_bytes_unchanged'] is True and actual['source_view_sha256']==spec['source_view_sha256'],
                 'Each policy actual completed0/source view')
            need(actual['binding']==load(Path(actual['run_dir'])/'RUN_BINDING.json')
                 and actual['binding']['protocol_sha256']==sha(ROOT/bound['protocol_path'])
                 and actual['binding']['rules']==spec['policies'][policy]
                 and actual['binding']['source_hashes']==expected_hashes==smoke['binding']['source_hashes']
                 and actual['accepted_smoke_sha256']==sha(ROOT/spec['required_smoke_receipt']),'Exact actual common sources/rules/smoke')
            unit=actual['unit_interpretation']
            need(unit['raw_rate_unit']=='UNCONFIRMED' and unit['assumed_funding_rate_unit']=='FRACTION'
                 and unit['conditional_fraction_assumption'] is True and unit['bp_multiplier']==10000
                 and unit['full_732_event_unit_certified'] is False and unit['sampled_API_unit_certified'] is False
                 and unit['current_period_archive_unit_certified'] is False,'No unit certification or native claim')
            derivation=actual['period_derivation']
            need(derivation['policy']==policy and derivation['period_calendar']==list(MONTHS)
                 and derivation['base_sha256']==spec['base_account_sha256']
                 and derivation['pair_trim_sha256']==spec['frozen_sources']['scripts/investment/conditional_carry_reduce_adapter.py']
                 and derivation['old_simulate_code_unchanged'] is True and derivation['legacy_globals_mutated'] is False
                 and set(derivation['function_changes'])==set(derivation['function_AST_sha256'])=={'load_inputs','main'},
                 'Only isolated source/period adapter over exact accepted account kernels')
            actuals.append((selector,actual,task))
        for path,digest in spec['frozen_sources'].items():need(sha(ROOT/path)==digest,'Frozen actual code/proof changed:'+path)
        report['verified_source_hashes']=expected_hashes
        write_new(WORK/'RUN_BINDING.json',dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),
            ACTUAL_BINDING_sha256=sha(WORK/'ACTUAL_BINDING.json'),reused_blocks_sha256=sha(WORK/'reused_blocks.py'),
            exact_command=' '.join(sys.argv),sys_prefix=sys.prefix,actuals=bound['actuals'],
            reused_inputs={k:bound[k] for k in ('core_path','core_sha256','pair_audit_path','pair_audit_sha256',
                'pair_delta_path','pair_delta_sha256','price_reader_path','price_reader_sha256')},
            source_hashes=bound['small_inputs'],cash_tolerance_USDT='1e-7',ratio_tolerance='1e-10'))
        compiled_financial={policy:rb.financial(core,trim,delta,policy) for policy in ('ALL_FLAT','PAIR_TRIM')}
        prices,events,inputs=original_inputs(view,reader,core)
        for selector,actual,task in actuals:
            policy=selector['policy'];core.MAX_USDT_ERROR=core.MAX_RATIO_ERROR=core.ZERO
            need(sorted(actual['input_bindings'],key=lambda r:(r['kind'],r['symbol'],r['month']))==
                 sorted(inputs,key=lambda r:(r['kind'],r['symbol'],r['month'])),'Exact same24 physical source identities for each policy')
            need(len(actual['output_bindings'])==4 and {r['kind'] for r in actual['output_bindings']}==
                 {'minute_nav','fill_ledger','funding_ledger','daily_nav'},'Four actual policy artifacts')
            frames={}
            for row in actual['output_bindings']:
                path=Path(row['path']);need(path.parent==Path(actual['run_dir']) and path.resolve()==path and not path.is_symlink()
                     and sha(path)==row['sha256'],'Exact physical policy output')
                file=pq.ParquetFile(path);need(file.metadata.num_rows==row['rows'],'Actual artifact count');frames[row['kind']]=file
            fills=frames['fill_ledger'].read(use_threads=False).to_pylist()
            fundrows=frames['funding_ledger'].read(use_threads=False).to_pylist();daily=frames['daily_nav'].read(use_threads=False).to_pylist()
            need(len(fundrows)==540 and len(daily)==90 and [(r['symbol'],r['event_us'],r['raw_rate']) for r in fundrows]==
                 [(e['symbol'],e['event_us'],e['rate']) for e in events],'Every included/excluded original event and90 days')
            checked=dict(completed_minutes_verified=0)
            verify,proof=compiled_financial[policy]
            write_progress=dict(phase='独立金融核验 '+policy,completed=report['completed_cases_verified'],total=2,unit='控制账户',
                pid=os.getpid(),task_id=os.environ['COIN_TASK_ID'])
            (WORK/'progress.json').write_text(json.dumps(write_progress,ensure_ascii=False))
            result=verify(actual,actual['summary'],prices,events,frames,fills,fundrows,daily,checked)
            summary=actual['summary'];wallet=result['wallet'];obs=result['obs']
            financial=result['expected'] if policy=='ALL_FLAT' else result['financial']
            reductions=result.get('reductions',[])
            def plain(value):
                if isinstance(value,core.D):return float(value)
                if isinstance(value,dict):return {k:plain(v) for k,v in value.items()}
                if isinstance(value,list):return [plain(v) for v in value]
                return value
            report['cases'].append(dict(policy=policy,actual_report_path=selector['actual_report_path'],
                actual_report_sha256=sha(ROOT/selector['actual_report_path']),actual_task=task,
                completed_source_files_verified=len(inputs),completed_minutes_verified=checked['completed_minutes_verified'],
                completed_original_funding_events_verified=result['event_cursor'],completed_fills_verified=result['fill_cursor'],
                completed_days_verified=len(daily),completed_months_verified=len(result['months']),
                completed_pair_reductions_verified=len(reductions),owned_events=result['owned'],excluded_events=540-result['owned'],
                financial_summary=plain(financial),months=result['months'],independent_pair_reductions=plain(reductions),
                first_risk_signal=(obs.first_breach if policy=='ALL_FLAT' else result['stop_signal']),exit_us=result['exit_time'],
                terminal_bridge_error_USDT=str(result['bridge']-wallet.cash),maximum_cash_error_USDT=float(core.MAX_USDT_ERROR),
                maximum_ratio_error=float(core.MAX_RATIO_ERROR),minute_max_drawdown=float(result['minute_dd']),
                all_observation_max_drawdown=float(obs.max_dd),independent_financial_derivation=proof,
                output_bindings=actual['output_bindings']))
            report['completed_cases_verified']+=1
            need(time.monotonic()-started<=600 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=512000000,'Independent own resource budget')
        for path,digest in bound['small_inputs'].items():need(sha(path)==digest,'Small source changed during audit:'+path)
        for row in inputs:need(sha(row['parquet_path'])==row['parquet_sha256'],'Shared source changed during audit')
        for selector,actual,task in actuals:
            for row in actual['output_bindings']:need(sha(row['path'])==row['sha256'],'Policy output changed during audit')
        a,b=report['cases'];report.update(
            status='PASS_CARRY_90D_TWO_POLICY_DECIMAL_CONDITIONAL_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR',
            paired_net_PnL_delta_USDT=b['financial_summary']['net_PnL_USDT']-a['financial_summary']['net_PnL_USDT'],
            monthly_paired_deltas=[dict(month=y['month'],net_PnL_delta_USDT=y['net_PnL_USDT']-x['net_PnL_USDT'],
                signed_funding_delta_USDT=y['signed_funding_USDT']-x['signed_funding_USDT'])
                for x,y in zip(a['months'],b['months'],strict=True)],
            limitations=['Fixed seen90d development sample, not unseen or long-term APR',
                'Raw fractions, event ownership and past mark are uncertified conditional hypotheses',
                'Common initial capital/cost/caps do not certify equal realized risk or native execution/MMR/ADL'])
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        write_new(OUT,report)
    print(json.dumps(dict(status=report['status'],output=str(OUT),sha256=sha(OUT))))
if __name__=='__main__':main()