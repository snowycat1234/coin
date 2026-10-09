"""Preserve two audited frozen v2 request wallets; never execute accounts/fits."""
import argparse, hashlib, json, re, shutil, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ARMS=('V2_GRU64_NO_CASH','V2_LATEST_MLP_NO_CASH')


def package(state,public,cash=False):
    sha=lambda b:hashlib.sha256(b).hexdigest()
    arms=('V2_GRU64_WITH_CASH','V2_LATEST_MLP_WITH_CASH') if cash else ARMS
    plan_directory=HERE/('temporal-v2-native61-cash-plans' if cash else 'temporal-v2-native61-plans')
    root=state/('portable-v2-cash-native61' if cash else 'portable-v2-native61');root.mkdir(exist_ok=False)
    transport=public/'transport';transport.mkdir(exist_ok=False)
    records={}
    for arm in arms:
        source=state/'temporal-v2-native61'/arm
        audit=json.loads((source/'INDEPENDENT_AUDIT.json').read_text())
        s=json.loads((source/'account/summary.json').read_text())
        proxy=json.loads((source/'SAME_PATH_V2_PROXY.json').read_text())
        assert audit['status'].startswith('PASS_') and audit['mapped_request_targets_exact'] and s['terminal_cash_realized'] and s['completed_minutes']==87840
        shutil.copytree(source,root/'accounts'/arm)
        target=public/arm;target.mkdir(exist_ok=True)
        for n in ('summary.json','INDEPENDENT_AUDIT.json','REQUEST_GATE.json','SAME_PATH_V2_PROXY.json'):
            shutil.copyfile(source/('account/summary.json' if n=='summary.json' else n),target/n)
        execution=json.loads((source/'EXECUTION.json').read_text());provenance=execution['export_provenance']
        plan=json.loads((plan_directory/(arm+'.json')).read_text())
        assert plan['request_manifest_sha256']==execution['request_manifest_sha256']
        r=dict(status='COMPLETE_AND_AUDITED',arm=arm,fresh_capital_USDT=10000,
               net_PnL_USDT=s['net_PnL'],May_PnL_USDT=s['months'][0]['net_PnL'],June_PnL_USDT=s['months'][1]['net_PnL'],
               months=s['months'],minute_max_drawdown=s['minute_max_drawdown'],realized_exposure=s['realized_exposure'],
               maximum_actual_gross_weight=s['maximum_actual_gross_weight'],maximum_actual_asset_weights=s['maximum_actual_asset_weights'],
               risk_reduction_signal_count=s['risk_reduction_signal_count'],liquidations=s['liquidation_count'],terminal_paid_flat=True,
               original_engine_SHA256='318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585',
               execution_plan_commit=execution['plan_commit'],request_export_commit=plan['public_export']['commit'],
               same_path_v2_proxy=proxy,training_status='CAPPED_NOT_CONVERGED',additional_v2_updates=provenance['completed_v2_updates'],
               cumulative_Adam_updates=provenance['cumulative_Adam_step'],development_role='ORIGINAL_SEEN_MAY_JUNE_NOT_OOS',
               adapter_contract_SHA256=plan['adapter_contract_sha256'],
               legacy_export_compatibility=plan.get('legacy_export_compatibility'),
               adapter_changes=['REVIEWED_ELIGIBILITY_RELEASE_CHECK; EXACT_UNCHANGED_TARGET_AND_BUDGET_BYTES'] if cash else [])
        (target/'RESULT.json').write_text(json.dumps(r,indent=2)+'\n');records[arm]=r
    controls={}
    for arm in ('STATIC50','CASH50'):
        p=state/'results61'/arm;s=json.loads((p/'account/summary.json').read_text());a=json.loads((p/'INDEPENDENT_AUDIT.json').read_text())
        assert a['status'].startswith('PASS_') and s['terminal_cash_realized']
        controls[arm]=dict(status='REUSED_ORIGINAL_AUDITED_ACCOUNT_NO_RERUN',net_PnL_USDT=s['net_PnL'],months=s['months'],
                           minute_max_drawdown=s['minute_max_drawdown'],realized_exposure=s['realized_exposure'],
                           summary_SHA256=sha((p/'account/summary.json').read_bytes()),audit_SHA256=sha((p/'INDEPENDENT_AUDIT.json').read_bytes()),
                           public_transport_relative_path='../comparison61/ARTIFACT.json')
    reused_models={}
    if cash:
        for arm in ARMS:
            p=HERE/'temporal-v2-native61-results'/arm/'RESULT.json';reused_models[arm]=json.loads(p.read_text())
    result=dict(status='PASS_TWO_COMPLETE_AUDITED_REAL_FROZEN_V2_NATIVE61_ACCOUNTS',accounts=records,reused_controls=controls,reused_completed_no_cash_models=reused_models,
                conclusion='Full seen-development results with unequal realized risk; neither convergence nor OOS alpha is established. Cash-arm evaluation reuses completed no-cash accounts without rerunning them.' if cash else 'Both frozen no-cash v2 arms lost more than both reused static controls in this seen development wallet. Risk is unequal; neither convergence nor OOS alpha is established.',
                research_only=True,fits=0,new_native_wallets=2,provider_downloads=0,static_wallet_reruns=0,
                historical_exchange_account_rules_certified=False,account_stitching=False)
    (public/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    shutil.copyfile(public/'RESULTS.json',root/'RESULTS.json')
    for n in ('verify_native61.py','native61.py','v2_same_path_diagnostic.py','EVALUATE_REQUESTS61_ADAPTER.json','requirements-native61.txt'):
        shutil.copyfile(HERE/n,root/n)
    for n in ('modules/transformer_v3/isolated_audit.py','scripts/investment/audit_shared_direction.py'):
        dest=root/'verification_helpers'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/'verification_helpers'/n,dest)
    shutil.copytree(plan_directory,root/'plans')
    deps=state/'v2-proxy-sources'
    for n in ('H1_VALIDATE.npz','prototype.py'):
        dest=root/'proxy-inputs'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(deps/n,dest)
    bindings=json.loads((deps/'RECOVERY.json').read_text())
    bindings['reference_source_SHA256']=sha((HERE/'v2_same_path_diagnostic.py').read_bytes())
    bindings['export_commit']=plan['public_export']['commit']
    bindings['export_root']='research/temporal-surrogate-resume-v2-20261009/native61-requests'
    bindings['original_objective_source_relative_path']=arms[0]+'/OBJECTIVE_SOURCE.py'
    bindings['original_objective_source_SHA256']='c438a85a1853f7b8cef02dede194dd3c905d93f74bbb2882b5ae0fd8d50ad040'
    (root/'PROXY_RECOVERY.json').write_text(json.dumps(bindings,indent=2)+'\n')
    shutil.copyfile(root/'PROXY_RECOVERY.json',public/'PROXY_RECOVERY.json')
    for n in ('training_packet.py','exact.py'):
        expected=json.loads((state/'temporal-v2-exports'/plan['public_export']['commit']/arms[0]/'RUN.json').read_text())['specification']['sources']['modules/temporal_two_expert/'+n]
        assert sha((deps/n).read_bytes())==expected
    shutil.copyfile(HERE/('V2_NATIVE61_CASH_RESULTS_README.md' if cash else 'V2_NATIVE61_RESULTS_README.md'),root/'README.md');shutil.copyfile(root/'README.md',public/'README.md')
    files=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        b=p.read_bytes();assert '__pycache__' not in p.parts
        if p.suffix in ('.json','.md','.py','.txt'):
            assert not re.search(rb'/(?:workspace|mnt/d|home/xflops)/[A-Za-z0-9_.-]',b),p
            assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)',b),p
        files.append(dict(path=p.relative_to(root).as_posix(),bytes=len(b),sha256=sha(b)))
    manifest=dict(schema='TWO_FROZEN_V2_NATIVE61_RESULT_MEMBERS_V1',files=files,original_account_journals_edited=False,
                  private_runtime_inventory_included=False,raw_market_archives_included=False,model_weights_duplicated=False)
    (root/'RESULT_MEMBER_HASHES.json').write_text(json.dumps(manifest,indent=2)+'\n');shutil.copyfile(root/'RESULT_MEMBER_HASHES.json',public/'RESULT_MEMBER_HASHES.json')
    archive=state/('coin_frozen_v2_cash_native61_results_20261009.zip' if cash else 'coin_frozen_v2_no_cash_native61_results_20261009.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    b=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(b),768*1024)):
        data=b[start:start+768*1024];n=archive.name+f'.bytepart{i:03d}';(transport/n).write_bytes(data)
        parts.append(dict(path='transport/'+n,bytes=len(data),sha256=sha(data)))
    artifact=dict(schema='TWO_FROZEN_V2_NATIVE61_ORDERED_RESULT_PARTS_V1',filename=archive.name,bytes=len(b),sha256=sha(b),part_max_bytes=768*1024,parts=parts,
                  member_manifest_sha256=sha((root/'RESULT_MEMBER_HASHES.json').read_bytes()),account_journals_byte_identical=True,market_and_model_downloads_duplicated=False)
    (public/'ARTIFACT.json').write_text(json.dumps(artifact,indent=2)+'\n')
    print(json.dumps(dict(status='PASS_TWO_AUDITED_UNCHANGED_ACCOUNT_PACKAGE',members=len(files),bytes=len(b),sha256=artifact['sha256'],parts=len(parts))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--public',type=Path,required=True);p.add_argument('--cash',action='store_true');a=p.parse_args();package(a.state,a.public,a.cash)
