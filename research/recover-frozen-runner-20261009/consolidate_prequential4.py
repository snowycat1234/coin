"""Read-only consolidation of four independent native folds and prior screen."""
import argparse,json
from pathlib import Path
import april_native63 as april
from package_prequential63 import write_once
HERE=april.HERE;read=april.read;sha=april.sha


def consolidate(state,april_artifact_commit):
    prior=read(HERE/'prequential2023/COMPLETION.json');folders={
        'FOLD_20230703':HERE/'prequential2023/FOLD_20230703/results',
        'FOLD_20231002':HERE/'prequential2023/FOLD_20231002/results',
        'FOLD_20240101':HERE/'prequential63-native-results',
        'FOLD_20240401':april.PUBLIC/'results'}
    folds={};old_utilities=[];rows=['| Fold start | Model net USDT | Static50 | Cash50 | Model − Static50 | Model DD | Model mean gross |','|---|---:|---:|---:|---:|---:|---:|']
    for fold,folder in folders.items():
        result=read(folder/'RESULTS.json');artifact=read(folder/'ARTIFACT.json');receipt=read(folder/'PUBLIC_READBACK.json')
        assert receipt['status'].startswith('PASS_PUBLIC_') and receipt['archive_SHA256']==artifact['sha256'] and result['status']=='PASS_THREE_COMPLETE_AUDITED_FROZEN_NATIVE63_ACCOUNTS'
        if fold!='FOLD_20240401':assert sha(folder/'RESULTS.json')==prior['folds'][fold]['results_SHA256'] and artifact['sha256']==prior['folds'][fold]['archive_SHA256']
        accounts={}
        for arm,r in result['accounts'].items():
            assert r['fresh_capital_USDT']==10000 and r['calendar']==result['calendar'] and r['terminal_paid_flat'] and r['engine_SHA256']=='318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585' and r['liquidation_count']==0
            assert abs(r['net_PnL_USDT']-(r['price_PnL_USDT']+r['funding_USDT']-r['fees_USDT']-r['execution_cost_USDT']))<1e-8
            accounts[r['producer_policy']]=r
        model=accounts['FRESH_GRU'];static=accounts['VOL50_CS50'];cash=accounts['CASH50_VOL25_CS25']
        producer=(state/'prequential63-native-wrappers/producer') if fold=='FOLD_20240101' else (state/'prequential2023-wrappers'/fold/'producer') if fold!='FOLD_20240401' else april.locations(state)[1]
        manifest=read(producer/'MANIFEST.json');assert sha(producer/'RESULT.json')==manifest['files']['RESULT.json']['SHA256'];proxy=read(producer/'RESULT.json')
        if fold!='FOLD_20240401':old_utilities.append(proxy['primary_utility_excess'])
        folds[fold]=dict(calendar=result['calendar'],result_relative_path=(folder/'RESULTS.json').relative_to(HERE).as_posix(),result_SHA256=sha(folder/'RESULTS.json'),archive_SHA256=artifact['sha256'],archive_commit=april_artifact_commit if fold=='FOLD_20240401' else receipt['commit'] if fold=='FOLD_20240101' else receipt['artifact_commit'],public_readback_relative_path=(folder/'PUBLIC_READBACK.json').relative_to(HERE).as_posix(),public_readback_SHA256=sha(folder/'PUBLIC_READBACK.json'),public_readback_status=receipt['status'],accounts=accounts,model_minus_fixed_control=result['model_minus_fixed_control'],original_daily_proxy_primary_utility_excess=proxy['primary_utility_excess'],original_daily_proxy_RESULT_SHA256=sha(producer/'RESULT.json'),model_wins_primary=model['net_PnL_USDT']>static['net_PnL_USDT'],model_wins_cashheavy=model['net_PnL_USDT']>cash['net_PnL_USDT'])
        date=fold[-8:];rows.append(f"| {date[:4]}-{date[4:6]}-{date[6:]} | {model['net_PnL_USDT']:.6f} | {static['net_PnL_USDT']:.6f} | {cash['net_PnL_USDT']:.6f} | {model['net_PnL_USDT']-static['net_PnL_USDT']:.6f} | {model['minute_max_drawdown']:.6%} | {model['realized_exposure']['minute_mean_gross_weight']:.6%} |")
    original_screen=dict(formula='mean_block_own_path_utility_excess>0_AND_worst_block_excess>=0_vs_fixed_primary',scope='ORIGINAL_JULY_OCTOBER_JANUARY_DAILY_PROXY_SCREEN_RETAINED;NOT_REPLACED_BY_NATIVE_PNL_OR_APRIL_RESULT',primary_control='VOL50_CS50',original_three_fold_utility_excesses=old_utilities,original_three_fold_mean_utility_excess=sum(old_utilities)/3,original_three_fold_worst_utility_excess=min(old_utilities),original_screen_passed=(sum(old_utilities)/3>0 and min(old_utilities)>=0))
    assert original_screen['original_screen_passed'] is False
    r=dict(status='PASS_FOUR_SEPARATE_PREQUENTIAL_NATIVE_FOLD_COMPARISONS',folds=folds,original_failed_screen=original_screen,model_beats_primary_folds=sum(x['model_wins_primary'] for x in folds.values()),model_beats_cashheavy_folds=sum(x['model_wins_cashheavy'] for x in folds.values()),worst_native_primary_excess_USDT=min(x['model_minus_fixed_control']['VOL50_CS50']['net_PnL_USDT'] for x in folds.values()),separate_accounts=12,capital_USDT_each=10000,April_new_wallets=3,old_wallets_reused_without_rerun=9,account_stitching=False,compound_or_APR_return_computed=False,model_fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0,interpretation='July primary gain survives native costs; October, January and April trail primary control. Original failed screen remains failed. Unequal realized gross/net exposure and drawdown; no stable equal-risk alpha, pristine project OOS, convergence, seed robustness or executable switching evidence.',limitations=['Each fold starts fresh10k and paid-flat closes; gaps and capital resets prevent a continuous capital path.','The four folds use increasing causal prefix information, but periods were already project-seen; April was a coverage-chosen continuation after a failed screen.','Shared target caps do not equalize realized risk; SHORT pool was selected after seen June2024.','Public empty-Adam birth0 receipts and actual consumed input identities were checked; optimizer history was not independently replayed.','Historical publication, venue/account/filter rules uncertified; original2023 retrieval timestamps UNKNOWN. Original source/container evidence retained.'])
    public=HERE/'prequential-four-folds';write_once(public/'COMPARISON.json',(json.dumps(r,indent=2)+'\n').encode())
    text='Four separate original guard-OFF native fold comparisons, each fresh10k /63decisions /90720minutes /945actual funding records /full costs /paid flat closure.\n\n'+'\n'.join(rows)+f"\n\nModel beats Static50 in {r['model_beats_primary_folds']}/4 folds and Cash50 in {r['model_beats_cashheavy_folds']}/4. July gain survives native costs; October, January and April trail the primary control. Full per-account monthly PnL, gross/net exposure, drawdown, funding, fees/execution costs and archive/readback hashes are in COMPARISON.json and each linked fold result.\n\nOriginal three-fold daily-proxy screen remains FAILED: mean own-path utility excess {original_screen['original_three_fold_mean_utility_excess']:.12f}, worst {original_screen['original_three_fold_worst_utility_excess']:.12f}; the worst-fold requirement fails. This original utility screen is not silently replaced with native PnL or a new result.\n\nThese12accounts are not stitched or annualized. Nine completed accounts were read without rerunning; only the three April accounts were new. Actual risk/exposure differs substantially. Historical prequential project-seen inputs, coverage-chosen April continuation, uncertified historical publication/venue/account/filter rules, source-bound fresh receipts without optimizer replay, fixed512without convergence proof. No stable equal-risk alpha or executable switching claim; no model fits/inference/provider downloads/old reruns.\n"
    write_once(public/'README.md',text.encode());print(json.dumps(dict(status=r['status'],model_beats_primary_folds=r['model_beats_primary_folds'],model_beats_cashheavy_folds=r['model_beats_cashheavy_folds'],original_failed_screen=original_screen,worst_native_primary_excess_USDT=r['worst_native_primary_excess_USDT'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--april-artifact-commit',required=True);a=p.parse_args();consolidate(a.state,a.april_artifact_commit)
