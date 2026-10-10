"""Preserve audited Q4 accounts and full recovery state without another rollout."""
import argparse,hashlib,json,re,shutil,zipfile
from datetime import datetime,UTC
from pathlib import Path
import q4_native92 as run
read=run.read;sha=run.sha;encoded=run.encoded;write_once=run.write_once;PUBLIC=run.PUBLIC


def months(directory):
    import polars as pl
    minute=pl.read_parquet(directory/'account/minute.parquet');previous=dict(nav=10000.,cumulative_fees=0.,cumulative_execution_costs=0.,cumulative_funding=0.);result=[]
    for month,frame in minute.with_columns(pl.from_epoch('close_us',time_unit='us').dt.offset_by('-1us').dt.strftime('%Y-%m').alias('month')).partition_by('month',as_dict=True).items():
        row=frame.row(-1,named=True);net=row['nav']-previous['nav'];fees=row['cumulative_fees']-previous['cumulative_fees'];cost=row['cumulative_execution_costs']-previous['cumulative_execution_costs'];fund=row['cumulative_funding']-previous['cumulative_funding']
        result.append(dict(month=month[0],minute_observations=frame.height,last_close_us=row['close_us'],net_PnL_USDT=net,price_PnL_USDT=net+fees+cost-fund,fees_USDT=fees,execution_cost_USDT=cost,funding_USDT=fund,ending_NAV=row['nav'],terminal_tail_included=row['close_us']==run.END));previous=row
    summary=read(directory/'account/summary.json')
    assert abs(sum(r['net_PnL_USDT'] for r in result)-summary['net_PnL'])<1e-8 and sum(r['minute_observations'] for r in result)==131046
    return result


def checkpoint(state,arm):
    original=state/'q4-native92'/arm;s=read(original/'account/summary.json');a=read(original/'INDEPENDENT_AUDIT.json');e=read(original/'EXECUTION.json');recovery=read(original/'RECOVERY_AUDIT.json');gate=read(original/'REQUEST_GATE.json');plan=read(PUBLIC/(arm+'.json'))
    assert e['status']==s['completion']=='COMPLETE_CONDITIONAL_ACCOUNT' and e['original_engine_sha256']==run.ENGINE_SHA and s['terminal_cash_realized'] and s['terminal_not_forced_free_fill'] and all(p['quantity']==0 for p in s['positions'].values())
    assert gate==plan['mapping_preflight'] and a['status'].startswith('PASS_') and a['minutes']==s['completed_minutes']==s['required_minutes']==131046 and a['actual_input_check']['funding_events']==1370 and recovery['account_snapshot_exact'] and recovery['minute_journal_bit_exact']
    assert abs(s['net_PnL']-(s['gross_PnL_same_quantities']+s['funding_USDT']-s['fees_USDT']-s['execution_cost_USDT']))<1e-8
    result=dict(status='COMPLETE_AND_INDEPENDENTLY_AUDITED',arm=arm,producer_commit=run.PRODUCER,data_commit=run.DATA,engine_SHA256=run.ENGINE_SHA,source_plan_commit=e['plan_commit'],request_SHA256=gate['request_sha256'],adapter_contract_SHA256=plan['adapter_contract_sha256'],model_identity=read(PUBLIC/'PRECHECK.json')['model_identity'] if arm=='SELECTED_FULL773_256' else None,checkpoint_identity=read(PUBLIC/'PRECHECK.json')['checkpoint_sha256'] if arm=='SELECTED_FULL773_256' else None,execution_calendar=run.EXECUTION_CAL,fresh_capital_USDT=10000,net_PnL_USDT=s['net_PnL'],price_PnL_USDT=s['gross_PnL_same_quantities'],funding_USDT=s['funding_USDT'],fees_USDT=s['fees_USDT'],execution_cost_USDT=s['execution_cost_USDT'],spread_USDT=s['spread_cost_USDT'],slippage_USDT=s['slippage_cost_USDT'],minute_max_drawdown=s['minute_max_drawdown'],realized_exposure=s['realized_exposure'],maximum_actual_gross_weight=s['maximum_actual_gross_weight'],maximum_actual_asset_weights=s['maximum_actual_asset_weights'],risk_reduction_signal_count=s['risk_reduction_signal_count'],liquidation_count=s['liquidation_count'],trade_legs=s['trade_legs'],normalized_total_turnover=s['normalized_total_turnover'],terminal=a['terminal'],full_minute_window_months=months(original),original_monthly_table_scope=s['monthly_table_scope'],maximum_NAV_error_USDT=a['maximum_NAV_error_USDT'],actual_input_audit=a['actual_input_check'],elapsed_seconds=e['elapsed_seconds'],peak_RSS_bytes=e['peak_RSS_bytes'],full_original_snapshot_recovery=recovery,new_wallets=1,completed_wallet_reruns=0,fits=0,model_inference=0,provider_downloads=0)
    public=PUBLIC/'results'/arm
    for name in ('INDEPENDENT_AUDIT.json','REQUEST_GATE.json','RECOVERY_AUDIT.json'):write_once(public/name,(original/name).read_bytes())
    write_once(public/'summary.json',(original/'account/summary.json').read_bytes());write_once(public/'RESULT.json',encoded(result));return original,result


def package(state,arm):
    original,result=checkpoint(state,arm);public=PUBLIC/'results'/arm;root=state/'portable-q4-native92'/arm;root.mkdir(parents=True,exist_ok=False)
    for p in sorted(original.rglob('*')):
        if not p.is_file() or 'recovery' in p.relative_to(original).parts:continue
        target=root/'accounts'/arm/p.relative_to(original);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    pointer=read(original/'recovery/CHECKPOINT.json')
    for name in ['CHECKPOINT.json',pointer['snapshot']['path'],*[v['path'] for v in pointer['minute_chunks']]]:
        target=root/'accounts'/arm/'recovery'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original/'recovery'/name,target)
    repo=root/'repo';helper=repo/run.HERE.relative_to(run.REPO);helper.mkdir(parents=True,exist_ok=True)
    for name in ('q4_native92.py','verify_q4_native92.py','package_q4_native92.py','verify_q4_native92_public.py','prefix_static_native63.py','evaluate_requests63.py','evaluate_requests61.py','native61.py','package_prequential63.py','requirements.txt','requirements-native61.txt','EVALUATE_REQUESTS61_ADAPTER.json','NATIVE61_PLAN.json'):
        shutil.copyfile(run.HERE/name,helper/name)
    for n,h in read(PUBLIC/'ADAPTER_CONTRACT.json')['source_sha256'].items():
        p=run.REPO/n;assert sha(p)==h;target=repo/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    for name in ('modules/transformer_v3/isolated_audit.py','scripts/investment/audit_shared_direction.py'):
        target=helper/'verification_helpers'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(run.HERE/'verification_helpers'/name,target)
    shutil.copytree(PUBLIC,helper/'q4-native92',ignore=shutil.ignore_patterns('results','COMPARISON.json','RESULTS.md','COMPLETION.json'))
    target=repo/run.reused.FINANCIAL.relative_to(run.REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(run.reused.FINANCIAL,target)
    write_once(root/'RESULT.json',encoded(result));write_once(root/'RECOVERY_MANIFEST.json',encoded(dict(schema='Q4_NATIVE92_PORTABLE_ORIGINAL_ACCOUNT_V1',arm=arm,required_repository='snowycat1234/coin',plan_commit=result['source_plan_commit'],account='accounts/'+arm,checkpoint='accounts/'+arm+'/recovery/CHECKPOINT.json',dependency_recipe='repo/'+str(run.HERE.relative_to(run.REPO))+'/requirements-native61.txt',retained_market_contract='repo/'+str((PUBLIC/'ADAPTER_CONTRACT.json').relative_to(run.REPO)),market_inputs='BOUND_RETAINED_STATE_OR_PINNED_PUBLIC_PARTS;NO_PROVIDER_DOWNLOADS',restore='ORIGINAL_NATIVE_DAILY_SIMULATOR_FROM_SNAPSHOT_WITH_BYBIT_ISOLATED_ACCOUNT;COMPLETED_ACCOUNT_MUST_NOT_ADVANCE',completed_minutes=131046,original_engine_SHA256=run.ENGINE_SHA,private_runtime_inventory_included=False)))
    members=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        raw=p.read_bytes();assert '__pycache__' not in p.parts and p.suffix!='.pt'
        if p.suffix in ('.json','.md','.py','.txt'):assert not re.search(rb'/(?:workspace|home/xflops|mnt/d)/|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY',raw),p
        members.append(dict(path=p.relative_to(root).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    manifest=dict(schema='Q4_NATIVE92_ORIGINAL_ACCOUNT_MEMBER_HASHES_V1',files=members,original_account_journals_edited=False,raw_market_or_model_weights_duplicated=False,private_runtime_inventories_included=False)
    raw=encoded(manifest);write_once(root/'RESULT_MEMBER_HASHES.json',raw);write_once(public/'RESULT_MEMBER_HASHES.json',raw);archive=state/('coin_q4_native92_'+arm+'_20261010.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    data=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(data),768*1024)):
        raw=data[start:start+768*1024];name=archive.name+f'.bytepart{i:03d}';write_once(public/'transport'/name,raw);parts.append(dict(path='transport/'+name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    artifact=dict(schema='Q4_NATIVE92_ORDERED_PUBLIC_ACCOUNT_PARTS_V1',filename=archive.name,bytes=len(data),sha256=sha(archive),part_max_bytes=768*1024,parts=parts,member_manifest_sha256=sha(root/'RESULT_MEMBER_HASHES.json'),original_journals_byte_identical=True,raw_market_and_weights_duplicated=False)
    write_once(public/'ARTIFACT.json',encoded(artifact));print(json.dumps(dict(status='PASS_ORIGINAL_Q4_ACCOUNT_PACKAGE',arm=arm,bytes=len(data),sha256=artifact['sha256'],parts=len(parts),members=len(members))),flush=True)


def comparison():
    accounts={a:read(PUBLIC/'results'/a/'RESULT.json') for a in run.ARMS};model=accounts['SELECTED_FULL773_256'];score=read(PUBLIC/'producer/RESULT.json')
    result=dict(status='PASS_FOUR_COMPLETE_SOURCE_FROZEN_NATIVE_Q4_ACCOUNTS_STUDY_CLOSED',execution_calendar=run.EXECUTION_CAL,accounts=accounts,model_minus_fixed_control={c:{k:model[k]-accounts[c][k] for k in ('net_PnL_USDT','price_PnL_USDT','funding_USDT','fees_USDT','execution_cost_USDT')} for c in run.ARMS if c!='SELECTED_FULL773_256'},producer_once_score_reference=score,comparison_scope='FOUR_SEPARATE_FRESH10000_SAME_ACTUAL_TAPE_CONTRACT_AND_PARTIAL_TERMINAL;REALIZED_RISK_NOT_EQUALIZED;NO_ACCOUNT_STITCHING',data_role='PROJECT_SEEN_HISTORICAL_Q4;UNTOUCHED_BY_THIS_TUNING_UNTIL_THE_FROZEN_ONCE_SCORE;NOT_PRISTINE_UNSEEN',terminal_contract=run.terminal_contract(),study='COMPLETED_AT_LEAST600DAY_FIXED_SMALL_TUNING_MODULE;NO_FURTHER_RECIPES_REFITS_RESELECTION_OR_Q4_TUNING',model_fits=0,model_inference=0,new_native_wallets=4,completed_wallet_reruns=0,provider_downloads=0,historical_publication_and_account_rules_certified=False,APR_claimed=False,deployable_efficacy_claimed=False)
    write_once(PUBLIC/'COMPARISON.json',encoded(result));text='# Frozen Q4 native validation\n\nExactly four source-frozen fresh10,000USDT accounts; 92 decisions, 91 held intervals, then six original terminal minutes on December31. No refit, inference, reselection, provider download or completed-wallet rerun.\n\n| Account | Net USDT | Price USDT | Funding | Fees | Execution | Minute DD | Mean gross |\n|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for a,r in accounts.items():text+=f"| {a} | {r['net_PnL_USDT']:.2f} | {r['price_PnL_USDT']:.2f} | {r['funding_USDT']:.2f} | {r['fees_USDT']:.2f} | {r['execution_cost_USDT']:.2f} | {r['minute_max_drawdown']:.2%} | {r['realized_exposure']['minute_mean_gross_weight']:.2%} |\n"
    text+='\nAll accounts paid terminal-flat and passed independent financial, actual-input and full original checkpoint recovery audits. The producer assumes complete epsilon-time daily fills; native results retain actual delayed/partial fills, capacity, lot, costs, funding ownership and final-close timing. No exact fill parity is claimed. Full-minute monthly attribution includes the terminal tail; the untouched original summary reports complete UTC-day endpoints only.\n\nQ4 is project-seen historical data, untouched by this tuning until its frozen once-score. These are unequal-risk conditional cross-venue accounts; historical publication, contract and account rules remain uncertified. No pristine-OOS, APR or deployment conclusion follows. This closes the fixed tuning module; no further recipes or retuning. See COMPARISON.json and each results account for exact identities, audits, transport parts and public recovery receipts.\n'
    write_once(PUBLIC/'RESULTS.md',text.encode());print(json.dumps(dict(status=result['status'],net_PnL={a:r['net_PnL_USDT'] for a,r in accounts.items()})),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('package','comparison'));p.add_argument('--state',type=Path);p.add_argument('--arm',choices=tuple(run.ARMS));a=p.parse_args()
    if a.command=='comparison':comparison()
    else:package(a.state,a.arm)
