"""Checkpoint or preserve the two completed short-expansion request wallets.

Copies immutable completed journals; no account, model, fit or provider call.
"""
import argparse, hashlib, json, re, shutil, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ARMS=('EXP_GRU64_CASH_CONTROL','EXP_GRU64_CASH_MOM30_SHORT')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def write_once(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==data,path
    else:path.write_bytes(data)


def checkpoint(state,public,arm):
    assert arm in ARMS
    root=state/'temporal-short-native61'/arm;s=read(root/'account/summary.json');audit=read(root/'INDEPENDENT_AUDIT.json');gate=read(root/'REQUEST_GATE.json');execution=read(root/'EXECUTION.json')
    plan=read(HERE/'temporal-short-native61-plans'/(arm+'.json'))
    assert audit['status'].startswith('PASS_') and audit['mapped_request_targets_exact'] and s['terminal_cash_realized'] and s['completed_minutes']==87840 and s['liquidation_count']==0
    assert execution['status']=='COMPLETE_CONDITIONAL_ACCOUNT' and gate['manifest_sha256']==plan['request_manifest_sha256']==execution['request_manifest_sha256']
    assert gate['request_payload_sha256']==plan['public_export']['request_sha256']
    for field in ('fractions_f64_sha256','budgets_f64_sha256'):assert gate[field]==plan['mapping_preflight'][field]
    assert execution['original_engine_sha256']==plan['engine_sha256']=='318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585'
    result=dict(status='COMPLETE_AND_INDEPENDENTLY_AUDITED',arm=arm,fresh_capital_USDT=10000,net_PnL_USDT=s['net_PnL'],May_PnL_USDT=s['months'][0]['net_PnL'],June_PnL_USDT=s['months'][1]['net_PnL'],price_PnL_USDT=s['gross_PnL_same_quantities'],funding_USDT=s['funding_USDT'],fees_USDT=s['fees_USDT'],execution_cost_USDT=s['execution_cost_USDT'],months=s['months'],minute_max_drawdown=s['minute_max_drawdown'],realized_exposure=s['realized_exposure'],maximum_actual_gross_weight=s['maximum_actual_gross_weight'],maximum_actual_asset_weights=s['maximum_actual_asset_weights'],risk_reduction_signal_count=s['risk_reduction_signal_count'],normalized_total_turnover=s['normalized_total_turnover'],trade_legs=s['trade_legs'],long_short_marked_contribution=s['long_short_marked_contribution'],liquidations=0,terminal_paid_flat=True,completed_minutes=87840,original_engine_SHA256=plan['engine_sha256'],adapter_contract_SHA256=plan['adapter_contract_sha256'],plan_commit=execution['plan_commit'],public_export=plan['public_export'],short_target_provenance=plan['short_target_provenance'],producer_mapper_parity=plan['mapping_preflight']['producer_mapper_parity'],training_status=plan['training_status'],completed_expansion_updates=plan['completed_expansion_updates'],cumulative_base_Adam_step=plan['cumulative_base_Adam_step'],new_head_Adam_step=plan['new_head_Adam_step'],development_role='ALREADY_SEEN_MAY_JUNE_NOT_OOS',fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0)
    for name in ('summary.json','INDEPENDENT_AUDIT.json','REQUEST_GATE.json'):
        source=root/('account/summary.json' if name=='summary.json' else name);write_once(public/arm/name,source.read_bytes())
    write_once(public/arm/'RESULT.json',(json.dumps(result,indent=2)+'\n').encode())
    return root,result


def package(state,public):
    pairs={arm:checkpoint(state,public,arm) for arm in ARMS};control,short=(pairs[n][1] for n in ARMS)
    delta={k:short[k]-control[k] for k in ('net_PnL_USDT','May_PnL_USDT','June_PnL_USDT','price_PnL_USDT','funding_USDT','fees_USDT','execution_cost_USDT')}
    assert abs(delta['net_PnL_USDT']-(delta['price_PnL_USDT']+delta['funding_USDT']-delta['fees_USDT']-delta['execution_cost_USDT']))<1e-8
    controls={}
    for name in ('STATIC50','CASH50'):
        root=state/'results61'/name;s=read(root/'account/summary.json');a=read(root/'INDEPENDENT_AUDIT.json');assert a['status'].startswith('PASS_')
        controls[name]=dict(status='REUSED_COMPLETED_AUDITED_ACCOUNT_NO_RERUN',net_PnL_USDT=s['net_PnL'],months=s['months'],minute_max_drawdown=s['minute_max_drawdown'],realized_exposure=s['realized_exposure'],summary_SHA256=sha(root/'account/summary.json'),audit_SHA256=sha(root/'INDEPENDENT_AUDIT.json'),public_relative_path='../comparison61/ARTIFACT.json')
    parent=HERE/'temporal-v2-native61-cash-results/V2_GRU64_WITH_CASH/RESULT.json'
    import numpy as np
    import evaluate_requests61 as adapter
    contexts=adapter.contexts(state,True);mapper=adapter.frozen.modules(state).mapper;allocation={}
    for arm in ARMS:
        plan=read(HERE/'temporal-short-native61-plans'/(arm+'.json'));bundle=state/'temporal-short-exports'/plan['public_export']['commit']/arm/'MANIFEST.json'
        m,a=adapter.load_bundle(bundle,plan['request_manifest_sha256']);full,_=adapter.validate(m,a,contexts);targets,budgets=adapter.mapped(full,contexts,mapper)
        assert hashlib.sha256(targets.tobytes()).hexdigest()==plan['mapping_preflight']['fractions_f64_sha256'] and hashlib.sha256(budgets.tobytes()).hexdigest()==plan['mapping_preflight']['budgets_f64_sha256']
        allocation[arm]={}
        for label,mask in (('ALL',np.ones(61,bool)),('MAY',np.arange(61)<31),('JUNE',np.arange(61)>=31)):
            allocation[arm][label]=dict(request_mean=dict(zip(contexts['expert_order'],map(float,full[mask].mean(0)))),ramped_budget_mean=dict(zip(contexts['expert_order'],map(float,budgets[mask].mean(0)))),requested_short_maximum=float(full[mask,5].max()),ramped_short_maximum=float(budgets[mask,5].max()))
    result=dict(status='PASS_TWO_COMPLETE_AUDITED_SHORT_EXPANSION_NATIVE61_WALLETS',accounts={n:pairs[n][1] for n in ARMS},primary_short_minus_matched_control_USDT=delta,request_and_ramped_budget_allocation=allocation,allocation_scope='READ_ONLY_REMAPPING_OF_FROZEN_REQUESTS_EXACT_SAVED_TARGET_AND_PLAN_BUDGET_SHA256; EXPERT_SIMPLEX_WEIGHTS_NOT_LITERAL_NAV_ALLOCATION',reused_static_controls=controls,reused_parent_GRU_withCash=read(parent),primary_comparison='TWO_SEPARATE_FRESH_SHARED_WALLETS_SAME_TAPES_AND_CONTRACT; NO_STITCHING',interpretation='Seen development with capped unequal updates and unequal actual exposure. Independent-account differences are comparisons, not causal expansion effects or executable switching gains.',new_native_wallets=2,fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0,account_stitching=False,historical_publication_and_exchange_account_rules_certified=False)
    write_once(public/'RESULTS.json',(json.dumps(result,indent=2)+'\n').encode())
    root=state/'portable-short-expansion-native61';root.mkdir(exist_ok=False)
    for arm in ARMS:shutil.copytree(pairs[arm][0],root/'accounts'/arm)
    shutil.copyfile(public/'RESULTS.json',root/'RESULTS.json');shutil.copytree(HERE/'temporal-short-native61-plans',root/'plans')
    for name in ('prepare_short_expansion61.py','evaluate_requests61.py','package_short_expansion61.py','verify_native61.py','native61.py','EVALUATE_REQUESTS61_ADAPTER.json','requirements-native61.txt','requirements.txt'):
        shutil.copyfile(HERE/name,root/name)
    for name in ('modules/transformer_v3/isolated_audit.py','scripts/investment/audit_shared_direction.py'):
        target=root/'verification_helpers'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/'verification_helpers'/name,target)
    shutil.copyfile(public/'README.md',root/'README.md');members=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        b=p.read_bytes();assert '__pycache__' not in p.parts
        if p.suffix in ('.json','.md','.py','.txt'):
            assert not re.search(rb'/(?:workspace|home/xflops|mnt/d)/|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY',b),p
        members.append(dict(path=p.relative_to(root).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    manifest=dict(schema='TWO_SHORT_EXPANSION_NATIVE61_ORIGINAL_RESULT_MEMBERS_V1',files=members,original_account_journals_edited=False,private_runtime_inventory_included=False,raw_market_archives_included=False,model_weights_duplicated=False)
    write_once(root/'RESULT_MEMBER_HASHES.json',(json.dumps(manifest,indent=2)+'\n').encode());write_once(public/'RESULT_MEMBER_HASHES.json',(root/'RESULT_MEMBER_HASHES.json').read_bytes())
    archive=state/'coin_short_expansion_native61_results_20261009.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    data=archive.read_bytes();transport=public/'transport';transport.mkdir(exist_ok=False);parts=[]
    for i,start in enumerate(range(0,len(data),768*1024)):
        piece=data[start:start+768*1024];name=archive.name+f'.bytepart{i:03d}';write_once(transport/name,piece);parts.append(dict(path='transport/'+name,bytes=len(piece),sha256=hashlib.sha256(piece).hexdigest()))
    artifact=dict(schema='TWO_SHORT_EXPANSION_NATIVE61_ORDERED_RESULT_PARTS_V1',filename=archive.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),part_max_bytes=768*1024,parts=parts,member_manifest_sha256=sha(root/'RESULT_MEMBER_HASHES.json'),original_account_journals_byte_identical=True,market_archives_and_model_weights_duplicated=False)
    write_once(public/'ARTIFACT.json',(json.dumps(artifact,indent=2)+'\n').encode());print(json.dumps(dict(status='PASS_TWO_UNCHANGED_AUDITED_ACCOUNT_PACKAGE',members=len(members),bytes=len(data),sha256=artifact['sha256'],parts=len(parts),primary_short_minus_control=delta)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('checkpoint','package'));p.add_argument('--state',type=Path,required=True);p.add_argument('--public',type=Path,required=True);p.add_argument('--arm',choices=ARMS);a=p.parse_args()
    if a.command=='checkpoint':assert a.arm is not None;print(json.dumps(checkpoint(a.state,a.public,a.arm)[1]),flush=True)
    else:package(a.state,a.public)
