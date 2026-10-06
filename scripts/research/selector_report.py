"""Automatic financial report; development screening is not investment proof."""
import json,math
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT
from scripts.research.selector_jobs import atomic
from scripts.investment.reuse_cycle_controls import sha

def publish(config,run,binding,accounts,fits,champion,scores):
    run=Path(run);rows=[];decisions=[];h=int(champion.rsplit('_H',1)[1])
    for r in accounts:
        s=r['summary'];complete=s['completed_minutes']==s['required_minutes'] and s['terminal_cash_realized']
        rows.append(dict(id=r['id'],unit=r['unit'],complete=complete,role='FUTURE_INFORMED_ORACLE_NOT_CANDIDATE' if r['id'].startswith('ORACLE') else 'PLACEBO_CONTROL' if r['id'].startswith(('LABEL_SHUFFLE','FEATURE_SHUFFLE','RANDOM')) else 'SEEN_CHRONOLOGICAL_VALIDATION',
            net_PnL=s['net_PnL'] if complete else None,stopped_prefix_PnL=s['net_PnL'],gross_PnL=s['gross_PnL_same_quantities'],fees=s['fees_USDT'],execution=s['execution_cost_USDT'],funding=s['funding_USDT'],
            annualized_return=s.get('daily_metrics',{}).get('annual_return'),Sharpe=s.get('daily_metrics',{}).get('sharpe'),MDD=s.get('minute_max_drawdown'),volatility=s.get('daily_metrics',{}).get('annual_volatility'),
            turnover=s.get('normalized_total_turnover'),direction=s['long_short_marked_contribution'],calendar_year=r['calendar_year_contribution'],risk=s.get('realized_exposure'),
            initial_capital=10000,observed_gross=s['maximum_actual_gross_weight'],collateral_assumption='ISOLATED1X_NO_TOPUP',instantaneous_caps_guaranteed=False,
            missing_or_halt_preserved=not complete,short_open_legs=r['independent']['actual_short_open_legs'],concentration=s.get('daily_net_gain_concentration'),
            artifacts=r['artifacts'],wallet_error=r['independent']['maximum_wallet_error_USDT'],NAV_error=r['independent']['maximum_NAV_error_USDT']))
    for unit in config['units']:
        candidates=[v for v in rows if v['unit']==unit and v['id'].removesuffix('_'+unit) in ('SMA200_SIGNED','HOLD','CASH','STATIC')]
        baseline=max((v for v in candidates if v['complete']),key=lambda v:v['net_PnL']);selected=next(v for v in rows if v['id']==champion+'_'+unit)
        oracle=next(v for v in rows if v['id']=='ORACLE_H'+str(h)+'_'+unit)
        placebos=[v for v in rows if v['unit']==unit and v['role']=='PLACEBO_CONTROL'];assert len(placebos)==64
        all_complete=selected['complete'] and oracle['complete'] and all(v['complete'] for v in candidates+placebos)
        if all_complete:
            gap=oracle['net_PnL']-baseline['net_PnL'];capture=(selected['net_PnL']-baseline['net_PnL'])/gap if gap>0 else None
            groups={kind:[v['net_PnL'] for v in placebos if v['id'].startswith(kind)] for kind in ('LABEL_SHUFFLE','FEATURE_SHUFFLE','RANDOM')}
            thresholds={k:float(np.quantile(v,.95)) for k,v in groups.items()}
            year_checks={y:selected['calendar_year'][y]['net']>baseline['calendar_year'][y]['net'] for y in ('2022','2023')}
            checks=dict(net_gt_best_static=selected['net_PnL']>baseline['net_PnL'],capture_ge015=capture is not None and capture>=config['success']['capture_min'],
                above_all_placebo95=all(selected['net_PnL']>v for v in thresholds.values()),both_year_segments_improve=all(year_checks.values()),
                vol_within_fixed_budget=selected['volatility']<=config['success']['max_realized_vol'],MDD_within_reference=selected['MDD']<=max(config['success']['DD_floor'],baseline['MDD']*config['success']['DD_factor']))
        else:gap=capture=None;thresholds={};year_checks={};checks=dict(all_required_accounts_complete=False)
        shorts2022=selected['calendar_year'].get('2022',{}).get('SHORT');oracle_short2022=oracle['calendar_year'].get('2022',{}).get('SHORT')
        decisions.append(dict(unit=unit,selected_model=champion,best_static_id=baseline['id'],oracle_id=oracle['id'],capture_ratio=capture,oracle_gap_USDT=gap,
            placebo95=thresholds,year_checks=year_checks,checks=checks,pass_development_screen=all(checks.values()),
            short2022_Q4=shorts2022,short2022_Q4_capture=shorts2022/oracle_short2022 if oracle_short2022 and oracle_short2022>0 else None,
            short2022_scope='ONLY2022Q4_92D_VALIDATION; NOT_FULL_YEAR_OR_TRAIN_REPLAY',short2023=selected['calendar_year'].get('2023',{}).get('SHORT')))
    # Preserve actual order/target transitions, including near short-to-flat or
    # short-to-long changes. The direction contributions use the same wallet.
    transitions=[]
    for unit in config['units']:
        r=next(v for v in accounts if v['id']==champion+'_'+unit);target=pl.read_parquet(r['artifacts']['targets.parquet']['path']).sort('available_us')
        before=None
        for row in target.iter_rows(named=True):
            w=row['target_weight']
            if before is not None and before<0 and w>=0:transitions.append(dict(unit=unit,decision_us=row['available_us'],previous_signed_target=before,new_signed_target=w,scope='TARGET_TRANSITION; FILLS/FEES_IN_ACTUAL_LEDGER'))
            before=w
    partial_fit_starts=list((run/'cv').glob('*/attempts/*/started.json'))
    successful=[Path(v['model_path']).parent for v in fits];unfinished=[str(p) for p in partial_fit_starts if p.parent not in successful]
    output=dict(status='COMPLETE_SELECTOR_ML_DAG_DEVELOPMENT_ONLY',binding=binding,config=config,champion_by_preregistered_rank=champion,validation_rank_scores=scores,
        decisions=decisions,rows=rows,fit_records=[{k:v for k,v in item.items() if k!='_binding'} for item in fits],actual_scalar_model_fits=sum(v['scalar_model_fits'] for v in fits),actual_scaler_fits=sum(v['scaler_fits'] for v in fits),
        unfinished_fit_attempts=unfinished,unknown_partial_fit_count='UNKNOWN' if unfinished else 0,
        economic_accounts=len(accounts),static_parameters_changed=False,selector_short_to_cash_hold_transitions=transitions,
        features=dict(columns=config['features'],availability_file=str(run/'features.parquet'),sha256=sha(run/'features.parquet'),cross_sectional='OMITTED_NO_COMMON_COMPLETE_MULTIASSET2022_2023',funding_basis='OMITTED_UNCERTIFIED_UNIT_AND_PUBLICATION'),
        model_eligibility=json.loads((run/'MLP_SKIP.json').read_bytes()),FINAL_LOCKED_TEST='NOT_RUN_NOT_AUTHORIZED',investment_candidate='NONE_CASH',LLM_API_calls=0,
        decision='RETAIN_DEVELOPMENT_ML_CHALLENGER_REQUIRES_INDEPENDENT_VALIDATION' if all(v['pass_development_screen'] for v in decisions) else 'NO_ML_PROMOTION_OVERFIT_OR_INSUFFICIENT_NET_ADVANTAGE_NO_COMPLEXITY_INCREASE',
        limitations=['ALL_EVALUATED_HISTORY_PREVIOUSLY_SEEN','OVERLAPPING_DAILY_LABELS_NOT_INDEPENDENT_SAMPLES','PURGED_PLUS_HDAY_EMBARGO','ONLY2022Q4_AND2023VALIDATION','BINANCE_PRICE_BYBIT_FEE_PROXY','FUNDING_TWO_CONDITIONAL_UNITS','NATIVE_QUANTITY_MMR_ASSUMPTIONS','MATCHED_CAPS_NOT_REALIZED_RISK_MATCHED','ORACLE_NONCAUSAL_NOT_GLOBAL_ACTUAL_OPTIMUM','PLACEBO_REPLICATES_NOT_MORE_HISTORY','LONG_TERM_APR_NOT_CERTIFIED'])
    destination=ROOT/'reports/SELECTOR_ML_RESULTS.json'
    if destination.exists():
        previous=json.loads(destination.read_bytes());assert previous['binding']==binding,'Never overwrite frozen results for another configuration'
        assert (ROOT/'reports/SELECTOR_ML_REPORT.md').exists() and (ROOT/'reports/SELECTOR_ML_PLOTS').is_dir();return
    plotdir=ROOT/'reports/SELECTOR_ML_PLOTS';plotdir.mkdir(exist_ok=True)
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    for unit in config['units']:
        fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
        for name in (champion,'SMA200_SIGNED','HOLD','STATIC','ORACLE_H'+str(h)):
            r=next(v for v in accounts if v['id']==name+'_'+unit);nav=pl.read_parquet(r['artifacts']['daily_nav.parquet']['path']).sort('day_end_us');values=np.r_[10000.,nav['nav'].to_numpy()]
            axes[0].plot(values,label=name+(' [future-informed]' if name.startswith('ORACLE') else ''));axes[1].plot(1-values/np.maximum.accumulate(values))
        axes[0].set_ylabel('NAV / full 10k USDT');axes[1].set_ylabel('Daily drawdown');axes[1].set_xlabel('Validation days; seen history');axes[0].legend(fontsize=7)
        fig.suptitle(unit+' | Binance prices + Bybit cost proxy | not investment evidence');fig.tight_layout();fig.savefig(plotdir/(unit+'.png'),dpi=130);plt.close(fig)
    text=['# SELECTOR ML REPORT','',output['decision'],'','Investment qualification: **NONE/CASH**. Final locked test: **NOT_RUN**. All history is previously seen development/internal chronological validation.',
        '',f'Selected by minimum funding-condition common-date validation utility rank: `{champion}`. No selection by best backtest PnL; no post-result parameter change.',
        f'Actual scalar model fits: {output["actual_scalar_model_fits"]}; actual scaler fits: {output["actual_scaler_fits"]}; actual one-wallet counterfactual accounts: {len(accounts)}. MLP skipped for insufficient sample size. No LLM/API calls.',
        '', '|Account|Funding condition|Net USDT|Annual extrapolation|Sharpe|Minute MDD|Vol|Turnover|Fee|Execution|Funding|LONG|SHORT|','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in rows:
        if v['role']=='PLACEBO_CONTROL':continue
        values=[v['net_PnL'],v['annualized_return'],v['Sharpe'],v['MDD'],v['volatility'],v['turnover'],v['fees'],v['execution'],v['funding'],v['direction']['LONG']['net_contribution'],v['direction']['SHORT']['net_contribution']]
        text.append('|'+v['id']+'|'+v['unit']+'|'+'|'.join('NOT_EVALUABLE' if x is None else f'{x:.5f}' for x in values)+'|')
    text += ['', '## Preregistered decisions','',json.dumps(decisions,indent=2), '',
        '2022 capture covers only Q4 (92 days); it is not a full-year result. 2023 SHORT, year contributions, actual fees/execution/funding, margin/exposure and concentration are in RESULTS.json with complete ledger references.',
        'Annualized return is a descriptive extrapolation from this seen window, not stable APR. Same caps do not equal risk matching. Halted accounts retain actual prefixes and do not qualify; missing/unknown costs are not zero-filled.',
        'Train/validation R² and purged chronology are retained per fold; excellent training and weak validation do not justify larger models. Placebos include training-only label/feature shuffle and conditional same-frequency random weights; random schedules are diagnostic, not deployable.',
        'All source and configuration hashes bind the preregistration commit. Restart/resume reuses only complete matching checkpoints; no independent wallets are added into a synthetic strategy curve.', '']
    (ROOT/'reports/SELECTOR_ML_REPORT.md').write_text('\n'.join(text),encoding='utf-8')
    atomic(run/'final_results.json',output);atomic(destination,output)
