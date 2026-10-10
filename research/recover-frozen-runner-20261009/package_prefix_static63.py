"""Preserve four original baseline accounts and compare retained controls; no account advances."""
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path
import prefix_static_native63 as runner
from package_prequential63 import write_once
PUBLIC=runner.PUBLIC;HERE=runner.HERE;read=runner.read;sha=runner.sha;encoded=runner.encoded


def checkpoint(state,fold):
    output=state/'prefix-static63-native'/fold;folder=PUBLIC/fold;summary=read(output/'account/summary.json');audit=read(output/'INDEPENDENT_AUDIT.json');execution=read(output/'EXECUTION.json');plan=read(folder/'EXECUTION_PLAN.json');recovery=read(output/'RECOVERY_AUDIT.json')
    assert summary['completed_minutes']==summary['required_minutes']==90720 and summary['terminal_cash_realized'] and summary['terminal_not_forced_free_fill'] and all(p['quantity']==0 for p in summary['positions'].values())
    assert audit['status'].startswith('PASS_') and audit['actual_input_check']['status']=='PASS_ACTUAL_FILLS_CAPACITY_FEES_MARKS_AND_FUNDING' and audit['actual_input_check']['funding_events']==945 and audit['mapped_request_targets_exact'] and audit['terminal_request_onehot_preserved']
    assert execution['status']=='COMPLETE_CONDITIONAL_ACCOUNT' and execution['original_engine_sha256']==runner.ENGINE_SHA and execution['request_manifest_sha256']==plan['request_manifest_sha256'] and recovery['minute_journal_bit_exact'] and recovery['account_snapshot_exact']
    assert abs(summary['net_PnL']-(summary['gross_PnL_same_quantities']+summary['funding_USDT']-summary['fees_USDT']-summary['execution_cost_USDT']))<1e-8
    choice=read(folder/'PRECHECK.json')['choice'];result=dict(status='COMPLETE_AND_INDEPENDENTLY_AUDITED',fold=fold,selected_expert=choice['selected_expert'],E6_slot=choice['E6_slot'],mature_prefix_labels=choice['mature_labels'],choice_commit=runner.CHOICE,export_commit=runner.EXPORT,source_manifest_SHA256=runner.FOLDS[fold][0],source_plan_commit=execution['plan_commit'],request_manifest_SHA256=execution['request_manifest_sha256'],engine_SHA256=runner.ENGINE_SHA,calendar=plan['calendar'],fresh_capital_USDT=10000,net_PnL_USDT=summary['net_PnL'],price_PnL_USDT=summary['gross_PnL_same_quantities'],funding_USDT=summary['funding_USDT'],fees_USDT=summary['fees_USDT'],execution_cost_USDT=summary['execution_cost_USDT'],spread_USDT=summary['spread_cost_USDT'],slippage_USDT=summary['slippage_cost_USDT'],months=summary['months'],minute_max_drawdown=summary['minute_max_drawdown'],realized_exposure=summary['realized_exposure'],maximum_actual_gross_weight=summary['maximum_actual_gross_weight'],maximum_actual_asset_weights=summary['maximum_actual_asset_weights'],risk_reduction_signal_count=summary['risk_reduction_signal_count'],liquidation_count=summary['liquidation_count'],trade_legs=summary['trade_legs'],normalized_total_turnover=summary['normalized_total_turnover'],terminal_paid_flat=True,terminal_request_onehot_preserved=True,maximum_NAV_error_USDT=audit['maximum_NAV_error_USDT'],actual_input_audit=audit['actual_input_check'],elapsed_seconds=execution['elapsed_seconds'],peak_RSS_bytes=execution['peak_RSS_bytes'],full_original_snapshot_recovery=recovery,new_wallets=1,completed_wallet_reruns=0,fits=0,model_inference=0,provider_downloads=0)
    results=folder/'results'
    for name,p in [('summary.json',output/'account/summary.json'),('INDEPENDENT_AUDIT.json',output/'INDEPENDENT_AUDIT.json'),('REQUEST_GATE.json',output/'REQUEST_GATE.json'),('RECOVERY_AUDIT.json',output/'RECOVERY_AUDIT.json')]:write_once(results/name,p.read_bytes())
    write_once(results/'RESULT.json',encoded(result));return output,result


def package(state,fold):
    original,result=checkpoint(state,fold);results=PUBLIC/fold/'results';root=state/'portable-prefix-static63'/fold;root.mkdir(parents=True,exist_ok=False)
    for p in sorted(original.rglob('*')):
        if not p.is_file() or 'recovery' in p.relative_to(original).parts:continue
        target=root/'accounts'/fold/p.relative_to(original);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    pointer=read(original/'recovery/CHECKPOINT.json')
    for name in ['CHECKPOINT.json',pointer['snapshot']['path'],*[v['path'] for v in pointer['minute_chunks']]]:
        target=root/'accounts'/fold/'recovery'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original/'recovery'/name,target)
    repo=root/'repo';helper=repo/HERE.relative_to(runner.REPO);helper.mkdir(parents=True,exist_ok=True)
    for name in ('prefix_static_native63.py','durable_native_checkpoint.py','package_prefix_static63.py','verify_prefix_static63_public.py','evaluate_requests61.py','evaluate_requests63.py','native61.py','package_prequential63.py','verify_native61.py','requirements-native61.txt','requirements.txt','EVALUATE_REQUESTS61_ADAPTER.json','NATIVE61_PLAN.json'):
        shutil.copyfile(HERE/name,helper/name)
    for n,h in read(PUBLIC/fold/'ADAPTER_CONTRACT.json')['source_sha256'].items():
        p=runner.REPO/n;assert sha(p)==h;target=repo/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    for name in ('modules/transformer_v3/isolated_audit.py','scripts/investment/audit_shared_direction.py'):
        target=helper/'verification_helpers'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/'verification_helpers'/name,target)
    shutil.copytree(PUBLIC/fold,helper/'prefix-static63'/fold,ignore=shutil.ignore_patterns('results'));shutil.copyfile(PUBLIC/'FROZEN_SELECTIONS.json',helper/'prefix-static63/FROZEN_SELECTIONS.json')
    for p in (runner.FINANCIAL,HERE/runner.FOLDS[fold][1]/'ADAPTER_CONTRACT.json'):
        target=repo/p.relative_to(runner.REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    write_once(root/'RESULT.json',encoded(result));write_once(root/'RECOVERY_MANIFEST.json',encoded(dict(schema='PREFIX_STATIC63_PORTABLE_ACCOUNT_RECOVERY_V1',fold=fold,plan_commit=result['source_plan_commit'],required_repository='snowycat1234/coin',repository_source_scope='Archive binds original financial sources and thin helpers; transitive source dependencies remain recoverable from the pinned public repository commit.',dependency_recipe='repo/'+str(HERE.relative_to(runner.REPO))+'/requirements-native61.txt',account='accounts/'+fold,checkpoint='accounts/'+fold+'/recovery/CHECKPOINT.json',source_export_commit=runner.EXPORT,choice_commit=runner.CHOICE,retained_market_contract='repo/'+str((PUBLIC/fold/'ADAPTER_CONTRACT.json').relative_to(runner.REPO)),market_inputs='REUSE_BOUND_RETAINED_STATE;NO_PROVIDER_DOWNLOADS;NO_RAW_MARKET_DUPLICATION',resume_method='NativeDailySimulator.from_snapshot with BybitIsolatedAccount; original complete account must not advance',original_engine_SHA256=runner.ENGINE_SHA,completed_minutes=90720,paid_terminal_flat=True,private_runtime_inventory_included=False)))
    members=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        raw=p.read_bytes();assert '__pycache__' not in p.parts and p.suffix!='.pt'
        if p.suffix in ('.json','.md','.py','.txt'):assert not re.search(rb'/(?:workspace|home/xflops|mnt/d)/|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY',raw),p
        members.append(dict(path=p.relative_to(root).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    manifest=dict(schema='PREFIX_STATIC63_ORIGINAL_JOURNAL_AND_CHECKPOINT_MEMBERS_V1',fold=fold,files=members,original_journals_edited=False,private_runtime_inventory_included=False,raw_market_or_model_weights_included=False)
    write_once(root/'RESULT_MEMBER_HASHES.json',encoded(manifest));write_once(results/'RESULT_MEMBER_HASHES.json',encoded(manifest));archive=state/('coin_prefix_static_native_'+fold+'_20261010.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    raw=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(raw),768*1024)):
        chunk=raw[start:start+768*1024];name='transport/'+archive.name+f'.bytepart{i:03d}';write_once(results/name,chunk);parts.append(dict(path=name,bytes=len(chunk),sha256=hashlib.sha256(chunk).hexdigest()))
    artifact=dict(schema='PREFIX_STATIC63_ORDERED_ORIGINAL_RESULT_AND_CHECKPOINT_PARTS_V1',filename=archive.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),parts=parts,part_max_bytes=768*1024,member_manifest_sha256=sha(root/'RESULT_MEMBER_HASHES.json'),original_journals_byte_identical=True,durable_final_snapshot_included=True)
    write_once(results/'ARTIFACT.json',encoded(artifact));print(json.dumps(dict(status='PASS_UNCHANGED_BASELINE_JOURNAL_AND_RECOVERY_PACKAGE',fold=fold,net_PnL=result['net_PnL_USDT'],bytes=len(raw),sha256=artifact['sha256'],parts=len(parts),members=len(members))),flush=True)


def comparison():
    prior_path=HERE/'prequential-four-folds/COMPARISON.json';assert sha(prior_path)=='0a8dbfa0eaf704c637fe8740b72b262cb007fe14c95fb7ebe449d928991bcd12';prior=read(prior_path);folds={};rows=['| Fold | Frozen baseline | Baseline net USDT | GRU | Static50 | Cash50 | Baseline DD | Mean gross |','|---|---|---:|---:|---:|---:|---:|---:|']
    for fold in runner.FOLDS:
        result=read(PUBLIC/fold/'results/RESULT.json');controls=prior['folds'][fold]['accounts'];remote=read(PUBLIC/fold/'results/PUBLIC_READBACK.json');assert remote['status'].startswith('PASS_') and remote['completed_wallet_reruns']==0
        diffs={arm:result['net_PnL_USDT']-r['net_PnL_USDT'] for arm,r in controls.items()};folds[fold]=dict(baseline=result,retained_accounts=controls,baseline_minus_retained_net_PnL_USDT=diffs,retained_result_SHA256=prior['folds'][fold]['result_SHA256'],retained_archive_commit=prior['folds'][fold]['archive_commit'],new_result_SHA256=sha(PUBLIC/fold/'results/RESULT.json'),new_archive_SHA256=read(PUBLIC/fold/'results/ARTIFACT.json')['sha256'],public_readback_SHA256=sha(PUBLIC/fold/'results/PUBLIC_READBACK.json'),public_recovery_status=remote['status'],calendar=result['calendar'],realized_risk_not_equalized=True)
        rows.append(f"| {fold[5:]} | {result['selected_expert']} | {result['net_PnL_USDT']:.2f} | {controls['FRESH_GRU']['net_PnL_USDT']:.2f} | {controls['VOL50_CS50']['net_PnL_USDT']:.2f} | {controls['CASH50_VOL25_CS25']['net_PnL_USDT']:.2f} | {result['minute_max_drawdown']:.3%} | {result['realized_exposure']['minute_mean_gross_weight']:.3%} |")
    document=dict(status='PASS_FOUR_FROZEN_PREFIX_STATIC_NATIVE63_ACCOUNTS_AND_RETAINED_CONTROL_COMPARISONS',folds=folds,choice_commit=runner.CHOICE,export_commit=runner.EXPORT,engine_SHA256=runner.ENGINE_SHA,retained_comparison_path=prior_path.relative_to(runner.REPO).as_posix(),retained_comparison_SHA256=sha(prior_path),retained_original_screen=prior.get('original_failed_screen',prior.get('original_screen','See unchanged retained COMPARISON.json')),interpretation='Four separate fresh10000 accounts on repeatedly seen development history. Frozen prefix choice, no training or re-selection. Unequal realized gross/net risk; no stitched account, pristine OOS, APR, convergence or executable switching claim. Historical publication and venue/account filter rules remain uncertified.',new_wallets=4,completed_control_wallets_reused=12,completed_wallet_reruns=0,fits=0,model_inference=0,provider_downloads=0)
    write_once(PUBLIC/'COMPARISON.json',encoded(document));text='Four source-frozen prefix-static choices through the original guard-OFF native minute engine. Each wallet is separate fresh10k, 63days/90720minutes/945 actual signed funding events, with charged terminal-flat closure.\n\n'+'\n'.join(rows)+'\n\nCOMPARISON.json retains full monthly PnL, price/funding/fees/execution, drawdown and realized gross/net exposure for all16 separate accounts. Twelve completed comparison accounts were reused without rerunning. Each new archive includes byte-identical original journals and a recoverable final engine checkpoint, verified by public readback and actual-input audits.\n\nChoices were SHORT/VOL/VOL/VOL, committed before forward evaluation. Requests remain one-hot through the terminal day; execution target forcing belongs to the unchanged engine. No training, fitting, provider downloads or alternative choice search. These are repeatedly seen development periods with unequal realized risk, not pristine OOS or a stitched/APR result. Original failed prequential screen remains unchanged. Historical publication and exchange/account rules remain uncertified.\n'
    write_once(PUBLIC/'RESULTS.md',text.encode());print(json.dumps(dict(status=document['status'],net_PnL={f:r['baseline']['net_PnL_USDT'] for f,r in folds.items()},new_wallets=4,completed_wallet_reruns=0)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('package','checkpoint','comparison'));p.add_argument('--state',type=Path);p.add_argument('--fold',choices=tuple(runner.FOLDS));a=p.parse_args()
    if a.command=='comparison':comparison()
    elif a.command=='checkpoint':print(json.dumps(checkpoint(a.state,a.fold)[1]),flush=True)
    else:package(a.state,a.fold)
