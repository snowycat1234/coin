"""UNRUN D034 small-metadata close; --binding is frozen only after five real closed0 roles.
Binding: helper_sha256; protocol {path,sha256}; roles SOURCE/TINY/RESEARCH/INDEPENDENT/COMPARISON
{report,report_sha256,required_status,expected_task_id,run_binding?,run_binding_sha256?};
owned_STATE_directories; project_files [{path,sha256}]; INDEPENDENT/COMPARISON roles also
source {path,sha256}; preserved_failures with the same
report/task fields plus exit_code=1 and host_result. Never read price/ledger payloads.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, subprocess, sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from quant import resources
ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state'); LIMIT=2_000_000
VM='VOL_MANAGED_BUY_AND_HOLD'; LOCK='state/dataset_lock.json'
LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
ARCHIVE='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
META='docs/archive/VOL_MANAGED_HOLD_547D_USED_ACTUAL_METADATA_20261003_V1'
OUT='reports/fast_research/VOL_MANAGED_HOLD_547D_ROOT_ACCEPTANCE_20261003_V1.json'
GIT='reports/GITHUB_VOL_MANAGED_HOLD_547D_SOURCE_BINDING_20261003_V1.json'
PARENT='protocols/PUBLIC_LONG_547D_FIXED_THREE_ACCOUNTS_20261003_V1.json'
PARENT_SHA='5366363196157c1629e2e00a00301956e61b2c295b476520359bc0bd55ac746d'
MONTHS=[f'2024-{m:02d}' for m in range(1,13)]+[f'2025-{m:02d}' for m in range(1,7)]
STATUSES=dict(SOURCE='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_578D_CALENDAR',TINY='PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT',RESEARCH='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING',INDEPENDENT='PASS_D034_SINGLE_VM_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR',COMPARISON='COMPLETE_D034_SAVED_SUMMARY_RISK_COST_COMPARISON_NOT_LONG_TERM_APR')
METRICS=dict(net_cash_PnL='net_PnL',gross_cash_PnL_same_quantities='gross_PnL_same_quantities',fees='fees',execution_costs='execution_costs',turnover='normalized_daily_turnover',max_observed_minute_MDD='minute_MDD',max_drawdown='daily_MDD',terminal_marked_notional='terminal_marked_notional')

def check(ok,reason):
    if not ok:raise ValueError(reason)

def ordinary(path):
    p=Path(path); base=ROOT if p.is_relative_to(ROOT) else STATE
    check(p.is_relative_to(base) and p.is_file() and p.stat().st_size<=LIMIT,'Ordinary small ROOT/STATE file only')
    for ancestor in (p,*p.parents):
        check(not ancestor.is_symlink(),'No symlink in metadata path')
        if ancestor==base:break
    check(p.suffix in {'.json','.py','.ps1','.xml','.md','.toml','.lock','.sh'} or p.name.endswith('LICENSE'),'No market/binary payload')
    return p

def small(path,digest=None,parse=True):
    data=ordinary(path).read_bytes(); actual=hashlib.sha256(data).hexdigest()
    check(digest is None or actual==digest,'Small frozen proof changed: '+str(path))
    return (json.loads(data) if parse else None),actual

def project(name):
    check(not Path(name).is_absolute() and '..' not in Path(name).parts,'ROOT-relative metadata only')
    check(name==LOCK or name=='configs/dataset_policy.json' or name.startswith(('scripts/','src/','tests/','protocols/','environments/','third_party/','docs/archive/','reports/')),'No private runtime Git source')
    return ordinary(ROOT/name)

def closed(identity,code=0):
    check(isinstance(identity,str) and re.fullmatch('[0-9a-f]{32}',identity),'Exact actual task identity')
    p=STATE/'task-progress'/('task-'+identity+'.json'); value,digest=small(p)
    check(value['id']==identity and type(value['exit_code']) is int and value['exit_code']==code and value['status']==('completed' if code==0 else 'failed'),'Actual terminal task, no assumed completion')
    check(all(type(value[k]) in (int,float) and math.isfinite(value[k]) for k in ('started_at','ended_at')),'Actual task timestamps')
    return dict(path=str(p),sha256=digest,task=value)

def canonical_reports(value):
    result={}
    for name,digest in value.items():
        p=(Path(name) if Path(name).is_absolute() else ROOT/name).resolve();check(p.is_relative_to(ROOT/'reports/fast_research') and str(p) not in result,'Unique ROOT report provenance');result[str(p)]=digest
    return result

def bounded(value):check(value['ram_limit_bytes']<=5_000_000_000 and value['swap_bytes']==0 and not value['gpu_used'],'Shared5GB/swap0/GPU0')
def near(a,b,tol):check(math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b))<=tol,'Saved summary differs from independent proof')

def owned(paths):
    check(paths and len(paths)==len(set(paths)),'Explicit distinct new D034 directories')
    rows=[]
    for name in paths:
        p=Path(name);check(p.parent==STATE and p.is_dir() and not p.is_symlink() and (p.name.startswith(('d034-','vol-managed-hold-','test-d034-','test-vol-managed-hold-547d-boundary-'))),'Only dedicated D034 ownership, not old D033 or all STATE')
        count=total=0
        for current,dirs,files in os.walk(p,followlinks=False):
            check(not any((Path(current)/name).is_symlink() for name in dirs+files),'No ownership symlink')
            for name in files:total+=(Path(current)/name).stat().st_size;count+=1
        rows.append(dict(path=str(p),bytes=total,files=count))
    total=sum(row['bytes'] for row in rows);check(total<=300_000_000,'Combined new D034 STATE300MB limit')
    return dict(directories=rows,total_owned_bytes=total,maximum_owned_bytes=300_000_000,scope='EXPLICIT_NEW_D034_FILE_STAT_ONLY')

def write(path,value):
    payload=(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode();check(len(payload)<=LIMIT,'Small metadata output')
    with path.open('xb') as stream:stream.write(payload)
    return hashlib.sha256(payload).hexdigest(),len(payload)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--binding',type=Path,required=True);args=parser.parse_args()
    check(os.environ.get('COIN_TASK_ID') and Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2','Actual bounded/progress clean environment')
    plan_path=args.binding;check(plan_path.parent==ROOT/'protocols','Root-frozen close binding');plan,plan_sha=small(plan_path)
    check(plan['ready_to_execute'] is True and set(plan['roles'])==set(STATUSES),'All actual closed roles ready')
    _,own_sha=small(__file__,plan['helper_sha256'],False);small(ROOT/ARCHIVE,own_sha,False)
    check(not (ROOT/OUT).exists() and not (ROOT/GIT).exists() and not (ROOT/META).exists(),'Exclusive new report/archive paths')
    before=resources.status();bounded(before);ownership_before=owned(plan['owned_STATE_directories'])
    proto=plan['protocol'];check(re.fullmatch(r'protocols/VOL_MANAGED_HOLD_547D_BYBIT_20261003_V([2-9]|[1-9][0-9]+)\.json',proto['path']),'Corrected protocol; failed V1 excluded')
    spec,proto_sha=small(project(proto['path']),proto['sha256']);parent,_=small(ROOT/PARENT,PARENT_SHA)
    check(spec['namespace_parent_protocol']==dict(path=PARENT,sha256=PARENT_SHA) and spec['strategy_ids']==[VM] and spec['planned_ledgers']==1,'Original fixed VM-only subset')
    for key in ('folds','source_receipt','source_receipt_sha256','source_scope','source_calendar','source_days_per_symbol','common_config','costs','environment','fee_settlement','fee_profile_path','fee_profile_sha256','market_type'):check(spec[key]==parent[key],'Parent dates/source/capital/risk/cost/fee/environment unchanged: '+key)
    check(spec['costs']['spread_bps']==[8] and spec['costs']['nominal_roundtrip_bps']==[36] and spec['maximum_new_owned_bytes']==280_000_000 and spec['module_combined_STATE_budget_bytes']==300_000_000 and spec['maximum_per_process_RSS_bytes']==3_500_000_000,'Exact preregistered cost and resource limits')
    scientific={**spec['frozen_sources'],proto['path']:proto_sha};check(scientific[LOCK]==LOCK_SHA,'Private scientific lock stays exact')
    hashes={str(plan_path.relative_to(ROOT)):plan_sha,ARCHIVE:own_sha};local={LOCK:LOCK_SHA};reports={};tasks={};copies=[]
    for name,digest in scientific.items():small(project(name),digest,False);hashes.update({name:digest} if name!=LOCK else {})
    for role,expected_status in STATUSES.items():
        item=plan['roles'][role];report,digest=small(project(item['report']),item['report_sha256']);check(report['status']==item['required_status']==expected_status,'Actual role status')
        check(report['binding']['task_id']==item['expected_task_id'],'Exact report/task');tasks[role]=closed(item['expected_task_id']);reports[role]=report;hashes[item['report']]=digest
        copies.append((tasks[role]['path'],role+'_TASK_ACTUAL.json',tasks[role]['sha256']))
        if item.get('run_binding'):
            value,rb_sha=small(item['run_binding'],item['run_binding_sha256']);check(value['task_id']==item['expected_task_id'],'Actual RUN_BINDING identity')
            if 'run_binding_sha256' in report:check(report['run_binding_sha256']==rb_sha,'Actual RUN_BINDING receipt SHA')
            copies.append((item['run_binding'],role+'_RUN_BINDING.json',rb_sha))
    source,tiny,actual,audit,comparison=[reports[k] for k in STATUSES]
    check(len({r['task']['id'] for r in tasks.values()})==5,'Five distinct actually completed tasks')
    for left,right in (('SOURCE','TINY'),('TINY','RESEARCH'),('RESEARCH','INDEPENDENT'),('INDEPENDENT','COMPARISON')):check(tasks[right]['task']['started_at']>=tasks[left]['task']['ended_at'],'Actual causal run order')
    check(plan['roles']['SOURCE']['report']==spec['source_receipt'] and plan['roles']['SOURCE']['report_sha256']==spec['source_receipt_sha256'] and source['source_files']==38 and source['days_per_symbol']==578 and source['actual_minute_rows']==1664640 and not source['locked_consumed'] and source['models_fit']==source['orders_sent']==source['GPU']==0,'Prior accepted38-source metadata only')
    check(plan['roles']['TINY']['report']==spec['required_smoke_receipt'] and tiny['junit_counts']==dict(tests=1,failures=0,errors=0,skipped=0) and tiny['test_exit_code']==0 and not tiny['market_inputs_read'],'Exactly new onecase passed, not old greens')
    junit=Path(tiny['run_dir'])/'junit.xml';small(junit,tiny['junit_sha256'],False);tree=ET.parse(junit).getroot();check({k:sum(int(s.get(k,0)) for s in tree.iter('testsuite')) for k in ('tests','failures','errors','skipped')}==tiny['junit_counts'],'Actual onecase JUnit');copies.append((str(junit),'TINY_JUNIT_ACTUAL.xml',tiny['junit_sha256']))
    check(actual['binding']['source_hashes']==tiny['binding']['source_hashes']==audit['verified_source_hashes']==comparison['source_hashes']==scientific and actual['binding']['protocol_sha256']==proto_sha,'Exact current scientific bindings across all new roles')
    check(actual['all_planned_ledgers_complete'] and actual['completed_ledgers']==actual['planned_ledgers']==1 and actual['accepted_smoke_sha256']==plan['roles']['TINY']['report_sha256'] and actual['source_bytes_unchanged'] and actual['market_models_fit']==actual['orders_sent']==0 and not actual['locked_consumed'] and actual['candidate_status']=='NO_QUALIFIED_CANDIDATE','Complete new account, no candidate/model/order/locked')
    oldref=spec['saved_comparison_references']['actual'];old,_=small(project(oldref['path']),oldref['sha256'])
    check(spec['reused_minute_input']==dict(report_path=oldref['path'],report_sha256=oldref['sha256'],path=old['minute_source']['path'],sha256=old['minute_source']['sha256']) and actual['reused_minute_input']==spec['reused_minute_input'] and actual['raw_normalized_market_files_read'] is False,'Exact existing Parquet reuse; no raw38 reread')
    check(actual['orchestrator_peak_RSS_bytes']<=3_500_000_000 and actual['owned_bytes']<=280_000_000 and actual['elapsed_seconds']<=1800,'Actual research resource bounds');bounded(actual['resources']);bounded(tiny['resources'])
    fold=actual['folds'][0];check(len(actual['folds'])==1 and fold['status']=='COMPLETE_PROXY_COMPARISON' and fold['days']==547 and len(fold['results'])==1,'Full uninterrupted single547day account')
    check(audit['actual_report_sha256']==plan['roles']['RESEARCH']['report_sha256'] and canonical_reports(audit['binding']['actual_reports'])=={str(project(plan['roles']['RESEARCH']['report']).resolve()):plan['roles']['RESEARCH']['report_sha256']} and audit['completed_ledgers_verified']==1 and len(audit['ledgers'])==1,'Unique actual independent proof')
    row,proof=fold['results'][0],audit['ledgers'][0];summary=row['summary']
    check(row['strategy']==proof['strategy']==VM and row['spread_bps']==proof['spread_bps']==8 and row['nominal_roundtrip_bps']==36 and summary['initial_nav']==10000 and summary['period_days']==547 and [r['month'] for r in proof['months']]==MONTHS,'Exact complete fixed-capital/cost/months')
    check(audit['completed_source_files_verified']==38 and audit['completed_minutes_verified']==787680 and audit['completed_days_verified']==547 and audit['completed_months_verified']==18 and audit['peak_RSS_bytes']<=3_500_000_000,'Independent scope/resource proof')
    for key,target in METRICS.items():near(summary[key],proof[target],1e-10 if key in ('turnover','max_observed_minute_MDD','max_drawdown') else 1e-7)
    near(proof['sparse_Decimal_settlement']['maximum_Decimal_cash_error_USDT'],0,1e-7)
    check(summary['trade_count']==proof['trade_count'] and {name:item['sha256'] for name,item in row['artifacts'].items()}==proof['ledger_artifact_hashes'],'Saved artifacts/trades match independent audit; payloads not reread')
    check(summary['annualized_return_is_descriptive_only'] and not summary['net_long_term_CAGR_proven'] and not summary['candidate_qualification_allowed'] and not summary['native_Bybit_market_or_filters_proven'] and not summary['real_BBO'],'No APR/native/BBO qualification')
    work=Path(actual['run_dir']);check(str(work) in plan['owned_STATE_directories'],'Actual ownership included');rb,rb_sha=small(work/'RUN_BINDING.json',actual['run_binding_sha256']);check(rb==actual['binding'],'Actual binding exact')
    for name,digest in scientific.items():small(work/'source-snapshot'/name,digest,False)
    check(len(comparison['cases'])==4 and {r['strategy'] for r in comparison['cases']}=={VM,'CASH','COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER','COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER'} and comparison['economic_action']=='SAVED_DEVELOPMENT_RISK_RETURN_COMPARISON_NO_INVESTMENT_ADOPTION','Saved four-account comparison, no new replay/adoption')
    check(comparison['small_report_hashes'][proto['path']]==proto_sha and comparison['small_report_hashes'][plan['roles']['RESEARCH']['report']]==plan['roles']['RESEARCH']['report_sha256'],'Comparison current protocol/actual pins')
    check(set(spec['saved_comparison_references'])=={'role','actual','independent','root'} and type(spec['saved_comparison_references']['role']) is str,'Only exact three saved references plus descriptive role')
    for name in ('actual','independent','root'):
        reference=spec['saved_comparison_references'][name];small(project(reference['path']),reference['sha256']);check(comparison['small_report_hashes'][reference['path']]==reference['sha256'],'Saved D033 accepted references exact');hashes[reference['path']]=reference['sha256']
    failures=plan['preserved_failures'];check(failures,'Preserve actual V1 synthetic failure')
    for number,item in enumerate(failures):
        receipt,digest=small(project(item['report']),item['report_sha256']);task=closed(item['expected_task_id'],1);check(receipt['binding']['task_id']==item['expected_task_id'] and receipt['status']==item['required_status'] and not receipt['status'].startswith('PASS') and item['exit_code']==item['host_result']['exit_code']==1,'Real failed evidence never upgraded')
        hashes[item['report']]=digest;copies.append((task['path'],f'PRESERVED_FAILURE_{number}_TASK_ACTUAL.json',task['sha256']))
    for item in plan['project_files']:small(project(item['path']),item['sha256'],False);check(item['path']!=LOCK,'Private lock not portable');hashes[item['path']]=item['sha256']
    for role,reported_sha in [('INDEPENDENT',audit['binding']['checker_sha256']),('COMPARISON',comparison['binding']['source_sha256'])]:
        code=plan['roles'][role]['source'];small(project(code['path']),code['sha256'],False);check(code['sha256']==reported_sha and hashes.get(code['path'])==reported_sha,'Executed helper exact public source bytes')
    check(audit['independent_source_sha256']==audit['binding']['checker_sha256'] and summary['fee_settlement_version']=='BYBIT_SPOT_RECEIVED_ASSET_V1','Executed fee/checker scope')
    check(sum(ordinary(origin).stat().st_size for origin,_,_ in copies)<=LIMIT and len({name for _,name,_ in copies})==len(copies),'Small distinct task/binding archive budget')
    (ROOT/META).mkdir()
    for origin,name,digest in copies:
        data=ordinary(origin).read_bytes();check(hashlib.sha256(data).hexdigest()==digest,'Closed metadata unchanged');target=ROOT/META/name
        with target.open('xb') as stream:stream.write(data)
        hashes[str(target.relative_to(ROOT))]=digest
    ownership_after=owned(plan['owned_STATE_directories']);after=resources.status();bounded(after)
    for name,digest in hashes.items():small(project(name),digest,False)
    common=dict(created_utc=datetime.now(UTC).isoformat(),binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=own_sha,closure_binding_sha256=plan_sha,root_own_completion='NOT_YET_CERTIFIED_LIVE_CALLER'),source_hashes=hashes,local_non_git_source_hashes=local,actual_task_bindings=tasks,preserved_actual_failures=failures,ownership_before=ownership_before,ownership_after=ownership_after,resources_before=before,resources_after=after,metadata_only=True,price_or_ledger_arrays_or_QA_or_old_green_replayed=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,candidate_status='NO_QUALIFIED_CANDIDATE',sustainable_net_APR='NOT_ESTABLISHED',native_account_certified=False,unseen_qualification=False)
    root=dict(common,status='PASS_ROOT_D034_547D_SINGLE_VM_SAVED_SUMMARY_METADATA_NOT_NATIVE_OR_LONG_TERM_APR',scientific_source_hashes=scientific,git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),completed_accounts=1,period_days=547,financial_summary=summary,months_from_independent_saved_audit=proof['months'],comparison_report=plan['roles']['COMPARISON'],root_RUN_BINDING_created=False,private_lock_body_archived=False)
    root_sha,root_bytes=write(ROOT/OUT,root);portable=dict(common,status='PASS_CLOSED_VOL_MANAGED_HOLD_547D_PORTABLE_SOURCE_BINDING_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR',source_hashes={**hashes,OUT:root_sha},root_report_sha256=root_sha,exclusions_from_portable_source_hashes=[LOCK],private_scientific_hash_guard_preserved=True,own_root_task_completed0_must_be_verified_by_later_push_helper=True)
    git_sha,git_bytes=write(ROOT/GIT,portable);check(root_bytes+git_bytes+sum(ordinary(origin).stat().st_size for origin,_,_ in copies)<=LIMIT,'Combined small closure archive/output2MB budget')
    print(json.dumps(dict(root_report=OUT,root_sha256=root_sha,portable_report=GIT,portable_sha256=git_sha,completed_prior_roles=5,root_caller_still_live=True)))

if __name__=='__main__':main()
