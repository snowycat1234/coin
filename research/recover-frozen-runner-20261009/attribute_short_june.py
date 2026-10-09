"""Read-only June activity, risk scaling and unfilled-order attribution."""
import argparse
from collections import Counter
from datetime import datetime,UTC
import json
from pathlib import Path

START,END=1717200000000000,1719792000000000
DAY=86400000000


def attribute(directory):
    import numpy as np
    import pyarrow.parquet as pq
    account=directory/'account';read=lambda p:json.loads(p.read_bytes())
    meta=read(account/'target_meta.json');trades=read(account/'trades.json');rejections=read(account/'rejections.json')
    witnesses=read(directory/'INDEPENDENT_SIGNAL_WITNESSES.json');summary=read(account/'summary.json')
    minute=pq.read_table(account/'minute_nav_inventory.parquet').to_pandas()
    minute=minute[(minute.close_us>START)&(minute.close_us<=END)]
    targets=pq.read_table(account/'targets.parquet').to_pandas();targets=targets[(targets.available_us>=START)&(targets.available_us<END)]
    risks={r['decision_us']:r for r in meta['risk']}
    result={}
    stamp=lambda t:datetime.fromtimestamp(t/1e6,UTC).isoformat()
    for s in summary['symbols']:
        own=[r for r in witnesses if r['symbol']==s and START<=r['decision_us']<END]
        active=[r for r in own if r['held_short_after']]
        scales=[min(1,.1/risks[r['decision_us']]['unscaled_signed_covariance_annual_vol']) for r in active]
        weights=minute[s+'_signed_weight'].to_numpy();q=minute[s+'_quantity'].to_numpy()
        days=np.unique(((minute.close_us.to_numpy()[q<0]-1)//DAY)*DAY)
        fills=[r for r in trades if r['symbol']==s and START<=r['event_us']<END]
        initial=[r for r in fills if r['quantity_before']==0 and r['quantity_after']<0]
        exits=[r for r in fills if r['quantity_before']<0 and r['quantity_after']==0]
        reductions=[r for r in fills if r['leg']=='CLOSE' and r['quantity_after']<0]
        own_rejections=[r for r in rejections if r['symbol']==s and START<=r['event_us']<END]
        expired=[r for r in own_rejections if r.get('reason')=='FIVE_ATTEMPTS_EXPIRED']
        lookup={r['decision_us']:r['completed_close'] for r in own}
        expiries=[]
        for r in expired:
            # Signal price is a historical notional descriptor, not a fill.
            t=((r['event_us']-1)//DAY)*DAY;qleft=abs(r['remaining_signed_quantity'])
            expiries.append(dict(event_us=r['event_us'],order_id=r['order_id'],remaining_signed_quantity=r['remaining_signed_quantity'],
                below_one_lot=qleft<1e-8,remaining_notional_at_completed_signal_close=qleft*lookup[t],kind=r['kind']))
        target=targets[targets.symbol==s].target_weight.to_numpy()
        result[s]=dict(initial_short_entry_UTC=[stamp(r['event_us']) for r in initial],full_short_exit_UTC=[stamp(r['event_us']) for r in exits],
            actual_short_exposure_days=len(days),actual_short_exposure_dates=[stamp(int(t))[:10] for t in days],raw_active_signal_days=len(active),
            active_executable_target_days=int((target<0).sum()),days_with_any_fill=len({(r['event_us']//DAY) for r in fills}),
            mean_abs_actual_weight=float(-weights.mean()),peak_abs_actual_weight=float(-weights.min()),
            covariance_scale_active_day_mean=float(np.mean(scales)) if scales else None,covariance_scale_active_day_min=float(min(scales)) if scales else None,
            covariance_scaled_active_days=sum(x<1 for x in scales),raw_active_fraction=-.12,June_budget_scale=1.,
            fill_legs=len(fills),partial_position_reduction_legs=len(reductions),order_attempt_reasons=dict(Counter(str(r.get('reason')) for r in own_rejections)),
            expired_orders=expiries,hard_risk_reductions=0 if summary['risk_reduction_signal_count']==0 else 'SEE_BREACH_JOURNAL')
    return dict(schema='READ_ONLY_JUNE_SHORT_ACTIVITY_AND_RISK_ATTRIBUTION_V1',period='2024-06-01 to2024-07-01 exclusive',assets=result,
        budget='FULL_RISKY_EXPERT_BUDGET_SINCE_MAY20; JUNE_NOT_LIMITED_BY_INITIAL_CASH_RAMP',
        terminal='JUNE30_EXECUTED_TARGET_ZERO; RAW_SIGNAL_STATE_REMAINS_SEPARATE',
        distinctions='Raw inactivity, causal covariance scale-down, actual fill/exposure and below-minimum order residuals are distinct; no counterfactual gain calculated',
        new_wallets=0,new_fits=0,source_journals_modified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=attribute(a.directory);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({s:{k:v[k] for k in ('initial_short_entry_UTC','full_short_exit_UTC','actual_short_exposure_days','raw_active_signal_days','mean_abs_actual_weight','peak_abs_actual_weight','covariance_scale_active_day_mean','covariance_scale_active_day_min','days_with_any_fill','partial_position_reduction_legs')} for s,v in r['assets'].items()}),flush=True)
