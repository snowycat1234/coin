"""Checkpoint or preserve a pair of completed frozen E6 request wallets.

Copies immutable completed journals; no account, model, fit or provider call.
"""
import argparse, hashlib, json, re, shutil, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ARMS=('EXP_GRU64_CASH_CONTROL','EXP_GRU64_CASH_MOM30_SHORT')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def profile_paths(profile):
    if profile=='expert-input':return (('EXP_GRU64_EXPERT_INPUT_CONTROL','EXP_GRU64_EXPERT_INPUT_ACTIVE'),'temporal-expert-input-native61','temporal-expert-input-native61-plans','temporal-expert-input-exports','portable-expert-input-native61','coin_expert_input_native61_results_20261009.zip','completed_input_ablation_updates')
    if profile=='weighting512':return (('EXP_GRU64_WEIGHT_DATE','EXP_GRU64_WEIGHT_MIXED'),'temporal-weighting512-native61','temporal-weighting512-native61-plans','temporal-weighting512-exports','portable-weighting512-native61','coin_weighting512_native61_results_20261009.zip','completed_weighting_updates')
    return (ARMS,'temporal-short-native61','temporal-short-native61-plans','temporal-short-exports','portable-short-expansion-native61','coin_short_expansion_native61_results_20261009.zip','completed_expansion_updates')


def write_once(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==data,path
    else:path.write_bytes(data)


def checkpoint(state,public,arm,profile='short-expansion'):
    arms,state_root,plans,_,_,_,updates=profile_paths(profile);assert arm in arms
    root=state/state_root/arm;s=read(root/'account/summary.json');audit=read(root/'INDEPENDENT_AUDIT.json');gate=read(root/'REQUEST_GATE.json');execution=read(root/'EXECUTION.json')
    plan=read(HERE/plans/(arm+'.json'))
    assert audit['status'].startswith('PASS_') and audit['mapped_request_targets_exact'] and s['terminal_cash_realized'] and s['completed_minutes']==87840 and s['liquidation_count']==0
    assert execution['status']=='COMPLETE_CONDITIONAL_ACCOUNT' and gate['manifest_sha256']==plan['request_manifest_sha256']==execution['request_manifest_sha256']
    assert gate['request_payload_sha256']==plan['public_export']['request_sha256']
    for field in ('fractions_f64_sha256','budgets_f64_sha256'):assert gate[field]==plan['mapping_preflight'][field]
    assert execution['original_engine_sha256']==plan['engine_sha256']=='318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585'
    result=dict(status='COMPLETE_AND_INDEPENDENTLY_AUDITED',arm=arm,fresh_capital_USDT=10000,net_PnL_USDT=s['net_PnL'],May_PnL_USDT=s['months'][0]['net_PnL'],June_PnL_USDT=s['months'][1]['net_PnL'],price_PnL_USDT=s['gross_PnL_same_quantities'],funding_USDT=s['funding_USDT'],fees_USDT=s['fees_USDT'],execution_cost_USDT=s['execution_cost_USDT'],months=s['months'],minute_max_drawdown=s['minute_max_drawdown'],realized_exposure=s['realized_exposure'],maximum_actual_gross_weight=s['maximum_actual_gross_weight'],maximum_actual_asset_weights=s['maximum_actual_asset_weights'],risk_reduction_signal_count=s['risk_reduction_signal_count'],normalized_total_turnover=s['normalized_total_turnover'],trade_legs=s['trade_legs'],long_short_marked_contribution=s['long_short_marked_contribution'],liquidations=0,terminal_paid_flat=True,completed_minutes=87840,original_engine_SHA256=plan['engine_sha256'],adapter_contract_SHA256=plan['adapter_contract_sha256'],plan_commit=execution['plan_commit'],public_export=plan['public_export'],short_target_provenance=plan['short_target_provenance'],producer_mapper_parity=plan['mapping_preflight']['producer_mapper_parity'],training_status=plan['training_status'],**{updates:plan[updates]},cumulative_base_Adam_step=plan['cumulative_base_Adam_step'],new_head_Adam_step=plan['new_head_Adam_step'],development_role='ALREADY_SEEN_MAY_JUNE_NOT_OOS',fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0)
    if profile in ('expert-input','weighting512'):result.update(input_enabled=plan['input_enabled'],current_expert_input_check=plan['current_expert_input_check'],source_declared_parameters_each=plan['source_declared_parameters_each'])
    if profile=='weighting512':result['matched_weighting512_contract']=plan['matched_weighting512_contract']
    for name in ('summary.json','INDEPENDENT_AUDIT.json','REQUEST_GATE.json'):
        source=root/('account/summary.json' if name=='summary.json' else name);write_once(public/arm/name,source.read_bytes())
    write_once(public/arm/'RESULT.json',(json.dumps(result,indent=2)+'\n').encode())
    return root,result


def package(state,public,profile='short-expansion'):
    arms,state_root,plans,exports,portable,filename,_=profile_paths(profile)
    pairs={arm:checkpoint(state,public,arm,profile) for arm in arms};control,short=(pairs[n][1] for n in arms)
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
    for arm in arms:
        plan=read(HERE/plans/(arm+'.json'));bundle=state/exports/plan['public_export']['commit']/arm/'MANIFEST.json'
        m,a=adapter.load_bundle(bundle,plan['request_manifest_sha256']);full,_=adapter.validate(m,a,contexts);targets,budgets=adapter.mapped(full,contexts,mapper)
        assert hashlib.sha256(targets.tobytes()).hexdigest()==plan['mapping_preflight']['fractions_f64_sha256'] and hashlib.sha256(budgets.tobytes()).hexdigest()==plan['mapping_preflight']['budgets_f64_sha256']
        from pyarrow.parquet import read_table
        minute=read_table(pairs[arm][0]/'account/minute_nav_inventory.parquet',columns=['close_us','nav','gross_weight','net_signed_weight'])
        assert np.array_equal(minute['close_us'].to_numpy(),np.arange(adapter.frozen.START+60000000,adapter.frozen.END+1,60000000))
        nav=minute['nav'].to_numpy();gross=minute['gross_weight'].to_numpy();net=minute['net_signed_weight'].to_numpy()
        allocation[arm]={}
        for label,mask in (('ALL',np.ones(61,bool)),('MAY',np.arange(61)<31),('JUNE',np.arange(61)>=31)):
            allocation[arm][label]=dict(request_mean=dict(zip(contexts['expert_order'],map(float,full[mask].mean(0)))),ramped_budget_mean=dict(zip(contexts['expert_order'],map(float,budgets[mask].mean(0)))),requested_short_maximum=float(full[mask,5].max()),ramped_short_maximum=float(budgets[mask,5].max()),requested_CS_gt_VOL_dates=int((full[mask,4]>full[mask,1]).sum()),ramped_CS_gt_VOL_dates=int((budgets[mask,4]>budgets[mask,1]).sum()))
            minute_mask=np.repeat(mask,1440);start=int(np.flatnonzero(minute_mask)[0]);path=np.r_[nav[start-1] if start else 10000.,nav[minute_mask]]
            allocation[arm][label]['observed_minute_exposure_and_drawdown']=dict(mean_gross=float(gross[minute_mask].mean()),maximum_gross=float(gross[minute_mask].max()),mean_net_signed=float(net[minute_mask].mean()),drawdown_from_period_start_NAV=float((1-path/np.maximum.accumulate(path)).max()),net_PnL_USDT=float(path[-1]-path[0]))
    primary_key='primary_mixed_minus_date_USDT' if profile=='weighting512' else ('primary_active_minus_matched_control_USDT' if profile=='expert-input' else 'primary_short_minus_matched_control_USDT')
    interpretation=('Seen development pair with identical initialization, exactly512 updates each, and only episode-loss weighting changed. Actual exposure differs. One matched pair establishes an observed training-recipe comparison, not OOS efficacy, convergence, or executable switching gain.' if profile=='weighting512' else 'Seen development with capped unequal updates and unequal actual exposure. Independent-account differences are comparisons, not isolated causal effects or executable switching gains.')
    result=dict(status='PASS_TWO_COMPLETE_AUDITED_FROZEN_E6_NATIVE61_WALLETS',profile=profile,accounts={n:pairs[n][1] for n in arms},**{primary_key:delta},request_and_ramped_budget_allocation=allocation,allocation_scope='READ_ONLY_REMAPPING_OF_FROZEN_REQUESTS_EXACT_SAVED_TARGET_AND_PLAN_BUDGET_SHA256; EXPERT_SIMPLEX_WEIGHTS_NOT_LITERAL_NAV_ALLOCATION',reused_static_controls=controls,reused_parent_GRU_withCash=read(parent),primary_comparison='TWO_SEPARATE_FRESH_SHARED_WALLETS_SAME_TAPES_AND_CONTRACT; NO_STITCHING',interpretation=interpretation,new_native_wallets=2,fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0,account_stitching=False,historical_publication_and_exchange_account_rules_certified=False)
    if profile=='weighting512':
        result['matched_training_contract']={arm:pairs[arm][1]['matched_weighting512_contract'] for arm in arms}
        result['observed_native_PnL_difference_from_reused_fixed_controls_USDT']={arm:{name:pairs[arm][1]['net_PnL_USDT']-c['net_PnL_USDT'] for name,c in controls.items()} for arm in arms}
    write_once(public/'RESULTS.json',(json.dumps(result,indent=2)+'\n').encode())
    root=state/portable;root.mkdir(exist_ok=False)
    for arm in arms:shutil.copytree(pairs[arm][0],root/'accounts'/arm)
    shutil.copyfile(public/'RESULTS.json',root/'RESULTS.json');shutil.copytree(HERE/plans,root/'plans')
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
    manifest=dict(schema='TWO_FROZEN_E6_NATIVE61_ORIGINAL_RESULT_MEMBERS_V1',profile=profile,files=members,original_account_journals_edited=False,private_runtime_inventory_included=False,raw_market_archives_included=False,model_weights_duplicated=False)
    write_once(root/'RESULT_MEMBER_HASHES.json',(json.dumps(manifest,indent=2)+'\n').encode());write_once(public/'RESULT_MEMBER_HASHES.json',(root/'RESULT_MEMBER_HASHES.json').read_bytes())
    archive=state/filename
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    data=archive.read_bytes();transport=public/'transport';transport.mkdir(exist_ok=False);parts=[]
    for i,start in enumerate(range(0,len(data),768*1024)):
        piece=data[start:start+768*1024];name=archive.name+f'.bytepart{i:03d}';write_once(transport/name,piece);parts.append(dict(path='transport/'+name,bytes=len(piece),sha256=hashlib.sha256(piece).hexdigest()))
    artifact=dict(schema='TWO_FROZEN_E6_NATIVE61_ORDERED_RESULT_PARTS_V1',profile=profile,filename=archive.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),part_max_bytes=768*1024,parts=parts,member_manifest_sha256=sha(root/'RESULT_MEMBER_HASHES.json'),original_account_journals_byte_identical=True,market_archives_and_model_weights_duplicated=False)
    write_once(public/'ARTIFACT.json',(json.dumps(artifact,indent=2)+'\n').encode());print(json.dumps(dict(status='PASS_TWO_UNCHANGED_AUDITED_ACCOUNT_PACKAGE',members=len(members),bytes=len(data),sha256=artifact['sha256'],parts=len(parts),**{primary_key:delta})),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('checkpoint','package'));p.add_argument('--state',type=Path,required=True);p.add_argument('--public',type=Path,required=True);p.add_argument('--arm');p.add_argument('--profile',choices=('short-expansion','expert-input','weighting512'),default='short-expansion');a=p.parse_args()
    if a.command=='checkpoint':assert a.arm is not None;print(json.dumps(checkpoint(a.state,a.public,a.arm,a.profile)[1]),flush=True)
    else:package(a.state,a.public,a.profile)
