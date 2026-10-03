"""Thin reuse of D039 pytest orchestration; preselected new tests only, no market IO."""
import argparse, hashlib, json, os, resource, shlex, subprocess, sys, time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from quant import resources
from scripts.investment import public_pair_diagnostics as reuse
ROOT, STATE = reuse.ROOT, reuse.STATE
ARCHIVE = 'docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py'
require, sha, save = reuse.require, reuse.sha, reuse.save

def main():
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--experiment-id',required=True);a=p.parse_args()
    require(os.environ.get('COIN_TASK_ID') and Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2','Actual bounded task in pinned environment')
    require(sha(__file__)==sha(ROOT/ARCHIVE),'Exact case runner archive')
    spec,proto_sha=reuse.small(a.protocol)
    hashes=dict(spec['frozen_sources']);hashes[a.protocol.relative_to(ROOT).as_posix()]=proto_sha
    for name,digest in hashes.items():require(sha(ROOT/name)==digest,'Frozen case source '+name)
    tests=spec['tests'];test=tests[0]
    require(all(t in hashes and t.startswith('tests/') for t in tests) and ARCHIVE in hashes,'New case and runner frozen before test')
    work=a.run_dir
    require(work.is_relative_to(STATE) and work.resolve()==work and not work.exists(),'Exclusive new case STATE')
    require(a.output.parent==ROOT/'reports/fast_research' and not a.output.exists(),'Exclusive small case receipt')
    work.mkdir();command=[sys.executable,'-m','pytest',*tests,'-q','--basetemp='+str(work/'pytest'),'-o','cache_dir='+str(work/'pytest-cache'),'--junitxml='+str(work/'junit.xml')]
    binding=dict(task_id=os.environ['COIN_TASK_ID'],git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        protocol_sha256=proto_sha,source_hashes=hashes,sys_prefix=sys.prefix,python=sys.executable,
        exact_command=shlex.join([sys.executable,__file__,*sys.argv[1:]]),exact_test_command=shlex.join(command),
        environment_lock_sha256=hashes['environments/v8/uv.lock'],data_scope='SYNTHETIC_ONLY')
    save(work/'RUN_BINDING.json',binding)
    event=dict.fromkeys(reuse.FIELDS);event.update(experiment_id=a.experiment_id,event_id=a.experiment_id+':START',event_type='OPERATIONAL_START',
        git_commit=binding['git_commit'],data_manifest_hash=hashes[test],protocol_hash=proto_sha,feature_set='NONE_NEW_PRODUCT_AND_SIGNAL_SYNTHETIC_TESTS',labels='NONE',model_family='NONE',
        hyperparameters={},seed='NOT_APPLICABLE_DETERMINISTIC',thresholds=spec['calculation_rules'],cost_assumptions=spec['fee_profile'],all_folds=['SYNTHETIC_ONLY'],
        success_failure='START',reason_for_next_experiment='Validate new product accounting and causal strategy boundaries before research economics',result_influenced_later_choice=False,
        source_hashes=hashes,exact_command=binding['exact_command'],environment_lock_sha256=binding['environment_lock_sha256'],run_binding_sha256=sha(work/'RUN_BINDING.json'),market_models_fit=0)
    registered=reuse.append_event(ROOT/'reports/experiment_registry.jsonl',event)
    started=time.monotonic();value=dict(status='FAIL_BOUNDED_RESEARCH_TESTS_SYNTHETIC',binding=binding,registration_start=registered,
        run_dir=str(work),run_binding_sha256=sha(work/'RUN_BINDING.json'),market_or_saved_ledger_arrays_read=False,old_tests_replayed=False,models_fit=0,orders_sent=0,locked_consumed=False)
    try:
        before=resources.status();require(before['ram_limit_bytes']<=5_000_000_000 and before['swap_bytes']==0,'Shared hard RAM and swap bounds')
        result=subprocess.run(command,cwd=ROOT,check=False,timeout=120)
        value['test_exit_code']=result.returncode
        if (work/'junit.xml').is_file():
            tree=ET.parse(work/'junit.xml').getroot();value['junit_counts']={k:sum(int(s.get(k,0)) for s in tree.iter('testsuite')) for k in ('tests','errors','failures','skipped')}
            value['junit_sha256']=sha(work/'junit.xml')
        require(result.returncode==0 and value.get('junit_counts',{}).get('tests',0)>0 and all(value['junit_counts'][k]==0 for k in ('errors','failures','skipped')),'Only the preselected new substantive tests passed')
        require(all(sha(ROOT/n)==h for n,h in hashes.items()),'Frozen case sources remain exact')
        value['source_bytes_unchanged']=True;value['status']='PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT'
    except Exception as e:
        value.update(error_type=type(e).__name__,reason=str(e));raise
    finally:
        value.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)*1024,
            owned_bytes=sum(x.stat().st_size for x in work.rglob('*') if x.is_file()),resources=resources.status())
        save(a.output,value);reuse.append_event(ROOT/'reports/experiment_registry.jsonl',{**event,'event_id':a.experiment_id+':RESULT','event_type':'OPERATIONAL_RESULT','success_failure':value['status'],'artifact_path':a.output.relative_to(ROOT).as_posix(),'artifact_sha256':sha(a.output)})
        print(json.dumps(dict(status=value['status'],sha256=sha(a.output),task_id=binding['task_id'])))

if __name__=='__main__':main()
