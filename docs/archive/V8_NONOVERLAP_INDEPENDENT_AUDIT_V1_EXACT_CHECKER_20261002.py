from __future__ import annotations
import hashlib,itertools,json,math,resource,subprocess,sys,time
from datetime import date,datetime,timezone
from pathlib import Path
import numpy as np
import polars as pl
from scipy.stats import pearsonr,spearmanr
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state/test-v8-mechanism-output-audit-20261002-v1')
sys.path.insert(0,str(root/'scripts/research_v8'))
import labels_v5 as labels
US=1_000_000;MIN=60*US;DAY=86400*US

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def stamp(day):return int(datetime.combine(date.fromisoformat(day),datetime.min.time(),timezone.utc).timestamp())*US
paths={k:root/p for k,p in {'protocol_v1':'protocols/NONOVERLAP_MECHANISM_V8_V1.json','protocol_v2':'protocols/NONOVERLAP_MECHANISM_V8_V2.json',
 'P1':'protocols/P1_GATE_V8.json','label_contract':'protocols/LABEL_CONTRACT_V8.json','source_v1':'scripts/research_v8/nonoverlap_mechanism.py',
 'source_v2':'scripts/research_v8/nonoverlap_mechanism_v2.py','actual_output':'reports/fast_research/V8_NONOVERLAP_MECHANISM_20261002_V2.json',
 'label_audit':'reports/fast_research/V8_LABEL_ADVERSARIAL_AUDIT_20261002_V5_R2.json'}.items()}
paths['actual_execution_receipt']=root/'reports/fast_research/V8_NONOVERLAP_ACTUAL_EXECUTION_RECEIPT_20261002_V2.json'
start_hashes={k:sha(p) for k,p in paths.items()};head_start=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
spec=json.loads(paths['protocol_v2'].read_text());gates=json.loads(paths['P1'].read_text());report=json.loads(paths['actual_output'].read_text())
execution=json.loads(paths['actual_execution_receipt'].read_text())
checks=[];mismatches=[];calendar_gaps=[];fold_evidence=[];read_output_paths=[];metric_pairs_checked=0;daily_metrics_checked=0

def check(name,passed,evidence=None):
    checks.append({'id':name,'passed':bool(passed),'evidence':evidence})
    if not passed and not name.startswith('full_train_calendar_'):mismatches.append(name)

def approx(a,b):
    return a is None and b is None or a is not None and b is not None and math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-12)

def corr(x,y):
    x=np.asarray(x);y=np.asarray(y)
    if len(x)<3 or np.ptp(x)==0 or np.ptp(y)==0:return {'rows':len(x),'pearson':None,'spearman':None,'reason':'INSUFFICIENT_OR_CONSTANT'}
    return {'rows':len(x),'pearson':float(pearsonr(x,y).statistic),'spearman':float(spearmanr(x,y).statistic),'reason':None}

def corr_equal(a,b):return a.get('rows')==b['rows'] and a.get('reason')==b['reason'] and approx(a.get('pearson'),b['pearson']) and approx(a.get('spearman'),b['spearman'])

old=paths['source_v1'].read_text();new=paths['source_v2'].read_text()
normalized=(old.replace('NONOVERLAP_MECHANISM_V8_V1.json','NONOVERLAP_MECHANISM_V8_V2.json').replace("audit.get('sources_sha256',{})","audit.get('verified_source_hashes',{})")
 .replace("'scripts/research_v8/nonoverlap_mechanism.py':","'scripts/research_v8/nonoverlap_mechanism_v2.py':").replace('v8-nonoverlap-mechanism-20261002-v1','v8-nonoverlap-mechanism-20261002-v2'))
check('V1_V2_algorithm_bytes_unchanged_after_declared_binding_changes',normalized==new)
registration=report['registration_start'];dependency_hashes={name:sha(root/name) for name in report['source_hashes']}
check('registered_current_dependency_hashes',dependency_hashes==report['source_hashes']==registration['source_hashes'])
check('registered_protocol_and_fold_binding',registration['protocol_hash']==start_hashes['protocol_v2'] and start_hashes['P1']==spec['fold_contract_sha256'])
check('registered_lock_and_label_audit_binding',registration['environment_hash']==dependency_hashes['environments/v8/uv.lock'] and registration['label_audit_sha256']==start_hashes['label_audit'])
source_receipt=root/spec['source_receipt'];source_receipt_sha=sha(source_receipt)
check('accepted_source_receipt_binding_without_raw_QA',source_receipt_sha==spec['source_receipt_sha256']==registration['data_manifest_hash'])
check('root_reported_actual_runner_protocol_sha',start_hashes['source_v2']=='1286c66b4439475cf381d6bdf21348dc0c02e5c53f4f2b7f15cdb85a7c76a5f1' and start_hashes['protocol_v2']=='a8e010cc22298320f1dd2cb7d818b943105425c99101f9a550103fec4ff82130')
expected_command=['bash','scripts/with_task_progress.sh','--title','V8 非重叠机制四fold诊断','--','/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python',str(paths['source_v2']),
 '--label-audit',str(paths['label_audit']),'--output',str(paths['actual_output']),'--state-directory','/home/xflops/coin-state/v8-nonoverlap-mechanism-20261002-v2']
check('actual_exit_receipt_source_output_command_bindings',start_hashes['actual_execution_receipt']=='9c85997f9c96bea9e9d8905d71707ae00fd4228c7120e2264a5cc51806788cb7' and execution['actual_unified_session_id']==98389 and execution['actual_unified_exit_code']==execution['actual_task']['exit_code']==0 and execution['actual_task']['id']=='f5ee55fc6c1645618454ae66b17a7efd' and execution['actual_task']['status']=='completed' and execution['output_sha256']==start_hashes['actual_output'] and execution['source_hashes']==dependency_hashes and execution['exact_command']==expected_command and execution['protocol_hash']==start_hashes['protocol_v2'] and execution['environment_hash']==registration['environment_hash'])
check('exact_registered_progress_wrapper_command',registration['exact_command']==expected_command)
check('all_fold_and_variant_registration',registration['all_folds']==gates['folds'] and registration['labels']==spec['variants'] and [x['fold'] for x in report['folds']]==spec['all_fold_ids'])
check('diagnostic_hypothesis_count',report['descriptive_hypotheses']==4*3*4*2)
economic=['net_CAGR','gross_executed_edge','net_executed_edge','strongest_benchmark_delta','break_even_roundtrip_cost','multiple_testing_corrected_evidence','executed_PnL_concentration']
check('economic_statistical_fields_null_and_no_qualification',all(k in report and report[k] is None for k in economic) and report['P1_gate']=='NOT_READY' and report['next_gate_allowed'] is False and report['candidate_status']=='NO_QUALIFIED_CANDIDATE' and report['candidate']=='NONE')
check('scope_flags_no_models_orders_locked',report['market_models_fit']==0 and report['orders_sent']==0 and report['locked_consumed'] is False and registration['model_family']=='NONE' and registration['hyperparameters']['scaler']=='NONE' and report['classification']=='SCREENING_MECHANISM_ONLY')
check('actual_standard_costs_remain_only_registered_scenarios',report['actual_standard_costs_roundtrip_bps']==gates['cost_bps_standard_roundtrip'])

for fold_spec,fold in zip(gates['folds'],report['folds']):
    path=Path(fold['calendar_path']);expected_path=Path('/home/xflops/coin-state/v8-nonoverlap-mechanism-20261002-v2')/f"{fold_spec['id']}-nonoverlap-label-calendar.parquet"
    check('calendar_path_'+fold_spec['id'],path==expected_path)
    digest=sha(path);check('calendar_hash_'+fold_spec['id'],digest==fold['calendar_sha256'])
    frame=pl.read_parquet(path);read_output_paths.append({'path':str(path),'sha256':digest,'rows':len(frame),'columns':frame.columns})
    train_start,val_start,test_start,end=[stamp(fold_spec[k]) for k in ('train_start','validation_start','test_start','test_end_exclusive')]
    cutoff=val_start-(gates['embargo_seconds']+gates['maximum_nominal_label_lag_seconds'])*US-1
    full_train=np.arange(train_start,val_start,MIN,dtype=np.int64);executed_train=np.arange(train_start,cutoff,MIN,dtype=np.int64);test_grid=np.arange(test_start,end,MIN,dtype=np.int64)
    check('complete_variant_set_'+fold_spec['id'],frame['label_variant'].unique().sort().to_list()==sorted(spec['variants']) and [x['variant'] for x in fold['variants']]==spec['variants'])
    check('only_explicit_train_OOS_and_observed_flow_'+fold_spec['id'],set(frame['split'].to_list())=={'TRAIN','OOS_SCREENING'} and set(frame['signal_kind'].to_list())=={'OBSERVED_FUTURE_FLOW_DIAGNOSTIC'} and frame['decision_us'].min()>=labels.BEGIN and frame['return_label_end_us'].max()<=labels.END)
    fold_rows=[]
    for variant_result in fold['variants']:
        variant=variant_result['variant'];v=frame.filter(pl.col('label_variant')==variant).sort('decision_us')
        labels.assert_nonoverlap(v)
        train_calendar=v.filter(pl.col('split')=='TRAIN');test_calendar=v.filter(pl.col('split')=='OOS_SCREENING')
        actual_train=train_calendar['decision_us'].to_numpy();actual_test=test_calendar['decision_us'].to_numpy()
        missing=np.setdiff1d(full_train,actual_train)
        gap={'fold':fold_spec['id'],'variant':variant,'complete_pre_validation_train_minutes':len(full_train),'actual_train_minutes':len(actual_train),'missing_train_minutes':len(missing),
             'fitting_cutoff_us':cutoff,'missing_start_us':int(missing[0]) if len(missing) else None,'missing_last_us':int(missing[-1]) if len(missing) else None,'actual_OOS_minutes':len(actual_test),'expected_OOS_minutes':len(test_grid)}
        calendar_gaps.append(gap)
        check('full_train_calendar_'+fold_spec['id']+'_'+variant,np.array_equal(actual_train,full_train),gap)
        check('actual_cutoff_window_complete_'+fold_spec['id']+'_'+variant,np.array_equal(actual_train,executed_train) and np.array_equal(actual_test,test_grid))
        check('fixed_maturity_deadline_'+fold_spec['id']+'_'+variant,train_calendar['split_maturity_deadline_us'].unique().to_list()==[cutoff] and test_calendar['split_maturity_deadline_us'].unique().to_list()==[end])
        expected_valid=v.select((pl.col('label_valid') & (pl.col('label_mature_us')<=pl.col('split_maturity_deadline_us'))).fill_null(False).alias('expected'))['expected']
        check('validity_exactly_label_and_deadline_'+fold_spec['id']+'_'+variant,v['diagnostic_outcome_valid'].equals(expected_valid))
        train=v.filter((pl.col('split')=='TRAIN') & pl.col('diagnostic_outcome_valid'));test=v.filter((pl.col('split')=='OOS_SCREENING') & pl.col('diagnostic_outcome_valid'))
        invalid=v.filter(~pl.col('label_valid'));immature=v.filter(pl.col('label_valid') & ~pl.col('diagnostic_outcome_valid'))
        check('summary_counts_and_invalid_rows_retained_'+fold_spec['id']+'_'+variant,variant_result['calendar_minutes']==len(v) and variant_result['train_valid']==len(train) and variant_result['test_valid']==len(test) and variant_result['invalid_or_immature']==len(invalid)+len(immature))
        fold_rows.append({'variant':variant,'present_calendar_rows':len(v),'train_rows':len(train_calendar),'OOS_rows':len(test_calendar),'invalid_future_rows_preserved':len(invalid),'immature_label_rows_preserved':len(immature),'used_train':len(train),'used_OOS':len(test),'complete_pre_validation_missing':len(missing)})
        expected_pairs=set(itertools.product(labels.STREAMS,labels.RETURN_STREAMS));pairs=variant_result['pairs'];actual_pairs=[(p['flow_stream'],p['return_stream']) for p in pairs]
        check('all_eight_pairs_no_OOS_selection_'+fold_spec['id']+'_'+variant,len(actual_pairs)==len(set(actual_pairs))==8 and set(actual_pairs)==expected_pairs)
        for pair in pairs:
            flow,ret=pair['flow_stream'],pair['return_stream'];fn,rn=f'{flow}__future_flow',f'{ret}__subsequent_return_proxy'
            tr=corr(train[fn].to_numpy(),train[rn].to_numpy());ts=corr(test[fn].to_numpy(),test[rn].to_numpy())
            direction=None if tr['spearman'] is None or tr['spearman']==0 else int(np.sign(tr['spearman']))
            agreement=None if direction is None or ts['spearman'] is None else bool(direction*ts['spearman']>0)
            response=None if direction is None or not len(test) else float(np.mean(direction*np.sign(test[fn].to_numpy())*test[rn].to_numpy())*10000)
            correct_primary=[flow,ret] in spec['primary_pairs']
            pair_id=fold_spec['id']+'_'+variant+'_'+flow+'_'+ret
            check('pair_summary_and_train_frozen_direction_'+pair_id,corr_equal(pair['train'],tr) and corr_equal(pair['test'],ts) and pair['train_frozen_direction']==direction and pair['OOS_sign_agreement']==agreement and approx(pair['train_signed_mean_response_bps'],response) and pair['primary']==correct_primary)
            metric_pairs_checked+=1
            day_frames=test.with_columns((pl.col('decision_us')//DAY).alias('UTC_day_index')).partition_by('UTC_day_index',maintain_order=True)
            expected_days=[datetime.fromtimestamp(int(df['decision_us'][0])//US,timezone.utc).date().isoformat() for df in day_frames]
            actual_days=[d['UTC_day'] for d in pair['daily']]
            daily_ok=actual_days==expected_days and sum(d['rows'] for d in pair['daily'])==len(test)
            weighted_sum=0.;weights=0
            for daily,df in zip(pair['daily'],day_frames):
                observed=corr(df[fn].to_numpy(),df[rn].to_numpy())
                daily_agreement=None if direction is None or observed['spearman'] is None else bool(direction*observed['spearman']>0)
                daily_response=None if direction is None else float(np.mean(direction*np.sign(df[fn].to_numpy())*df[rn].to_numpy())*10000)
                daily_ok=daily_ok and corr_equal(daily,observed) and daily['train_frozen_direction']==direction and daily['OOS_sign_agreement']==daily_agreement and approx(daily['train_signed_mean_response_bps'],daily_response)
                if daily_response is not None:weighted_sum+=daily['rows']*daily_response;weights+=daily['rows']
                daily_metrics_checked+=1
            daily_ok=daily_ok and approx(response,weighted_sum/weights if weights else None)
            check('daily_summary_consistency_and_frozen_direction_'+pair_id,daily_ok,{'days':len(day_frames),'total_rows':len(test),'daily_rows_sum':sum(d['rows'] for d in pair['daily'])})
    fold_evidence.append({'fold':fold_spec['id'],'calendar_sha256':digest,'variants':fold_rows})
    del frame
    print('Verified output calendar and all reported statistics for '+fold_spec['id'],flush=True)

end_hashes={k:sha(p) for k,p in paths.items()};end_dependencies={name:sha(root/name) for name in dependency_hashes}
check('all_input_source_and_output_bytes_unchanged',start_hashes==end_hashes and dependency_hashes==end_dependencies and all(sha(Path(p['path']))==p['sha256'] for p in read_output_paths))
head_end=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();missing_total=sum(x['missing_train_minutes'] for x in calendar_gaps)
findings=[]
if missing_total:
    findings.append({'id':'V8M-01','priority':'P2','status':'CONFIRMED_COMPLETE_CALENDAR_SCOPE_GAP','title':'Pre-validation TRAIN minute calendar is truncated at the fitting cutoff',
      'source':'scripts/research_v8/nonoverlap_mechanism_v2.py','source_lines':[106,108,163],'contract_fields':['calendar','train_cutoff','P1_GATE_V8.folds'],
      'actual_missing_variant_rows':missing_total,'per_fold_per_variant_missing_minutes':20,
      'evidence':'All 12 fold/variant calendars omit the predetermined 20 minute interval before validation_start, keeping 17260 of the 17280 pre-validation TRAIN minutes. All 10080 OOS minutes are present. The existing pre-cutoff calendar retains invalid and immature labels and the statistics are independently consistent with only label_valid and deadline-eligible rows. The fitting cutoff should filter statistics while the complete TRAIN calendar retains these additional unscored minutes.',
      'scope_consequence':'Do not accept a complete TRAIN calendar for V2. This is a calendar/output scope gap; it is not a new alpha-negative conclusion or an economic P1 failure.',
      'required_fix':'Preserve V2 outputs, append an independently bound thin supplement of the missing 20 minutes per fold using unchanged V5 labels and source definitions. Keep original scored rows, direction and all statistics unchanged; independently verify the supplemented calendar.'})
for mismatch in mismatches:findings.append({'id':mismatch,'priority':'P1','status':'OUTPUT_CONTRACT_MISMATCH'})
raw={'checks':checks,'calendar_gaps':calendar_gaps,'fold_evidence':fold_evidence,'findings':findings}
raw_path=state/'output_checks.json';raw_path.write_text(json.dumps(raw,indent=2)+'\n')
audit={'report_id':'V8_NONOVERLAP_MECHANISM_INDEPENDENT_AUDIT_20261002_V1','created_at_utc':datetime.now(timezone.utc).isoformat(),
 'status':'FAIL_DIAGNOSTIC_CALENDAR_SCOPE' if findings else 'PASS_DIAGNOSTIC_OUTPUT_SCOPE_ONLY',
 'audited_diagnostic_version':'V8_NONOVERLAP_MECHANISM_20261002_V2','candidate_status':'NO_QUALIFIED_CANDIDATE','P1_gate':'NOT_READY','P1_statistical_economic_gate':'NOT_EVALUATED','qualification_claim':False,
 'actual_HEAD_at_audit_start':head_start,'actual_HEAD_at_audit_end':head_end,
 'input_artifact_hashes':{k:{'path':str(paths[k]),'sha256':v} for k,v in start_hashes.items()},
 'verified_registered_dependency_hashes':dependency_hashes,'source_receipt_sha256_only':{'path':str(source_receipt),'sha256':source_receipt_sha},
 'source_and_output_bytes_unchanged_during_audit':start_hashes==end_hashes and dependency_hashes==end_dependencies,
 'scope':{'read_raw_or_bar_market_source_files':False,'repeat_source_QA':False,'read_market_derived_output_labels':True,'allowed_output_parquets':read_output_paths,
  'read_real_locked_or_model_artifacts':False,'fit_market_model':False,'read_builder_explanations_or_root_state_documents':False,
  'modified_original_code_output_or_registry':False,'GPU_used':False,'python':sys.executable,
  'purpose':'Read-only deterministic output verification; scipy descriptive correlations on supplied label outputs are recomputed, no market fitting or parameter selection.',
  'hash_only_code_dependencies_not_semantically_reaudited':list(dependency_hashes),
  'resource_policy':'hpc_linux bounded.sh/with_task_progress shared 5GB RAM, swap0, GPU0'},
 'original_actual_execution_evidence':{'evidence_kind':'verified_actual_execution_receipt_and_trusted_parent_message','actual_session_id':98389,'actual_exit_code':0,'actual_completed_days':76,'actual_total_days':76,
  'exact_registered_command_verified':registration['exact_command']==expected_command,'task_receipt_path':str(paths['actual_execution_receipt']),'task_receipt_sha256':start_hashes['actual_execution_receipt'],'actual_task_id':execution['actual_task']['id'],'output_sha256':execution['output_sha256'],
  'limitation':'Actual task exit 0, completed status, source/protocol/environment/output digests and exact command are cross-checked against the supplied immutable actual receipt. Root completion message corroborates 76/76 days. No mechanism JUnit/XML was generated or asserted.'},
 'independent_checker_execution':{'exit_code':0,'argv':['wsl','-d','hpc_linux','--','bash','-lc',
  'cd /mnt/d/codex/coin && scripts/with_task_progress.sh --title V8非重叠机制独立输出核验 -- env PYTHONPATH=/mnt/d/codex/coin/src /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python /home/xflops/coin-state/test-v8-mechanism-output-audit-20261002-v1/check_outputs.py'],
  'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024},
 'independent_checker':{'directory':str(state),'script_sha256':sha(state/'check_outputs.py'),'output':str(raw_path),'output_sha256':sha(raw_path)},
 'checked_pair_summaries':metric_pairs_checked,'checked_daily_statistics':daily_metrics_checked,'checks':checks,
 'complete_TRAIN_missing_variant_rows':missing_total,'calendar_gap_evidence':calendar_gaps,'findings':findings,'acceptance_blocker_ids':[x['id'] for x in findings],
 'limits':['The accepted 153-day source receipt and registered source-byte hashes are bound; raw source QA, label recomputation from raw bars and dataset-source hash reconstruction were not repeated.',
  'Only the allowed V2 output calendars, all 96 registered descriptive pair summaries and their UTC daily statistics were inspected/recomputed.',
  'No predictor, OOF surprise, matched direct-return executable ledger, benchmark, dependence correction, economic/statistical P1 gate or trading qualification is accepted.',
  'Observed future flow remains a mechanism diagnostic; adjacent minute labels overlap and no IID p-value is accepted.',
  'V2 calendar gap requires a preserved supplement; root confirmation of the ambiguity is not used to relabel the original incomplete scope as passed.'],
 'decision':'Preserve V2 source and output bytes with their actual successful process exit. Statistics and dependency bindings pass output checks within the recorded truncated TRAIN domain; block complete-calendar acceptance pending an independently verified thin supplement. Keep P1 NOT_READY and NO_QUALIFIED_CANDIDATE.'}
path=root/'reports/fast_research/V8_NONOVERLAP_MECHANISM_INDEPENDENT_AUDIT_20261002_V1.json'
if path.exists():raise RuntimeError('Refusing to overwrite prior audit evidence')
path.write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps({'report':str(path),'sha256':sha(path),'status':audit['status'],'blockers':audit['acceptance_blocker_ids'],
 'missing_TRAIN_variant_rows':missing_total,'pair_summaries_checked':metric_pairs_checked,'daily_statistics_checked':daily_metrics_checked,
 'non_calendar_mismatches':mismatches,'checks':len(checks),'actual_HEAD_at_start':head_start,'actual_HEAD_at_end':head_end},indent=2))