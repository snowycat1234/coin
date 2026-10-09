"""Read-only regime economics, per-asset activity and frozen target checks."""
import argparse
from datetime import datetime,UTC
import hashlib,json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import native61 as frozen
import short_regimes


def summarize(state):
    import numpy as np
    import pyarrow.parquet as pq
    preflight=frozen.read(HERE/'SHORT_REGIMES_PREFLIGHT.json');cases={}
    for case,spec in short_regimes.CASES.items():
        root=state/'short-regimes'/case;s=frozen.read(root/'account/summary.json');e=frozen.read(root/'EXECUTION.json');a=frozen.read(root/'INDEPENDENT_AUDIT.json')
        frozen.require(a['status'].startswith('PASS') and a['actual_input_check']['status'].startswith('PASS'),'Financial/actual-source audit required')
        t=pq.read_table(root/'account/targets.parquet').to_pandas();values=t.target_weight.to_numpy().reshape(spec['days'],5)
        frozen.require(t.symbol.tolist()==list(frozen.SYMBOLS)*spec['days'],'Ordered CORE5 target calendar required')
        expected=short_regimes.target_path(short_regimes.window(state,case)['daily'],spec)[0]
        frozen.require(hashlib.sha256(expected.tobytes()).hexdigest()==preflight['cases'][case]['targets']['target_sha256'] and np.array_equal(values,expected),'Saved target differs from frozen protocol')
        m=pq.read_table(root/'account/minute_nav_inventory.parquet').to_pandas()
        witnesses=frozen.read(root/'INDEPENDENT_SIGNAL_WITNESSES.json');trades=frozen.read(root/'account/trades.json');rejections=frozen.read(root/'account/rejections.json')
        assets={}
        for symbol in frozen.SYMBOLS:
            q=m[symbol+'_quantity'].to_numpy();w=m[symbol+'_signed_weight'].to_numpy();f=[r for r in trades if r['symbol']==symbol]
            frozen.require((q<=0).all() and (w<=0).all(),'Forbidden actual long exposure')
            assets[symbol]=dict(raw_active_signal_days=sum(r['held_short_after'] for r in witnesses if r['symbol']==symbol),
                actual_exposure_days=len(np.unique(((m.close_us.to_numpy()[q<0]-1)//frozen.DAY)*frozen.DAY)),
                minute_mean_short_abs_weight=float(-w.mean()),minute_peak_short_abs_weight=float(-w.min()),fill_legs=len(f),
                initial_short_entries_UTC=[datetime.fromtimestamp(r['event_us']/1e6,UTC).isoformat() for r in f if r['quantity_before']==0 and r['quantity_after']<0],
                final_short_exits_UTC=[datetime.fromtimestamp(r['event_us']/1e6,UTC).isoformat() for r in f if r['quantity_before']<0 and r['quantity_after']==0],
                expired_order_count=sum(r.get('reason')=='FIVE_ATTEMPTS_EXPIRED' for r in rejections if r['symbol']==symbol))
        bridge=s['gross_PnL_same_quantities']-s['fees_USDT']-s['execution_cost_USDT']+s['funding_USDT']
        frozen.require(abs(bridge-s['net_PnL'])<1e-7,'Complete financial price/cost/funding bridge differs')
        fields=('NAV','net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT','trade_legs','normalized_total_turnover',
            'all_observation_max_drawdown','daily_metrics','realized_exposure','maximum_actual_asset_weights','long_short_marked_contribution','months','terminal_cash_realized','liquidation_count','risk_reduction_signal_count')
        cases[case]=dict(calendar=spec,**{k:s[k] for k in fields},activity=a['activity'],assets=assets,source_preflight=preflight['cases'][case]['status'],
            financial_audit=a['status'],actual_input_audit=a['actual_input_check'],maximum_NAV_error_USDT=a['maximum_NAV_error_USDT'],maximum_wallet_error_USDT=a['maximum_wallet_error_USDT'],
            target_numeric_maximum_error=0,first_entry_UTC=datetime.fromtimestamp(s['first_entry_us']/1e6,UTC).isoformat() if s['first_entry_us'] is not None else None,
            elapsed_seconds=e['elapsed_seconds'],peak_RSS_bytes=e['peak_RSS_bytes'],plan_commit=e['plan_commit'])
    return dict(schema='THREE_FROZEN_SHORT_REGIME_RESULTS_V1',status='PASS_THREE_INDEPENDENT_COMPLETE_AUDITED_ACCOUNTS',cases=cases,
        exact_recipe_sha256=frozen.sha(frozen.REPO/'scripts/investment/donchian_short_daily_pool_target.py'),exact_engine_sha256=frozen.sha(frozen.REPO/'scripts/investment/resumable_perpetual.py'),
        fresh_capital_USDT_each=10000,actual_wallets_started=3,actual_wallets_completed=3,account_stitching=False,post_result_parameters_changed=False,
        roles='NOVEMBER_JANUARY_KNOWN_RESEARCH_HISTORY; OKX_PREVIOUSLY_SEEN_CONDITIONAL_ROBUSTNESS_NOT_PRISTINE_OOS',
        zero_activity_interpretation='JANUARY_INACTIVE_IS_NOT_ALPHA',models_fit=0,provider_downloads=0,hold_wallets_started=0,pool_promotion=False,
        next_gate='Separately controlled pool-expansion comparison requires explicit protocol; do not automatically promote or fit',
        historic_exchange_account_rules_certified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=summarize(a.state);a.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:{n:v[n] for n in ('net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT','trade_legs','activity','all_observation_max_drawdown')} for k,v in r['cases'].items()}),flush=True)
