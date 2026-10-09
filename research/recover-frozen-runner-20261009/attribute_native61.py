"""Read saved native journals: monthly costs/exposure and daily co-occurrence."""
import argparse
from datetime import datetime,UTC
import json
from pathlib import Path


def attribute(state):
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq
    roots={k:state/'pool61'/k for k in ('SMA50_200_SIGNED','DONCHIAN_EXIT10')}
    roots['RSI2_LONG_SHORT']=state/'rsi61/RSI2_LONG_SHORT'
    roots.update({k:state/'results61'/k for k in ('STATIC50','CASH50')})
    records,paths={},{}
    for name,root in roots.items():
        summary=json.loads((root/'account/summary.json').read_bytes());audit=json.loads((root/'INDEPENDENT_AUDIT.json').read_bytes())
        assert audit['status'].startswith('PASS') and audit['actual_input_check']['status'].startswith('PASS')
        daily=pq.read_table(root/'account/daily_nav.parquet').to_pandas();dates=daily.day_end_us.to_numpy(np.int64)-86400000000
        assert len(dates)==61 and np.array_equal(dates,np.arange(1714521600000000,1719792000000000,86400000000))
        delta=np.diff(np.r_[10000.,daily.nav.to_numpy()]);paths[name]=(dates,delta)
        cols=['close_us','gross_weight','net_signed_weight']+[s+'_signed_weight' for s in summary['symbols']]
        minute=pq.read_table(root/'account/minute_nav_inventory.parquet',columns=cols).to_pandas()
        months=pd.to_datetime(minute.close_us.to_numpy()-1,unit='us',utc=True).strftime('%Y-%m');exposures={}
        for month in ('2024-05','2024-06'):
            rows=minute[months==month];weights=rows[[s+'_signed_weight' for s in summary['symbols']]].to_numpy()
            exposures[month]=dict(minutes=len(rows),mean_gross=float(rows.gross_weight.mean()),peak_gross=float(rows.gross_weight.max()),mean_net_signed=float(rows.net_signed_weight.mean()),mean_long_weight=float(np.maximum(weights,0).sum(1).mean()),mean_short_abs_weight=float(np.maximum(-weights,0).sum(1).mean()))
        for m in summary['months']:
            bridge=m['gross_PnL']-m['fees']-m['spread_cost']-m['slippage_cost']+m['funding_USDT']
            assert abs(bridge-m['net_PnL'])<1e-7
        row={k:summary[k] for k in ('NAV','net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT','trade_legs','normalized_total_turnover','all_observation_max_drawdown','maximum_actual_asset_weights','long_short_marked_contribution','months','first_entry_us','realized_exposure')}
        row.update(first_entry_UTC=datetime.fromtimestamp(summary['first_entry_us']/1e6,UTC).isoformat(),monthly_exposure=exposures,first20_net_USDT=float(delta[:20].sum()),remaining41_net_USDT=float(delta[20:].sum()),positive_days=int((delta>0).sum()),loss_days=int((delta<0).sum()),flat_days=int((delta==0).sum()),planned_risky_expert_budget_full_day='2024-05-10' if name=='CASH50' else '2024-05-20')
        records[name]=row
    comparisons={}
    for own in ('SMA50_200_SIGNED','DONCHIAN_EXIT10','RSI2_LONG_SHORT'):
        dates,a=paths[own];comparisons[own]={}
        for other in ('SMA50_200_SIGNED','DONCHIAN_EXIT10','RSI2_LONG_SHORT','STATIC50'):
            if own==other:continue
            t,b=paths[other];assert np.array_equal(dates,t)
            mask=(a>0)&(b<0)
            comparisons[own][other]=dict(daily_net_delta_correlation=float(np.corrcoef(a,b)[0,1]),positive_on_other_loss_days=int(mask.sum()),positive_on_other_loss_USDT=float(a[mask].sum()),net_on_all_other_loss_days_USDT=float(a[b<0].sum()),positive_on_other_loss_dates=[datetime.fromtimestamp(int(x)/1e6,UTC).date().isoformat() for x in dates[mask]],both_loss_days=int(((a<0)&(b<0)).sum()))
    both=(paths['SMA50_200_SIGNED'][1]<0)&(paths['DONCHIAN_EXIT10'][1]<0);rsi=paths['RSI2_LONG_SHORT'][1]
    return dict(schema='READ_ONLY_NATIVE61_MONTH_AND_DAILY_ATTRIBUTION_V1',calendar='May1-July1 exclusive2024',fresh_capital_USDT_each=10000,independent_wallets=True,wallets=records,co_occurrence=comparisons,
        RSI_on_both_trend_loss_days=dict(both_trend_loss_days=int(both.sum()),RSI_positive_days=int((both&(rsi>0)).sum()),RSI_net_USDT=float(rsi[both].sum())),
        standalone_VOL_CSMOM_MayJune_native_journals='NOT_RECOVERED; STATIC50 is the actual shared VOL/CS mixture, cannot decompose its fills/costs into separately funded expert payoffs',
        other_saved_VOL_CSMOM_native_accounts='Different2026JulyOctober scopes; excluded from2024regime attribution',
        ramp_hypothesis='20day CASH deployment differs from a continuously held portfolio, but no matched no-ramp or continuously running same-expert counterfactual has been run; first20 actual gains do not prove or refute opportunity cost',
        financial_interpretation='SMA positive price PnL erased by costs/funding; Donchian negative price PnL dominates; RSI slightly negative price PnL plus substantial costs/funding. May/June reversal alone does not imply the combined market simply fell.',
        oracle_sum_computed=False,executable_switching_payoff_claimed=False,new_replays=0,new_fits=0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=attribute(a.state);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(months={k:[m['net_PnL'] for m in v['months']] for k,v in r['wallets'].items()},RSI_complement=r['co_occurrence']['RSI2_LONG_SHORT'],both_loss=r['RSI_on_both_trend_loss_days'])),flush=True)
