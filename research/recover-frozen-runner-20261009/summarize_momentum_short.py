"""Read-only four-window economics, monthly bridge and fixed-target identity."""
import argparse
from collections import Counter
from datetime import datetime, UTC
import hashlib, json, os
from pathlib import Path
import resource, sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native61 as frozen
import momentum_short_challenge as recipe


def summarize(state):
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq
    recipe.source_check(); frozen.modules(state)
    preflight = frozen.read(HERE/'MOMENTUM_SHORT_PREFLIGHT.json'); cases = {}
    stamp = lambda t: datetime.fromtimestamp(t/1e6, UTC).isoformat()
    for case, spec in recipe.CASES.items():
        root = state/'momentum-short'/case
        s = frozen.read(root/'account/summary.json'); e = frozen.read(root/'EXECUTION.json'); a = frozen.read(root/'INDEPENDENT_AUDIT.json')
        frozen.require(a['status'].startswith('PASS') and a['actual_input_check']['status'].startswith('PASS'), 'Completed independent account/source audits required')
        t = pq.read_table(root/'account/targets.parquet').to_pandas()
        frozen.require(t.symbol.tolist() == list(frozen.SYMBOLS)*spec['days'], 'Ordered CORE5 calendar required')
        saved = t.target_weight.to_numpy().reshape(spec['days'], 5)
        expected = recipe.targets(recipe.window(state, case)['daily'], spec)[0]
        frozen.require(hashlib.sha256(expected.tobytes()).hexdigest() == preflight['cases'][case]['targets']['target_sha256'] and np.array_equal(saved, expected), 'Saved target differs from frozen protocol')
        bits = saved.view(np.uint64) != expected.view(np.uint64)
        frozen.require((saved[bits] == 0).all() and (expected[bits] == 0).all(), 'Only terminal signed-zero serialization may differ')
        m = pq.read_table(root/'account/minute_nav_inventory.parquet').to_pandas()
        daily = pq.read_table(root/'account/daily_nav.parquet').to_pandas(); nav = daily.nav.to_numpy()
        returns = nav/np.r_[10000., nav[:-1]]-1; delta = np.diff(np.r_[10000., nav])
        months = pd.to_datetime(m.close_us.to_numpy()-1, unit='us', utc=True).strftime('%Y-%m')
        dm = pd.to_datetime(daily.day_end_us.to_numpy()-frozen.DAY, unit='us', utc=True).strftime('%Y-%m')
        monthly = []
        for original in s['months']:
            month = original['month']; ix = np.flatnonzero(dm == month); rows = m[months == month]
            initial = 10000. if ix[0] == 0 else float(nav[ix[0]-1]); pnl = float(delta[ix].sum())
            bridge = original['gross_PnL']-original['fees']-original['spread_cost']-original['slippage_cost']+original['funding_USDT']
            frozen.require(abs(pnl-original['net_PnL']) < 1e-8 and abs(bridge-pnl) < 1e-7, 'Monthly price/cost/funding bridge differs')
            full = np.r_[initial, rows.nav.to_numpy()]
            monthly.append(dict(**original, opening_NAV=initial, return_on_month_opening_NAV=pnl/initial,
                execution_cost=original['spread_cost']+original['slippage_cost'],
                realized_daily_annual_volatility=float(np.std(returns[ix], ddof=1)*np.sqrt(365)),
                minute_max_drawdown_from_month_start=float(np.max(1-full/np.maximum.accumulate(full))),
                minute_mean_gross=float(rows.gross_weight.mean()), minute_peak_gross=float(rows.gross_weight.max())))
        witnesses = frozen.read(root/'INDEPENDENT_SIGNAL_WITNESSES.json'); trades = frozen.read(root/'account/trades.json'); rejections = frozen.read(root/'account/rejections.json')
        risks = {r['decision_us']:r for r in frozen.read(root/'account/target_meta.json')['risk']}
        assets = {}
        for symbol in frozen.SYMBOLS:
            q = m[symbol+'_quantity'].to_numpy(); w = m[symbol+'_signed_weight'].to_numpy()
            frozen.require((q <= 0).all() and (w <= 0).all(), 'Forbidden long inventory')
            fills = [r for r in trades if r['symbol'] == symbol]; own = [r for r in witnesses if r['symbol'] == symbol]
            rejected = [r for r in rejections if r['symbol'] == symbol]; expired = [r for r in rejected if r.get('reason') == 'FIVE_ATTEMPTS_EXPIRED']
            lookup = {r['decision_us']: r['current_completed_close'] for r in own}
            residuals = []
            for r in expired:
                close = lookup[((r['event_us']-1)//frozen.DAY)*frozen.DAY]; quantity = abs(r['remaining_signed_quantity'])
                residuals.append(dict(event_us=r['event_us'], kind=r['kind'], remaining_signed_quantity=r['remaining_signed_quantity'], below_one_lot=quantity < 1e-8, remaining_notional_at_completed_signal_close=quantity*close))
            asset_monthly = {}
            for month in (r['month'] for r in monthly):
                selected = months == month; rows = m[selected]; mq = q[selected]; mw = w[selected]
                active = [r for r in own if stamp(r['decision_us'])[:7] == month and r['held_short_after']]
                scales = [min(1., .1/risks[r['decision_us']]['unscaled_signed_covariance_annual_vol']) if risks[r['decision_us']]['unscaled_signed_covariance_annual_vol'] else 1. for r in active]
                mf = [r for r in fills if stamp(r['event_us'])[:7] == month]
                asset_monthly[month] = dict(raw_active_signal_days=len(active),
                    actual_exposure_days=len(np.unique(((rows.close_us.to_numpy()[mq < 0]-1)//frozen.DAY)*frozen.DAY)),
                    mean_short_abs_weight=float(-mw.mean()), peak_short_abs_weight=float(-mw.min()),
                    covariance_scale_active_day_mean=float(np.mean(scales)) if scales else None,
                    initial_short_entries_UTC=[stamp(r['event_us']) for r in mf if r['quantity_before'] == 0 and r['quantity_after'] < 0],
                    final_short_exits_UTC=[stamp(r['event_us']) for r in mf if r['quantity_before'] < 0 and r['quantity_after'] == 0])
            assets[symbol] = dict(raw_active_signal_days=sum(r['held_short_after'] for r in own),
                actual_exposure_days=len(np.unique(((m.close_us.to_numpy()[q < 0]-1)//frozen.DAY)*frozen.DAY)),
                minute_mean_short_abs_weight=float(-w.mean()), minute_peak_short_abs_weight=float(-w.min()), fill_legs=len(fills),
                initial_short_entries_UTC=[stamp(r['event_us']) for r in fills if r['quantity_before'] == 0 and r['quantity_after'] < 0],
                final_short_exits_UTC=[stamp(r['event_us']) for r in fills if r['quantity_before'] < 0 and r['quantity_after'] == 0],
                order_attempt_reasons=dict(Counter(str(r.get('reason')) for r in rejected)), expired_orders=residuals, monthly=asset_monthly)
        bridge = s['gross_PnL_same_quantities']-s['fees_USDT']-s['execution_cost_USDT']+s['funding_USDT']
        frozen.require(abs(bridge-s['net_PnL']) < 1e-7, 'Full price/cost/funding bridge differs')
        fields = ('NAV', 'net_PnL', 'gross_PnL_same_quantities', 'fees_USDT', 'execution_cost_USDT', 'funding_USDT', 'trade_legs',
            'normalized_total_turnover', 'all_observation_max_drawdown', 'daily_metrics', 'realized_exposure', 'maximum_actual_asset_weights',
            'long_short_marked_contribution', 'terminal_cash_realized', 'liquidation_count', 'risk_reduction_signal_count')
        cases[case] = dict(calendar=spec, **{k:s[k] for k in fields}, monthly=monthly, assets=assets,
            activity=a.get('activity', 'ACTIVELY_TRADED' if trades else 'INACTIVE_ZERO_TRADING_NOT_ALPHA'),
            financial_audit=a['status'], actual_input_audit=a['actual_input_check'], maximum_NAV_error_USDT=a['maximum_NAV_error_USDT'],
            maximum_wallet_error_USDT=a['maximum_wallet_error_USDT'], target_numeric_maximum_error=0,
            target_signed_zero_bit_differences=int(bits.sum()), first_entry_UTC=stamp(s['first_entry_us']) if s['first_entry_us'] is not None else None,
            elapsed_seconds=e['elapsed_seconds'], peak_RSS_bytes=e['peak_RSS_bytes'], plan_commit=e['plan_commit'])
    return dict(schema='ONE_FIXED_MOMENTUM_SHORT_FOUR_REGIME_RESULTS_V1', status='PASS_FOUR_COMPLETE_INDEPENDENT_ACCOUNTS_AND_FROZEN_TARGETS', cases=cases,
        exact_recipe_sha256=frozen.sha(frozen.REPO/'scripts/investment/momentum_short_pool_target.py'), exact_engine_sha256=frozen.sha(frozen.REPO/'scripts/investment/resumable_perpetual.py'),
        fresh_capital_USDT_each=10000, actual_wallets_started=4, actual_wallets_completed=4, account_stitching=False, June1_wallet_reset=False,
        selected_after_seeing_June2024=True, roles='KNOWN_DEVELOPMENT_AND_PREVIOUSLY_SEEN_CONDITIONAL_ROBUSTNESS_NOT_PRISTINE_OOS',
        models_fit=0, provider_downloads=0, hold_wallets_started=0, parameter_sweeps=0, post_result_parameters_changed=False, pool_promotion=False,
        next_gate='Stop after these four accounts; further recipes or pool-expansion comparisons require separate authorization.', historic_exchange_account_rules_certified=False)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--state',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'): os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))}); resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000))
    r=summarize(a.state); a.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:{n:v[n] for n in ('net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT','trade_legs','activity','all_observation_max_drawdown','monthly')} for k,v in r['cases'].items()}),flush=True)
