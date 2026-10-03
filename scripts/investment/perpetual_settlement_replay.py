"""Replay only the two recorded false-halt cases after an exact settlement fix.

The frozen market controller, targets, costs, input dates and capacity are reused.
This is a correctness replay, not another strategy or funding-unit selection.
"""
import argparse, gc, json, os, resource, shlex, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
from quant import disk, resources
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_directional as reuse

CONTRACT='USDM_EXACT_SETTLEMENT_TWO_FALSE_HALTS_20261003_V1'
STATUS='COMPLETE_TWO_EXACT_SETTLEMENT_CORRECTNESS_REPLAYS_NOT_NATIVE_OR_LONG_TERM_APR'
SELECTORS=['90D_SHORT_ONLY_BASE27_RAW_AS_PERCENT','90D_LONG_SHORT_BASE27_RAW_AS_PERCENT']

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','run-dir','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--experiment-id',required=True);a=p.parse_args()
    spec=reuse.small(a.protocol);run=a.run_dir.resolve();out=a.output.resolve()
    reuse.need(os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2')
        and reuse.pl.thread_pool_size()<=2,'Actual bounded CPU2 research task')
    reuse.need(spec['contract_id']==CONTRACT and spec['selectors']==SELECTORS and spec['rules']==reuse.RULES
        and spec['cost']==reuse.COSTS[0] and spec['unit']==reuse.UNITS[1], 'Only predeclared false-halt cases, financial design unchanged')
    reuse.need(run.parent==STATE and not run.exists() and out.parent==ROOT/'reports/fast_research' and not out.exists()
        and str(run)==spec['run_dir'] and str(out.relative_to(ROOT))==spec['output_path'],'Exclusive frozen output paths')
    hashes=spec['frozen_sources'];own=Path(__file__).relative_to(ROOT).as_posix()
    reuse.need(hashes.get(own)==reuse.sha(__file__),'Own exact source before financial reads')
    for name,value in hashes.items():reuse.need(reuse.sha(ROOT/name)==value,'Frozen source '+name)
    original=reuse.relative_proof(spec['original_actual']);audit=reuse.relative_proof(spec['original_independent'])
    for report in (original,audit):
        t=reuse.small(STATE/'task-progress'/f"task-{report['binding']['task_id']}.json")
        reuse.need(t['status']=='completed' and t['exit_code']==0,'Original actual closed0')
    reuse.need(original['completed_cases']==32 and original['incomplete_or_halted_cases']==2
        and audit['completed_cases_verified']==32 and audit['incomplete_or_halted_cases_verified']==2,
        'Original 30 complete and two actual false-halt prefixes retained')
    old=[c for c in original['cases'] if c['id'] in SELECTORS]
    reuse.need([c['id'] for c in old]==SELECTORS and all(c['summary']['halt_witness']['decimal_strings']['unpaid_liability']=='1.000E-37'
        and c['summary']['NAV']>10000 and c['summary']['free_cash']>9000 for c in old),'Exact recorded numerical failure, no economic halt relabeling')
    test=reuse.relative_proof(spec['required_settlement_test'])
    t=reuse.small(STATE/'task-progress'/f"task-{test['binding']['task_id']}.json")
    reuse.need(test['test_exit_code']==0 and test['source_bytes_unchanged'] is True and t['status']=='completed'
        and t['exit_code']==0,'Actual exact-settlement new case passed before market arrays')
    manifest=reuse.relative_proof(spec['input_manifest']);window_spec=next(w for w in manifest['windows'] if w['id']=='90D')
    run.mkdir();started=time.monotonic();budget=spec['budgets'];before=resources.status()
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_path=str(Path(__file__).resolve()),source_sha256=reuse.sha(__file__),
        source_hashes=hashes,protocol_path=str(a.protocol.resolve()),protocol_sha256=reuse.sha(a.protocol),
        exact_command=shlex.join([sys.executable,*sys.argv]),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sys_prefix=sys.prefix,selected_periods=['90D'],selected_case_ids=SELECTORS,rules=reuse.RULES)
    reuse.write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(reuse.FIELDS);event.update(experiment_id=a.experiment_id,event_id=a.experiment_id+':START',event_type='CORRECTNESS_RESEARCH_START',
        git_commit=binding['git_commit'],data_manifest_hash=spec['input_manifest']['sha256'],protocol_hash=binding['protocol_sha256'],
        feature_set='UNCHANGED_PUBLIC_SMA50_200',labels='NONE',model_family='NONE',hyperparameters={},seed=None,
        thresholds='NO_EPSILON_EXACT_FULL_CLOSE_COLLATERAL_RELEASE',cost_assumptions={'cost':spec['cost'],'unit':spec['unit']},
        all_folds=['SEEN_90D_TWO_PREDECLARED_FALSE_HALTS'],success_failure='START_BEFORE_MARKET_ARRAYS',
        reason_for_next_experiment='Repair Decimal rounding false-bankruptcy; no alpha tuning',result_influenced_later_choice=True,
        source_hashes=hashes,exact_command=binding['exact_command'])
    report=dict(status='FAIL_TWO_EXACT_SETTLEMENT_CORRECTNESS_REPLAYS',binding=binding,run_dir=str(run),run_binding_sha256=reuse.sha(run/'RUN_BINDING.json'),
        registration_start=reuse.append_event(ROOT/'reports/experiment_registry.jsonl',event),required_cases=2,completed_cases=0,cases=[],input_windows=[],
        original_report_sha256=spec['original_actual']['sha256'],original_independent_sha256=spec['original_independent']['sha256'],
        completed_trading_account_simulations=0,completed_constant_cash_baselines=0,original_other_thirty_financial_cases_replayed=False,
        funding_rate_unit='UNCONFIRMED',unit_certified=False,native_market_certified=False,candidate='NO_QUALIFIED_CANDIDATE',
        long_term_APR='NOT_EVALUABLE',models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,resources_before=before)
    progress=reuse.support.progress_writer(2)
    def guard():
        reuse.need(reuse.support.owned_bytes(run)<=budget['new_owned_bytes'] and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=budget['peak_RSS_bytes']
            and time.monotonic()-started<=budget['wall_seconds'],'Fixed exclusive replay resource budget')
    try:
        progress.update('实际容量扫描，总量未知',None,None,'扫描')
        report['disk']=dict(scan_started_utc=datetime.now(UTC).isoformat(),**disk.check(budget['new_owned_bytes']))
        report['disk']['scan_finished_utc']=datetime.now(UTC).isoformat()
        reuse.need(report['disk']['total_bytes']+budget['new_owned_bytes']+1_000_000_000<=32_000_000_000,'Capacity including temporary reserve')
        w=reuse.load_window(manifest,window_spec)
        report['input_windows'].append(dict(id='90D',input_proofs=w['input_proofs'],original_funding_events=len(w['events']),
            score_start_us=w['start'],score_end_exclusive_us=w['end']))
        for selector,mode in zip(SELECTORS,['SHORT_ONLY','LONG_SHORT'],strict=True):
            case=reuse.simulate(w,mode,spec['cost'],spec['unit'],progress,guard)
            saved=reuse.save_case(case,run/selector);del case;gc.collect()
            report['cases'].append(dict(id=selector,period='90D',mode=mode,cost_id='BASE27',unit_id='RAW_AS_PERCENT',**saved))
            report['completed_cases']=report['completed_trading_account_simulations']=len(report['cases']);guard()
            s=saved['summary']
            reuse.need(s['completion']=='COMPLETE_CONDITIONAL_ACCOUNT' and s['completed_minutes']==s['required_minutes']==129600
                and s['unpaid_liability']==0 and s['terminal_marked_notional']==0 and not s.get('halt_witness'),
                'Repaired account genuinely completes calendar and costed capacity-limited close')
            progress.update('两项正确性复测',report['completed_cases'],2,'账户')
        reuse.need(report['completed_cases']==2 and all(reuse.sha(ROOT/n)==h for n,h in hashes.items()),'Actual two cases and source stability')
        report.update(status=STATUS,completed_full_calendar_cases=2,incomplete_or_halted_cases=0)
    except Exception as error:report.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=reuse.support.owned_bytes(run),resources_after=resources.status())
        reuse.write(out,report);reuse.append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=a.experiment_id+':RESULT',event_type='CORRECTNESS_RESEARCH_RESULT',
            success_failure=report['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=reuse.sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=report['status'],completed_cases=report['completed_cases'],sha256=reuse.sha(out))))

if __name__=='__main__':main()
