"""Read-only monthly short-account economics and frozen target reconciliation."""
import argparse
from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import native61 as frozen


def summarize(state):
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq
    root=state/'donchian-short61/DONCHIAN20_EXIT10_SHORT_ONLY';account=root/'account'
    summary=frozen.read(account/'summary.json');execution=frozen.read(root/'EXECUTION.json');audit=frozen.read(root/'INDEPENDENT_AUDIT.json')
    frozen.require(audit['status'].startswith('PASS') and audit['actual_input_check']['status'].startswith('PASS'),'Completed independent financial and actual input audits required')
    targets=pq.read_table(account/'targets.parquet').to_pandas()
    frozen.require(len(targets)==305 and targets.symbol.tolist()==list(frozen.SYMBOLS)*61,'Exact ordered305 target rows required')
    values=targets.target_weight.to_numpy().reshape(61,5)
    digest=hashlib.sha256(values.tobytes()).hexdigest();preflight=frozen.read(HERE/'DONCHIAN_SHORT61_PREFLIGHT.json')
    import donchian_short61
    expected=donchian_short61.targets(state)[0]
    frozen.require(hashlib.sha256(expected.tobytes()).hexdigest()==preflight['target_sha256'],'Frozen causal target preflight differs')
    frozen.require(np.array_equal(values,expected) and (values<=0).all(),'Saved executed target stream differs from frozen preflight')
    bitwise_difference=values.view(np.uint64)!=expected.view(np.uint64)
    frozen.require((values[bitwise_difference]==0).all() and (expected[bitwise_difference]==0).all(),'Only signed zero may differ in native terminal target serialization')
    minute=pq.read_table(account/'minute_nav_inventory.parquet').to_pandas()
    weights=minute[[s+'_signed_weight' for s in frozen.SYMBOLS]].to_numpy()
    quantities=minute[[s+'_quantity' for s in frozen.SYMBOLS]].to_numpy()
    frozen.require((weights<=0).all() and (quantities<=0).all(),'Forbidden long inventory in minute ledger')
    daily=pq.read_table(account/'daily_nav.parquet').to_pandas();nav=daily.nav.to_numpy()
    delta=np.diff(np.r_[10000.,nav]);returns=nav/np.r_[10000.,nav[:-1]]-1
    months=pd.to_datetime(minute.close_us.to_numpy()-1,unit='us',utc=True).strftime('%Y-%m')
    day_months=pd.to_datetime(daily.day_end_us.to_numpy()-frozen.DAY,unit='us',utc=True).strftime('%Y-%m')
    rows=[]
    for saved in summary['months']:
        m=saved['month'];ix=np.flatnonzero(day_months==m);d=minute[months==m]
        initial=10000. if ix[0]==0 else float(nav[ix[0]-1])
        pnl=float(delta[ix].sum());frozen.require(abs(pnl-saved['net_PnL'])<1e-8,'Monthly incremental NAV bridge differs')
        bridge=saved['gross_PnL']-saved['fees']-saved['spread_cost']-saved['slippage_cost']+saved['funding_USDT']
        frozen.require(abs(bridge-pnl)<1e-7,'Monthly price/cost/funding bridge differs')
        full=np.r_[initial,d.nav.to_numpy()]
        rows.append(dict(**saved,opening_NAV=initial,return_on_month_opening_NAV=pnl/initial,
            realized_daily_annual_volatility=float(np.std(returns[ix],ddof=1)*np.sqrt(365)),
            minute_max_drawdown_from_month_start=float(np.max(1-full/np.maximum.accumulate(full))),
            minute_mean_gross=float(d.gross_weight.mean()),minute_peak_gross=float(d.gross_weight.max()),
            minute_mean_short_abs_weight=float(-d.net_signed_weight.mean()),minute_mean_long_weight=0.,
            execution_cost=saved['spread_cost']+saved['slippage_cost']))
    baseline_root=state/'pool61/DONCHIAN_EXIT10'
    baseline=frozen.read(baseline_root/'account/summary.json')
    baseline_audit=frozen.read(baseline_root/'INDEPENDENT_AUDIT.json')
    frozen.require(baseline_audit['status'].startswith('PASS'),'Saved baseline audit required')
    refs=dict(policy='DONCHIAN_EXIT10_LONG_ONLY',scope='SAME61_SAVED_INDEPENDENT_WALLET_READ_ONLY',
        months=baseline['months'],net_PnL=baseline['net_PnL'],realized_exposure=baseline['realized_exposure'],
        daily_annual_volatility=baseline['daily_metrics']['annual_volatility'],all_observation_max_drawdown=baseline['all_observation_max_drawdown'],
        limits='Different direction and removed SMA200 entry filter; actual risk is not matched; cannot add independent wallet payoffs into executable switching returns')
    fields=('NAV','net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT','trade_legs','gross_fill_turnover_USDT',
        'normalized_total_turnover','all_observation_max_drawdown','daily_metrics','realized_exposure','maximum_actual_asset_weights',
        'long_short_marked_contribution','first_entry_us','terminal_cash_realized','liquidation_count','risk_reduction_signal_count')
    return dict(schema='ONE_FIXED_DONCHIAN_SHORT_NATIVE61_RESULTS_V1',status='PASS_COMPLETE_ACCOUNT_FINANCIAL_ACTUAL_SOURCE_AND_TARGET_AUDITS',
        plan_commit=execution['plan_commit'],engine_sha256=execution['original_engine_sha256'],calendar='2024-05-01 to2024-07-01 exclusive',
        fresh_capital_USDT=10000,selected_after_seeing_June2024=True,evidence_role='SEEN_DEVELOPMENT_NOT_OOS',June1_wallet_reset=False,
        June_incremental_net_USDT=rows[1]['net_PnL'],June_opening_NAV=rows[1]['opening_NAV'],actual_wallets_started=1,actual_wallets_completed=1,
        hold_wallets_started=0,model_fits=0,provider_downloads=0,parameter_sweeps=0,pool_promotion=False,
        financial_audit=audit['status'],actual_input_audit=audit['actual_input_check'],saved_target_sha256=digest,
        frozen_target_sha256=preflight['target_sha256'],numeric_target_maximum_error=0,
        target_signed_zero_bit_differences=int(bitwise_difference.sum()),
        maximum_NAV_error_USDT=audit['maximum_NAV_error_USDT'],maximum_wallet_error_USDT=audit['maximum_wallet_error_USDT'],
        first_entry_UTC=datetime.fromtimestamp(summary['first_entry_us']/1e6,UTC).isoformat(),
        execution_seconds=execution['elapsed_seconds'],peak_RSS_bytes=execution['peak_RSS_bytes'],
        results={k:summary[k] for k in fields},monthly=rows,saved_long_reference=refs,
        interpretation='June net positive after all paid costs; May loss leaves a small full-period gain. Actual signed funding aids shorts. Does not establish OOS alpha or selector benefit.',
        next_gate='A separately predeclared independent-period comparison is required before any selector-pool addition; no further wallet authorized by this result',
        annualization_role='DESCRIPTIVE_DAILY_RETURN_VOLATILITY_OVER61_DAYS_NOT_LONG_TERM_APR',historical_exchange_account_rules_certified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=summarize(a.state);a.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=r['status'],monthly=[{k:m[k] for k in ('month','net_PnL','minute_mean_gross','minute_peak_gross','realized_daily_annual_volatility','minute_max_drawdown_from_month_start')} for m in r['monthly']],net=r['results']['net_PnL'])),flush=True)
