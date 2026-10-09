"""Read-only fresh512 versus retained warm native journals, then public preservation."""
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path
import fresh61
from package_prequential63 import write_once
base=fresh61.base;HERE=base.HERE;PUBLIC=fresh61.PUBLIC;read=fresh61.read;sha=fresh61.sha;ARM=fresh61.ARM;WARM='EXP_GRU64_WEIGHT_DATE'


def allocations(state,arm,original,bundle,manifest_sha,gate):
    import numpy as np
    from pyarrow.parquet import read_table
    c=base.contexts(state,True);m,a=base.load_bundle(bundle/'MANIFEST.json',manifest_sha);full,_=base.validate(m,a,c);f,b=base.mapped(full,c,base.frozen.modules(state).mapper)
    assert hashlib.sha256(f.tobytes()).hexdigest()==gate['fractions_f64_sha256'] and hashlib.sha256(b.tobytes()).hexdigest()==gate['budgets_f64_sha256']
    assert np.array_equal(read_table(original/'account/targets.parquet')['target_weight'].to_numpy().reshape(61,5),f)
    minute=read_table(original/'account/minute_nav_inventory.parquet',columns=['close_us','nav','gross_weight','net_signed_weight']);tt=minute['close_us'].to_numpy();nav=minute['nav'].to_numpy();gross=minute['gross_weight'].to_numpy();net=minute['net_signed_weight'].to_numpy()
    assert np.array_equal(tt,np.arange(base.frozen.START+base.frozen.MINUTE,base.frozen.END+1,base.frozen.MINUTE));report={}
    for label,mask in [('ALL',np.ones(61,bool)),('MAY',np.arange(61)<31),('JUNE',np.arange(61)>=31)]:
        minutes=np.repeat(mask,1440);start=int(np.flatnonzero(minutes)[0]);path=np.r_[nav[start-1] if start else 10000.,nav[minutes]]
        report[label]=dict(request_mean=dict(zip(c['expert_order'],map(float,full[mask].mean(0)))),native_applied_ramped_budget_mean=dict(zip(c['expert_order'],map(float,b[mask].mean(0)))),requested_short_maximum=float(full[mask,5].max()),ramped_short_maximum=float(b[mask,5].max()),observed_minute_exposure_and_drawdown=dict(mean_gross=float(gross[minutes].mean()),maximum_gross=float(gross[minutes].max()),mean_net_signed=float(net[minutes].mean()),minimum_net_signed=float(net[minutes].min()),maximum_net_signed=float(net[minutes].max()),drawdown_from_period_start_NAV=float((1-path/np.maximum.accumulate(path)).max()),net_PnL_USDT=float(path[-1]-path[0])))
    return report


def package(state):
    original=state/'temporal-fresh-init-native61'/ARM;warm=state/'temporal-weighting512-native61'/WARM;bundle,evidence=fresh61.locations(state);public=PUBLIC/'results';plan=read(PUBLIC/(ARM+'.json'))
    s=read(original/'account/summary.json');a=read(original/'INDEPENDENT_AUDIT.json');e=read(original/'EXECUTION.json');gate=read(original/'REQUEST_GATE.json');ws=read(warm/'account/summary.json');wa=read(warm/'INDEPENDENT_AUDIT.json');wg=read(warm/'REQUEST_GATE.json');we=read(warm/'EXECUTION.json')
    assert a['status'].startswith('PASS_') and a['mapped_request_targets_exact'] and a['actual_input_check']['status']=='PASS_ACTUAL_FILLS_CAPACITY_FEES_MARKS_AND_FUNDING' and a['actual_input_check']['funding_events']==915
    assert s['completed_minutes']==s['required_minutes']==87840 and s['terminal_cash_realized'] and s['terminal_not_forced_free_fill'] and all(v['quantity']==0 for v in s['positions'].values()) and s['liquidation_count']==0 and e['status']=='COMPLETE_CONDITIONAL_ACCOUNT'
    assert e['request_manifest_sha256']==gate['manifest_sha256']==plan['request_manifest_sha256']==fresh61.MANIFEST_SHA and e['original_engine_sha256']==plan['engine_sha256']
    assert wa['status'].startswith('PASS_') and sha(warm/'account/summary.json')==plan['reused_warm_native']['summary_SHA256'] and sha(warm/'INDEPENDENT_AUDIT.json')==plan['reused_warm_native']['audit_SHA256'] and sha(warm/'EXECUTION.json')==plan['reused_warm_native']['execution_SHA256']
    summaries={ARM:s,WARM:ws};accounts={}
    for name,x in summaries.items():
        accounts[name]=dict(status='NEW_COMPLETE_AUDITED_ONCE' if name==ARM else 'REUSED_COMPLETE_AUDITED_NO_RERUN',fresh_capital_USDT=10000,net_PnL_USDT=x['net_PnL'],May_PnL_USDT=x['months'][0]['net_PnL'],June_PnL_USDT=x['months'][1]['net_PnL'],price_PnL_USDT=x['gross_PnL_same_quantities'],funding_USDT=x['funding_USDT'],fees_USDT=x['fees_USDT'],execution_cost_USDT=x['execution_cost_USDT'],spread_USDT=x['spread_cost_USDT'],slippage_USDT=x['slippage_cost_USDT'],minute_max_drawdown=x['minute_max_drawdown'],realized_exposure=x['realized_exposure'],maximum_actual_asset_weights=x['maximum_actual_asset_weights'],months=x['months'],liquidations=x['liquidation_count'],risk_reduction_signal_count=x['risk_reduction_signal_count'],terminal_paid_flat=x['terminal_cash_realized'],trade_legs=x['trade_legs'],normalized_total_turnover=x['normalized_total_turnover'])
        assert abs(x['net_PnL']-(x['gross_PnL_same_quantities']+x['funding_USDT']-x['fees_USDT']-x['execution_cost_USDT']))<1e-8
    metrics=('net_PnL_USDT','May_PnL_USDT','June_PnL_USDT','price_PnL_USDT','funding_USDT','fees_USDT','execution_cost_USDT');delta={k:accounts[ARM][k]-accounts[WARM][k] for k in metrics};assert abs(delta['net_PnL_USDT']-(delta['price_PnL_USDT']+delta['funding_USDT']-delta['fees_USDT']-delta['execution_cost_USDT']))<1e-8
    proxy=read(evidence/'RESULT.json');proxies={ARM:proxy['fresh'],WARM:proxy['warm_comparator']['seen_May_June_charged_daily_proxy']};bridges={}
    for name,p in proxies.items():
        native=accounts[name];values=dict(net_PnL_USDT=p['net_PnL'],funding_USDT=p['funding'],fees_USDT=p['fees'],execution_cost_USDT=p['spread']+p['slippage']+p.get('charged_reduction_cost',0));values['price_PnL_USDT']=values['net_PnL_USDT']-values['funding_USDT']+values['fees_USDT']+values['execution_cost_USDT'];d={k:native[k]-values[k] for k in values};assert abs(d['net_PnL_USDT']-(d['price_PnL_USDT']+d['funding_USDT']-d['fees_USDT']-d['execution_cost_USDT']))<1e-8
        bridges[name]=dict(proxy=values,native={k:native[k] for k in values},native_minus_proxy=d,scope='SAME_FROZEN_REQUESTS_AND_MAPPED_TARGETS;DAILY_PROXY_VERSUS_ACTUAL_MINUTE_FILLS_MARKS_FUNDING_CAPACITY_AND_COSTS;PRICE_RESIDUAL_NOT_CAUSALLY_SPLIT')
    warm_bundle=state/'temporal-weighting512-exports'/fresh61.WARM_COMMIT/WARM
    allocation={ARM:allocations(state,ARM,original,bundle,fresh61.MANIFEST_SHA,gate),WARM:allocations(state,WARM,warm,warm_bundle,wg['manifest_sha256'],wg)}
    result=dict(status='PASS_ONE_FRESH512_NATIVE61_AND_REUSED_WARM_DATE_COMPARISON',accounts=accounts,fresh_minus_warm_native_USDT=delta,request_and_native_ramped_budget_allocation=allocation,allocation_scope='EXPERT_SIMPLEX_WEIGHTS_NOT_LITERAL_NAV_CASH_OR_SHORT_HOLDINGS;EXACT_GATE_BUDGET_SHA_AND_SAVED_TARGETS;ORIGINAL_FINAL_DAY_EXECUTION_TARGET_ZERO',cost_bridge=bridges,proxy_fresh_minus_warm_USDT=proxy['PnL_difference_vs_exact_warm'],native_minus_proxy_comparison_difference_USDT=delta['net_PnL_USDT']-proxy['PnL_difference_vs_exact_warm'],seen_gate_statistics=dict(fresh=proxy['fresh']['seen_gate_statistics'],warm=proxy['warm_seen_gate_statistics'],source='ORIGINAL_FROZEN_RESULT_NO_INFERENCE_HERE'),provenance=plan,reused_warm_journal_hashes=plan['reused_warm_native'],maximum_independent_NAV_error_USDT=a['maximum_NAV_error_USDT'],native_elapsed_seconds=e['elapsed_seconds'],peak_RSS_bytes=e['peak_RSS_bytes'],new_native_wallets=1,fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0,account_stitching=False,interpretation='Fresh regime reduced observed native loss, while realized exposure and optimizer lifetime differ; still negative on seen MayJune. Not equal-risk causal initialization proof, optimizer convergence, pristine OOS, seed robustness or executable switching.',historical_publication_and_account_rules_certified=False)
    write_once(public/'RESULTS.json',(json.dumps(result,indent=2)+'\n').encode())
    for name,p in [('summary.json',original/'account/summary.json'),('INDEPENDENT_AUDIT.json',original/'INDEPENDENT_AUDIT.json'),('REQUEST_GATE.json',original/'REQUEST_GATE.json')]:write_once(public/ARM/name,p.read_bytes())
    write_once(public/ARM/'RESULT.json',(json.dumps(accounts[ARM],indent=2)+'\n').encode())
    text=f"One fresh512 native account completed: {s['net_PnL']:+.6f}USDT, May {s['months'][0]['net_PnL']:+.6f}, June {s['months'][1]['net_PnL']:+.6f}. Retained warm-date {ws['net_PnL']:+.6f}; fresh-minus-warm {delta['net_PnL_USDT']:+.6f}. Fresh minute drawdown {s['minute_max_drawdown']:.6%}, mean gross {s['realized_exposure']['minute_mean_gross_weight']:.6%}; warm {ws['minute_max_drawdown']:.6%}, {ws['realized_exposure']['minute_mean_gross_weight']:.6%}.\n\nExactly one new fresh10k, original guardOFF native61 account,87840minutes/915actual signed funding events, full costs, paid terminal-flat closure; zero liqs. Warm/static accounts retained without rerunning. RESULTS.json includes monthly gross/net/DD, requests versus native-applied eligibility-released/ramped expert weights, cost decomposition and proxy/native bridge. Expert weights are not literal NAV allocation. Actual risk and optimizer lifetime differ; still a negative seen-development result, not pristine OOS, equal-risk causal efficacy, convergence or switching proof.\n\nArchive preserves original fresh journals unchanged, source, dependency recipe, frozen requests and public provenance hashes. Warm journals are referenced by their original public archive and exact summary/audit/execution hashes; no duplicate warm wallets, model weights, raw data or private runtime inventories.\n"
    write_once(public/'README.md',text.encode());root=state/'portable-fresh-init-native61';root.mkdir(exist_ok=False);shutil.copytree(original,root/'accounts'/ARM)
    for name in ('fresh61.py','package_fresh61.py','evaluate_requests61.py','verify_native61.py','native61.py','requirements.txt','requirements-native61.txt'):shutil.copyfile(HERE/name,root/name)
    shutil.copytree(PUBLIC,root/'plans',ignore=shutil.ignore_patterns('results'))
    for name in ('RESULTS.json','README.md'):shutil.copyfile(public/name,root/name)
    for name in ('modules/transformer_v3/isolated_audit.py','scripts/investment/audit_shared_direction.py'):
        p=root/'verification_helpers'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/'verification_helpers'/name,p)
    for name in ('REQUESTS.npz','CURRENT_EXPERT_INPUTS61.npz','RUN.json','TERMINAL.json','TRAINING_PLAN.json','SCALER.npz'):p=root/'frozen-evidence'/name;p.parent.mkdir(exist_ok=True);shutil.copyfile(bundle/name,p)
    members=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        raw=p.read_bytes();assert '__pycache__' not in p.parts and p.suffix!='.pt'
        if p.suffix in ('.py','.md','.json','.txt'):assert not re.search(rb'/(?:workspace|home/xflops|mnt/d)/|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY',raw),p
        members.append(dict(path=p.relative_to(root).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    raw=(json.dumps(dict(schema='ONE_FRESH_NATIVE61_ORIGINAL_RESULT_MEMBERS_V1',files=members,original_account_journals_edited=False,warm_journals_duplicated=False,raw_market_or_model_weights_duplicated=False),indent=2)+'\n').encode();write_once(root/'RESULT_MEMBER_HASHES.json',raw);write_once(public/'RESULT_MEMBER_HASHES.json',raw)
    archive=state/'coin_fresh_initialization_native61_results_20261009.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    raw=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(raw),768*1024)):
        piece=raw[start:start+768*1024];name='transport/'+archive.name+f'.bytepart{i:03d}';write_once(public/name,piece);parts.append(dict(path=name,bytes=len(piece),sha256=hashlib.sha256(piece).hexdigest()))
    artifact=dict(schema='ONE_FRESH_NATIVE61_ORDERED_RESULT_PARTS_V1',filename=archive.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),part_max_bytes=768*1024,parts=parts,member_manifest_sha256=sha(root/'RESULT_MEMBER_HASHES.json'),original_journals_byte_identical=True,warm_or_static_wallets_rerun=False,raw_market_or_model_weights_duplicated=False);write_once(public/'ARTIFACT.json',(json.dumps(artifact,indent=2)+'\n').encode());print(json.dumps(dict(status='PASS_ONE_UNCHANGED_FRESH_ACCOUNT_PACKAGE',bytes=len(raw),sha256=artifact['sha256'],parts=len(parts),members=len(members),fresh_minus_warm_USDT=delta['net_PnL_USDT'],allocation=allocation,cost_bridge=bridges)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);a=p.parse_args();package(a.state)
