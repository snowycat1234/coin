"""Read saved audited wallets and compare daily paths; no new simulation."""
import argparse
import json
from pathlib import Path


def summarize(state):
    import numpy as np
    import pyarrow.parquet as pq
    policies=('SMA50_200_SIGNED','DONCHIAN_EXIT10')
    keys=('NAV','net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','spread_cost_USDT','slippage_cost_USDT','funding_USDT',
        'gross_fill_turnover_USDT','normalized_total_turnover','trade_legs','funding_original_events','funding_owned_events',
        'all_observation_max_drawdown','maximum_actual_asset_weights','realized_exposure','long_short_marked_contribution','months',
        'completed_minutes','terminal_cash_realized','terminal_not_forced_free_fill','liquidation_count')
    saved={}; paths={}
    for name in policies+('NO_CASH','WITH_CASH','STATIC50','CASH50'):
        root=state/('pool61' if name in policies else 'results61')/name
        summary=json.loads((root/'account/summary.json').read_bytes())
        audit=json.loads((root/'INDEPENDENT_AUDIT.json').read_bytes())
        assert audit['status'].startswith('PASS') and audit['actual_input_check']['status'].startswith('PASS')
        daily=pq.read_table(root/'account/daily_nav.parquet').to_pandas()
        assert len(daily)==61
        paths[name]=(daily.day_end_us.to_numpy(),np.diff(np.r_[10000.,daily.nav.to_numpy()]))
        if name in policies:
            r={k:summary[k] for k in keys}
            r['daily_risk']={k:summary['daily_metrics'][k] for k in ('annual_volatility','sharpe','max_drawdown')}
            r['resource_execution']=json.loads((root/'EXECUTION.json').read_bytes())
            r['independent_audit']=audit
            saved[name]=r
    comparisons={}
    for name in policies:
        dates,own=paths[name];comparisons[name]={}
        for ref in ('NO_CASH','WITH_CASH','STATIC50','CASH50'):
            t,other=paths[ref];assert np.array_equal(dates,t)
            loss=other<0
            comparisons[name][ref]=dict(reference_net_USDT=float(other.sum()),candidate_net_minus_reference_USDT=float(own.sum()-other.sum()),
                daily_net_delta_correlation=float(np.corrcoef(own,other)[0,1]),reference_loss_days=int(loss.sum()),
                candidate_positive_on_reference_loss_days=int((loss&(own>0)).sum()),candidate_flat_on_reference_loss_days=int((loss&(own==0)).sum()),
                candidate_net_on_reference_loss_days_USDT=float(own[loss].sum()),reference_net_on_reference_loss_days_USDT=float(other[loss].sum()),
                both_loss_days=int((loss&(own<0)).sum()))
    return dict(schema='TWO_ORIGINAL_E5_NATIVE61_SAVED_JOURNAL_DIAGNOSTICS_V1',calendar='2024-05-01 through 2024-07-01 exclusive',
        initial_USDT_each=10000,independent_fresh_accounts=True,account_stitching=False,guard=False,policies=saved,seen_daily_path_comparisons=comparisons,
        scope='Already seen chronological development; both candidates are trend mechanisms, not proven complementary or profitable',
        conclusion='Both paid net results are negative. Relative improvement versus saved reference wallets is descriptive, affected by unequal realized exposure, and does not justify promotion or model fitting.',
        fits=0,tuning=0,new_provider_retrievals=0,new_wallets=2)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=summarize(a.state);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(net_USDT={k:v['net_PnL'] for k,v in r['policies'].items()},seen_comparisons=r['seen_daily_path_comparisons'])),flush=True)


if __name__=='__main__':main()
