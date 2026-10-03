"""Bind two already accepted source manifests; no new data or repeated QA."""
import argparse,hashlib,importlib.util,os,resource,time
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
LOCK='state/dataset_lock.json';LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--binding',type=Path,required=True);a=p.parse_args()
    assert sha(ROOT/GUARD)==GUARD_SHA and sha(ROOT/LOCK)==LOCK_SHA
    loader=importlib.util.spec_from_file_location('_d044_source_reuse_guard',ROOT/GUARD)
    g=importlib.util.module_from_spec(loader);loader.loader.exec_module(g)
    plan,ph=g.small(a.binding);run=Path(plan['run_dir']);started=time.monotonic()
    g.check(plan['ready_to_execute'] is True and os.getenv('COIN_TASK_ID') and run.parent==STATE and not run.exists(),'New metadata STATE/task')
    run.mkdir();binding=dict(task_id=os.environ['COIN_TASK_ID'],source_hashes=plan['source_hashes'],binding_sha256=ph)
    rb,_=g.write(run/'RUN_BINDING.json',binding);roots={};manifests={}
    for label,item in plan['sources'].items():
        source,h=g.small(g.project(item['root']['path']),item['root']['sha256'])
        g.check(source['status']==item['root']['required_status'] and source.get('funding_unit_certified',False) is False,'Prior source-only qualification')
        roots[label]=g.closed(source['binding']['task_id'])
        manifests[label],_=g.small(g.project(item['manifest']['path']),item['manifest']['sha256'])
        g.check(manifests[label]['status']==item['manifest']['required_status'],'Exact accepted input metadata')
    new,old=manifests['213D'],manifests['122D90D'];files=dict(new['source_files'])
    g.check(not(set(files)&set(old['source_files'])),'Distinct dated source IDs without relabeling owners')
    files.update(old['source_files']);windows=[*new['windows'],*old['windows']]
    g.check(len(files)==156 and [w['id'] for w in windows]==['213D','122D','90D'],'72 plus84 original entries and three disjoint score windows')
    g.check(all(w['end_exclusive']<='2026-03-01T00:00:00+00:00' for w in windows),'Only prelocked dates')
    combined=dict(status='BOUND_D044_THREE_PREVIOUSLY_ACCEPTED_USDM_WINDOWS_NOT_ECONOMICS',source_files=files,windows=windows,
        funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,locked_consumed=False,
        native_market_certified=False,source_only=True,original_input_manifests=plan['sources'],
        original_547D_source_failure_preserved=True,independent_accounts_no_NAV_stitch=True)
    for name,digest in plan['source_hashes'].items():g.check(sha(ROOT/name)==digest,'Frozen metadata dependency '+name)
    manifest_sha,_=g.write(ROOT/plan['combined_output'],combined)
    value=dict(status='PASS_D044_EXISTING_ACCEPTED_SOURCE_ONLY_NO_REPEATED_QA',binding=binding,run_dir=str(run),run_binding_sha256=rb,
        source_only=True,funding_unit_certified=False,native_market_certified=False,source_files=156,source_roots=roots,
        original_input_manifests=plan['sources'],combined_manifest_path=plan['combined_output'],combined_manifest_sha256=manifest_sha,
        new_source_QA_or_payload_IO=False,old_accounts_replayed=False,orders_sent=0,models_fit=0,GPU=0,locked_consumed=False,
        local_non_git_hash_guard={LOCK:LOCK_SHA},created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    out_sha,_=g.write(ROOT/plan['output'],value);print(out_sha)
if __name__=='__main__':main()
