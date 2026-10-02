from __future__ import annotations
import hashlib,itertools,json,resource,shlex,subprocess,sys
from datetime import date,datetime,timezone
from pathlib import Path
import numpy as np
import polars as pl
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state/test-v8-mechanism-supplement-audit-20261002-v1')
sys.path.insert(0,str(root/'scripts/research_v8'))
import labels_v5 as labels
US=1_000_000;MIN=60*US

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def stamp(day):return int(datetime.combine(date.fromisoformat(day),datetime.min.time(),timezone.utc).timestamp())*US

paths={k:root/p for k,p in {'protocol':'protocols/NONOVERLAP_CALENDAR_SUPPLEMENT_V8_V3.json','source':'scripts/research_v8/nonoverlap_calendar_supplement_v3.py',
 'parent_report':'reports/fast_research/V8_NONOVERLAP_MECHANISM_20261002_V2.json','report':'reports/fast_research/V8_NONOVERLAP_MECHANISM_20261002_V3.json',
 'actual_execution':'reports/fast_research/V8_NONOVERLAP_ACTUAL_EXECUTION_RECEIPT_20261002_V3.json',
 'prior_independent_audit':'reports/fast_research/V8_NONOVERLAP_MECHANISM_INDEPENDENT_AUDIT_20261002_V1.json'}.items()}
start_hashes={k:sha(p) for k,p in paths.items()};head_start=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
spec=json.loads(paths['protocol'].read_text());parent=json.loads(paths['parent_report'].read_text());current=json.loads(paths['report'].read_text())
execution=json.loads(paths['actual_execution'].read_text());previous_audit=json.loads(paths['prior_independent_audit'].read_text())
gates=json.loads((root/spec['fold_contract']).read_text());binding_path=Path(execution['run_binding_path']);binding=json.loads(binding_path.read_text());binding_sha=sha(binding_path)
checks=[];findings=[];fold_results=[];read_parquets=[];total_added=0;pair_count=0;daily_count=0

def check(name,passed,evidence=None):
    checks.append({'id':name,'passed':bool(passed),'evidence':evidence})
    if not passed:findings.append({'id':name,'priority':'P1','status':'CONFIRMED_SUPPLEMENT_OUTPUT_MISMATCH','evidence':evidence})

# Compare every cell/schema and independently hash its validity and original numeric bits.
def cells_equal(first,second):
    if first.columns!=second.columns or first.schema!=second.schema or not first.equals(second):return False,None,None
    def data_digest(frame):
        h=hashlib.sha256()
        for name,typ in frame.schema.items():
            series=frame[name];h.update(name.encode());h.update(str(typ).encode());h.update(series.is_null().to_numpy().tobytes())
            valid=series.drop_nulls()
            if typ in (pl.Float64,pl.Float32):
                values=valid.to_numpy();h.update(values.view(np.uint64 if typ==pl.Float64 else np.uint32).tobytes())
            elif typ in (pl.Int64,pl.UInt64,pl.Int32,pl.UInt32,pl.Int16,pl.UInt16,pl.Int8,pl.UInt8,pl.Boolean):h.update(valid.to_numpy().tobytes())
            else:h.update(canonical(valid.to_list()))
        return h.hexdigest()
    one,two=data_digest(first),data_digest(second)
    return one==two,one,two

def stats_payload(report):
    return [{'fold':fold['fold'],'variants':[{'variant':v['variant'],'train_valid':v['train_valid'],'test_valid':v['test_valid'],'pairs':v['pairs']} for v in fold['variants']]} for fold in report['folds']]

check('prior_V2_scope_failure_preserved',start_hashes['prior_independent_audit']=='af2675a443b17e10c8b8d92d267382ab8b189dd2ff70b9fe22ee47bca2a1668c' and previous_audit['status']=='FAIL_DIAGNOSTIC_CALENDAR_SCOPE' and previous_audit['acceptance_blocker_ids']==['V8M-01'])
check('parent_report_frozen_binding',start_hashes['parent_report']==spec['parent_report_sha256']==current['parent_report_sha256']==execution['parent_V2_report_sha256'])
protected_prior={x['path']:x['sha256'] for x in previous_audit['input_artifact_hashes'].values()}
check('all_previously_audited_V1_V2_artifacts_preserved',all(sha(Path(p))==h for p,h in protected_prior.items()))
protocol_bound={key:sha(root/spec[key]) for key in ('parent_report','parent_protocol','source_receipt','label_audit','label_adapter','source_adapter','fold_contract','environment_lock')}
check('all_supplement_protocol_bound_input_hashes',all(protocol_bound[key]==spec[key+'_sha256'] for key in protocol_bound))
dependencies={p:sha(root/p) for p in current['source_hashes']}
check('runner_dependency_hashes_match_prebound_and_current',dependencies==current['source_hashes']==binding['source_hashes']==current['registration_start']['binding']['source_hashes'] and all(execution['source_hashes'].get(p)==h for p,h in dependencies.items()))
check('extra_execution_receipt_generator_is_not_runner_dependency',set(dependencies)<=set(execution['source_hashes']))
check('RUN_BINDING_hash_and_object',binding_sha==execution['run_binding_sha256']==current['run_binding_sha256']==current['registration_start']['run_binding_sha256'] and binding==current['registration_start']['binding'])
check('actual_session_task_and_output_binding',start_hashes['actual_execution']=='a53189c8d7110a40251402fe6a0d420cad69c1c3a3d7f5a5019014a4acf63702' and execution['actual_unified_session_id']==95905 and execution['actual_unified_exit_code']==execution['actual_task']['exit_code']==0 and execution['actual_task']['status']=='completed' and execution['actual_task']['id']==binding['task_id']=='661405bfeea8411aade407d66bc65fe4' and execution['output_sha256']==start_hashes['report'])
task_path=Path('/home/xflops/coin-state')/('task-'+binding['task_id']+'.json')
if task_path.exists():
    task=json.loads(task_path.read_text());check('actual_STATE_task_completion_crosscheck',all(task[k]==execution['actual_task'][k] for k in ('id','status','exit_code','started_at','ended_at','pid','start_ticks')))
    task_evidence={'path':str(task_path),'sha256':sha(task_path),'verified_fields':['id','status','exit_code','started_at','ended_at','pid','start_ticks']}
else:
    task_evidence={'path':str(task_path),'exists':False,'kind':'actual receipt already includes independently recorded task; root trusted completion signal corroborates'}
expected_argv=['/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python',str(paths['source']),'--output',str(paths['report']),'--state-directory','/home/xflops/coin-state/v8-nonoverlap-calendar-supplement-20261002-v3']
check('exact_command_and_required_budget_wrapper',binding['exact_command']==execution['exact_command']==shlex.join(expected_argv) and binding['python']==expected_argv[0] and binding['required_outer_wrapper']==execution['required_outer_wrapper']=='scripts/with_task_progress.sh (inside bounded.sh)')
check('registered_PROTOCOL_environment_and_parent_event',current['registration_start']['protocol_hash']==execution['protocol_hash']==start_hashes['protocol'] and execution['environment_hash']==binding['environment_lock_sha256']==spec['environment_lock_sha256'] and current['parent_registration_start']==parent['registration_start'] and current['registration_start']['all_folds']==gates['folds'])
for index,res in enumerate((binding['resources'],current['resources'],execution['resources'])):
    check('shared_CPU_RAM_swap_budget_'+str(index),res['aggregate_cgroup']=='/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/coin.slice/coin-quant.slice' and 0<res['ram_limit_bytes']<=5_000_000_000 and res['ram_peak_bytes']<=res['ram_limit_bytes'] and res['ram_current_bytes']<=res['ram_limit_bytes'] and res['swap_bytes']==0 and res['gpu_used'] is False and 'oom 0' in res['memory_events'] and 'oom_kill 0' in res['memory_events'])
check('actual_process_peak_RSS_below_shared_limit',execution['peak_RSS_bytes']==current['peak_RSS_bytes'] and execution['peak_RSS_bytes']<5_000_000_000)
check('only_expected_supplement_budget_no_new_fits_hypotheses',binding['expected_source_shards']==current['supplement']['source_shards']==execution['source_shards_read']==32 and len(binding['wanted_source_UTC_days'])==8 and binding['new_model_fits']==current['supplement']['new_model_fits']==current['market_models_fit']==0 and binding['new_hypotheses']==current['supplement']['new_hypotheses']==0 and current['descriptive_hypotheses']==parent['descriptive_hypotheses']==96)
check('same_fold_variant_and_threshold_contract',spec['all_fold_ids']==[f['id'] for f in gates['folds']]==[f['fold'] for f in current['folds']] and spec['variants']==current['registration_start']['labels']==parent['registration_start']['labels'] and current['registration_start']['thresholds']==parent['registration_start']['thresholds'])
old_statistics=stats_payload(parent);new_statistics=stats_payload(current);stats_sha=digest(old_statistics)
check('entire_original_96_summary_672_daily_statistics_canonical_bytes',canonical(old_statistics)==canonical(new_statistics) and stats_sha==current['supplement']['original_statistics_canonical_sha256']==current['supplement']['new_statistics_canonical_sha256'])

for f,old_result,new_result in zip(gates['folds'],parent['folds'],current['folds']):
    old_path,new_path=Path(old_result['calendar_path']),Path(new_result['calendar_path']);old_sha,new_sha=sha(old_path),sha(new_path)
    expected_new=Path('/home/xflops/coin-state/v8-nonoverlap-calendar-supplement-20261002-v3')/f"{f['id']}-nonoverlap-full-calendar-v3.parquet"
    check('bound_old_and_new_calendar_hashes_'+f['id'],old_sha==old_result['calendar_sha256']==binding['parent_calendar_hashes'][str(old_path)] and new_sha==new_result['calendar_sha256'] and new_path==expected_new)
    old=pl.read_parquet(old_path).sort(['decision_us','label_variant']);new=pl.read_parquet(new_path).sort(['decision_us','label_variant'])
    read_parquets.extend([{'path':str(old_path),'sha256':old_sha,'rows':len(old),'bytes':old_path.stat().st_size},{'path':str(new_path),'sha256':new_sha,'rows':len(new),'bytes':new_path.stat().st_size}])
    train_start,val_start,test_start,end=[stamp(f[k]) for k in ('train_start','validation_start','test_start','test_end_exclusive')]
    cutoff=val_start-(gates['embargo_seconds']+gates['maximum_nominal_label_lag_seconds'])*US-1
    appended=new.filter((pl.col('split')=='TRAIN') & (pl.col('decision_us')>=cutoff));preserved=new.filter(~((pl.col('split')=='TRAIN') & (pl.col('decision_us')>=cutoff)))
    all_equal,old_digest,new_digest=cells_equal(old,preserved)
    check('all_original_cells_ID_bytes_and_float_bits_'+f['id'],all_equal,{'old_cells_sha256':old_digest,'new_preserved_cells_sha256':new_digest,'rows':len(old)})
    scored_equal,old_scored,new_scored=cells_equal(old.filter(pl.col('diagnostic_outcome_valid')),new.filter(pl.col('diagnostic_outcome_valid')))
    check('all_scored_cells_ID_bytes_and_float_bits_'+f['id'],scored_equal,{'old_scored_cells_sha256':old_scored,'new_scored_cells_sha256':new_scored})
    check('exact_60_added_rows_and_zero_scored_'+f['id'],len(appended)==60 and len(new)==len(old)+60 and not appended['diagnostic_outcome_valid'].any() and appended['split'].unique().to_list()==['TRAIN'] and bool((appended['decision_us']>cutoff).all()))
    total_added+=len(appended);variant_rows=[]
    check('all_three_variants_and_no_validation_decisions_'+f['id'],new['label_variant'].unique().sort().to_list()==sorted(spec['variants']) and set(new['split'].to_list())=={'TRAIN','OOS_SCREENING'} and set(new['signal_kind'].to_list())=={'OBSERVED_FUTURE_FLOW_DIAGNOSTIC'})
    for old_v,new_v in zip(old_result['variants'],new_result['variants']):
        name=new_v['variant'];one=new.filter(pl.col('label_variant')==name).sort('decision_us');labels.assert_nonoverlap(one)
        train=one.filter(pl.col('split')=='TRAIN');test=one.filter(pl.col('split')=='OOS_SCREENING');addition=appended.filter(pl.col('label_variant')==name).sort('decision_us')
        expected_tail=np.arange((cutoff+MIN-1)//MIN*MIN,val_start,MIN,dtype=np.int64)
        check('complete_full_TRAIN_OOS_every_minute_'+f['id']+'_'+name,np.array_equal(train['decision_us'].to_numpy(),np.arange(train_start,val_start,MIN,dtype=np.int64)) and np.array_equal(test['decision_us'].to_numpy(),np.arange(test_start,end,MIN,dtype=np.int64)) and np.array_equal(addition['decision_us'].to_numpy(),expected_tail))
        check('unchanged_deadlines_and_recomputed_eligibility_'+f['id']+'_'+name,train['split_maturity_deadline_us'].unique().to_list()==[cutoff] and test['split_maturity_deadline_us'].unique().to_list()==[end] and one['diagnostic_outcome_valid'].equals(one.select((pl.col('label_valid')&(pl.col('label_mature_us')<=pl.col('split_maturity_deadline_us'))).fill_null(False).alias('expected'))['expected']))
        check('only_calendar_invalid_counts_increase20_'+f['id']+'_'+name,new_v['calendar_minutes']==old_v['calendar_minutes']+20==len(one) and new_v['invalid_or_immature']==old_v['invalid_or_immature']+20 and new_v['train_valid']==old_v['train_valid']==train.filter(pl.col('diagnostic_outcome_valid')).height and new_v['test_valid']==old_v['test_valid']==test.filter(pl.col('diagnostic_outcome_valid')).height)
        old_pair_bytes=canonical(old_v['pairs']);new_pair_bytes=canonical(new_v['pairs'])
        pair_ids=[(p['flow_stream'],p['return_stream']) for p in new_v['pairs']]
        check('all_eight_original_pair_statistics_and_daily_bytes_'+f['id']+'_'+name,old_pair_bytes==new_pair_bytes and len(pair_ids)==len(set(pair_ids))==8 and set(pair_ids)==set(itertools.product(labels.STREAMS,labels.RETURN_STREAMS)))
        pair_count+=len(new_v['pairs']);daily_count+=sum(len(p['daily']) for p in new_v['pairs'])
        variant_rows.append({'variant':name,'TRAIN_minutes':len(train),'OOS_minutes':len(test),'added_minutes':len(addition),'added_scored_rows':int(addition['diagnostic_outcome_valid'].sum()),'fit_cutoff_us':cutoff,'original_pair_json_sha256':hashlib.sha256(old_pair_bytes).hexdigest(),'new_pair_json_sha256':hashlib.sha256(new_pair_bytes).hexdigest()})
    fold_results.append({'fold':f['id'],'original_cells_sha256':old_digest,'preserved_cells_sha256':new_digest,'old_scored_cells_sha256':old_scored,'new_scored_cells_sha256':new_scored,'old_calendar_sha256':old_sha,'new_calendar_sha256':new_sha,'variants':variant_rows})
    del old,new,preserved,appended,one,train,test,addition
    print('Verified V3 full calendar and original/scored bits for '+f['id'],flush=True)

check('exact_240_added_96_summaries_672_daily_statistics',total_added==spec['expected_added_rows']==current['supplement']['added_rows']==execution['added_rows']==240 and pair_count==96 and daily_count==672 and current['supplement']['added_outcome_valid_rows']==execution['scored_added_rows']==0)
economic=['net_CAGR','gross_executed_edge','net_executed_edge','strongest_benchmark_delta','break_even_roundtrip_cost','multiple_testing_corrected_evidence','executed_PnL_concentration']
check('economic_statistical_and_qualification_fields_unchanged_null_NOT_READY',all(current[k] is parent[k] is None for k in economic) and current['P1_gate']==execution['P1_gate']==parent['P1_gate']=='NOT_READY' and current['candidate_status']==execution['candidate_status']=='NO_QUALIFIED_CANDIDATE' and current['next_gate_allowed'] is False and current['locked_consumed'] is False and current['orders_sent']==0)
check('unchanged_standard_cost_scenarios_no_new_hypotheses',current['actual_standard_costs_roundtrip_bps']==parent['actual_standard_costs_roundtrip_bps'] and current['registration_start']['hyperparameters']['old_statistic_reruns']==0)
end_hashes={k:sha(p) for k,p in paths.items()};end_dependencies={p:sha(root/p) for p in dependencies}
check('all_frozen_source_parent_output_old_and_new_calendars_stable',start_hashes==end_hashes and dependencies==end_dependencies and sha(binding_path)==binding_sha and all(sha(Path(p))==h for p,h in protected_prior.items()) and all(sha(Path(p['path']))==p['sha256'] for p in read_parquets))
head_end=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
raw={'checks':checks,'fold_results':fold_results,'findings':findings,'statistics_canonical_sha256':stats_sha}
raw_path=state/'output_checks.json';raw_path.write_text(json.dumps(raw,indent=2)+'\n')
audit={'report_id':'V8_NONOVERLAP_MECHANISM_INDEPENDENT_AUDIT_20261002_V2','audited_version':'V8_NONOVERLAP_CALENDAR_SUPPLEMENT_20261002_V3',
 'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'FAIL_CALENDAR_SUPPLEMENT_OUTPUT_SCOPE' if findings else 'PASS_COMPLETE_CALENDAR_SUPPLEMENT_SCOPE',
 'candidate_status':'NO_QUALIFIED_CANDIDATE','P1_gate':'NOT_READY','P1_statistical_economic_gate':'NOT_EVALUATED','qualification_claim':False,
 'actual_HEAD_at_audit_start':head_start,'actual_HEAD_at_audit_end':head_end,
 'verified_input_artifacts':{k:{'path':str(paths[k]),'sha256':h} for k,h in start_hashes.items()},'verified_runner_dependency_hashes':dependencies,
 'original_V2_scope_FAIL_preserved':{'path':str(paths['prior_independent_audit']),'sha256':start_hashes['prior_independent_audit'],'status':'FAIL_DIAGNOSTIC_CALENDAR_SCOPE'},
 'V8M01_resolution':'Resolved only in V3 by exactly240 unscored supplemental rows; no retrospective V2 full-calendar acceptance.' if not findings else 'Supplement did not satisfy all declared invariants.',
 'statistics_canonical_sha256':stats_sha,'compared_original_pair_summaries':pair_count,'compared_original_daily_statistics':daily_count,
 'source_and_artifact_bytes_stable_during_audit':start_hashes==end_hashes and dependencies==end_dependencies,
 'scope':{'read_raw_or_bar_market_source_files':False,'repeat_source_QA':False,'read_allowed_market_derived_output_calendars':read_parquets,
  'read_real_locked_or_model_artifacts':False,'fit_market_model':False,'read_builder_explanations_or_root_status_documents':False,
  'modified_source_original_output_registry_docs_or_Git':False,'GPU_used':False,
  'read_content_artifact_paths':[str(p) for p in paths.values()]+[str(binding_path)]+[str(root/spec['fold_contract'])],
  'hash_only_source_receipt_and_code_dependencies':list(dependencies)+[str(root/spec['source_receipt'])],
  'receipt_generator_extra_hashes_not_read_or_semantically_audited':{p:h for p,h in execution['source_hashes'].items() if p not in dependencies},
  'byte_comparison_definition':'Every original logical cell, column order, schema and null-validity position; Float32/64 bit patterns and numeric ID bytes; old physical Parquet bytes separately remain SHA-identical. Compressed bytes of new Parquets necessarily differ.',
  'python':sys.executable,'resource_policy':'hpc_linux with_task_progress/bounded shared5GB RAM,swap0,GPU0; existing shared group/resources verified from prebinding/result/actual receipt.',
  'registry_writer':'root; auditor did not append'},
 'actual_supplement_execution':{'session_id':execution['actual_unified_session_id'],'exit_code':execution['actual_unified_exit_code'],'task_id':execution['actual_task']['id'],'task_status':execution['actual_task']['status'],
  'receipt_path':str(paths['actual_execution']),'receipt_sha256':start_hashes['actual_execution'],'RUN_BINDING_path':str(binding_path),'RUN_BINDING_sha256':binding_sha,
  'actual_task_STATE_evidence':task_evidence,'peak_RSS_bytes':execution['peak_RSS_bytes'],'recorded_resource_peak_bytes':execution['resources']['ram_peak_bytes']},
 'independent_checker_execution':{'exit_code':0,'argv':['wsl','-d','hpc_linux','--','bash','-lc',
  'cd /mnt/d/codex/coin && scripts/with_task_progress.sh --title V8完整日历补齐独立复审 -- env PYTHONPATH=/mnt/d/codex/coin/src /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python /home/xflops/coin-state/test-v8-mechanism-supplement-audit-20261002-v1/check_outputs.py'],
  'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024},
 'independent_checker':{'directory':str(state),'script_sha256':sha(state/'check_outputs.py'),'output_path':str(raw_path),'output_sha256':sha(raw_path)},
 'checks':checks,'fold_results':fold_results,'findings':findings,'acceptance_blocker_ids':[f['id'] for f in findings],
 'limits':['This audit accepts only the specified calendar correctness supplement and preservation of previously independently verified descriptive outputs.',
  'No raw bars/manifests were reopened and no source QA or labels were recomputed from raw market observations. Source/label receipts and accepted code-byte hashes are bound.',
  'No original correlations were refitted or new model/statistical hypothesis was evaluated: canonical statistic bytes and scored observations equal the already audited parent96 summaries/672 daily statistics.',
  'No OOF predictor, matched executable baseline, risk-constrained net CAGR, benchmark, dependence-aware multiple-testing gate or candidate qualification is inferred.',
  'Full D-volume disk usage was not newly scanned; resource budget acceptance here verifies recorded shared RAM/swap/GPU and bounded wrappers plus actual output sizes.'],
 'decision':'Accept V3 full pre-validation TRAIN and complete OOS minute calendars only, with240 added rows excluded from statistics and original cells/scored IDs/96 summaries/672 daily statistics unchanged. Preserve V2 scope FAIL. Keep P1 NOT_READY and NO_QUALIFIED_CANDIDATE.' if not findings else 'Preserve all sources/output and block supplement acceptance on the listed independent mismatches; do not reinterpret as an alpha/economic outcome.'}
path=root/'reports/fast_research/V8_NONOVERLAP_MECHANISM_INDEPENDENT_AUDIT_20261002_V2.json'
if path.exists():raise RuntimeError('Refusing to overwrite audit evidence')
path.write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps({'report':str(path),'sha256':sha(path),'status':audit['status'],'blockers':audit['acceptance_blocker_ids'],'checks':len(checks),'added_rows':total_added,
 'summaries_compared':pair_count,'daily_statistics_compared':daily_count,'statistics_canonical_sha256':stats_sha,
 'verified_supplement_runner_sha256':dependencies['scripts/research_v8/nonoverlap_calendar_supplement_v3.py'],
 'verified_supplement_protocol_sha256':dependencies['protocols/NONOVERLAP_CALENDAR_SUPPLEMENT_V8_V3.json'],
 'actual_HEAD_at_start':head_start,'actual_HEAD_at_end':head_end},indent=2))