"""Preserve only completed original January63 accounts; no reruns or market calls."""
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path
import evaluate_requests63 as native
HERE=native.HERE;ARMS=('FRESH_GRU_FOLD20240101','STATIC50','CASH50');LABELS=dict(zip(ARMS,('FRESH_GRU','VOL50_CS50','CASH50_VOL25_CS25')))
read=lambda p:json.loads(p.read_bytes());sha=native.base.frozen.sha


def write_once(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==data,path
    else:path.write_bytes(data)


def checkpoint(state,public,arm):
    original=state/'prequential63-native'/arm;s=read(original/'account/summary.json');a=read(original/'INDEPENDENT_AUDIT.json');e=read(original/'EXECUTION.json');gate=read(original/'REQUEST_GATE.json');plan=read(HERE/'prequential63-native-plans'/(arm+'.json'))
    assert s['completed_minutes']==s['required_minutes']==90720 and s['terminal_cash_realized'] and s['terminal_not_forced_free_fill'] and s['liquidation_count']==0 and all(p['quantity']==0 for p in s['positions'].values())
    assert a['status'].startswith('PASS_') and a['actual_input_check']['status']=='PASS_ACTUAL_FILLS_CAPACITY_FEES_MARKS_AND_FUNDING' and a['actual_input_check']['funding_events']==945 and a['mapped_request_targets_exact']
    assert e['status']=='COMPLETE_CONDITIONAL_ACCOUNT' and e['request_manifest_sha256']==gate['manifest_sha256']==plan['request_manifest_sha256'] and e['original_engine_sha256']==plan['engine_sha256']
    assert all(gate[k]==plan['mapping_preflight'][k] for k in ('fractions_f64_sha256','budgets_f64_sha256','request_payload_sha256'))
    assert abs(s['net_PnL']-(s['gross_PnL_same_quantities']+s['funding_USDT']-s['fees_USDT']-s['execution_cost_USDT']))<1e-8
    for name,path in [('summary.json',original/'account/summary.json'),('INDEPENDENT_AUDIT.json',original/'INDEPENDENT_AUDIT.json'),('REQUEST_GATE.json',original/'REQUEST_GATE.json')]:write_once(public/arm/name,path.read_bytes())
    r=dict(status='COMPLETE_AND_INDEPENDENTLY_AUDITED',arm=arm,producer_policy=LABELS[arm],fresh_capital_USDT=10000,net_PnL_USDT=s['net_PnL'],price_PnL_USDT=s['gross_PnL_same_quantities'],funding_USDT=s['funding_USDT'],fees_USDT=s['fees_USDT'],execution_cost_USDT=s['execution_cost_USDT'],months=s['months'],minute_max_drawdown=s['minute_max_drawdown'],realized_exposure=s['realized_exposure'],maximum_actual_gross_weight=s['maximum_actual_gross_weight'],risk_reduction_signal_count=s['risk_reduction_signal_count'],liquidation_count=s['liquidation_count'],calendar=native.CALENDAR,terminal_paid_flat=True,audit_scope=a['actual_input_check'],maximum_NAV_error_USDT=a['maximum_NAV_error_USDT'],elapsed_seconds=e['elapsed_seconds'],peak_RSS_bytes=e['peak_RSS_bytes'],engine_SHA256=e['original_engine_sha256'],source_plan_commit=e['plan_commit'],request_manifest_SHA256=e['request_manifest_sha256'],new_wallets=1,fits=0,model_inference=0,provider_downloads=0)
    write_once(public/arm/'RESULT.json',(json.dumps(r,indent=2)+'\n').encode());return original,r


def package(state,public):
    pairs={arm:checkpoint(state,public,arm) for arm in ARMS};accounts={a:pairs[a][1] for a in ARMS};model=accounts[ARMS[0]]
    deltas={LABELS[c]:{k:model[k]-accounts[c][k] for k in ('net_PnL_USDT','price_PnL_USDT','funding_USDT','fees_USDT','execution_cost_USDT')} for c in ARMS[1:]}
    r=dict(status='PASS_THREE_COMPLETE_AUDITED_FROZEN_NATIVE63_ACCOUNTS',calendar=native.CALENDAR,accounts=accounts,model_minus_fixed_control=deltas,analytic_CASH=read(HERE/'prequential63-native-plans/CASH_ANALYTIC.json'),comparison_scope='SEPARATE_FRESH10000_SAME_TAPE_AND_FINANCIAL_CONTRACT;REALIZED_RISK_NOT_EQUALIZED;NO_STITCHING',training_provenance=read(HERE/'prequential63-native-plans/PRECHECK.json')['prefix_proof'],interpretation='Historical prequential project data, not pristine unseen. Fixed512 does not prove convergence. Native model and fixed controls have unequal realized exposure; no executable switching or OOS efficacy inferred.',new_native_wallets=3,model_fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0,historical_publication_and_account_filter_rules_certified=False)
    write_once(public/'RESULTS.json',(json.dumps(r,indent=2)+'\n').encode())
    root=state/'portable-prequential63-native';root.mkdir(exist_ok=False)
    for arm in ARMS:shutil.copytree(pairs[arm][0],root/'accounts'/arm)
    shutil.copytree(HERE/'prequential63-native-plans',root/'plans');shutil.copyfile(public/'RESULTS.json',root/'RESULTS.json');shutil.copyfile(public/'README.md',root/'README.md')
    for name in ('evaluate_requests61.py','evaluate_requests63.py','prequential63_producer.py','package_prequential63.py','verify_native61.py','native61.py','requirements.txt','requirements-native61.txt'):shutil.copyfile(HERE/name,root/name)
    for name in ('ADAPTER_CONTRACT.json','TAPE_INVENTORY.json','CANONICAL_CONTEXTS63.npz','MOMENTUM_SHORT_CONTEXTS63.npz'):p=root/'prequential63'/name;p.parent.mkdir(exist_ok=True);shutil.copyfile(HERE/'prequential63'/name,p)
    for name in ('modules/transformer_v3/isolated_audit.py','scripts/investment/audit_shared_direction.py'):p=root/'verification_helpers'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/'verification_helpers'/name,p)
    wrappers=state/'prequential63-native-wrappers'
    for name in ('producer/REQUESTS.npz','STATIC50_REQUESTS.npz','CASH50_REQUESTS.npz','TRAINING_CLOCKS.npz','PREFIX_PROOF.json'):p=root/'frozen-request-evidence'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(wrappers/name,p)
    members=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        raw=p.read_bytes();assert '__pycache__' not in p.parts and p.suffix!='.pt'
        if p.suffix in ('.json','.md','.py','.txt'):assert not re.search(rb'/(?:workspace|home/xflops|mnt/d)/|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY',raw),p
        members.append(dict(path=p.relative_to(root).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    manifest=dict(schema='THREE_FROZEN_NATIVE63_ORIGINAL_MEMBERS_V1',files=members,original_account_journals_edited=False,raw_market_archives_included=False,trained_weights_duplicated=False,private_runtime_inventories_included=False)
    raw=(json.dumps(manifest,indent=2)+'\n').encode();write_once(root/'RESULT_MEMBER_HASHES.json',raw);write_once(public/'RESULT_MEMBER_HASHES.json',raw)
    archive=state/'coin_prequential63_native_results_20261009.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    data=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(data),768*1024)):
        raw=data[start:start+768*1024];name=archive.name+f'.bytepart{i:03d}';write_once(public/'transport'/name,raw);parts.append(dict(path='transport/'+name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    artifact=dict(schema='THREE_FROZEN_NATIVE63_ORDERED_RESULT_PARTS_V1',filename=archive.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),part_max_bytes=768*1024,parts=parts,member_manifest_sha256=sha(root/'RESULT_MEMBER_HASHES.json'),original_journals_byte_identical=True,raw_market_and_trained_weights_duplicated=False)
    write_once(public/'ARTIFACT.json',(json.dumps(artifact,indent=2)+'\n').encode());print(json.dumps(dict(status='PASS_THREE_UNCHANGED_ACCOUNT_PACKAGE',bytes=len(data),sha256=artifact['sha256'],parts=len(parts),members=len(members))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--public',type=Path,required=True);a=p.parse_args();package(a.state,a.public)
