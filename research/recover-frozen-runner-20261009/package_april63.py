"""Read-only April account preservation and four separate fold comparisons."""
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path
import april_native63 as april
from package_prequential63 import write_once
HERE=april.HERE;PUBLIC=april.PUBLIC;RESULTS=PUBLIC/'results';read=april.read;sha=april.sha


def checkpoint(state,arm):
    original=state/'april63-native'/arm;s=read(original/'account/summary.json');a=read(original/'INDEPENDENT_AUDIT.json');e=read(original/'EXECUTION.json');gate=read(original/'REQUEST_GATE.json');plan=read(PUBLIC/(arm+'.json'))
    assert s['completed_minutes']==s['required_minutes']==90720 and s['terminal_cash_realized'] and s['terminal_not_forced_free_fill'] and s['liquidation_count']==0 and all(p['quantity']==0 for p in s['positions'].values())
    assert a['status'].startswith('PASS_') and a['actual_input_check']['status']=='PASS_ACTUAL_FILLS_CAPACITY_FEES_MARKS_AND_FUNDING' and a['actual_input_check']['funding_events']==945 and a['mapped_request_targets_exact']
    assert e['status']=='COMPLETE_CONDITIONAL_ACCOUNT' and e['request_manifest_sha256']==gate['manifest_sha256']==plan['request_manifest_sha256'] and e['original_engine_sha256']==plan['engine_sha256']
    assert all(gate[k]==plan['mapping_preflight'][k] for k in ('fractions_f64_sha256','budgets_f64_sha256','request_payload_sha256'))
    assert abs(s['net_PnL']-(s['gross_PnL_same_quantities']+s['funding_USDT']-s['fees_USDT']-s['execution_cost_USDT']))<1e-8
    for name,p in [('summary.json',original/'account/summary.json'),('INDEPENDENT_AUDIT.json',original/'INDEPENDENT_AUDIT.json'),('REQUEST_GATE.json',original/'REQUEST_GATE.json')]:write_once(RESULTS/arm/name,p.read_bytes())
    r=dict(status='COMPLETE_AND_INDEPENDENTLY_AUDITED',fold='FOLD_20240401',arm=arm,producer_policy=april.LABELS[arm],fresh_capital_USDT=10000,net_PnL_USDT=s['net_PnL'],price_PnL_USDT=s['gross_PnL_same_quantities'],funding_USDT=s['funding_USDT'],fees_USDT=s['fees_USDT'],execution_cost_USDT=s['execution_cost_USDT'],spread_USDT=s['spread_cost_USDT'],slippage_USDT=s['slippage_cost_USDT'],months=s['months'],minute_max_drawdown=s['minute_max_drawdown'],realized_exposure=s['realized_exposure'],maximum_actual_gross_weight=s['maximum_actual_gross_weight'],maximum_actual_asset_weights=s['maximum_actual_asset_weights'],risk_reduction_signal_count=s['risk_reduction_signal_count'],liquidation_count=s['liquidation_count'],trade_legs=s['trade_legs'],normalized_total_turnover=s['normalized_total_turnover'],calendar=april.CAL,terminal_paid_flat=True,audit_scope=a['actual_input_check'],maximum_NAV_error_USDT=a['maximum_NAV_error_USDT'],elapsed_seconds=e['elapsed_seconds'],peak_RSS_bytes=e['peak_RSS_bytes'],engine_SHA256=e['original_engine_sha256'],source_plan_commit=e['plan_commit'],request_manifest_SHA256=e['request_manifest_sha256'],new_wallets=1,model_fits=0,model_inference=0,provider_downloads=0)
    write_once(RESULTS/arm/'RESULT.json',(json.dumps(r,indent=2)+'\n').encode());return original,r


def package(state):
    pairs={arm:checkpoint(state,arm) for arm in april.LABELS};accounts={arm:pairs[arm][1] for arm in pairs};model=accounts[april.MODEL]
    deltas={april.LABELS[c]:{k:model[k]-accounts[c][k] for k in ('net_PnL_USDT','price_PnL_USDT','funding_USDT','fees_USDT','execution_cost_USDT')} for c in ('STATIC50','CASH50')}
    _,producer,wrapper=april.locations(state);proxy=read(producer/'RESULT.json');bridges={}
    for arm,label in april.LABELS.items():
        p=proxy['policies'][label];n=accounts[arm];bridges[arm]=dict(proxy_net_PnL_USDT=p['net_PnL'],native_net_PnL_USDT=n['net_PnL_USDT'],native_minus_proxy_net_PnL_USDT=n['net_PnL_USDT']-p['net_PnL'])
    result=dict(status='PASS_THREE_COMPLETE_AUDITED_FROZEN_NATIVE63_ACCOUNTS',fold='FOLD_20240401',calendar=april.CAL,accounts=accounts,model_minus_fixed_control=deltas,proxy_native_bridge=bridges,training_provenance=read(PUBLIC/'PRECHECK.json')['prefix_proof'],comparison_scope='SEPARATE_FRESH10000_SAME_TAPE_AND_FINANCIAL_CONTRACT;REALIZED_RISK_NOT_EQUALIZED;NO_STITCHING',interpretation='Historical prequential project data. Fixed512 does not prove convergence. Account risk/exposure differs. Retain the original failed screen; no pristine OOS, equal-risk alpha or executable switching claim.',new_native_wallets=3,model_fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0,historical_publication_and_account_filter_rules_certified=False)
    write_once(RESULTS/'RESULTS.json',(json.dumps(result,indent=2)+'\n').encode())
    rows=['| Policy | Net USDT | Apr | May | Jun 1–2 | Minute DD | Mean gross | Mean signed net |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for arm,r in accounts.items():
        m=r['months'];x=r['realized_exposure'];rows.append(f"| {r['producer_policy']} | {r['net_PnL_USDT']:.6f} | {m[0]['net_PnL']:.6f} | {m[1]['net_PnL']:.6f} | {m[2]['net_PnL']:.6f} | {r['minute_max_drawdown']:.6%} | {x['minute_mean_gross_weight']:.6%} | {x['minute_mean_net_signed_weight']:.6%} |")
    text='Three original guard-OFF fresh10k April1–June3exclusive native accounts.\n\n'+'\n'.join(rows)+'\n\nEach90720minutes/945actual signed funding events, paid terminal flat and independently audited with actual fills, costs, previous-minute quote capacity and strictly prior funding marks. RESULTS.json retains monthly results, full costs/risk/exposure and native/proxy differences. No model fit, inference, provider download or old wallet rerun. Actual risk differs; original failed prequential screen remains. Archive contains byte-identical original journals, request/prefix evidence, source/contract and dependency recipe; no market or model-weight duplication. Historical publication/venue/account rules remain uncertified.\n'
    write_once(RESULTS/'README.md',text.encode());root=state/'portable-april63-native';root.mkdir(exist_ok=False)
    for arm in accounts:shutil.copytree(pairs[arm][0],root/'accounts'/arm)
    shutil.copytree(PUBLIC,root/'plans',ignore=shutil.ignore_patterns('results'));shutil.copytree(april.CONTRACT.parent,root/'april63')
    for name in ('RESULTS.json','README.md'):shutil.copyfile(RESULTS/name,root/name)
    for name in ('april_native63.py','prepare_april63.py','package_april63.py','evaluate_requests61.py','evaluate_requests63.py','prequential63_producer.py','package_prequential63.py','verify_native61.py','native61.py','requirements.txt','requirements-native61.txt'):shutil.copyfile(HERE/name,root/name)
    for name in ('modules/transformer_v3/isolated_audit.py','scripts/investment/audit_shared_direction.py'):p=root/'verification_helpers'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/'verification_helpers'/name,p)
    for name in ('producer/REQUESTS.npz','producer/CURRENT_CONTEXT63.npz','producer/PAIRED_PATHS.npz','producer/RUN.json','producer/TERMINAL.json','producer/SCALER.npz','READY.json','STATIC50_REQUESTS.npz','CASH50_REQUESTS.npz','TRAINING_CLOCKS.npz','PREFIX_PROOF.json'):
        p=root/'frozen-request-evidence'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(wrapper/name,p)
    for arm in accounts:shutil.copyfile(wrapper/('MANIFEST_'+arm+'.json'),root/'plans'/('MANIFEST_'+arm+'.json'))
    members=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        raw=p.read_bytes();assert '__pycache__' not in p.parts and p.suffix!='.pt'
        if p.suffix in ('.json','.md','.py','.txt'):assert not re.search(rb'/(?:workspace|home/xflops|mnt/d)/|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY',raw),p
        members.append(dict(path=p.relative_to(root).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    manifest=dict(schema='THREE_FROZEN_NATIVE63_ORIGINAL_MEMBERS_V1',fold='FOLD_20240401',files=members,original_account_journals_edited=False,raw_market_archives_included=False,trained_weights_duplicated=False,private_runtime_inventories_included=False);raw=(json.dumps(manifest,indent=2)+'\n').encode();write_once(root/'RESULT_MEMBER_HASHES.json',raw);write_once(RESULTS/'RESULT_MEMBER_HASHES.json',raw)
    archive=state/'coin_prequential_native_FOLD_20240401_20261010.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    data=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(data),768*1024)):
        raw=data[start:start+768*1024];name='transport/'+archive.name+f'.bytepart{i:03d}';write_once(RESULTS/name,raw);parts.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    artifact=dict(schema='THREE_FROZEN_NATIVE63_ORDERED_RESULT_PARTS_V1',filename=archive.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),part_max_bytes=768*1024,parts=parts,member_manifest_sha256=sha(root/'RESULT_MEMBER_HASHES.json'),original_journals_byte_identical=True,raw_market_and_trained_weights_duplicated=False);write_once(RESULTS/'ARTIFACT.json',(json.dumps(artifact,indent=2)+'\n').encode())
    print(json.dumps(dict(status='PASS_THREE_UNCHANGED_APRIL_ACCOUNT_PACKAGE',bytes=len(data),sha256=artifact['sha256'],parts=len(parts),members=len(members),accounts={a:r['net_PnL_USDT'] for a,r in accounts.items()})),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--checkpoint',choices=tuple(april.LABELS));a=p.parse_args()
    if a.checkpoint:print(json.dumps(checkpoint(a.state,a.checkpoint)[1]),flush=True)
    else:package(a.state)
