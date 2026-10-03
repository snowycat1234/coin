"""D038 V2: one exact small-source path compatibility over frozen V1 audit.

V1 failed before any financial arrays: its reused ROOT metadata whitelist did
not include docs/OPEN_SOURCE_REGISTRY.md. The original guard and every target,
financial statement and tolerance remain unchanged. No blanket docs allowance.
"""
from pathlib import Path
import hashlib, importlib.util

ROOT=Path('/mnt/d/codex/coin')
PARENT='docs/archive/PUBLIC_SMA_DAILY_INDEPENDENT_USED_SOURCE_20261003_V1.py'
PARENT_SHA='395538619fe754cb93f4ae986220a53998182a4547f0272c99cb62e050b331b2'
REGISTRY='docs/OPEN_SOURCE_REGISTRY.md'
REGISTRY_ARCHIVE='docs/archive/OPEN_SOURCE_REGISTRY_SMACROSSOVER_ACCEPTED_20261003_V1.md'
REGISTRY_SHA='8da5b04187f618759de190260bb7b277bf402c6f31b0480c37a85c8788e06f0e'
FAILED_REPORT='reports/fast_research/PUBLIC_SMA_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json'
FAILED_SHA='958f1168adbd9caeb60cdae4baf3364fe78297bac3a6edf0242c5a79947af419'
FAILED_TASK='f8285234aef34fc7a35dc97484ee944c'
OUT=ROOT/'reports/fast_research/PUBLIC_SMA_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V2.json'

def need(value,message):
    if not bool(value):raise ValueError(message)

def context():
    path=ROOT/PARENT
    need(hashlib.sha256(path.read_bytes()).hexdigest()==PARENT_SHA,'Executed V1 independent source byte identity')
    spec=importlib.util.spec_from_file_location('d038_failed_parent_private',path)
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    parent.__file__=__file__;parent.OUT=OUT
    private=parent.context();original_imported=private['imported'];proof={}
    def imported(path,digest,label):
        module=original_imported(path,digest,label)
        if Path(path)==ROOT/private['GUARD']:
            original_project=module.project
            module.small(module.project(REGISTRY_ARCHIVE),REGISTRY_SHA,False)
            failed,failed_sha=module.small(module.project(FAILED_REPORT),FAILED_SHA)
            failed_task=module.closed(FAILED_TASK,1)
            need(failed['binding']['task_id']==FAILED_TASK and failed['binding']['checker_sha256']==PARENT_SHA
                and failed['completed_ledgers_verified']==0 and not failed['runtime_inputs'] and not failed['target_causality']
                and failed['reason']=='No private runtime Git source','Preserve real V1 pre-array failure, never promote it to PASS')
            proof.update(report=FAILED_REPORT,report_sha256=failed_sha,actual_task=failed_task,source=PARENT,source_sha256=PARENT_SHA,
                V1_financial_arrays_entered=False,V1_completed_ledgers_verified=0,restored_scope='ONLY_EXACT_ROOT_REGISTRY_METADATA_PATH')
            def project(name):
                if name==REGISTRY:
                    result=module.ordinary(ROOT/name)
                    module.small(result,REGISTRY_SHA,False)
                    return result
                return original_project(name)
            module.project=project
        return module
    private['imported']=imported;original_write=private['write']
    def write(g,path,value):
        if Path(path)==OUT:
            value.update(preserved_failure=proof,metadata_source_guard_extension=dict(path=REGISTRY,sha256=REGISTRY_SHA,
                exact_archive=REGISTRY_ARCHIVE,unrestricted_docs_prefix_allowed=False,
                original_guard_source_unchanged=True,original_ordinary_symlink_containment_and_2MB_guard_reused=True,
                current_ROOT_path_byte_SHA_verified=True),V2_repeats_previous_financial_assertions=False,
                financial_and_target_algorithms_or_tolerances_changed=False)
        return original_write(g,path,value)
    private['write']=write
    return private

def main():context()['main']()

if __name__=='__main__':main()
