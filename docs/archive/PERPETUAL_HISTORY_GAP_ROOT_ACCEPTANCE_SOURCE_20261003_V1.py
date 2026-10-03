"""Accept an actual failed-source diagnosis, never the incomplete market source."""
import argparse, hashlib, importlib.util, json, os, resource, sys, time
from pathlib import Path
from quant import resources
from scripts.research_v8.registry import FIELDS,append_event
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
OUT='reports/fast_research/PERPETUAL_HISTORY_GAP_ROOT_ACCEPTANCE_20261003_V1.json'
PORTABLE='reports/GITHUB_PERPETUAL_HISTORY_GAP_SOURCE_BINDING_20261003_V1.json'
STATUS='PASS_ROOT_D042_OFFICIAL_MONTH_AND_DAY_GAP_DIAGNOSIS_SOURCE_REJECTED_NO_ECONOMICS'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--binding',required=True,type=Path);a=p.parse_args()
    spec=importlib.util.spec_from_file_location('gap_root_guard',ROOT/'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py')
    g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    plan,plan_sha=g.small(a.binding)
    assert os.environ.get('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2'
    assert plan['checker_sha256']==sha(__file__) and plan['ready_to_execute'] is True
    identity='D042-HISTORY-GAP-ROOT-20261003-V1';event=dict.fromkeys(FIELDS)
    event.update(experiment_id=identity,event_id=identity+':START',event_type='OPERATIONAL_DIAGNOSTIC_ACCEPTANCE_START',
        protocol_hash=plan_sha,feature_set='ONE_OFFICIAL_MARK_GAP_AND_FAILED_SOURCE',labels='NONE',model_family='NONE',
        seed=None,thresholds={'wall_seconds':120,'peak_RSS_bytes':512_000_000},cost_assumptions='NOT_COMPUTED',
        all_folds='SOURCE_ONLY_NO_ECONOMICS',success_failure='START_BEFORE_METADATA_CLOSE',
        reason_for_next_experiment='Accept diagnosis and reject incomplete full history; choose complete calendar before new PnL',
        result_influenced_later_choice=False,source_hashes=plan['source_hashes'],exact_command=' '.join([sys.executable,*sys.argv]))
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    g.bounded(resources.status());started=time.monotonic();tasks={};rows={};proofs={}
    assert set(plan['roles'])=={'METADATA','SOURCE_FAILURE','RAW_DIAGNOSTIC','OFFICIAL_DAY'}
    for role,item in plan['roles'].items():
        row,digest=g.small(ROOT/item['path'],item['sha256'])
        assert row['status']==item['status'] and row['binding']['task_id']==item['task_id']
        tasks[role]=g.closed(item['task_id'],item['exit_code']);rows[role]=row;proofs[item['path']]=digest
    meta,failed,diagnostic,day=(rows[k] for k in ('METADATA','SOURCE_FAILURE','RAW_DIAGNOSTIC','OFFICIAL_DAY'))
    assert meta['completed_files']==meta['required_files']==148 and meta['archive_bodies_downloaded']==0
    assert failed['completed_files']==83 and failed['archive_bodies_downloaded']==84 and failed['reason']=='Missing/shifted minute'
    clock=diagnostic['raw_clock_diagnostic'];missing=['2024-08-12T10:02:00+00:00','2024-08-12T10:03:00+00:00']
    assert diagnostic['failed_producer_report_sha256']==proofs[plan['roles']['SOURCE_FAILURE']['path']]
    assert clock['missing_UTC_minutes']==missing and clock['missing_minutes']==2
    assert day['diagnostic_sha256']==proofs[plan['roles']['RAW_DIAGNOSTIC']['path']]
    assert day['actual_rows']==1438 and day['expected_rows']==1440 and day['missing_UTC_minutes']==missing
    assert day['complete_day'] is False and day['monthly_missing_records_available'] is False
    assert not diagnostic['source_gap_repaired'] and not day['source_repaired']
    hashes={}
    for name,value in plan['source_hashes'].items():
        if name=='state/dataset_lock.json':assert sha(ROOT/name)==value;continue
        g.small(g.project(name),value,False);hashes[name]=value
    private={'state/dataset_lock.json':'29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'}
    assert all(sha(ROOT/k)==v for k,v in private.items())
    folder=ROOT/'docs/archive/PERPETUAL_HISTORY_GAP_USED_ACTUAL_METADATA_20261003_V1';folder.mkdir()
    for role,item in plan['roles'].items():
        task_path=folder/(role+'_TASK.json');task_path.write_bytes(Path(tasks[role]['path']).read_bytes())
        hashes[task_path.relative_to(ROOT).as_posix()]=sha(task_path)
        rb_path=Path(plan['run_bindings'][role]);assert sha(rb_path)==rows[role]['run_binding_sha256']
        rb_dst=folder/(role+'_RUN_BINDING.json');rb_dst.write_bytes(rb_path.read_bytes());hashes[rb_dst.relative_to(ROOT).as_posix()]=sha(rb_dst)
    run=STATE/'d042-perpetual-history-gap-root-20261003-v1';run.mkdir()
    binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),protocol_sha256=plan_sha,
        source_hashes=hashes,exact_command=[sys.executable,*sys.argv])
    rb_sha,_=g.write(run/'RUN_BINDING.json',binding)
    prior=ROOT/'reports/GITHUB_PERPETUAL_PUBLIC_BENCHMARK_STAGED_PREFLIGHT_20261003_V1.json'
    old,_=g.small(prior);assert old['status']=='STAGED_MODULE_CHECKPOINT_PASS'
    verified={**old['frozen_blob_hashes'],**proofs,str(a.binding.relative_to(ROOT)):plan_sha}
    aliases=[dict(original_path='docs/OPEN_SOURCE_REGISTRY.md',original_sha256='1c33a5a19063cd4a4331892c1f2490d80a4fa30ad2ee138d39a20090b92b503d',
        archive_path='docs/archive/OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_HISTORY_20261003_V1.md')]
    assert sha(ROOT/aliases[0]['archive_path'])==aliases[0]['original_sha256']
    result=dict(status=STATUS,binding=binding,run_binding_sha256=rb_sha,run_dir=str(run),roles=tasks,
        metadata_objects_checked=148,completed_producer_format_files=83,downloaded_archives_before_stop=84,
        rejected_full_period='2024-01-01..<2025-07-01',missing_UTC_minutes=missing,
        original_source_acceptance=False,full148_QA_executed=False,source_gap_repaired=False,
        original_partial_sources_preserved=True,old83_QA_repeated=False,market_arrays_read=False,
        economics='NOT_COMPUTED',investment_candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',
        next_predeclared_source_period='2024-01-01..<2024-08-01_213D',selection_criterion='COMPLETE_CALENDAR_BEFORE_KNOWN_GAP_NO_NEW_PNL_VIEW',
        subsequent_period_if_complete='2024-09-01..<2025-07-01_303D_SEPARATE_ACCOUNT_NO_NAV_STITCH',
        source_hashes=hashes,verified_prior_files=verified,historical_source_aliases=aliases,
        local_non_git_hash_guard=private,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,
        elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    assert result['elapsed_seconds']<=120 and result['peak_RSS_bytes']<=512_000_000
    digest,_=g.write(ROOT/OUT,result)
    g.write(ROOT/PORTABLE,dict(status='D042_GAP_DIAGNOSTIC_BYTES_PENDING_ROOT_EXIT',source_hashes=hashes,
        verified_prior_files={**verified,OUT:digest},historical_source_aliases=aliases,local_non_git_hash_guard=private,
        root_task_id=binding['task_id'],market_data_source_accepted=False))
    append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=identity+':RESULT',event_type='OPERATIONAL_DIAGNOSTIC_ACCEPTANCE_RESULT',
        success_failure=STATUS,artifact_path=OUT,artifact_sha256=digest))
    print(json.dumps(dict(status=STATUS,root_report_sha256=digest)))
if __name__=='__main__':main()
